#!/usr/bin/env python3
"""Reference parser for positional-table PDFs (see SKILL.md).

Adapt the constants below to your PDF, then run with:
    /root/.local/share/pipx/venvs/pdfplumber/bin/python parse_positional_tables.py
"""
import os
import re
import sys
import time

import pdfplumber

# ============================================================================
# PROJECT-SPECIFIC CONSTANTS — replace these for your PDF.
# Use scripts/probe_columns.py to discover the x-coordinates.
# ============================================================================
PDF_PATH = 'input.pdf'
OUTPUT_PATH = 'tables.md'

# Each column's left-edge x0 in points. The columns will be assigned by:
# token at x is in column C  iff  C has the greatest x0 <= token.x0 + slack.
# Order the dict left-to-right (Python preserves insertion order).
COL_X0 = {
    'Column Name':     44.13,
    'Data Type':      213.19,
    'Null':           285.20,
    'Default':        299.67,
    'Index Name':     344.70,
    'PK/FKey Object': 476.19,
    'Notes':          610.82,
}

# Y-coordinate cuts to drop the page header (top) and footer (bottom).
HEADER_Y_MAX = 50
FOOTER_Y_MIN = 565

# Regex matching the line that introduces a new logical table.
# Capture group 1 is the table name.
TABLE_RE = re.compile(r'^Table:\s+(.+?)\s*$')

# 0-indexed half-open page range to process. Use this to skip cover/copyright
# pages at the front and any back-matter.
PAGES = (2, None)  # None means "to end of document"

# How aggressively to merge consecutive words on the same line into one token.
# Words separated by <= X_GAP horizontal points join into a single cell value.
X_GAP = 3.5

# Same-line y-tolerance when grouping words into lines (points).
Y_TOLERANCE = 2.5
# ============================================================================

COLS = list(COL_X0.keys())


def _append(existing, new):
    """Join continuation text to an existing cell value. Identifier-like values
    (no internal whitespace) are joined without a separator (PDF wraps split
    them mid-token). Descriptive prose joins with a space."""
    if not existing:
        return new
    if ' ' in existing:
        return existing + ' ' + new
    return existing + new


def column_for_x(x0, slack=2):
    chosen = COLS[0]
    for col in COLS:
        if x0 + slack >= COL_X0[col]:
            chosen = col
        else:
            break
    return chosen


def group_words_into_lines(words):
    if not words:
        return []
    sorted_w = sorted(words, key=lambda w: (w['top'], w['x0']))
    lines = []
    current = [sorted_w[0]]
    cur_top = sorted_w[0]['top']
    for w in sorted_w[1:]:
        if abs(w['top'] - cur_top) <= Y_TOLERANCE:
            current.append(w)
        else:
            current.sort(key=lambda x: x['x0'])
            lines.append(current)
            current = [w]
            cur_top = w['top']
    current.sort(key=lambda x: x['x0'])
    lines.append(current)
    return lines


def words_to_tokens(line_words):
    if not line_words:
        return []
    tokens = []
    cur_text = line_words[0]['text']
    cur_x0 = line_words[0]['x0']
    cur_x1 = line_words[0]['x1']
    for w in line_words[1:]:
        gap = w['x0'] - cur_x1
        if gap <= X_GAP:
            cur_text += ' ' + w['text']
            cur_x1 = w['x1']
        else:
            tokens.append((cur_x0, cur_text))
            cur_text = w['text']
            cur_x0 = w['x0']
            cur_x1 = w['x1']
    tokens.append((cur_x0, cur_text))
    return tokens


def is_column_header_line(tokens):
    """PROJECT-SPECIFIC: returns True for a line that contains the table's
    column-header text (so the parser can skip it instead of treating it as a
    data row). Edit the required-words tuple below to match your PDF.
    """
    if not tokens:
        return False
    text = ' '.join(t[1] for t in tokens)
    return all(w in text for w in ('Column Name', 'Data Type'))  # <-- EDIT


def md_escape(s):
    if s is None:
        return ''
    return s.replace('|', '\\|').replace('\n', ' ').strip()


