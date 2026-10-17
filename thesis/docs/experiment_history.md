# Experiment history

This document summarizes the order of the experiments behind the thesis. Dates are file modification times or git dates from the original working repository (2026). Paths under `research_history/` and `supervisor_update/` refer to `thesis_archive.zip`, which holds the earlier phases; the final pipeline is in `thesis/scripts/` and `mechanistic/`.

## 1. Early TOFU experiments (2026-05-22 to 05-25)

Ten unlearning methods (CEU, GradAscent, GradDiff, NPO, PDU, RMU, SatImp, SimNPO, UNDIAL, WGA) were run on Llama-3.2-1B, and subsets on Qwen2.5-1.5B and Qwen2.5-3B, on the TOFU `forget10` split (batch label `a180` in script and checkpoint names). Scripts: `research_history/01_tofu_baselines/scripts/run_qwen15_methods_a180.sh`, `run_llama1b_paper_methods_a180.sh`, `run_llama1b_other_methods_fullmetrics_a180.sh`, `run_qwen3b_selected_methods_a100.sh`, `run_qwen3b_all_methods_fullmetrics_a180.sh`. Checkpoints were `saves/unlearn/paper_llama32_1b_{method}_f10_a180[_fullmetrics]/` (20 directories); trainer states are in `supervisor_update/code_settings/trainer_states/`. Metrics were those of the stock TOFU evaluator (`configs/eval/tofu.yaml`). No checkpoint-selection override was used. This phase confirmed that all methods run end to end.

## 2. Scaling and checkpoint-selection development (2026-05-31 to 06-23)

- Model scaling to Llama-3.1-8B and Qwen2.5-7B with a reduced method set: `research_history/02_model_method_scaling/scripts/run_7bscale_top3_fullmetrics_a180.sh`, `run_llama32_3b_qwen7b_top3_fullmetrics_a180.sh` (2026-05-31).
- `Agg_proxy` / `Selection_proxy` introduced on 2026-06-14 (`research_history/03_checkpoint_selection_development/trainer_snapshots/base.py.bak_before_agg_proxy` is the trainer before it). A single-run smoke test followed the same day (`run_test_qwen7b_simnpo_save_bestagg.sh`, using `metric_for_best_model=eval_Agg_proxy`). `run_4models_4methods_save_bestagg.sh` (2026-06-17) applied it to SatImp, SimNPO, RMU and WGA on Llama-3.2-1B, Llama-3.2-3B, Qwen2.5-3B and Qwen2.5-7B (`saves/unlearn/bestagg_{model}_{method}_savebest/`, 16 directories).
- PrivacyLens was first used here (`research_history/02_model_method_scaling/scripts/run_privacylens_full_before_after.sh`, 2026-06-17), with further sweeps for the 3B, 8B and 14B models (06-19 to 06-21).
- Scaling to the full TOFU forget set (`tofufull`) and to Llama-3.1-8B and Qwen2.5-14B (2026-06-18 to 06-21): `run_qwen_tofu_full_finetune_array.sh`, `run_qwen_tofufull_unlearn_best_array.sh`, `run_llama31_8b_tofufull_unlearn_{4methods_clean,best_array,remaining3_aggproxy}.sh`, `run_qwen25_14b_tofufull_unlearn_4methods_aggproxy.sh`. The selection metric changed from `eval_Selection_proxy` (no MIA/privacy term; `saves/unlearn/proper_qwen25_{3b,7b}_*_from_tofufull_selectionproxy_savebest/`, 06-19) to `eval_Agg_proxy` (with the MIA-derived `Privacy_proxy`; `proper_{llama31_8b,qwen25_14b}_*_from_tofufull_aggproxy_savebest/`, 06-20 to 06-23).

The harmonic-mean selection idea developed here is the ancestor of `best_agg`. The TOFU-specific metrics (MIA scores, `exact_memorization`) do not exist in MUSE, so a MUSE-specific variant was written (`docs/trainer_patch.md`).

## 3. Transition to MUSE (from 2026-07-01)

