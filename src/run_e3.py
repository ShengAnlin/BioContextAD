"""
run_e3.py — Experiment 3: Evidence Ranking Evaluation

For each (claim, evidence) pair in data/evidence_pairs.jsonl,
asks the model to judge whether the evidence is relevant to the claim.
Computes precision, recall, and F1 against gold labels.
"""

import json
import argparse
from pathlib import Path
from tqdm import tqdm

from llm_client import call_llm
from metrics import compute_classification_metrics

JUDGE_PROMPT = """You are evaluating whether a retrieved evidence passage is relevant to an AD biomarker claim.

Claim: {claim}

Evidence: {evidence}

Is this evidence passage directly relevant to the claim above?
Respond with exactly one word: RELEVANT or IRRELEVANT.
"""


def judge_pair(claim: str, evidence: str, sample_id: str) -> str:
    prompt = JUDGE_PROMPT.format(claim=claim, evidence=evidence)
    raw = call_llm("evidence", prompt, sample_id=sample_id, task="e3_ranking").strip().upper()
    if "IRRELEVANT" in raw:
        return "irrelevant"
    return "relevant"


def run(data_path: str = "data/evidence_pairs.jsonl", limit: int = None):
    pairs = []
    with open(data_path) as f:
        for line in f:
            pairs.append(json.loads(line.strip()))

    if limit:
        pairs = pairs[:limit]

    predictions, labels = [], []

    for i, item in enumerate(tqdm(pairs, desc="Evidence Ranking")):
        pid = item.get("id", f"e{i:03d}")
        pred = judge_pair(item["claim"], item["evidence"], sample_id=pid)
        predictions.append(pred)
        labels.append(item.get("label", "relevant"))

    metrics = compute_classification_metrics(
        labels, predictions, labels=["relevant", "irrelevant"]
    )

    Path("results").mkdir(exist_ok=True)
    out = {
        "predictions": predictions,
        "labels": labels,
        "metrics": metrics,
        "n_relevant_pred": predictions.count("relevant"),
        "n_irrelevant_pred": predictions.count("irrelevant"),
    }
    with open("results/e3_results.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n=== E3 Evidence Ranking Results ===")
    print(f"Macro-F1 : {metrics['macro_f1']:.4f}")
    print(f"Accuracy : {metrics['accuracy']:.4f}")
    print(f"N samples: {len(predictions)}")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/evidence_pairs.jsonl")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(args.data, args.limit)
