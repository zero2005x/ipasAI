#!/usr/bin/env python3
"""Parse an extracted iPAS textbook (book_L2x.json) into a structured
Markdown skeleton that keeps PDF page anchors.

Usage:
    python3 tools/parse_book.py L21        # writes book/L21/skeleton.md + toc.json

Design notes
------------
* Input  : sources_extracted/book_<VOL>.json  (list[str], one entry per PDF page)
* Output : book/<VOL>/skeleton.md   -- full text, page-anchored, heading-normalised
           book/<VOL>/toc.json      -- chapter/section index with page + char offsets
The skeleton is the *raw material*. Editing rules live in shared/ and per-volume
prompts; this script never rewrites prose.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources_extracted"

# ---------------------------------------------------------------- normalisation

# Running heads observed in v0.2.0, e.g.
#   "iPAS  AI應用規劃師（中級）考綱教科書         自然語言處理技術與應用"
RUNNING_HEAD = re.compile(r"^iPAS\s*AI應用規劃師（中級）考綱教科書")
FRONT_HEAD = re.compile(r"^iPAS\s*AI應用規劃師（中級）考綱教科書\s*考綱地圖")
PAGE_FOLIO = re.compile(r"^[ivxlcdm]+$|^\d{1,3}$")  # roman or arabic page number

# "第 1章" / "第  10章" possibly glued to following text
CH_HEAD = re.compile(r"^第\s*(\d+)\s*章\s*(.*)$")
# "1.1 核心概念與技術原理" possibly glued to trailing text
SEC_HEAD = re.compile(r"^(\d{1,2})\.(\d{1,2})\s+(\S[^\n]*)$")
# "模擬題 SIM-L21101-001　｜　計算題..." possibly with irregular spacing
SIM_HEAD = re.compile(r"^模擬題\s+(SIM-[A-Za-z0-9\-]+)\s*(.*)$")
# "附錄 A：政府指引速查表"
APX_HEAD = re.compile(r"^附錄\s*([A-Z])[：:]\s*(.*)$")
# "Part II"
PART_HEAD = re.compile(r"^Part\s+([IVX]+)\s*$")


def norm_ws(s: str) -> str:
    """Collapse runs of spaces, but keep single spaces."""
    return re.sub(r"[ \t\u3000]+", " ", s).strip()


def norm_line(s: str) -> str:
    """Normalise a content line, fixing the PDF's doubled-space artefacts."""
    s = s.replace("\u00ad", "")           # soft hyphen
    s = re.sub(r"[ \t\u3000]+", " ", s)   # runs of spaces -> one
    return s.strip()


def load_pages(vol: str) -> list[str]:
    p = SRC / f"book_{vol}.json"
    if not p.exists():
        raise SystemExit(f"missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- line assembly

def build_lines(pages: list[str]) -> list[tuple[str, int]]:
    """Return (line, pdf_page) with running heads and folios removed.

    Heading lines keep their raw form so the caller can split glued headings.
    """
    out: list[tuple[str, int]] = []
    for i, page in enumerate(pages, start=1):
        for raw in page.splitlines():
            s = norm_line(raw)
            if not s:
                continue
            if RUNNING_HEAD.match(s) or FRONT_HEAD.match(s):
                continue
            if PAGE_FOLIO.match(s):
                continue
            out.append((s, i))
    return out


def split_glued(text: str, sub: re.Pattern, nexts: list[re.Pattern]):
    """A heading printed at a page bottom can be glued to following text.

    Returns (heading, remainder) where remainder may be ''.
    """
    m = sub.match(text)
    if not m:
        return None, text
    return text, ""


# ---------------------------------------------------------------- main parse

def parse(vol: str):
    pages = load_pages(vol)
    lines = build_lines(pages)
    # second pass: split glued headings like "第 5章" + "AI導入評估"
    fixed: list[tuple[str, int]] = []
    for s, pg in lines:
        m = CH_HEAD.match(s)
        if m and m.group(2).strip():
            fixed.append((f"第 {m.group(1)}章", pg))
            fixed.append((m.group(2).strip(), pg))
            continue
        m2 = SEC_HEAD.match(s)
        if m2 and len(m2.group(3)) > 30 and re.match(r"^\d+\.\d+\s", m2.group(3)):
            # "1.1 核心..." unlikely; guard against table rows like "112.08 ..."
            fixed.append((s, pg))
            continue
        fixed.append((s, pg))
    lines = fixed

    toc: list[dict] = []
    cur_ch = None
    cur_sec = None
    for idx, (s, pg) in enumerate(lines):
        m = CH_HEAD.match(s)
        if m:
            cur_ch = {"kind": "chapter", "num": int(m.group(1)), "title": "", "pdf_page": pg, "line": idx, "sections": []}
            toc.append(cur_ch)
            cur_sec = None
            continue
        if cur_ch and not cur_ch["title"] and len(s) < 45 and not SEC_HEAD.match(s):
            cur_ch["title"] = s
            continue
        m = APX_HEAD.match(s)
        if m and len(s) < 45:
            cur_ch = {"kind": "appendix", "label": m.group(1), "title": s, "pdf_page": pg, "line": idx, "sections": []}
            toc.append(cur_ch)
            cur_sec = None
            continue
        m = SEC_HEAD.match(s)
        if m and len(m.group(3)) < 45 and cur_ch is not None:
            cur_sec = {"num": f"{m.group(1)}.{m.group(2)}", "title": m.group(3).strip(), "pdf_page": pg, "line": idx}
            cur_ch["sections"].append(cur_sec)
            continue
        m = SIM_HEAD.match(s)
        if m and cur_ch is not None:
            cur_ch.setdefault("sims", []).append({"id": m.group(1), "pdf_page": pg, "line": idx})
    return lines, toc


def to_markdown(lines: list[tuple[str, int]], toc: list[dict], vol: str) -> str:
    parts: list[str] = []
    parts.append(f"<!-- generated by tools/parse_book.py from book_{vol}.json -->")
    parts.append(f"<!-- RAW v0.2.0 material. Do not edit by hand: regenerate instead. -->\n")
    for s, pg in lines:
        m = CH_HEAD.match(s)
        if m:
            parts.append(f"\n<!-- pdf-page {pg} -->\n## 第 {m.group(1)}章\n")
            continue
        m = APX_HEAD.match(s)
        if m and len(s) < 45:
            parts.append(f"\n<!-- pdf-page {pg} -->\n## {s}\n")
            continue
        m = SEC_HEAD.match(s)
        if m and len(m.group(3)) < 45:
            parts.append(f"\n### {m.group(1)}.{m.group(2)} {m.group(3).strip()}\n")
            continue
        m = SIM_HEAD.match(s)
        if m:
            parts.append(f"\n#### 模擬題 {m.group(1)} {m.group(2).strip()}\n")
            continue
        parts.append(s)
    return "\n".join(parts)


def main() -> int:
    vol = sys.argv[1] if len(sys.argv) > 1 else "L21"
    lines, toc = parse(vol)
    outdir = ROOT / "book" / vol
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "skeleton.md").write_text(to_markdown(lines, toc, vol), encoding="utf-8")
    (outdir / "toc.json").write_text(json.dumps(toc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{vol}: {len(lines)} lines")
    for c in toc:
        if c["kind"] == "chapter":
            print(f"  CH{c['num']:>3} p{c['pdf_page']:>3}  {c['title'][:38]:<40} secs={len(c['sections'])} sims={len(c.get('sims', []))}")
        else:
            print(f"  APX {c['label']} p{c['pdf_page']:>3}  {c['title'][:38]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
