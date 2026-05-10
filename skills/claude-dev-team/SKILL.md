---
name: dev-team
description: A reusable Claude Code bundle that turns the main session into a disciplined software-development team. Provides slash commands, hooks, and conventions for vertical-slice development with issue tracking (GitHub or GitLab), per-slice docs, and Notion publishing for IT Ops. Use when starting a new project that needs structured development discipline, or when the user asks about "dev-team", "/work-start", "/dev-team-init", or any of the bundle's slash commands.
---

# dev-team — software development team in skill form

This is not a single workflow — it's a small set of conventions wired into Claude Code so that every project follows the same discipline:

1. **One main Claude session = the team lead.** No multi-agent orchestration; subagents are used surgically (review, exploration, second opinion) only when they add real value.
2. **Vertical slices, one sitting each.** Every issue cuts through the whole stack end-to-end. Larger work is decomposed into linked sub-issues under an `epic` label.
3. **The issue tracker is the shared brain.** GitHub Issues for GitHub projects, GitLab Issues for GitLab projects. Auto-detected from `git remote`.
4. **Per-slice docs are mandatory.** User-guide, troubleshooting, and ADR updates land in the same MR/PR as the code. The `docs/ops/` subtree publishes to a shared Notion database for IT Ops.
5. **Phase-tracked work, advisory enforcement.** `/work-start` → `/work-design-done` → `/work-review` → `/work-done`. Out-of-phase actions trigger warnings, not blocks.

## When to invoke this skill

Invoke directly when the user asks "what is dev-team", "how does this skill work", or anything about the overall design. For specific actions, defer to the appropriate slash command:

| User intent | Command |
|---|---|
| Set up bundle on a new machine | `/dev-team-setup` |
| Start a new project from scratch | `/dev-team-init` |
| Adopt the bundle on an existing project | `/dev-team-adopt` |
| Pull skill updates | `/dev-team-update` |
| Begin a slice | `/work-start <issue or description>` |
| Move slice from design → implement | `/work-design-done` |
| Push, open MR/PR, run review | `/work-review` |
| Close out a slice | `/work-done` |
| Pause / resume slice across sessions | `/work-pause`, `/work-resume <id>` |
| Slice scope was wrong | `/work-rethink` |
| Glanceable status | `/work-status`, `/dashboard` |
| Mid-slice doc stub | `/work-docs` |
| Manual Notion publish | `/publish-ops-docs` |
| Force Notion dashboard refresh | `/refresh-notion-dashboard` |
| Local metrics | `/team-stats` |
| Independent sanity check | `/second-opinion <question>` |

## Subagent palette (use sparingly)

- `reviewer` — cold review of a diff with no conversation context. Already covered by built-in `/review` and `/security-review`.
- `explorer` — read-heavy research across the repo. Use the built-in `Explore` agent type.
- `second-opinion` — manual sanity check via `/second-opinion`.

Do not spawn subagents for "ongoing roles" (tester, debugger, coder). Those are skills running in the main thread.

## State that lives where

- **Skill bundle** — internal GitLab repo, cloned to `~/.claude/skills/dev-team/`.
- **Per-user config** — `~/.config/claude-dev-team/config.toml` (plaintext, `chmod 600`).
- **Per-project state** — `.claude/` inside each project repo. `project.json` is committed; `current-work.json`, `paused/`, `events.jsonl`, `flakes.jsonl` are gitignored.

## Key principles to enforce

- **Network presence is required for GitLab projects.** No outbox, no offline mode. `preflight.sh` refuses to start if the tracker is unreachable.
- **Notion is a mirror, never a source.** Repo is the source of truth for `docs/ops/`; Notion is auto-published.
- **CI flakes retry once, then fail loud.** Logged to `.claude/flakes.jsonl` for pattern-spotting.
- **Advisory enforcement, not strict.** Warn on out-of-phase actions, missing docs, unusual slice shapes — never block.
- **Skill updates are notification-driven, not silent.** SessionStart hook checks for updates; `/dev-team-update` applies them.
