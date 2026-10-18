# Third-party notices

This repository is a fork of OpenUnlearning and builds on other people's work. The notes below record attribution and licence status as far as it is known. They are not legal advice and make no claim beyond what is stated.

## OpenUnlearning (framework)
- Source: https://github.com/locuslab/open-unlearning, MIT licence (`LICENSE`, copyright CMU Locus Lab). Everything outside `thesis/`, `mechanistic/` and the modified files listed in `README.md` is theirs. Please cite the OpenUnlearning, TOFU and MUSE papers (`CITATION.cff`, `README.md`).

## PersistBench
- Source: https://github.com/ivaxi0s/PersistBench, included as the git submodule `external/PersistBench`, pinned to commit `302ea2ff2cfce97e9458a9897a10b67a2c1d479f`.
- **Licence status: unresolved.** The repository at the pinned commit contains no licence file and its README states no licence. This repository does not assume a licence for PersistBench.
- This repository changes PersistBench only through `thesis/patches/persistbench.patch` (local judge routing and generation controls), applied by the user; the modified files are not distributed here.
- **No raw PersistBench-derived files are included**: the benchmark samples, the generations and the judgments (`external/PersistBench/outputs*`) are not in this repository. The 40 files that regenerate the appendix tables are listed with checksums in `thesis/appendix_material/reproducibility/artifact_manifest_external.tsv`, are held separately, and are **not published** until redistribution is clarified with the PersistBench authors.

## privacy-collapse and PrivacyLens
- `external/privacy-collapse` (https://github.com/parameterlab/privacy-collapse, MIT licence, copyright Parameter Lab), submodule pinned to `f35e8ba7e3614f987afcd0dcd6920c25c878e229`, unmodified. It carries the PrivacyLens data used for evaluation. `thesis/results/privacylens/` contains only per-item A/B answers and run summaries, no benchmark text.

## Gemma-3-12B (judge robustness check)
- Model: `google/gemma-3-12b-it`, revision `96b6f1eccf38110c56df3a15bffe176da04bfd80`, used as a second judge for the robustness check.
- Terms of use: https://ai.google.dev/gemma/terms (the model is gated on Hugging Face; its use is subject to those terms).
- The Gemma JSON files in this repository, `thesis/analysis/judge_robustness/qwen_vs_gemma_frk.json` and `qwen_vs_gemma_agreement.json`, contain **aggregate results only** (rates and agreement statistics), no model text. The per-generation Gemma outputs are among the unpublished files described above.

## Models and data
- Qwen2.5-7B-Instruct (Apache-2.0), Llama-2-7b and Llama-3.1-8B-Instruct (their community licences), the MUSE targets `muse-bench/MUSE-News_target` and `muse-bench/MUSE-Books_target`, and the MUSE and TOFU datasets are used under their own terms. No weights are distributed here.
