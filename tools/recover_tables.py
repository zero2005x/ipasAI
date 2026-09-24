#!/usr/bin/env python3
"""Recover table structure flattened by PDF extraction.

    python3 tools/recover_tables.py L21                # 稽核摘要
    python3 tools/recover_tables.py L21 --show 4       # 看重建結果
    python3 tools/recover_tables.py L21 --report       # 完整稽核報告（原文 vs 重建）

The problem
-----------
Tables survive as column-aligned text: cells sit at repeated character offsets
separated by runs of spaces. Two things make naive parsing fail:

1. **Spaces inside a cell.** A cell may itself contain a wide gap (e.g.
   "風險識別、安全與合規性、AI倫理、負責任  AI"), so "split on 2+ spaces" invents
   phantom columns.
2. **Wrapped cells.** A cell too wide for its column wraps to the next line, and
   that line often starts at column 0 -- indistinguishable from a new row unless
   you know where the columns are.

This is circular: you need the columns to join wrapped cells, but wrapped lines
pollute the column estimate.

The method
----------
Column starts are found by voting with each line's **last** segment only:

    for every line, the last whitespace-separated segment begins at a column start

Leading segments are either intra-cell wraps (mid-line continuation of a wide
cell) or deliberate indentation, so they are not column starts; the *last* segment
is always the start of the final populated column. Voting these offsets and keeping
the ones that recur across rows recovers the true column set without being fooled
by intra-cell gaps.

With columns known, wrapped cells are joined two ways: a cell that runs into the
next column's edge was cut off, and a cell whose text ends mid-sentence continues
on the next line.

Safety
------
Every raw line must appear verbatim in the rebuilt grid, otherwise the table is
discarded. This guarantees the tool can never silently drop or reorder content --
a rejected table simply stays as text.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources_extracted"

RUNNING_HEAD = re.compile(r"^iPAS\s*AI應用規劃師（中級）考綱教科書")
PAGE_FOLIO = re.compile(r"^[ivxlcdm]{1,7}$|^\d{1,3}$")
DOT_LEADER = re.compile(r"(\s*\.\s*){3,}")

MIN_ROWS = 3
MIN_COLS = 2
MAX_CELL = 120
TOL = 3                      # offsets within this many chars are the same column
MIN_COL_W = 6                # a column narrower than this is noise, not a column
SENT_END = ("。", "！", "？", "；", "：", ")", "）", "】", "」", "》", "%", "％", "，")


def normalise(line: str) -> str:
    return line.replace("\u00ad", "").replace("\t", "    ").rstrip()


def segments(line: str) -> list[tuple[int, int]]:
    """Whitespace-separated segments, each possibly spanning single spaces."""
    return [(m.start(), m.end()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def infer_columns(lines: list[str]) -> list[int]:
    """Column start offsets, voted with adjacent-segment gaps.

    For each line the gap between segment i and i+1 is a *candidate* column
    boundary (intra-cell gaps are candidates too). A real column boundary is one
    that recurs on many lines **at a consistent offset**; an intra-cell gap lands
    at a different offset each time because the text before it differs in length.
    Requiring the vote at an exact offset is what removes the phantom columns.
    """
    votes: Counter[int] = Counter()
    for line in lines:
        segs = segments(line)
        for (_s1, e1), (s2, _e2) in zip(segs, segs[1:]):
            votes[s2] += 1                      # gap starts at s2, ends at e1
    if not votes:
        return []
    multi = sum(1 for line in lines if len(segments(line)) >= 2)
    need = 2
    starts = sorted(s for s, n in votes.items() if n >= need and s > 0)
    # merge offsets that are within TOL of each other
    merged: list[int] = []
    for s in starts:
        if merged and s - merged[-1] <= TOL:
            continue
        merged.append(s)
    # drop columns that are too narrow to hold anything
    out: list[int] = []
    for i, s in enumerate(merged):
        nxt = merged[i + 1] if i + 1 < len(merged) else 10 ** 6
        if nxt - s >= MIN_COL_W:
            out.append(s)
    return out


def classify(line: str, bounds: list[int]) -> list[tuple[int, int, int, str]]:
    """(column_index, start, end, text) for each segment of a line."""
    out = []
    for s, e in segments(line):
        col = 0
        for i, b in enumerate(bounds):
            if s >= b - 1:
                col = i
        out.append((col, s, e, line[s:e].strip()))
    return out


SECTION_HEAD = re.compile(r"^\d+(?:\.\d+)*\s*\S")


def looks_tabular(line: str) -> bool:
    """Heuristic: is this single-segment line plausibly a wrapped table cell?

    Section headings ("7.1核心概念與技術原理"), list markers and page furniture are
    not, and absorbing them corrupts the grid.
    """
    s = line.strip()
    if not s:
        return False
    if SECTION_HEAD.match(s):
        return False
    if s.startswith(("•", "-", "*", "第", "附錄")):
        return False
    return True


def build_table(raw: list[tuple[str, int]]) -> dict | None:
    lines = [r[0] for r in raw]
    starts = infer_columns(lines)
    if len(starts) < MIN_COLS - 1:
        return None
    bounds = [0] + starts
    ncols = len(bounds)

    grid: list[list[str]] = []
    uncertain = 0

    for line in lines:
        cs = classify(line, bounds)
        if not cs:
            continue

        # Which column does this line belong to?
        #   * a segment that runs up to the next column's edge was CUT OFF, so the
        #     following line continues it;
        #   * otherwise the line starts a new row.
        # Only column geometry decides this. Sentence punctuation must NOT decide it:
        # a normal row such as "資料截止日：中華民國 115年10月1日" has no full stop,
        # and treating "no full stop" as "unfinished" collapses whole tables into one row.
        cont_col = None
        for col, _s, e, text in cs:
            if col + 1 < ncols and text and e >= bounds[col + 1] - 2:
                cont_col = col
        if cont_col is None and len(cs) == 1 and grid:
            col = cs[0][0]
            prev = grid[-1][col] if col < len(grid[-1]) else ""
            # a lone segment sitting in a later column continues that column
            if col > 0 and prev:
                cont_col = col

        if cont_col is not None and grid:
            for col, _s, _e, text in cs:
                tgt = cont_col if len(cs) == 1 else col
                while len(grid[-1]) <= tgt:
                    grid[-1].append("")
                grid[-1][tgt] = (grid[-1][tgt] + text).strip()
            continue

        if len(cs) == 1 and grid and any(grid[-1]):
            uncertain += 1

        row = [""] * ncols
        for col, _s, _e, text in cs:
            if col < ncols:
                row[col] = (row[col] + " " + text).strip() if row[col] else text
        grid.append(row)

    if len(grid) < MIN_ROWS:
        return None
    widths = [len(c) for r in grid for c in r if c]
    if not widths or max(widths) > MAX_CELL * 3:
        return None

    # hard guard: nothing may be lost or reordered
    def squash(s: str) -> str:
        return re.sub(r"\s+", "", s)

    joined = squash("".join(c for r in grid for c in r))
    pos = -1
    for line in lines:
        n = squash(line)
        if not n:
            continue
        at = joined.find(n)
        if at < 0 or at < pos:
            return None      # 內容遺失或次序被打亂 -> 放棄，維持原文字
        pos = at

    long_ratio = sum(1 for w in widths if w > MAX_CELL) / len(widths)
    conf = "high"
    if uncertain > len(grid) // 2 or long_ratio > 0.30:
        conf = "low"
    elif long_ratio > 0.12:
        conf = "medium"
    return {"page": raw[0][1], "columns": ncols, "rows": grid,
            "confidence": conf, "uncertain": uncertain, "raw": lines}


def finished(text: str) -> bool:
    """Does the cell's text look complete (so the next line is a new row)?"""
    s = text.rstrip()
    if not s:
        return False
    return s.endswith(SENT_END) and not s.endswith(("，", "、", "（", "：", "/"))


