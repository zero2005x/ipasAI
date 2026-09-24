#!/usr/bin/env python3
"""Recover table structure lost when the PDF text was flattened.

*** STATUS: PROTOTYPE -- NOT WIRED INTO THE BUILD PIPELINE. ***

It detects real tables (e.g. L21 p.2 分層標籤表) but does NOT handle multi-line
cell wrapping reliably: a cell that wraps inside a non-first column gets split
into extra rows, which silently truncates text (e.g. "本冊涵蓋：L2110" /
"1–L21302").  Shipping its output would introduce new content errors, so it is
kept for reference only.  The tables that matter have been rewritten by hand.

See book/<VOL>/v0.3/REVIEW.md for the manual table-repair task list.

The v0.2.0 PDFs are available only as text. Their tables survive as
*column-aligned* lines: cells are separated by runs of spaces, and the column
x-positions are consistent within a table.  The skeleton builder collapsed those
runs, which turned every table into prose.

This tool rebuilds GFM tables from column alignment:

    python3 tools/recover_tables.py L21 --dry-run     # report only
    python3 tools/recover_tables.py L21              # write tables.json

Output: book/<VOL>/tables.json  — recovered tables keyed by pdf page, plus a
confidence score and the raw lines, so the result can be reviewed before use.

Detection rules
---------------
* A table is a run of >= 2 consecutive lines that all split into >= 2 columns at
  consistent character offsets.
* Column boundaries are taken from the union of split positions across the run.
* A line whose only content sits in the first column is treated as a wrapped
  continuation of the previous row's first cell.
* Prose is rejected: we require the run to have >= 2 columns in most lines and
  reject runs where any "cell" is longer than ~60 CJK chars (prose wrapped by
  indentation rather than a table).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources_extracted"

RUNNING_HEAD = re.compile(r"^iPAS\s*AI應用規劃師（中級）考綱教科書")
PAGE_FOLIO = re.compile(r"^[ivxlcdm]{1,7}$|^\d{1,3}$")
GAP = re.compile(r"\S {2,}\S")          # a column boundary candidate
MAX_CELL = 70                            # a cell longer than this is probably prose
MIN_ROWS = 3          # 兩列的多半是排版造成的巧合，不是表格


def load_pages(vol: str) -> list[str]:
    p = SRC / f"book_{vol}.json"
    if not p.exists():
        raise SystemExit(f"missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def cell_spans(line: str) -> list[tuple[int, int]]:
    """Character spans of the cells in a column-aligned line."""
    spans = []
    start = None
    prev_was_space = False
    space_run = 0
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == " ":
            space_run += 1
            i += 1
            continue
        if space_run >= 2 and start is not None:
            spans.append((start, i - space_run))
            start = i
        elif start is None:
            start = i
        space_run = 0
        i += 1
    if start is not None:
        spans.append((start, n - space_run if space_run else n))
    return spans


def strip_heads(pages: list[str]) -> list[list[tuple[str, int]]]:
    out = []
    for i, page in enumerate(pages, start=1):
        rows = []
        for raw in page.splitlines():
            s = raw.replace("\u00ad", "").rstrip()
            if not s.strip() or RUNNING_HEAD.match(s.strip()) or PAGE_FOLIO.match(s.strip()):
                continue
            rows.append((s, i))
        out.append(rows)
    return out


def find_tables(rows: list[tuple[str, int]]) -> list[dict]:
    """Locate runs of column-aligned lines and rebuild them."""
    tables = []
    i = 0
    while i < len(rows):
        line, page = rows[i]
        if not GAP.search(line):
            i += 1
            continue
        # grow a run
        j = i
        run = []
        while j < len(rows) and GAP.search(rows[j][0]):
            run.append(rows[j])
            j += 1
        if len(run) >= MIN_ROWS:
            t = build_table(run)
            if t:
                tables.append(t)
        i = j if j > i else i + 1
    return tables


def build_table(run: list[tuple[str, int]]) -> dict | None:
    """Rebuild one table from a run of aligned lines."""
    # column start positions = start of every span after the first
    starts: list[int] = []
    for line, _ in run:
        spans = cell_spans(line)
        for s, _e in spans[1:]:
            starts.append(s)
    if not starts:
        return None
    starts = sorted(set(starts))
    # cluster starts that are within 2 chars of each other
    clusters: list[list[int]] = []
    for s in starts:
        if clusters and s - clusters[-1][-1] <= 2:
            clusters[-1].append(s)
        else:
            clusters.append([s])
    bounds = [c[0] for c in clusters]
    # keep only boundaries that recur (a real table has >= 2 aligned rows)
    counts = {b: sum(1 for line, _ in run if any(abs(s - b) <= 2 for s, _ in cell_spans(line)[1:]))
              for b in bounds}
    bounds = [b for b in bounds if counts[b] >= max(2, len(run) // 3)]
    if not bounds:
        return None

    # split each line at the boundaries
    def split(line: str) -> list[str]:
        cuts = [0] + bounds + [len(line)]
        cells = []
        for a, b in zip(cuts, cuts[1:]):
            cells.append(line[a:b].strip())
        return cells

    grid: list[list[str]] = []
    for line, _ in run:
        cells = split(line)
        cells = [re.sub(r"\s{2,}", " ", c) for c in cells]
        if grid and cells[0] and not any(cells[1:]):
            # continuation of the previous row's first cell
            grid[-1][0] = (grid[-1][0] + " " + cells[0]).strip()
            continue
        grid.append(cells)

    # reject prose: too many very long cells, or single-column throughout
    widths = [len(c) for row in grid for c in row if c]
    if not widths:
        return None
    multi = sum(1 for row in grid if sum(1 for c in row if c) >= 2)
    if multi < MIN_ROWS or len(grid) < MIN_ROWS:
        return None
    # 前言／封面那種「標籤：值」的對齊不是表格
    labelish = sum(1 for row in grid if row and row[0].rstrip().endswith(("：", ":")))
    if labelish >= 2:
        return None
    # 表格的第一列通常是短標題；若首列有超長儲存格，多半是本文
    if grid and max((len(c) for c in grid[0]), default=0) > MAX_CELL:
        return None
    if max(widths) > MAX_CELL * 3:
        return None
    long_cells = sum(1 for w in widths if w > MAX_CELL)
    confidence = "high"
    if long_cells / max(1, len(widths)) > 0.35:
        confidence = "low"
    elif long_cells / max(1, len(widths)) > 0.15:
        confidence = "medium"

    return {
        "page": run[0][1],
        "columns": len(bounds) + 1,
        "rows": grid,
        "confidence": confidence,
        "raw": [l for l, _ in run],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volume")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", type=int, default=0, help="print N samples")
    args = ap.parse_args()
    vol = args.volume

    pages = load_pages(vol)
    rows = [r for page_rows in strip_heads(pages) for r in page_rows]
    tables = find_tables(rows)

    by_conf: dict[str, int] = {}
    for t in tables:
        by_conf[t["confidence"]] = by_conf.get(t["confidence"], 0) + 1
    multi_col = [t for t in tables if t["columns"] >= 2]
    print(f"{vol}: {len(tables)} 個候選區塊（>=2 欄者 {len(multi_col)}）")
    print(f"     信心分布 {by_conf}")
    print(f"     總列數 {sum(len(t['rows']) for t in tables)}")

    if args.show:
        for t in multi_col[: args.show]:
            print(f"\n--- p{t['page']} {t['columns']} 欄 {len(t['rows'])} 列 [{t['confidence']}] ---")
            for r in t["rows"][:6]:
                print("   | " + " | ".join(x[:24] for x in r))

    if not args.dry_run:
        out = ROOT / "book" / vol / "tables.json"
        out.write_text(json.dumps(tables, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n→ {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
