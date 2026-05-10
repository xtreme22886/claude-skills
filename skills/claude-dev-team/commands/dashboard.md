---
name: dashboard
description: Full-picture status across all your projects — active slices, paused slices with last-touched dates, open MRs/PRs, recent CI flakes, doc-publish status, and a "suggested next actions" section that surfaces gentle nudges (stale paused slices, missing docs, etc.). Use when the user wants a Monday-morning overview or asks "what's going on across my work".
---

# /dashboard

You're the on-demand rich status command. Pulls cross-project state, surfaces gentle nudges that don't make it into the always-on status line.

## Discover projects

The `default_project_root` from `~/.config/claude-dev-team/config.toml` is the search root. Find subdirectories that contain a `.claude/project.json` — those are dev-team-managed projects.

## For each project, gather

- Active slice (from `.claude/current-work.json`)
- Paused slices (from `.claude/paused/`)
- Open MRs/PRs (via tracker adapter, filtered to `assignee == me` or `author == me`)
- CI status of any open MR/PRs
- Recent flakes (last 7 days from `.claude/flakes.jsonl`)
- Doc-publish status: any `docs/ops/` files modified locally vs the most recent published-to-Notion timestamp

## Compose the dashboard

```
=== Active work ===

projectA:
  #42 Add user timezone preference  [implement, 3h 12m]
projectB:
  (no active slice)

=== Paused (3) ===

projectA #41 Refactor session middleware  (paused 12 days ago)  ⚠ stale
projectB #38 Improve search UX            (paused 3 days ago)
projectC #15 Migrate config to TOML       (paused 21 days ago)  ⚠ stale

=== Open MRs/PRs (2) ===

projectA !87  Add timezone preference     CI: passing  Reviewer: 2 comments
projectD !142 Fix race in worker pool     CI: failing  ⚠

=== Recent CI flakes (last 7d) ===

projectA: 2 flakes (network timeouts on test stage)
projectD: 1 flake

=== Doc publish status ===

projectA: docs/ops/ unchanged since last publish
projectB: 1 file modified locally, not yet on main → will publish on merge

=== Suggested next actions ===

- ⚠ projectD MR !142 — CI failing, address before continuing other work
- projectA: 2 reviewer comments waiting on you
- ⚠ Paused slice projectA#41 idle 12 days. Resume or close?
- ⚠ Paused slice projectC#15 idle 21 days. Resume or close?
```

## Output rules

- Always include all four "=== ... ===" sections, even if empty (print "(none)" for empty).
- Use ⚠ to mark items the user should look at; bold-equivalent (or just the warning glyph in plain text).
- Soft nudges (paused stale, doc-publish-pending) live ONLY here — not in the status line.
- Tracker calls in parallel where possible.

## Performance notes

This command can be slow if there are many projects or many MRs. Cap concurrency at ~5 parallel tracker calls. If a single tracker call exceeds 5s, mark that project as "(tracker slow)" and continue.

## Don'ts

- Do not modify any state.
- Do not include any project that doesn't have a `.claude/project.json` — those aren't ours.
- Do not block on slow trackers; show partial data with a clear marker.
