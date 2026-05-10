"""notion_publish.py — publish docs/ops/ to the org-wide Engineering Docs DB.

Status: SCAFFOLD — interface defined, common cases sketched, edge cases marked
TODO. Needs testing against the real Notion DB on the work machine.

Walks docs/ops/{setup,troubleshooting,requirements}/ (or a configurable root),
reads frontmatter, upserts pages in the target Notion database. Uses each
file's frontmatter `notion_type`, `component`, `audience`, `last_reviewed`.

Also supports --dashboard mode: builds and upserts the cross-project dashboard
page used by /refresh-notion-dashboard.

Required env: NOTION_TOKEN
Required args: --project NAME --docs-root PATH [--database-id ID]

If --database-id not passed, reads from ~/.config/claude-dev-team/config.toml.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

# Both notion_client and tomli are runtime deps installed via requirements.txt.
# We import lazily inside main() so this module can be statically inspected
# without the deps installed.

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (metadata_dict, body) given a markdown file's text.

    Raises ValueError if no frontmatter present — mandatory for ops/ docs.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("missing frontmatter")
    raw_meta, body = m.group(1), m.group(2)
    meta: dict[str, Any] = {}
    for line in raw_meta.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body


def load_user_config() -> dict:
    config_path = Path.home() / ".config" / "claude-dev-team" / "config.toml"
    if not config_path.exists():
        return {}
    try:
        import tomllib  # 3.11+
    except ImportError:
        import tomli as tomllib  # type: ignore
    return tomllib.loads(config_path.read_text())


def markdown_to_notion_blocks(body: str) -> list[dict]:
    """Convert markdown body to a list of Notion blocks.

    SCAFFOLD: handles the common cases — paragraphs, headings, bullet lists,
    numbered lists, code blocks. Tables, callouts, images, and complex
    nesting are TODOs. The publisher should reject (with a clear error) any
    file that uses constructs we can't render, rather than silently producing
    a degraded page.
    """
    blocks: list[dict] = []
    lines = body.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        # Heading
        if line.startswith("# "):
            blocks.append(_heading(1, line[2:].strip()))
        elif line.startswith("## "):
            blocks.append(_heading(2, line[3:].strip()))
        elif line.startswith("### "):
            blocks.append(_heading(3, line[4:].strip()))
        # Code block
        elif line.startswith("```"):
            lang = line[3:].strip() or "plain text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [_text("\n".join(code_lines))],
                    "language": lang,
                },
            })
        # Bullet list
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [_text(line[2:].strip())]},
            })
        # Numbered list
        elif re.match(r"^\d+\.\s", line):
            content = re.sub(r"^\d+\.\s", "", line).strip()
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": [_text(content)]},
            })
        # Paragraph
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [_text(line.strip())]},
            })
        i += 1
    return blocks


def _heading(level: int, text: str) -> dict:
    key = f"heading_{level}"
    return {
        "object": "block",
        "type": key,
        key: {"rich_text": [_text(text)]},
    }


def _text(content: str) -> dict:
    return {"type": "text", "text": {"content": content}}


def upsert_page(notion, database_id: str, project_name: str,
                source_path: Path, source_url: Optional[str],
                meta: dict, body: str) -> str:
    """Upsert a Notion page keyed by (Project, Source File). Returns page id."""
    # Find existing page
    query = notion.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Project", "select": {"equals": project_name}},
                {"property": "Source File", "url": {"equals": source_url or str(source_path)}},
            ]
        },
    )

    properties = {
        "Project": {"select": {"name": project_name}},
        "Type": {"select": {"name": meta.get("notion_type", "setup").capitalize()}},
        "Component": {"rich_text": [_text(meta.get("component", ""))]},
        "Status": {"select": {"name": "Active"}},
        "Last Reviewed": {"date": {"start": meta.get("last_reviewed", "")}}
            if meta.get("last_reviewed") else None,
        "Source File": {"url": source_url or str(source_path)},
    }
    properties = {k: v for k, v in properties.items() if v is not None}

    title = source_path.stem.replace("-", " ").replace("_", " ").title()
    properties_with_title = {
        "Name": {"title": [_text(title)]},
        **properties,
    }

    blocks = markdown_to_notion_blocks(body)

    if query["results"]:
        page_id = query["results"][0]["id"]
        notion.pages.update(page_id=page_id, properties=properties_with_title)
        # Replace body: delete existing children, append new ones
        # TODO(testing): Notion API requires paginating block children for delete.
        # The simple version below works for small pages only.
        existing = notion.blocks.children.list(block_id=page_id)
        for child in existing["results"]:
            notion.blocks.delete(block_id=child["id"])
        notion.blocks.children.append(block_id=page_id, children=blocks)
        return page_id
    else:
        page = notion.pages.create(
            parent={"database_id": database_id},
            properties=properties_with_title,
            children=blocks,
        )
        return page["id"]


def archive_orphans(notion, database_id: str, project_name: str,
                    live_source_paths: set[str]) -> int:
    """Add deprecated banner + archive Notion pages whose source files are gone."""
    query = notion.databases.query(
        database_id=database_id,
        filter={
            "and": [
                {"property": "Project", "select": {"equals": project_name}},
                {"property": "Status", "select": {"equals": "Active"}},
            ]
        },
    )
    archived = 0
    for page in query["results"]:
        source_url_prop = page["properties"].get("Source File", {})
        source_url = source_url_prop.get("url")
        if source_url and source_url not in live_source_paths:
            # Add deprecated banner block
            notion.blocks.children.append(
                block_id=page["id"],
                children=[{
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [_text(
                            "⚠ Deprecated — the source markdown file for this page "
                            "no longer exists in the repo. This page is archived."
                        )],
                        "icon": {"type": "emoji", "emoji": "⚠️"},
                    },
                }],
            )
            notion.pages.update(
                page_id=page["id"],
                properties={"Status": {"select": {"name": "Archived"}}},
                archived=True,
            )
            archived += 1
    return archived


def publish_ops(args):
    try:
        from notion_client import Client
    except ImportError:
        print("notion-client not installed. Run: pip install --user -r adapter/requirements.txt",
              file=sys.stderr)
        sys.exit(2)

    user_cfg = load_user_config()
    token = os.environ.get("NOTION_TOKEN") or user_cfg.get("notion", {}).get("token")
    db_id = args.database_id or user_cfg.get("notion", {}).get("database_id")
    if not token:
        print("NOTION_TOKEN required (env or ~/.config/claude-dev-team/config.toml)",
              file=sys.stderr)
        sys.exit(2)
    if not db_id:
        print("--database-id required (or set in user config)", file=sys.stderr)
        sys.exit(2)

    notion = Client(auth=token)
    docs_root = Path(args.docs_root)
    if not docs_root.exists():
        print(f"docs root not found: {docs_root}", file=sys.stderr)
        sys.exit(2)

    upserted = 0
    skipped = 0
    live_paths: set[str] = set()

    for md_file in docs_root.rglob("*.md"):
        try:
            text = md_file.read_text()
            meta, body = parse_frontmatter(text)
        except ValueError as e:
            print(f"  skip {md_file}: {e}", file=sys.stderr)
            skipped += 1
            continue
        # TODO(work-machine): construct source_url from project's git remote +
        # the file path. Hard-code repo URL prefix or read from .claude/project.json.
        source_url = str(md_file)
        live_paths.add(source_url)
        upsert_page(notion, db_id, args.project, md_file, source_url, meta, body)
        upserted += 1
        print(f"  upserted {md_file}")

    archived = archive_orphans(notion, db_id, args.project, live_paths)

    print(f"\nDone. Upserted: {upserted}, Skipped: {skipped}, Archived: {archived}")


def publish_dashboard(args):
    """Build and upsert the cross-project dashboard page."""
    # TODO(implementation): walk default_project_root, gather state, render as
    # a single Notion page. Same shape as the /dashboard slash command output.
    print("publish_dashboard: not implemented in scaffold", file=sys.stderr)
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", help="Project name (required for ops publish)")
    parser.add_argument("--docs-root", default="docs/ops",
                        help="Root directory of ops docs (default: docs/ops)")
    parser.add_argument("--database-id", help="Notion database ID (or read from user config)")
    parser.add_argument("--dashboard", action="store_true",
                        help="Publish the cross-project dashboard instead")
    args = parser.parse_args()

    if args.dashboard:
        publish_dashboard(args)
    else:
        if not args.project:
            print("--project required for ops publish", file=sys.stderr)
            sys.exit(2)
        publish_ops(args)


if __name__ == "__main__":
    main()
