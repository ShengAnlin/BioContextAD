#!/bin/bash
# BioContextAD — End-to-end pipeline runner
# Usage: bash scripts/run_all.sh [--dry-run]
# Output: results/ directory + results/weekly_report.md

set -e

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "[dry-run] Skipping API calls, using cached results only."
fi

echo ""
echo "============================================"
echo "  BioContextAD Pipeline"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# Check .env exists
if [ ! -f ".env" ]; then
  echo "ERROR: .env not found. Run: cp .env.example .env and fill in API keys."
  exit 1
fi

mkdir -p results/raw logs

# Step 1: BioRouter (E1)
echo "[1/4] Running BioRouter evaluation (E1)..."
cd src
python run_e1.py --data ../data/eval_questions.jsonl
cd ..
echo "      ✓ E1 complete → results/e1_results.json"
echo ""

# Step 2: Evidence Ranking (E3)
echo "[2/4] Running Evidence Ranking (E3)..."
cd src
python run_e3.py --data ../data/evidence_pairs.jsonl
cd ..
echo "      ✓ E3 complete → results/e3_results.json"
echo ""

# Step 3: Multi-teacher (E4) — runs if evidence_pairs available
echo "[3/4] Skipping E4 (multi-teacher) — run separately after E3."
echo ""

# Step 4: Generate weekly report
echo "[4/4] Generating weekly report..."
cd src
python report.py
cd ..
echo "      ✓ Report → results/weekly_report.md"
echo ""

echo "============================================"
echo "  Pipeline complete."
echo "  Summary: results/weekly_report.md"
echo "============================================"
