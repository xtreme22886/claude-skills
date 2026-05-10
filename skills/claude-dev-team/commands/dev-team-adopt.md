---
name: dev-team-adopt
description: Adopt the claude-dev-team bundle on an existing project that already has code, history, and possibly its own conventions. Migration mode — same intent as /dev-team-init but skips remote creation and prompts before overwriting any existing files. Use when the user has an existing project they want to bring under the dev-team conventions.
---

# /dev-team-adopt

You're the migration wizard for an existing project. Bring it under the dev-team conventions without trampling what's already there.

## Prechecks

1. Ensure `~/.config/claude-dev-team/config.toml` exists (else send to `/dev-team-setup`).
2. Confirm the current dir is a git repo with at least one commit.
3. Confirm `origin` is set and points at GitHub or a configured GitLab host.

## What you do, with confirmations along the way

For each item below, check whether it already exists. If it doesn't, add it. If it does, ask the user before overwriting (show a diff if helpful).

### 1. `.claude/project.json`

Almost certainly missing. Create it via the `project.json.tmpl`. Sniff lint/typecheck/test commands from existing config files (package.json scripts, pyproject.toml, Makefile, etc.) and ask the user to confirm.

### 2. `CLAUDE.md`

If it exists: ask whether to merge dev-team conventions into it (preferred) or leave alone (then dev-team conventions live only in `.claude/project.json`).

If it doesn't: create from `claude.md.tmpl`.

### 3. Doc directories

Create any missing `docs/{user-guide,troubleshooting,training,adr,ops/{setup,troubleshooting,requirements}}/` with `.gitkeep` files. Do not modify existing doc files.

### 4. ADR backlog

If `docs/adr/` is empty, create `0001-adopting-dev-team.md` recording that this project just adopted the bundle and what the existing stack is. If ADRs already exist, skip.

### 5. CI

If a CI config (`.gitlab-ci.yml` or `.github/workflows/`) already exists: ask whether to leave alone, append a `docs-publish` job for Notion, or replace with the bundle's template (with diff).

If none exists: drop in the appropriate template like `/dev-team-init` would.

### 6. Pre-push hook

If `.git/hooks/pre-push` exists: ask. Either skip, append our verify-fast call, or replace.

If absent: install the symlink as in `/dev-team-init`.

### 7. Notion registration

Add a row in the org-wide Notion DB if not already present. Use project name from `.claude/project.json` to dedup.

### 8. `.gitignore` additions

Append to existing `.gitignore` (without dups):
- `.claude/current-work.json`
- `.claude/paused/`
- `.claude/events.jsonl`
- `.claude/flakes.jsonl`

### 9. Commit

Create a commit titled `adopt claude-dev-team conventions`. Do not push automatically — let the user review and push themselves.

## Final summary

Print what was added vs left alone, the new commit hash, and the suggested next command (`/work-status` to see initial state, or `/work-start` to begin a slice).

## Don'ts

- Do not delete or rewrite any existing project file without confirming.
- Do not push anything.
- Do not enable strict enforcement on adoption — too disruptive. Stay advisory.
