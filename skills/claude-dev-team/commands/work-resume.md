---
name: work-resume
description: Resume a paused slice. Restores current-work.json from .claude/paused/, checks out the branch, fetches latest main and reports any conflicts coming from upstream changes, surfaces the "where I left off" summary so the user (and Claude) can pick up cold. Use when the user wants to come back to a previously paused slice.
---

# /work-resume

You're the resume command. Surface the saved context so the slice can pick up without re-discovery.

## Argument

- An issue ID (e.g. `#42` or `42`).
- No arg → list available paused snapshots and ask the user to pick one.

## Prechecks

1. Confirm `.claude/paused/<issue-id>.json` exists. If not, error: "No paused snapshot for that issue. Available: <list>."
2. Check `.claude/current-work.json`. If present and active, refuse: "Slice <other-id> is currently active. Pause or finish it first."

## Restore state

1. Read the paused snapshot.
2. Restore `current-work.json` from `current_work_snapshot` field.
3. `git checkout <branch>` from the snapshot.

## Reconcile with main

The branch may have drifted from main while paused. Run:

- `git fetch origin`
- Compute "commits in main not in branch" (`git log <branch>..origin/main --oneline`)
- If non-empty, surface the count and ask: "Main has moved by N commits. Rebase or merge now, or defer?" Default: defer (let the user choose when to deal with it).

If there are likely conflicts (`git merge-tree` or similar quick check), surface that too.

## Surface the summary

Print the `left_off_summary` from the snapshot prominently. This is the entry point for Claude into the slice — read it carefully and use it as context for any subsequent tool calls.

## Update current-work.json

Set `last_phase_change_at` to now (so staleness checks restart). Phase stays as it was at pause.

## Log

Append to `.claude/events.jsonl`:
```json
{"ts": "<ISO>", "event": "work_resume", "issue_id": "<id>", "paused_for_days": <N>}
```

## Clean up

Delete the snapshot file at `.claude/paused/<issue-id>.json` (it's been promoted back to active state).

## Final output

- Branch checked out
- Phase
- The "left off" summary
- Main-drift status
- Suggested next: continue from the next-action in the summary.

## Don'ts

- Do not silently rebase or merge without asking.
- Do not skip surfacing the summary.
- Do not lose the snapshot — only delete after successful restore.
