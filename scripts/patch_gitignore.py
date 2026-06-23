"""
patch_gitignore.py
------------------------------------------------------------
Append common scratch / backup patterns to .gitignore so they
are not committed:

  - _backup_*/                  (sync script's pre-overwrite backups)
  - results/raw_backup_*/       (clean_cache's pre-edit snapshots)
  - results/cache_clean_report_*.txt
  - _meta/                      (commit message templates)

Idempotent — only adds entries that aren't already there.

Run from repo root:
    python scripts/patch_gitignore.py
"""
from __future__ import annotations
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GI = ROOT / ".gitignore"

NEW_ENTRIES = [
    "# operational scratch — not part of the published repo",
    "_meta/",
    "_backup_*/",
    "results/raw_backup_*/",
    "results/cache_clean_report_*.txt",
]


def main():
    if not GI.exists():
        print(f"[err] no {GI}")
        sys.exit(1)

    text = GI.read_text(encoding="utf-8")
    existing = set(line.strip() for line in text.splitlines() if line.strip())

    to_add = [e for e in NEW_ENTRIES if e.strip() not in existing]

    if not to_add:
        print("[ok] all entries already present — no change")
        return

    if not text.endswith("\n"):
        text += "\n"
    text += "\n" + "\n".join(to_add) + "\n"

    GI.write_text(text, encoding="utf-8")
    print(f"[ok] added {len(to_add)} entries to .gitignore:")
    for e in to_add:
        print(f"     {e}")


if __name__ == "__main__":
    main()
