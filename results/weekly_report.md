# Weekly Report — 2026-06-17

## 1. Completed experiments
- E1 · BioRouter feasibility probe (30 questions × N models)
- E3 · Evidence ranking three-way agreement (30 pairs × N models)

## 2. Metrics summary
**E1 (router macro-F1):**
- router_fast (n=60): macro-F1 = **1.000**, acc = 1.000, parse_fail = 0
- teacher_medical (n=60): macro-F1 = **1.000**, acc = 1.000, parse_fail = 0
- teacher_premium (n=60): macro-F1 = **1.000**, acc = 1.000, parse_fail = 0

**E3 (evidence Fleiss' κ):** **0.788**  (n_pairs = 30)
- majority distribution: {'SUPPORT': 13, 'REFUTE': 15, 'UNCERTAIN': 1, 'TIE': 1}

## 3. Key observations
- Best router role: **router_fast** with macro-F1 = 1.000.
- router_fast: macro-F1 ≥ 0.70 → BioRouter prompt-only path viable for this model.
- teacher_medical: macro-F1 ≥ 0.70 → BioRouter prompt-only path viable for this model.
- teacher_premium: macro-F1 ≥ 0.70 → BioRouter prompt-only path viable for this model.
- Fleiss' κ = 0.788 ≥ 0.60 (substantial agreement) → multi-teacher consistency usable as paper contribution.

## 4. Failure cases
- No format-level failures detected. Inspect router_results.csv / evidence_results.csv for substantive misroutings.

## 5. Decisions
- Adopt prompt-only BioRouter for the v0 pipeline; defer classification-head training.
- Promote multi-teacher consistency to a primary evaluation axis in the paper.

## 6. Next steps
- Scale eval set from 30 to 100 once dry-run decisions are taken.
- Implement Biomarker-guided RAG module (P0) and Abstention module (P0) — see project tasks.yaml.
- Freeze results/figs/router_confusion.png and results/figs/evidence_agreement.png for the 06-05 GitHub README.