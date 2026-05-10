#!/usr/bin/env bash
# Install claude-dev-team into ~/.claude/.
# Idempotent — safe to re-run.
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
SKILL_DIR="$CLAUDE_HOME/skills/dev-team"
COMMANDS_DIR="$CLAUDE_HOME/commands"
SETTINGS_FILE="$CLAUDE_HOME/settings.json"
MARKER_FILE="$CLAUDE_HOME/.dev-team-installed"

VERSION="$(grep -m1 '^## ' "$BUNDLE_DIR/CHANGELOG.md" | sed -E 's/^## ([^ ]+).*/\1/')"

echo "claude-dev-team installer (version $VERSION)"
echo "  bundle:  $BUNDLE_DIR"
echo "  target:  $CLAUDE_HOME"
echo

# 1. Ensure dirs exist
mkdir -p "$SKILL_DIR" "$COMMANDS_DIR"

# 2. Symlink SKILL.md
ln -sf "$BUNDLE_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
echo "  linked SKILL.md"

# 3. Symlink each slash command
for cmd in "$BUNDLE_DIR/commands/"*.md; do
  name="$(basename "$cmd")"
  ln -sf "$cmd" "$COMMANDS_DIR/$name"
done
echo "  linked $(ls "$BUNDLE_DIR/commands/" | wc -l) slash commands"

# 4. Symlink statusline.sh and ensure executable
ln -sf "$BUNDLE_DIR/hooks/statusline.sh" "$CLAUDE_HOME/statusline.sh"
chmod +x "$BUNDLE_DIR/hooks/"*.sh
echo "  linked statusline.sh"

# 5. Patch settings.json (idempotent)
# We use python here because shell-based JSON editing is fragile.
python3 - "$SETTINGS_FILE" "$BUNDLE_DIR" <<'PYEOF'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
bundle_dir = sys.argv[2]

if settings_path.exists():
    settings = json.loads(settings_path.read_text())
else:
    settings = {}

# StatusLine
settings.setdefault("statusLine", {})
settings["statusLine"]["type"] = "command"
settings["statusLine"]["command"] = f"{Path.home()}/.claude/statusline.sh"

# Hooks
hooks = settings.setdefault("hooks", {})

def upsert_hook(event_name, command, matcher=None):
    """Insert (or replace) a dev-team hook entry without disturbing others."""
    entries = hooks.setdefault(event_name, [])
    # Remove any existing dev-team entries for this event
    entries[:] = [e for e in entries if "dev-team" not in json.dumps(e)]
    entry = {
        "hooks": [
            {
                "type": "command",
                "command": command,
            }
        ]
    }
    if matcher is not None:
        entry["matcher"] = matcher
    entries.append(entry)

upsert_hook(
    "SessionStart",
    f"{bundle_dir}/hooks/session-start.sh",
)
upsert_hook(
    "PreToolUse",
    f"{bundle_dir}/hooks/phase-warn.sh",
    matcher="Edit|Write|Bash",
)

settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(settings, indent=2) + "\n")
print(f"  patched {settings_path}")
PYEOF

# 6. Drop marker file
cat > "$MARKER_FILE" <<EOF
bundle_dir=$BUNDLE_DIR
version=$VERSION
installed_at=$(date -Iseconds)
EOF
echo "  marker: $MARKER_FILE"

echo
echo "Install complete."
echo
echo "Next steps:"
echo "  1. Restart Claude Code so it re-scans ~/.claude/commands/."
echo "  2. Run /dev-team-setup inside Claude Code to configure tokens."
echo "  3. cd into a project and run /dev-team-init or /dev-team-adopt."
