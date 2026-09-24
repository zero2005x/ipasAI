#!/usr/bin/env python3
"""Generate 附錄 B（勘誤、來源、版本資訊）for a volume.

    python3 tools/make_appendix_b.py L22

Spec: 「附錄 B 列出全部 19 條，加一欄『對本書的影響』」 and 「讀者版附錄只留
附錄 A、B」. The appendix is generated from shared/errata_1150410.json plus the
volume's own chapter list, so all three volumes carry the same 19 entries and the
same terminology table without hand-copying.

The old 附錄 D content (建置狀態、補件流程、索引採用限制、著作權處理) is
maintenance material and is deliberately NOT emitted here.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TYPE_LABEL = {
    "用語": "用語",
    "錯字": "錯字",
    "錯字（重複）": "錯字",
    "內容修正（P0）": "**內容修正**",
    "內容修正（公式錯誤）": "**公式錯誤**",
}


def load_volume(vol: str):
    d = ROOT / "book" / vol
    toc = json.loads((d / "toc.json").read_text(encoding="utf-8"))
    stats = json.loads((d / "stats.json").read_text(encoding="utf-8"))
    # prefer the recount from the deliverable when present in REVIEW
    return toc, stats


def chapter_rows(toc: list[dict], vol: str) -> list[tuple[str, str, str]]:
    rows = []
    for c in toc:
        if c["kind"] != "chapter":
            continue
        code = ""
        p = ROOT / "book" / vol / "v0.3" / f"ch{c['num']:02d}.md"
        if p.exists():
            m = re.search(r"^官方代碼\s+(L\d{5})", p.read_text(encoding="utf-8"), re.M)
            code = m.group(1) if m else ""
        rows.append((f"ch{c['num']:02d}", c["title"], code))
    return rows


def source_rows(vol: str, toc: list[dict]) -> list[tuple[str, str, str]]:
    p = ROOT / "sources_extracted" / "學習指引頁碼對照.csv"
    pagemap = {r["評鑑內容代碼"]: (r["學習指引"], r["起始頁"], r["結束頁（含章末練習題時一併列入）"])
               for r in csv.DictReader(p.read_text(encoding="utf-8-sig").splitlines())}
    out = []
    for _, title, code in chapter_rows(toc, vol):
        if code in pagemap:
            g, a, b = pagemap[code]
            out.append((code, title, f"{g} {a}～{b}"))
    return out


def build(vol: str) -> str:
    toc, stats = load_volume(vol)
    errata = json.loads((ROOT / "shared" / "errata_1150410.json").read_text(encoding="utf-8"))
    n_sim = stats.get("sim_total", "?")
    n_prog = stats.get("program_sim_total", "?")
    codes = [c for _, _, c in chapter_rows(toc, vol) if c]
    code_range = f"{codes[0]}–{codes[-1]}" if codes else "—"

    L = []
    L.append("## 附錄 B：勘誤、來源、版本資訊")
    L.append("")
    L.append("附錄 B：勘誤、來源、版本資訊")
    L.append("")
    L.append("本附錄只放三類內容：**勘誤**、**來源**、**版本資訊**。製作與稽核流程另見維護用文件，不進讀者版。")
    L.append("")

    # ---- B.1 errata
    L.append("### B.1 學習指引勘誤表（115.04.10 版，全 19 條）")
    L.append("")
    L.append("官方《AI應用規劃師（中級）學習指引內容勘誤表》115.04.10 版共 **19 條**，下表全數列出，並加一欄「對本書的影響」。")
    L.append("")
    L.append("| 編號 | 科目 | 指引頁碼 | 類型 | 更正後內容 | 對本書的影響 |")
    L.append("|---|---|---|---|---|---|")
    for e in errata["entries"]:
        typ = TYPE_LABEL.get(e["type"], e["type"])
        corr = re.sub(r"\s+", " ", e["corrected"])[:110]
        imp = re.sub(r"\s+", " ", e["book_impact"])[:110]
        L.append(f"| {e['id']} | {e['subject']} | {e['guide_page']} | {typ} | {corr} | {imp} |")
    L.append("")
    L.append("**四條必須照改的內容修正**：ERR-1150410-03（IDF 底數）、ERR-1150410-14（個資法事前告知義務）、ERR-1150410-17（NMF 逐元素非負）、ERR-1150410-18（邏輯斯對數勝算）。")
    L.append("**另有 ERR-1150410-19 公式錯誤（召回率分母應為 TP+FN）亦屬阻斷級**。")
    L.append("")

    # ---- B.2 terminology
    L.append("### B.2 勘誤表的用語對照（已納入自動檢查）")
    L.append("")
    tm = {k: v for k, v in errata["terminology_map"].items() if not k.startswith("_")}
    items = list(tm.items())
    L.append("| 誤 | 正 | 誤 | 正 |")
    L.append("|---|---|---|---|")
    for i in range(0, len(items), 2):
        a = items[i]
        b = items[i + 1] if i + 1 < len(items) else ("", "")
        L.append(f"| {a[0]} | {a[1]} | {b[0]} | {b[1]} |")
    L.append("")
    L.append("**三條須以語境判斷，不可全域取代**：「通過」（三讀通過、通過考試等保留）、「檢測」（瑕疵檢測、異常檢測等固定術語保留）、「水平」（水平線、水平面、水平翻轉保留）。")
    L.append("")

    # ---- B.3 confusable
    L.append("### B.3 易混用語對照框")
    L.append("")
    L.append("> **列式／欄式**：本書維持臺灣用法（列＝row、欄＝column）。")
    L.append("> 學習指引 4-14 的「**列式儲存**」就是本書的「**欄式儲存**」（columnar storage，如 Parquet／ORC）。兩者是同一件事。")
    L.append("")
    L.append("其他用語差異（指引／考卷 vs 本書）：指引的「均衡機率」「群體平等率」＝ 本書的「均等賠率」「統計均等」；考卷的「成員推斷」「支援度」＝ 本書的「成員推論」「支持度」。")
    L.append("")

    # ---- B.4 sources
    L.append("### B.4 本冊來源登錄")
    L.append("")
    L.append("| 來源編號 | 名稱 | 性質 | 狀態 |")
    L.append("|---|---|---|---|")
    L.append(f"| IPAS‑SCOPE‑11506 | AI應用規劃師能力鑑定評鑑內容範圍參考（115.06 版，115.06.02） | 官方評鑑範圍 | 已取得 |")
    L.append("| IPAS-SYLLABUS-11504 | 115 年度能力鑑定簡章（115.04 版） | 官方簡章 | 規則層級已確認 |")
    L.append(f"| IPAS-GUIDE-{vol} | 中級學習指引 科目{ {'L21':'一','L22':'二','L23':'三'}.get(vol,'?') } | 官方學習指引 | 已取得（見下表頁碼） |")
    L.append("| IPAS-ERRATA-MID | 中級學習指引內容勘誤表（115.04.10） | 官方勘誤 | 19 條全數併入（見 B.1） |")
    L.append("| IPAS-PYQ-NOTICE | 中級程式題型比重說明（115.03.31） | 官方公告 | 原句已引用 |")
    L.append("| IPAS-EXAM-114-2 | 114 年第二次中級公告試題（三科） | 正式試題 | 已取得 |")
    L.append("| IPAS-EXAM-115-1 | 115 年第一次中級公告試題（三科） | 正式試題 | 已取得 |")
    L.append("| GOV-AI-BASIC-ACT | 人工智慧基本法 | 法律 | 114.12.23 三讀、115.01.14 公布施行 |")
    L.append("| GOV-MODA-RISK-V1 | 人工智慧風險分類框架 v1.0（115.07.07） | 依基本法第 16 條之參考框架 | 三大類 20 子類型已列出 |")
    L.append("| GOV-EY-GENAI | 行政院使用生成式 AI 參考指引 | 行政院對所屬機關之內部規範 | 112.08.31 院會通過、112.10.03 函頒 |")
    L.append("| GOV-FSC-AI | 金融業運用人工智慧（AI）指引 | 行政指導性質的監理期待 | 已確認 |")
    L.append("| GOV-BA-AI-RULES | 金融機構運用人工智慧技術作業規範 | 公會自律規範（經主管機關備查） | 另有 114.10.02 修正版 |")
    L.append("| GOV-PDPA | 個人資料保護法 | 法律 | 114.11.11 修正公布、施行日另定 |")
    L.append("| GOV-MOEA-MFG | 產發署《AI 導入指引》 | 產業參考資源 | 已確認 |")
    L.append("")
    L.append("**版本敏感**：上表法規與政府文件均可能異動，查核日中華民國 115 年 10 月 1 日，應試前請自行複查。")
    L.append("")

    L.append("### B.5 本冊各章對應學習指引頁碼")
    L.append("")
    L.append("| 代碼 | 章名 | 學習指引頁碼 |")
    L.append("|---|---|---|")
    for code, title, pages in source_rows(vol, toc):
        L.append(f"| {code} | {title} | {pages} |")
    L.append("")

    # ---- B.6 version info
    L.append("### B.6 版本資訊")
    L.append("")
    L.append("| 項目 | 內容 |")
    L.append("|---|---|")
    L.append("| 本冊版本 | v0.3 |")
    L.append("| 資料截止日 | 中華民國 115 年 10 月 1 日 |")
    L.append("| 內容凍結 | 115.11.01 |")
    L.append("| 對應評鑑內容範圍參考 | **115.06 版**（115.06.02） |")
    L.append(f"| 涵蓋代碼 | {code_range}（{len(codes)} 個代碼、{len(codes)} 章） |")
    L.append(f"| 模擬題 | {n_sim} 題（程式題 {n_prog} 題） |")
    L.append("")
    L.append("**版本紀錄（兩行）**")
    L.append("")
    L.append("- 115.06 版起官方已更正 L233 代碼。")
    L.append("- v0.2.0 引用的 115.02 版，在其資料截止日前已被 115.06 版取代。")
    L.append("")
    L.append("**下次複審觸發**：官方發布新版評鑑範圍、新梯次試題公告、勘誤表更新，或 AI 相關法規異動。")
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volume")
    args = ap.parse_args()
    vol = args.volume
    out = ROOT / "book" / vol / "v0.3" / "apxB.md"
    old = ROOT / "book" / vol / "v0.3" / "apxD.md"
    out.write_text(build(vol), encoding="utf-8")
    print(f"{vol}: wrote {out.name} ({len(out.read_text(encoding='utf-8').splitlines())} lines)")
    if old.exists():
        old.unlink()
        print(f"{vol}: removed old {old.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
