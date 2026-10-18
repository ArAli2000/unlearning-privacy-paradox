# Thesis code

This repository is the code accompanying a master's thesis on LLM unlearning evaluated on MUSE-News and MUSE-Books. It is a fork of [OpenUnlearning](https://github.com/locuslab/open-unlearning); its original documentation is at https://github.com/locuslab/open-unlearning. The thesis adds a checkpoint-selection patch to the trainer, launcher scripts for the behavioral benchmarks (PrivacyLens, PersistBench), a mechanistic analysis of hidden states, and the manifests and appendix material needed to trace the reported numbers.

## Where things are

| Path | Contents |
|---|---|
| `src/trainer/base.py` | The only modified framework source file. Adds the `best_agg` checkpoint-selection metric (harmonic mean of a utility proxy and a forgetting proxy), used with `metric_for_best_model=best_agg`. Description: `thesis/docs/trainer_patch.md`. The only other change to upstream is in `configs/eval/tofu.yaml` (extra TOFU metrics enabled by default: MIA variants, `exact_memorization`, `forget_Q_A_gibberish`); the MUSE experiments use `configs/eval/muse.yaml` and are unaffected. |
| `thesis/scripts/` | Launchers by benchmark: `muse_news/`, `muse_books/` (finetune and unlearn), `privacylens/`, `persistbench/` (generation and local judging), `persistbench_fullprompt_robustness/` and `persistbench_fullprompt_complete/` (full-prompt robustness check), `validation/` (generation-validity summaries). `common.sh` provides repository-root detection and conda activation; `setup_external_dependencies.sh` sets up `external/`. |
| `mechanistic/` | Hidden-state and activation-patching analyses (PrivacyLens, PersistBench native, controlled MCQ probes, sycophancy experiments). Per-directory notes are in `mechanistic/README.md` and `mechanistic/privacy_collapse/README.md`. |
| `thesis/manifests/` | Small frozen records: selected checkpoint paths per benchmark, trainer states, model lists used by the launchers, environment snapshot, external dependency pins, generation-setting corrections. |
| `thesis/appendix_material/` | Exact prompts, configuration tables, FR@K/validity/robustness/judge tables and LaTeX snippets for the thesis appendix. |
| `thesis/docs/` | Notes on the trainer patch, the PersistBench patch, generation provenance and the experiment history. |
| `thesis/patches/persistbench.patch` | Thesis modifications to PersistBench (local judge routing and generation controls). |
| `thesis/analysis/` | Final analysis tables (`final_thesis_handoff_20261016/`). |
| `external/` | `PersistBench` and `privacy-collapse`, included as git submodules. |

`thesis/README.md` is the detailed guide: final datasets and methods, canonical checkpoints, generation settings, and known caveats.

## Getting the external dependencies

Clone with submodules:

```bash
git clone --recurse-submodules <this-repo-url>
# or, in an existing clone:
git submodule update --init
```

The submodules are pinned to the commits recorded in `thesis/manifests/external_dependencies/external_dependencies.tsv`. `external/privacy-collapse` is used unmodified. PersistBench was modified for the thesis (local judge routing, generation controls); these changes are not in the submodule and are applied from the patch:

```bash
git -C external/PersistBench apply ../../thesis/patches/persistbench.patch
```

Alternatively, if `external/PersistBench` and `external/privacy-collapse` do not exist, `bash thesis/scripts/setup_external_dependencies.sh` clones each at its pinned commit and applies the patch. The script never overwrites an existing checkout and skips one that is already present.

## Reproducing the results