def load(vol: str) -> list[tuple[str, int]]:
    p = SRC / f"book_{vol}.json"
    if not p.exists():
        raise SystemExit(f"missing {p}")
    pages = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for i, page in enumerate(pages, start=1):
        for line in page.splitlines():
            s = normalise(line)
            if not s.strip() or RUNNING_HEAD.match(s.strip()) or PAGE_FOLIO.match(s.strip()):
                continue
            if DOT_LEADER.search(s):
                continue
            out.append((s, i))
    return out


def find_tables(rows: list[tuple[str, int]]) -> list[dict]:
    """Segment into blocks of consecutive multi-segment lines.

    Trailing single-segment lines are absorbed only while they keep belonging to
    the table: at most 2 in a row, and never more than 12 total. Without these
    caps a table bleeds into the prose (or the next table) that follows it, which
    is what produced nonsense grids earlier.
    """
    tables, i = [], 0
    while i < len(rows):
        if len(segments(rows[i][0])) < 2:
            i += 1
            continue
        j, run = i, []
        single_run = absorbed = 0
        while j < len(rows):
            n = len(segments(rows[j][0]))
            if n >= 2:
                run.append(rows[j]); j += 1
                single_run = 0
                continue
            if run and single_run < 2 and absorbed < 12 and looks_tabular(rows[j][0]):
                run.append(rows[j]); j += 1
                single_run += 1; absorbed += 1
                continue
            break
        if len(run) >= MIN_ROWS:
            t = build_table(run)
            if t:
                tables.append(t)
        i = max(j, i + 1)
    return tables


def render_md(t: dict) -> str:
    head = t["rows"][0]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in t["rows"][1:]:
        r = (r + [""] * len(head))[: len(head)]
        out.append("| " + " | ".join(c.replace("|", "\\|") for c in r) + " |")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volume")
    ap.add_argument("--show", type=int, default=0)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--emit-json", action="store_true")
    args = ap.parse_args()

    tables = find_tables(load(args.volume))
    conf = Counter(t["confidence"] for t in tables)
    print(f"{args.volume}: {len(tables)} 個表格　信心 {dict(conf)}"
          f"　低信心 {conf.get('low', 0)} 需人工覆核")
    for t in tables[: args.show]:
        print(f"\n--- p{t['page']}　{t['columns']} 欄 × {len(t['rows'])} 列　[{t['confidence']}] ---")
        print(render_md(t))
    if args.report:
        out = ROOT / "book" / args.volume / "table_recovery_report.md"
        L = [f"# {args.volume} 表格重建稽核報告", "",
             f"- 候選表格：{len(tables)}", f"- 信心分布：{dict(conf)}",
             f"- 低信心（需人工覆核）：{conf.get('low', 0)}", ""]
        for t in tables:
            L.append(f"## p{t['page']}　{t['columns']} 欄 × {len(t['rows'])} 列　`{t['confidence']}`")
            L += ["", "原文：", "```"] + t["raw"][:16] + ["```", "", "重建：", "", render_md(t), ""]
        out.write_text("\n".join(L), encoding="utf-8")
        print(f"→ {out}")
    if args.emit_json:
        (ROOT / "book" / args.volume / "tables.json").write_text(
            json.dumps(tables, ensure_ascii=False, indent=2), encoding="utf-8")
        print("→ tables.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
