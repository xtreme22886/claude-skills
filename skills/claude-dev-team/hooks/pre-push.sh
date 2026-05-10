#!/usr/bin/env bash
# pre-push.sh — git pre-push hook running verify-fast.
#
# Symlinked into <project>/.git/hooks/pre-push by /dev-team-init or /dev-team-adopt.
# Runs ~/.claude/skills/dev-team/adapter/verify_fast.py which dispatches to the
# project's lint/typecheck/changed-file-tests commands from .claude/project.json.
#
# Time-budgeted by config/defaults.toml verify_fast.budget_seconds (default 30s).
# Blocks the push on failure. Override with `git push --no-verify`.

set -euo pipefail

if [[ ! -f ".claude/project.json" ]]; then
  # Not a dev-team project — let the push through
  exit 0
fi

ADAPTER="${HOME}/.claude/skills/dev-team/adapter/verify_fast.py"

if [[ ! -f "$ADAPTER" ]]; then
  echo "[pre-push] verify_fast.py not found at $ADAPTER. Bundle install incomplete?" >&2
  echo "[pre-push] Skipping verify-fast and allowing push." >&2
  exit 0
fi

echo "[pre-push] Running verify-fast..."
START=$(date +%s)

if python3 "$ADAPTER"; then
  END=$(date +%s)
  echo "[pre-push] verify-fast passed in $((END - START))s"
  exit 0
else
  echo "[pre-push] verify-fast FAILED. Push blocked. Override with --no-verify if you really need to push." >&2
  exit 1
fi
