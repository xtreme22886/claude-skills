---
name: refresh-notion-dashboard
description: Force a refresh of the cross-project Notion dashboard page. Normally a nightly cron job (set up by /dev-team-setup via the cron skill) updates this page automatically. Use this when the user wants the dashboard to reflect current state right now — e.g. for a meeting, a stakeholder check-in, or just to see across all their projects in Notion without waiting until tomorrow.
---

# /refresh-notion-dashboard

You're the manual override for the nightly Notion dashboard publisher.

## What this dashboard is

A single Notion page (under the org-wide Engineering Docs database) titled "Dev dashboard — <username>". Read-only; auto-overwritten on each refresh. Contains roughly the same content as `/dashboard` but in Notion form so non-developers (or the user themselves when away from Claude Code) can see it.

## Prechecks

1. Read user config — Notion token + database ID required.
2. Confirm the user has at least one project under their `default_project_root`. If none, exit with "no projects to dashboard yet".

## Run the dashboard publisher

Invoke `python3 ~/.claude/skills/dev-team/adapter/notion_publish.py --dashboard`:

The publisher:

- Walks projects under `default_project_root`, gathering the same data as `/dashboard`.
- Constructs a Notion page body with sections: Active, Paused, Open MRs/PRs, Recent flakes, Last 7 days of work_done events.
- Upserts the dashboard page in the Engineering Docs database (uses a stable `page_id` recorded in user config so we always update the same page, never create duplicates).
- Sets `Status = Active`, `Last Reviewed = now`.

## Final output

- Link to the published Notion page
- Time taken
- A reminder: this page is read-only; edits in Notion are wiped on next refresh.

## Don'ts

- Do not write any non-dashboard data into the page — keep it focused.
- Do not create a new dashboard page each run — always upsert the same one.
- Do not include closed/done slices older than ~14 days. Dashboard is for current state, not history.
