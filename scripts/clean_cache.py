"""
clean_cache.py  (v2 — aligned with audit_cache.py detection)
------------------------------------------------------------
Scan results/raw/ for cache files whose `text` field contains
a mojibake trailer (English content followed by 8+ corrupted
CJK characters) and truncate it.

v2 changes:
  - Uses the SAME detection regex as audit_cache.py
    (8+ consecutive CJK after English/digit/punctuation),
    so both tools agree on what counts as mojibake.
  - The previous v1 used a stricter sliding-window heuristic
    that missed shorter mojibake trailers.

Non-destructive: backs up results/raw/ to results/raw_backup_<stamp>/
before any in-place edit.

Run from repo root:
    python scripts/clean_cache.py              # do it
    python scripts/clean_cache.py --dry-run    # report only
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import sys
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"

# Same regex as audit_cache.py: an English-ish anchor character
# followed by optional whitespace and 8+ consecutive CJK chars.
MOJIBAKE_TRAILER = re.compile(
    r"[A-Za-z\.\)\]\d][\s\n]*([\u4e00-\u9fff]{8,})"
)
SENTENCE_END = re.compile(r"[\.\?\!][\s\n]+")
CJK = re.compile(r"[\u4e00-\u9fff]")
COMMON_CN = set("的是在一我不了有和也就要这上人来到他时大地为子中你说生国年着")


def looks_legitimate_chinese(s: str) -> bool:
    if not s:
        return False
    hits = sum(1 for ch in s if ch in COMMON_CN)
    return hits / len(s) >= 0.08


def find_trailer_cut(text: str, lookahead: int = 30) -> Optional[int]:
    """Find the start index of the first mojibake CJK trailer, then
    backtrack to the nearest English sentence boundary."""
    if not text:
        return None
    m = MOJIBAKE_TRAILER.search(text)
    if not m:
        return None
    # the CJK group start in the absolute text
    cjk_start = m.start(1)

    # Avoid cutting legitimate Chinese: examine the CJK run, plus continuation
    # of any CJK characters immediately after it.
    j = cjk_start
    while j < len(text) and (CJK.match(text[j]) or text[j] in " 　\n\u3000"):
        j += 1
    cjk_segment = "".join(ch for ch in text[cjk_start:j] if CJK.match(ch))
    if looks_legitimate_chinese(cjk_segment):
        return None

    # Backtrack to last English sentence boundary within [0, cjk_start + lookahead]
    end = min(len(text), cjk_start + lookahead)
    search_region = text[:end]
    boundaries = list(SENTENCE_END.finditer(search_region))
    if boundaries:
        return boundaries[-1].end()
    nl = search_region.rfind("\n")
    if nl >= 0:
        return nl + 1
    return cjk_start


def process_file(fp: pathlib.Path, dry_run: bool, log) -> bool:
    try:
        with open(fp, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        log(f"  [skip] cannot parse: {fp.name} ({e})")
        return False

    text = payload.get("text", "")
    if not isinstance(text, str) or not text:
        return False

    cut = find_trailer_cut(text)
    if cut is None:
        return False

    truncated = text[:cut].rstrip()
    removed = text[cut:]
    log(f"  {fp.relative_to(ROOT)}")
    log(f"    last kept (40c):   ...{text[max(0,cut-40):cut]!r}")
    log(f"    first removed (60c): {removed[:60]!r}")

    if not dry_run:
        payload["text"] = truncated
        payload["_cleaned"] = {
            "removed_chars": len(removed),
            "removed_at": dt.datetime.utcnow().isoformat() + "Z",
            "tool": "clean_cache.py",
        }
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report only, do not modify")
    args = ap.parse_args()

    if not RAW.exists():
        print(f"[err] no {RAW}")
        sys.exit(1)

    cache_files = list(RAW.rglob("*.json"))
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_lines = []

    def log(msg):
        print(msg)
        report_lines.append(msg)

    log(f"Scanning {len(cache_files)} cache files under {RAW}")
    log(f"Mode: {'DRY-RUN (no changes)' if args.dry_run else 'IN-PLACE EDIT'}")
    log("=" * 60)

    if not args.dry_run:
        backup_root = ROOT / "results" / f"raw_backup_{stamp}"
        log(f"Pre-edit backup: {backup_root.name}")
        shutil.copytree(RAW, backup_root)

    modified = 0
    for fp in cache_files:
        if process_file(fp, args.dry_run, log):
            modified += 1

    log("")
    log("=" * 60)
    log(f"  {'Would modify' if args.dry_run else 'Modified'}: {modified} / {len(cache_files)} files")
    log("=" * 60)

    if not args.dry_run and modified > 0:
        report_path = ROOT / "results" / f"cache_clean_report_{stamp}.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        log(f"  Report: {report_path.relative_to(ROOT)}")

    if modified == 0:
        log("  No mojibake trailers detected. Cache is clean.")
    elif not args.dry_run:
        log("  Backup directory left in place. Add to .gitignore before commit:")
        log("    Add-Content .gitignore \"`nresults/raw_backup_*/\"")


if __name__ == "__main__":
    main()
