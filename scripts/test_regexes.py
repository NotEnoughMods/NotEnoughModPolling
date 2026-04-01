"""Test every active mod's regex against live API data and report results."""

import argparse
import asyncio
import contextlib
import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import aiohttp
import yaml

MODS_JSON = Path("mod_polling/mods.json")
CONFIG_YML = Path("mod_polling/config.yml")
REPORT_JSON = Path("scripts/regex_report.json")

STALE_CUTOFF = datetime.now(UTC) - timedelta(days=3 * 365)  # 3+ years = stale
REQUEST_DELAY = 0.3

# Status constants
PASS = "PASS"
FAIL = "FAIL"
DEAD = "DEAD"
STALE = "STALE"
SKIP = "SKIP"

CACHE_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "cfwidget_cache"
CACHE_TTL = timedelta(hours=1)


def load_config():
    with open(CONFIG_YML) as f:
        return yaml.safe_load(f)


def find_regex(data):
    """Recursively find the 'regex' key in a mod's data dict."""
    if isinstance(data, dict):
        if "regex" in data:
            return data["regex"]
        for v in data.values():
            ret = find_regex(v)
            if ret:
                return ret
    return None


def cache_get(url):
    """Return cached JSON for url if fresh, else None."""
    key = hashlib.sha256(url.encode()).hexdigest()
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
        if age < CACHE_TTL:
            with open(path) as f:
                return json.load(f)
    return None


