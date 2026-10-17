# Trainer patch: `best_agg` checkpoint selection

`src/trainer/base.py` is an upstream OpenUnlearning file modified in place. The patch adds two independent checkpoint-selection metrics to `FinetuneTrainer.evaluate()`.

## `best_agg` (MUSE; used for all final results)

Added 2026-07-06, the day the locally fine-tuned MUSE-News Qwen2.5-7B-Instruct target was created. On every evaluation call in which `retain_knowmem_ROUGE`, `forget_knowmem_ROUGE`, `forget_verbmem_ROUGE` and `extraction_strength` are all present, it computes

```
utility_proxy = clamp(retain_knowmem_ROUGE, 0, 1)
memory_proxy  = clamp(1 - mean(forget_knowmem_ROUGE, forget_verbmem_ROUGE, extraction_strength), 0, 1)
best_agg      = harmonic_mean(utility_proxy, memory_proxy)
```

and stores it in `eval_metrics["best_agg"]` and `eval_metrics["eval_best_agg"]`. The launchers select checkpoints with the Hydra overrides `++trainer.args.metric_for_best_model=best_agg`, `++trainer.args.load_best_model_at_end=True` and `++trainer.args.greater_is_better=True`. These are set in:

- `thesis/scripts/muse_news/run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh` and its retry script
- `thesis/scripts/muse_books/run_muse_books_llama2_7b_unlearn_selected_methods.sh`
- `thesis/scripts/muse_books/run_muse_books_qwen25_7b_instruct_unlearn_after_ft.sh`

Check: `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459/trainer_state.json` records `best_metric = 0.19242792501682263` and `best_global_step = 459`, and the log-history entry at step 459 has `eval_best_agg = 0.19242792501682263`. The same value is in the `best_metric` column of `thesis/manifests/selection/muse_news_qwen25_7b_instruct_SELECTED_MODEL_PATHS.tsv`. Trainer-state snapshots are in `thesis/manifests/trainer_states/`.

The patch has no comment stating its rationale. The design is consistent with the Hugging Face `Trainer` requirement of a single scalar for `load_best_model_at_end`: MUSE evaluation yields several metrics with no built-in combination, and the harmonic mean requires both utility and forgetting to be acceptable at the same time.

## `Agg_proxy` / `Selection_proxy` (TOFU; not used for MUSE results)

Added 2026-06-14 for the earlier TOFU model and method scaling work. It uses the same harmonic-mean idea over TOFU metrics (`extraction_strength`, `exact_memorization`, `forget_Q_A_Prob`, `forget_truth_ratio`, four MIA scores, `model_utility`, `forget_Q_A_gibberish`). `Agg_proxy` includes an MIA-derived `Privacy_proxy` term; `Selection_proxy` omits it. MUSE evaluations never produce the TOFU-specific keys this path requires, so it does nothing for MUSE. It remains in `src/trainer/base.py` so that the TOFU experiments can still be reproduced.

## Pre-patch versions

Copies of the trainer before each patch (`base.py.bak_before_agg_proxy`, from 2026-06-14, and `base.py.bak_before_bestagg_patch`, from 2026-07-06) are in `thesis_archive.zip` under `research_history/03_checkpoint_selection_development/trainer_snapshots/`.
