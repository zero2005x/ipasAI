#!/usr/bin/env python3
"""Apply callout box syntax to the identified 43 callout boxes."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# List of all 43 callout definitions:
# (relpath, label_str, callout_type)
CALLOUTS_DEF = [
    # L21
    ("book/L21/v0.3/ch01.md", "最易混淆的一點", "trap"),
    ("book/L21/v0.3/ch01.md", "選型口訣", "tip"),
    ("book/L21/v0.3/ch02.md", "高頻誤述", "trap"),
    ("book/L21/v0.3/ch02.md", "產業延伸（非官方核心考點）", "ext"),
    ("book/L21/v0.3/ch03.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L21/v0.3/ch03.md", "必背判準", "key"),
    ("book/L21/v0.3/ch03.md", "產業延伸（非官方核心考點）", "ext"),  # line ~173
    ("book/L21/v0.3/ch03.md", "產業延伸（非官方核心考點）", "ext"),  # line ~183
    ("book/L21/v0.3/ch04.md", "選型口訣", "tip"),
    ("book/L21/v0.3/ch04.md", "缺值填 0的陷阱", "trap"),
    ("book/L21/v0.3/ch05.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L21/v0.3/ch05.md", "計算題的兩個陷阱", "trap"),
    ("book/L21/v0.3/ch07.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L21/v0.3/ch08.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L21/v0.3/ch08.md", "考點提示", "tip"),
    ("book/L21/v0.3/ch08.md", "其他陷阱", "trap"),
    ("book/L21/v0.3/ch09.md", "選型訊號", "tip"),
    ("book/L21/v0.3/ch09.md", "四者的分辨口訣", "tip"),
    ("book/L21/v0.3/ch09.md", "產業延伸（非官方核心考點）", "ext"),

    # L22
    ("book/L22/v0.3/ch01.md", "偏態方向：必背的一句話", "key"),
    ("book/L22/v0.3/ch03.md", "p值的正確定義（本科最高頻陷阱）", "trap"),
    ("book/L22/v0.3/ch03.md", "方向性必背", "key"),
    ("book/L22/v0.3/ch06.md", "選型訊號", "tip"),
    ("book/L22/v0.3/ch06.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L22/v0.3/ch06.md", "本章第一名考點", "key"),
    ("book/L22/v0.3/ch06.md", "產業延伸（非官方核心考點）", "ext"),
    ("book/L22/v0.3/ch07.md", "PCA的四個陷阱", "trap"),
    ("book/L22/v0.3/ch08.md", "本章第一名考點", "key"),
    ("book/L22/v0.3/ch08.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L22/v0.3/ch11.md", "本章核心考點", "key"),
    ("book/L22/v0.3/ch12.md", "去重為何是第一優先", "key"),
    ("book/L22/v0.3/ch13.md", "常見陷阱與錯誤觀念", "trap"),

    # L23
    ("book/L23/v0.3/ch01.md", "選型訊號", "tip"),
    ("book/L23/v0.3/ch01.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L23/v0.3/ch02.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L23/v0.3/ch03.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L23/v0.3/ch04.md", "方向性陷阱：C與 alpha相反", "trap"),
    ("book/L23/v0.3/ch05.md", "必背的一句話", "key"),
    ("book/L23/v0.3/ch05.md", "方向性陷阱", "trap"),
    ("book/L23/v0.3/ch06.md", "本章最高頻陷阱：多標籤不可用 softmax", "trap"),
    ("book/L23/v0.3/ch06.md", "最易混淆的一點", "trap"),
    ("book/L23/v0.3/ch08.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L23/v0.3/ch09.md", "五個公式與其分母（必背）", "key"),
    ("book/L23/v0.3/ch09.md", "方向性必背", "key"),
    ("book/L23/v0.3/ch09.md", "常見陷阱與錯誤觀念", "trap"),
    ("book/L23/v0.3/ch12.md", "常見陷阱與錯誤觀念", "trap"),  # 1st occurrence
    ("book/L23/v0.3/ch12.md", "常見陷阱與錯誤觀念", "trap"),  # 2nd occurrence

    # shared
    ("shared/book/apxA.md", "常見陷阱與錯誤觀念", "trap"),
]

def apply_callouts_to_file(path: Path, defs: list[tuple[str, str]]):
    lines = path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    def_idx = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        s = line.strip()

        if def_idx < len(defs) and s == defs[def_idx][0] and not line.startswith(":::"):
            label_text, c_type = defs[def_idx]
            def_idx += 1

            # Start callout
            new_lines.append(f":::{c_type} {label_text}")
            i += 1

            # Collect content until next heading, next callout, or end of section
            content_lines = []
            while i < len(lines):
                cur = lines[i]
                cur_s = cur.strip()

                # Stop conditions: heading (##, ###, ####), or next def label, or pdf-page followed by heading
                if cur_s.startswith(("#", "####", "###", "##")):
                    break
                if def_idx < len(defs) and cur_s == defs[def_idx][0]:
                    break
                if cur_s.startswith("<!-- pdf-page"):
                    # Peek next non-empty line
                    peek = i + 1
                    while peek < len(lines) and not lines[peek].strip():
                        peek += 1
                    if peek < len(lines) and lines[peek].strip().startswith("#"):
                        break

                content_lines.append(cur)
                i += 1

            # Trim trailing empty lines from content
            while content_lines and not content_lines[-1].strip():
                content_lines.pop()

            new_lines.extend(content_lines)
            new_lines.append(":::")
            # If there's an empty line next, preserve it
            if i < len(lines) and not lines[i].strip():
                new_lines.append("")
                i += 1
            continue

        new_lines.append(line)
        i += 1

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main():
    # Group definitions by file
    from collections import defaultdict
    grouped = defaultdict(list)
    for relpath, label, c_type in CALLOUTS_DEF:
        grouped[relpath].append((label, c_type))

    inventory_records = []

    for relpath, defs in grouped.items():
        file_path = ROOT / relpath
        apply_callouts_to_file(file_path, defs)
        for label, c_type in defs:
            inventory_records.append(f"{relpath}\t{label}\t{c_type}\t1\tv0.2 original PDF box")

    out_tsv = ROOT / "tmp" / "callout_inventory.tsv"
    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_tsv, "w", encoding="utf-8") as fh:
        fh.write("file\tlabel\ttype\tparagraphs\tbasis\n")
        for r in inventory_records:
            fh.write(r + "\n")

    print(f"Applied {len(CALLOUTS_DEF)} callout boxes across {len(grouped)} files.")
    print(f"Saved inventory to {out_tsv.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
