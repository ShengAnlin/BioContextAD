"""
report.py — Automated 6-section weekly report generator

Sections:
  1. Completed Experiments
  2. Metrics Summary
  3. Key Observations
  4. Failure Cases
  5. Decisions
  6. Next Steps
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional

from llm_client import call_llm


REPORT_PROMPT = """You are a research assistant writing a concise weekly progress report for a biomedical AI project.

Project: BioContextAD — Biomarker-Guided Context Engineering for Alzheimer's Disease Early Screening

Given the following experiment results, write a structured report with exactly 6 sections:

## 1. Completed Experiments
## 2. Metrics Summary
## 3. Key Observations
## 4. Failure Cases
## 5. Decisions
## 6. Next Steps

Be precise and academic. Use bullet points. Do not add preamble.

Experiment Results:
{results_json}
"""


def generate_report(results: Dict, save_path: str = "results/weekly_report.md") -> str:
    prompt = REPORT_PROMPT.format(results_json=json.dumps(results, indent=2, ensure_ascii=False))
    report_text = call_llm("report", prompt, sample_id="weekly", task="report", use_cache=False)

    header = f"# BioContextAD Weekly Report\n\n**Generated**: {time.strftime('%Y-%m-%d %H:%M')}\n\n---\n\n"
    full_report = header + report_text

    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    with open(save_path, "w") as f:
        f.write(full_report)

    print(f"Weekly report saved to {save_path}")
    return full_report


def load_results() -> Dict:
    results = {}
    result_files = {
        "e1_router":   "results/e1_results.json",
        "e3_evidence": "results/e3_results.json",
        "e4_teacher":  "results/e4_results.json",
    }
    for key, path in result_files.items():
        if Path(path).exists():
            with open(path) as f:
                results[key] = json.load(f)
    return results


if __name__ == "__main__":
    results = load_results()
    if not results:
        print("No results found. Run experiments first.")
    else:
        generate_report(results)
