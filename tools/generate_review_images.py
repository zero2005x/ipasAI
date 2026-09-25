#!/usr/bin/env python3
"""Generate review page screenshots and stitched overview grid for visual inspection.

Usage:
    python -B tools/generate_review_images.py [L21|L22|L23]
"""
from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def find_review_pages(vol: str, pdf_path: Path) -> list[tuple[str, int]]:
    r = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf_path), "-"],
                       capture_output=True, check=True)
    raw_text = r.stdout.decode("utf-8", "replace")
    pages = raw_text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()

    targets: list[tuple[str, int]] = []
    seen = set()

    def add(lbl: str, pno: int):
        if pno not in seen and 1 <= pno <= len(pages):
            targets.append((lbl, pno))
            seen.add(pno)

    # 1. 封面
    add("01_cover", 1)

    # 2. 前頁各篇第一頁
    front_titles = [
        ("front_免責聲明", ["封面涵蓋範圍與免責"]),
        ("front_法制時間軸", ["AI法制時間軸", "AI 法制時間軸"]),
        ("front_路線導航", ["授證路線導航"]),
        ("front_考綱地圖", ["考綱地圖"]),
        ("front_考試規則", ["考試規則速覽"]),
        (f"front_{vol}答題策略", [f"{vol}答題策略", f"{vol} 答題策略"]),
    ]
    for lbl, titles in front_titles:
        for pno, ptext in enumerate(pages, start=1):
            if any(t in ptext for t in titles):
                add(lbl, pno)
                break

    # 3. 每章章首
    num_chapters = {"L21": 9, "L22": 13, "L23": 12}[vol]
    ch_pages: dict[int, int] = {}
    for ch_idx in range(1, num_chapters + 1):
        pat = re.compile(rf'CHAPTER\s+0?{ch_idx}\b')
        for pno, ptext in enumerate(pages, start=1):
            lines_top = "\n".join(ptext.splitlines()[:5])
            if pat.search(lines_top):
                ch_pages[ch_idx] = pno
                add(f"ch{ch_idx:02d}_head", pno)
                break

    # 4. 考點補丁, 5. 模擬題, 6. 解答區
    for ch_idx in range(1, num_chapters + 1):
        start_p = ch_pages.get(ch_idx, 1)
        next_ch_p = ch_pages.get(ch_idx + 1, len(pages) + 1)

        found_patch = False
        found_sim = False
        found_ans = False
        for pno in range(start_p, next_ch_p):
            ptext = pages[pno - 1]
            if not found_patch and "考點補丁：" in ptext:
                add(f"ch{ch_idx:02d}_patch", pno)
                found_patch = True
            if not found_sim and ("解答見本章末" in ptext or f"SIM-{vol}" in ptext):
                add(f"ch{ch_idx:02d}_sim", pno)
                found_sim = True
            if not found_ans and "模擬題解答與解析" in ptext:
                add(f"ch{ch_idx:02d}_ans", pno)
                found_ans = True

    # 7. 附錄 B 第一頁
    for pno, ptext in enumerate(pages, start=1):
        if "附錄 B" in ptext:
            add("apxB_head", pno)
            break

    # Sort targets by page number
    targets.sort(key=lambda x: x[1])
    return targets


def render_and_stitch(vol: str):
    pdf_path = ROOT / "build" / vol / f"{vol}_v0.3_校訂稿.pdf"
    if not pdf_path.exists():
        print(f"ERROR: {pdf_path} not found.")
        return False

    out_dir = ROOT / "tmp" / "layout_review" / vol
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = find_review_pages(vol, pdf_path)
    print(f"[{vol}] Generating screenshots for {len(targets)} review pages at 60 DPI...")

    rendered_images = []

    for lbl, pno in targets:
        prefix = out_dir / f"p{pno:03d}_{lbl}"
        # pdftoppm appends -<page>.png
        cmd = ["pdftoppm", "-png", "-r", "60", "-f", str(pno), "-l", str(pno), str(pdf_path), str(prefix)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Locate generated file
        candidates = list(out_dir.glob(f"p{pno:03d}_{lbl}*.png"))
        if candidates:
            # Use the newest / matching
            img_path = candidates[0]
            rendered_images.append((lbl, pno, img_path))

    if not rendered_images:
        print(f"[{vol}] No images were rendered.")
        return False

    # Stitch into overview grid
    # Grid: 5 columns
    cols = 5
    rows = math.ceil(len(rendered_images) / cols)

    sample_img = Image.open(rendered_images[0][2])
    thumb_w, thumb_h = sample_img.size
    sample_img.close()

    header_h = 32
    padding = 16
    grid_w = cols * (thumb_w + padding) + padding
    grid_h = rows * (thumb_h + header_h + padding) + padding

    grid_img = Image.new("RGB", (grid_w, grid_h), color=(240, 243, 245))
    draw = ImageDraw.Draw(grid_img)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for idx, (lbl, pno, img_path) in enumerate(rendered_images):
        c = idx % cols
        r = idx // cols

        x = padding + c * (thumb_w + padding)
        y = padding + r * (thumb_h + header_h + padding)

        # Draw label box
        label_text = f"p.{pno} {lbl}"
        draw.rectangle([x, y, x + thumb_w, y + header_h - 4], fill=(15, 92, 110))
        draw.text((x + 6, y + 6), label_text, fill=(255, 255, 255), font=font)

        # Paste page image
        with Image.open(img_path) as page_img:
            grid_img.paste(page_img, (x, y + header_h))

    overview_path = out_dir / "overview.png"
    grid_img.save(overview_path, "PNG")
    print(f"[{vol}] Overview saved → {overview_path} ({grid_w}x{grid_h} px, {len(rendered_images)} pages)")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("volumes", nargs="*", default=["L21", "L22", "L23"])
    args = ap.parse_args()

    for v in args.volumes:
        if not render_and_stitch(v):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
