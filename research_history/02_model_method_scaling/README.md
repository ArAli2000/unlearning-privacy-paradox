# Phase 02 — Model/method scaling

**This is real, completed research history, not obsolete clutter.**

## 1. Question investigated
Do the same methods and results hold up at much larger model scale (up to 14B), on the full (100%) TOFU forget set rather than the 10% subset, and does PrivacyLens as a second evaluation axis change the picture?

## 2. Dataset / models / methods
TOFU (`f10`, then full/100% forget); Llama-3.1-8B, Llama-3.2-3B, Qwen2.5-3B/7B/14B; narrowed to a top method subset (SatImp/SimNPO/RMU/WGA).

## 3. Key scripts / configs / manifests
- `scripts/run_7bscale_top3_fullmetrics_a180.sh`, `run_llama32_3b_qwen7b_top3_fullmetrics_a180.sh`, `run_privacylens_full_before_after.sh` (+ its byte-identical `.bak_raw_base`, kept alongside it — see `thesis_cleanup_audit/DELETE_CANDIDATES_FINAL.md`) — first PrivacyLens use in the thesis
- `scripts/run_qwen_tofu_full_finetune_array.sh`, `run_qwen_tofufull_unlearn_best_array.sh`
- `scripts/run_llama31_8b_tofufull_unlearn_{4methods_clean,best_array,remaining3_aggproxy}.sh` — documents a deliberate same-day switch from `Selection_proxy` (no privacy term) to `Agg_proxy` (with an MIA-derived privacy term) for checkpoint selection
- `scripts/run_qwen25_14b_tofufull_{finetune,unlearn_4methods_aggproxy,unlearn_remaining_wga_satimp_h200}.sh`
- `scripts/run_privacylens_{llama32_3b,llama31_8b,qwen,qwen25_14b}_tofufull_methods.sh`
- `configs/Qwen2.5-14B-Instruct.yaml`
- `manifests/` — trainer-state snapshots for the `bestagg_*`/`proper_*_from_tofufull_*`/`test_bestagg_*` runs, the 5 model-list files, and the 108-file `hydra_configs/` snapshot (all confirmed TOFU-scaling by run name)
- `privacylens_results_snapshot/` — 40 PrivacyLens result JSON files for this phase's models; kept here because the canonical `outputs/` location is gitignored and not committed, making this the only surviving committed copy

## 4. What was learned
The top-4-method subset scales cleanly to 14B. The `Selection_proxy`→`Agg_proxy` switch (adding the MIA privacy term) happened within a single day of experimentation, a deliberate methodological refinement, not noise.

## 5. Why the thesis moved on
TOFU is a synthetic benchmark; the thesis needed a more realistic, citable unlearning benchmark (MUSE) for its central claims.

## 6. Influence on final methodology
The harmonic-mean utility/forgetting selection idea validated here for TOFU (`Agg_proxy`/`Selection_proxy`) is the direct conceptual ancestor of `best_agg` — the metric that selected every canonical MUSE-News/MUSE-Books checkpoint. See `../03_checkpoint_selection_development/` and `../../thesis/docs/trainer_patch.md`.
