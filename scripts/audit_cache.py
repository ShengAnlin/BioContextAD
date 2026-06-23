"""
audit_cache.py  (v3)
------------------------------------------------------------
Pre-commit safety scan for cached LLM responses under
results/raw/. Flags two severities:

  HIGH  — never acceptable, must redact (API keys, emails, phones)
  WATCH — model self-identification or trailing Chinese follow-ups
          (informational, not blocking)

v3 changes vs v2:
  - Renamed "mojibake_trailer" detector to "chinese_followup".
    Initial inspection of the PowerShell-rendered cache made these
    runs look like mojibake, but inline Python inspection confirmed
    they are valid UTF-8 Chinese — typically a Baichuan-M3-Plus
    follow-up prompt offering further retrieval ("我建议您进一步查阅...").
    They are part of the model's natural behaviour and do not affect
    axis-level labels.
  - Adjusted the summary text accordingly: this finding no longer
    recommends running clean_cache.py.

Run from repo root:
    python scripts/audit_cache.py
"""
from __future__ import annotations
import json
import pathlib
import re
import sys
from collections import defaultdict, Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "results" / "raw"

PATTERNS = {
    "HIGH api_key_like":     re.compile(r"sk-[A-Za-z0-9_]{16,}"),
    "HIGH email":            re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "HIGH cn_phone":         re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "WATCH baichuan_zh":     re.compile(r"百川"),
    "WATCH baichuan_en":     re.compile(r"\bBaichuan\b", re.IGNORECASE),
    "WATCH deepseek":        re.compile(r"\bDeepSeek\b", re.IGNORECASE),
    "WATCH qwen":            re.compile(r"\bQwen\b", re.IGNORECASE),
    "WATCH claude":          re.compile(r"\bClaude\b", re.IGNORECASE),
    "WATCH openai_or_gpt":   re.compile(r"\b(OpenAI|GPT-\d)\b", re.IGNORECASE),
    "WATCH paratera":        re.compile(r"paratera", re.IGNORECASE),
}

# Detector for "English content followed by 8+ Chinese characters".
# Originally labelled mojibake; verified to be legitimate Chinese
# follow-ups from Baichuan-M3-Plus. Kept as a WATCH-level signal so
# the user can see how many cached responses include the trailer.
CHINESE_FOLLOWUP = re.compile(
    r"[A-Za-z\.\)\]\d][\s\n]*[\u4e00-\u9fff]{8,}"
)


def main():
    if not RAW.exists():
        print(f"[err] no {RAW}")
        sys.exit(1)

    cache_files = list(RAW.rglob("*.json"))
    print(f"Scanning {len(cache_files)} cache files under {RAW}")
    print("=" * 60)

    findings = defaultdict(list)
    high_count = 0
    watch_count = 0
    followup_count = 0

    for fp in cache_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            findings[fp].append(("HIGH json_parse_error", [str(e)]))
            high_count += 1
            continue

        haystack_parts = []
        if isinstance(payload.get("text"), str):
            haystack_parts.append(payload["text"])
        if isinstance(payload.get("model"), str):
            haystack_parts.append(payload["model"])
        haystack = "\n".join(haystack_parts)

        if not haystack:
            continue

        for label, pat in PATTERNS.items():
            matches = pat.findall(haystack)
            if matches:
                uniq = sorted(set(matches))
                findings[fp].append((label, uniq[:5]))
                if label.startswith("HIGH"):
                    high_count += 1
                else:
                    watch_count += 1

        text = payload.get("text", "")
        if isinstance(text, str) and CHINESE_FOLLOWUP.search(text):
            findings[fp].append(("WATCH chinese_followup", ["<Chinese run after English>"]))
            followup_count += 1

    high_files = [(p, fs) for p, fs in findings.items() if any(l.startswith("HIGH") for l, _ in fs)]
    watch_files = [(p, fs) for p, fs in findings.items() if not any(l.startswith("HIGH") for l, _ in fs)]

    if high_files:
        print()
        print("=" * 60)
        print(f"  HIGH-SEVERITY: {len(high_files)} files (review immediately)")
        print("=" * 60)
        for p, fs in high_files:
            rel = p.relative_to(ROOT)
            print(f"\n  {rel}")
            for label, examples in fs:
                print(f"    [{label}] examples: {examples}")

    if watch_files:
        print()
        print("=" * 60)
        print(f"  WATCH-LEVEL: {len(watch_files)} files (model IDs / Chinese follow-ups)")
        print("=" * 60)
        label_counter = Counter()
        for p, fs in watch_files:
            for label, _ in fs:
                label_counter[label] += 1
        for label, n in label_counter.most_common():
            print(f"    {label}: {n} files")
        print()
        print("  Showing first 5 watch-level files for spot-check:")
        for p, fs in watch_files[:5]:
            rel = p.relative_to(ROOT)
            print(f"    {rel}")
            for label, examples in fs:
                print(f"      [{label}] examples: {examples[:3]}")

    print()
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Total scanned:           {len(cache_files)}")
    print(f"  HIGH findings:           {high_count}")
    print(f"  WATCH (model IDs):       {watch_count}")
    print(f"  WATCH (chinese_followup):{followup_count}")
    print()

    if high_count > 0:
        print("  >>> ACTION REQUIRED: review HIGH findings above before commit.")
        sys.exit(2)
    if followup_count > 0:
        print(f"  Note: {followup_count} cached responses contain a Chinese")
        print( "  follow-up prompt (e.g. Baichuan offering further retrieval).")
        print( "  This is the model's natural behaviour and does not affect")
        print( "  axis-level labels. The README documents this under Known")
        print( "  Limitations. No cleanup is required.")
        print()
    if watch_count > 0:
        print("  Model self-mentions are expected — the model name lives in")
        print("  the `model` field of every cache entry by design, and the")
        print("  README already attributes results to the three backbones.")
        print()
    print("  Safe to proceed with: git add -A && git commit ... && git push")
    sys.exit(0)


if __name__ == "__main__":
    main()
