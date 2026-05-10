---
name: dev-team-promote
description: Upgrade a project that was created with /dev-team-init --minimal to the full kickoff (CI, docs structure, Notion registration, ADR #1). Use when the user originally bootstrapped a throwaway prototype and now wants the full discipline because the project has graduated past prototype.
---

# /dev-team-promote

You're the promotion path from minimal to full. The project was bootstrapped with `--minimal`; the user now wants the rest.

## Prechecks

1. Read `.claude/project.json`. Confirm `minimal: true`. If not, tell the user the project is already full and stop.
2. Confirm git is in a clean state (no uncommitted changes). If dirty, ask the user to commit or stash first.

## What you add

Run only the steps from `/dev-team-init` that were skipped under `--minimal`:

1. **Doc directories** — create the full `docs/...` structure with `.gitkeep` files.
2. **ADR #1** — create `docs/adr/0001-promotion-from-minimal.md` recording the original stack choices and the date of promotion.
3. **CI** — drop in the appropriate CI template (GitLab or GitHub).
4. **Notion registration** — add a row in the org-wide Engineering Docs DB.
5. **Update `project.json`** — set `minimal: false`.

## Commit and summary

- One commit: `promote project to full dev-team kickoff`.
- Print what was added.
- Suggest `/work-start` for the next slice; warn that any code already shipped without doc updates should get a retrospective `/work-docs` pass.

## Don'ts

- Do not push automatically.
- Do not retroactively try to file issues for past work — that's manual and lossy. Just go forward.
