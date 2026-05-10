---
name: team-stats
description: Read .claude/events.jsonl and .claude/flakes.jsonl in the current project (or aggregated across all dev-team projects with --all) and report metrics — slice durations, rethink frequency, CI flake patterns, doc-completion rate. Use when the user wants to see how the development process is actually going, spot patterns, or sanity-check whether slices are getting smaller over time.
---

# /team-stats

You're the local telemetry reporter. Read-only over `.claude/events.jsonl` and `.claude/flakes.jsonl`. No network calls.

## Args

- No args → current project only.
- `--all` → aggregate across all projects under `default_project_root`.
- `--since <date|relative>` → window. Default: last 30 days.
- `--format json` → machine-readable output.

## Compute

Parse the events.jsonl streams. Compute:

### Slice metrics

- Total slices completed in window
- Median, p25, p75 duration (from `started_at` to `work_done`)
- % of slices completed within `slice.target_session_hours` (from defaults.toml)
- % over `slice.ceiling_hours` (these are the ones that should have been epics)

### Phase metrics

- Median time in design, implement, review (per-phase durations)
- Distribution of phase transitions — does the user usually go design → implement → review → done, or are there frequent rethinks?

### Rethink metrics

- Number of `work_rethink` events in window
- Decision distribution: a / b1 / b2
- Median time-into-slice when rethink fires (early rethinks = healthier than late)

### Pause/resume metrics

- Number of slices paused
- Median pause duration before resume
- Slices paused but never resumed (>30 days) — these are the ones we should close

### CI flake metrics

- Flake count per project, per stage
- Most common failure_excerpt patterns (top 3)

### Doc completion

- For each `work_done`, did the slice include changes under `docs/user-guide/`, `docs/troubleshooting/`, `docs/ops/`?
- Surface % completion rate for each.

## Output

Pretty-printed report (markdown). Headlines first, drill-downs after. Example:

```
=== team-stats — projectA — last 30 days ===

Slices: 12 completed. Median duration: 2h 41m.
  ✓ 8 (67%) within 3h target
  ⚠ 1 (8%) over 8h ceiling (should have been an epic)

Phase distribution (medians):
  design     22m
  implement  1h 58m
  review     19m

Rethinks: 3 (25% of slices)
  → All early-stage (< 30m in)
  → Decisions: 1× a (design tweak), 2× b2 (close + spike)

Pauses: 4 paused. 2 resumed. 2 idle >14 days.

CI flakes: 3 (1 stage:test network timeout x3) — investigate
Doc completion: user-guide 75% / troubleshooting 50% / ops 33%
```

If `--format json`, dump the same data structured.

## Don'ts

- Do not make any tracker calls. Local logs only.
- Do not aggregate across projects unless `--all` is passed — different projects have different rhythms.
- Do not infer trends from <5 data points. Say "not enough data" instead.
