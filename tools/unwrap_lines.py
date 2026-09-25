#!/usr/bin/env python3
"""Unwrap hard-wrapped lines in Markdown files for iPAS textbooks.

Usage:
    python tools/unwrap_lines.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.check_text_integrity import BASELINE_FILE, find_target_files, normalize


def dw(s: str) -> int:
    """Calculate display width where fullwidth/wide East Asian chars count as 2."""
    return sum(2 if unicodedata.east_asian_width(c) in ("F", "W") else 1 for c in s)


def is_fence(line: str) -> bool:
    return line.strip().startswith("```")


def is_callout(line: str) -> bool:
    return line.strip().startswith(":::")


def is_heading(line: str) -> bool:
    return line.strip().startswith("#")


def is_table(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") or bool(re.match(r"^\|?[\s:\-|]+\|[\s:\-|]*$", s))


def is_comment(line: str) -> bool:
    return line.strip().startswith("<!--")


def is_quote(line: str) -> bool:
    return line.strip().startswith(">")


def is_tier_label(line: str) -> bool:
    s = line.strip()
    return s in (
        "核心必考", "官方補充", "產業延伸", "版本敏感",
        "**核心必考**", "**官方補充**", "**產業延伸**", "**版本敏感**",
    )


def is_unconverted_label(line: str) -> bool:
    s = line.strip()
    return s in ("本章命題密度", "著作權處理與使用方式", "來源與稽核紀錄", "學習目標", "考綱對位", "章節識別卡")


def is_sim_header(line: str) -> bool:
    s = line.strip()
    return s.startswith(("模擬題 SIM-", "題組 SET-"))


def is_option_start(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r"^(\([A-Da-d]\)|（[A-Da-d]）|[A-Da-d]\.)\s*", s))


def is_answer_marker_start(line: str) -> bool:
    s = line.strip()
    if s == "答案與逐項解析":
        return True
    if re.match(r"^答案：\s*[A-D]", s):
        return True
    if s.startswith(("干擾項設計理由", "延伸考點", "本書對應段落：")):
        return True
    return False


def is_list_item_start(line: str) -> bool:
    s = line.strip()
    if s.startswith(("•", "·")):
        return True
    if re.match(r"^[-*+]\s+", s):
        return True
    if re.match(r"^\d+[.．、]\s*", s):
        return True
    if re.match(r"^（\d+）\s*", s) or re.match(r"^\(\d+\)\s*", s):
        return True
    return False


def is_metadata_row_start(line: str) -> bool:
    s = line.strip()
    return s.startswith((
        "官方來源：", "套用勘誤：", "政府文件：", "編者推論／延伸：",
        "層級判定依據：", "本索引之 L代碼為編者對位",
    ))


def cannot_merge_onto_prev(line: str) -> bool:
    """True if line cannot be merged onto the previous line (i.e. cannot be line b)."""
    s = line.strip()
    if not s:
        return True
    if is_fence(line) or is_callout(line) or is_heading(line) or is_table(line):
        return True
    if is_comment(line) or is_quote(line) or is_tier_label(line) or is_unconverted_label(line):
        return True
    if is_sim_header(line) or is_option_start(line) or is_answer_marker_start(line):
        return True
    if is_list_item_start(line) or is_metadata_row_start(line):
        return True
    return False


def cannot_accept_next(line: str) -> bool:
    """True if line cannot accept next line being appended to it (i.e. cannot be line a)."""
    s = line.strip()
    if not s:
        return True
    if is_fence(line) or is_callout(line) or is_heading(line) or is_table(line):
        return True
    if is_comment(line) or is_quote(line) or is_tier_label(line) or is_unconverted_label(line):
        return True
    if is_sim_header(line):
        return True
    return False


PUNCT_FULL_STOP = set("。！？!?")
PUNCT_CLAUSE_END = set("：；」）)］】")


def should_merge(curr: str, nxt: str, last_line: str) -> bool:
    """Determine whether nxt should be merged onto curr."""
    sa = curr.strip()
    sb = nxt.strip()
    if not sa or not sb:
        return False
    if cannot_accept_next(curr) or cannot_merge_onto_prev(nxt):
        return False

    # Question stem continuation
    if re.match(r"^下列.*何者.*[？?]$", sb):
        return True

    # If sa ends with full period, it is almost certainly a paragraph/sentence boundary
    if sa[-1] in PUNCT_FULL_STOP:
        return False

    w = dw(last_line.strip())
    # If sa ends with clause end (colon, semicolon, closing quote/paren)
    if sa[-1] in PUNCT_CLAUSE_END:
        # Merge only if full width (wrapped line at line end)
        return w >= 80

    # For other endings (characters, commas, dashes, English words):
    # If short line (< 50) and not ending with continuation punctuation:
    if w < 50 and sa[-1] not in "，、—–-":
        return False

    return True


def insert_paragraph_breaks(lines: list[str]) -> list[str]:
    """Insert empty lines between distinct paragraphs that both end with sentence-ending punctuation."""
    punct_end = set("。！？")
    out: list[str] = []
    in_code = False

    for i in range(len(lines)):
        curr = lines[i]
        out.append(curr)
        if curr.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        if i + 1 < len(lines):
            nxt = lines[i + 1]
            sc = curr.strip()
            sn = nxt.strip()
            if not sc or not sn:
                continue
            if cannot_accept_next(curr) or cannot_merge_onto_prev(nxt):
                continue
            if is_list_item_start(sc) or is_list_item_start(sn):
                continue
            if is_option_start(sc) or is_option_start(sn):
                continue
            if is_answer_marker_start(sc) or is_answer_marker_start(sn):
                continue
            if is_metadata_row_start(sc) or is_metadata_row_start(sn):
                continue
            # If both end with sentence-ending punctuation, they are two separate paragraphs!
            if sc[-1] in punct_end and sn[-1] in punct_end:
                out.append("")

    return out


def join_lines(la: str, lb: str) -> str:
    """Join line b to line a.

    Join directly without space, unless a ends with alphanumeric and b starts with alphanumeric.
    """
    sa = la.rstrip()
    sb = lb.lstrip()
    if not sa:
        return sb
    if not sb:
        return sa
    if re.search(r"[a-zA-Z0-9]$", sa) and re.match(r"^[a-zA-Z0-9]", sb):
        return sa + " " + sb
    return sa + sb


def unwrap_content(content: str) -> tuple[str, int]:
    """Unwrap hard wraps in a markdown document, returning new text and merge count."""
    lines = content.splitlines()
    in_code = False
    new_lines: list[str] = []
    merges = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            in_code = not in_code
            new_lines.append(line)
            i += 1
            continue
        if in_code:
            new_lines.append(line)
            i += 1
            continue

        curr = line
        last_line = line
        while i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.strip().startswith("```"):
                break
            if should_merge(curr, next_line, last_line):
                curr = join_lines(curr, next_line)
                last_line = next_line
                merges += 1
                i += 1
            else:
                break
        new_lines.append(curr)
        i += 1

    new_lines = insert_paragraph_breaks(new_lines)
    result = "\n".join(new_lines)
    if content.endswith("\n"):
        result += "\n"
    return result, merges


def check_appendix_a(text: str) -> list[tuple[int, str, str]]:
    """Check residual suspicious hard wraps according to Appendix A."""
    lines = text.splitlines()
    in_code = False
    punct_end = set("。：？！」）)］】；")
    residuals: list[tuple[int, str, str]] = []

    for i in range(len(lines) - 1):
        la = lines[i]
        lb = lines[i + 1]
        if la.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue

        if not la.strip() or not lb.strip():
            continue

        def has_forbidden_start(s: str) -> bool:
            if s.startswith(("  ", "\t")):
                return True
            st = s.strip()
            if st.startswith(("#", "|", "<", "```", ">", ":::")):
                return True
            if st.startswith(("- ", "* ")):
                return True
            return False

        if has_forbidden_start(la) or has_forbidden_start(lb):
            continue

        b_strip = lb.strip()
        if b_strip.startswith(("(", "（", "•", "答案")):
            continue

        a_strip = la.strip()
        if a_strip and a_strip[-1] in punct_end:
            continue

        if re.match(r"^(\d+|[一二三四五六七八九十]+)[.．、]", b_strip):
            continue

        residuals.append((i + 1, la, lb))

    return residuals


def classify_residuals(residuals: list[tuple[str, int, str, str]]) -> dict[str, list[tuple[str, int, str, str]]]:
    """Classify residuals into structural categories and content residuals."""
    categories: dict[str, list[tuple[str, int, str, str]]] = {
        "tier_label": [],
        "sim_header": [],
        "answer_marker": [],
        "section_meta": [],
        "matrix_art": [],
        "content_residual": [],
    }
    for fn, ln, la, lb in residuals:
        sa = la.strip()
        if sa in ("核心必考", "官方補充", "產業延伸", "版本敏感", "**核心必考**", "**官方補充**", "**產業延伸**", "**版本敏感**"):
            categories["tier_label"].append((fn, ln, la, lb))
        elif sa.startswith(("模擬題 SIM-", "題組 SET-")):
            categories["sim_header"].append((fn, ln, la, lb))
        elif sa.startswith("答案：") or sa == "答案與逐項解析" or sa.startswith(("干擾項設計理由", "延伸考點", "本書對應段落：")):
            categories["answer_marker"].append((fn, ln, la, lb))
        elif sa in ("本章命題密度", "著作權處理與使用方式", "來源與稽核紀錄", "學習目標", "考綱對位", "章節識別卡"):
            categories["section_meta"].append((fn, ln, la, lb))
        elif sa in (" ", "TN FP", "FN TP", "scikit‑learn二元分類混淆矩陣的排列為", "H0實際為真 H0實際為假", "偽陽性——說有效其實無效", "偽陰性——說無效其實有效"):
            categories["matrix_art"].append((fn, ln, la, lb))
        else:
            categories["content_residual"].append((fn, ln, la, lb))
    return categories


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Unwrap hard-wrapped lines in book Markdown files.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write files, only test.")
    args = parser.parse_args()

    with open(BASELINE_FILE, encoding="utf-8") as f:
        baseline = json.load(f)

    files = find_target_files()
    total_merges = 0
    all_integrity_pass = True
    all_residuals: list[tuple[str, int, str, str]] = []

    for p in files:
        content = p.read_text(encoding="utf-8")
        unwrapped, merges = unwrap_content(content)
        total_merges += merges

        norm_new = normalize(unwrapped)
        rel_path = p.relative_to(ROOT).as_posix()
        norm_base = baseline[rel_path]["normalized"]
        if norm_new != norm_base:
            print(f"[FAIL INTEGRITY] {p.name}")
            all_integrity_pass = False

        res = check_appendix_a(unwrapped)
        for ln, la, lb in res:
            all_residuals.append((p.name, ln, la, lb))

        if not args.dry_run and all_integrity_pass:
            p.write_text(unwrapped, encoding="utf-8")

    print(f"Total files processed: {len(files)}")
    print(f"Total merges performed: {total_merges}")
    print(f"Integrity check: {'ALL PASS' if all_integrity_pass else 'FAILED'}")

    classified = classify_residuals(all_residuals)
    print(f"\nAppendix A Total Raw Matches: {len(all_residuals)}")
    print(f"  - 分層標籤 (tier labels): {len(classified['tier_label'])}")
    print(f"  - 模擬題標籤 (SIM meta lines): {len(classified['sim_header'])}")
    print(f"  - 答案標記 (answer markers): {len(classified['answer_marker'])}")
    print(f"  - 章節中繼標籤 (section meta labels): {len(classified['section_meta'])}")
    print(f"  - 矩陣圖樣 (matrix art): {len(classified['matrix_art'])}")
    print(f"  - 內文殘留短句/公式 (content residuals): {len(classified['content_residual'])} (門檻: <= 50)")

    if classified["content_residual"]:
        print(f"\n--- 內文殘留清單 ({len(classified['content_residual'])} 處) ---")
        for fn, ln, la, lb in classified["content_residual"]:
            print(f"[{fn}:{ln}] {la.strip()}  -->  {lb.strip()[:40]}")


if __name__ == "__main__":
    main()
