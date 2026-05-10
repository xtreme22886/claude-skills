"""tracker.py — dispatch to gh or glab based on .claude/project.json.

Workflow skills (work-start, work-review, etc.) call the functions exported here
instead of shelling out to gh/glab directly. That keeps the workflow skills
tracker-agnostic.

Status: SCAFFOLD — interface defined, common cases implemented, edge cases
marked TODO. Needs testing against real GitHub + GitLab instances on the work
machine before being trusted.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

TrackerType = Literal["github", "gitlab"]


@dataclass
class ProjectConfig:
    name: str
    tracker_type: TrackerType
    tracker_host: str
    tracker_project_path: str
    tracker_project_id: Optional[str]

    @classmethod
    def load(cls, project_root: Path = Path(".")) -> "ProjectConfig":
        cfg_path = project_root / ".claude" / "project.json"
        if not cfg_path.exists():
            raise RuntimeError(f"no .claude/project.json found at {project_root}")
        cfg = json.loads(cfg_path.read_text())
        t = cfg["tracker"]
        return cls(
            name=cfg["name"],
            tracker_type=t["type"],
            tracker_host=t["host"],
            tracker_project_path=t["project_path"],
            tracker_project_id=t.get("project_id"),
        )


# ---------- preflight ----------

def preflight(project: ProjectConfig) -> bool:
    """Return True iff the tracker is reachable and the CLI is authed."""
    if project.tracker_type == "github":
        return _run_capture(["gh", "auth", "status"]).returncode == 0
    elif project.tracker_type == "gitlab":
        # Reachability check first (catches no-VPN case with a useful message)
        rc = _run_capture(
            ["curl", "-sfI", "--max-time", "5", f"https://{project.tracker_host}"]
        ).returncode
        if rc != 0:
            print(f"preflight: cannot reach {project.tracker_host}", file=sys.stderr)
            return False
        return (
            _run_capture(
                ["glab", "auth", "status", "--hostname", project.tracker_host]
            ).returncode
            == 0
        )
    raise ValueError(f"unknown tracker type: {project.tracker_type}")


# ---------- issues ----------

def get_issue(project: ProjectConfig, issue_id: str) -> dict:
    """Fetch an issue. Returns a normalized dict.

    Schema (normalized across GitHub/GitLab):
        {
          "id": str,
          "url": str,
          "title": str,
          "body": str,
          "state": "open" | "closed",
          "labels": list[str],
          "assignees": list[str],
        }
    """
    issue_id_clean = issue_id.lstrip("#")
    if project.tracker_type == "github":
        out = _run(
            ["gh", "issue", "view", issue_id_clean, "--json",
             "number,url,title,body,state,labels,assignees"],
            cwd=None,
        )
        raw = json.loads(out)
        return {
            "id": str(raw["number"]),
            "url": raw["url"],
            "title": raw["title"],
            "body": raw["body"] or "",
            "state": raw["state"].lower(),
            "labels": [l["name"] for l in raw["labels"]],
            "assignees": [a["login"] for a in raw["assignees"]],
        }
    elif project.tracker_type == "gitlab":
        out = _run(
            ["glab", "issue", "view", issue_id_clean, "-F", "json",
             "--hostname", project.tracker_host],
            cwd=None,
        )
        raw = json.loads(out)
        return {
            "id": str(raw["iid"]),
            "url": raw["web_url"],
            "title": raw["title"],
            "body": raw.get("description") or "",
            "state": "open" if raw["state"] == "opened" else "closed",
            "labels": raw.get("labels", []),
            "assignees": [a["username"] for a in raw.get("assignees", [])],
        }
    raise ValueError(project.tracker_type)


def create_issue(project: ProjectConfig, title: str, body: str,
                 labels: Optional[list[str]] = None) -> dict:
    """Create an issue. Returns the same normalized dict as get_issue."""
    labels = labels or []
    if project.tracker_type == "github":
        cmd = ["gh", "issue", "create", "--title", title, "--body", body]
        for lbl in labels:
            cmd.extend(["--label", lbl])
        url = _run(cmd).strip().splitlines()[-1]
        # gh returns the URL; parse the issue number from it
        issue_id = url.rstrip("/").rsplit("/", 1)[-1]
        return get_issue(project, issue_id)
    elif project.tracker_type == "gitlab":
        cmd = [
            "glab", "issue", "create",
            "--title", title,
            "--description", body,
            "--hostname", project.tracker_host,
        ]
        if labels:
            cmd.extend(["--label", ",".join(labels)])
        out = _run(cmd)
        # TODO(testing): confirm glab output format includes the URL we can parse
        url = out.strip().splitlines()[-1]
        issue_id = url.rstrip("/").rsplit("/", 1)[-1]
        return get_issue(project, issue_id)
    raise ValueError(project.tracker_type)


def comment_on_issue(project: ProjectConfig, issue_id: str, body: str) -> None:
    issue_id_clean = issue_id.lstrip("#")
    if project.tracker_type == "github":
        _run(["gh", "issue", "comment", issue_id_clean, "--body", body])
    elif project.tracker_type == "gitlab":
        _run([
            "glab", "issue", "note", issue_id_clean,
            "--message", body,
            "--hostname", project.tracker_host,
        ])


def close_issue(project: ProjectConfig, issue_id: str, comment: Optional[str] = None) -> None:
    if comment:
        comment_on_issue(project, issue_id, comment)
    issue_id_clean = issue_id.lstrip("#")
    if project.tracker_type == "github":
        _run(["gh", "issue", "close", issue_id_clean])
    elif project.tracker_type == "gitlab":
        _run([
            "glab", "issue", "close", issue_id_clean,
            "--hostname", project.tracker_host,
        ])


# ---------- merge requests / pull requests ----------

def open_mr_or_pr(project: ProjectConfig, branch: str, title: str, body: str,
                  base: str = "main") -> dict:
    """Open an MR (GitLab) or PR (GitHub). Returns {url, id, number}."""
    if project.tracker_type == "github":
        out = _run([
            "gh", "pr", "create",
            "--head", branch,
            "--base", base,
            "--title", title,
            "--body", body,
        ])
        url = out.strip().splitlines()[-1]
        return {"url": url, "id": url.rstrip("/").rsplit("/", 1)[-1], "type": "pr"}
    elif project.tracker_type == "gitlab":
        out = _run([
            "glab", "mr", "create",
            "--source-branch", branch,
            "--target-branch", base,
            "--title", title,
            "--description", body,
            "--hostname", project.tracker_host,
        ])
        # TODO(testing): confirm output format. May need --output json to be safe.
        url_lines = [l for l in out.splitlines() if "://" in l]
        url = url_lines[-1] if url_lines else ""
        return {"url": url, "id": url.rstrip("/").rsplit("/", 1)[-1], "type": "mr"}
    raise ValueError(project.tracker_type)


def get_ci_status(project: ProjectConfig, mr_or_pr_id: str) -> dict:
    """Fetch CI status for a MR/PR. Returns {state, jobs, url}.

    state: "passing" | "failing" | "running" | "unknown"
    """
    if project.tracker_type == "github":
        out = _run(["gh", "pr", "checks", mr_or_pr_id, "--json", "name,state,link"])
        checks = json.loads(out)
        if not checks:
            return {"state": "unknown", "jobs": [], "url": None}
        states = {c["state"].lower() for c in checks}
        if "failure" in states or "failed" in states:
            state = "failing"
        elif {"in_progress", "queued", "pending"} & states:
            state = "running"
        else:
            state = "passing"
        return {"state": state, "jobs": checks, "url": None}
    elif project.tracker_type == "gitlab":
        # TODO(testing): glab ci view doesn't have a clean json mode for MR-level
        # status. May need to use the API directly via `glab api`.
        out = _run([
            "glab", "api",
            f"projects/:id/merge_requests/{mr_or_pr_id}/pipelines",
            "--hostname", project.tracker_host,
        ])
        pipelines = json.loads(out)
        if not pipelines:
            return {"state": "unknown", "jobs": [], "url": None}
        latest = pipelines[0]
        gl_status = latest.get("status", "unknown")
        state = {
            "success": "passing",
            "failed": "failing",
            "running": "running",
            "pending": "running",
            "created": "running",
        }.get(gl_status, "unknown")
        return {"state": state, "jobs": pipelines, "url": latest.get("web_url")}
    raise ValueError(project.tracker_type)


def get_ci_logs(project: ProjectConfig, mr_or_pr_id: str, only_failed: bool = True) -> str:
    """Fetch failure logs from the most recent CI run on a MR/PR.

    Returns the raw text (truncated to ~50k chars). Caller does the parsing.
    """
    if project.tracker_type == "github":
        out = _run(["gh", "pr", "checks", mr_or_pr_id, "--json", "name,state,link"])
        checks = json.loads(out)
        failed = [c for c in checks if c["state"].lower() in ("failure", "failed")]
        logs = []
        for c in failed:
            run_id = c["link"].rstrip("/").split("/")[-1]
            try:
                log = _run(["gh", "run", "view", run_id, "--log-failed"])
                logs.append(f"=== {c['name']} ===\n{log}")
            except Exception as e:
                logs.append(f"=== {c['name']} === (could not fetch: {e})")
        return ("\n\n".join(logs))[:50000]
    elif project.tracker_type == "gitlab":
        # TODO(implementation): walk pipeline -> jobs -> trace
        return "TODO: implement GitLab CI log fetching"
    raise ValueError(project.tracker_type)


# ---------- helpers ----------

def _run(cmd: list[str], cwd: Optional[Path] = None) -> str:
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, check=True
    )
    return result.stdout


def _run_capture(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("preflight")

    p = sub.add_parser("get-issue")
    p.add_argument("issue_id")

    p = sub.add_parser("ci-status")
    p.add_argument("mr_id")

    args = parser.parse_args()
    project = ProjectConfig.load()

    if args.cmd == "preflight":
        sys.exit(0 if preflight(project) else 1)
    elif args.cmd == "get-issue":
        print(json.dumps(get_issue(project, args.issue_id), indent=2))
    elif args.cmd == "ci-status":
        print(json.dumps(get_ci_status(project, args.mr_id), indent=2))


if __name__ == "__main__":
    main()
