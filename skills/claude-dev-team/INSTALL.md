# Installing claude-dev-team

This document covers installing the bundle on a Linux machine (WSL2 or VM). Native Windows is not supported.

## Prerequisites

- Linux (WSL2 with Ubuntu/Debian, or a Linux VM). Project files live inside the Linux filesystem (`~/...`), never on a Windows mount (`/mnt/c/...`).
- `git`, `bash`, `python3` (≥3.10), `python3-venv`, `curl`
  - On Debian/Ubuntu: `sudo apt install python3 python3-venv git curl`
  - `python3-venv` is required so `install.sh` can build the bundle's private venv. You do **not** need system `pip`; the venv brings its own.
- `gh` (GitHub CLI) — `sudo apt install gh` or per https://cli.github.com/
- `glab` (GitLab CLI) — `sudo apt install glab` or per https://gitlab.com/gitlab-org/cli
- Claude Code installed and working

## Install

```bash
# clone (or copy) the bundle to a stable location
cd ~/dev   # or wherever you keep tools
git clone https://gitlab.your-internal-host/your-namespace/claude-dev-team.git
cd claude-dev-team

# run the installer — it handles the venv and adapter deps for you
./install.sh
```

`install.sh` performs:

1. Creates `~/.claude/skills/dev-team/` if missing.
2. Creates a private Python venv at `<bundle>/.venv/` and installs `adapter/requirements.txt` into it. This is how the bundle satisfies PEP 668 on modern Debian/Ubuntu without `--break-system-packages` — adapters never touch the system Python's site-packages.
3. Writes `~/.claude/skills/dev-team/dt-python`, a tiny wrapper that execs the venv's Python. Hooks and slash commands call this when they need a dependency from `requirements.txt`.
4. Symlinks `SKILL.md` → `~/.claude/skills/dev-team/SKILL.md`.
5. Symlinks `adapter/` → `~/.claude/skills/dev-team/adapter/` so the adapter scripts are reachable via a stable path no matter where the bundle is cloned.
6. Symlinks each `commands/*.md` → `~/.claude/commands/<name>.md`.
7. Symlinks `hooks/statusline.sh` → `~/.claude/statusline.sh` (and ensures executable bit).
8. Adds (idempotently) the relevant entries to `~/.claude/settings.json`:
   - `SessionStart` → `hooks/session-start.sh` (skill update + stale slice nudge)
   - `PreToolUse` → `hooks/phase-warn.sh` (advisory phase enforcement)
   - `statusLine.command` → `~/.claude/statusline.sh`
9. Drops a marker file at `~/.claude/.dev-team-installed` recording the install path and version.

The installer is idempotent. Re-running it is safe.

## Per-project install of the pre-push hook

The pre-push hook lives in each project's `.git/hooks/pre-push`. It is **not** installed globally. `/dev-team-init` and `/dev-team-adopt` install it as part of project bootstrap.

To install it manually in an existing project:

```bash
cd /path/to/your/project
ln -s ~/dev/claude-dev-team/hooks/pre-push.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Per-machine setup

After `install.sh`, you must run the setup wizard inside Claude Code:

```
/dev-team-setup
```

This walks you through:

- Tokens (GitLab PAT, GitHub PAT, Notion integration token)
- Default tracker host (e.g. `gitlab.your-internal-host`)
- Default Notion database ID (for the org-wide "Engineering Docs" DB)
- Per-machine paths (project root, etc.)

Tokens are validated by making a test API call against each service before being written to `~/.config/claude-dev-team/config.toml` (`chmod 600`).

## Updating

```
/dev-team-update
```

This pulls the latest from the bundle's git repo and re-runs `install.sh`. The session-start hook will notify you when updates are available; you decide when to apply them.

## Uninstalling

```bash
cd ~/dev/claude-dev-team
./uninstall.sh
```

`uninstall.sh` removes the symlinks and the settings.json entries, but leaves your `~/.config/claude-dev-team/config.toml` and per-project `.claude/` directories intact.

## Troubleshooting

**`/dev-team-setup` fails with "GitLab unreachable"** — confirm VPN is connected, then retry. Setup refuses to write a token it can't validate.

**Slash commands don't appear after install** — restart Claude Code so it re-scans `~/.claude/commands/`.

**Status line doesn't update** — confirm `~/.claude/statusline.sh` is executable (`chmod +x`) and that `~/.claude/settings.json` has `statusLine.command` pointing at it.

**`install.sh` fails with "python3 -m venv is unavailable"** — install the venv module: `sudo apt install python3-venv`. Some minimal Ubuntu/Debian images don't ship it by default.

**`install.sh` fails inside the pip step** — confirm you can reach PyPI from this machine (or whichever index you've configured). Behind a corporate proxy, set `PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` before running `install.sh`.

**`error: externally-managed-environment` (PEP 668)** — this should not happen with the current installer; it only appears if you (or an older version of these instructions) ran `pip install --user` against the system Python. The bundle's private venv at `<bundle>/.venv/` is the supported install path. Re-run `./install.sh` and that will be set up correctly.
