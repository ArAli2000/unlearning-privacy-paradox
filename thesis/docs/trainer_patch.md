# Trainer patch: `best_agg` checkpoint selection

`src/trainer/base.py` is a tracked upstream open-unlearning file, modified in place. It adds two independent capabilities to `FinetuneTrainer.evaluate()`. Full line-by-line diff analysis: `thesis_cleanup_audit/CHECKPOINT_SELECTION_PATCH.md`.

## `best_agg` (MUSE checkpoint selection — the one used by every final result)

Added 2026-07-06, the same day the MUSE-News locally-finetuned Qwen2.5-7B-Instruct target was created. Computes, on every evaluation call, whenever `retain_knowmem_ROUGE`, `forget_knowmem_ROUGE`, `forget_verbmem_ROUGE`, and `extraction_strength` are all present in the eval metrics:

```
utility_proxy = clamp(retain_knowmem_ROUGE, 0, 1)
memory_proxy  = clamp(1 - mean(forget_knowmem_ROUGE, forget_verbmem_ROUGE, extraction_strength), 0, 1)
best_agg      = harmonic_mean(utility_proxy, memory_proxy)
```

written to `eval_metrics["best_agg"]` / `eval_metrics["eval_best_agg"]`, and used via Hydra override `++trainer.args.metric_for_best_model=best_agg` (`++trainer.args.load_best_model_at_end=True`, `++trainer.args.greater_is_better=True`) in exactly the four launchers that produced the canonical checkpoints: `thesis/scripts/muse_news/run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh` (+ its retry), `thesis/scripts/muse_books/run_muse_books_llama2_7b_unlearn_selected_methods.sh`, `thesis/scripts/muse_books/run_muse_books_qwen25_7b_instruct_unlearn_after_ft.sh`.

**Proof this is the actual selection mechanism**: `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459/trainer_state.json` records `best_metric=0.19242792501682263`, `best_global_step=459`; the log-history entry at step 459 shows `eval_best_agg=0.19242792501682263` — an exact match, independently confirmed against `thesis/manifests/selection/muse_news_qwen25_7b_instruct_SELECTED_MODEL_PATHS.tsv`'s `best_metric` column.

Rationale (inferred from code structure and usage, not stated in any prose comment anywhere in the repo — see `CHECKPOINT_SELECTION_PATCH.md` §2): HF `Trainer`'s `load_best_model_at_end` needs one scalar metric; MUSE evaluation produces several (utility-side ROUGE, forgetting-side ROUGE/extraction-strength) with no built-in combination. A harmonic mean forces both to be simultaneously acceptable before a checkpoint scores well, rather than letting one collapse to zero while the other looks good.

## `Agg_proxy` / `Selection_proxy` (TOFU checkpoint selection — historical, not used by the final MUSE results)

Added 2026-06-14, ~3 weeks earlier, for the TOFU model/method-scaling work now preserved under `research_history/02_model_method_scaling/` and `research_history/03_checkpoint_selection_development/`. Same harmonic-mean idea, but over TOFU-specific metrics (`extraction_strength`, `exact_memorization`, `forget_Q_A_Prob`, `forget_truth_ratio`, 4 MIA scores, `model_utility`, `forget_Q_A_gibberish`); `Agg_proxy` includes an MIA-derived `Privacy_proxy` term, `Selection_proxy` omits it. **This code path is a guaranteed no-op for every MUSE evaluation** (MUSE metrics never populate the TOFU-specific keys it requires), so it does not affect any canonical result — it remains in `src/trainer/base.py` only because it is still load-bearing for reproducing the historical TOFU work in `research_history/`.

## Pre-patch history

The only surviving record of the trainer before each patch:

- `research_history/03_checkpoint_selection_development/trainer_snapshots/base.py.bak_before_agg_proxy` — state before `Agg_proxy`/`Selection_proxy` existed (2026-06-14).
- `research_history/03_checkpoint_selection_development/trainer_snapshots/base.py.bak_before_bestagg_patch` — state after `Agg_proxy`/`Selection_proxy`, before `best_agg` (2026-07-06).

## Status of this file

`src/trainer/base.py` was **not modified as part of the file-moving migration** — it remains exactly as it was, in its original location, per `METHODOLOGY_PRESERVATION_PLAN.md`. Extracting its logic into a separately-named `checkpoint_selection.py` module is a recommended future refactor, not performed in this pass (see that plan's §"Recommended sequencing").
