# Phase 04 — MUSE-News Track A (official target)

**This is a real, complete, working research result — not a failed experiment, and not obsolete clutter.** It is superseded by the track used in the final thesis, but it succeeded on its own terms.

## 1. Question investigated
Does directly unlearning from the official MUSE-News HuggingFace target (Llama-2-7b, no local finetuning step) produce a complete, usable MUSE+PrivacyLens result?

## 2. Dataset / models / methods
MUSE-News, official `muse-bench/MUSE-News_target` (Llama-2-7b); RMU, WGA, SimNPO, SatImp.

## 3. Key scripts / manifests
- `scripts/run_muse_news_remaining_methods.sbatch`, `run_muse_news_simnpo.sbatch` — training
- `scripts/select_muse_news_best_checkpoints.py`, `make_muse_news_selected_table.py`, `make_final_muse_news_combined_table.py` — post-hoc checkpoint selection and reporting (this track does **not** use in-training `best_agg`-style selection at all)
- `scripts/run_persistbench_muse_news_judge.sh` (earlier draft) and `run_persistbench_muse_news_judge_like_tofu.sh` (later, canonical-for-this-track judge script) — kept together as a documented iteration, not because one is "junk"
- `scripts/run_persistbench_muse_news_selected.sh`, `run_privacylens_muse_news_selected.sh` — evaluation
- `manifests/openunlearning_selection/` — `SELECTED_MODEL_PATHS.tsv`, `FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv`, `MUSE_News_all_methods_checkpoint_selection.csv`, `MUSE_News_selected_methods_summary.csv` (small csv/tsv copies; originals also remain in `saves/final_muse_news_openunlearning_selection/`, untouched)
- `manifests/simnpo_precursor/` — the single-method precursor selection, one day before the full 4-method one

## 4. What was learned
This setup **fully worked end-to-end** — a real, complete combined MUSE+PrivacyLens result exists (`FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv`) for 4 unlearning methods.

## 5. Why the thesis moved on
The thesis shifted to a locally-finetuned Qwen2.5-7B-Instruct target instead (the canonical "Track B," in `../../thesis/`), for methodological consistency with how MUSE-Books was later done, and because the mechanistic-interpretability phase that followed was built specifically around the Qwen2.5-7B-Instruct model family. See `../../thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md` for the full, evidence-based resolution of why Track B — not this track — is the one cited in the final thesis text.

## 6. Influence on final methodology
This track's checkpoint-selection and combined-table scripts are the direct template that Track B's own selection/reporting was modeled on.
