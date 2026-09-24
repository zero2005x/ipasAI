#!/usr/bin/env python3
"""Apply the mechanical P0 edits from 「iPAS 中級考綱教科書 v0.3 修訂規格」 to a
volume's chapter files.

    python3 tools/apply_p0_mechanical.py L21 [--dry-run]

These are the *rule-based* edits that need no judgement:

* 對齊 115.06       IPAS-SCOPE-11502 -> IPAS-SCOPE-11506
* 資料截止日         115年8月1日 -> 115年10月1日
* 對應來源 PENDING   填入學習指引頁碼區間（sources_extracted/學習指引頁碼對照.csv）
* 章節卡「規劃 N 題」  刪除；模擬題數改由 stats.json 帶入
* 製作殘留          「其餘於 v0.2 補齊」、「編號正規化」、「industrybox」、「V-0x」
* 查核日            115年8月1日 -> 115年10月1日

The judgement calls (絕對化用語改寫、考點補丁、勘誤內容修正、附錄重編) are NOT
done here -- they live in the per-volume prompt and are edited by hand.

Run with --dry-run first; it prints every change and writes nothing.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CUTOFF_OLD = ["115年 8月 1日", "115年8月1日", "115 年 8 月 1 日"]
CUTOFF_NEW = "115年 10月 1日"

SCOPE_OLD = ["IPAS‑SCOPE‑11502", "IPAS-SCOPE-11502"]
SCOPE_NEW = "IPAS‑SCOPE‑11506"

# 章節卡「規劃 N 題」與「其餘於 v0.2 補齊」等製作殘留
CARD_RESIDUE = [
    (re.compile(r"（規劃\s*\d+\s*題[^）]*）"), ""),
    (re.compile(r"規劃\s*\d+\s*題[，,、]?"), ""),
    (re.compile(r"其餘於\s*v0\.2\s*補齊[；;]?"), ""),
    (re.compile(r"正式題索引已併入[；;]"), ""),
]
ARTIFACT_LINES = [
    (re.compile(r"已於\s*industrybox\s*中隔離"), "見本章產業延伸框"),
    (re.compile(r"\bV-0\d\b"), ""),
]


def load_page_map() -> dict[str, str]:
    p = ROOT / "sources_extracted" / "學習指引頁碼對照.csv"
    rows = list(csv.DictReader(p.read_text(encoding="utf-8-sig").splitlines()))
    return {r["評鑑內容代碼"]: f"{r['學習指引']} {r['起始頁']}～{r['結束頁（含章末練習題時一併列入）']}"
            for r in rows}


def chapter_code(text: str) -> str | None:
    m = re.search(r"^官方代碼\s+(L\d{5})", text, re.M)
    return m.group(1) if m else None


def apply(text: str, vol: str, pagemap: dict[str, str], log: list[str], name: str) -> str:
    orig = text

    code = chapter_code(text)
    guide = pagemap.get(code or "", "")

    # 1. 考綱版本
    for old in SCOPE_OLD:
        if old in text:
            text = text.replace(old, SCOPE_NEW)
            log.append(f"{name}: 考綱 {old} → {SCOPE_NEW}")

    # 2. 資料截止日 / 查核日
    for old in CUTOFF_OLD:
        if old in text:
            text = text.replace(old, CUTOFF_NEW)
            log.append(f"{name}: 截止日「{old}」→「{CUTOFF_NEW}」")

    # 3. 對應來源 PENDING -> 實際頁碼
    def fix_source(m: re.Match) -> str:
        return f"對應來源 {SCOPE_NEW}"

    if "頁碼 PENDING" in text or "頁碼PENDING" in text:
        text = re.sub(r"、\s*IPAS‑GUIDE‑L2\d\s*（頁碼\s*PENDING）", "", text)
        text = re.sub(r"（頁碼\s*PENDING）", "", text)
        log.append(f"{name}: 移除 對應來源 的 PENDING")
    if guide and code:
        text = text.replace(
            f"對應來源 {SCOPE_NEW}、IPAS‑GUIDE‑L2{vol[-1]}",
            f"對應來源 {SCOPE_NEW}、IPAS‑GUIDE‑{vol}（學習指引 {guide}）")
        text = text.replace(
            f"對應來源 {SCOPE_NEW}",
            f"對應來源 {SCOPE_NEW}、IPAS‑GUIDE‑{vol}（學習指引 {guide}）")
        text = text.replace(
            f"對應來源 {SCOPE_NEW}（115.06版評鑑內容範圍參考，115.06.02）、IPAS‑GUIDE‑{vol}（學習指引 {guide}）",
            f"對應來源 {SCOPE_NEW}、IPAS‑GUIDE‑{vol}（學習指引 {guide}）")
        log.append(f"{name}: 對應來源 填入指引頁碼（{code} → {guide}）")

    # 4. 章節卡殘留
    for pat, rep in CARD_RESIDUE:
        new = pat.sub(rep, text)
        if new != text:
            log.append(f"{name}: 章節卡殘留 {pat.pattern} → {rep!r}")
            text = new

    # 5. 其他製作殘留
    for pat, rep in ARTIFACT_LINES:
        new = pat.sub(rep, text)
        if new != text:
            log.append(f"{name}: 製作殘留 {pat.pattern} → {rep!r}")
            text = new

    # 6. 「正文來源與稽核紀錄」中殘留的頁碼 PENDING 敘述
    text = text.replace("，章節與頁碼 PENDING", "")
    text = text.replace("，頁碼 PENDING", "")

    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volume")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vdir = ROOT / "book" / args.volume / "v0.3"
    if not vdir.exists():
        raise SystemExit(f"missing {vdir}; run tools/make_v03.py {args.volume} first")
    pagemap = load_page_map()

    log: list[str] = []
    changed = 0
    for f in sorted(vdir.glob("ch*.md")) + sorted(vdir.glob("apx*.md")) + sorted((vdir / "front").glob("*.md")):
        text = f.read_text(encoding="utf-8")
        new = apply(text, args.volume, pagemap, log, f.name)
        if new != text:
            changed += 1
            if not args.dry_run:
                f.write_text(new, encoding="utf-8")

    mode = "（dry-run，未寫入）" if args.dry_run else ""
    print(f"{args.volume}: {changed} 個檔案有變更{mode}")
    for line in log:
        print("  -", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
