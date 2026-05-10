#!/usr/bin/env bash
# phase-warn.sh — PreToolUse hook providing advisory phase enforcement.
#
# Reads .claude/current-work.json (if present in CWD) and the tool being called
# from stdin (Claude Code passes a JSON payload). Prints a non-blocking warning
# to stderr if the action looks out-of-phase. Exits 0 always — never blocks.
#
# Settings.json wires this for matchers Edit|Write|Bash.

set -euo pipefail

# Quick exit if not in a dev-team project
if [[ ! -f ".claude/current-work.json" ]]; then
  exit 0
fi

# Quick exit if project is in strict mode and we want different behavior, or if
# enforcement is disabled. Default is advisory — that's what this script does.
ENF=$(python3 -c "
import json
try:
    cfg = json.load(open('.claude/project.json'))
    print(cfg.get('enforcement', {}).get('mode', 'advisory'))
except Exception:
    print('advisory')
")

# In advisory mode (default and only mode this script implements), we just warn.
# Strict mode would require reading the hook payload more carefully and exiting
# nonzero — left as future work, see TODO at the bottom.

PHASE=$(python3 -c "import json; print(json.load(open('.claude/current-work.json'))['phase'])" 2>/dev/null || echo "")

# Read hook input — Claude Code provides JSON on stdin for hooks
HOOK_INPUT=$(cat || true)
TOOL_NAME=$(echo "$HOOK_INPUT" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('tool_name', ''))" 2>/dev/null || echo "")

case "$PHASE" in
  design)
    if [[ "$TOOL_NAME" == "Edit" || "$TOOL_NAME" == "Write" ]]; then
      echo "[phase-warn] Slice is in DESIGN phase. Editing code now is unusual — consider /work-design-done first if you've finished planning. (advisory; proceeding)" >&2
    fi
    ;;
  review)
    if [[ "$TOOL_NAME" == "Edit" || "$TOOL_NAME" == "Write" ]]; then
      echo "[phase-warn] Slice is in REVIEW phase. New edits will need a re-push and re-review. (advisory; proceeding)" >&2
    fi
    ;;
  done)
    echo "[phase-warn] Slice phase is DONE but current-work.json still present — should have been cleared. Investigate. (advisory; proceeding)" >&2
    ;;
esac

# TODO(strict-mode): when enforcement.mode == "strict" in project.json, exit
# non-zero on out-of-phase actions to actually block them. Not implemented in
# this scaffold — advisory is the default and only behavior shipped.

exit 0
