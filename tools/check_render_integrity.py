#!/usr/bin/env python3
"""Verify rendering integrity between source Markdown and compiled HTML / PDF.

Usage:
    python -B tools/check_render_integrity.py [L21|L22|L23]

Checks:
1. Simulation questions:
   - Each chapter's answers count in "模擬題解答與解析" == number of "#### 模擬題" in that chapter.
   - "答案與逐項解析" does not appear inside any sim-card.
2. ID integrity in PDF:
   - pdftotext output must preserve all OFFICIAL, GUIDE, and ERR IDs without hyphen breaks.
3. Character multiset integrity:
   - Character counts between expanded Markdown and compiled HTML must match,
     with differences strictly limited to the documented whitelist.
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from book_files import read_expanded, render_stats, volume_files
from recount_stats import recount

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def check_sim_counts(vol: str, html_text: str) -> tuple[bool, list[str]]:
    """Verify simulation question count vs answer count per chapter, and no answer leaks."""
    errors = []
    stats = recount(vol)
    files = volume_files(vol)

    # Check no "答案與逐項解析" in any sim-card
    cards = re.findall(r'<div class="sim-card">.*?</div>\s*</div>', html_text, re.S)
    for idx, card in enumerate(cards):
        if "答案與逐項解析" in card:
            errors.append(f"Card {idx+1} contains '答案與逐項解析'!")

    # Check per-chapter counts by splitting on '<div class="chapter">'
    ch_blocks = html_text.split('<div class="chapter">')[1:]
    if len(ch_blocks) != len(files):
        errors.append(f"Chapter block count mismatch: {len(ch_blocks)} in HTML vs {len(files)} files")

    for f, block in zip(files, ch_blocks):
        raw_md = render_stats(read_expanded(f), stats)
        sim_matches = re.findall(r'^####\s*模擬題\s*(SIM-[^\s\n]+)', raw_md, re.M)
        num_sims = len(sim_matches)

        ans_items = re.findall(r'<div class="sim-ans-item">', block)
        num_ans = len(ans_items)

        if num_sims != num_ans:
            errors.append(f"{f.name}: {num_sims} questions in MD but {num_ans} answers in HTML")

    return (len(errors) == 0, errors)


def check_pdf_ids(vol: str, pdf_path: Path) -> tuple[bool, list[str]]:
    """Verify that pdftotext preserves all official, guide, and err IDs without breaks."""
    errors = []
    if not pdf_path.exists():
        return (False, [f"PDF file not found: {pdf_path}"])

    stats = recount(vol)
    files = volume_files(vol)

    id_patterns = [
        re.compile(r'\b(OFFICIAL-\d{3}-\d-L2\d-Q\d\d)\b'),
        re.compile(r'\b(GUIDE-L2\d-\d-\d\d)\b'),
        re.compile(r'\b(ERR-1150410-\d\d)\b'),
    ]

    expected_counts: dict[str, int] = {}
    for f in files:
        raw_md = render_stats(read_expanded(f), stats)
        for pat in id_patterns:
            for m in pat.findall(raw_md):
                expected_counts[m] = expected_counts.get(m, 0) + 1

    try:
        r = subprocess.run(["pdftotext", str(pdf_path), "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return (False, ["pdftotext not available in PATH"])

    if r.returncode != 0:
        return (False, [f"pdftotext failed: {r.stderr[:500]}"])

    pdf_text = r.stdout
    actual_counts: dict[str, int] = {}
    for pat in id_patterns:
        for m in pat.findall(pdf_text):
            actual_counts[m] = actual_counts.get(m, 0) + 1

    for id_str, exp_count in expected_counts.items():
        act_count = actual_counts.get(id_str, 0)
        if act_count != exp_count:
            errors.append(f"ID {id_str}: expected {exp_count} in MD, got {act_count} in PDF")

    return (len(errors) == 0, errors)


def check_character_multiset(vol: str, html_text: str) -> tuple[bool, list[str]]:
    """Compare character multiset between source Markdown and compiled HTML with whitelist."""
    errors = []
    stats = recount(vol)
    files = volume_files(vol)

    md_parts = [render_stats(read_expanded(f), stats) for f in files]
    all_md = "\n".join(md_parts)

    num_sims = 0
    num_ch_with_sims = 0
    for f in files:
        raw_md = render_stats(read_expanded(f), stats)
        sims = re.findall(r'^####\s*模擬題\s*(SIM-[^\s\n]+)', raw_md, re.M)
        if sims:
            num_sims += len(sims)
            num_ch_with_sims += 1

    html_no_cover = re.sub(r'<div class="cover">.*?</div>\s*<div class="pagebreak"></div>', '', html_text, flags=re.S)
    body_match = re.search(r'<body[^>]*>(.*)</body>', html_no_cover, re.S)
    if not body_match:
        return (False, ["Could not find <body> in HTML"])
    body_html = body_match.group(1)
    plain_html = html.unescape(re.sub(r'<[^>]+>', '', body_html))

    cjk_re = re.compile(r'[\u4e00-\u9fff]')
    c_md = Counter(cjk_re.findall(all_md))
    c_html = Counter(cjk_re.findall(plain_html))

    # Whitelist additions to HTML:
    # 1. "解答見本章末" * num_sims
    # 2. "模擬題解答與解析" * num_ch_with_sims
    # 3. Repeated SET group titles in answers section ("題組 SET-...")
    expected_added = Counter()
    for _ in range(num_sims):
        expected_added.update(cjk_re.findall("解答見本章末"))
    for _ in range(num_ch_with_sims):
        expected_added.update(cjk_re.findall("模擬題解答與解析"))
    sets_in_vol = re.findall(r'^####\s*題組\s*(SET-[^\n]+)', all_md, re.M)
    for s in sets_in_vol:
        expected_added.update(cjk_re.findall(f"題組 {s}"))


    # Whitelist subtractions from MD:
    # 1. Duplicate "模擬題" on meta lines (num_sims times)
    # 2. "答案與逐項解析" on each question (num_sims times)
    expected_removed = Counter()
    for _ in range(num_sims):
        expected_removed.update(cjk_re.findall("模擬題"))
        expected_removed.update(cjk_re.findall("答案與逐項解析"))

    adj_html = c_html - expected_added
    adj_md = c_md - expected_removed

    diff_md_not_html = adj_md - adj_html
    diff_html_not_md = adj_html - adj_md

    if diff_md_not_html or diff_html_not_md:
        errors.append(f"CJK multiset mismatch: in MD not HTML: {diff_md_not_html}, in HTML not MD: {diff_html_not_md}")

    return (len(errors) == 0, errors)


def verify_volume(vol: str) -> bool:
    print(f"=== Verifying {vol} ===")
    outdir = ROOT / "build" / vol
    stem = f"{vol}_v0.3_校訂稿"
    html_path = outdir / f"{stem}.html"
    pdf_path = outdir / f"{stem}.pdf"

    if not html_path.exists():
        print(f"ERROR: {html_path} does not exist. Run build_pdf.py first.")
        return False

    html_text = html_path.read_text(encoding="utf-8")

    # Check 1: Sim counts
    ok1, errs1 = check_sim_counts(vol, html_text)
    if ok1:
        print(f"  [OK] Simulation questions and answers count verified.")
    else:
        print(f"  [FAIL] Sim counts check failed:")
        for e in errs1:
            print(f"    - {e}")

    # Check 2: Character multiset
    ok2, errs2 = check_character_multiset(vol, html_text)
    if ok2:
        print(f"  [OK] Character multiset integrity verified (whitelist exact match).")
    else:
        print(f"  [FAIL] Character multiset check failed:")
        for e in errs2:
            print(f"    - {e}")

    # Check 3: PDF IDs
    ok3, errs3 = check_pdf_ids(vol, pdf_path)
    if ok3:
        print(f"  [OK] PDF IDs verified intact via pdftotext.")
    else:
        print(f"  [FAIL] PDF IDs check failed:")
        for e in errs3:
            print(f"    - {e}")

    success = ok1 and ok2 and ok3
    print(f"Result for {vol}: {'PASS' if success else 'FAIL'}\n")
    return success


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volumes", nargs="*", default=["L21", "L22", "L23"])
    args = ap.parse_args()

    all_ok = True
    for v in args.volumes:
        if not verify_volume(v):
            all_ok = False
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