MUSE work started about eight days after the last TOFU scaling checkpoint (2026-06-23). Two MUSE-News setups were run.

- Official-target run: unlearning directly from `muse-bench/MUSE-News_target` (Llama-2-7b), with checkpoints selected after training by `research_history/04_muse_track_a/scripts/select_muse_news_best_checkpoints.py`, `make_muse_news_selected_table.py` and `make_final_muse_news_combined_table.py`. It did not use `best_agg`. Output: `FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv`. This run is complete but is not used in the thesis.
- Qwen2.5-7B-Instruct run (used in the thesis): the target was fine-tuned locally (`saves/finetune/muse_news_qwen25_7b_instruct_target`, 2026-07-06) with `thesis/scripts/muse_news/run_muse_news_qwen25_7b_instruct_finetune.sh`, then unlearned with `run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh`, plus `_unlearn_retry_after_rmu.sh` for three methods that ran out of memory (the failed attempts are `saves/unlearn/muse_news_qwen25_7b_instruct_{satimp,simnpo,wga}_failed_oom_before_retry_20260706_231334/`). The `best_agg` patch was written on 2026-07-06 immediately before these runs.

The Qwen track is the one used by every later analysis. BASE, SatImp and SimNPO are the three models in all mechanistic analyses; RMU and WGA are included only in the behavioral evaluation.

## 4. MUSE-News behavioral evaluation (2026-07-06 to 07-08)

1. Fine-tune the target and unlearn four methods as above; `best_agg` selects the checkpoint during training.
2. Selection frozen on 2026-07-08 in `thesis/manifests/selection/muse_news_qwen25_7b_instruct_SELECTED_MODEL_PATHS.tsv`: BASE, SatImp-459, SimNPO-459, RMU-459, WGA-306.
3. PrivacyLens: `thesis/scripts/privacylens/run_privacylens_muse_news_qwen25_selected.sh` into `outputs/privacylens_muse_news_qwen25_selected/`.
4. PersistBench: generation with `thesis/scripts/persistbench/run_persistbench_muse_news_qwen25_selected.sh` (2026-07-08) into `external/PersistBench/outputs/muse_news_qwen25_selected_full/`, judged locally with `run_persistbench_muse_news_qwen25_judge_like_tofu.sh` (`docs/persistbench_patch.md`).
5. Validity summary: `thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py`.

The `best_metric` and `best_global_step` in the SatImp `trainer_state.json` match the `best_metric` column of the selection manifest (see `docs/trainer_patch.md`).

## 5. Mechanistic analysis (2026-08-15 to 08-28)

All on the Qwen MUSE-News BASE, SatImp and SimNPO checkpoints.

1. 2026-08-15: PrivacyLens hidden-state and logit-lens tooling (`mechanistic/extract_single_privacylens.py`, `build_population_manifest.py`, `extract_privacylens_population.py`, `compare_privacylens_samples.py`, `analyze_single_representation_drift.py`): whole-model and population-level (12 versus 12) analysis of safe and leaky responses.
2. 2026-08-23 to 08-24: `mechanistic/privacy_collapse/` pilot (`prepare_manifest.py`, `validate_outputs.py`, `validate_static.py`, `extract_pilot.py`, `analyze_pilot.py`, run with `slurm/run_muse_news_qwen25_7b_pilot.sbatch`). `mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/gpu_extraction_provenance.json` records the checkpoint paths used.
3. 2026-08-24 to 08-25: PersistBench single-case and stress-test tooling. The RMU-specific scripts (`analyze_single_persistbench_case.py`, `extract_single_persistbench_case.py`) were generalized into `analyze_persistbench_case_generic.py` and `extract_persistbench_case_generic.py`; `mechanistic/privacy_collapse/persistbench/` holds the stress-test scripts (`run_local_{simple,target,matched_rewrite,minimal_edit,smoke}_stress.py`) and validation helpers (`pair_validation.py`, `token_audit.py`, `two_stage_validation.py`).
4. 2026-08-27: `persistbench_mcq/`, the controlled MCQ privacy-judgment probe (`build_manifest.py`, `extract.py`, `analyze.py`).
5. 2026-08-27 to 08-28: `persistbench_native/`, native prompt-end hidden-state extraction on PersistBench generations, with `prepare_native_sycophancy_200.py` and `analyze_sycophancy.py` for the sycophancy transition analysis (non to non, non to syc, syc to non, syc to syc, before versus after unlearning).
6. 2026-08-28: `persistbench_sycophancy_mcq/`, the controlled MCQ sycophancy probe with A/B label-swap robustness (`original_directions.pt`, `swapped_directions.pt`), and `finalize.py`, which links its output to the native pipeline's category comparison.

