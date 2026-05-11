#!/usr/bin/env bash
# Uninstall claude-dev-team. Removes symlinks and hook entries.
# Leaves ~/.config/claude-dev-team/ and per-project .claude/ alone.
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
SKILL_DIR="$CLAUDE_HOME/skills/dev-team"
COMMANDS_DIR="$CLAUDE_HOME/commands"
SETTINGS_FILE="$CLAUDE_HOME/settings.json"
MARKER_FILE="$CLAUDE_HOME/.dev-team-installed"

echo "claude-dev-team uninstaller"
echo "  bundle:  $BUNDLE_DIR"
echo "  target:  $CLAUDE_HOME"
echo

# 1. Remove symlinked SKILL.md
rm -f "$SKILL_DIR/SKILL.md"
echo "  removed SKILL.md link"

# 2. Remove the adapter/ symlink and dt-python wrapper
rm -f "$SKILL_DIR/adapter"
rm -f "$SKILL_DIR/dt-python"
echo "  removed adapter link and dt-python wrapper"

# 3. Try to remove the now-likely-empty skill dir
rmdir --ignore-fail-on-non-empty "$SKILL_DIR" 2>/dev/null || true

# 4. Remove symlinked slash commands
for cmd in "$BUNDLE_DIR/commands/"*.md; do
  name="$(basename "$cmd")"
  rm -f "$COMMANDS_DIR/$name"
done
echo "  removed slash command links"

# 5. Remove statusline.sh symlink
rm -f "$CLAUDE_HOME/statusline.sh"
echo "  removed statusline.sh link"

# 6. Strip dev-team entries from settings.json
if [[ -f "$SETTINGS_FILE" ]]; then
  python3 - "$SETTINGS_FILE" <<'PYEOF'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
settings = json.loads(settings_path.read_text())

# Remove statusline if it points at our script
sl = settings.get("statusLine", {})
if isinstance(sl, dict) and "dev-team" in json.dumps(sl) or sl.get("command", "").endswith("/statusline.sh"):
    settings.pop("statusLine", None)

# Strip our hook entries
hooks = settings.get("hooks", {})
for event, entries in list(hooks.items()):
    entries[:] = [e for e in entries if "dev-team" not in json.dumps(e)]
    if not entries:
        hooks.pop(event)
if not hooks:
    settings.pop("hooks", None)

settings_path.write_text(json.dumps(settings, indent=2) + "\n")
print(f"  cleaned {settings_path}")
PYEOF
fi

# 7. Remove marker
rm -f "$MARKER_FILE"

echo
echo "Uninstall complete."
echo "  ~/.config/claude-dev-team/ is preserved (your tokens and config)."
echo "  per-project .claude/ directories are preserved."
echo "  the bundle directory itself ($BUNDLE_DIR) is preserved (including its .venv/)."
