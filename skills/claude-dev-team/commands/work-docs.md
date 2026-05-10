---
name: work-docs
description: Mid-slice doc-stub generator. Looks at the current slice's diff and drops skeleton entries into docs/user-guide/, docs/troubleshooting/, and/or docs/ops/ that match what the slice introduces. Use when the user wants to draft per-slice docs without doing it from memory at end-of-slice.
---

# /work-docs

You're the per-slice doc-stub generator. The point: docs get written while context is fresh, not from memory at end-of-slice.

## Prechecks

1. Read `.claude/current-work.json`. Refuse if no active slice.
2. Confirm there are some changes on the slice branch (`git diff main...HEAD --stat`). If none, no-op with a note.

## Detect what kind of doc updates the slice needs

Read the diff. Apply these heuristics — surface results to the user, ask which to draft:

- **User-facing behavior change** → `docs/user-guide/` stub
  Triggers: changes to UI components, public API handlers, CLI flag definitions, public function signatures in libraries.

- **New error or failure mode** → `docs/troubleshooting/` stub
  Triggers: new exception types, new error message strings, new validation failures, new return-codes from CLI, new HTTP error responses.

- **Setup / config / deploy change** → `docs/ops/setup/` and/or `docs/ops/requirements/` stub
  Triggers: changes to Dockerfile, docker-compose.yml, env vars, secrets, deploy scripts, schema migrations, new external service dependencies.

- **IT-Ops-relevant new failure mode** → `docs/ops/troubleshooting/` stub
  Triggers: changes to anything an operator (not a developer) would encounter — service startup failures, network/firewall errors, license/auth errors visible at runtime.

## For each detected category

Ask the user: "Draft a stub for <category>? (y/n)"

On yes:

1. Pick the appropriate template from `~/.claude/skills/dev-team/templates/` (e.g. `ops-troubleshooting.md.tmpl` for ops/troubleshooting).
2. Pre-fill what we know from the diff:
   - Title (slugify the slice's issue title or generate from the change)
   - `component` frontmatter (best guess from the diff path — e.g. `auth-service` if changes are in `services/auth/`)
   - `last_reviewed` = today's date
3. For ops templates, fill in the `## Requirements` section header but leave content blank for the user.
4. Write the stub to the right path (`docs/user-guide/<slug>.md`, `docs/ops/troubleshooting/<slug>.md`, etc.) — don't overwrite if a file at that path already exists.
5. Open it for the user to fill in (or just print the path).

## Final output

- List of files created (with paths).
- Reminder: the doc-publish CI job auto-publishes `docs/ops/` to Notion on merge to main. The other doc directories stay in-repo only.
- Suggested next: fill in the stubs, then `/work-review` when ready.

## Don'ts

- Do not write fake content into the stubs — only the structure and what we know from the diff. The user fills in the human parts.
- Do not skip frontmatter on `docs/ops/` files — CI will fail without it.
- Do not overwrite existing doc files. Add a numeric suffix or skip with a note.
