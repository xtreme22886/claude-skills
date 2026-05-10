"""verify_fast.py — runs lint, typecheck, and changed-file unit tests.

Called by the project's pre-push hook. Time-budgeted (default 30s).
Reads commands from .claude/project.json. Returns 0 on pass, non-zero on fail.

Status: SCAFFOLD — handles the simple cases. Per-stack changed-file test
selection is a TODO; this version runs the full configured test command
within the time budget, which can be too slow for large projects.
"""

from __future__ import annotations

import argparse
import json
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_BUDGET_SECONDS = 30


def load_project_config() -> dict:
    cfg = Path(".claude/project.json")
    if not cfg.exists():
        print("verify_fast: no .claude/project.json — nothing to verify", file=sys.stderr)
        sys.exit(0)
    return json.loads(cfg.read_text())


def load_budget() -> int:
    """Read verify_fast.budget_seconds from user config or fall back to default."""
    cfg_path = Path.home() / ".config" / "claude-dev-team" / "config.toml"
    if not cfg_path.exists():
        return DEFAULT_BUDGET_SECONDS
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore
        cfg = tomllib.loads(cfg_path.read_text())
        return int(cfg.get("verify_fast", {}).get("budget_seconds", DEFAULT_BUDGET_SECONDS))
    except Exception:
        return DEFAULT_BUDGET_SECONDS


def run_step(name: str, cmd: str, remaining_budget: int) -> tuple[bool, float]:
    """Run a step with the remaining budget as a timeout. Returns (ok, elapsed)."""
    if not cmd or cmd.strip() == "":
        return True, 0.0
    print(f"  [{name}] {cmd}")
    start = time.monotonic()
    try:
        subprocess.run(
            shlex.split(cmd),
            check=True,
            timeout=max(remaining_budget, 1),
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        print(f"  [{name}] TIMED OUT after {elapsed:.1f}s (budget {remaining_budget}s)",
              file=sys.stderr)
        return False, elapsed
    except subprocess.CalledProcessError as e:
        elapsed = time.monotonic() - start
        print(f"  [{name}] FAILED after {elapsed:.1f}s (rc={e.returncode})", file=sys.stderr)
        return False, elapsed
    elapsed = time.monotonic() - start
    print(f"  [{name}] ok ({elapsed:.1f}s)")
    return True, elapsed


def main():
    # Parse args first so --help works regardless of project state.
    argparse.ArgumentParser(description="Run pre-push verify-fast checks.").parse_args()

    cfg = load_project_config()
    ci_cfg = cfg.get("ci", {})
    budget = load_budget()

    # Steps in order. verify_fast_command takes precedence if set; otherwise
    # we run lint then typecheck then test.
    if ci_cfg.get("verify_fast_command"):
        steps = [("verify-fast", ci_cfg["verify_fast_command"])]
    else:
        steps = [
            ("lint", ci_cfg.get("lint_command", "")),
            ("typecheck", ci_cfg.get("typecheck_command", "")),
            ("test", ci_cfg.get("test_command", "")),
        ]

    elapsed_total = 0.0
    for name, cmd in steps:
        if not cmd:
            continue
        remaining = max(int(budget - elapsed_total), 1)
        ok, took = run_step(name, cmd, remaining)
        elapsed_total += took
        if not ok:
            sys.exit(1)
        if elapsed_total >= budget:
            print(f"verify_fast: budget exhausted after {elapsed_total:.1f}s", file=sys.stderr)
            sys.exit(1)

    print(f"verify_fast: all checks passed in {elapsed_total:.1f}s")
    sys.exit(0)


if __name__ == "__main__":
    main()
