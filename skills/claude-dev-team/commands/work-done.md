---
name: work-done
description: Close out a slice. Confirms CI green, MR/PR merged (or asks user to merge), closes the tracker issue, clears .claude/current-work.json, switches back to default branch. Use when a slice is fully shipped and the user wants to wrap it up.
---

# /work-done

You're the slice-close command. Make sure nothing dangles.

## Prechecks

1. Read `.claude/current-work.json`. Refuse if missing or `phase != review`.
2. Confirm CI is green on the MR/PR. If not, refuse: "CI is <status>. Wait for green or use `/work-rethink` if the slice is stuck."
3. Check whether the MR/PR is merged.
   - If not yet merged: ask the user "Merge now via the tracker, or have you merged elsewhere?" Do not auto-merge — the user merges.
   - If already merged: proceed.

## Close out

1. Move the tracker issue to `Done` / closed (depending on board).
2. Add a comment on the issue: `Shipped via <merge-commit-sha>.`
3. Switch local branch back to `main` (or default branch from project config).
4. `git pull --ff-only` to get the merged state.
5. Optional: delete the local slice branch (`git branch -d <branch>`). Ask the user before deleting.
6. Clear `.claude/current-work.json` (delete the file, not just empty it — its absence means "no active slice").

## Update Notion (if relevant)

If the slice changed any `docs/ops/` files, the GitLab CI / GitHub Actions docs-publish job will already have run on the merge to main. No action needed here. Just surface a one-liner: "Notion ops docs updated by CI."

## Log

Append to `.claude/events.jsonl`:
```json
{"ts": "<ISO>", "event": "work_done", "issue_id": "<id>", "merge_sha": "<sha>", "duration_minutes": <minutes from started_at>}
```

## Final output

- Issue closed (with link)
- Branch deleted (or kept, per user choice)
- Merge SHA on `main`
- Duration of the slice (handy data — celebrate short ones, surface long ones)
- Suggested next: pick another issue with `/work-start <ref>`, or run `/dashboard` to see what's next.

## Don'ts

- Do not auto-merge. User merges.
- Do not skip the duration log — that's the data that powers `/team-stats` and slice-sizing improvements over time.
- Do not delete the branch without asking. Some users like keeping shipped branches as bookmarks.
