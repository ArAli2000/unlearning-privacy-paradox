# Thesis: unlearning on MUSE-News and MUSE-Books

This directory holds the thesis-specific code, manifests and documentation. The repository is a fork of [OpenUnlearning](https://github.com/locuslab/open-unlearning). The thesis studies unlearning on MUSE-News and MUSE-Books at three levels: standard MUSE evaluation, black-box privacy and robustness behavior (PrivacyLens, PersistBench), and a mechanistic analysis of hidden states (native prompt-end representations, sycophancy transitions, controlled MCQ probes, A/B label-swap robustness).

Earlier research phases, cleanup notes and bulk analysis outputs are in `thesis_archive.zip` at the repository root (not tracked by git).

## 1. Changes to the upstream framework

Two upstream files are modified:

- `src/trainer/base.py` adds the `best_agg` checkpoint-selection metric (`docs/trainer_patch.md`).
- `configs/eval/tofu.yaml` has minor evaluation-metric additions (see `git log -p`).

Everything else in `src/`, `configs/` and `data/` is upstream.

## 2. Datasets and methods

- MUSE-News: locally fine-tuned Qwen2.5-7B-Instruct target. An earlier run that unlearned directly from the official Llama-2-7b target (`muse-bench/MUSE-News_target`) gave a complete result but is not the one used in the thesis; it is documented in `thesis_archive.zip` (`research_history/04_muse_track_a/`).
- MUSE-Books: two targets, the official Llama-2-7b target and a locally fine-tuned Qwen2.5-7B-Instruct target.
- Methods: BASE (no unlearning), SatImp and SimNPO are used in every mechanistic analysis. RMU and WGA are evaluated only at the behavioral level (PrivacyLens, PersistBench).

## 3. Layout

```
thesis/
  scripts/       launchers
    common.sh                        repository-root detection and conda activation
    muse_news/  muse_books/          fine-tuning and unlearning
    privacylens/                     PrivacyLens evaluation
    persistbench/                    PersistBench generation and local judging
    persistbench_fullprompt_robustness/, persistbench_fullprompt_complete/
                                     full-prompt robustness check (MUSE-News Qwen)
    validation/                      generation-validity summaries
    setup_external_dependencies.sh   clone/pin/patch external/ (section 9)
  manifests/     small frozen records
    selection/            selected checkpoint paths per benchmark (with best_agg values)
    trainer_states/       trainer_state.json of the canonical MUSE-News checkpoints
    model_lists/          model-path lists read by the launchers
    environment/          conda environment, pip freeze, git commit/status snapshot
    provenance/           generation-setting correction record
    external_dependencies/  URL, commit and patch for each external dependency
  patches/       persistbench.patch
  appendix_material/   appendix tables, prompts and configuration (see its README)
  docs/          trainer patch, PersistBench patch, generation provenance, experiment history
  analysis/      final analysis tables (final_thesis_handoff_20261016/)
mechanistic/     mechanistic-analysis code and its slurm wrappers
external/        PersistBench and privacy-collapse (git submodules)
```

Not in the repository: `saves/` (checkpoints, several TB), `logs/`, `outputs/`, `external/PersistBench/outputs/`, and extracted hidden-state tensors (`mechanistic/**/representations/`). They are excluded by `.gitignore`.

## 4. Canonical checkpoints

| Dataset | Target | BASE | SatImp | SimNPO |
|---|---|---|---|---|
| MUSE-News | Qwen2.5-7B-Instruct | `saves/finetune/muse_news_qwen25_7b_instruct_target` | `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459` | `saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459` |
| MUSE-Books | Llama-2-7b | `muse-bench/MUSE-Books_target` (official) | `saves/unlearn/muse_books_llama2_7b_satimp/checkpoint-153` | `saves/unlearn/muse_books_llama2_7b_simnpo/checkpoint-408` |
| MUSE-Books | Qwen2.5-7B-Instruct | `saves/finetune/muse_books_qwen25_7b_instruct_target` | `saves/unlearn/muse_books_qwen25_7b_instruct_satimp/checkpoint-51` | `saves/unlearn/muse_books_qwen25_7b_instruct_simnpo/checkpoint-51` |

All methods, including RMU and WGA, and the `best_agg` value of each selected checkpoint are in `manifests/selection/*_SELECTED_MODEL_PATHS.tsv`. The checkpoints themselves are not distributed.

## 5. Standard unlearning evaluation

Models are trained with OpenUnlearning's `FinetuneTrainer` with `metric_for_best_model=best_agg` and `load_best_model_at_end=True`, so the best checkpoint is chosen during training (`docs/trainer_patch.md`). Launchers:

- `scripts/muse_news/run_muse_news_qwen25_7b_instruct_finetune.sh`, `run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh` and `run_muse_news_qwen25_7b_instruct_unlearn_retry_after_rmu.sh` (re-run of methods that ran out of memory)
- `scripts/muse_books/run_muse_books_llama2_7b_unlearn_selected_methods.sh`, `run_muse_books_qwen25_7b_instruct_finetune.sh`, `run_muse_books_qwen25_7b_instruct_unlearn_after_ft.sh`

MUSE metrics (ROUGE-based knowledge and verbatim memorization, `extraction_strength`, `model_utility`) are computed by the framework's evaluator during training. `scripts/muse_news/run_final_muse_eval_qwen25_7b_instruct_selected.sh` runs the final evaluation of the selected MUSE-News checkpoints.

## 6. PrivacyLens

`scripts/privacylens/eval_privacylens_mcq_local.py` evaluates a checkpoint on `external/privacy-collapse/benchmarks/privacylens/data/main_data.json`. It is called by `run_privacylens_muse_{news_qwen25,books_llama2,books_qwen25}_selected.sh`. Results are written to `outputs/privacylens_muse_*_selected/`. The `_strict` and `_forced_choice` variants were not used for reported results.

## 7. PersistBench

Generation: `scripts/persistbench/run_persistbench_muse_{news_qwen25,books_llama2,books_qwen25}_selected.sh` serve each checkpoint with vLLM and call PersistBench's `openai_compatible` provider. Judging: `run_local_judge_server_penelope.sh` starts the judge server, and `run_persistbench_muse_*_{judge_like_tofu,localjudge}.sh` run the judgments.

Generation settings of the Qwen-family MUSE-News and MUSE-Books runs, taken from the output metadata and the vLLM server logs of those jobs (`docs/generation_provenance.md`):

| Setting | Value |
|---|---|
| `temperature` | 0.0 |
| `max_tokens` | 96 |
| Prompt truncation | last 1800 tokens |
| `max_model_len` | 2048 |
| `repetition_penalty` | 1.05 |
| Generations per item: cross-domain / sycophancy / beneficial memory | 3 / 3 / 1 |

No seed was set; at temperature 0 decoding is greedy, so this does not affect the output. The `repetition_penalty` of 1.05 comes from the checkpoint's `generation_config.json`, which vLLM adopted as its default. For the Llama-2 MUSE-Books runs, `repetition_penalty`, `top_p` and `top_k` could not be established from the logs.

All PersistBench judgments in this repository come from a locally served `Qwen/Qwen2.5-7B-Instruct`, not from the canonical PersistBench judge (`moonshotai/kimi-k2-thinking`). This should be stated wherever PersistBench numbers are reported. `appendix_material/` also contains a Gemma-3-12B re-judging for robustness.

## 8. Mechanistic analysis

Code is in `mechanistic/`:

- `privacy_collapse/persistbench_native/`: native prompt-end hidden-state extraction and sycophancy transition analysis on PersistBench generations.
- `privacy_collapse/persistbench_mcq/`: controlled MCQ privacy-judgment probe.
- `privacy_collapse/persistbench_sycophancy_mcq/`: controlled MCQ sycophancy probe with A/B label-swap robustness.
- `experiments/muse_news_sycophancy_paradox/`, `experiments/muse_news_sycophancy_final_mechanism/`: activation patching, free-generation patching, and recognition-versus-behavior experiments.
- Top-level `extract_*`/`analyze_*` scripts and `slurm/`: PrivacyLens hidden-state and population analyses.

The MUSE-News analyses use the Qwen2.5-7B-Instruct checkpoints listed in section 4. The MUSE-Books replication is in `mechanistic/outputs/muse_books_weekly_update_analysis/` (not tracked). Entry points for every analysis are listed in `appendix_material/reproducibility/script_map.tsv`.

Re-deriving tables without regenerating text requires the frozen generation and judgment files, which are not in the repository. Scripts that serve models with vLLM, train models, or start with `extract_` need a GPU; the analysis and table scripts (for example `scripts/validation/create_persistbench_validity_summary_with_muse.py` and `appendix_material/reproducibility/export_scripts/compute_tables.py`) run on CPU.

## 9. External dependencies and running on another machine

`external/PersistBench` and `external/privacy-collapse` are git submodules (`git clone --recurse-submodules`, or `git submodule update --init`). `manifests/external_dependencies/external_dependencies.tsv` records the repository URL, pinned commit and patch of each. `external/privacy-collapse` is unmodified. For PersistBench, apply `patches/persistbench.patch` (a diff of four files against pinned commit `302ea2f`; see `docs/persistbench_patch.md`):

```bash
git -C external/PersistBench apply ../../thesis/patches/persistbench.patch
```

`scripts/setup_external_dependencies.sh` does the same from scratch when the directories do not exist. It never overwrites an existing checkout.

All launchers source `scripts/common.sh`, which finds the repository root with `git rev-parse --show-toplevel`. The conda activation script and environment name default to the values used originally and can be overridden with `UNLEARNING_CONDA_ACTIVATE` and `UNLEARNING_CONDA_ENV`. Some launchers still export cluster-specific `HF_HOME`, `TRANSFORMERS_CACHE` and `CUDA_HOME` paths that must be adapted.

The environment used is recorded in `manifests/environment/` (`conda_unlearning.yml` for training; `pip_freeze_current_env.txt` is the base environment used for vLLM serving). PersistBench's `uv.lock` pins its own dependencies.

## 10. Known caveats

- Judge: all PersistBench judgments use the local Qwen2.5-7B-Instruct judge (section 7).
- Repetition penalty: the Qwen-family generations used 1.05, not 1.08. Nine generation JSONL files under `mechanistic/privacy_collapse/persistbench_native/generations/` and `mechanistic/outputs/muse_books_weekly_update_analysis/` carry `repetition_penalty: 1.08` in their metadata, which is wrong. The generated text is unchanged and the correction is recorded in `manifests/provenance/persistbench_generation_corrections.json`.
- PersistBench code: `external/PersistBench/src/benchmark/utils.py` contains generation controls (`STRICT_GENERATION_CONTROL`, default `repetition_penalty=1.08`, an injected system prompt) that were added after all MUSE generations. Running the launchers with the patched code does not reproduce the original generation parameters. In addition, rerunning the original pipeline gave text identical to the original only about 55% of the time at temperature 0, so the stored generation files are the reference.
- MUSE-News: use the Qwen2.5-7B-Instruct track for reported numbers, not the earlier official-target track.
- Validity: official FR@K counts every judged generation; the thesis also reports a validity-aware variant. See `appendix_material/README.md`.

## 11. Further documentation

- `docs/trainer_patch.md`, `docs/persistbench_patch.md`, `docs/generation_provenance.md`, `docs/experiment_history.md`
- `appendix_material/README.md`
- `thesis_archive.zip`: research history, the experimental-setup audit (`thesis/docs/experimental_setup_audit/`), PersistBench pre-patch snapshots (`thesis/docs/persistbench_patch_history/`), and the judge-robustness and robustness-replication analysis directories under `thesis/analysis/`.
