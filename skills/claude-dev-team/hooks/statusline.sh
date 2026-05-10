#!/usr/bin/env bash
# statusline.sh — claude-dev-team status line.
#
# Wired to settings.json statusLine.command by install.sh.
# Reads .claude/current-work.json from CWD (if present) and the matching
# tracker MR/PR + CI status (cached, not live-fetched on every render).
#
# Output format (one line):
#   [issue-id] phase | branch | ✓/✗ ci | ⚠ N urgent
#
# "Urgent" counter only includes blocking things — failed CI on current
# branch, blocked review, broken pre-push hook. Soft nudges (paused stale,
# missing docs, etc.) live in /dashboard, not here.

set -euo pipefail

# Quick exit if not in a dev-team project
if [[ ! -f ".claude/current-work.json" ]]; then
  # Optional: still show project name if .claude/project.json exists
  if [[ -f ".claude/project.json" ]]; then
    PROJECT=$(python3 -c "import json; print(json.load(open('.claude/project.json'))['name'])" 2>/dev/null || echo "?")
    echo "[$PROJECT] no active slice"
  fi
  exit 0
fi

python3 - <<'PYEOF' 2>/dev/null || echo "[dev-team] statusline error"
import json
from pathlib import Path

cw = json.loads(Path(".claude/current-work.json").read_text())
issue_id = cw.get("issue_id", "?")
phase = cw.get("phase", "?")
branch = cw.get("branch", "?")
ci_status = cw.get("ci_status")  # cached: "passing", "failing", "running", or None

ci_glyph = ""
if ci_status == "passing":
    ci_glyph = " | ✓ ci"
elif ci_status == "failing":
    ci_glyph = " | ✗ ci"
elif ci_status == "running":
    ci_glyph = " | ... ci"

# Urgent counter — only things needing immediate action
urgent = 0
if ci_status == "failing":
    urgent += 1
# Add other urgent signals here as they're implemented

urgent_glyph = f" | ⚠ {urgent}" if urgent else ""

print(f"[{issue_id}] {phase} | {branch}{ci_glyph}{urgent_glyph}")
PYEOF
