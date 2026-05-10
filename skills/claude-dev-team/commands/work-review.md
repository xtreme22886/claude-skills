---
name: work-review
description: Push the slice branch, open an MR (GitLab) or PR (GitHub), spawn a cold reviewer subagent on the diff, and fetch CI status. Detects missing per-slice docs and ops-doc deltas (advisory). Updates phase to review. Use when the user has finished implementing and is ready for review.
---

# /work-review

You're the push-and-review command. Heavy lifter — gets the slice in front of CI and a cold reviewer in one motion.

## Prechecks

1. Read `.claude/current-work.json`. Refuse if missing or `phase` not in `{design, implement}` (review/done = no-op or warn).
2. Confirm working tree is clean or has only relevant changes. If unrelated changes are staged, ask the user.
3. Run `adapter/verify_fast.py` first. If it fails, surface the failure and stop — don't push broken code. User can override with explicit confirmation.

## Slice-completeness check (advisory)

Before pushing, run the per-slice doc audit:

- If the diff touches user-visible behavior (UI files, API handlers, CLI flags) and there's no change under `docs/user-guide/`, warn.
- If the diff introduces new error paths, error messages, or failure modes and there's no change under `docs/troubleshooting/` or `docs/ops/troubleshooting/`, warn.
- If the diff introduces or changes setup/config (Dockerfile, env vars, deploy scripts, schema migrations) and there's no change under `docs/ops/setup/` or `docs/ops/requirements/`, warn.

For each warning, offer to run `/work-docs` now. Don't block.

## Push

```bash
git push -u origin <branch>
```

If push fails (rejected, ahead/behind), investigate before retrying.

## Open MR / PR

Via the tracker adapter. Title = issue title. Body = template:

```
Closes #<issue-id>

## What this slice does

<one paragraph from the issue body>

## How to review

- Start with: <suggest a file/function based on diff>
- Look for: <surface the slice-completeness warnings if any were ignored>

## Docs touched

<list of changed docs/ files>

🤖 Slice opened by claude-dev-team
```

## Update current-work.json

- `phase: "review"`
- `merge_request_url`: the new MR/PR URL
- `last_phase_change_at: <ISO>`

## Spawn cold reviewer subagent

Invoke a subagent (use `Agent` tool with subagent_type matching the project's available reviewer agent — typically the built-in `code-reviewer` or invoke the `/review` skill):
- Hand it ONLY the diff and the issue body.
- Do NOT pass conversation context. The whole point is independent eyes.
- Return its findings to the main session as comments to add to the MR/PR.

## Fetch CI status

After ~30s, fetch the CI pipeline status via the tracker adapter. If still running, surface a `pending` status; if failed, route to the CI flake / real-failure flow.

### CI flake handling

Read `config/defaults.toml` `ci.flake_retry_budget` (default 1). If the failure looks like a flake (timeout, runner exited, network error in logs), retry once. If it passes the second time, log to `.claude/flakes.jsonl`:

```json
{"ts": "<ISO>", "issue_id": "<id>", "pipeline_url": "<url>", "failure_excerpt": "<first 500 chars of failure>"}
```

If it fails again (or doesn't look like a flake), seed the `diagnose` skill with the parsed failure and let the user iterate.

## Log

Append to `.claude/events.jsonl`:
```json
{"ts": "<ISO>", "event": "phase_transition", "issue_id": "<id>", "from": "<prev>", "to": "review"}
{"ts": "<ISO>", "event": "review_opened", "issue_id": "<id>", "mr_url": "<url>"}
```

## Final output

- MR/PR URL
- CI status (or "pending, will check back")
- Summary of reviewer findings
- Slice-completeness warnings, if any
- Suggested next: address review/CI feedback, then `/work-done` when green.

## Don'ts

- Do not merge anything. The user merges, not the bot.
- Do not skip the cold reviewer just because verify-fast passed.
- Do not retry CI more than once even if it keeps flaking — surface the pattern instead.
