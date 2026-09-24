#!/usr/bin/env python3
"""Split a volume's skeleton into per-chapter v0.3 working files and emit a
review report of every P0 item.

    python3 tools/make_v03.py L21

Outputs (under book/<VOL>/v0.3/):
    front/00_cover.md ...        front matter split into workable units
    ch01.md ... ch09.md          one file per chapter (9 fixed sections each)
    apxA.md, apxB.md             appendices
    REVIEW.md                    P0 checklist + checker findings, per chapter
    MANIFEST.json                file list with byte sizes and line counts

Rationale: the shared content (免責聲明、分層標籤、法制時間軸、考試規則、附錄 A) is
maintained once in shared/ and injected at compile time, so those blocks are
extracted here for review but marked SHARED.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FIXED_SECTIONS = [
    "核心概念與技術原理",
    "應用規劃與決策流程",
    "常見陷阱與錯誤觀念",
    "政府指引與產業落地實務",
    "正式公告試題索引",
    "自編模擬題",
    "章末複習",
]


def load(vol: str):
    d = ROOT / "book" / vol
    text = (d / "skeleton.md").read_text(encoding="utf-8")
    toc = json.loads((d / "toc.json").read_text(encoding="utf-8"))
    stats = json.loads((d / "stats.json").read_text(encoding="utf-8"))
    return text, toc, stats


def slug(vol: str, ch: dict) -> str:
    if ch["kind"] == "chapter":
        return f"ch{ch['num']:02d}"
    return f"apx{ch['label']}"


def heading_of(vol: str, ch: dict) -> str:
    if ch["kind"] == "chapter":
        return f"## 第 {ch['num']}章 {ch['title']}"
    return f"## 附錄 {ch['label']}：{ch['title']}"


def split_volume(text: str, vol: str, toc: list[dict]) -> dict[str, str]:
    """Cut the skeleton at '## ' headings that match the TOC chapters."""
    lines = text.split("\n")
    # The printed TOC repeats every chapter as "## 第 N章 標題", so the first
    # occurrence of each heading is NOT the body. Keep the LAST occurrence of
    # each chapter key, which is the real chapter start.
    last: dict[str, tuple[int, dict]] = {}
    for i, l in enumerate(lines):
        if not l.startswith("## "):
            continue
        for ch in toc:
            want = (f"第 {ch['num']}章" if ch["kind"] == "chapter"
                    else f"附錄 {ch['label']}")
            if l.startswith(f"## {want}"):
                last[slug(vol, ch)] = (i, ch)
                break

    body_marks = sorted(last.values(), key=lambda t: t[0])

    out: dict[str, str] = {}
    for idx, (start, ch) in enumerate(body_marks):
        end = body_marks[idx + 1][0] if idx + 1 < len(body_marks) else len(lines)
        chunk = "\n".join(lines[start:end]).rstrip() + "\n"
        out[slug(vol, ch)] = chunk
    # front matter = everything before the first body chapter, minus the printed TOC
    first = body_marks[0][0] if body_marks else len(lines)
    out["front"] = "\n".join(lines[:first]).rstrip() + "\n"
    return out


def front_units(front: str) -> dict[str, str]:
    """Split front matter into named units so shared blocks can be identified."""
    units: dict[str, str] = {}
    lines = front.split("\n")
    # drop the printed TOC block (dot-leader lines and their section headings)
    keep = [l for l in lines if not re.search(r"(\s\.\s){3,}", l)]
    front = "\n".join(keep)
    names = ["免責與使用聲明", "導讀", "授證路線導航", "考試規則速覽",
             "考綱地圖", "我國 AI法制時間軸", "L21答題策略"]
    idxs = []
    for n in names:
        m = re.search(rf"^{re.escape(n)}", front, re.M)
        if m:
            idxs.append((m.start(), n))
    idxs.sort()
    for i, (pos, n) in enumerate(idxs):
        end = idxs[i + 1][0] if i + 1 < len(idxs) else len(front)
        units[n] = front[pos:end].strip() + "\n"
    return units


def checker_findings(vol: str) -> list[dict]:
    """Re-derive findings without writing files."""
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        tmp = tf.name
    subprocess.run(["python3", str(ROOT / "tools" / "check_book.py"), vol, "--json", tmp],
                   capture_output=True, cwd=ROOT)
    try:
        return json.loads(Path(tmp).read_text(encoding="utf-8"))
    except Exception:
        return []


def build_review(vol: str, toc: list[dict], stats: dict, chunks: dict[str, str],
                 findings: list[dict]) -> str:
    by_page: dict[str, list[dict]] = {}
    for f in findings:
        by_page.setdefault(str(f.get("volume_page", "?")), []).append(f)

    out = [f"# {vol} v0.3 待辦與稽核報告", "",
           "由 `tools/make_v03.py` 產生。自動檢查結果以 `tools/check_book.py` 為準。", "",
           "## 自動檢查摘要", ""]
    sev: dict[str, int] = {}
    for f in findings:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1
    out.append(f"- error（P0，阻斷編譯）：**{sev.get('error', 0)}**")
    out.append(f"- warn（須檢視）：{sev.get('warn', 0)}")
    out.append(f"- info（僅提示）：{sev.get('info', 0)}")
    out.append("")
    chk: dict[str, int] = {}
    for f in findings:
        chk[f["check"]] = chk.get(f["check"], 0) + 1
    out.append("| 檢查 | 筆數 |")
    out.append("|---|---|")
    for k, v in sorted(chk.items(), key=lambda kv: -kv[1]):
        out.append(f"| {k} | {v} |")
    out.append("")

    out += ["## 統計（唯一來源：stats.json）", "",
            f"- 模擬題總數：**{stats['sim_total']}**",
            f"- 程式題：**{stats['program_sim_total']}**",
            f"- 章節數：{stats['chapters']}　節數：{stats['sections']}", "",
            "| 代碼 | 模擬題 |", "|---|---|"]
    for k, v in stats["sim_by_code"].items():
        out.append(f"| {k} | {v} |")
    out.append("")

    out += ["## 章節檔案", "", "| 檔 | 章 | 節 |", "|---|---|---|"]
    for ch in toc:
        key = slug(vol, ch)
        title = ch["title"]
        secs = "、".join(s["num"] for s in ch["sections"])
        out.append(f"| `{key}.md` | {title} | {secs} |")
    out.append("")

    out += ["## 每章待辦（依 PDF 頁碼分組）", ""]
    for idx, ch in enumerate(toc):
        key = slug(vol, ch)
        lo = ch["pdf_page"]
        hi = toc[idx + 1]["pdf_page"] if idx + 1 < len(toc) else 10 ** 6
        hits = [f for f in findings
                if isinstance(f.get("volume_page"), int) and lo <= f["volume_page"] < hi]
        errs = sum(1 for h in hits if h["severity"] == "error")
        out.append(f"### {key} {ch['title']}（p{lo} 起｜error {errs}）")
        if not hits:
            out.append("- 自動檢查無發現")
        else:
            for h in sorted(hits, key=lambda x: (x["severity"] != "error", x["line"]))[:20]:
                tag = {"error": "✗", "warn": "!", "info": "·"}[h["severity"]]
                tgt = f" → {h['should_be']}" if h["should_be"] else ""
                out.append(f"- {tag} p{h['volume_page']} {h['found'][:40]}{tgt}")
            if len(hits) > 20:
                out.append(f"- … 其餘 {len(hits) - 20} 筆見 `check_book.py --json`")
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volume")
    ap.add_argument("--force", action="store_true",
                    help="覆寫已存在的章節檔（會蓋掉你的編輯！）")
    ap.add_argument("--review-only", action="store_true",
                    help="只重生 REVIEW.md 與 MANIFEST.json，不動章節檔")
    args = ap.parse_args()
    vol = args.volume

    text, toc, stats = load(vol)
    outdir = ROOT / "book" / vol / "v0.3"
    (outdir / "front").mkdir(parents=True, exist_ok=True)

    chunks = split_volume(text, vol, toc)
    manifest = []
    skipped = []

    def emit(rel: str, content: str, overwrite: bool = True):
        p = outdir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not overwrite:
            skipped.append(rel)
        else:
            p.write_text(content, encoding="utf-8")
        manifest.append({"file": rel, "bytes": len(content.encode("utf-8")),
                         "lines": content.count("\n") + 1})

    if not args.review_only:
        for name, content in front_units(chunks.get("front", "")).items():
            safe = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name).strip("_")
            emit(f"front/{safe}.md", content, overwrite=args.force)
        for key, content in chunks.items():
            if key == "front":
                continue
            emit(f"{key}.md", content, overwrite=args.force)

    # Always re-run the checker here: findings must reflect the files as they are
    # on disk right now, not the state before other tools edited them.
    findings = checker_findings(vol)
    emit("REVIEW.md", build_review(vol, toc, stats, chunks, findings))

    (outdir / "MANIFEST.json").write_text(
        json.dumps({"volume": vol, "files": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{vol} → book/{vol}/v0.3/")
    if skipped:
        print(f"  ⚠ 保留既有編輯、未覆寫 {len(skipped)} 個檔案：{', '.join(skipped[:6])}"
              f"{' …' if len(skipped) > 6 else ''}")
        print("    （首次產生或要重新產生時加 --force）")
    for m in manifest:
        print(f"  {m['file']:<28} {m['lines']:>5} lines")
    errs = sum(1 for f in findings if f["severity"] == "error")
    print(f"  findings: error={errs} warn={sum(1 for f in findings if f['severity']=='warn')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
