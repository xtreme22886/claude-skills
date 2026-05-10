---
name: dev-team-init
description: Bootstrap a brand-new project from an empty directory. Interactive wizard that creates the remote repo (GitHub or GitLab), scaffolds the project skeleton (CLAUDE.md, docs/, .claude/, ADR #1), drops in CI templates, registers the project in the org-wide Notion database, and installs the pre-push hook. Supports a --minimal flag for throwaway prototypes. Use when the user is starting a new project from scratch.
---

# /dev-team-init

You're the new-project wizard. Walk the user through bootstrapping a fresh project end-to-end so they can immediately start working with `/work-start`.

## Arguments

- No args → full bootstrap.
- `--minimal` → skip CI, skip Notion registration, skip docs/ structure. Just `.claude/project.json`, `CLAUDE.md`, basic `.gitignore`. Promotes to full kickoff later via `/dev-team-promote`.

## Prechecks

1. Ensure `~/.config/claude-dev-team/config.toml` exists. If not, tell user to run `/dev-team-setup` first.
2. Ensure current directory is empty (no files except possibly `.git/` or similar harmless ones). If not empty and not adopting, ask whether they meant `/dev-team-adopt` instead.

## Resumability

If a previous run failed partway, detect by reading `.claude/init-progress.json` (a tiny state file you write after each step). Resume from where it left off. Each step is idempotent.

## The full wizard, in order

### 1. Project basics

- Project name (default: directory name)
- One-line description
- Stack: detect from any existing files, otherwise show the blessed-stack menu (Python+pytest, TypeScript+vitest, Go+go test, Rust+cargo, "other"). For "other", ask for lint/typecheck/test commands.

### 2. Tracker selection

Sniff `git remote get-url origin` if the dir is already a git repo. Otherwise ask: "GitHub or GitLab?"

For GitLab, use the host from the user config. For GitHub, use `github.com`.

### 3. Remote repo creation

Ask: "Create new remote repo, or hook up to an existing one?"

- **New:** run `gh repo create <name> --private` or `glab repo create <name> --private` (per tracker).
- **Existing:** ask for the URL, validate it's reachable.

In both cases, set as `origin`.

### 4. Skeleton files

Render templates from `~/.claude/skills/dev-team/templates/` to the project:

- `.gitignore` — base + stack-specific concatenated
- `README.md` — stub with name, description, "How to develop on this project" pointing at the dev-team conventions
- `CLAUDE.md` — from `claude.md.tmpl`, filled in with project specifics
- `docs/adr/0001-initial-stack-decision.md` — ADR recording the stack choices the user just made
- `docs/user-guide/.gitkeep`
- `docs/troubleshooting/.gitkeep`
- `docs/training/.gitkeep`
- `docs/ops/setup/.gitkeep`
- `docs/ops/troubleshooting/.gitkeep`
- `docs/ops/requirements/.gitkeep`
- `.claude/project.json` — from `project.json.tmpl`
- `.claude/.gitignore` — gitignores `current-work.json`, `paused/`, `events.jsonl`, `flakes.jsonl`

For `--minimal`, skip everything under `docs/` and skip the ADR.

### 5. CI

Drop in the CI template per tracker:
- GitLab → `.gitlab-ci.yml` from `gitlab-ci.yml.tmpl`
- GitHub → `.github/workflows/main.yml` from `github-actions-main.yml.tmpl`

Substitute lint/typecheck/test commands from the stack choice.

For GitHub, also copy `adapter/notion_publish.py` to `.github/scripts/notion_publish.py` (CI runs this directly; on GitLab, CI references the user's installed copy at `~/.claude/skills/dev-team/adapter/notion_publish.py`).

For `--minimal`, skip CI entirely.

### 6. Notion registration

Add a row to the org-wide Engineering Docs Notion database with:
- `Project` = project name
- `Status` = Active
- `Source File` = repo URL

No actual doc pages are published yet (none exist).

For `--minimal`, skip.

### 7. Pre-push hook

```bash
ln -s ~/.claude/skills/dev-team/hooks/pre-push.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### 8. First commit + push

- `git add .`
- `git commit -m "initial scaffold via /dev-team-init"`
- `git push -u origin main`

### 9. Final summary

Print:

- Repo URL
- What got created
- Suggested next command:
  - If scope is fuzzy: `/grill-with-docs` to refine, then `/to-prd` to write a PRD, then `/to-issues` to break into slices.
  - If scope is clear: `/work-start "your first slice"` directly.

## Failure handling

- Network blip mid-step → save progress, tell user to re-run `/dev-team-init` to resume.
- Name collision on remote → ask for a different name, retry.
- Token rejection → tell user to re-run `/dev-team-setup` to refresh the relevant token.

## Don'ts

- Do not file any issues yet. The wizard is for project bootstrap, not work tracking.
- Do not write any actual documentation content into the doc directories — the templates are touched only when slices add real content via `/work-docs`.
- Do not enable strict enforcement mode. Default is advisory per the bundle convention.
