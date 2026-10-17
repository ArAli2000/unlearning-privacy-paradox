# Phase 01 — TOFU baselines

**This is real, completed research history, not obsolete clutter.** It establishes the baseline every later phase builds on.

## 1. Question investigated
Does the open-unlearning framework correctly run all standard unlearning methods end-to-end, and what do their baseline results look like at small model scale, before any thesis-specific extension exists?

## 2. Dataset / models / methods
TOFU (`f10`, 10%-forget split); Llama-3.2-1B, Qwen2.5-1.5B, Qwen2.5-3B; all 10 upstream methods — CEU, GradAscent, GradDiff, NPO, PDU, RMU, SatImp, SimNPO, UNDIAL, WGA.

## 3. Key scripts / manifests / configs
- `scripts/run_qwen15_methods_a180.sh`, `run_llama1b_paper_methods_a180.sh`, `run_llama1b_other_methods_fullmetrics_a180.sh`, `run_qwen3b_selected_methods_a100.sh`, `run_qwen3b_all_methods_fullmetrics_a180.sh`
- `manifests/` — 20 frozen `trainer_state.json` snapshots for the `paper_llama32_1b_*_f10_a180[_fullmetrics]` runs (checkpoints themselves remain in `saves/unlearn/`, not copied here)
- `configs/tofu_partial_backup.yaml` — moved here 2026-09-14 from `configs/eval/tofu_partial_backup.yaml` (was sitting untouched at repo root, undecided). Its mtime (2026-05-24 12:49) is exactly one minute before the live `configs/eval/tofu.yaml`'s own mtime (12:50:25) — this is the config's state immediately before the MIA scores (`mia_loss`/`mia_zlib`/`mia_min_k`/`mia_min_k_plus_plus`), `exact_memorization`, and `forget_Q_A_gibberish` metrics were uncommented (it has them commented out; the live file has them enabled). Both changes happened the same day this phase's "paper methods" (partial-metrics) and "other methods, full metrics" script batches were both run (`run_llama1b_other_methods_fullmetrics_a180.sh`, 2026-05-24 13:34) — this file is the frozen "partial metrics" counterpart to that split, kept here rather than left stranded at repo root.

## 4. What was learned
All 10 methods run correctly on this codebase. Established the standard TOFU metric set (ROUGE-based knowledge/verbatim memorization, `extraction_strength`, `exact_memorization`, `forget_Q_A_Prob`, `forget_truth_ratio`, 4 MIA scores, `model_utility`) as the baseline, before any custom checkpoint-selection logic existed.

## 5. Why the thesis moved on
No checkpoint-selection mechanism existed yet — checkpoints were saved on a fixed schedule, not selected by any metric. Model sizes (1B–3B) and the 10%-forget split were too small to support the thesis's eventual larger-scale claims.

## 6. Influence on final methodology
Direct precursor establishing which methods (SatImp/SimNPO/RMU/WGA) were viable candidates, carried into every subsequent phase through to the final MUSE-News/MUSE-Books work in `../../thesis/`.
