"""slice_check.py — heuristic checks on whether an issue looks like a vertical slice.

Status: SCAFFOLD — heuristics will need tuning against real issues. The point
is to surface advisory warnings when an issue looks horizontal, oversized, or
missing acceptance criteria. Used by /work-start and /work-review.

Run modes:

  python3 slice_check.py --issue <id>         # check an issue body via tracker
  python3 slice_check.py --diff               # check current branch diff for slice-completeness
  python3 slice_check.py --doc-deltas <files> # check doc deltas for an MR
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Hints that an issue is horizontal (build-out of one layer)
HORIZONTAL_KEYWORDS = [
    "all schemas", "all endpoints", "all migrations", "entire database",
    "build the database", "set up the entire", "rewrite the whole",
    "full schema", "complete refactor", "all components",
]

# Hints that an issue is properly vertical (one user-visible behavior)
VERTICAL_KEYWORDS = [
    "user can", "as a user", "given... when... then",
    "endpoint returns", "ui shows", "cli flag", "new metric",
]


def check_issue_body(body: str) -> dict:
    """Score an issue body. Returns {'verdict': 'vertical'|'horizontal'|'unclear',
    'reasons': [...], 'warnings': [...]}.
    """
    body_lower = body.lower()
    reasons = []
    warnings = []

    horizontal_hits = [k for k in HORIZONTAL_KEYWORDS if k in body_lower]
    vertical_hits = [k for k in VERTICAL_KEYWORDS if k in body_lower]

    if horizontal_hits:
        reasons.append(f"horizontal keywords: {horizontal_hits}")
    if vertical_hits:
        reasons.append(f"vertical keywords: {vertical_hits}")

    if not body.strip():
        warnings.append("issue body is empty — no slice shape to evaluate")

    if "## " not in body and "### " not in body:
        warnings.append("no section headings — vertical slices usually have at least 'What' and 'Acceptance criteria'")

    if "acceptance" not in body_lower and "accept" not in body_lower:
        warnings.append("no acceptance criteria visible")

    if len(body) < 100:
        warnings.append("issue body is very short — may not have enough detail for a slice")

    if horizontal_hits and not vertical_hits:
        verdict = "horizontal"
    elif vertical_hits and not horizontal_hits:
        verdict = "vertical"
    else:
        verdict = "unclear"

    return {"verdict": verdict, "reasons": reasons, "warnings": warnings}


def check_diff_completeness(diff_files: list[str]) -> dict:
    """Given the list of files changed on the slice branch, surface advisories
    about missing layers (DB without UI, code without tests, code without docs).

    Note: completeness is project-shape-dependent. This implementation makes
    Python/JS-flavored guesses; per-stack rules can be added in project.json
    later (see TODO).
    """
    result = {"warnings": []}

    has_db = any(f.endswith((".sql",)) or "migration" in f.lower() for f in diff_files)
    has_api = any(re.search(r"(routes?|handlers?|controllers?|api/|server/)", f) for f in diff_files)
    has_ui = any(re.search(r"(\.tsx?|\.jsx?|\.vue|\.svelte|components?/|pages?/|views?/)", f) for f in diff_files)
    has_tests = any(re.search(r"(tests?/|_test\.|\.test\.|spec/)", f) for f in diff_files)
    has_user_guide = any(f.startswith("docs/user-guide/") for f in diff_files)
    has_troubleshooting = any(
        f.startswith("docs/troubleshooting/") or f.startswith("docs/ops/troubleshooting/")
        for f in diff_files
    )
    has_ops_setup = any(f.startswith("docs/ops/setup/") for f in diff_files)
    has_ops_requirements = any(f.startswith("docs/ops/requirements/") for f in diff_files)
    has_setup_change = any(
        f in ("Dockerfile", "docker-compose.yml") or
        re.search(r"(deploy|terraform|infra|env\.|\.env)", f)
        for f in diff_files
    )

    if has_db and not (has_api or has_ui):
        result["warnings"].append(
            "DB change with no API/UI touch — looks horizontal. Vertical slice should expose the DB change to the user."
        )
    if (has_api or has_ui) and not has_tests:
        result["warnings"].append("Code changes with no tests — every slice should have at least one test exercising the new path.")
    if (has_api or has_ui) and not has_user_guide:
        result["warnings"].append("User-visible change with no docs/user-guide/ update — consider /work-docs.")
    if has_setup_change and not has_ops_setup:
        result["warnings"].append("Setup/deploy change with no docs/ops/setup/ update — IT Ops won't know.")
    if has_setup_change and not has_ops_requirements:
        result["warnings"].append("Setup change with no docs/ops/requirements/ update — confirm prereqs are still accurate.")
    # New error paths heuristic
    if any("raise " in _try_read(f) or "throw new " in _try_read(f) for f in diff_files if Path(f).exists()):
        if not has_troubleshooting:
            result["warnings"].append("Diff introduces new exceptions/throws — consider docs/troubleshooting/ entry.")

    return result


def _try_read(path: str) -> str:
    try:
        return Path(path).read_text(errors="ignore")
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", help="Issue ID to check (uses tracker.py)")
    parser.add_argument("--diff", action="store_true",
                        help="Check current branch's diff vs default branch")
    parser.add_argument("--default-branch", default="main")
    args = parser.parse_args()

    if args.issue:
        # Lazy import to avoid requiring tracker setup for diff-only mode
        from tracker import ProjectConfig, get_issue
        project = ProjectConfig.load()
        issue = get_issue(project, args.issue)
        result = check_issue_body(issue["body"])
        print(json.dumps(result, indent=2))
    elif args.diff:
        out = subprocess.check_output(
            ["git", "diff", f"{args.default_branch}...HEAD", "--name-only"],
            text=True,
        )
        diff_files = [f for f in out.splitlines() if f]
        result = check_diff_completeness(diff_files)
        print(json.dumps(result, indent=2))
    else:
        parser.error("must pass --issue or --diff")


if __name__ == "__main__":
    main()
