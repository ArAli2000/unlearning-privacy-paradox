# Mechanistic analysis

Hidden-state, logit-lens and activation-patching analyses. Run every script from the
repository root; Slurm wrappers are in `slurm/`. Generated outputs go to
`mechanistic/outputs/` and are not part of the repository.

| Directory | Contents |
|---|---|
| `privacylens/` | PrivacyLens hidden-state extraction for one sample, the 493-sample population and token positions; PCA, representation drift, validation. `extract_single_privacylens.py` holds the shared prompt and model-path helpers. |
| `persistbench/` | PersistBench single-case and generic case extraction and analysis, privacy-branch counterfactuals, privacy-bearing token analysis. |
| `paradox/` | Benchmark-paradox analysis and selection of candidates for the mechanistic study. |
| `muse_news/` | MUSE-News activation patching, memory ablation, continuation-preference and logit-lens analyses, transition tables. |
| `experiments/` | Self-contained experiment folders (sycophancy paradox, final mechanism) with their own README, manifests and reports. |
| `privacy_collapse/` | Small manifests and analysis tables for the PersistBench native, sycophancy and MCQ runs. |
| `slurm/` | Slurm launchers for the scripts above. |

Example: `sbatch mechanistic/slurm/run_single_privacylens.sbatch main415`
