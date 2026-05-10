---
name: publish-ops-docs
description: Manually trigger the Notion publish for the current project's docs/ops/ subtree. Normally CI handles this on merge to main; use this command for ad-hoc republish (e.g. fixed a typo, want it on Notion right now without waiting for a merge). Use when the user wants to publish ops docs to Notion outside the normal CI flow.
---

# /publish-ops-docs

You're the manual Notion publish command. Normally CI handles this; this is for "I just edited a typo, push it now" cases.

## Prechecks

1. Read `.claude/project.json`. Confirm `docs.publish_to_notion == true`.
2. Read `~/.config/claude-dev-team/config.toml` — confirm Notion token + database ID present.
3. Confirm `docs/ops/` exists in the current project.

## Run the publisher

Invoke `python3 ~/.claude/skills/dev-team/adapter/notion_publish.py`:

```bash
NOTION_TOKEN=<from user config> \
python3 ~/.claude/skills/dev-team/adapter/notion_publish.py \
  --project "<from .claude/project.json>" \
  --docs-root docs/ops \
  --database-id "<from user config>"
```

The publisher:

- Walks `docs/ops/{setup,troubleshooting,requirements}/`.
- For each markdown file, reads frontmatter (`notion_type`, `component`, `audience`, `last_reviewed`).
- Skips files without frontmatter (warns the user).
- Upserts a Notion page in the database with:
  - `Project` = project name from `project.json`
  - `Type`, `Component`, `Last Reviewed` from frontmatter
  - `Status` = Active
  - `Source File` = URL back to repo (constructed from project's tracker config)
- Converts markdown body to Notion blocks.
- Detects deletions (Notion pages whose source file no longer exists) — adds a deprecated banner and archives those pages.

## Final output

- Number of pages upserted
- Number of pages archived (deleted upstream)
- Any files skipped due to missing frontmatter
- Link to the Notion view, filtered by `Project = <name>`.

## Don'ts

- Do not publish if Notion validation fails — fix the file and try again, don't push half-broken pages.
- Do not edit files in Notion to "fix things" — repo is the source of truth.
- Do not remove the publisher's archived-page banners; they're how readers know a page is dead.