def write_table_md(f, t):
    f.write(f"## {t['name']}\n\n")
    if t['description']:
        f.write(' '.join(t['description']) + '\n\n')
    if not t['rows']:
        f.write('_(no columns parsed)_\n\n')
        return
    f.write('| ' + ' | '.join(COLS) + ' |\n')
    f.write('|' + '|'.join(['---'] * len(COLS)) + '|\n')
    for r in t['rows']:
        cells = [md_escape(r.get(c, '')) for c in COLS]
        f.write('| ' + ' | '.join(cells) + ' |\n')
    f.write('\n')


def parse_and_stream(body_path, names_out, verbose=False):
    current = None
    table_count = 0
    row_count = 0
    page_count = 0
    t0 = time.time()

    with open(body_path, 'w') as bf, pdfplumber.open(PDF_PATH) as pdf:
        start, end = PAGES
        if end is None:
            end = len(pdf.pages)
        for page_idx in range(start, end):
            page = pdf.pages[page_idx]
            words = page.extract_words(keep_blank_chars=False, use_text_flow=True)
            words = [w for w in words
                     if HEADER_Y_MAX < w['top'] < FOOTER_Y_MIN]
            lines = group_words_into_lines(words)

            for line_words in lines:
                tokens = words_to_tokens(line_words)
                if not tokens:
                    continue
                line_text = ' '.join(t[1] for t in tokens).strip()

                m = TABLE_RE.match(line_text)
                if m:
                    if current is not None:
                        write_table_md(bf, current)
                        names_out.append(current['name'])
                        table_count += 1
                        row_count += len(current['rows'])
                    current = {
                        'name': m.group(1).strip(),
                        'description': [],
                        'rows': [],
                        '_seen_header': False,
                    }
                    continue

                if current is None:
                    continue

                if is_column_header_line(tokens):
                    current['_seen_header'] = True
                    continue

                if not current['_seen_header']:
                    current['description'].append(line_text)
                    continue

                # Continuation line: first token starts well past Column Name.
                first_x0 = tokens[0][0]
                is_continuation = first_x0 > COL_X0[COLS[0]] + 30

                if is_continuation:
                    if current['rows']:
                        last = current['rows'][-1]
                        for x0, text in tokens:
                            col = column_for_x(x0)
                            last[col] = _append(last.get(col, ''), text)
                    continue

                row = {c: '' for c in COLS}
                for x0, text in tokens:
                    col = column_for_x(x0)
                    row[col] = _append(row[col], text)
                current['rows'].append(row)

            page.flush_cache()
            page.get_textmap.cache_clear()
            page_count += 1
            if verbose and page_count % 200 == 0:
                elapsed = time.time() - t0
                rate = page_count / elapsed
                remaining = (end - start - page_count) / rate
                print(f'  page {page_idx+1}: {page_count} processed, '
                      f'{table_count} tables flushed, '
                      f'{elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining',
                      file=sys.stderr, flush=True)

        if current is not None:
            write_table_md(bf, current)
            names_out.append(current['name'])
            table_count += 1
            row_count += len(current['rows'])

    return table_count, row_count


def assemble_final(body_path, names, out_path, title='Extracted Tables'):
    with open(out_path, 'w') as f:
        f.write(f'# {title}\n\n')
        f.write(f'Total tables: {len(names)}\n\n')
        f.write('## Table of Contents\n\n')
        for n in names:
            anchor = re.sub(r'[^a-z0-9-]', '', n.lower().replace(' ', '-'))
            f.write(f"- [{n}](#{anchor})\n")
        f.write('\n---\n\n')
        with open(body_path) as bf:
            for chunk in iter(lambda: bf.read(1 << 20), ''):
                f.write(chunk)


if __name__ == '__main__':
    body = OUTPUT_PATH + '.body.tmp'
    names = []
    t0 = time.time()
    n_tables, n_rows = parse_and_stream(body, names, verbose=True)
    print(f'Parsed {n_tables} tables, {n_rows} rows in {time.time()-t0:.1f}s',
          file=sys.stderr)
    assemble_final(body, names, OUTPUT_PATH)
    os.remove(body)
    print(f'Wrote to {OUTPUT_PATH}', file=sys.stderr)
