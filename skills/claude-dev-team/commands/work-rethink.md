---
name: work-rethink
description: Mid-slice escape hatch when the slice scope or design turns out to be wrong. Snapshots WIP, forces a deliberate decision (reshape this slice OR close it and file a separate design spike), and records the rethink trail on the original issue. Prevents silent scope creep. Use when the user realizes mid-implementation that the slice is the wrong shape.
---

# /work-rethink

You're the rethink command. The whole point: catching the wrong-shape slice *small* instead of *large*. Make the rethink a first-class flow, not a guilty silent rework.

## Prechecks

1. Read `.claude/current-work.json`. Refuse if missing.
2. WIP-commit any uncommitted changes to the slice branch (commit message: `WIP: rethink trigger`). Don't lose work.

## Force the decision

Ask the user explicitly — show both options and require a choice:

> The slice as filed turned out to be the wrong shape. What's the actual situation?
>
>   **(a) Scope is still right; I just need to change the design.**
>   → Record the new design choice as an ADR via `/grill-with-docs`.
>   → Phase moves back to `design`.
>   → Continue with the same issue.
>
>   **(b) The scope was wrong; this slice should be a different (or differently-shaped) piece of work.**
>   → File a new "design spike" issue capturing what we learned.
>   → Choose one for the original issue:
>      (b1) Reshape it (rewrite description + acceptance criteria), keep open, work on it next.
>      (b2) Close it (with a comment pointing at the spike).
>   → Phase moves back to `design` for whichever issue we continue on.

Do not let the user defer or pick "both open, figure out later". That's silent state drift.

## Execute the decision

### Path (a):

- Run `/grill-with-docs` to capture the new design as an ADR.
- Set `current-work.json` `phase` back to `design`.

### Path (b):

- File the spike issue with `to-issues` flow. Body: include what we learned about why the original was wrong-shaped.
- For (b1): rewrite the original issue body to match the new understanding. Keep `current-work.json` pointing at the original.
- For (b2): close the original with comment `Closed via /work-rethink — see #<spike-id> for the new direction.`. Update `current-work.json` to point at the spike (which becomes the active slice).
- Set phase back to `design`.

## Add a trail comment on the original issue

Always — regardless of path:

```
/work-rethink triggered at <commit-sha>.
Decision: <a / b1 / b2>.
<Optional: link to new ADR or spike issue>
```

## Log

Append to `.claude/events.jsonl`:
```json
{"ts": "<ISO>", "event": "work_rethink", "issue_id": "<orig-id>", "decision": "<a/b1/b2>", "spike_id": "<id-or-null>"}
```

This event is one of the most useful telemetry signals — frequent rethinks in one project = we're filing slices wrong.

## Final output

- What was decided
- Active issue (original or spike)
- Phase: `design`
- Suggested next: continue the design conversation; `/work-design-done` when ready.

## Don'ts

- Do not allow a fourth choice ("leave it open, decide later"). Force a decision.
- Do not lose the WIP — always commit it before moving on.
- Do not skip the trail comment on the original issue.