1. Install the framework (see [OpenUnlearning](https://github.com/locuslab/open-unlearning) and `docs/` for details):

   ```bash
   conda create -n unlearning python=3.11 && conda activate unlearning
   pip install ".[lm-eval]"
   pip install --no-build-isolation flash-attn==2.6.3
   ```

    The environment used for training is recorded in `thesis/manifests/environment/conda_unlearning.yml`.
2. Fine-tune the targets and unlearn with the launchers in `thesis/scripts/muse_news/` and `thesis/scripts/muse_books/`. Checkpoints are selected during training by `best_agg`. The selected checkpoints are listed in `thesis/manifests/selection/`.
3. Evaluate with `thesis/scripts/privacylens/` and `thesis/scripts/persistbench/` (the latter serves checkpoints with vLLM and judges with a locally served Qwen2.5-7B-Instruct). The launchers are SLURM scripts and call `thesis/scripts/common.sh`; the conda environment is set through `UNLEARNING_CONDA_ACTIVATE` and `UNLEARNING_CONDA_ENV`.
4. Run the analyses in `mechanistic/` and the validity summaries in `thesis/scripts/validation/`. Entry points for each analysis are listed in `thesis/appendix_material/reproducibility/script_map.tsv`.

Launchers locate the repository root relative to themselves (`common.sh`) or, for `sbatch` scripts, from the submit directory (`SLURM_SUBMIT_DIR`), so submit them from the repository root. Some launchers still export cluster-specific cache and environment paths (`HOME`, `HF_HOME`, `CUDA_HOME`, conda activation) that must be adapted. The scripts under `thesis/appendix_material/reproducibility/export_scripts/` and `thesis/analysis/final_thesis_handoff_20261016/scripts/` regenerate the appendix tables from the original cluster's Hugging Face cache and conda paths; they are provenance records, not portable tools. Model generation is not bitwise reproducible even with identical settings (see `thesis/README.md`), so the frozen result files, not regenerated outputs, are the reference for reported numbers.

## Not included

Model checkpoints (`saves/`), generations and judgments (`external/PersistBench/outputs/`, `outputs/`), extracted hidden-state tensors, and logs are not part of the repository. They are large and are excluded by `.gitignore`.

## Development history

`thesis_archive.zip` (repository root, not tracked by git) holds the development history that was removed from the submission tree: earlier research phases (`research_history/`), the cleanup and audit notes, bulk analysis outputs, and `MASTER_THESIS_MAP.md`.

## Attribution

The framework (training, unlearning methods, evaluation metrics, configs, benchmark integration) was developed by the OpenUnlearning authors and is used here under its MIT license; it is not the work of this thesis. If you use the framework, please cite:

```bibtex
@article{openunlearning2025,
  title={{OpenUnlearning}: Accelerating {LLM} Unlearning via Unified Benchmarking of Methods and Metrics},
  author={Dorna, Vineeth and Mekala, Anmol and Zhao, Wenlong and McCallum, Andrew and Lipton, Zachary C and Kolter, J Zico and Maini, Pratyush},
  journal={arXiv preprint arXiv:2506.12618},
  year={2025},
  url={https://arxiv.org/abs/2506.12618}
}
```

The benchmarks it implements should be cited as well:

```bibtex
@inproceedings{maini2024tofu,
  title={{TOFU}: A Task of Fictitious Unlearning for {LLMs}},
  author={Maini, Pratyush and Feng, Zhili and Schwarzschild, Avi and Lipton, Zachary Chase and Kolter, J Zico},
  booktitle={First Conference on Language Modeling},
  year={2024}
}
@article{shi2024muse,
  title={{MUSE}: Machine Unlearning Six-Way Evaluation for Language Models},
  author={Weijia Shi and Jaechan Lee and Yangsibo Huang and Sadhika Malladi and Jieyu Zhao and Ari Holtzman and Daogao Liu and Luke Zettlemoyer and Noah A. Smith and Chiyuan Zhang},
  year={2024},
  eprint={2407.06460},
  archivePrefix={arXiv},
  primaryClass={cs.CL},
  url={https://arxiv.org/abs/2407.06460}
}
```

PersistBench and privacy-collapse are third-party projects included as submodules and are credited to their authors.

What is specific to this thesis: the `best_agg` checkpoint-selection patch in `src/trainer/base.py`, everything under `thesis/` and `mechanistic/`, and the PersistBench patch.
