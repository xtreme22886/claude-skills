---
name: work-start
description: Begin work on a slice. Resolves the argument to a tracker issue (creating one via to-issues if needed), checks out a branch, writes .claude/current-work.json with phase=design. Warns if the issue looks too big or horizontal (advisory, not blocking). Use when the user is starting a new piece of work.
---

# /work-start

You're the slice-kickoff command. Make starting work cheap and consistent so it gets done every time.

## Argument

- An issue ref (`#123`, `gl#123`, full URL) → use that issue.
- Free text ("add a hello-world endpoint") → file a new issue via the `to-issues` skill flow first, then use it.

## Prechecks

1. Read `.claude/project.json`. If missing, tell user to `/dev-team-init` or `/dev-team-adopt` first.
2. Read `.claude/current-work.json`. If present and `phase != done`, warn: "Slice <issue-id> is still active in <phase>. Pause it first with `/work-pause` or finish with `/work-done`."
3. Read user config. Confirm the project's tracker is reachable (call `adapter/tracker.py preflight`).

## Resolving the issue

If user passed an issue ref:
- Fetch issue details via the tracker adapter.
- Check labels — if labeled `epic`, refuse: "This is an epic. List its sub-issues with `/work-status epic <id>` and pick one."
- Check size signals: estimated hours, attached labels (`size/L`, `size/XL`), description length. If the issue smells too big (more than `slice.ceiling_hours` from defaults.toml), warn but allow.

If user passed free text:
- Run the `to-issues` skill flow to file a properly-shaped vertical slice. Confirm with user before creation.

## Slice-shape advisory check

Run `adapter/slice_check.py --issue <id>` (it reads the issue body looking for layered vs vertical hints). If it flags the issue as horizontal-shaped, surface the warning to the user. Do not block.

## Branch creation

- Branch name: `slice/<issue-id>-<slugified-title>`. Truncate slug to ~40 chars.
- `git checkout -b <branch>` from the default branch (default branch fetched from tracker, fallback `main`).
- If the branch already exists locally (resuming after pause/rethink), check it out instead.

## Write current-work.json

From `templates/current-work.json.tmpl`, fill in:
- `issue_id`, `issue_url`, `issue_title`
- `branch`
- `phase: "design"`
- `started_at`, `last_phase_change_at`

## Move issue on the tracker board

Move the issue to the "In Progress" or "Design" column (per project's board config). Add a comment: `Started locally on branch <branch>.`

## Log the event

Append to `.claude/events.jsonl`:
```json
{"ts": "<ISO>", "event": "work_start", "issue_id": "<id>", "branch": "<branch>"}
```

## Final output

Print:
- Issue URL + title
- Branch name
- Phase: `design`
- Suggested next: brainstorm the design, write down the approach (or a decision sketch). When ready to code, run `/work-design-done`.

## Don'ts

- Do not start coding immediately. Phase is `design` for a reason.
- Do not file an issue without confirming with the user.
- Do not skip the slice-shape check, even though it's advisory.