def cache_put(url, data):
    """Store JSON response in cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()
    path = CACHE_DIR / f"{key}.json"
    with open(path, "w") as f:
        json.dump(data, f)


def check_group_quality(match, regex_str):
    """Check for quality issues in named group captures. Returns list of warnings."""
    warnings = []
    groups = match.groupdict()

    mc = groups.get("mc")
    version = groups.get("version")

    # mc group should only contain version-like characters (digits and dots)
    if mc and re.search(r"[a-zA-Z]", mc):
        warnings.append(f"mc group contains non-version chars: '{mc}'")

    # version should not contain the MC version
    if version and mc and mc in version:
        warnings.append(f"version group contains MC version '{mc}': '{version}'")

    # version starting with MC version pattern (1.X.Y-...) followed by a separator
    # and another digit is suspicious if there's no mc group
    if version and not mc and re.match(r"1\.\d{2,}(?:\.\d+)*[-+]\d", version):
        warnings.append(f"version may contain MC version (no mc group): '{version}'")

    return warnings


async def fetch_json(session, url, use_cache):
    """Fetch JSON from url, using cache if enabled."""
    if use_cache:
        cached = cache_get(url)
        if cached is not None:
            return cached

    async with session.get(url) as resp:
        if resp.status >= 400:
            return {"_http_error": resp.status}
        data = await resp.json(content_type=None)

    if use_cache:
        cache_put(url, data)
    return data


async def check_curse(session, mod_name, mod_data, compiled_regex, *, use_cache=False, all_files=False):
    curse = mod_data["curse"]
    curse_id = curse["id"]
    field_name = curse.get("field", "name")
    url = f"https://api.cfwidget.com/{curse_id}"

    data = await fetch_json(session, url, use_cache)

    if "_http_error" in data:
        return DEAD, f"HTTP {data['_http_error']}", None, [], []
    if data.get("accepted"):
        return DEAD, "cfwidget queued (not yet cached)", None, [], []
    if "error" in data:
        return DEAD, f"cfwidget error: {data['error']}", None, [], []
    if not data.get("files"):
        return DEAD, "No files in cfwidget response", None, [], []

    sorted_files = sorted(data["files"], key=lambda x: x["id"], reverse=True)
    filenames = [f[field_name] for f in sorted_files]

    # Check last update date
    last_update = None
    for f in sorted_files:
        uploaded = f.get("uploaded_at")
        if uploaded:
            with contextlib.suppress(ValueError, TypeError):
                last_update = datetime.fromisoformat(uploaded.replace("Z", "+00:00"))
            break

    quality_warnings = []

    # Test regex against the LATEST file first (mirrors real bot behavior)
    latest = filenames[0] if filenames else None
    if latest:
        match = compiled_regex.search(latest)
        if not match:
            # Show non-matching files for debugging
            detail = f"Regex doesn't match latest release: {latest}"
            return FAIL, detail, last_update, filenames[:5], quality_warnings

        quality_warnings = check_group_quality(match, compiled_regex.pattern)

        # All-files analysis
        all_files_info = []
        if all_files and filenames:
            matched = 0
            non_matching = []
            for fn in filenames:
                m = compiled_regex.search(fn)
                if m:
                    matched += 1
                elif len(non_matching) < 5:
                    non_matching.append(fn)
            rate = matched / len(filenames) * 100
            all_files_info = [f"Match rate: {matched}/{len(filenames)} ({rate:.0f}%)"]
            if non_matching:
                all_files_info.append(f"Non-matching: {non_matching}")

        if last_update and last_update < STALE_CUTOFF:
            return (
                STALE,
                f"Match: {latest} -> {match.groupdict()}",
                last_update,
                filenames[:5] + all_files_info,
                quality_warnings,
            )
        return (
            PASS,
            f"Match: {latest} -> {match.groupdict()}",
            last_update,
            filenames[:5] + all_files_info,
            quality_warnings,
        )

    return FAIL, "No filenames found", last_update, [], quality_warnings


async def check_jenkins(session, mod_name, mod_data, compiled_regex, *, use_cache=False, all_files=False):
    jenkins = mod_data["jenkins"]
    url = jenkins["url"]
    item_idx = jenkins.get("item", 0)

    fetch_url = url + "?tree=artifacts[fileName],timestamp"

    data = await fetch_json(session, fetch_url, use_cache)

    if "_http_error" in data:
        return DEAD, f"HTTP {data['_http_error']}", None, [], []
    if not data.get("artifacts"):
        return DEAD, "No artifacts", None, [], []

    filenames = [a["fileName"] for a in data["artifacts"]]

    last_update = None
    ts = data.get("timestamp")
    if ts:
        last_update = datetime.fromtimestamp(ts / 1000, tz=UTC)

    if item_idx < len(filenames):
        target = filenames[item_idx]
        match = compiled_regex.search(target)
        if match:
            quality_warnings = check_group_quality(match, compiled_regex.pattern)
            if last_update and last_update < STALE_CUTOFF:
                return STALE, f"Match: {target} -> {match.groupdict()}", last_update, filenames, quality_warnings
            return PASS, f"Match: {target} -> {match.groupdict()}", last_update, filenames, quality_warnings
        return FAIL, f"No match on artifact[{item_idx}]: {target}", last_update, filenames, []

    return FAIL, f"Artifact index {item_idx} out of range ({len(filenames)} artifacts)", last_update, filenames, []


async def check_github_release(
    session, mod_name, mod_data, compiled_regex, config, *, use_cache=False, all_files=False
):
    github = mod_data["github"]
    repo = github["repo"]
    type_ = github.get("type", "asset")

    url = f"https://api.github.com/repos/{repo}/releases"

    client_id = config.get("github", {}).get("client_id")
    client_secret = config.get("github", {}).get("client_secret")

    kwargs = {}
    if client_id and client_secret:
        kwargs["auth"] = aiohttp.BasicAuth(client_id, client_secret)

    async with session.get(url, **kwargs) as resp:
        if resp.status >= 400:
            return DEAD, f"HTTP {resp.status}", None, [], []
        releases = await resp.json(content_type=None)

    if not releases:
        return DEAD, "No releases", None, [], []

    last_update = None
    published = releases[0].get("published_at")
    if published:
        with contextlib.suppress(ValueError, TypeError):
            last_update = datetime.fromisoformat(published.replace("Z", "+00:00"))

    if type_ == "tag":
        tag_name = releases[0]["tag_name"]
        if compiled_regex:
            match = compiled_regex.search(tag_name)
            if match:
                quality_warnings = check_group_quality(match, compiled_regex.pattern)
                if last_update and last_update < STALE_CUTOFF:
                    return (
                        STALE,
                        f"Match tag: {tag_name} -> {match.groupdict()}",
                        last_update,
                        [tag_name],
                        quality_warnings,
                    )
                return PASS, f"Match tag: {tag_name} -> {match.groupdict()}", last_update, [tag_name], quality_warnings
            return FAIL, f"No match on tag: {tag_name}", last_update, [tag_name], []
        else:
            if last_update and last_update < STALE_CUTOFF:
                return STALE, f"Tag (no regex): {tag_name}", last_update, [tag_name], []
            return PASS, f"Tag (no regex): {tag_name}", last_update, [tag_name], []

    for release in releases:
        asset_names = [a["name"] for a in release.get("assets", [])]
        for name in asset_names:
            match = compiled_regex.search(name)
            if match:
                quality_warnings = check_group_quality(match, compiled_regex.pattern)
                if last_update and last_update < STALE_CUTOFF:
                    return (
                        STALE,
                        f"Match: {name} -> {match.groupdict()}",
                        last_update,
                        asset_names[:5],
                        quality_warnings,
                    )
                return PASS, f"Match: {name} -> {match.groupdict()}", last_update, asset_names[:5], quality_warnings

    all_assets = []
    for release in releases[:3]:
        all_assets.extend(a["name"] for a in release.get("assets", []))
    total_releases = min(3, len(releases))
    return (
        FAIL,
        f"No match in {len(all_assets)} assets across {total_releases} releases",
        last_update,
        all_assets[:10],
        [],
    )


async def check_forge_json(session, mod_name, mod_data, compiled_regex, *, use_cache=False, all_files=False):
    forgejson = mod_data["forgejson"]
    url = forgejson["url"]

    data = await fetch_json(session, url, use_cache)

    if "_http_error" in data:
        return DEAD, f"HTTP {data['_http_error']}", None, [], []
    if "promos" not in data:
        return DEAD, "No 'promos' key in response", None, [], []

    promos = data["promos"]
    if not promos:
        return DEAD, "Empty promos", None, [], []

    versions = []
    for promo, version in promos.items():
        if promo == "reserved":
            continue
        versions.append(f"{promo}: {version}")

    if versions:
        return PASS, f"Found {len(versions)} promo entries", None, versions[:5], []
    return FAIL, "No valid promo entries", None, [], []


async def check_mcforge2(session, mod_name, mod_data, compiled_regex, *, use_cache=False, all_files=False):
    mcforge = mod_data["mcforge"]
    url = mcforge["url"]

    data = await fetch_json(session, url, use_cache)

    if "_http_error" in data:
        return DEAD, f"HTTP {data['_http_error']}", None, [], []
    if "promos" not in data:
        return DEAD, "No 'promos' key", None, [], []

    promos = data["promos"]
    if not promos:
        return DEAD, "Empty promos", None, [], []

    entries = [f"{k}: {v}" for k, v in list(promos.items())[:10]]
    return PASS, f"Found {len(promos)} promo entries", None, entries[:5], []


async def check_html(session, mod_name, mod_data, compiled_regex, *, use_cache=False, all_files=False):
    html = mod_data["html"]
    url = html["url"]

    async with session.get(url) as resp:
        if resp.status >= 400:
            return DEAD, f"HTTP {resp.status}", None, [], []
        page = await resp.text()

    matches = list(compiled_regex.finditer(page))
    if matches:
        results = [m.groupdict() for m in matches[:5]]
        return PASS, f"Found {len(matches)} matches: {results}", None, [], []
    return FAIL, f"No regex matches in HTML page ({len(page)} chars)", None, [], []


async def check_buildcraft(session, mod_name, mod_data, compiled_regex, *, use_cache=False, all_files=False):
    url = "https://raw.githubusercontent.com/BuildCraft/BuildCraft/master/buildcraft_resources/versions.txt"

    async with session.get(url) as resp:
        if resp.status >= 400:
            return DEAD, f"HTTP {resp.status}", None, [], []
        page = await resp.text()

    lines = [line for line in page.splitlines() if line]
    if lines:
        mc, _mod_name, version = lines[-1].split(":")
        return PASS, f"mc={mc}, version={version}", None, lines[-3:], []
    return FAIL, "No version lines found", None, [], []


async def check_custom_dead(session, mod_name, mod_data, compiled_regex, *, use_cache=False, all_files=False):
    """For custom parsers (CheckSpacechase, CheckLunatrius, CheckBigReactors) — likely dead."""
    return DEAD, "Custom parser endpoint (likely dead)", None, [], []


async def check_neoforge(session, mod_name, mod_data, compiled_regex, *, use_cache=False, all_files=False):
    url = mod_data["neoforge"]["url"]
    fallback_url = mod_data["neoforge"].get("fallback_url")

    data = None
    for attempt_url in [url, fallback_url]:
        if not attempt_url:
            continue
        try:
            async with session.get(attempt_url) as resp:
                if resp.status >= 400:
                    continue
                data = await resp.json(content_type=None)
                break
        except Exception:
            continue

    if data is None:
        return DEAD, "Both primary and fallback URLs failed", None, [], []

    versions = data.get("versions", [])
    if not versions:
        return DEAD, "Empty versions list", None, [], []

    samples = versions[-5:]
    return PASS, f"Found {len(versions)} NeoForge versions", None, samples, []


PARSER_MAP = {
    "cfwidget": check_curse,
    "jenkins": check_jenkins,
    "github_release": check_github_release,
    "forge_json": check_forge_json,
    "mcforge_v2": check_mcforge2,
    "html": check_html,
    "buildcraft": check_buildcraft,
    "neoforge": check_neoforge,
}


async def test_mod(session, mod_name, mod_data, config, *, use_cache=False, all_files=False):
    function = mod_data.get("parser", "")

    if not mod_data.get("active", True):
        return {
            "name": mod_name,
            "status": SKIP,
            "parser": function,
            "detail": "Marked inactive",
            "last_update": None,
            "samples": [],
            "quality_warnings": [],
        }

    regex_str = find_regex(mod_data)
    compiled_regex = re.compile(regex_str, re.I) if regex_str else None

    checker = PARSER_MAP.get(function)
    if not checker:
        return {
            "name": mod_name,
            "status": DEAD,
            "parser": function,
            "detail": f"Unknown parser: {function}",
            "last_update": None,
            "samples": [],
            "quality_warnings": [],
        }

    try:
        if function == "github_release":
            status, detail, last_update, samples, quality_warnings = await checker(
                session,
                mod_name,
                mod_data,
                compiled_regex,
                config,
                use_cache=use_cache,
                all_files=all_files,
            )
        else:
            status, detail, last_update, samples, quality_warnings = await checker(
                session,
                mod_name,
                mod_data,
                compiled_regex,
                use_cache=use_cache,
                all_files=all_files,
            )
    except Exception as e:
        status = DEAD
        detail = f"Exception: {type(e).__name__}: {e}"
        last_update = None
        samples = []
        quality_warnings = []

    return {
        "name": mod_name,
        "status": status,
        "parser": function,
        "detail": detail,
        "last_update": last_update.isoformat() if last_update else None,
        "samples": samples,
        "quality_warnings": quality_warnings,
    }


async def main():
    parser = argparse.ArgumentParser(description="Test mod regexes against live API data")
    parser.add_argument("--cache", action="store_true", help="Cache API responses (1-hour TTL)")
    parser.add_argument("--all-files", action="store_true", help="Test regex against ALL files, not just latest")
    parser.add_argument("--mod", type=str, help="Test a single mod by name")
    args = parser.parse_args()

    with open(MODS_JSON) as f:
        mods = json.load(f)

    config = load_config()

    if args.mod:
        if args.mod not in mods:
            print(f"Mod '{args.mod}' not found in mods.json")
            print(f"Available: {', '.join(sorted(mods.keys()))}")
            return
        mods = {args.mod: mods[args.mod]}

    timeout = aiohttp.ClientTimeout(total=15)
    connector = aiohttp.TCPConnector(limit=5)
    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        headers={"User-Agent": "NotEnoughMods:RegexTest/2.0 (+https://github.com/NotEnoughMods/NotEnoughModPolling)"},
    ) as session:
        results = []
        total = len(mods)

        for i, (mod_name, mod_data) in enumerate(mods.items(), 1):
            active = mod_data.get("active", True)
            function = mod_data.get("parser", "?")

            if not active:
                result = {
                    "name": mod_name,
                    "status": SKIP,
                    "parser": function,
                    "detail": "Marked inactive",
                    "last_update": None,
                    "samples": [],
                    "quality_warnings": [],
                }
                results.append(result)
                print(f"[{i:3d}/{total}] SKIP  {mod_name} (inactive)")
                continue

            result = await test_mod(
                session,
                mod_name,
                mod_data,
                config,
                use_cache=args.cache,
                all_files=args.all_files,
            )
            results.append(result)

            status = result["status"]
            color = {
                PASS: "\033[32m",
                FAIL: "\033[31m",
                DEAD: "\033[90m",
                STALE: "\033[33m",
            }.get(status, "")
            reset = "\033[0m"

            update_str = ""
            if result["last_update"]:
                update_str = f" [last update: {result['last_update'][:10]}]"

            warn_str = ""
            if result["quality_warnings"]:
                warn_str = f" \033[33m⚠ {len(result['quality_warnings'])} warning(s)\033[0m"

            print(f"[{i:3d}/{total}] {color}{status:5s}{reset} {mod_name} ({function}){update_str}{warn_str}")
            if status in (FAIL, DEAD):
                print(f"        {result['detail']}")
                if result["samples"]:
                    for s in result["samples"][:3]:
                        print(f"          sample: {s}")
            if result["quality_warnings"]:
                for w in result["quality_warnings"]:
                    print(f"        \033[33mWARN: {w}\033[0m")

            await asyncio.sleep(REQUEST_DELAY)

    # Summary
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    quality_warn_count = sum(1 for r in results if r["quality_warnings"])

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for status in [PASS, FAIL, DEAD, STALE, SKIP]:
        if status in counts:
            print(f"  {status:5s}: {counts[status]}")
    print(f"  TOTAL: {len(results)}")
    if quality_warn_count:
        print(f"  Quality warnings: {quality_warn_count} mod(s)")

    # List FAILs
    fails = [r for r in results if r["status"] == FAIL]
    if fails:
        print(f"\nFAILED MODS ({len(fails)}):")
        for r in fails:
            print(f"  - {r['name']}: {r['detail']}")

    # List quality warnings
    warned = [r for r in results if r["quality_warnings"]]
    if warned:
        print(f"\nQUALITY WARNINGS ({len(warned)}):")
        for r in warned:
            for w in r["quality_warnings"]:
                print(f"  - {r['name']}: {w}")

    # Write report
    with open(REPORT_JSON, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nReport written to {REPORT_JSON}")


if __name__ == "__main__":
    asyncio.run(main())