Key outputs: `mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_category_comparison_validated.{json,md}` and `muse_news_persistbench_metric_reconciliation.{json,md}`. The latter reconciles the official category-specific FR@K against an earlier custom classifier and against the official-target MUSE-News numbers, and concludes that they are different measurements rather than a contradiction. Later experiments are in `mechanistic/experiments/muse_news_sycophancy_paradox/` and `mechanistic/experiments/muse_news_sycophancy_final_mechanism/`.

## 6. MUSE-Books (2026-07-10 to 09-06)

Behavioral layer, 2026-07-10 to 07-12:

- Llama-2-7b: `thesis/scripts/muse_books/run_muse_books_llama2_7b_unlearn_selected_methods.sh` into `saves/final_muse_books_llama2_7b_selection/`, then `thesis/scripts/persistbench/run_persistbench_muse_books_llama2_selected.sh` and `_judge_like_tofu.sh` (generation 2026-07-10/11), then `thesis/scripts/privacylens/run_privacylens_muse_books_llama2_selected.sh`.
- Qwen2.5-7B-Instruct: `run_muse_books_qwen25_7b_instruct_finetune.sh`, then `run_muse_books_qwen25_7b_instruct_unlearn_after_ft.sh` (with `best_agg`), then `run_persistbench_muse_books_qwen25_selected.sh` and `_localjudge.sh` (generation 2026-07-12), then `run_privacylens_muse_books_qwen25_selected.sh`.

Mechanistic replication (2026-09-06), using the frozen manifests and methods of the MUSE-News analysis: `mechanistic/outputs/muse_books_weekly_update_analysis/{DISCOVERY_REPORT.md,README.md}`, on `saves/finetune/muse_books_qwen25_7b_instruct_target` and `saves/unlearn/muse_books_qwen25_7b_instruct_{satimp,simnpo}/checkpoint-51`. The report's conclusion is: "The full MUSE-News story does not replicate on MUSE-Books. PrivacyLens again shows no Privacy-Collapse-style collapse, and the controlled A/B direction is again lexically confounded. However, the central PersistBench behavioral split reverses or becomes mixed: cross-domain FR@K is essentially unchanged/mixed, and sycophancy FR@K improves, not worsens." The Qwen MUSE-Books selection is checkpoint 51, confirmed by both the selection manifest and `trainer_state.json`.

## 7. Final scope

- Datasets: MUSE-News and MUSE-Books.
- Methods: BASE, SatImp and SimNPO for the mechanistic analyses; RMU and WGA additionally for the behavioral evaluation.
- Checkpoints: MUSE-News Qwen2.5-7B-Instruct; MUSE-Books Llama-2-7b and Qwen2.5-7B-Instruct.
- Analyses: MUSE evaluation, PrivacyLens (behavioral and hidden-state), PersistBench (cross-domain, sycophancy, beneficial memory FR@K; native hidden-state extraction; controlled MCQ probes; A/B label swap), the News versus Books comparison, a full-prompt robustness check and a Gemma-3-12B judge robustness check.

The TOFU phases (sections 1 and 2) and a WMDP-Cyber side investigation (`research_history/05_wmdp_side_investigation/`, 2026-07-13 to 07-22, with an MMLU-utility follow-up on 2026-08-12) are outside the final scope. The WMDP work was discussed with the supervisor before the move to interpretability. All of these are in `thesis_archive.zip`.
