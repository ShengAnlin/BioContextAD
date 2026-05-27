# BioContextAD — Pipeline Architecture

## Overview

BioContextAD implements a **biomarker-guided context engineering** framework for LLM-based Alzheimer's disease early screening. The core design principle is that unconstrained LLM inference over clinical questions is unreliable; structured routing through pathological axes and evidence-grounded retrieval substantially improves accuracy and safety.

## Module Descriptions

### 1. BioRouter

**Purpose**: Classify incoming AD queries into one of six pathological axes before retrieval.

**Input**: Free-text question about AD biomarkers, diagnosis, or clinical findings.

**Output**: Axis label ∈ {A, T, N, I, V, OTHER}

**Design**: A lightweight prompt-based classifier. The system prompt provides per-axis definitions, biomarker lists, and few-shot examples aligned to the NIA-AA ATNIV framework. In Phase 2, the router can be replaced with a fine-tuned BGE-M3 + classification head.

**Metric**: Macro-F1 across six classes (balanced evaluation accounting for axis imbalance).

---

### 2. Biomarker-Guided RAG

**Purpose**: Retrieve axis-specific evidence passages from the AD literature corpus and generate a grounded answer.

**Input**: Query + axis label from BioRouter.

**Output**: Answer with cited evidence passages.

**Design**: The retrieval query is rewritten to incorporate axis-specific biomarker terms, improving retrieval precision compared to vanilla query embedding. The generator is prompted to cite specific biomarker findings rather than produce unsupported claims.

**Metric**: Evidence Relevance Score (human-validated or LLM-judged relevance of retrieved passages to the query).

---

### 3. Abstention Module

**Purpose**: Safety and uncertainty gate. Prevents the system from answering queries that are unsafe or unanswerable given available evidence.

**Input**: Original query + axis label.

**Output**: Decision ∈ {ANSWER, ABSTAIN_UNCERTAIN, ABSTAIN_UNSAFE}

**Design**: Three-way classification prompted with explicit safety criteria. Unsafe queries include requests for individual-level clinical diagnosis, treatment recommendations, or queries about specific patients.

**Metric**: Abstention F1 (precision and recall on the ABSTAIN classes).

---

### 4. Evidence Graph

**Purpose**: Lightweight knowledge graph linking AD biomarkers, pathological processes, and findings.

**Implementation**: `networkx` graph stored as `nodes.csv` + `edges.csv`. No external graph database required.

**Node types**: Biomarker, PathologicalProcess, ClinicalFinding, Gene, BrainRegion

**Edge types**: INDICATES, CORRELATES_WITH, PRECEDES, REGULATED_BY

**Use**: Provides structured context for the RAG module and supports evidence tracing in generated answers.

---

### 5. Multi-Teacher Consistency

**Purpose**: Cross-model validation of generated answers using three independent LLM teachers.

**Input**: Query + generated answer from RAG module.

**Output**: Agreement label (CONSISTENT / INCONSISTENT) from each teacher + overall agreement rate.

**Metric**: Agreement Rate and Fleiss' kappa (κ) across three teachers.

**Design**: Teachers are prompted to independently judge whether the generated answer is factually consistent with established AD biomarker knowledge, without seeing each other's responses.

---

### 6. Automated Evaluation Pipeline

**Purpose**: End-to-end automation from question intake to metrics to report.

**Components**:
- `run_all.sh`: Sequential pipeline runner
- `metrics.py`: Macro-F1, Fleiss' κ, confusion matrix, agreement plots
- `report.py`: 6-section weekly Markdown report (auto-generated via LLM)

**Output artifacts**:
- `results/e1_results.json` — BioRouter classification results
- `results/e3_results.json` — Evidence ranking results
- `results/confusion_matrix.png` — Axis-level confusion matrix
- `results/weekly_report.md` — Weekly progress report

---

## Design Decisions

| Decision | Rationale |
|---|---|
| Prompt-based router (not fine-tuned) | Sufficient for dry-run scale (30–50 cases); avoids labeling overhead in Phase 1 |
| networkx over neo4j | Zero infrastructure overhead; graph traversal adequate for <1000 nodes |
| 3 teacher models | Covers three provider families (Anthropic, OpenAI, Baichuan) for diversity |
| Abstention as separate module | Decouples safety logic from answer generation; easier to audit and update |
| Caching all API responses | Enables free reruns for metric recomputation without additional API cost |

---

## Limitations

- This is a research prototype, not a clinical tool.
- The evidence corpus (20–30 papers) is intentionally small for Phase 1; coverage limitations should be reported.
- LLM-based evidence relevance scoring is a proxy metric; ground-truth human annotation is needed for final evaluation.
- Abstention criteria are heuristic; clinical validation of the safety gate is out of scope.
