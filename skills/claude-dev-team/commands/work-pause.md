---
name: work-pause
description: Pause an in-flight slice so you can context-switch to something else without losing state. Snapshots current-work.json into .claude/paused/, generates a "where I left off" summary from the conversation, leaves the branch and any uncommitted changes intact. Use when the user is stepping away from a slice for more than a session.
---

# /work-pause

You're the pause command. Make context-switching cheap. The "where I left off" summary is the magic — write it well so resume is trivial.

## Prechecks

1. Read `.claude/current-work.json`. Refuse if missing.
2. Check for uncommitted changes. If any, ask the user: "Stash, WIP-commit on the slice branch, or discard?" Default: WIP commit on the branch (commit message: `WIP: pause slice <issue-id>`).

## Generate the "where I left off" summary

This is the most important part. Look back over the conversation and write a short summary covering:

- **What was the goal of this slice?** (one sentence from the issue)
- **What's been done so far?** (concrete: files changed, decisions made, what's working)
- **What's the next concrete action?** (the very next thing to do — be specific)
- **What's blocking or uncertain?** (open questions, things you weren't sure about)
- **Any context that won't be obvious from the diff?** (why a non-obvious choice was made, what didn't work)

Keep it under ~250 words. The goal: the user (or future-Claude on resume) can read this and pick up without reading the diff.

## Save the snapshot

Write to `.claude/paused/<issue-id>.json`:

```json
{
  "issue_id": "...",
  "branch": "...",
  "phase": "...",
  "paused_at": "<ISO>",
  "last_commit_sha": "<sha>",
  "left_off_summary": "<the summary>",
  "current_work_snapshot": <full prior current-work.json>
}
```

## Clear current state

Delete `.claude/current-work.json` (its absence = "no active slice").

## Switch branches (optional)

Ask the user: "Switch back to main? (default: yes)". If yes, `git checkout main` (the slice branch stays — never delete on pause).

## Log

Append to `.claude/events.jsonl`:
```json
{"ts": "<ISO>", "event": "work_pause", "issue_id": "<id>", "phase_at_pause": "<phase>"}
```

## Final output

- Confirm the slice is paused
- Path to the paused snapshot
- The "left off" summary (echoed back so the user can sanity-check it)
- Suggested next: `/work-start` something else, or `/work-resume <id>` to come back later.

## Don'ts

- Do not delete the slice branch.
- Do not skip the "where I left off" summary — even if the user is just pausing for an hour. Future-you will thank you.
- Do not push the WIP commit to the remote unless the user asks.
