#!/usr/bin/env python3
"""Probe a PDF to see whether column-header word x-coordinates are stable
across pages. If they are, the pdf-positional-tables skill applies.

Run with the pdfplumber interpreter:
    /root/.local/share/pipx/venvs/pdfplumber/bin/python probe_columns.py input.pdf

Optional: pass space-separated header words to require, e.g.:
    probe_columns.py input.pdf "Column Name" "Data Type" Notes
"""
import sys
import pdfplumber


def probe(pdf_path, required_words=None):
    if required_words is None:
        required_words = ['Column', 'Name', 'Data', 'Type', 'Notes']

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        # Sample 10 pages spread across the document, plus first content pages.
        sample_idxs = sorted(set(
            list(range(min(10, total)))
            + [int(total * f) for f in (0.1, 0.25, 0.5, 0.75, 0.9, 0.99)]
        ))
        sample_idxs = [i for i in sample_idxs if i < total]

        rows = []
        for idx in sample_idxs:
            page = pdf.pages[idx]
            words = page.extract_words(keep_blank_chars=False, use_text_flow=True)
            page.flush_cache()

            # Find a y-line that contains all required header words
            from collections import defaultdict
            by_top = defaultdict(list)
            for w in words:
                # Bucket by ~1pt y precision
                by_top[round(w['top'] * 2) / 2].append(w)

            picked = None
            for top, ws in by_top.items():
                texts = {w['text'] for w in ws}
                if all(rw in texts for rw in required_words):
                    picked = sorted(ws, key=lambda w: w['x0'])
                    break

            if picked:
                # Print x0 of each occurrence of each required word, in left-to-right order.
                line = ' '.join(w['text'] for w in picked)
                rows.append((idx + 1, line, [(w['text'], round(w['x0'], 2)) for w in picked]))
            else:
                rows.append((idx + 1, None, None))

    print(f'Sampled {len(rows)} of {total} pages.\n')
    found_pages = [r for r in rows if r[1]]
    if not found_pages:
        print('No column-header line found on any sampled page. '
              'This skill probably does not apply. Inspect the PDF manually.')
        return

    print('First found header line (full text):')
    print(f'  Page {found_pages[0][0]}: {found_pages[0][1]}\n')

    # Extract the header anchor positions by collecting just the required words on each page.
    print(f'x-coordinates of {required_words} across sampled pages:')
    print(f'{"page":>6}  ' + '  '.join(f'{w:>14}' for w in required_words))
    for page_no, line, positions in found_pages:
        if not positions:
            continue
        # Map the LAST occurrence of each required word (cope with duplicates)
        x_by_word = {}
        for txt, x in positions:
            if txt in required_words:
                x_by_word[txt] = x
        cells = []
        for w in required_words:
            cells.append(f'{x_by_word.get(w, "—"):>14}')
        print(f'{page_no:>6}  ' + '  '.join(cells))

    # Stability check: are values within 1pt of each other?
    print()
    stable = True
    for w in required_words:
        xs = [
            next((x for t, x in positions if t == w), None)
            for _, _, positions in found_pages if positions
        ]
        xs = [x for x in xs if x is not None]
        if not xs:
            continue
        spread = max(xs) - min(xs)
        marker = 'STABLE' if spread <= 1.0 else 'UNSTABLE'
        if spread > 1.0:
            stable = False
        print(f'  {w}: min={min(xs):.2f} max={max(xs):.2f} spread={spread:.2f}  -> {marker}')

    print()
    if stable:
        print('All probed columns are stable across pages. The skill applies — '
              'copy these x0 values into COL_X0 in parse_positional_tables.py.')
    else:
        print('Column positions vary across pages. This skill may not apply, '
              'or your required-words list may need adjustment.')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: probe_columns.py <pdf> [required_word ...]', file=sys.stderr)
        sys.exit(2)
    pdf_path = sys.argv[1]
    required = sys.argv[2:] or None
    probe(pdf_path, required)
