# Thesis: unlearning on MUSE-News and MUSE-Books

This directory holds the thesis-specific code, manifests and documentation. The repository is a fork of [OpenUnlearning](https://github.com/locuslab/open-unlearning). The thesis studies unlearning on MUSE-News and MUSE-Books (main focus) and, at the behavioral level, on TOFU, at three levels: standard MUSE evaluation, black-box privacy and robustness behavior (PrivacyLens, PersistBench), and a mechanistic analysis of hidden states (native prompt-end representations, sycophancy transitions, controlled MCQ probes, A/B label-swap robustness).

Earlier research phases, cleanup notes and bulk analysis outputs are in `thesis_archive.zip` at the repository root (not tracked by git).

## 1. Changes to the upstream framework

Two upstream files are modified:

- `src/trainer/base.py` adds the `best_agg` checkpoint-selection metric (`docs/trainer_patch.md`).
- `configs/eval/tofu.yaml` has minor evaluation-metric additions (see `git log -p`).

Everything else in `src/`, `configs/` and `data/` is upstream.

## 2. Datasets and methods

- MUSE-News: locally fine-tuned Qwen2.5-7B-Instruct target. An earlier run that unlearned directly from the official Llama-2-7b target (`muse-bench/MUSE-News_target`) gave a complete result but is not the one used in the thesis; it is documented in `thesis_archive.zip` (`research_history/04_muse_track_a/`).
- MUSE-Books: two targets, the official Llama-2-7b target and a locally fine-tuned Qwen2.5-7B-Instruct target.
- TOFU (forget10/retain90): Qwen2.5-7B-Instruct and Llama-3.1-8B-Instruct, each fine-tuned on TOFU and unlearned with RMU, WGA, SatImp and SimNPO. TOFU is evaluated behaviorally (PrivacyLens, PersistBench) and appears in the final tables. The TOFU training and evaluation launchers are not tracked here; they are in `thesis_archive.zip` (`research_history/02_model_method_scaling/scripts/`). The selected steps and the weight provenance are in `analysis/final_thesis_handoff_20261016/TOFU_WEIGHT_PROVENANCE.md`.
- Methods: BASE (no unlearning), SatImp and SimNPO are used in every mechanistic analysis. RMU and WGA are evaluated at the behavioral level (PrivacyLens, PersistBench). RMU also has a supporting mechanistic audit on MUSE-News Qwen2.5-7B-Instruct (`mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/`, with `RMU_AUDIT.md`): a replication of the SatImp/SimNPO transition audit and activation patching for RMU. WGA has no mechanistic analysis.

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
    trainer_states/       trainer_state.json of all 12 selected MUSE checkpoints
    muse_eval/            MUSE_SUMMARY.json of the selected checkpoints (and the Llama-2 MUSE-Books BASE); see its README
    selection/selected_checkpoint_metrics.tsv   per-run MUSE metrics at the selected step (built by scripts/validation/build_selected_checkpoint_metrics.py)
    model_lists/          model-path lists read by the launchers
    environment/          conda environment, pip freeze, git commit/status snapshot
    provenance/           generation-setting correction record
    external_dependencies/  URL, commit and patch for each external dependency
  patches/       persistbench.patch
  appendix_material/   appendix tables, prompts and configuration (see its README)
  docs/          trainer patch, PersistBench patch, generation provenance, experiment history
  analysis/      final analysis tables (final_thesis_handoff_20261016/)
  results/       PrivacyLens per-item results (privacylens/) and their run summary
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

`thesis/scripts/privacylens/eval_privacylens_mcq_local.py` evaluates a checkpoint on `external/privacy-collapse/benchmarks/privacylens/data/main_data.json`. It is called by `run_privacylens_muse_{news_qwen25,books_llama2,books_qwen25}_selected.sh`. Results are written to `outputs/privacylens_muse_*_selected/`. The `_strict` and `_forced_choice` variants were not used for reported results.

PrivacyLens answers are sampled, not greedy: `do_sample=True`, temperature 1.0, `max_new_tokens` 20, one answer per item. `torch.manual_seed(42)` is set once before the loop, so a rerun on the same hardware and software may reproduce the answers, but this was not verified, and different hardware or library versions can change individual answers. The reported accuracies are one sampled draw. All settings are in `appendix_material/configs/privacylens_configuration.tsv`.

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

This applies to the MUSE PersistBench generations only (Qwen2.5 and Llama-2). No seed was set; at temperature 0 decoding is greedy, so a seed would not change the output in principle. In practice, byte-identical reproduction was not guaranteed: rerunning the original vLLM pipeline at temperature 0 gave text identical to the original only about 55% of the time (section 10). TOFU PersistBench generation used sampling (temperature 1.0, no seed; `appendix_material/configs/generation_configurations.tsv`). PrivacyLens used sampling too (section 6). The `repetition_penalty` of 1.05 comes from the checkpoint's `generation_config.json`, which vLLM adopted as its default. For the Llama-2 MUSE-Books runs, `repetition_penalty`, `top_p` and `top_k` could not be established from the logs.

All PersistBench judgments in this repository come from a locally served `Qwen/Qwen2.5-7B-Instruct`, not from the canonical PersistBench judge (`moonshotai/kimi-k2-thinking`). This should be stated wherever PersistBench numbers are reported. `appendix_material/` also contains a Gemma-3-12B re-judging for robustness.

## 8. Mechanistic analysis

Code is in `mechanistic/`:

- `privacy_collapse/persistbench_native/`: native prompt-end hidden-state extraction and sycophancy transition analysis on PersistBench generations.
- `privacy_collapse/persistbench_mcq/`: controlled MCQ privacy-judgment probe.
- `privacy_collapse/persistbench_sycophancy_mcq/`: controlled MCQ sycophancy probe with A/B label-swap robustness.
- `experiments/muse_news_sycophancy_paradox/`, `experiments/muse_news_sycophancy_final_mechanism/`: activation patching, free-generation patching, and recognition-versus-behavior experiments.
- Top-level `extract_*`/`analyze_*` scripts and `slurm/`: PrivacyLens hidden-state and population analyses.

The MUSE-News analyses use the Qwen2.5-7B-Instruct checkpoints listed in section 4. The MUSE-Books replication is in `mechanistic/outputs/muse_books_weekly_update_analysis/` (not tracked). Entry points for every analysis are listed in `appendix_material/reproducibility/script_map.tsv`.

Re-deriving tables without regenerating text requires the frozen generation and judgment files, which are not in the repository. Scripts that serve models with vLLM, train models, or start with `extract_` need a GPU. The analysis and table scripts need no GPU, but they need those frozen files.

`appendix_material/reproducibility/export_scripts/compute_tables.py` reads 46 input files. Six are tracked in this repository (the validity-classifier source, one stored FR@K table, the two stored judge-robustness JSONs, and two stored cross-check tables in `appendix_material/reproducibility/stored_inputs/`). The other 40 are PersistBench-derived raw outputs (judged generations, Gemma re-judged files, two analysis summaries), which are not in the repository. Without them the script checks its inputs first, stops with exit code 2 and lists every missing file (`--check-inputs` only reports their status). `--artifact-root PATH` (or `PERSISTBENCH_ARTIFACT_ROOT`) reads them from an extracted external archive instead of `external/PersistBench/`; the exact commands are in `appendix_material/reproducibility/ARTIFACT_MANIFEST_README.md`. That archive (40 files, 77.2 MB, listed with SHA-256 in `artifact_manifest_external.tsv`) has not been published: publication is blocked until the PersistBench authors clarify redistribution (the pinned PersistBench commit has no licence file). On the original cluster, and in a clean copy supplied with the 40 files through a temporary artifact root, the script regenerates the five tables in `appendix_material/tables/` byte for byte.

## 9. External dependencies and running on another machine

`external/PersistBench` and `external/privacy-collapse` are git submodules (`git clone --recurse-submodules`, or `git submodule update --init`). `manifests/external_dependencies/external_dependencies.tsv` records the repository URL, pinned commit and patch of each. `external/privacy-collapse` is unmodified. For PersistBench, apply `patches/persistbench.patch` (a diff of four files against pinned commit `302ea2f`; see `docs/persistbench_patch.md`):

```bash
git -C external/PersistBench apply ../../thesis/patches/persistbench.patch
```

`scripts/setup_external_dependencies.sh` does the same from scratch when the directories do not exist. It never overwrites an existing checkout.

All launchers source `scripts/common.sh`, which finds the repository root with `git rev-parse --show-toplevel`. No conda path is assumed. A launcher uses, in this order: the `activate` script in `UNLEARNING_CONDA_ACTIVATE` (then `conda activate` of the requested environment, `unlearning` by default, `UNLEARNING_CONDA_ENV` overrides it; the serving and judging launchers request `base`); otherwise the conda environment that is already active, if its name matches the requested one (or if `UNLEARNING_USE_ACTIVE_ENV=1`); otherwise it stops with an error that says what to set. `sbatch` passes on the submitting shell's active environment, so running `conda activate unlearning` before `sbatch` is enough. The `.sbatch` launchers under `mechanistic/` source `thesis/scripts/common.sh` from the submit directory and use the same conda rules. No launcher contains a personal path.

Cluster settings are read from environment variables, set them in your shell (or `sbatch --export=ALL,VAR=...`) before submitting. Launchers must be submitted from the repository root.

| Variable | Meaning (default if unset) |
|---|---|
| `UNLEARNING_CONDA_ACTIVATE`, `UNLEARNING_CONDA_ENV`, `UNLEARNING_USE_ACTIVE_ENV` | conda activation, see above |
| `UNLEARNING_HOME` | writable directory used as `$HOME` by launchers that override it (the current `$HOME`) |
| `XDG_CACHE_HOME`, `HF_HOME`, `TRANSFORMERS_CACHE`, `TRITON_CACHE_DIR` | cache locations (`$HOME/.cache`, `$XDG_CACHE_HOME/huggingface`, `$HF_HOME`, `$HOME/.triton/autotune` or a `/tmp` path) |
| `CUDA_HOME`, `CUDA_PATH` | CUDA toolkit; the default `/nfs/cuda/cuda-12.2` is the original cluster's module path, an example only |
| `REPO_ROOT`, `PROJECT_ROOT` | repository root (submit directory) |
| `PYTHON`, `VLLM` | binaries for the PersistBench stress-test launchers (`python`, `vllm` from the activated `base` environment) |
| `JUDGE` | required by `run_hybrid_gemma_qwen.sbatch`: local snapshot of Qwen/Qwen2.5-7B-Instruct, revision a09a35458c702b33eeacc393d103063234e8bc28 |
| `GEMMA_LOCAL_PATH`, `GEMMA_JUDGE_HOME`, `GEMMA_JUDGE_PORT` | Gemma judge launchers, see `appendix_material/README.md` |

The `#SBATCH` lines (partition, GPU type, memory, time) are the values of the original runs and the account (`ukp-student`), node (`--nodelist`) and QOS (`--qos`) directives are original cluster settings that users will usually need to override; override on the command line, for example `sbatch --account=<ACCOUNT> --partition=<PARTITION> <launcher>`. Some launchers still export cluster-specific `HF_HOME`, `TRANSFORMERS_CACHE` and `CUDA_HOME` paths that must be adapted.

Two environments were used, and both are recorded exactly in `manifests/environment/` and `appendix_material/reproducibility/software_environment.tsv`: the conda environment `unlearning` (`conda_unlearning.yml`: Python 3.11.15, torch 2.4.1+cu121, transformers 4.51.3, numpy 1.26.4, flash-attn 2.8.3 for the Llama-2 runs, lm-eval 0.4.11) for training, MUSE evaluation, PrivacyLens and the mechanistic scripts; and the conda base environment (`pip_freeze_current_env.txt`: Python 3.13.13, torch 2.11.0+cu130, transformers 5.12.1, vLLM 0.23.0) for vLLM serving and judging. Despite its name, `pip_freeze_current_env.txt` is the serving environment, not the training environment. The top-level `requirements.txt` is OpenUnlearning's own list; it matches `conda_unlearning.yml` for all pinned packages except numpy (`requirements.txt` pins 2.2.3, the recorded environment has 1.26.4). PersistBench's `uv.lock` pins its own dependencies.

## 10. Known caveats

- Judge: all PersistBench judgments use the local Qwen2.5-7B-Instruct judge (section 7).
- Repetition penalty: the Qwen-family generations used 1.05, not 1.08. Nine generation JSONL files under `mechanistic/privacy_collapse/persistbench_native/generations/` and `mechanistic/outputs/muse_books_weekly_update_analysis/` carry `repetition_penalty: 1.08` in their metadata, which is wrong. The generated text is unchanged and the correction is recorded in `manifests/provenance/persistbench_generation_corrections.json`.
- PersistBench code: `external/PersistBench/src/benchmark/utils.py` contains generation controls (`STRICT_GENERATION_CONTROL`, default `repetition_penalty=1.08`, an injected system prompt) that were added after all MUSE generations. Running the launchers with the patched code does not reproduce the original generation parameters. In addition, rerunning the original pipeline gave text identical to the original only about 55% of the time at temperature 0, so the stored generation files are the reference.
- MUSE-News: use the Qwen2.5-7B-Instruct track for reported numbers, not the earlier official-target track.
- Validity: official FR@K counts every judged generation; the thesis also reports a validity-aware variant. See `appendix_material/README.md`.

## 11. Further documentation

- `docs/trainer_patch.md`, `docs/persistbench_patch.md`, `docs/generation_provenance.md`, `docs/experiment_history.md`
- `appendix_material/README.md`
- `thesis_archive.zip`: research history, the experimental-setup audit (`thesis/docs/experimental_setup_audit/`), PersistBench pre-patch snapshots (`thesis/docs/persistbench_patch_history/`), and the judge-robustness and robustness-replication analysis directories under `thesis/analysis/`. Only `thesis/analysis/judge_robustness/gemma_judge.py` (the Gemma-3-12B judging code) and `qwen_vs_gemma_analysis.py` (which produces the stored Qwen-versus-Gemma tables) are tracked; the rest of that directory, including the stored result JSONs, is in the archive.
