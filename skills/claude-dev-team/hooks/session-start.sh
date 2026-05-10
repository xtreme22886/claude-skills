#!/usr/bin/env bash
# session-start.sh — SessionStart hook.
#
# Two responsibilities:
#   1. Check whether the bundle has updates available (git fetch + log compare).
#   2. Surface stale-paused-slice nudges for the current project (if in one).
#
# Output goes to stdout (Claude Code shows hook output to the user).
# Always exits 0; this hook is purely informational.

set -euo pipefail

MARKER="${HOME}/.claude/.dev-team-installed"
if [[ ! -f "$MARKER" ]]; then
  exit 0
fi

# shellcheck disable=SC1090
source "$MARKER"   # provides $bundle_dir, $version

# 1. Skill update check
if [[ -d "$bundle_dir/.git" ]]; then
  (
    cd "$bundle_dir"
    if git fetch --quiet origin 2>/dev/null; then
      AHEAD=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
      if [[ "$AHEAD" -gt 0 ]]; then
        echo "[dev-team] Bundle is $AHEAD commit(s) behind origin/main. Run /dev-team-update to apply."
      fi
    fi
  ) || true
fi

# 2. Stale paused slice nudges (only if in a dev-team project)
if [[ -f ".claude/project.json" && -d ".claude/paused" ]]; then
  python3 - <<'PYEOF' || true
import json
import os
import time
from pathlib import Path

paused_dir = Path(".claude/paused")
now = time.time()
stale_threshold_days = 7
stale = []

for f in paused_dir.glob("*.json"):
    try:
        snap = json.loads(f.read_text())
        paused_at = snap.get("paused_at")
        if not paused_at:
            continue
        # crude ISO parse without dateutil
        from datetime import datetime
        ts = datetime.fromisoformat(paused_at.replace("Z", "+00:00")).timestamp()
        days = (now - ts) / 86400
        if days >= stale_threshold_days:
            stale.append((snap["issue_id"], int(days)))
    except Exception:
        continue

if stale:
    msg_lines = ["[dev-team] Stale paused slices (>7 days):"]
    for issue_id, days in stale:
        msg_lines.append(f"  - {issue_id} ({days}d). Resume with /work-resume {issue_id} or close.")
    print("\n".join(msg_lines))
PYEOF
fi

exit 0
