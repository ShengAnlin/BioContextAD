"""
metrics.py — Evaluation metrics for BioContextAD

Includes:
  - Macro-F1 and per-class metrics for BioRouter (E1)
  - Evidence relevance scoring (E3)
  - Fleiss' kappa for multi-teacher agreement (E4)
  - Confusion matrix visualization
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional

from sklearn.metrics import (
    f1_score, accuracy_score, classification_report, confusion_matrix
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


# ── Classification (E1 BioRouter) ────────────────────────────────────────────
def compute_classification_metrics(
    labels: List[str],
    predictions: List[str],
    labels: List[str] = None,
) -> Dict:
    macro_f1  = f1_score(labels, predictions, average="macro", zero_division=0)
    accuracy  = accuracy_score(labels, predictions)
    report    = classification_report(labels, predictions, zero_division=0, output_dict=True)
    return {
        "macro_f1": macro_f1,
        "accuracy": accuracy,
        "per_class": report,
    }


def plot_confusion_matrix(
    labels: List[str],
    predictions: List[str],
    class_names: List[str],
    save_path: str = "results/confusion_matrix.png",
):
    cm = confusion_matrix(labels, predictions, labels=class_names)
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=class_names, yticklabels=class_names, ax=ax
    )
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("BioRouter Confusion Matrix")
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Confusion matrix saved to {save_path}")


# ── Fleiss' Kappa (E4 Multi-teacher) ─────────────────────────────────────────
def fleiss_kappa(ratings: List[List[str]]) -> float:
    """
    Compute Fleiss' kappa for multi-rater agreement.

    Args:
        ratings: List of [rater1_label, rater2_label, rater3_label] per item

    Returns:
        Fleiss' kappa coefficient
    """
    n_items = len(ratings)
    n_raters = len(ratings[0])
    categories = sorted(set(r for row in ratings for r in row))
    n_cats = len(categories)
    cat_idx = {c: i for i, c in enumerate(categories)}

    # Build n x k matrix
    mat = np.zeros((n_items, n_cats), dtype=int)
    for i, row in enumerate(ratings):
        for r in row:
            mat[i, cat_idx[r]] += 1

    # Observed agreement
    P_i = (np.sum(mat ** 2, axis=1) - n_raters) / (n_raters * (n_raters - 1))
    P_bar = np.mean(P_i)

    # Expected agreement
    p_j = np.sum(mat, axis=0) / (n_items * n_raters)
    P_e = np.sum(p_j ** 2)

    if P_e == 1.0:
        return 1.0
    return (P_bar - P_e) / (1 - P_e)


def compute_agreement(teacher_outputs: List[Dict]) -> Dict:
    """
    Compute agreement rate and Fleiss' kappa across teacher models.

    Args:
        teacher_outputs: List of dicts with keys 'id', 'teacher_1', 'teacher_2', 'teacher_3'

    Returns:
        Dict with agreement_rate and kappa
    """
    ratings = [
        [item["teacher_1"], item["teacher_2"], item["teacher_3"]]
        for item in teacher_outputs
    ]
    # Simple agreement: all three agree
    agreement_rate = sum(
        1 for row in ratings if len(set(row)) == 1
    ) / len(ratings)

    kappa = fleiss_kappa(ratings)

    return {
        "agreement_rate": agreement_rate,
        "fleiss_kappa": kappa,
        "n_items": len(ratings),
    }


def plot_agreement(teacher_outputs: List[Dict], save_path: str = "results/agreement.png"):
    labels_per_teacher = {
        "Teacher 1": [x["teacher_1"] for x in teacher_outputs],
        "Teacher 2": [x["teacher_2"] for x in teacher_outputs],
        "Teacher 3": [x["teacher_3"] for x in teacher_outputs],
    }
    fig, ax = plt.subplots(figsize=(8, 4))
    categories = sorted(set(
        v for vals in labels_per_teacher.values() for v in vals
    ))
    x = np.arange(len(categories))
    width = 0.25
    for i, (name, vals) in enumerate(labels_per_teacher.items()):
        counts = [vals.count(c) for c in categories]
        ax.bar(x + i * width, counts, width, label=name)
    ax.set_xticks(x + width)
    ax.set_xticklabels(categories)
    ax.set_ylabel("Count")
    ax.set_title("Multi-Teacher Label Distribution")
    ax.legend()
    plt.tight_layout()
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    print(f"Agreement plot saved to {save_path}")
