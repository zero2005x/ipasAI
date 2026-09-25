#!/usr/bin/env python3
"""Compile a volume's v0.3 Markdown into an HTML intermediate, then a PDF.

    python3 tools/build_pdf.py L21            # -> build/L21/L21_v0.3.pdf
    python3 tools/build_pdf.py L21 --draft  # -> clearly labelled review PDF
    python3 tools/build_pdf.py L21 --html-only

Pipeline: book/<VOL>/v0.3/*.md -> HTML (+ CSS) -> WeasyPrint/Chrome -> PDF

The HTML/CSS is print-oriented (A4, page numbers). WeasyPrint is preferred
when present; Chrome or Edge headless is used on Windows without WeasyPrint.

The check_book gate blocks ordinary output when unresolved errors remain.
--draft writes separate, visibly labelled review files while preserving that
release gate.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from book_files import read_expanded, render_stats, volume_files  # noqa: E402

# 字型堆疊：Noto CJK TC 優先，其次回退到系統既有字型。
BODY_CJK = "Noto Serif TC"    # 正文用襯線（可長時間閱讀）
HEAD_CJK = "Noto Sans TC"     # 標題用黑體
BODY_LATIN = "DejaVu Serif"       # 拉丁與數字（含數學符號）
HEAD_LATIN = "DejaVu Sans"
MONO = "DejaVu Sans Mono"

BODY_STACK = f'"{BODY_CJK}", "{BODY_LATIN}", "Droid Sans Fallback", serif'
HEAD_STACK = f'"{HEAD_CJK}", "{HEAD_LATIN}", "Droid Sans Fallback", sans-serif'
MONO_STACK = f'"{MONO}", monospace'

CSS = """
@page {
  size: A4;
  margin: 20mm 18mm 18mm 18mm;
  @bottom-center { content: counter(page); font-size: 9pt; color: #667085; font-family: %(head)s; }
  @top-right { content: string(book-title); font-size: 8pt; color: #667085; font-family: %(head)s; }
}
@page :first { @top-right { content: none; } @bottom-center { content: none; } }

:root {
  --primary: #0F5C6E;
  --primary-light: #EAF3F5;
  --danger: #B42318;
  --danger-light: #FDECEA;
  --success: #1E7B4F;
  --success-light: #E8F5EE;
  --amber: #B45309;
  --amber-light: #FFF4E5;
  --gray: #667085;
  --gray-light: #F8F9FA;
  --body-font: %(body)s;
  --head-font: %(head)s;
  --mono-font: %(mono)s;
}

html {
  font-family: %(body)s;
  font-size: 10.5pt;
  line-height: 1.75;
  color: #1D2939;
  text-align: justify;
}
body { margin: 0; }

h1, h2, h3, h4, h5, h6 {
  font-family: %(head)s;
  line-height: 1.4;
  text-align: left;
  color: #1D2939;
}
h1 { string-set: book-title content(); font-size: 20pt; margin: 0 0 4mm 0; color: #0F5C6E; }
h2 {
  font-size: 16pt;
  border-bottom: 1.5pt solid #0F5C6E;
  padding-bottom: 1.5mm;
  margin: 0 0 4mm 0;
  page-break-after: avoid;
  break-after: avoid;
}
.chapter { page-break-before: always; break-before: page; }

/* Chapter & Front Header */
.chapter-header {
  margin: 6mm 0 5mm 0;
  page-break-after: avoid;
  break-after: avoid;
}
.chapter-num {
  font-family: %(head)s;
  font-size: 11pt;
  font-weight: bold;
  letter-spacing: 2px;
  color: #0F5C6E;
  margin-bottom: 1.5mm;
}
.chapter-title {
  font-size: 17pt;
  font-weight: bold;
  color: #1D2939;
  border-bottom: none;
  padding-bottom: 0;
  margin: 0 0 2.5mm 0;
}
.chapter-bar {
  height: 2.5pt;
  background: #0F5C6E;
  border-radius: 1pt;
  margin-bottom: 4mm;
}
.front-header {
  margin: 6mm 0 4mm 0;
  page-break-after: avoid;
  break-after: avoid;
}
.front-title {
  font-size: 15pt;
  font-weight: bold;
  color: #0F5C6E;
  border-bottom: 1.5pt solid #0F5C6E;
  padding-bottom: 1.5mm;
  margin: 0 0 3mm 0;
}

h3 {
  font-size: 13pt;
  margin: 6mm 0 2.5mm 0;
  padding-left: 2.5mm;
  border-left: 3pt solid #0F5C6E;
  page-break-after: avoid;
  break-after: avoid;
}
h3.h3-trap {
  border-left-color: #B42318;
  color: #B42318;
}
h3.h3-gov {
  border-left-color: #0F5C6E;
  color: #0F5C6E;
}
h4 {
  font-size: 11.5pt;
  margin: 5mm 0 2mm 0;
  color: #1D2939;
  page-break-after: avoid;
  break-after: avoid;
}
h4 .badge {
  margin-left: 2mm;
}

p, li { orphans: 2; widows: 2; margin: 0 0 2.2mm 0; }
ul, ol { margin: 1.5mm 0 2.5mm 0; padding-left: 6mm; }
li { text-align: left; margin-bottom: 1mm; }
li.li-highlight {
  background: #FFF9E6;
  border-left: 2pt solid #B45309;
  padding: 1mm 2.5mm;
  border-radius: 0.8mm;
  list-style-position: inside;
}

/* Learning goals */
ol.learning-goals {
  background: #F8FAFB;
  border-left: 2.5pt solid #0F5C6E;
  padding: 2.5mm 3.5mm 2.5mm 7mm;
  border-radius: 0 1.5mm 1.5mm 0;
  margin: 2mm 0 4mm 0;
}
ol.learning-goals li {
  margin-bottom: 1.5mm;
  color: #344054;
}

/* Tables */
table {
  border-collapse: collapse;
  width: 100%%;
  margin: 3.5mm 0;
  font-size: 9.5pt;
  page-break-inside: avoid;
  break-inside: avoid;
}
table.long-table {
  page-break-inside: auto;
  break-inside: auto;
}
table.long-table tr {
  page-break-inside: avoid;
  break-inside: avoid;
}
table.index-table {
  font-size: 9pt;
}
th, td {
  border: 0.5pt solid #D0D5DD;
  padding: 1.5mm 2mm;
  text-align: left;
  vertical-align: top;
  line-height: 1.5;
}
th {
  background: #EAF3F5;
  color: #0F5C6E;
  font-family: %(head)s;
  font-weight: bold;
  border-bottom: 1.5pt solid #0F5C6E;
}
tbody tr:nth-child(even) td {
  background: #F8FAFB;
}
caption {
  font-family: %(head)s;
  font-size: 10pt;
  font-weight: bold;
  color: #0F5C6E;
  text-align: left;
  margin-bottom: 1.5mm;
}
.nowrap {
  white-space: nowrap;
}

/* Info card table (章節識別卡) */
table.info-card-table {
  border: 1pt solid #D0D5DD;
  border-radius: 1.5mm;
  overflow: hidden;
  margin: 2mm 0 4mm 0;
}
table.info-card-table thead {
  display: none;
}
table.info-card-table td:first-child {
  width: 22%%;
  background: #EAF3F5;
  color: #0F5C6E;
  font-family: %(head)s;
  font-weight: bold;
  white-space: nowrap;
  border-right: 1pt solid #E4E7EC;
}
table.info-card-table td:last-child {
  background: #FFFFFF;
}

/* Code */
code {
  font-family: %(mono)s;
  font-size: 9.2pt;
  background: #F2F4F7;
  color: #0F5C6E;
  padding: 0.2mm 0.8mm;
  border-radius: 0.6mm;
  word-break: break-word;
  overflow-wrap: anywhere;
}
pre {
  font-family: %(mono)s;
  font-size: 9pt;
  background: #F8F9FA;
  padding: 2.5mm 3.5mm;
  border-left: 2.5pt solid #0F5C6E;
  white-space: pre-wrap;
  line-height: 1.5;
  page-break-inside: avoid;
  break-inside: avoid;
  border-radius: 0 1.5mm 1.5mm 0;
  position: relative;
  margin: 3mm 0;
}
pre code {
  background: none;
  padding: 0;
  color: inherit;
}
pre[data-lang]::before {
  content: attr(data-lang);
  position: absolute;
  top: 1mm;
  right: 2.5mm;
  font-size: 7.5pt;
  font-family: %(head)s;
  font-weight: bold;
  color: #98A2B3;
  letter-spacing: 0.5px;
}

/* Math */
.math, .mathvar {
  font-family: "%(latin_serif)s", "%(body_cjk)s", serif;
  font-style: italic;
}
.mathop {
  font-family: "%(latin_serif)s", "%(body_cjk)s", serif;
  font-style: normal;
}

blockquote {
  margin: 3mm 0;
  padding: 2mm 3mm;
  background: #F8F9FA;
  border-left: 3pt solid #667085;
  page-break-inside: avoid;
  break-inside: avoid;
}

/* Badges */
.badge {
  font-family: %(head)s;
  font-size: 8pt;
  font-weight: bold;
  line-height: 1;
  padding: 0.8mm 2mm;
  border-radius: 0.8mm;
  display: inline-block;
  vertical-align: middle;
}
.badge-core {
  background: #0F5C6E;
  color: #FFFFFF;
  border: 0.5pt solid #0F5C6E;
}
.badge-supp {
  background: #FFFFFF;
  color: #0F5C6E;
  border: 1pt solid #0F5C6E;
}
.badge-ext {
  background: #FFFFFF;
  color: #667085;
  border: 1pt solid #98A2B3;
}
.badge-ver {
  background: #FFF4E5;
  color: #B45309;
  border: 0.8pt solid #B45309;
}
.badge-ans {
  background: #0F5C6E;
  color: #FFFFFF;
  font-size: 9.5pt;
  padding: 1mm 3mm;
  border-radius: 1mm;
}

/* Callouts */
.callout {
  border-radius: 1.5mm;
  padding: 2.5mm 3.5mm;
  margin: 3.5mm 0;
  page-break-inside: avoid;
  break-inside: avoid;
}
.callout-header {
  font-family: %(head)s;
  font-weight: bold;
  font-size: 10pt;
  margin-bottom: 1.5mm;
  display: flex;
  align-items: center;
}
.callout-icon {
  margin-right: 1.8mm;
  font-size: 11pt;
}
.callout-trap {
  background: #FDECEA;
  border-left: 3.5pt solid #B42318;
}
.callout-trap .callout-header {
  color: #B42318;
}
.callout-key {
  background: #EAF3F5;
  border-left: 3.5pt solid #0F5C6E;
}
.callout-key .callout-header {
  color: #0F5C6E;
}
.callout-tip {
  background: #E8F5EE;
  border-left: 3.5pt solid #1E7B4F;
}
.callout-tip .callout-header {
  color: #1E7B4F;
}
.callout-ext {
  background: #F4F5F7;
  border-left: 3.5pt solid #667085;
}
.callout-ext .callout-header {
  color: #475467;
}
.callout-note {
  background: #F0F4F8;
  border-left: 3.5pt solid #4A6572;
}
.callout-note .callout-header {
  color: #344054;
}

/* Section boxes (考點補丁、學習指引補充、共用模組) */
.section-box {
  margin: 4mm 0;
  padding: 3mm 4mm;
  border-radius: 1.5mm;
  page-break-inside: auto;
  break-inside: auto;
}
.box-patch {
  background: #F4F9FA;
  border-left: 3.5pt solid #0F5C6E;
}
.box-guide {
  background: #F5F7F8;
  border-left: 3.5pt solid #4A6572;
}
.box-module {
  background: #F4F5FB;
  border-left: 3.5pt solid #5C6BC0;
}

/* Simulation Question Cards */
.sim-card {
  background: #F8FAFB;
  border-left: 3.5pt solid #0F5C6E;
  border-radius: 2mm;
  padding: 3.5mm 4.5mm;
  margin: 4.5mm 0;
  page-break-inside: avoid;
  break-inside: avoid;
}
.sim-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 2mm;
}
.sim-title {
  margin: 0;
  font-size: 11.5pt;
  color: #0F5C6E;
  font-weight: bold;
}
.sim-hint {
  font-size: 8.5pt;
  color: #667085;
  font-family: %(head)s;
}
.sim-meta {
  margin-bottom: 2.5mm;
}
.sim-tag {
  display: inline-block;
  font-family: %(head)s;
  font-size: 8pt;
  color: #344054;
  background: #EAF3F5;
  padding: 0.5mm 2mm;
  border-radius: 0.8mm;
  margin-right: 1.5mm;
}
.sim-options {
  margin-top: 3mm;
  page-break-inside: avoid;
  break-inside: avoid;
}
.sim-opt {
  display: flex;
  align-items: flex-start;
  margin-bottom: 1.8mm;
  line-height: 1.6;
}
.sim-opt:last-child {
  margin-bottom: 0;
}
.opt-label {
  font-family: %(head)s;
  font-weight: bold;
  color: #0F5C6E;
  min-width: 7mm;
  flex-shrink: 0;
}
.opt-text {
  flex-grow: 1;
}

/* Simulation Answers Section */
.sim-answers-section {
  margin-top: 8mm;
  padding-top: 4mm;
  border-top: 1.5pt solid #0F5C6E;
  page-break-before: auto;
  break-before: auto;
}
.ans-section-title {
  color: #0F5C6E;
  border-bottom: 1pt solid #0F5C6E;
  padding-bottom: 2mm;
  margin-bottom: 4mm;
}
.ans-set-title {
  color: #1D2939;
  margin: 5mm 0 3mm 0;
  font-size: 11pt;
}
.sim-ans-item {
  margin-bottom: 5mm;
  padding-bottom: 3.5mm;
  border-bottom: 0.5pt dashed #D0D5DD;
  page-break-inside: avoid;
  break-inside: avoid;
}
.sim-ans-item:last-child {
  border-bottom: none;
}
.sim-ans-header {
  margin-bottom: 2mm;
  display: flex;
  align-items: center;
}
.sim-ans-id {
  font-family: %(head)s;
  font-weight: bold;
  font-size: 11pt;
  color: #1D2939;
  margin-right: 3mm;
}
.sim-ans-body {
  font-size: 10pt;
  line-height: 1.65;
  color: #344054;
}
.sim-ans-body p {
  margin-bottom: 1.5mm;
}

.pagebreak { page-break-after: always; break-after: page; }
.keep { page-break-inside: avoid; break-inside: avoid; }
ul.cont, ol.cont { margin-top: -1.2mm; }
.cover { text-align: center; margin-top: 60mm; }
.cover h1 { font-size: 17pt; text-align: center; line-height: 1.6; }
.cover .sub { font-size: 13pt; color: #444; margin-top: 6mm; }
.cover .meta { font-size: 10pt; color: #666; margin-top: 20mm; line-height: 2; }
""" % {"body": BODY_STACK, "head": HEAD_STACK, "mono": MONO_STACK,
       "latin_serif": BODY_LATIN, "body_cjk": BODY_CJK}

# --------------------------------------------------------- text normalisation

_MATH_SPAN = re.compile(r"\(([^()]{1,60})\)")
_CJK = r"\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef"
CJK_CHAR = r'[\u4e00-\u9fff\u3400-\u4dbf]'
LATIN_NUM = r'[A-Za-z0-9]'
ID_PATTERN = re.compile(r'\b((?:OFFICIAL|GUIDE|ERR|SIM|SET|GOV|IPAS)[-‑][A-Za-z0-9\-‑]+)\b')


def tidy_math(t: str) -> str:
    """Trim redundant spaces inside parentheses that hold a formula."""
    def fix(m: re.Match) -> str:
        inner = m.group(1)
        if (m.start() > 0 and t[m.start() - 1] == "]") or inner.startswith(("http://", "https://")):
            return m.group(0)
        cjk = len(re.findall(f"[{_CJK}]", inner))
        if cjk > 1:
            return m.group(0)
        inner = re.sub(r"\s+", " ", inner).strip()
        inner = re.sub(r"\s*([/+=−\-×÷·^])\s*", r" \1 ", inner)
        inner = re.sub(r"\s{2,}", " ", inner).strip()
        return f"({inner})"
    for _ in range(3):
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


def add_cjk_spacing(text: str) -> str:
    """Insert U+200A hair space between CJK ideographs and adjacent Latin/digits."""
    tokens = re.split(r'(<[^>]+>|\x00\d+\x00)', text)
    for i, tok in enumerate(tokens):
        if tok.startswith(('<', '\x00')):
            continue
        tok = re.sub(f'({CJK_CHAR})({LATIN_NUM})', lambda m: m.group(1) + '\u200a' + m.group(2), tok)
        tok = re.sub(f'({LATIN_NUM})({CJK_CHAR})', lambda m: m.group(1) + '\u200a' + m.group(2), tok)
        tokens[i] = tok
    return ''.join(tokens)


def calc_visual_width(text: str) -> int:
    """Calculate visual width: full-width chars count 2, ASCII/half-width count 1."""
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[`*]', '', text)
    w = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ('F', 'W') or 0x4e00 <= ord(ch) <= 0x9fff:
            w += 2
        else:
            w += 1
    return w


def inline(t: str) -> str:
    """Format inline Markdown into HTML spans, badges, code, and links."""
    t = html.escape(t, quote=False)
    t = re.sub(r"&lt;br\s*/?&gt;", "<br/>", t)
    spans: list[str] = []

    def stash(m: re.Match) -> str:
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    t = re.sub(r"`([^`]+)`", stash, t)
    t = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        lambda m: f'<a href="{html.escape(html.unescape(m.group(2)), quote=True)}">{m.group(1)}</a>',
        t,
    )
    # Wrap IDs with nowrap span
    t = ID_PATTERN.sub(r'<span class="nowrap">\1</span>', t)
    # Tier badges
    t = re.sub(r"（產業延伸）", r'<span class="badge badge-ext">產業延伸</span>', t)
    t = re.sub(r"\*\*版本敏感\*\*", r'<span class="badge badge-ver">版本敏感</span>', t)
    t = re.sub(r"(?<![<\w])版本敏感(?![>\w])", r'<span class="badge badge-ver">版本敏感</span>', t)
    # Bold & Italic
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    # CJK spacing
    t = add_cjk_spacing(t)
    # Restore code
    t = re.sub(r"\x00(\d+)\x00",
               lambda m: f"<code>{spans[int(m.group(1))]}</code>", t)
    return t


def format_table(header: list[str], rows: list[list[str]], caption: str = None,
                 is_info_card: bool = False, is_index: bool = False) -> str:
    """Render a table with calculated colgroup widths, nowrap columns, and classes."""
    num_cols = len(header)
    for r in rows:
        if len(r) > num_cols:
            num_cols = len(r)
    header = header + [''] * (num_cols - len(header))
    padded_rows = [r + [''] * (num_cols - len(r)) for r in rows]

    col_max = [0] * num_cols
    col_avg = [0.0] * num_cols
    nowrap_cols = set()

    for c in range(num_cols):
        cells = [header[c]] + [r[c] for r in padded_rows]
        widths = [calc_visual_width(cell) for cell in cells]
        mx = max(widths) if widths else 8
        avg = sum(widths) / len(widths) if widths else 8.0
        col_max[c] = mx
        col_avg[c] = avg
        if mx <= 12:
            nowrap_cols.add(c)

    if is_info_card and num_cols == 2:
        pcts = [22.0, 78.0]
        nowrap_cols.add(0)
    else:
        fixed_widths = {}
        for c in nowrap_cols:
            fixed_widths[c] = max(col_max[c] + 2, 8)

        non_fixed_cols = [c for c in range(num_cols) if c not in nowrap_cols]
        if not non_fixed_cols:
            tot = sum(fixed_widths.values()) or 1.0
            pcts = [fixed_widths[c] / tot * 100.0 for c in range(num_cols)]
        else:
            col_weights = {}
            for c in nowrap_cols:
                col_weights[c] = max(float(fixed_widths[c]), 8.0)
            for c in non_fixed_cols:
                col_weights[c] = max(math.sqrt(col_avg[c]) * 3.0, 8.0)
            tot = sum(col_weights.values()) or 1.0
            pcts = [col_weights[c] / tot * 100.0 for c in range(num_cols)]

    classes = []
    if len(rows) > 15:
        classes.append("long-table")
    if is_info_card:
        classes.append("info-card-table")
    if is_index:
        classes.append("index-table")
    cls_attr = f' class="{" ".join(classes)}"' if classes else ''

    out = [f'<table{cls_attr}>']
    if caption:
        out.append(f'<caption>{inline(caption)}</caption>')

    out.append('<colgroup>')
    for c in range(num_cols):
        col_cls = ' class="nowrap"' if c in nowrap_cols else ''
        out.append(f'<col style="width: {pcts[c]:.1f}%;"{col_cls}>')
    out.append('</colgroup>')

    out.append('<thead><tr>')
    for c in range(num_cols):
        col_cls = ' class="nowrap"' if c in nowrap_cols else ''
        out.append(f'<th{col_cls}>{inline(header[c])}</th>')
    out.append('</tr></thead><tbody>')

    for r in padded_rows:
        out.append('<tr>')
        for c in range(num_cols):
            col_cls = ' class="nowrap"' if c in nowrap_cols else ''
            out.append(f'<td{col_cls}>{inline(r[c])}</td>')
        out.append('</tr>')
    out.append('</tbody></table>')
    return "\n".join(out)


# ------------------------------------------------------------------ markdown

def extract_sim_questions(text: str) -> tuple[str, list]:
    """Extract simulation questions into cards and collect answers for chapter end."""
    lines = text.splitlines()
    out_lines = []
    answers = []

    current_set = None
    i = 0
    while i < len(lines):
        line = lines[i]

        m_set = re.match(r'^####\s*題組\s*(SET-[^\n]+)', line)
        if m_set:
            current_set = m_set.group(1).strip()
            out_lines.append(line)
            i += 1
            continue

        m_sim = re.match(r'^####\s*模擬題\s*(SIM-[^\s\n]+)', line)
        if m_sim:
            sim_id = m_sim.group(1).strip()
            i += 1
            meta_tags = []
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines) and lines[i].strip().startswith('模擬題 SIM-'):
                parts = [p.strip() for p in re.split(r'[｜|]', lines[i].strip())]
                meta_tags = parts[1:]
                i += 1

            stem_lines = []
            while i < len(lines):
                if re.match(r'^\s*\([A-D]\)', lines[i]):
                    break
                if lines[i].startswith(('#### 模擬題', '#### 題組', '### ', '## ')):
                    break
                if lines[i].strip() == '答案與逐項解析':
                    break
                stem_lines.append(lines[i])
                i += 1

            options = []
            while i < len(lines):
                m_opt = re.match(r'^\s*\(([A-D])\)\s*(.*)$', lines[i])
                if m_opt:
                    options.append((m_opt.group(1), m_opt.group(2)))
                    i += 1
                else:
                    break

            ans_letter = "?"
            explanation_lines = []
            in_ans = False
            while i < len(lines):
                if lines[i].startswith(('#### 模擬題', '#### 題組', '### ', '## ')):
                    break
                if lines[i].strip() == '答案與逐項解析':
                    in_ans = True
                    i += 1
                    continue
                if in_ans:
                    m_ans = re.match(r'^答案[：:]\s*([A-D])', lines[i].strip())
                    if m_ans and ans_letter == "?":
                        ans_letter = m_ans.group(1)
                        i += 1
                        continue
                    explanation_lines.append(lines[i])
                i += 1

            answers.append((current_set, sim_id, ans_letter, explanation_lines))

            # Build Question Card
            card = [
                '<div class="sim-card">',
                '<div class="sim-header">',
                f'<h4 class="sim-title">模擬題 {sim_id}</h4>',
                '<span class="sim-hint">解答見本章末</span>',
                '</div>',
            ]
            if meta_tags:
                card.append('<div class="sim-meta">')
                for t in meta_tags:
                    card.append(f'<span class="sim-tag">{inline(t)}</span>')
                card.append('</div>')
            card.append('<div class="sim-body">')
            card.extend(stem_lines)
            if options:
                card.append('<div class="sim-options">')
                for ltr, opt_text in options:
                    card.append(f'<div class="sim-opt"><span class="opt-label">({ltr})</span><span class="opt-text">{inline(opt_text)}</span></div>')
                card.append('</div>')
            card.append('</div>')  # sim-body
            card.append('</div>')  # sim-card
            out_lines.extend(card)
            continue

        out_lines.append(line)
        i += 1

    return "\n".join(out_lines), answers


def build_answers_section(answers: list) -> str:
    """Format collected answers into a dedicated chapter-end section."""
    if not answers:
        return ""
    res = [
        '<div class="sim-answers-section">',
        '<h3 class="ans-section-title">模擬題解答與解析</h3>'
    ]
    cur_set = None
    for set_title, sim_id, ans_letter, exp_lines in answers:
        if set_title != cur_set:
            cur_set = set_title
            if cur_set:
                res.append(f'<h4 class="ans-set-title">題組 {cur_set}</h4>')
        res.append('<div class="sim-ans-item">')
        res.append(f'<div class="sim-ans-header"><span class="sim-ans-id">{sim_id}</span>　<span class="badge badge-ans">答案：{ans_letter}</span></div>')
        res.append('<div class="sim-ans-body">')
        res.extend(exp_lines)
        res.append('</div>')
        res.append('</div>')
    res.append('</div>')
    return "\n".join(res)


def md_to_html(md: str, is_apx_a: bool = False) -> str:
    """Minimal, dependency-free Markdown subset -> HTML with textbook layout enhancements."""
    out: list[str] = []
    lines = md.split("\n")
    i = 0
    in_code = False
    in_ul = False
    in_ol = False
    in_callout = False
    open_box = None
    prev_was_card_header = False
    pending_caption = None

    def close_ul():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def close_ol():
        nonlocal in_ol
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def close_section_box():
        nonlocal open_box
        if open_box:
            out.append("</div>")
            open_box = None

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        stripped = line.strip()

        # Fenced code
        if stripped.startswith("```"):
            close_ul(); close_ol()
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                lang = stripped.lstrip("`").strip()
                code_lang = lang.capitalize() if lang else ""
                lang_attr = f' data-lang="{code_lang}"' if code_lang else ''
                out.append(f'<pre class="code-block"{lang_attr}><code>')
                in_code = True
            i += 1
            continue
        if in_code:
            out.append(html.escape(raw))
            i += 1
            continue

        if not stripped:
            close_ul(); close_ol()
            i += 1
            continue

        if stripped == "<!-- pagebreak -->":
            close_ul(); close_ol()
            out.append('<div class="pagebreak"></div>')
            i += 1
            continue
        if stripped.startswith("<!--"):
            i += 1
            continue

        # Raw HTML pass-through
        if stripped.startswith(('<div', '</div', '<table', '</table', '<span', '<h3', '<h4', '<p class="sim')):
            close_ul(); close_ol()
            out.append(stripped)
            i += 1
            continue

        # Callouts :::type [title]
        m_callout = re.match(r"^:::(\w+)(?:\s+(.*))?$", stripped)
        if m_callout:
            close_ul(); close_ol()
            ctype = m_callout.group(1).lower()
            ctitle = m_callout.group(2).strip() if m_callout.group(2) else ""
            icons = {"trap": "⚠️", "key": "🔑", "tip": "💡", "ext": "🌐", "note": "📝"}
            icon = icons.get(ctype, "📝")
            out.append(f'<div class="callout callout-{ctype}">')
            if ctitle:
                out.append(f'<div class="callout-header"><span class="callout-icon">{icon}</span><span class="callout-title">{inline(ctitle)}</span></div>')
            out.append('<div class="callout-body">')
            in_callout = True
            i += 1
            continue
        if stripped == ":::":
            close_ul(); close_ol()
            if in_callout:
                out.append('</div></div>')
                in_callout = False
            i += 1
            continue

        # Caption check for tables: e.g. "考綱對位" followed by table
        if stripped == "考綱對位" and i + 1 < len(lines) and "|" in lines[i + 1]:
            pending_caption = stripped
            i += 1
            continue

        stripped = tidy_line(stripped)

        # Tier badge immediately following a heading
        if stripped in ("核心必考", "官方補充", "產業延伸", "版本敏感"):
            badge_map = {
                "核心必考": '<span class="badge badge-core">核心必考</span>',
                "官方補充": '<span class="badge badge-supp">官方補充</span>',
                "產業延伸": '<span class="badge badge-ext">產業延伸</span>',
                "版本敏感": '<span class="badge badge-ver">版本敏感</span>',
            }
            badge = badge_map[stripped]
            if out and re.search(r'</(h[2345])>$', out[-1]):
                out[-1] = re.sub(r'</(h[2345])>$', f' {badge}</\\1>', out[-1])
            else:
                out.append(f'<p>{badge}</p>')
            i += 1
            continue

        # Headings
        m_h = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m_h:
            close_ul(); close_ol()
            lvl = len(m_h.group(1))
            htext = m_h.group(2).strip()

            if lvl <= 3:
                close_section_box()

            if lvl == 2:
                # Chapter or front header
                m_ch = re.match(r"^第\s*(\d+)\s*章\s*(.*)$", htext)
                if m_ch:
                    num = int(m_ch.group(1))
                    name = m_ch.group(2).strip()
                    out.append('<div class="chapter-header">')
                    out.append(f'<div class="chapter-num">CHAPTER {num:02d}</div>')
                    out.append(f'<h2 class="chapter-title">第 {num} 章　{inline(name)}</h2>')
                    out.append('<div class="chapter-bar"></div>')
                    out.append('</div>')
                else:
                    out.append('<div class="front-header">')
                    out.append(f'<h2 class="front-title">{inline(htext)}</h2>')
                    out.append('<div class="front-bar"></div>')
                    out.append('</div>')
                i += 1
                continue

            if lvl == 3:
                prev_was_card_header = (htext == "章節識別卡")
                if "常見陷阱與錯誤觀念" in htext:
                    out.append(f'<h3 class="h3-trap">{inline(htext)}</h3>')
                elif "政府指引與產業落地實務" in htext:
                    out.append(f'<h3 class="h3-gov">{inline(htext)}</h3>')
                else:
                    out.append(f'<h3>{inline(htext)}</h3>')
                i += 1
                continue

            if lvl == 4:
                close_section_box()
                if "考點補丁：" in htext:
                    out.append('<div class="section-box box-patch">')
                    open_box = 'patch'
                elif "學習指引補充：" in htext:
                    out.append('<div class="section-box box-guide">')
                    open_box = 'guide'
                elif "共用模組" in htext:
                    out.append('<div class="section-box box-module">')
                    open_box = 'module'
                out.append(f'<h4>{inline(htext)}</h4>')
                i += 1
                continue

            out.append(f'<h{lvl}>{inline(htext)}</h{lvl}>')
            i += 1
            continue

        # Tables
        if "|" in stripped and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$", lines[i + 1]):
            close_ul(); close_ol()
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                r_cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(r_cells)
                i += 1
            caption = pending_caption
            pending_caption = None
            is_info = prev_was_card_header
            prev_was_card_header = False
            is_idx = is_apx_a or any(any(ID_PATTERN.search(c) for c in r) for r in rows)
            tbl_html = format_table(header, rows, caption=caption, is_info_card=is_info, is_index=is_idx)
            out.append(tbl_html)
            continue

        # Blockquote
        if stripped.startswith(">"):
            close_ul(); close_ol()
            out.append(f"<blockquote>{inline(stripped.lstrip('> ').strip())}</blockquote>")
            i += 1
            continue

        # Numbered list (Learning goals or general ordered list)
        m_num = re.match(r"^(\d+)[.．、]\s*(.*)$", stripped)
        if m_num:
            close_ul()
            if not in_ol:
                out.append('<ol class="learning-goals">')
                in_ol = True
            out.append(f"<li>{inline(m_num.group(2))}</li>")
            i += 1
            continue

        # Bullet list
        m_ul = re.match(r"^[-*•]\s+(.*)$", stripped)
        if m_ul:
            close_ol()
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            content = m_ul.group(1)
            is_highlight = content.startswith(("**一句判斷規則**", "**易混點**"))
            li_cls = ' class="li-highlight"' if is_highlight else ''
            out.append(f"<li{li_cls}>{inline(content)}</li>")
            i += 1
            continue

        # Normal paragraph
        close_ul(); close_ol()
        out.append(f"<p>{inline(stripped)}</p>")
        i += 1

    close_ul(); close_ol()
    close_section_box()
    if in_callout:
        out.append('</div></div>')
    if in_code:
        out.append("</code></pre>")
    return "\n".join(keep_with_next(out))


_TIER_P = re.compile(r"^<p>(核心必考|官方補充|產業延伸|版本敏感)</p>$")
_SIM_META = re.compile(r"^<p>模擬題 SIM-")
_KEEP_MAX_LINES = 14


def _block_end(out: list[str], k: int) -> int:
    """Index just past the block that starts at out[k]."""
    first = out[k]
    for opener, closer in (("<ul>", "</ul>"), ("<ol", "</ol>"),
                           ("<table", "</tbody></table>"), ("<table", "</table>"),
                           ("<pre", "</code></pre>"), ("<pre", "</pre>")):
        if first.startswith(opener):
            j = k
            while j < len(out) and not out[j].endswith(closer) and out[j] != closer:
                j += 1
            return j + 1
    return k + 1


def keep_with_next(out: list[str]) -> list[str]:
    """Wrap each h3–h5 heading with its tier/meta line and first content block in a no-break box."""
    res: list[str] = []
    k = 0
    while k < len(out):
        line = out[k]
        if not re.match(r"^<h[345]>", line) or "sim-title" in line or "ans-" in line:
            res.append(line); k += 1; continue
        group = [line]
        k += 1
        while k < len(out) and (_TIER_P.match(out[k]) or _SIM_META.match(out[k])
                                or (re.match(r"^<h[345]>", out[k]) and "sim-title" not in out[k])):
            group.append(out[k]); k += 1
        if k < len(out) and not re.match(r"^<h[1-6]>|^<div", out[k]):
            end = _block_end(out, k)
            block = out[k:end]
            if len(block) > _KEEP_MAX_LINES and block[0] == "<ul>":
                group += ["<ul>", block[1], "</ul>"]
                rest = ['<ul class="cont">'] + block[2:]
            elif len(block) > _KEEP_MAX_LINES and block[0].startswith("<ol"):
                group += [block[0], block[1], "</ol>"]
                rest = ['<ol class="cont">'] + block[2:]
            else:
                group += block
                rest = []
            k = end
            res.append('<div class="keep">')
            res += group
            res.append("</div>")
            res += rest
            continue
        res.append('<div class="keep">'); res += group; res.append("</div>")
    return res


# ------------------------------------------------------------------ assembly

def collect(vol: str) -> list[Path]:
    d = ROOT / "book" / vol / "v0.3"
    if not d.exists():
        raise SystemExit(f"missing {d}; run tools/make_v03.py {vol} first")
    return volume_files(vol)


def build_html(vol: str, stats: dict, files: list[Path], draft: bool = False) -> str:
    body = []
    for f in files:
        body.append('<div class="chapter">')
        raw_md = render_stats(read_expanded(f), stats)
        # Preprocess simulation questions and answers
        card_md, answers = extract_sim_questions(raw_md)
        ans_section_md = build_answers_section(answers)
        file_md = card_md + ("\n\n" + ans_section_md if ans_section_md else "")
        body.append(md_to_html(file_md, is_apx_a=(f.name == "apxA.md")))
        body.append("</div>")
    roman = {"L21": "I", "L22": "II", "L23": "III"}[vol]
    cover = f"""
<div class="cover">
  <h1>iPAS AI應用規劃師（中級）考綱教科書　第 {roman} 冊（{vol}）</h1>
  <div class="sub">v0.3 校訂稿{'' if not draft else '｜尚有待補內容，請見附錄 B'}</div>
  <div class="meta">
    基準查核日：中華民國 115 年 9 月 24 日；續校訂日：115 年 9 月 25 日<br/>
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
    ap.add_argument("--draft", action="store_true", help="build an explicitly labelled draft while the release gate has findings")
    args = ap.parse_args()
    vol = args.volume

    r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_book.py"), vol],
                       capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if r.returncode != 0:
        print("編譯關卡未通過：check_book.py 發現未完成項目。")
        print(r.stdout[-2500:])
        if not args.draft:
            return 1
        print("以明確標示的校訂稿模式產生檢閱版。")

    from recount_stats import recount
    stats = recount(vol)
    files = collect(vol)
    doc = build_html(vol, stats, files, draft=args.draft)

    outdir = ROOT / "build" / vol
    outdir.mkdir(parents=True, exist_ok=True)
    stem = f"{vol}_v0.3_校訂稿" if args.draft else f"{vol}_v0.3"
    html_path = outdir / f"{stem}.html"
    html_path.write_text(doc, encoding="utf-8")
    print(f"HTML → {html_path} ({len(doc):,} chars, {len(files)} source files)")

    if args.html_only:
        return 0

    pdf_path = outdir / f"{stem}.pdf"
    try:
        from weasyprint import HTML
    except ImportError:
        chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        if not chrome.exists():
            chrome = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        if not chrome.exists():
            print("無可用的 PDF 引擎；HTML 已產生，PDF 未完成。")
            return 1
        cmd = [str(chrome), "--headless", "--disable-gpu", "--no-sandbox",
               "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", html_path.as_uri()]
        completed = subprocess.run(cmd, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=180)
        if completed.returncode != 0 or not pdf_path.exists():
            print(completed.stderr[-2000:])
            return 1
    else:
        HTML(string=doc, base_url=str(outdir)).write_pdf(str(pdf_path))
    size = pdf_path.stat().st_size
    print(f"PDF  → {pdf_path} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
