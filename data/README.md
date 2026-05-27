# Data

## eval_questions.jsonl

Seed evaluation set for BioRouter (Experiment 1) and RAG (Experiment 3).

Format:
```json
{"id": "q001", "question": "...", "label": "A"}
```

Labels correspond to NIA-AA ATNIV axes: `A`, `T`, `N`, `I`, `V`, `OTHER`.

Phase 1: 30 questions (5 per axis × 6 axes).
Phase 2: expand to 100 questions.

## evidence_pairs.jsonl

(claim, evidence) pairs for evidence ranking evaluation (Experiment 3).

Format:
```json
{"id": "e001", "claim": "...", "evidence": "...", "label": "relevant|irrelevant"}
```

## Note on data privacy

This repository does not contain real patient data. All evaluation questions are
constructed from published AD biomarker research literature.
