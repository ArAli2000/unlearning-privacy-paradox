# MUSE evaluation records of the selected checkpoints

`*_MUSE_SUMMARY.json`: the six-number MUSE summary (`extraction_strength`, `forget_knowmem_ROUGE`, `forget_verbmem_ROUGE`, `privleak`, `retain_knowmem_ROUGE`) of each of the 12 selected checkpoints, copied byte for byte from `<checkpoint>/evals/MUSE_SUMMARY.json`. The matching `trainer_state.json` files are in `../trainer_states/`; `../selection/selected_checkpoint_metrics.tsv` collects both (built by `thesis/scripts/validation/build_selected_checkpoint_metrics.py`). The per-example `MUSE_EVAL.json` files (about 0.85 to 0.97 MB each, MUSE benchmark text and model generations) are not in Git; they are listed in the external artifact manifest.

## `muse_books_llama2_7b_before_official_target_MUSE_SUMMARY.json`

MUSE evaluation of the BASE condition of the Llama-2 MUSE-Books runs, the official `muse-bench/MUSE-Books_target`. It is copied byte for byte from the evaluation directory `test_muse_books_target_before_eval` written by `thesis/scripts/muse_books/test_muse_books_target_load.sh`. The model identity comes from the evaluation's own recorded configuration, not from the directory name:

- `.hydra/overrides.yaml` of that evaluation: `experiment=eval/muse/default`, `data_split=Books`, `model.model_args.pretrained_model_name_or_path=muse-bench/MUSE-Books_target`, `model.tokenizer_args.pretrained_model_name_or_path=NousResearch/Llama-2-7b-hf`. `.hydra/config.yaml` repeats the model path and the `muse-bench/MUSE-Books` evaluation splits.
- The five override lines are the ones in the tracked launcher `test_muse_books_target_load.sh`.
- `muse-bench/MUSE-Books_target` is the BASE of the Llama-2 MUSE-Books condition in `thesis/manifests/selection/muse_books_llama2_7b_SELECTED_MODEL_PATHS.tsv`, in the PersistBench and PrivacyLens launchers, and in `thesis/README.md`.
- `eval.log` shows the evaluation ran on 2026-07-08 between 18:41 and 18:44 and reports the same six metrics as the summary file.

Limits: the Hugging Face revision of `muse-bench/MUSE-Books_target` at the time is not recorded anywhere I found, so the record identifies the model by its hub id only. `eval.log` warns that `retain_model_logs` were not provided, so `privleak` uses the default retain AUC of 0.5 (the same evaluator setting applies to the other summaries in this directory only if their runs also lacked retain logs; this was not checked).

No equivalent record was used for the two Qwen2.5 BASE targets: they have evaluations at many intermediate checkpoints and the canonical BASE checkpoint of those runs is not named in the selection manifests, so no BASE summary for them is included.
