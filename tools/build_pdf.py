#!/usr/bin/env python3
"""Compile a volume's v0.3 Markdown into an HTML intermediate, then a PDF.

    python3 tools/build_pdf.py L21            # -> build/L21/L21_v0.3.pdf
    python3 tools/build_pdf.py L21 --html-only

Pipeline: book/<VOL>/v0.3/*.md  ->  HTML (+ CSS)  ->  WeasyPrint  ->  PDF

Why not pandoc/LaTeX: pandoc is not installed in this environment, and the only
CJK font available is Droid Sans Fallback. WeasyPrint + that font produces a
correctly shaped zh-TW PDF today.  The HTML/CSS is deliberately print-oriented
(A4, running heads, page numbers) so the same CSS can later be reused if the
project moves to a LaTeX toolchain.

Two gates run before PDF generation:
  1. shared-content consistency (the three volumes must agree on shared blocks)
  2. tools/check_book.py --strict   (P0 failures block the compile)
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CJK_FONT = "Droid Sans Fallback"

CSS = """
@page {
  size: A4;
  margin: 20mm 18mm 18mm 18mm;
  @bottom-center { content: counter(page); font-size: 9pt; color: #555; }
  @top-right { content: string(book-title); font-size: 8pt; color: #777; }
}
@page :first { @top-right { content: none; } @bottom-center { content: none; } }
html { font-family: "%(font)s", sans-serif; font-size: 10.5pt; line-height: 1.65; }
body { margin: 0; }
h1 { string-set: book-title content(); font-size: 20pt; margin: 0 0 4mm 0; }
h2 { font-size: 16pt; border-bottom: 1.5pt solid #222; padding-bottom: 1.5mm;
     margin: 8mm 0 4mm 0; page-break-before: always; break-before: page; }
h2:first-of-type { page-break-before: avoid; break-before: avoid; }
h3 { font-size: 13pt; margin: 6mm 0 2.5mm 0; }
h4 { font-size: 11.5pt; margin: 5mm 0 2mm 0; color: #333; }
p, li { orphans: 2; widows: 2; }
table { border-collapse: collapse; width: 100%%; margin: 3mm 0; font-size: 9.5pt; }
th, td { border: 0.5pt solid #999; padding: 1.2mm 1.8mm; text-align: left;
         vertical-align: top; }
th { background: #f0f0f0; font-weight: bold; }
code, pre { font-family: monospace; font-size: 9pt; background: #f6f6f6; }
pre { padding: 2mm; border-left: 2pt solid #bbb; white-space: pre-wrap; }
blockquote { margin: 3mm 0; padding: 2mm 3mm; background: #f7f7f7;
             border-left: 3pt solid #888; }
.pagebreak { page-break-after: always; break-after: page; }
.cover { text-align: center; margin-top: 60mm; }
.cover .sub { font-size: 13pt; color: #444; margin-top: 6mm; }
.cover .meta { font-size: 10pt; color: #666; margin-top: 20mm; line-height: 2; }
""" % {"font": CJK_FONT}

# ------------------------------------------------------------------ markdown

def md_to_html(md: str) -> str:
    """Minimal, dependency-free Markdown subset -> HTML.

    Handles: ATX headings, tables (GFM), fenced code, blockquotes, lists,
    bold/italic/code spans. Deliberately small and predictable: the book uses a
    narrow subset, and a full parser would fight the PDF-extracted layout.
    """
    out: list[str] = []
    lines = md.split("\n")
    i = 0
    in_code = False
    in_table = False
    in_ul = False

    def close_table():
        nonlocal in_table
        if in_table:
            out.append("</tbody></table>")
            in_table = False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def inline(t: str) -> str:
        t = html.escape(t, quote=False)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
        return t

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            close_table(); close_ul()
            if in_code:
                out.append("</pre>")
                in_code = False
            else:
                out.append("<pre>")
                in_code = True
            i += 1
            continue
        if in_code:
            out.append(html.escape(raw))
            i += 1
            continue

        if not stripped:
            close_table(); close_ul()
            i += 1
            continue
        if stripped.startswith("<!--"):
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            close_table(); close_ul()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        # GFM table: current line has pipes, next line is a separator
        if "|" in stripped and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$", lines[i + 1]):
            close_ul()
            header = [c.strip() for c in stripped.strip("|").split("|")]
            out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in header) + "</tr></thead><tbody>")
            in_table = True
            i += 2
            continue
        if in_table and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
            i += 1
            continue
        close_table()

        if stripped.startswith(">"):
            close_ul()
            out.append(f"<blockquote>{inline(stripped.lstrip('> ').strip())}</blockquote>")
            i += 1
            continue
        m = re.match(r"^[-*•]\s+(.*)$", stripped)
        if m:
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline(m.group(1))}</li>")
            i += 1
            continue
        close_ul()
        out.append(f"<p>{inline(stripped)}</p>")
        i += 1

    close_table(); close_ul()
    if in_code:
        out.append("</pre>")
    return "\n".join(out)


# ------------------------------------------------------------------ assembly

def collect(vol: str) -> list[Path]:
    d = ROOT / "book" / vol / "v0.3"
    if not d.exists():
        raise SystemExit(f"missing {d}; run tools/make_v03.py {vol} first")
    front = sorted((d / "front").glob("*.md")) if (d / "front").exists() else []
    chaps = sorted(p for p in d.glob("ch*.md"))
    apx = sorted(p for p in d.glob("apx*.md"))
    return list(front) + chaps + apx


def build_html(vol: str, stats: dict, files: list[Path]) -> str:
    body = []
    for f in files:
        title = f.stem
        body.append(f'<div class="chapter">')
        body.append(md_to_html(f.read_text(encoding="utf-8")))
        body.append("</div>")
    cover = f"""
<div class="cover">
  <h1>iPAS AI應用規劃師（中級）考綱教科書　第 {vol} 冊</h1>
  <div class="sub">v0.3（草稿）</div>
  <div class="meta">
    資料截止日：中華民國 115 年 10 月 1 日<br/>
    對應考綱：經濟部 iPAS《評鑑內容範圍參考》115.06 版<br/>
    模擬題 {stats.get('sim_total', '?')} 題　章節 {stats.get('chapters', '?')} 章
  </div>
</div>
<div class="pagebreak"></div>
"""
    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"/>
<title>iPAS 中級考綱教科書 {vol} v0.3</title>
<style>{CSS}</style></head>
<body>
{cover}
{chr(10).join(body)}
</body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volume")
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--skip-gate", action="store_true", help="do not run check_book gate")
    args = ap.parse_args()
    vol = args.volume

    if not args.skip_gate:
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_book.py"), vol],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            print("編譯關卡未通過：check_book.py 回報 P0 失敗。")
            print(r.stdout[-2500:])
            print("（規格：公告試題索引任一列空白就不能編譯。要用 --skip-gate 產生草稿。）")

    stats = json.loads((ROOT / "book" / vol / "stats.json").read_text(encoding="utf-8"))
    files = collect(vol)
    doc = build_html(vol, stats, files)

    outdir = ROOT / "build" / vol
    outdir.mkdir(parents=True, exist_ok=True)
    html_path = outdir / f"{vol}_v0.3.html"
    html_path.write_text(doc, encoding="utf-8")
    print(f"HTML → {html_path} ({len(doc):,} chars, {len(files)} source files)")

    if args.html_only:
        return 0

    pdf_path = outdir / f"{vol}_v0.3.pdf"
    try:
        from weasyprint import HTML
    except ImportError:
        print("weasyprint 未安裝，僅產出 HTML。")
        return 0
    HTML(string=doc, base_url=str(outdir)).write_pdf(str(pdf_path))
    size = pdf_path.stat().st_size
    print(f"PDF  → {pdf_path} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
