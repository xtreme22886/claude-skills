---
name: work-status
description: Show the current slice's state — issue, phase, branch, MR/PR status, CI status, anything blocking. Read-only, no side effects. Use when the user wants a quick snapshot of "what am I working on right now".
---

# /work-status

You're the at-a-glance status command. Read-only.

## What to read

1. `.claude/current-work.json` — the active slice.
2. If active and has `merge_request_url` — fetch the MR/PR status and CI status via the tracker adapter.
3. `.claude/paused/` — list paused snapshots so the user remembers what's on the back burner.

## What to print

If no active slice and no paused: "No active or paused slices. Pick one with `/work-start`."

If active slice:

```
Active slice: #42 — Add user timezone preference
  Branch:   slice/42-user-timezone
  Phase:    implement
  Started:  2026-05-04 09:14 (3h 12m ago)
  MR/PR:    not yet opened
  CI:       n/a
```

If review phase, show MR/PR + CI status:

```
Active slice: #42 — Add user timezone preference
  Branch:   slice/42-user-timezone
  Phase:    review
  MR:       https://gitlab.../merge_requests/87
  CI:       passing (12/12 jobs green)
  Reviewer: 2 comments, awaiting your reply
```

If paused snapshots exist, append at the bottom:

```
Paused (2):
  #41 — Refactor session middleware  (paused 12 days ago)
  #38 — Improve search UX            (paused 3 days ago)
```

## Don'ts

- Do not modify any state.
- Do not print unrelated context (recent commits, etc.) — `/dashboard` is for that.
- Do not block on slow tracker fetches. If the tracker call takes >5s, fall back to local data only and add a note "tracker slow — showing local state only".
