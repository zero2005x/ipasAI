#!/usr/bin/env python3
"""Build a structured, page-anchored Markdown skeleton for one iPAS textbook.

v0.2.0 exists only as printed PDFs -- the book sources are not available -- so
this tool reconstructs an editable, structure-aware Markdown master so that v0.3
can be edited and compiled.

Structure detection
-------------------
Chapters and sections are detected from the **body**, not from the printed table
of contents. The printed TOC in v0.2.0 is not reliable (L22's TOC omits chapters
10-13 entirely, and its section lines drift into the wrong chapter), whereas the
body headings are regular: every chapter starts at the top of a page as
"第 N章", and every section starts a line as "N.M 標題".

Usage:
    python3 tools/build_skeleton.py L21
Outputs (under book/<VOL>/):
    skeleton.md   raw v0.2.0 content, page anchors, normalised headings
    toc.json      chapter / section index (detected from the body)
    stats.json    auto-computed counts (spec: 統計數字一律由原始檔計算)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources_extracted"

RUNNING_HEAD = re.compile(r"^iPAS\s*AI應用規劃師（中級）考綱教科書")
PAGE_FOLIO = re.compile(r"^[ivxlcdm]{1,7}$|^\d{1,3}$")
DOT_LEADER = re.compile(r"(\s*\.\s*){3,}")

CH_HEAD = re.compile(r"^第\s*(\d{1,2})\s*章\s*(.*?)\s*$")
SEC_HEAD = re.compile(r"^(\d{1,2})\.(\d{1,2})\s*(\S.*?)\s*$")
APX_HEAD = re.compile(r"^附錄\s*([A-Z])[：:]\s*(.+?)\s*$")
SIM_HEAD = re.compile(r"^模擬題\s+(SIM-[A-Za-z0-9]+-[0-9]+)\s*(.*)$")

# A body section title is short; longer matches are glued body prose or table rows.
MAX_SEC_TITLE = 26
MAX_APX_TITLE = 30


def norm_line(s: str) -> str:
    s = s.replace("\u00ad", "")
    s = re.sub(r"[ \t\u3000]+", " ", s)
    return s.strip()


def load_pages(vol: str) -> list[str]:
    p = SRC / f"book_{vol}.json"
    if not p.exists():
        raise SystemExit(f"missing {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def build_body_lines(pages: list[str]) -> list[tuple[str, int, bool]]:
    """(line, pdf_page, is_toc_line).

    is_toc_line marks printed-TOC entries (dot leaders) so structure detection
    can skip them.
    """
    out: list[tuple[str, int, bool]] = []
    for i, page in enumerate(pages, start=1):
        for raw in page.splitlines():
            s = norm_line(raw)
            if not s or RUNNING_HEAD.match(s) or PAGE_FOLIO.match(s):
                continue
            out.append((s, i, bool(DOT_LEADER.search(s))))
    return out


def detect_structure(lines: list[tuple[str, int, bool]]) -> list[dict]:
    """Detect chapters, appendices and their sections from the body.

    In v0.2.0 the chapter number and its title are printed on separate lines
    ("第 1章" / "自然語言處理技術與應用"), so when the number line carries no
    title we take the next non-empty, non-TOC line.
    """
    chapters: list[dict] = []
    cur: dict | None = None
    consumed: set[int] = set()
    for idx, (s, pg, is_toc) in enumerate(lines):
        if is_toc or idx in consumed:
            continue
        m = CH_HEAD.match(s)
        if m:
            title = m.group(2).strip()
            if not title:
                for j in range(idx + 1, min(idx + 4, len(lines))):
                    nxt, npg, ntoc = lines[j]
                    if ntoc:
                        break
                    # an appendix is numbered as a chapter but is not one
                    if APX_HEAD.match(nxt):
                        title = ""
                        break
                    if SEC_HEAD.match(nxt) or CH_HEAD.match(nxt):
                        break
                    if len(nxt) <= MAX_SEC_TITLE and not nxt.endswith(("。", "，", "；")):
                        title = nxt
                        consumed.add(j)
                        break
            if not title:
                continue  # "第 N章" that merely introduces an 附錄 heading
            cur = {"kind": "chapter", "num": int(m.group(1)), "title": title,
                   "pdf_page": pg, "line": idx, "sections": [], "sims": []}
            chapters.append(cur)
            continue
        m = APX_HEAD.match(s)
        if m and len(m.group(2)) <= MAX_APX_TITLE and cur is not None:
            cur = {"kind": "appendix", "num": len(chapters) + 1, "label": m.group(1),
                   "title": m.group(2).strip(), "pdf_page": pg, "line": idx,
                   "sections": [], "sims": []}
            chapters.append(cur)
            continue
        if cur is None:
            continue
        m = SEC_HEAD.match(s)
        if m and len(m.group(3)) <= MAX_SEC_TITLE:
            title = m.group(3).strip()
            # a real section title never ends in sentence punctuation
            if not title.endswith(("。", "，", "；", "：", ",", ";")):
                cur["sections"].append({"num": f"{int(m.group(1))}.{int(m.group(2))}",
                                        "title": title, "pdf_page": pg, "line": idx})
                continue
        m = SIM_HEAD.match(s)
        if m:
            cur["sims"].append({"id": m.group(1), "pdf_page": pg, "line": idx})
    return chapters


def render(vol: str, lines: list[tuple[str, int, bool]], toc: list[dict]) -> str:
    heads: dict[int, list[str]] = {}
    for ch in toc:
        label = (f"第 {ch['num']}章 {ch['title']}" if ch["kind"] == "chapter"
                 else f"附錄 {ch['label']}：{ch['title']}")
        heads.setdefault(ch["line"], []).append(f"## {label}")
        for sec in ch["sections"]:
            heads.setdefault(sec["line"], []).append(f"### {sec['num']} {sec['title']}")
        for sim in ch["sims"]:
            heads.setdefault(sim["line"], []).append(f"#### 模擬題 {sim['id']}")

    out = [f"<!-- generated by tools/build_skeleton.py from book_{vol}.json -->",
           "<!-- RAW v0.2.0 material, page-anchored. Regenerate; do not hand-edit. -->", ""]
    for i, (s, pg, is_toc) in enumerate(lines):
        for h in heads.get(i, []):
            out.append("")
            out.append(f"<!-- pdf-page {pg} -->")
            out.append(h)
            out.append("")
        if is_toc:
            continue  # the printed TOC is redundant once structure is detected
        out.append(s)
    return "\n".join(out)


def compute_stats(lines, toc: list[dict], vol: str) -> dict:
    text = "\n".join(s for s, _, _ in lines)
    sims = re.findall(r"模擬題\s+(SIM-L\d{5}-\d{3})", text)
    by_code: dict[str, int] = {}
    for sid in sims:
        code = sid.split("-")[1]
        by_code[code] = by_code.get(code, 0) + 1
    prog = len(re.findall(r"｜\s*程式", text))
    return {
        "volume": vol,
        "sim_total": len(sims),
        "sim_by_code": dict(sorted(by_code.items())),
        "program_sim_total": prog,
        "chapters": len([c for c in toc if c["kind"] == "chapter"]),
        "appendices": len([c for c in toc if c["kind"] == "appendix"]),
        "sections": sum(len(c["sections"]) for c in toc),
        "pdf_pages": None,
    }


def main() -> int:
    vol = sys.argv[1] if len(sys.argv) > 1 else "L21"
    pages = load_pages(vol)
    lines = build_body_lines(pages)
    toc = detect_structure(lines)
    outdir = ROOT / "book" / vol
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "skeleton.md").write_text(render(vol, lines, toc), encoding="utf-8")
    (outdir / "toc.json").write_text(json.dumps(toc, ensure_ascii=False, indent=2), encoding="utf-8")
    stats = compute_stats(lines, toc, vol)
    stats["pdf_pages"] = len(pages)
    (outdir / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{vol}: {len(lines)} body lines | chapters={stats['chapters']} "
          f"appendices={stats['appendices']} sections={stats['sections']}")
    print(f"     sims={stats['sim_total']} program_sims={stats['program_sim_total']}")
    for c in toc:
        tag = f"CH{c['num']:>3}" if c["kind"] == "chapter" else f"APX{c['label']}"
        miss = 7 - len(c["sections"]) if c["kind"] == "chapter" else 0
        flag = f"  ← 缺 {miss} 節" if miss > 0 else ""
        print(f"     {tag} p{c['pdf_page']:>3} {c['title'][:34]:<36} "
              f"secs={len(c['sections'])} sims={len(c['sims'])}{flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
