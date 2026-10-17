#!/usr/bin/env bash
# Rebuilds every table in thesis/analysis/final_validity_audit/ from EXISTING PersistBench outputs. No model, no job, no network.
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
python3 part_a.py   # Steps 1-4: FR@K official vs v1, invalid inventory, rule audit, blind manual audit tables
python3 part_b.py   # Steps 6-8: validity v2, FR@K v2, three-way comparison (+ paired exact sign tests)
python3 part_c.py   # headline-claim checks
python3 part_d.py   # paradox-analysis (strict/broad) sensitivity, reproduces the stored v1 CSV 24/24
python3 part_e.py   # Gemma/Qwen judge-robustness under v2 + scenario-level agreement
python3 part_f.py   # thesis-impact table + full-prompt v1 vs v2
python3 validate_v2.py
