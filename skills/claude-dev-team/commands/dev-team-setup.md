---
name: dev-team-setup
description: One-time per-machine setup for the claude-dev-team bundle. Walks the user through entering their GitLab PAT, GitHub PAT, and Notion integration token, validates each by making a live API call, then writes them to ~/.config/claude-dev-team/config.toml with chmod 600. Use when the user is on a new machine, has just installed the bundle, or asks "how do I set up dev-team".
---

# /dev-team-setup

You're the per-machine setup wizard for the claude-dev-team bundle. This is a one-time-per-machine command. It walks the user through providing tokens and config, validates each token, and writes them to disk.

## Prechecks

1. Confirm you're on Linux (WSL2 or VM). If `uname` returns something other than Linux, refuse with: "claude-dev-team is Linux-only. Run this inside WSL2 or a Linux VM, not native Windows."
2. Check that `gh`, `glab`, `python3`, and `git` are on PATH. For each one missing, tell the user the install command for their distro and stop.
3. Check whether `~/.config/claude-dev-team/config.toml` already exists. If yes, ask: "Existing config found. Reconfigure (overwrites tokens), update only specific fields, or cancel?"

## Walk through these prompts in order

For each prompt, echo a short explanation, then ask the user to paste the value. Do not proceed past a value until it validates.

1. **GitLab host** — e.g. `gitlab.your-internal-host`. Skip if the user has no GitLab projects.
2. **GitLab PAT** — required scopes: `api`, `read_repository`, `write_repository`. Validate by running `glab api /user --hostname <host>`. On 401, tell the user the token is rejected and ask again. On network failure, tell them VPN may be required and stop.
3. **GitHub PAT** — required scopes: `repo`, `workflow`. Validate by running `gh api /user`. Skip if the user says they have no GitHub projects.
4. **Notion integration token** — validate by `curl -sf -H "Authorization: Bearer $TOKEN" -H "Notion-Version: 2022-06-28" https://api.notion.com/v1/users/me`. Reject and re-ask on failure.
5. **Notion "Engineering Docs" database ID** — ask the user to paste the database URL and extract the ID (the 32-char hex segment). Validate by querying the database with the token. Reject if the integration doesn't have access.
6. **Default project root** — where they put repos on this machine, e.g. `~/dev`. Used by `/dev-team-init` as the default location for new projects. Default to `~/dev`.

## Writing the config

Write to `~/.config/claude-dev-team/config.toml`:

```toml
[user]
default_project_root = "~/dev"

[trackers.gitlab]
host = "gitlab.your-internal-host"
token = "..."

[trackers.github]
token = "..."

[notion]
token = "..."
database_id = "..."

[meta]
configured_at = "<ISO-8601 timestamp>"
bundle_version = "<from CHANGELOG>"
```

After writing, run `chmod 600` on the file.

## Final output

Print:
- Where the config was written.
- A reminder that this file contains plaintext tokens — the user is responsible for not committing it to git, not syncing it via cloud storage, etc.
- The next suggested action: `cd` into a project directory and run `/dev-team-init` or `/dev-team-adopt`.

## Don'ts

- Do not log token values.
- Do not run any tracker write operations during setup. Read-only validation only.
- Do not modify `~/.claude/settings.json` — that's the install script's job.
- Do not store tokens anywhere other than `~/.config/claude-dev-team/config.toml`.
