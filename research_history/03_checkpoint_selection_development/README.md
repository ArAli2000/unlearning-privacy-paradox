# Phase 03 — Checkpoint-selection development

**This is real, completed research history, not obsolete clutter — it is the direct ancestor of the mechanism used to select every final thesis checkpoint.**

## 1. Question investigated
How should HF `Trainer`'s `load_best_model_at_end` automatically pick the best unlearning checkpoint, given that unlearning has no single built-in "goodness" metric and trades off utility against forgetting (and, for TOFU, privacy/MIA)?

## 2. Dataset / models / methods
Cross-cutting: first validated on Qwen2.5-7B/SimNPO (TOFU), then applied across the whole model-scaling grid (`../02_model_method_scaling/`) and, once adapted into `best_agg`, across every canonical MUSE run (`../../thesis/`).

## 3. Key scripts / files
- `scripts/run_test_qwen7b_simnpo_save_bestagg.sh` — first smoke test of metric-driven checkpoint selection, launched the same day the trainer patch was written
- `scripts/run_4models_4methods_save_bestagg.sh` (+ its `.bak_before_tofufull_llama32_3b` prior version) — first systematic application at scale
- `trainer_snapshots/base.py.bak_before_agg_proxy` — the trainer before `Agg_proxy`/`Selection_proxy` existed (2026-06-14)
- `trainer_snapshots/base.py.bak_before_bestagg_patch` — the trainer after those, but before `best_agg` (2026-07-06)
- `scripts/run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh.bak_before_bestagg` — moved here 2026-09-14 from `thesis/scripts/muse_news/` (it does not belong in the final-code path). This is the canonical MUSE-News launcher **before** `best_agg` selection was wired into it: no `metric_for_best_model`/`load_best_model_at_end` overrides at all, `--config-name=train.yaml` instead of `unlearn.yaml`, and a wider array concurrency (`0-3%4` vs. the live script's `0-3%2`) — the launcher-level counterpart to `trainer_snapshots/base.py.bak_before_bestagg_patch` above.
- `scripts/run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh.bak_same_ckpt_diff` — moved here 2026-09-14, same reason. A later iteration of the same script, already using `best_agg`, but with `save_steps`/`eval_steps=100` instead of the live script's `51`. `51 × 9 = 459` — the live script's checkpoint grid was specifically tuned to land exactly on checkpoint-459 (the checkpoint actually selected for SatImp/SimNPO); with `save_steps=100` no checkpoint at step 459 would ever have existed. This file documents that the exact save/eval frequency was itself a deliberate, iterated choice, not an arbitrary default.

These two snapshots are the **only surviving record** of the trainer's pre-patch states. See `../../thesis_cleanup_audit/CHECKPOINT_SELECTION_PATCH.md` for the full technical diff and `../../thesis/docs/trainer_patch.md` for the citable summary.

## 4. What was learned
A harmonic mean of a utility proxy and a forgetting proxy (`Agg_proxy`/`Selection_proxy` for TOFU) gives `metric_for_best_model` a principled single scalar. This pattern was later adapted into `best_agg` specifically for MUSE's different metric set (no MIA/exact-memorization scores available there).

## 5. Why the thesis moved on
Once the thesis moved to MUSE, the TOFU-specific proxy metrics no longer applied (MUSE evaluation doesn't produce MIA/exact-memorization scores), requiring the MUSE-specific `best_agg` variant — but the underlying idea developed here carried over directly.

## 6. Influence on final methodology
**Direct and load-bearing.** `best_agg` (the direct adaptation of this phase's pattern) is the actual mechanism that selected every canonical MUSE-News and MUSE-Books checkpoint used in the reported thesis results — proven checkpoint-by-checkpoint in `../../thesis_cleanup_audit/CHECKPOINT_SELECTION_PATCH.md` §4 (the `trainer_state.json` `best_metric` for the canonical SatImp checkpoint matches the selection manifest's recorded value to 17 significant figures).
