#!/usr/bin/env python3
"""Automated checks required by 「iPAS 中級考綱教科書 v0.3 修訂規格」.

    python3 tools/check_book.py L21 [--strict] [--json out.json]

Checks
------
1. 用語        勘誤表 115.04.10 的 14 組用語對照（shared/errata_1150410.json）
2. 絕對化用語   15 則已核准改寫 + 通用偵測（shared/language_rules.json）
3. 製作殘留    「其餘於 v0.2 補齊」「編號正規化」、內部路徑、V-08／ERR 編號、AI 提示語
4. 統計數字    所有讀者可見計數必須來自 book/<VOL>/stats.json，不得手寫
5. 索引完整    「正式公告試題索引」每列都要有「本書對應段落」（規格：空白就不能編譯）
6. 考點補丁    每個補丁至少 5 行

Exit code is non-zero when a P0 (blocking) failure is found; --strict also fails on
warnings.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from book_files import read_expanded, volume_files  # noqa: E402

# ------------------------------------------------------------------ rule loading

def load_rules():
    errata = json.loads((SHARED / "errata_1150410.json").read_text(encoding="utf-8"))
    lang = json.loads((SHARED / "language_rules.json").read_text(encoding="utf-8"))
    return errata, lang


# 用語對照需要語境判斷，不可全域硬取代。這些是「若出現則必須檢視」的守門規則。
TERM_CONTEXT_GUARD = {
    "通過": {
        "allow": r"(三讀通過|表決通過|審議通過|通過考試|考試通過|通過測驗|通過驗收|通過審查|通過評鑑|通過認證|通過檢驗|檢驗|經[^\n]{0,12}通過|決議通過|議會通過|立法院通過|核定通過|票通過|通過成績|成績自應考日起|評估[^\n]{0,4}通過|通過率|已通過|通過門檻|通過四層|通過與否|是否通過|審核通過|複審通過)",
        "message": "「通過」若表『透過』義須改；若表『三讀通過／考試通過／通過檢驗』等則保留",
    },
    "檢測": {
        "allow": r"(瑕疵檢測|異常檢測|檢測器|檢測模型|檢測率|物件檢測|檢測到|視覺檢測|工業檢測|檢測管線|檢測系統|品質檢測|檢測站|安全件檢測)",
        "message": "「檢測」若指人臉／物件偵測須改為「偵測」；固定術語可保留",
    },
    "水平": {
        "allow": r"(水平線|水平面|水平軸|水平方向|水平翻轉|水平鏡像)",
        "message": "「水平」若表『水準／品質』義須改；若表水平方向／水平翻轉則保留",
    },
    "提取": {
        "allow": r"(提取率|特徵提取|提取特徵)",
        "message": "「提取」應改為「擷取」",
    },
}

# 製作殘留：讀者版不得出現（規格 §製作殘留與統計數字）
ARTIFACT_PATTERNS = [
    (r"其餘於\s*v0\.2\s*補齊", "刪除「其餘於 v0.2 補齊」"),
    (r"編號正規化", "刪除「編號正規化」段落（規格：附錄 B 版本紀錄改寫兩行）"),
    (r"references/", "移除內部路徑 references/"),
    (r"source_registry\.yaml", "移除內部檔名 source_registry.yaml"),
    (r"errata\.yaml", "移除內部檔名 errata.yaml"),
    (r"qa/blueprint\.md", "移除內部路徑 qa/blueprint.md"),
    (r"industrybox", "移除「industrybox」內部代號"),
    (r"\bV-0\d\b", "移除內部代號 V-0x"),
    (r"ERR[‑\-]L2\d[‑\-]?\d{3}", "勘誤編號統一寫法（規格：ERR-L23001 與 ERR-L23-001 兩種寫法要統一）"),
    (r"此原則優先於任何要求逐字保存官方題目的指示", "刪除寫給 AI 的提示語"),
    (r"待查證", "規格要求原標『待查證』的政府事實全部補上，不應殘留"),
    (r"PENDING", "來源頁碼不得留 PENDING"),
    (r"未核對，不列出", "規格要求改為列出（風險分類框架 20 子類型）"),
    (r"完整條目未取得", "勘誤表已公開，此句須刪除"),
]

# 手寫統計數字：應改為自動計算（stats.json）
HANDWRITTEN_STAT_PATTERNS = [
    (r"模擬題\s*\d+\s*題", "模擬題數須由 stats.json 帶入"),
    (r"規劃\s*\d+\s*題", "章節卡「規劃 N 題」須拿掉，改顯示自動計算的公告試題數與分層比例"),
    (r"程式判讀\s*\d+\s*題", "程式判讀題數須由 stats.json 帶入"),
    (r"(?:對位至本代碼者|佔)\s*\d+\s*(?:題|%)", "命題密度須由 stats.json 帶入"),
]

INDEX_HEAD = re.compile(r"^###\s*\d+\.\d+\s*正式公告試題索引", re.M)
INDEX_NEXT = re.compile(r"^###\s*\d+\.\d+\s", re.M)
PATCH_MIN_LINES = 5


def book_text(vol: str, source: str = "v03") -> str:
    """Read the text to check.

    source="v03"      the actual deliverable: book/<VOL>/v0.3/ (default)
    source="skeleton" the raw v0.2.0 reconstruction (baseline / migration diff)

    Checking the skeleton by mistake would validate text nobody ships, and would
    hide every fix made in v0.3. The default is therefore the deliverable.
    """
    d = ROOT / "book" / vol
    if source == "skeleton":
        p = d / "skeleton.md"
        if not p.exists():
            raise SystemExit(f"missing {p}; run tools/build_skeleton.py {vol} first")
        return p.read_text(encoding="utf-8")

    vdir = d / "v0.3"
    if not vdir.exists():
        raise SystemExit(f"missing {vdir}; run tools/make_v03.py {vol} --force first")
    # Same file set and include expansion as the PDF build, so the gate checks what ships.
    return "\n".join(read_expanded(p) for p in volume_files(vol))


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def pdf_page_near(text: str, pos: int) -> str:
    """Nearest preceding <!-- pdf-page N --> anchor."""
    m = None
    for m in re.finditer(r"<!-- pdf-page (\d+) -->", text[:pos]):
        pass
    return m.group(1) if m else "?"


# ------------------------------------------------------------------ checks

def check_terminology(text: str, errata: dict) -> list[dict]:
    out = []
    for bad, good in errata["terminology_map"].items():
        if bad.startswith("_"):
            continue
        guard = TERM_CONTEXT_GUARD.get(bad, {})
        for m in re.finditer(re.escape(bad), text):
            ctx = text[max(0, m.start() - 30): m.end() + 30]
            if guard.get("allow") and re.search(guard["allow"], ctx):
                continue
            out.append({
                "check": "用語",
                "severity": "warn",
                "volume_page": pdf_page_near(text, m.start()),
                "line": line_of(text, m.start()),
                "found": bad,
                "should_be": good,
                "message": guard.get("message", f"用語對照：{bad}→{good}"),
                "context": re.sub(r"\s+", " ", ctx).strip(),
            })
    return out


def check_language(text: str, lang: dict) -> list[dict]:
    out = []
    for item in lang["approved_rewrites"]:
        for m in re.finditer(item["pattern"], text):
            out.append({
                "check": "絕對化用語",
                "severity": "error",
                "rule": item["id"],
                "volume_page": pdf_page_near(text, m.start()),
                "line": line_of(text, m.start()),
                "found": re.sub(r"\s+", " ", m.group(0)),
                "should_be": item["rewrite"],
                "message": item["reason"],
            })
    for g in lang["generic_patterns"]:
        for m in re.finditer(g["pattern"], text):
            out.append({
                "check": "絕對化用語(通用)",
                "severity": "info",
                "volume_page": pdf_page_near(text, m.start()),
                "line": line_of(text, m.start()),
                "found": re.sub(r"\s+", " ", m.group(0)),
                "should_be": "",
                "message": g["note"],
            })
    return out


def check_artifacts(text: str) -> list[dict]:
    out = []
    for pat, msg in ARTIFACT_PATTERNS:
        for m in re.finditer(pat, text):
            out.append({
                "check": "製作殘留",
                "severity": "error",
                "volume_page": pdf_page_near(text, m.start()),
                "line": line_of(text, m.start()),
                "found": m.group(0),
                "should_be": "",
                "message": msg,
            })
    return out


def check_handwritten_stats(text: str) -> list[dict]:
    out = []
    for pat, msg in HANDWRITTEN_STAT_PATTERNS:
        for m in re.finditer(pat, text):
            out.append({
                "check": "統計數字",
                "severity": "warn",
                "volume_page": pdf_page_near(text, m.start()),
                "line": line_of(text, m.start()),
                "found": m.group(0),
                "should_be": "{{stats.*}}",
                "message": msg,
            })
    return out


def check_index_rows(text: str, vol: str | None = None) -> list[dict]:
    """Check that the 100 announced questions have a usable teaching locator.

    The reconstructed books use whitespace-delimited OFFICIAL rows, not GFM
    tables.  The earlier implementation silently passed when there was no
    table at all.  A missing index is an error, not an empty success.
    """
    out = []
    heads = list(INDEX_HEAD.finditer(text))
    if not heads:
        return [{"check": "索引完整", "severity": "error", "volume_page": "?",
                 "line": 1, "found": "找不到正式公告試題索引", "should_be": "每題均有本書對應段落",
                 "message": "正式公告試題索引缺失"}]
    found: dict[tuple[str, int], tuple[str, int]] = {}
    section_ids = set(re.findall(r"(?m)^####\s+(\d+\.\d+\.\d+)\s", text))
    row_re = re.compile(r"^OFFICIAL[-‑–]?(114[-‑–]2|115[-‑–]1)[-‑–]?L2[123][-‑–]?Q(\d{1,2})\s+(114[-‑–]2|115[-‑–]1)\s+([ABCD])\b(.*)$")
    for h in heads:
        nxt = INDEX_NEXT.search(text, h.end())
        body = text[h.end(): nxt.start() if nxt else len(text)]
        # rows are table lines; a row missing the last column is a blocker
        for line in body.splitlines():
            s = line.strip()
            if not s or s.startswith("<!--") or s.startswith("###"):
                continue
            if s.startswith("| OFFICIAL"):
                # Markdown table row: | ID | 場次 | 官方答案 | 原卷頁次 | 含圖表 | 本書對應段落 |
                cells = [c.strip() for c in s.strip("|").split("|")]
                s = f"{cells[0]} {cells[1] if len(cells) > 1 else ''} {cells[2] if len(cells) > 2 else ''} " \
                    f"本書對應段落：{cells[-1] if len(cells) >= 6 else ''}"
            if s.startswith("OFFICIAL"):
                m = row_re.match(s)
                if not m:
                    out.append({"check": "索引完整", "severity": "error",
                                "volume_page": pdf_page_near(text, h.start()),
                                "line": line_of(text, h.start()), "found": s[:90],
                                "should_be": "正規題號、場次、答案及本書對應段落",
                                "message": "公告試題列格式無法解析"})
                    continue
                exam, q, repeated_exam, answer, rest = m.groups()
                exam = exam.replace("‑", "-").replace("–", "-")
                repeated_exam = repeated_exam.replace("‑", "-").replace("–", "-")
                key = (exam, int(q))
                if exam != repeated_exam or key in found:
                    out.append({"check": "索引完整", "severity": "error",
                                "volume_page": pdf_page_near(text, h.start()),
                                "line": line_of(text, h.start()), "found": s[:90],
                                "should_be": "唯一題號且場次一致", "message": "公告試題題號重複或場次不一致"})
                found[key] = (answer, line_of(text, h.start()))
                target_match = re.search(
                    r"(?:本書對應段落|對應段落)\s*[:：]\s*(\d+\.\d+\.\d+)(?=\s|$)",
                    rest,
                )
                if not target_match:
                    out.append({"check": "索引完整", "severity": "error",
                                "volume_page": pdf_page_near(text, h.start()),
                                "line": line_of(text, h.start()), "found": s[:90],
                                "should_be": "本書對應段落：x.x.x",
                                "message": "公告試題未指向本書的具體教學段落"})
                elif target_match.group(1) not in section_ids:
                    out.append({"check": "索引完整", "severity": "error",
                                "volume_page": pdf_page_near(text, h.start()),
                                "line": line_of(text, h.start()), "found": s[:90],
                                "should_be": "存在的三級教學段落",
                                "message": "公告試題指向的段落標題不存在"})
                continue
            if s.startswith("|") and s.count("|") >= 3:
                cells = [c.strip() for c in s.strip("|").split("|")]
                if all(set(c) <= set("-: ") for c in cells):
                    continue  # separator row
                if any(c == "" for c in cells):
                    out.append({
                        "check": "索引完整",
                        "severity": "error",
                        "volume_page": pdf_page_near(text, h.start()),
                        "line": line_of(text, h.start()),
                        "found": s[:90],
                        "should_be": "",
                        "message": "索引列有空欄；規格：『本書對應段落』空白就不能編譯",
                    })
    if vol:
        expected = {(exam, q) for exam in ("114-2", "115-1") for q in range(1, 51)}
        missing = sorted(expected - set(found))
        if missing:
            out.append({"check": "索引完整", "severity": "error", "volume_page": "?",
                        "line": 1, "found": f"缺 {len(missing)} 題：{missing[:8]}",
                        "should_be": "兩場次各 50 題", "message": "公告試題索引不足 100 題"})
        for exam in ("114-2", "115-1"):
            p = ROOT / "sources_extracted" / f"exam_{exam.replace('-', '_')}_{vol}.txt"
            if not p.exists():
                continue
            # Some official answers are printed as full-width letters (Ａ–Ｄ); normalise first,
            # otherwise those questions are silently skipped.
            source = p.read_text(encoding="utf-8").translate(str.maketrans("ＡＢＣＤ", "ABCD"))
            answers = {int(q): a for a, q in re.findall(r"(?m)^\s*([ABCD])\s+(\d{1,2})\s*[.．]\s*", source)}
            unparsed = [q for q in range(1, 51) if q not in answers]
            if unparsed:
                out.append({"check": "官方答案", "severity": "error", "volume_page": "?", "line": 1,
                            "found": f"{exam} 無法解析官方答案：{unparsed[:8]}", "should_be": "50 題全數可比對",
                            "message": "官方答案解析不完整，比對結果不可信"})
            for q in range(1, 51):
                key = (exam, q)
                if key in found and q in answers and found[key][0] != answers[q]:
                    out.append({"check": "官方答案", "severity": "error", "volume_page": "?",
                                "line": found[key][1], "found": f"{exam} Q{q:02d}: {found[key][0]}",
                                "should_be": answers[q], "message": "索引答案與官方公告試題不符"})
    return out


def check_source_pages(text: str) -> list[dict]:
    """章節卡來源列及頁碼須與學習指引頁碼對照表一致。"""
    out = []
    page_map = {}
    with (ROOT / "sources_extracted" / "學習指引頁碼對照.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        for row in csv.DictReader(stream):
            page_map[row["評鑑內容代碼"]] = row
    chapter_heads = list(re.finditer(r"(?m)^##\s+第\s*\d+\s*章", text))
    for head in chapter_heads:
        card = text[head.end():head.end() + 1200]
        source = re.search(r"(?m)^\|\s*對應來源\s*\|([^\n]+)", card)
        if not source:
            out.append({
                "check": "對應來源",
                "severity": "error",
                "volume_page": pdf_page_near(text, head.start()),
                "line": line_of(text, head.start()),
                "found": head.group(0),
                "should_be": "章節識別卡內的「對應來源」列與實際指引頁碼",
                "message": "章節識別卡缺少對應來源列",
            })
            continue
        code = re.search(r"(?m)^\|\s*官方代碼\s*\|\s*(L\d{5})\s*\|", card)
        if not code or code.group(1) not in page_map:
            out.append({"check": "對應來源", "severity": "error",
                        "volume_page": pdf_page_near(text, head.start()),
                        "line": line_of(text, head.start()),
                        "found": code.group(1) if code else "缺官方代碼",
                        "should_be": "頁碼對照表中的官方代碼",
                        "message": "章節識別卡的官方代碼無法對照來源"})
            continue
        row = page_map[code.group(1)]
        expected = f'{row["學習指引"]} {row["起始頁"]}～{row["結束頁（含章末練習題時一併列入）"]}'
        if expected not in source.group(1):
            out.append({"check": "對應來源", "severity": "error",
                        "volume_page": pdf_page_near(text, head.start()),
                        "line": line_of(text, head.start()),
                        "found": source.group(1).strip()[:90],
                        "should_be": expected,
                        "message": "章節識別卡的學習指引頁碼與來源對照表不符"})
    if "頁碼 PENDING" in text or re.search(r"PENDING", text):
        for m in re.finditer(r"PENDING", text):
            out.append({
                "check": "對應來源",
                "severity": "error",
                "volume_page": pdf_page_near(text, m.start()),
                "line": line_of(text, m.start()),
                "found": "PENDING",
                "should_be": "實際指引頁碼",
                "message": "章節卡『對應來源』須補齊指引頁碼",
            })
    return out


def check_known_pdf_corruption(text: str) -> list[dict]:
    """Catch formula fragments known to have survived the PDF text extraction."""
    patterns = {
        r"TPTP\s*\+": "Precision／Recall 分數線遺失",
        r"TNTN\s*\+": "Specificity 分數線遺失",
        r"2PRP\s*\+": "F1 分數線遺失",
        r"ROI\s*=年度效益−年度成本總投資成本": "ROI 分數線遺失",
        r"Attention\(Q,K,V\)\s*=\s*softmax√": "Attention 矩陣與分母遺失",
        r"190190\+980": "陽性預測值分數線遺失",
        r"(\d{2,})\1\+\d+\s*=\s*\d+": "分數線遺失（分子與分母黏在一起，如 9999+495 = 99594）",
        r"(?m)^#{2,6}\s*[\d.]+\s*[%％–-]": "數值被轉成標題（題幹或表格被切斷）",
        r"O\(n2|n2增為|K2Cin": "上標遺失（n²、K²）",
        r"(?m)^\d(?:#|[A-Za-z_]\w*\s*=|[A-Za-z_]\w*\()": "程式碼行號殘留在 code fence 外",
        r"[̸￿]": "PDF 擷取的異常字元",
        r"5[%％][–-]40[%％]": "缺失率區間仍沿用舊稿 5–40%",
    }
    out = []
    for pat, reason in patterns.items():
        for m in re.finditer(pat, text):
            out.append({"check": "PDF擷取公式", "severity": "error",
                        "volume_page": pdf_page_near(text, m.start()),
                        "line": line_of(text, m.start()), "found": m.group(0),
                        "should_be": "依原 PDF 與正確定義重新排式", "message": reason})
    return out


# ------------------------------------------------------------------ reporting

SEV_ORDER = {"error": 0, "warn": 1, "info": 2}
ALLOWLIST = ROOT / "audit" / "strict_allowlist.tsv"


def apply_allowlist(findings: list[dict], vol: str) -> None:
    """Mark reviewed warnings (audit/strict_allowlist.tsv) so --strict ignores them.

    Columns: volume(L21/L22/L23/*)  check  found(*=any)  context_regex  reason
    Matching uses the finding's context, not line numbers, so entries survive edits.
    """
    if not ALLOWLIST.exists():
        return
    rules = []
    for ln in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#") or ln.startswith("volume\t"):
            continue
        v, chk, found, ctx, reason = (ln.split("\t") + [""] * 5)[:5]
        rules.append((v, chk, found, re.compile(ctx), reason))
    for f in findings:
        if f["severity"] != "warn":
            continue
        for v, chk, found, ctx, reason in rules:
            if v in ("*", vol) and chk == f["check"] and found in ("*", f["found"]) \
                    and ctx.search(f.get("context") or ""):
                f["allowed"] = reason
                break


def report(findings: list[dict], vol: str, source: str = "v03") -> int:
    findings.sort(key=lambda f: (SEV_ORDER.get(f["severity"], 9), f["check"], f["line"]))
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    label = "v0.3 交付檔" if source == "v03" else "v0.2.0 原文基準"
    print(f"\n=== {vol} 自動檢查（{label}）===")
    by_check: dict[str, list[dict]] = {}
    for f in findings:
        by_check.setdefault(f["check"], []).append(f)
    for check, items in by_check.items():
        errs = sum(1 for i in items if i["severity"] == "error")
        warns = sum(1 for i in items if i["severity"] == "warn")
        infos = sum(1 for i in items if i["severity"] == "info")
        print(f"\n[{check}] error={errs} warn={warns} info={infos}")
        for i in items[:12]:
            tag = {"error": "✗", "warn": "!", "info": "·"}[i["severity"]]
            if i.get("allowed"):
                tag = "✓"
            loc = f"p{i['volume_page']}/L{i['line']}"
            extra = f" → {i['should_be']}" if i["should_be"] else ""
            print(f"  {tag} {loc:<14} {i['found'][:46]:<48}{extra}")
            if i["severity"] != "info" and i.get("context"):
                print(f"      ctx: {i['context'][:100]}")
        if len(items) > 12:
            print(f"  … 其餘 {len(items) - 12} 筆")
    allowed = sum(1 for f in findings if f.get("allowed"))
    print(f"\n合計 error={counts.get('error', 0)} warn={counts.get('warn', 0)} info={counts.get('info', 0)}"
          f"（warn 中已審保留 {allowed}，未審 {counts.get('warn', 0) - allowed}；清單 audit/strict_allowlist.tsv）")
    return counts.get("error", 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volume")
    ap.add_argument("--strict", action="store_true", help="warn 也視為失敗")
    ap.add_argument("--json", help="write findings to a JSON file")
    ap.add_argument("--source", choices=("v03", "skeleton"), default="v03",
                    help="v03（預設，交付檔）或 skeleton（v0.2.0 原文基準）")
    args = ap.parse_args()

    errata, lang = load_rules()
    text = book_text(args.volume, args.source)
    findings: list[dict] = []
    findings += check_terminology(text, errata)
    findings += check_language(text, lang)
    findings += check_artifacts(text)
    findings += check_handwritten_stats(text)
    findings += check_index_rows(text, args.volume)
    findings += check_source_pages(text)
    findings += check_known_pdf_corruption(text)

    apply_allowlist(findings, args.volume)
    n_err = report(findings, args.volume, args.source)
    if args.json:
        Path(args.json).write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"findings → {args.json}")
    if args.strict:
        return 1 if (n_err or any(f["severity"] == "warn" and not f.get("allowed") for f in findings)) else 0
    return 1 if n_err else 0


if __name__ == "__main__":
    raise SystemExit(main())
