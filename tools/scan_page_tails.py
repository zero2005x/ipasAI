#!/usr/bin/env python3
"""Find headings stranded at the bottom of a PDF page (heading followed by <= 2 lines of text).

    python tools/scan_page_tails.py build/L22/L22_v0.3_校訂稿.pdf [--tsv out.tsv]

Needs poppler's pdftotext. A heading is a numbered section title (1.2 / 1.2.3 …), a
「模擬題 SIM-…」 or 「題組 SET-…」 title. Exit code 1 when any stranded heading is found.
"""
import re
import subprocess
import sys

HEAD = re.compile(r"^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})*\s+[^\s）)。，、%]|模擬題 SIM-L\d{5}-\d{3}$|題組 SET-|第\s*\d+\s*章\s)")
LABEL = re.compile(r"^(核心必考|官方補充|產業延伸|版本敏感|模擬題 SIM-L\d{5}-\d{3} ｜.*)$")
FOLIO = re.compile(r"^\d{1,3}$")


def pages(pdf: str) -> list[list[str]]:
    txt = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", pdf, "-"],
                         capture_output=True, check=True).stdout.decode("utf-8", "replace")
    return [[l.strip() for l in p.split("\n") if l.strip()] for p in txt.split("\f")]


def main() -> int:
    pdf = sys.argv[1]
    found = []
    for no, lines in enumerate(pages(pdf), start=1):
        body = [l for l in lines if not FOLIO.match(l)]
        tail = body[-3:]
        for k, l in enumerate(tail):
            if HEAD.match(l):
                rest = sum(1 for x in tail[k + 1:] if not LABEL.match(x))
                if rest == 0:            # 標題之後只剩分層標籤或題型列：真正的孤立標題
                    found.append((no, rest, l[:60]))
                break
    for no, rest, l in found:
        print(f"p{no}\t標題後 {rest} 行\t{l}")
    if "--tsv" in sys.argv:
        out = sys.argv[sys.argv.index("--tsv") + 1]
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("頁\t標題後剩餘行數\t頁尾標題\n")
            for no, rest, l in found:
                fh.write(f"{no}\t{rest}\t{l}\n")
    print(f"{pdf}: {len(found)} 個頁尾標題")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
