#!/usr/bin/env python3
"""Text integrity guard for iPAS book Markdown files.

Usage:
    python tools/check_text_integrity.py snapshot
    python tools/check_text_integrity.py verify

Snapshot normalizes all book/**/v0.3/*.md and shared/book/**/*.md files,
saving hash, length, and normalized text to tmp/integrity_baseline.json.

Verify recalculates in the exact same way and compares against baseline.
Exits with 1 on any mismatch, showing the file and first diff context.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_FILE = ROOT / "tmp" / "integrity_baseline.json"


def find_target_files() -> list[Path]:
    """Find all book/**/v0.3/*.md and shared/book/**/*.md files."""
    files: list[Path] = []
    # book/*/v0.3 and any subdirectories (like front/)
    for path in (ROOT / "book").glob("*/v0.3/**/*.md"):
        if path.is_file():
            files.append(path)
    for path in (ROOT / "book").glob("*/v0.3/*.md"):
        if path.is_file() and path not in files:
            files.append(path)
    for path in (ROOT / "shared" / "book").glob("**/*.md"):
        if path.is_file():
            files.append(path)
    return sorted(set(files))


def normalize(text: str) -> str:
    """Normalize text according to integrity guard specification:
    1. Table separator rows (|---|---|)
    2. Table pipes (|)
    3. Callout markers (:::type label -> label, standalone ::: -> empty)
    4. Heading hashes at line start (^#+)
    5. Backticks (`)
    6. All whitespace and newlines
    """
    # 1. Table separator rows: line containing only |, -, :, and spaces/tabs
    text = re.sub(r'(?m)^[ \t]*\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)+\|?[ \t]*$', '', text)
    # 2. Table pipes
    text = text.replace('|', '')
    # 3. Callout markers: :::type label -> label, standalone ::: -> empty
    text = re.sub(r'(?m)^[ \t]*:::[a-zA-Z0-9_-]*[ \t]*', '', text)
    # 4. Heading hashes at line start
    text = re.sub(r'(?m)^[ \t]*#+[ \t]*', '', text)
    # 5. Backticks
    text = text.replace('`', '')
    # 6. All whitespace and newlines
    text = re.sub(r'\s+', '', text)
    return text


def compute_file_info(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    norm = normalize(raw)
    sha256 = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    return {
        "relpath": path.relative_to(ROOT).as_posix(),
        "sha256": sha256,
        "length": len(norm),
        "normalized": norm,
    }


def find_diff(s1: str, s2: str) -> str:
    """Return context around the first differing character."""
    min_len = min(len(s1), len(s2))
    diff_idx = min_len
    for i in range(min_len):
        if s1[i] != s2[i]:
            diff_idx = i
            break

    start = max(0, diff_idx - 30)
    end1 = min(len(s1), diff_idx + 30)
    end2 = min(len(s2), diff_idx + 30)
    ctx1 = s1[start:diff_idx] + " >>>[" + (s1[diff_idx:diff_idx+1] if diff_idx < len(s1) else "EOF") + "]<<< " + s1[diff_idx+1:end1]
    ctx2 = s2[start:diff_idx] + " >>>[" + (s2[diff_idx:diff_idx+1] if diff_idx < len(s2) else "EOF") + "]<<< " + s2[diff_idx+1:end2]
    return f"Position {diff_idx}:\n  Baseline: ...{ctx1}...\n  Current:  ...{ctx2}..."


def do_snapshot() -> int:
    files = find_target_files()
    data = {}
    for f in files:
        info = compute_file_info(f)
        data[info["relpath"]] = info
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Snapshot saved: {len(data)} files recorded in {BASELINE_FILE.relative_to(ROOT)}")
    return 0


def do_verify() -> int:
    if not BASELINE_FILE.exists():
        print(f"ERROR: Baseline file missing: {BASELINE_FILE}. Run 'snapshot' first.")
        return 1

    baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
    current_files = find_target_files()
    current_map = {f.relative_to(ROOT).as_posix(): f for f in current_files}

    mismatches = []
    missing_files = []
    new_files = []

    for relpath, base_info in baseline.items():
        if relpath not in current_map:
            missing_files.append(relpath)
            continue
        cur_info = compute_file_info(current_map[relpath])
        if cur_info["sha256"] != base_info["sha256"]:
            diff_msg = find_diff(base_info["normalized"], cur_info["normalized"])
            mismatches.append((relpath, base_info["length"], cur_info["length"], diff_msg))

    for relpath in current_map:
        if relpath not in baseline:
            new_files.append(relpath)

    if missing_files:
        print("ERROR: Missing files found in current tree:")
        for f in missing_files:
            print(f"  - {f}")
    if new_files:
        print("ERROR: Unexpected new files found:")
        for f in new_files:
            print(f"  - {f}")

    if mismatches:
        print(f"ERROR: Text integrity violation in {len(mismatches)} file(s):")
        for relpath, blen, clen, diff_msg in mismatches:
            print(f"\n[{relpath}] (Baseline len: {blen}, Current len: {clen})")
            print(diff_msg)
        return 1

    if missing_files or new_files:
        return 1

    print(f"OK: All {len(baseline)} files verified identical to baseline.")
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("snapshot", "verify"):
        print("Usage: python tools/check_text_integrity.py [snapshot|verify]")
        return 1

    cmd = sys.argv[1]
    if cmd == "snapshot":
        return do_snapshot()
    else:
        return do_verify()


if __name__ == "__main__":
    sys.exit(main())
