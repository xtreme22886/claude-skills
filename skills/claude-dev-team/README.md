# claude-dev-team

A Claude Code skill bundle that turns the main session into a disciplined software development team. One main Claude (the team lead) plus a small palette of subagents, slash commands, hooks, and templates that enforce vertical-slice development with first-class issue tracking and documentation.

## What's in the box

- **19 slash commands** for project bootstrap, slice lifecycle, and visibility
- **5 hooks** (preflight, phase-warn, pre-push, session-start, statusline)
- **2 CI templates** (GitLab CI + GitHub Actions) — opinionated lint/test/docs-publish pipelines
- **Adapter scripts** for tracker dispatch (`gh` / `glab`) and Notion publishing
- **Templates** for project config, ADRs, doc types, and per-project `CLAUDE.md`

## Status

**Scaffold only.** Built locally on a personal machine with no network access to the target tracker. Not yet installed, not yet tested. See `TRANSFER.md` for moving this scaffold to your work machine and `INSTALL.md` for installing once it's there.

## Design

- `SKILL.md` — meta-skill manifest and short design summary.
- `DESIGN.md` — full ADR-style decision record. **Read this before making any structural change to the bundle.** Each decision lists the alternatives considered and the reasoning.
- `docs/design-conversation.md` (if present) — the original grilling conversation that produced the design.

The full grilled-out design conversation that produced this bundle covered:

- Why one-Claude-with-skills beats multi-agent orchestration in Claude Code
- Dual-tracker support (GitHub + GitLab), auto-detected per project
- Vertical slices, one-sitting sizing, epic/sub-issue escape hatch
- Per-slice docs, in-repo source, Notion mirror for IT Ops
- Failure modes: CI flakes, mid-slice rethink, context-switch resume
- Visibility: status line + `/dashboard` + nightly Notion dashboard
- Linux-only dev environment (WSL2 or VM)

## Layout

```
claude-dev-team/
├── SKILL.md                     # meta-skill, when invoked gives an overview
├── README.md
├── INSTALL.md                   # how to install on a new (work) machine
├── TRANSFER.md                  # how to move this scaffold off the personal machine
├── CHANGELOG.md
├── install.sh                   # symlinks files into ~/.claude/
├── uninstall.sh
├── commands/                    # slash commands as individual skill files
├── hooks/                       # bash hooks + CI templates
├── adapter/                     # Python: tracker dispatch, Notion publish, verify-fast
├── templates/                   # project bootstrap templates
└── config/
    └── defaults.toml            # bundle defaults
```

## Requirements (will need installing on the work machine)

- Linux (WSL2 or VM); not supported on native Windows
- `git`, `bash`, `python3` (≥3.10), `python3-venv` (the bundle creates its own private venv at install time — see `INSTALL.md`)
- `gh` (GitHub CLI) and `glab` (GitLab CLI)
- A Notion integration token + access to the org-wide "Engineering Docs" database
- A GitLab PAT (`api`, `read_repository`, `write_repository`)
- A GitHub PAT (`repo`, `workflow`)
