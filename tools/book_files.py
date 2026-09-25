"""Shared helpers for locating, expanding and rendering the v0.3 book sources.

Three-volume shared content lives once under ``shared/book/`` (spec §6).  A
volume file with the same relative name overrides the shared copy.  Chapters
may pull a shared module in with ``<!-- include: shared/book/modules/x.md -->``.
Reader-visible counts are written as ``{{stats.key}}`` and rendered from
``book/<VOL>/stats.json`` (spec §7), which ``tools/recount_stats.py`` rebuilds.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared" / "book"
INCLUDE = re.compile(r"^<!--\s*include:\s*(\S+)\s*-->\s*$", re.M)
PLACEHOLDER = re.compile(r"\{\{stats\.([\w.\-]+)\}\}")


def volume_dir(vol: str) -> Path:
    return ROOT / "book" / vol / "v0.3"


def _merged(vol: str, sub: str, pattern: str) -> list[Path]:
    found: dict[str, Path] = {}
    for base in (SHARED / sub, volume_dir(vol) / sub):
        if base.exists():
            for p in base.glob(pattern):
                found[p.name] = p
    return [found[k] for k in sorted(found)]


def volume_files(vol: str) -> list[Path]:
    """Front matter, chapters and appendices in reading order."""
    d = volume_dir(vol)
    front = _merged(vol, "front", "*.md")
    chaps = sorted(d.glob("ch*.md"))
    apx = _merged(vol, "", "apx*.md")
    return front + chaps + apx


def read_expanded(path: Path) -> str:
    """Read a source file with ``<!-- include: ... -->`` lines replaced by the file they name."""
    text = path.read_text(encoding="utf-8")

    def sub(m: re.Match) -> str:
        target = ROOT / m.group(1)
        if not target.exists():
            raise FileNotFoundError(f"{path}: include target missing: {m.group(1)}")
        return target.read_text(encoding="utf-8").rstrip("\n")

    return INCLUDE.sub(sub, text)


def load_stats(vol: str) -> dict:
    return json.loads((ROOT / "book" / vol / "stats.json").read_text(encoding="utf-8"))


def lookup(stats: dict, key: str):
    cur = stats
    for part in key.split("."):
        cur = cur[part]
    return cur


def render_stats(text: str, stats: dict) -> str:
    """Replace ``{{stats.a.b}}`` placeholders; unknown keys raise so a typo cannot ship."""
    return PLACEHOLDER.sub(lambda m: str(lookup(stats, m.group(1))), text)
