---
name: pdf-positional-tables
description: Extract positional tables from PDFs where tables are rendered as positioned text (not real PDF table objects) and every table shares the same column headers/x-coordinates throughout the document. Typical sources are Microsoft Access exports, schema/data dictionary dumps, API references, and other auto-generated reports. Use when the user wants to convert such a PDF into structured markdown/CSV/JSON, or mentions "data dictionary", "schema PDF", or many tables that all share the same columns. SKIP when the PDF contains real table objects with cell borders (use pdfplumber's `page.extract_tables()` instead) or when tables have varying column structures.
---

# Extracting Positional Tables from PDFs

## When this skill applies

Use this skill when **all** of the following are true:

1. The PDF contains many tables that all share the **same column headers** (e.g. every table has columns `Column Name | Data Type | ... | Notes`).
2. The tables are rendered as positioned text — words placed at fixed x/y coordinates — rather than as PDF table objects with cell borders. Telltale signs: the source application is Microsoft Access, an ORM schema dumper, or an internal report generator.
3. The "tables" can span multiple pages with continuation rows that have no column header repeated.

If the PDF has real table objects (lines/borders separating cells), don't use this skill — use `pdfplumber`'s `page.extract_tables()` via [Anthropic's official `pdf` skill](https://github.com/anthropics/skills/tree/main/skills/pdf), which is dramatically simpler.

## Why pdftotext is the wrong tool

`pdftotext -layout` is the reflexive choice for layout-preserving text extraction, but it is **broken for this use case**. pdftotext rescales character columns per page based on the widest line on that page (which often includes the page header). The same logical column will appear at different character positions on different pages. Heuristics to recover from this — clustering, scaling, content classification — are fragile and produce wrong column assignments on continuation pages.

The right tool is `pdfplumber`. It exposes each word's physical x-coordinate from the PDF, which is **byte-identical across every page** for the kind of PDFs this skill targets. No layout artifact, no per-page scaling.

## Workflow

### 1. Install pdfplumber

If pdfplumber is not available:

```bash
# Try the system package manager first; usually need pipx
apt-get install -y pipx 2>/dev/null || python3 -m pip install --user pipx
pipx install pdfplumber

# pipx installs into the invoking user's home directory. Resolve the
# interpreter portably (works for any user, any platform):
PDFPLUMBER_PY="$(pipx environment --value PIPX_LOCAL_VENVS)/pdfplumber/bin/python"
```

Verify: `$PDFPLUMBER_PY -c "import pdfplumber; print(pdfplumber.__version__)"`.

If `pipx` itself isn't available and can't be installed, fall back to a venv:

```bash
python3 -m venv /tmp/pdfplumber-venv
/tmp/pdfplumber-venv/bin/pip install pdfplumber
PDFPLUMBER_PY=/tmp/pdfplumber-venv/bin/python
```

### 2. Probe the PDF — confirm columns are stable

Before assuming the skill applies, sample several pages spread across the document and inspect the column-header line's word x-coordinates. Use `scripts/probe_columns.py`:

```bash
# Run from this skill's own directory; replace <path-to-pdf> with the actual file.
$PDFPLUMBER_PY scripts/probe_columns.py "<path-to-pdf>"
```

(The skill's directory is `~/.claude/skills/pdf-positional-tables/` for user-scope installs, or `<plugin-dir>/skills/pdf-positional-tables/` if installed via a plugin. Substitute `<path-to-pdf>` with the actual PDF the user provided — the script just takes a filesystem path.)

This prints the x-coordinate of each column-header word on ~10 sampled pages. If those x-coordinates match across all sampled pages (typically to within < 0.5 pt), proceed. If they vary significantly, this skill does not apply — fall back to the standard pdf skill or content-based heuristics.

### 3. Identify the structural anchors

Read the PDF's first content page and a couple of continuation pages to identify:

- **Column-header text**: e.g. `Column Name`, `Data Type`, `Null`, `Default`, `Index Name`, `PK/FKey`, `Notes`. These will be your column anchors. Record each anchor's x-coordinate.
- **Table-start marker**: e.g. lines starting with `Table:`. Used to split records into logical tables.
- **Page header/footer y-zones**: noise lines at the top and bottom of every page (page title, "CONFIDENTIAL", page numbers). Drop them by y-coordinate. Record the y-range to keep (e.g. `50 < top < 565`).

### 4. Adapt the reference parser

`scripts/parse_positional_tables.py` is a working template. **It will not run correctly out of the box** — you must edit it for the specific PDF before running.

Copy the script to the working directory, then edit:

1. **The constants block at the top of the file** (lines marked `PROJECT-SPECIFIC CONSTANTS`):
   - `PDF_PATH`, `OUTPUT_PATH` — file paths.
   - `COL_X0` — paste the column-name → x-coordinate map from `probe_columns.py`. Include every column the PDF has; remove any column the PDF doesn't have. Order matters (left to right).
   - `HEADER_Y_MAX`, `FOOTER_Y_MIN` — y-coordinate cuts for the page header/footer (from step 3).
   - `TABLE_RE` — regex matching the line that introduces a new logical table (capture group 1 = table name). Default matches `Table: NAME`; change if the PDF uses something else (e.g. `Entity:`, `## `, etc.).
   - `PAGES` — `(start, end)` half-open 0-indexed page range. Use this to skip cover/copyright pages.

2. **`is_column_header_line()`** (further down the file) — its required-words list (`'Column Name'`, `'Data Type'`) must match the actual column-header text in the PDF, or the parser will treat the column header as a data row.

Then run with the pdfplumber interpreter:

```bash
$PDFPLUMBER_PY parse_positional_tables.py
```

The parser:

- Streams pages and writes each completed table to disk immediately (avoids OOM on large PDFs).
- Calls `page.flush_cache()` after each page (otherwise pdfplumber accumulates per-page state and OOMs at ~3000 pages).
- Joins wrapped continuation lines: identifier values (no internal spaces) join without a separator (`PK__AE_...8` + `D` → `PK__AE_...8D`); descriptive prose (has spaces) joins with a separating space.

### 5. Spot-check the output

After running, verify on **one continuation page** explicitly. Pick a page that starts mid-table (no `Table:` marker at top, no column-header line at top) and confirm:

- Column Name values landed in the Column Name column.
- The rightmost column (e.g. Notes) didn't accidentally absorb identifier-shaped values.
- Wrapped values were rejoined.

If anything is wrong, the column x-coordinates in `COL_X0` likely need adjusting; re-run `probe_columns.py` on the failing page to see actual word positions.

## Output formats

The reference script writes markdown with one `## TableName` section per table and a markdown table per record whose columns match `COL_X0` (i.e. however many columns your PDF has). To produce CSV/JSON instead, replace `write_table_md()` in the script — the parsed structure is already a list of `{column: value}` dicts.

## Performance notes

- Expect ~2 seconds per 100 pages on a typical PDF. A 5000-page document parses in ~4 minutes.
- Memory grows linearly without `page.flush_cache()` — at ~3000 pages a 16 GB process gets OOM-killed. The reference script handles this; don't remove that call.
- Streaming output to disk (rather than accumulating all tables in a list) is what keeps Python's resident memory bounded even on huge PDFs.

## Common mistakes

- **Trusting `pdftotext -layout`.** Don't. Even with a "smart" parser on top, you'll fight column-position drift on every continuation page. Use pdfplumber's word x-coordinates.
- **Using `page.extract_tables()`.** This works on PDFs with line-bordered tables. The PDFs this skill targets have no table objects — extract_tables returns nothing useful.
- **Forgetting to drop the header/footer.** The page-title text on every page will pollute the first row of every continuation page if you don't filter by y-coordinate before processing.
- **Joining all wraps with a space.** Long identifier values (PK/FK names) wrap mid-token; joining with a space corrupts the identifier. Use the "if existing has spaces, prose; else identifier" heuristic in the reference script.
