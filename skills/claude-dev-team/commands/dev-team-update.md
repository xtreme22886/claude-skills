---
name: dev-team-update
description: Pull the latest version of the claude-dev-team bundle from internal GitLab and re-run the install script. Use when the SessionStart hook has notified the user of available updates, or when the user explicitly asks to update the bundle.
---

# /dev-team-update

You're the bundle update command. Pulls latest, re-installs, surfaces the changelog.

## Steps

1. Read `~/.claude/.dev-team-installed` to find `bundle_dir`.
2. `cd "$bundle_dir"`
3. Check git status — if there are local uncommitted changes, ask the user before pulling (they may be testing local edits).
4. `git fetch origin`
5. Show the user the commits between `HEAD` and `origin/main` (`git log --oneline HEAD..origin/main`). Surface the changelog diff (`git diff HEAD..origin/main -- CHANGELOG.md`) so they can see what's new.
6. Ask: "Apply update?"
7. On yes: `git pull --ff-only`. If fast-forward fails (local commits), ask user to handle manually and stop.
8. Re-run `./install.sh` to refresh symlinks and settings.json entries (idempotent).
9. Print the new version (from `CHANGELOG.md`) and a one-line summary of changes.

## Don'ts

- Do not pull silently. Always show what's new and confirm.
- Do not modify any project's `.claude/` directory — bundle updates only touch `~/.claude/`.
- Do not skip the install.sh re-run. New commands or hook changes won't take effect otherwise.
