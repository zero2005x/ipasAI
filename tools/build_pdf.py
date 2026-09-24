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

# 字型堆疊：Noto CJK TC 優先，其次回退到系統既有字型。
# 注意：不使用 "sans-serif"／"serif" 泛稱作為第一順位——fontconfig 在只有
# Droid Sans Fallback 的環境會讓所有字重都塌成同一個，標題與正文無法區分。
BODY_CJK = "Noto Serif TC"    # 正文用襯線（可長時間閱讀）
HEAD_CJK = "Noto Sans TC"     # 標題用黑體
BODY_LATIN = "DejaVu Serif"       # 拉丁與數字（含數學符號）
HEAD_LATIN = "DejaVu Sans"
MONO = "DejaVu Sans Mono"

# 找不到 Noto 時的候選（環境未安裝 Noto 也能編譯）
BODY_STACK = f'"{BODY_CJK}", "{BODY_LATIN}", "Droid Sans Fallback", serif'
HEAD_STACK = f'"{HEAD_CJK}", "{HEAD_LATIN}", "Droid Sans Fallback", sans-serif'
MONO_STACK = f'"{MONO}", monospace'

CSS = """
@page {
  size: A4;
  margin: 20mm 18mm 18mm 18mm;
  @bottom-center { content: counter(page); font-size: 9pt; color: #555; }
  @top-right { content: string(book-title); font-size: 8pt; color: #777; }
}
@page :first { @top-right { content: none; } @bottom-center { content: none; } }

html { font-family: %(body)s; font-size: 10.5pt; line-height: 1.75;
       text-align: justify; }
body { margin: 0; }

h1, h2, h3, h4, h5, h6 { font-family: %(head)s; line-height: 1.4;
                          text-align: left; }
h1 { string-set: book-title content(); font-size: 20pt; margin: 0 0 4mm 0; }
h2 { font-size: 16pt; border-bottom: 1.5pt solid #222; padding-bottom: 1.5mm;
     margin: 8mm 0 4mm 0; page-break-before: always; break-before: page;
     page-break-after: avoid; break-after: avoid; }
h2:first-of-type { page-break-before: avoid; break-before: avoid; }
h3 { font-size: 13pt; margin: 6mm 0 2.5mm 0; page-break-after: avoid;
     break-after: avoid; }
h4 { font-size: 11.5pt; margin: 5mm 0 2mm 0; color: #222;
     page-break-after: avoid; break-after: avoid; }

p, li { orphans: 2; widows: 2; margin: 0 0 1.6mm 0; }
ul { margin: 1.5mm 0 2.5mm 0; padding-left: 6mm; }
li { text-align: left; }

table { border-collapse: collapse; width: 100%%; margin: 3mm 0; font-size: 9.5pt;
        page-break-inside: avoid; }
th, td { border: 0.5pt solid #999; padding: 1.2mm 1.8mm; text-align: left;
         vertical-align: top; line-height: 1.5; }
th { background: #f0f0f0; font-family: %(head)s; font-weight: bold; }
caption { font-size: 9pt; color: #555; text-align: left; margin-bottom: 1mm; }

/* 行內程式碼與公式：等寬字型 + 允許在運算子後斷行，避免長式子被硬切 */
code { font-family: %(mono)s; font-size: 9.2pt; background: #f4f4f4;
       padding: 0 0.6mm; border-radius: 0.6mm;
       word-break: break-word; overflow-wrap: anywhere; }
pre { font-family: %(mono)s; font-size: 9pt; background: #f6f6f6;
      padding: 2mm 2.5mm; border-left: 2pt solid #bbb; white-space: pre-wrap;
      line-height: 1.5; page-break-inside: avoid; }
pre code { background: none; padding: 0; }

/* 數學符號：交給有完整符號覆蓋的襯線字型，不要用等寬 */
.math { font-family: "%(latin_serif)s", "%(body_cjk)s", serif;
        font-style: italic; }
.mathvar { font-family: "%(latin_serif)s", "%(body_cjk)s", serif;
           font-style: italic; }
.mathop { font-family: "%(latin_serif)s", "%(body_cjk)s", serif;
          font-style: normal; }

blockquote { margin: 3mm 0; padding: 2mm 3mm; background: #f7f7f7;
             border-left: 3pt solid #888; page-break-inside: avoid; }

/* 分層標籤：獨立一行、縮排、灰底，與正文區隔 */
.tag { font-family: %(head)s; font-size: 8.5pt; color: #444; background: #ececec;
       border: 0.5pt solid #ccc; padding: 0 1.2mm; border-radius: 0.8mm;
       display: inline-block; margin: 0 0 1.5mm 0; }

.pagebreak { page-break-after: always; break-after: page; }
.cover { text-align: center; margin-top: 60mm; }
.cover h1 { font-size: 17pt; text-align: center; line-height: 1.6; }
.cover .sub { font-size: 13pt; color: #444; margin-top: 6mm; }
.cover .meta { font-size: 10pt; color: #666; margin-top: 20mm; line-height: 2; }
""" % {"body": BODY_STACK, "head": HEAD_STACK, "mono": MONO_STACK,
       "latin_serif": BODY_LATIN, "body_cjk": BODY_CJK}

# --------------------------------------------------------- text normalisation

# PDF 擷取會在行內數學式裡插入多餘空白，例如 "( x̄ − μ₀ ) / ( s / √n )"。
# 只清掉「括號內緊鄰括號」的空白與重複空白——不動中文與英文之間該有的空格。
_MATH_SPAN = re.compile(r"\(([^()]{1,60})\)")

_CJK = r"\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef"


def tidy_math(t: str) -> str:
    """Trim redundant spaces inside parentheses that hold a formula."""
    def fix(m: re.Match) -> str:
        inner = m.group(1)
        # 只有當括號內幾乎沒有中文字時才視為數學式
        cjk = len(re.findall(f"[{_CJK}]", inner))
        if cjk > 1:
            return m.group(0)
        inner = re.sub(r"\s+", " ", inner).strip()
        inner = re.sub(r"\s*([/+=−\-×÷·^])\s*", r" \1 ", inner)
        inner = re.sub(r"\s{2,}", " ", inner).strip()
        return f"({inner})"
    for _ in range(3):  # 巢狀括號需多輪
        new = _MATH_SPAN.sub(fix, t)
        if new == t:
            break
        t = new
    return t


def tidy_line(t: str) -> str:
    """Normalise a source line before rendering."""
    t = t.replace("\u00ad", "")
    t = re.sub(r"[ \t\u3000]{2,}", " ", t)      # 壓縮重複空白
    t = re.sub(f"([{_CJK}])\\s+([，。、；：！？）】」』])", r"\1\2", t)  # 中文標點前不留空
    t = re.sub(f"([（【「『])\\s+([{_CJK}])", r"\1\2", t)                # 前括號後不留空
    t = tidy_math(t)
    return t.strip()


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
        # 允許表格儲存格內的 <br/> 換行：作者的 Markdown 用 <br/>，不應被轉義
        t = re.sub(r"&lt;br\s*/?&gt;", "<br/>", t)
        # 先保護行內程式碼，避免其中的 * 與 _ 被當成強調標記
        spans: list[str] = []

        def stash(m: re.Match) -> str:
            spans.append(m.group(1))
            return f"\x00{len(spans) - 1}\x00"

        t = re.sub(r"`([^`]+)`", stash, t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
        t = re.sub(r"\x00(\d+)\x00",
                   lambda m: f"<code>{spans[int(m.group(1))]}</code>", t)
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

        stripped = tidy_line(stripped)

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
