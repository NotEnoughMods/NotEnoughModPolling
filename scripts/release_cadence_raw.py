"""Analyze release cadence of all active CurseForge mods.

Fetches upload timestamps from cfwidget for every active CurseForge mod
in mods.json and reports per-file release gaps (no deduplication).

Run from repo root:
    uv run scripts/release_cadence_raw.py
"""

import asyncio
import json
from datetime import UTC, datetime

import aiohttp


async def fetch_mod(session, name, curse_id, semaphore):
    url = f"https://api.cfwidget.com/{curse_id}"
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                data = await resp.json(content_type=None)
                if "error" in data or data.get("accepted"):
                    return (name, curse_id, None, "error/queued")
                files = data.get("files", [])
                if not files:
                    return (name, curse_id, None, "no files")
                dates = []
                for f in files:
                    uploaded = f.get("uploaded_at")
                    if uploaded:
                        dt = datetime.fromisoformat(uploaded.replace("Z", "+00:00"))
                        dates.append(dt)
                dates.sort(reverse=True)
                return (name, curse_id, dates, None)
        except Exception as e:
            return (name, curse_id, None, str(e))


async def main():
    with open("mod_polling/mods.json") as f:
        mods = json.load(f)

    curse_mods = [
        (name, info["curse"]["id"])
        for name, info in mods.items()
        if info.get("function") == "CheckCurse" and info.get("active", True)
    ]

    semaphore = asyncio.Semaphore(5)

    async with aiohttp.ClientSession(headers={"User-agent": "NotEnoughMods:CadenceCheck/1.0"}) as session:
        tasks = [fetch_mod(session, name, cid, semaphore) for name, cid in curse_mods]
        results = await asyncio.gather(*tasks)

    now = datetime.now(UTC)

    all_gaps = []
    errors = []

    for name, cid, dates, err in results:
        if err or not dates:
            errors.append((name, cid, err or "no dates"))
            continue

        latest = dates[0]
        days_since_latest = (now - latest).total_seconds() / 86400

        if len(dates) >= 2:
            gaps = [(dates[i] - dates[i + 1]).total_seconds() / 86400 for i in range(min(len(dates) - 1, 20))]
            avg_gap = sum(gaps) / len(gaps)
            min_gap = min(gaps)
            median_gap = sorted(gaps)[len(gaps) // 2]
        else:
            avg_gap = None
            min_gap = None
            median_gap = None

        all_gaps.append(
            {
                "name": name,
                "latest": latest.isoformat(),
                "days_since_latest": round(days_since_latest, 1),
                "num_releases": len(dates),
                "avg_gap_days": round(avg_gap, 1) if avg_gap else None,
                "min_gap_days": round(min_gap, 2) if min_gap else None,
                "median_gap_days": round(median_gap, 1) if median_gap else None,
            }
        )

    with_gaps = [m for m in all_gaps if m["avg_gap_days"] is not None]
    without_gaps = [m for m in all_gaps if m["avg_gap_days"] is None]
    with_gaps.sort(key=lambda x: x["avg_gap_days"])

    print("=" * 90)
    print(f"{'Mod':<30} {'Latest':<12} {'Age(d)':>7} {'Rels':>5} {'AvgGap':>8} {'MinGap':>8} {'MedGap':>8}")
    print("=" * 90)
    for m in with_gaps:
        print(
            f"{m['name']:<30} {m['latest'][:10]:<12} {m['days_since_latest']:>7} "
            f"{m['num_releases']:>5} {m['avg_gap_days']:>8} {m['min_gap_days']:>8} "
            f"{m['median_gap_days']:>8}"
        )

    if without_gaps:
        print("\n--- Single release only ---")
        for m in without_gaps:
            print(f"{m['name']:<30} {m['latest'][:10]:<12} {m['days_since_latest']:>7} {m['num_releases']:>5}")

    if errors:
        print(f"\n--- Errors ({len(errors)}) ---")
        for name, cid, err in errors:
            print(f"{name:<30} {cid:<10} {err}")

    min_gaps_all = [m["min_gap_days"] for m in with_gaps if m["min_gap_days"] is not None]
    avg_gaps_all = [m["avg_gap_days"] for m in with_gaps]
    ages = [m["days_since_latest"] for m in all_gaps]

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total mods analyzed: {len(all_gaps)}")
    print(f"Mods with errors: {len(errors)}")
    print(f"Mods with 2+ releases: {len(with_gaps)}")
    print()
    print("Across all mods (min gap between any two consecutive releases):")
    print(f"  Smallest min gap: {min(min_gaps_all):.2f} days ({min(min_gaps_all) * 24:.1f} hours)")
    print(f"  Median of min gaps: {sorted(min_gaps_all)[len(min_gaps_all) // 2]:.2f} days")
    p10 = sorted(min_gaps_all)[len(min_gaps_all) // 10]
    print(f"  10th percentile min gap: {p10:.2f} days ({p10 * 24:.1f} hours)")
    print()
    print("Average gap between releases:")
    print(f"  Smallest avg gap: {min(avg_gaps_all):.1f} days")
    print(f"  Median avg gap: {sorted(avg_gaps_all)[len(avg_gaps_all) // 2]:.1f} days")
    print(f"  Mean avg gap: {sum(avg_gaps_all) / len(avg_gaps_all):.1f} days")
    print()
    print("Days since latest release:")
    print(f"  Min: {min(ages):.0f} days")
    print(f"  Median: {sorted(ages)[len(ages) // 2]:.0f} days")
    print(f"  Mean: {sum(ages) / len(ages):.0f} days")
    print(f"  Mods not updated in 1+ year: {sum(1 for a in ages if a > 365)}")


asyncio.run(main())
