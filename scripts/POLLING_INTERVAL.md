# Polling interval analysis

Last run: March 2026 against 127 active CurseForge mods.

## How polling works

1. `polling_task` polls all active mods, then sleeps for `interval` seconds.
2. `NEMP_TimerEvent` checks for results every 60 seconds.
3. Effective time between cycle starts = cycle duration + interval.

127 of the 145 active mods use CurseForge (api.cfwidget.com). Requests to
the same host are serialized with a 0.5s delay, so one cycle takes ~3-4
minutes just for CurseForge before the sleep even starts.

## Mod release cadence

Data sourced from cfwidget's `uploaded_at` timestamps across all files for
each mod. Batch uploads (multiple MC versions within 1 hour) are collapsed
into a single release event.

### Per-mod shortest gap between distinct release events

| Percentile | Gap          |
|------------|--------------|
| 25th       | ~2.4 hours   |
| Median     | ~2.4 hours   |
| 75th       | ~17 hours    |

### Average gap between releases

| Stat   | Gap      |
|--------|----------|
| Min    | < 1 day  |
| Median | ~29 days |
| Mean   | ~61 days |

### Staleness

- 50 out of 127 mods haven't been updated in over a year.
- 14 mods have only ever had a single release (all Reika's mods, last
  updated August 2023).

## Conclusion

Even the fastest mods rarely release more than once per day. The median mod
releases roughly monthly. A 30-minute interval (1800s) catches all updates
well within a reasonable timeframe while being respectful to cfwidget's API.

The previous default of 300s (5 minutes) resulted in ~8-minute effective
cycles, polling roughly 180 times per day — far more than the ~1 update/day
that even the most active mods produce.

## Scripts

- `scripts/release_cadence_raw.py` — per-file analysis (no deduplication)
- `scripts/release_cadence_deduped.py` — with batch-upload deduplication
