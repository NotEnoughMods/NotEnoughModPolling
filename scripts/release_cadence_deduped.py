"""Analyze release cadence with batch-upload deduplication.

Same as release_cadence_raw.py, but collapses uploads within 1 hour of
each other into a single "release event". This gives a more realistic
picture since mods often upload multiple files (different MC versions)
simultaneously.

Run from repo root:
    uv run scripts/release_cadence_deduped.py
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

    # Collapse uploads within this window into a single release event
    BATCH_THRESHOLD_HOURS = 1

    all_gaps = []

    for name, _cid, dates, err in results:
        if err or not dates or len(dates) < 2:
            continue

        deduped = [dates[0]]
        for d in dates[1:]:
            if (deduped[-1] - d).total_seconds() > BATCH_THRESHOLD_HOURS * 3600:
                deduped.append(d)

        if len(deduped) < 2:
            continue

        gaps_days = [(deduped[i] - deduped[i + 1]).total_seconds() / 86400 for i in range(min(len(deduped) - 1, 20))]

        avg_gap = sum(gaps_days) / len(gaps_days)
        min_gap = min(gaps_days)
        p10_gap = sorted(gaps_days)[max(0, len(gaps_days) // 10)]

        all_gaps.append(
            {
                "name": name,
                "events": len(deduped),
                "avg_gap": round(avg_gap, 1),
                "min_gap": round(min_gap, 1),
                "p10_gap": round(p10_gap, 1),
                "days_since": round((now - dates[0]).total_seconds() / 86400, 0),
            }
        )

    all_gaps.sort(key=lambda x: x["min_gap"])

    print("Release events (batch uploads within 1h collapsed)")
    print("=" * 95)
    print(f"{'Mod':<30} {'Events':>7} {'MinGap':>8} {'P10Gap':>8} {'AvgGap':>8} {'Stale(d)':>9}")
    print("=" * 95)
    for m in all_gaps:
        print(
            f"{m['name']:<30} {m['events']:>7} {m['min_gap']:>8} "
            f"{m['p10_gap']:>8} {m['avg_gap']:>8} {m['days_since']:>9}"
        )

    min_gaps = [m["min_gap"] for m in all_gaps]
    min_gaps.sort()
    print("\n" + "=" * 60)
    print("GLOBAL SUMMARY (min gap = shortest time between release events)")
    print("=" * 60)
    print(f"Mods analyzed: {len(all_gaps)}")
    print(f"Fastest min gap: {min_gaps[0]} days ({min_gaps[0] * 24:.1f} hours)")
    p5 = min_gaps[len(min_gaps) // 20]
    print(f"5th percentile: {p5:.1f} days ({p5 * 24:.1f} hours)")
    p10 = min_gaps[len(min_gaps) // 10]
    print(f"10th percentile: {p10:.1f} days ({p10 * 24:.1f} hours)")
    p25 = min_gaps[len(min_gaps) // 4]
    print(f"25th percentile: {p25:.1f} days ({p25 * 24:.1f} hours)")
    p50 = min_gaps[len(min_gaps) // 2]
    print(f"Median: {p50:.1f} days ({p50 * 24:.1f} hours)")
    print(f"75th percentile: {min_gaps[3 * len(min_gaps) // 4]:.1f} days")
    print()
    print("Interpretation:")
    print("  The min gap is the shortest interval a mod has EVER released")
    print("  two distinct updates. Your polling interval only needs to be")
    print("  faster than this to never miss an update between cycles.")


asyncio.run(main())
