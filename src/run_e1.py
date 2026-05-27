"""
run_e1.py — Experiment 1: BioRouter Evaluation

Classifies each question in data/eval_questions.jsonl into one of
six AD pathological axes (A / T / N / I / V / OTHER) and computes
macro-F1 against gold labels.
"""

import json
import argparse
from pathlib import Path
from tqdm import tqdm

from llm_client import call_llm
from metrics import compute_classification_metrics

PROMPT_TEMPLATE = Path("prompts/router_prompt.md").read_text()

AXES = ["A", "T", "N", "I", "V", "OTHER"]


def classify_question(question: str, sample_id: str) -> str:
    prompt = PROMPT_TEMPLATE + f"\n\n---\nQuestion: {question}\n\nAxis:"
    raw = call_llm("router", prompt, sample_id=sample_id, task="e1_router").strip()
    # Extract axis label from response
    for axis in AXES:
        if raw.upper().startswith(axis):
            return axis
    return "OTHER"


def run(data_path: str = "data/eval_questions.jsonl", limit: int = None):
    questions = []
    with open(data_path) as f:
        for line in f:
            questions.append(json.loads(line.strip()))

    if limit:
        questions = questions[:limit]

    predictions, labels = [], []

    for i, item in enumerate(tqdm(questions, desc="BioRouter")):
        qid = item.get("id", f"q{i:03d}")
        pred = classify_question(item["question"], sample_id=qid)
        predictions.append(pred)
        labels.append(item.get("label", "OTHER"))

    metrics = compute_classification_metrics(labels, predictions, labels=AXES)

    # Save results
    Path("results").mkdir(exist_ok=True)
    out = {"predictions": predictions, "labels": labels, "metrics": metrics}
    with open("results/e1_results.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n=== E1 BioRouter Results ===")
    print(f"Macro-F1 : {metrics['macro_f1']:.4f}")
    print(f"Accuracy : {metrics['accuracy']:.4f}")
    print(f"N samples: {len(predictions)}")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/eval_questions.jsonl")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(args.data, args.limit)
