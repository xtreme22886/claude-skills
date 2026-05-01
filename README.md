# claude-skills

A small collection of [Claude Code](https://claude.com/claude-code) skills I've built for tasks I run into.

## Skills

| Skill | What it does |
| --- | --- |
| [`pdf-positional-tables`](skills/pdf-positional-tables/) | Extract tables from PDFs where every table shares the same column headers and the columns are at the same x-coordinates throughout the document (Microsoft Access exports, schema dumps, API references). |

## Installing a skill

Each skill is a self-contained directory under `skills/`. To install one for your user:

```bash
mkdir -p ~/.claude/skills
cp -r skills/<skill-name> ~/.claude/skills/
```

The next Claude Code session will pick the skill up automatically — its name and description appear in the available-skills list, and Claude can invoke it via the `Skill` tool.

To uninstall, just delete the directory.

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`).
2. Put any helper scripts under `skills/<skill-name>/scripts/`.
3. Reference scripts from SKILL.md with relative paths (so the skill works regardless of where it's installed).
4. Add a row to the table above.
