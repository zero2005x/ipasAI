"""Recompute reader-visible counts from the v0.3 sources into book/<VOL>/stats.json.

Usage: python tools/recount_stats.py L21 [L22 L23]

Spec §7: every number the reader sees (mock-question counts, program-question
counts, announced-question density) is computed, never typed.  Chapters refer to
these values as ``{{stats.key}}``; see tools/book_files.py.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from book_files import ROOT, read_expanded, volume_dir  # noqa: E402

SIM_HEAD = re.compile(r"^#### 模擬題 (SIM-L\d{5}-\d{3})", re.M)
SIM_LINE = re.compile(r"^模擬題 (SIM-L\d{5}-\d{3}) ｜ ([^｜]+)｜", re.M)
OFFICIAL = re.compile(r"^\|?\s*OFFICIAL[-‑–](?:114|115)[-‑–]\d[-‑–]L2\d[-‑–]Q\d+", re.M)
CODE = re.compile(r"^\| 官方代碼 \| (L2\d{4}) \|", re.M)
TITLE = re.compile(r"^## 第\s*\d+\s*章\s*(.+)$", re.M)


def recount(vol: str) -> dict:
    path = ROOT / "book" / vol / "stats.json"
    stats = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"volume": vol}
    sim, prog, off, code_of, title_of, tiers = {}, {}, {}, {}, {}, {}
    by_code: dict[str, int] = {}
    for f in sorted(volume_dir(vol).glob("ch*.md")):
        t = read_expanded(f)
        ids = sorted(set(SIM_HEAD.findall(t)))
        kinds = {sid: kind.strip() for sid, kind in SIM_LINE.findall(t)}
        sim[f.stem] = len(ids)
        prog[f.stem] = sum(1 for i in ids if kinds.get(i, "").startswith("程式判讀"))
        off[f.stem] = len(OFFICIAL.findall(t))
        m = CODE.search(t)
        code_of[f.stem] = m.group(1) if m else "?"
        tm = TITLE.search(t)
        title_of[f.stem] = tm.group(1).strip() if tm else f.stem
        # tier label = the line right after a ####-level knowledge-point heading
        lines = t.split("\n")
        cnt = {"核心必考": 0, "官方補充": 0, "產業延伸": 0}
        for i, ln in enumerate(lines[:-1]):
            if re.match(r"^#### \d+\.\d+\.\d+ ", ln):
                nxt = lines[i + 1].strip()
                for k in cnt:
                    if nxt.startswith(k):
                        cnt[k] += 1
        tiers[f.stem] = f"核心必考 {cnt['核心必考']}／官方補充 {cnt['官方補充']}／產業延伸 {cnt['產業延伸']} 節"
        for i in ids:
            c = i.split("-")[1]
            by_code[c] = by_code.get(c, 0) + 1
    total_off = sum(off.values()) or 1
    pct = {k: round(100 * v / total_off) for k, v in off.items()}
    rows = sorted(off, key=lambda k: (-off[k], k))
    table = ["| 代碼 | 章 | 公告試題對位題數 | 佔比 | 本書模擬題 |", "| --- | --- | --- | --- | --- |"]
    table += [f"| {code_of[k]} | {title_of[k]} | {off[k]} | {pct[k]}% | {sim[k]} |" for k in rows]
    stats.update({
        "sim_total": sum(sim.values()),
        "sim_by_chapter": sim,
        "sim_by_code": dict(sorted(by_code.items())),
        "program_sim_total": sum(prog.values()),
        "chapters": len(sim),
        "sim": sim,
        "prog": prog,
        "official": off,
        "official_pct": pct,
        "official_total": sum(off.values()),
        "tiers": tiers,
        "density_table": "\n".join(table),
    })
    path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def main() -> int:
    vols = sys.argv[1:] or ["L21", "L22", "L23"]
    for v in vols:
        s = recount(v)
        print(f"{v}: sims={s['sim_total']} program={s['program_sim_total']} official={s['official_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
