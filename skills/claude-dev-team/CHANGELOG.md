# Changelog

## 0.2.0 — 2026-05-11 — bundle-owned venv (PEP 668 fix)

First real-machine install surfaced PEP 668 (`externally-managed-environment`) on Ubuntu 24.04 Python 3.12. The bundle now owns its Python environment instead of asking the user to install adapter deps with `pip install --user`.

- `install.sh` creates `<bundle>/.venv/` and installs `adapter/requirements.txt` into it.
- `install.sh` generates `~/.claude/skills/dev-team/dt-python`, a wrapper that execs the venv Python. Hooks and slash commands use this for any script that imports a third-party package.
- `install.sh` symlinks `adapter/` into `~/.claude/skills/dev-team/adapter/` so slash command instructions can use a stable path regardless of where the bundle is cloned.
- `uninstall.sh` removes the new symlinks and the `dt-python` wrapper. The venv stays with the bundle dir.
- `hooks/pre-push.sh` and the Notion-related slash commands (`/publish-ops-docs`, `/refresh-notion-dashboard`) updated to invoke `dt-python` instead of system `python3`.
- `INSTALL.md` and `README.md` updated to document the new flow and the `python3-venv` prerequisite. The old `pip install --user -r adapter/requirements.txt` step is gone.
- New ADR: D20 in `DESIGN.md` records the decision and the rejected alternatives.

Stdlib-only Python snippets in `install.sh`, `uninstall.sh`, and the rest of the hooks still use system `python3` — they don't need the venv.

## 0.1.0 — 2026-05-04 — initial scaffold

Built locally on a personal machine without VPN access to internal GitLab. Not yet installed, not yet tested.

- 19 slash commands scaffolded (commands/)
- 5 hooks scaffolded (hooks/)
- Adapter scripts scaffolded with interfaces and skeleton implementations (adapter/)
- Templates for project bootstrap, ADRs, doc types, and CI configs (templates/)
- Bundle defaults (config/defaults.toml)
- Install / uninstall scripts
- Documentation: README, INSTALL, TRANSFER, SKILL.md, DESIGN.md (full ADR-style decision record covering all 19 design decisions from the original grilling)
- `docs/design-conversation.md` — exported transcript of the original grilling conversation that produced the design
