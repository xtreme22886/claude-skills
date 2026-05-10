# Transferring this scaffold to the work machine

This scaffold was built on a personal machine without VPN access to the internal GitLab. To turn it into a real, installed bundle, move it to a work machine that has VPN access and follow these steps in order.

## Step 1 — Get the scaffold onto the work machine

Pick whichever method works for your environment:

**Option A: tarball + transfer**
```bash
# on the personal machine
cd /home/xtreme
tar czf claude-dev-team.tar.gz claude-dev-team/
# transfer claude-dev-team.tar.gz to the work machine via your usual method
# (USB drive, internal file share, etc.)

# on the work machine
mkdir -p ~/dev
cd ~/dev
tar xzf /path/to/claude-dev-team.tar.gz
```

**Option B: scp / rsync** (if the personal and work machines can reach each other on the network)
```bash
rsync -av /home/xtreme/claude-dev-team/ user@workmachine:~/dev/claude-dev-team/
```

After this step the scaffold should live at `~/dev/claude-dev-team/` on the work machine. The exact path doesn't matter, but examples below assume that location.

## Step 2 — Initialise as a git repo and push to internal GitLab

```bash
cd ~/dev/claude-dev-team

# verify everything looks right
ls -la

git init
git add .
git commit -m "initial scaffold"

# create the project on internal GitLab (via UI or CLI)
glab repo create your-namespace/claude-dev-team --private

# point local at the new remote and push
git remote add origin https://gitlab.your-internal-host/your-namespace/claude-dev-team.git
git branch -M main
git push -u origin main
```

If `glab` isn't installed yet, install it first:
- Debian/Ubuntu/WSL Ubuntu: `sudo apt install glab` (or grab the latest `.deb` from the GitLab CLI releases page)
- Then: `glab auth login --hostname gitlab.your-internal-host`

## Step 3 — Install the bundle locally

See `INSTALL.md` for the full install flow. Short version:

```bash
cd ~/dev/claude-dev-team
./install.sh
```

This symlinks the slash commands, hooks, and the SKILL.md into `~/.claude/`.

## Step 4 — Run the per-machine setup wizard

Inside Claude Code on the work machine, run:

```
/dev-team-setup
```

It will prompt you for:
- GitLab PAT
- GitHub PAT
- Notion integration token
- Default tracker host
- Default Notion database ID for the org-wide "Engineering Docs" database

Tokens are validated against each API before being written to `~/.config/claude-dev-team/config.toml` (`chmod 600`).

## Step 5 — Bootstrap the org-wide Notion database (one-time)

If the "Engineering Docs" Notion database doesn't already exist, you'll need to create it manually in Notion:

- Database properties: `Project` (select), `Type` (select: Setup / Troubleshooting / Requirements), `Component` (text), `Status` (select: Active / Deprecated / Archived), `Last Reviewed` (date), `Source File` (URL).
- Saved views: "By Type", "By Project", "Active only".
- Share the database with your Notion integration (via Notion's "Connections" UI on the database).

Grab the database ID from the URL and feed it into `/dev-team-setup` (or edit `~/.config/claude-dev-team/config.toml` directly afterward).

## Step 6 — First test project

Create a small throwaway project to validate the whole flow end-to-end:

```bash
mkdir -p ~/dev/test-dev-team
cd ~/dev/test-dev-team
# inside Claude Code:
# /dev-team-init
# /work-start "add a hello-world endpoint"
# (do the work, including a doc update)
# /work-review
# /work-done
```

If anything breaks, fix it in `~/dev/claude-dev-team/`, push, and run `/dev-team-update` from any project to pull the fix.

## Continuing development on the work machine — context

The bundle ships with three layers of design documentation. When starting a new Claude Code session on the work machine, brief the new Claude with:

> Read `SKILL.md`, then `DESIGN.md`, then (if present) `docs/design-conversation.md`. We're continuing development of this bundle — those three files are the design context.

- `SKILL.md` — short manifest, what the bundle is, command surface area.
- `DESIGN.md` — full ADR-style record of all 19 design decisions, the alternatives we considered, and why we chose what we chose. **This is the most important file** for any new contributor (human or Claude) deciding whether to change the bundle's shape.
- `docs/design-conversation.md` — the original grilling conversation. Optional, but high-bandwidth context. To create it: in the personal-machine Claude Code session that produced this scaffold, export the conversation as markdown and save it to `claude-dev-team/docs/design-conversation.md` *before* tarring.

If you don't include the conversation transcript, `DESIGN.md` alone is enough to make informed structural decisions — that was the point of writing it.

## What's intentionally not done in this scaffold

The following are **deferred to the work machine** because they require either network access, real credentials, or testing against live APIs:

- Validating that any of the Python adapter code actually runs
- Verifying the `gh` / `glab` invocations produce the expected output formats
- Confirming the Notion blocks are well-formed
- End-to-end test of `/dev-team-init` against a real GitLab instance
- Hook integration with `~/.claude/settings.json` (the install script handles this, but it hasn't been run)
- Confirming the statusline format renders correctly in your terminal

The scaffold contains all the *structure* and *intent*; the work machine is where it becomes real.
