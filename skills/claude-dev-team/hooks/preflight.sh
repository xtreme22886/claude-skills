#!/usr/bin/env bash
# preflight.sh — checks tracker reachability and auth before any tracker operation.
#
# Called explicitly by the tracker adapter (not wired into Claude Code's hook events
# directly — it would be too noisy as a SessionStart). Returns 0 if the project's
# tracker is reachable and authed, non-zero otherwise.
#
# Reads .claude/project.json from CWD to determine which tracker to check.
# Reads ~/.config/claude-dev-team/config.toml for tokens.

set -euo pipefail

PROJECT_JSON=".claude/project.json"
USER_CONFIG="$HOME/.config/claude-dev-team/config.toml"

if [[ ! -f "$PROJECT_JSON" ]]; then
  echo "preflight: no .claude/project.json — not a dev-team project" >&2
  exit 0   # not our concern, let the caller proceed
fi

TRACKER_TYPE=$(python3 -c "import json; print(json.load(open('$PROJECT_JSON'))['tracker']['type'])")
TRACKER_HOST=$(python3 -c "import json; print(json.load(open('$PROJECT_JSON'))['tracker']['host'])")

case "$TRACKER_TYPE" in
  github)
    if ! gh auth status >/dev/null 2>&1; then
      echo "preflight: gh not authenticated. Run /dev-team-setup or 'gh auth login'." >&2
      exit 1
    fi
    ;;
  gitlab)
    # Check VPN reachability first — common failure mode for internal hosts
    if ! curl -sfI --max-time 5 "https://${TRACKER_HOST}" >/dev/null 2>&1; then
      echo "preflight: cannot reach ${TRACKER_HOST}. Connect to VPN and retry." >&2
      exit 1
    fi
    if ! glab auth status --hostname "$TRACKER_HOST" >/dev/null 2>&1; then
      echo "preflight: glab not authenticated against ${TRACKER_HOST}. Run /dev-team-setup." >&2
      exit 1
    fi
    ;;
  *)
    echo "preflight: unknown tracker type '$TRACKER_TYPE'" >&2
    exit 2
    ;;
esac

exit 0
