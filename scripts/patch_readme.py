"""
patch_readme.py
------------------------------------------------------------
Append a short "Known Limitations" note to README.md documenting:

  1. The 53 cached responses that contain a Chinese follow-up
     prompt from Baichuan-M3-Plus, why they exist, and why they
     are kept verbatim.
  2. The placeholder folder named
     `{configs,data,prompts,src,notebooks,results,docs,scripts}`
     which is a relic of an early `mkdir -p {a,b,c}` shell idiom
     that did not brace-expand under PowerShell.

The patch is idempotent — if the section already exists it is
not re-added.

Run from repo root:
    python scripts/patch_readme.py
"""
from __future__ import annotations
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

MARKER = "<!-- BEGIN: cached-response-notes -->"
END_MARKER = "<!-- END: cached-response-notes -->"

SECTION = f"""
{MARKER}
## Notes on cached responses

The 270 JSON files under `results/raw/` are the verbatim API
responses produced during the Phase 1 evaluation runs. Two
properties of these files are documented here so future readers
know what to expect:

1. **Trailing Chinese follow-up prompts (53 / 270 files).** The
   Baichuan-M3-Plus role (`teacher_medical`) often appends a
   short Chinese sentence offering further retrieval, e.g.
   "我建议您进一步查阅...". This is the model's natural
   behaviour and is kept verbatim in the cache so that the
   recorded responses match what the API returned. Axis labels
   (`AXIS:` / `LABEL:`) appear before this trailer and are
   unaffected by it; reported metrics are computed from the
   labelled prefix.

2. **`{{configs,data,prompts,src,notebooks,results,docs,scripts}}`
   folder.** This is a relic of an early `mkdir -p {{a,b,c}}`
   shell idiom that PowerShell did not brace-expand. It is empty
   and will be removed in a follow-up cleanup commit. It does
   not affect any pipeline.
{END_MARKER}
"""


def main():
    if not README.exists():
        print(f"[err] no {README}")
        sys.exit(1)

    text = README.read_text(encoding="utf-8")

    if MARKER in text:
        print("[ok] section already present — no change")
        return

    # Append at the very end, after a blank line
    if not text.endswith("\n"):
        text += "\n"
    text += SECTION

    README.write_text(text, encoding="utf-8")
    print(f"[ok] appended Notes section to {README.relative_to(ROOT)}")
    print(f"     ({len(SECTION)} chars added)")


if __name__ == "__main__":
    main()
