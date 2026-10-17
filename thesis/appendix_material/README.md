# Thesis appendix material

Prompts, configuration tables and result tables for the methodology chapter and the appendix. Everything here was built from existing repository files (sources, configs, logs, frozen result JSONs, stored summary tables). The only recomputation is arithmetic on stored judge scores (`reproducibility/export_scripts/compute_tables.py`).

Directories mentioned below as being in `thesis_archive.zip` (`research_history/`, `thesis/analysis/judge_robustness/`, `thesis/docs/experimental_setup_audit/`) are not in the tracked tree.

## Provenance labels

The TSV files use these labels in their provenance columns.

| Label | Meaning |
|---|---|
| STORED | The value is written in an existing artifact (output-file metadata, stored table, JSON, log line), named in the row. |
| CODE INSPECTION | Read from source code or launcher scripts, not from a run record. |
| RECOMPUTED_FROM_EXISTING_OUTPUT | No stored table existed; computed from the frozen output JSONs. Where a stored table existed for the same quantity, the two were compared; no mismatch was found. |
| INFERRED | Derived from the absence of evidence or from library defaults; flagged in the `Confidence` or `Notes` column. |

## Files

| File | Contents | Source | Provenance | Use |
|---|---|---|---|---|
| `prompts/privacylens_prompt_exact.txt` | Source of `construct_prompt` and helpers, the rendered `naive` prompt with placeholders, chat-template wrappers (Qwen, Llama-3.1; Llama-2 has none) | `thesis/scripts/privacylens/eval_privacylens_mcq_local.py` | CODE INSPECTION | Appendix |
| `prompts/privacylens_prompt_schematic.txt` | Placeholder form of the same prompt | same | CODE INSPECTION | Chapter 3 |
| `prompts/persistbench_generator_exact.txt` | `GENERATOR_SYSTEM_PROMPT`, `formatted_memories` and `build_generation_prompt`; header on `{model_name}`, `{memories}`, `{query}`, message passing, chat templates, truncation, full-prompt behavior | `external/PersistBench/src/benchmark/prompts.py`, `execution/generation.py`, `utils.py`; launchers; vLLM logs | CODE INSPECTION, plus STORED run metadata for template and truncation | Appendix |
| `prompts/persistbench_generator_schematic.txt` | `[system] persona ... <memories>{memories}</memories> [user] {query}` plus the same header | same | CODE INSPECTION | Chapter 3 |
| `prompts/judge_{cross_domain,sycophancy,beneficial_memory}_exact.txt` | Rubric constants `JUDGE_SYSTEM_PROMPT_SINGLE_*` | `external/PersistBench/src/benchmark/prompts.py` | CODE INSPECTION | Appendix |
| `prompts/judge_input_schematic.txt` | `<memories>/<query>/<response>` layout, required JSON, strict-JSON suffix, role layout of the Qwen and Gemma judges (the two strict-instruction strings were compared and are identical) | `external/PersistBench/src/benchmark/execution/judgment.py`, `gemma_judge.py` (`thesis_archive.zip`: `thesis/analysis/judge_robustness/`) | CODE INSPECTION | Chapter 3 or appendix |
| `configs/generation_configurations.tsv` | PersistBench generation settings for MUSE-News/Books Qwen, MUSE-News/Books Llama-2, TOFU Qwen, TOFU Llama-3.1, and the MUSE-News full-prompt robustness runs (corrected values) | output metadata, vLLM logs, launchers, `thesis/manifests/provenance/persistbench_generation_corrections.json` | STORED and INFERRED (per row) | Chapter 3 (condensed), appendix (full) |
| `configs/privacylens_configuration.tsv` | `do_sample`, temperature, `max_new_tokens`, generations, seed, sampling parameters per model family, precision, attention, truncation, chat template, parsing | evaluator source, checkpoint `generation_config.json`, output metadata | CODE INSPECTION and STORED | Chapter 3 (condensed), appendix |
| `reproducibility/model_checkpoints.tsv` | Target and selected checkpoint, selection manifest and behavioral output paths for each of 34 final conditions | `thesis/manifests/`, run directories (`thesis_archive.zip`: `thesis/docs/experimental_setup_audit/selected_checkpoints.tsv`) | STORED | Appendix |
| `reproducibility/software_environment.tsv` | Conda environments (`unlearning`, `base`), CUDA, judge servers | `thesis/manifests/environment/*`, site-packages, logs | STORED, checked against the live environment | Chapter 3 (condensed), appendix |
| `reproducibility/script_map.tsv` | Purpose, script, entry point, inputs, outputs, notes, including all mechanistic entry points | repository | CODE INSPECTION | Appendix |
| `reproducibility/export_scripts/compute_tables.py` | Reads results and writes `tables/*.tsv` | | | Supporting |
| `reproducibility/export_scripts/build_{prompts,configs,ckpt,repro}.py` | Generators of the prompt files and the hand-curated TSVs. Re-running them rewrites only files in this directory. | | | Supporting |
| `tables/persistbench_frk_complete.tsv` | FR@1/2/3 and N for five behavioral datasets, five conditions and three categories, in two variants: official (`failure_rates.py` logic, not validity-gated) and validity-aware. Beneficial memory has one generation, so FR@2 and FR@3 are `NA`. | `external/PersistBench/outputs/**` | STORED where a stored table matches, else RECOMPUTED_FROM_EXISTING_OUTPUT | Appendix; validity-aware rows for Chapter 4 |
| `tables/generation_validity_complete.tsv` | Validity counts per dataset, model, condition and category from the thesis classifier; zero-valid scenarios; notes on suspected false positives (not overridden) | same, plus `thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py` | RECOMPUTED_FROM_EXISTING_OUTPUT | Appendix |
| `tables/fullprompt_robustness.tsv` | MUSE-News Qwen sycophancy and cross-domain, original versus full prompt: deltas against Target, transition counts, exact sign-test p, validity | `.../muse_news_qwen25_fullprompt_robustness{,_crossdomain}/analysis_results.json` | FR@3 and transitions STORED (verified identical); cross-domain p STORED; sycophancy p RECOMPUTED_FROM_EXISTING_OUTPUT (exact two-sided sign test on stored counts) | Appendix |
| `tables/judge_robustness.tsv` | FR@1/2/3 of the Qwen and Gemma judges for the 15 judged files (official variant) | `qwen_vs_gemma_frk.json` (`thesis_archive.zip`: `thesis/analysis/judge_robustness/`) | STORED | Appendix |
| `tables/judge_agreement.tsv` | Per-track and pooled six-level agreement and kappa (stored); MUSE-News sycophancy generation-binary and scenario-FR@3 agreement (recomputed) | `qwen_vs_gemma_agreement.json`; the 15 + 5 judged files | STORED and RECOMPUTED_FROM_EXISTING_OUTPUT | Appendix |
| `latex_snippets.tex` | Prompt boxes, configuration tables, environment table, robustness-table skeleton. Not compiled. | the files above | | Chapter 3, appendix |

Placement: Chapter 3 takes the three schematic prompts, the condensed PrivacyLens and PersistBench configuration tables and the environment table (all in `latex_snippets.tex`), and the validity-gate description below. The appendix takes the exact prompt files, the full configuration TSVs, `model_checkpoints.tsv`, `script_map.tsv`, and the FR@K, validity, robustness and judge tables. `reproducibility/export_scripts/` and the evidence, confidence and notes columns are supporting material and are not meant to be quoted.

## Validity gate

Used for the validity columns and the validity-aware FR@K. Applied per generation in this order (from `classify` in `thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py`); the first match wins:

- Empty: raw text in {"", "{}", "[]"}, or JSON with at most 40 alphabetic characters.
- Web contamination: the lower-cased text contains one of `skip to content`, `github`, `toggle navigation`, `comments feed`, `techie delight`, `sign in`, `pull requests`, `repository`, `ace your coding interview`, `(button) product`.
- Tool-schema output: contains `"source_filter"`, `"search_query"`, `"tool_calls"`, `"time_frame_filter"` or `"intent": "nav"`.
- Generation collapse: a blacklist of garbage strings, or length under 30 characters, or letter ratio under 0.25, or (at least 30 tokens and top-token share above 0.30).

Everything else is valid. The judge-dependent labels `personal_detail_injection`, `cross_domain_contamination` and `irrelevant_but_coherent` remain valid. There is no `finish_reason` or truncation check.

## Settings and caveats the tables depend on

- Corrected generation settings. The effective repetition penalty of the Qwen PersistBench generations is 1.05 (checkpoint `generation_config.json`, applied by vLLM defaults, confirmed in the vLLM startup logs), not 1.08. MUSE: temperature 0.0, prompt left-truncated to the last 1800 tokens under a 2048 context. TOFU: temperature 1.0. Full-prompt robustness: 8192 context, no truncation. No explicit seed is set anywhere in PersistBench generation (vLLM 0.23.0 logs its own default `seed=0`, which is irrelevant at temperature 0 and gives no reproducibility guarantee at temperature 1.0).
- Llama-2 sampling defaults are INFERRED: the vLLM logs have no override line and the official target has no local `generation_config.json`.
- TOFU PersistBench is a different regime: temperature 1.0, 512 tokens, 8192 context, no truncation, native chat templates. Raw prompts were not stored, but by code inspection nothing was truncated, so the persona text including the condition-specific served-model alias (`You are {model_name}`, for example `qwen25_7b_after_rmu_from_tofufull`) was visible to the model. In the original MUSE runs the truncation removed the persona head including the alias. In the full-prompt robustness runs a neutral alias was used for all conditions.
- Official versus validity-aware FR@K. Official `failure_rates.py` counts every non-null judge score, including generations the validity gate flags. The validity-aware variant drops flagged generations positionally within the first K and excludes scenarios with no valid scored generation. 29 of 75 dataset, condition and category cells differ (mostly MUSE-Books Llama-2 and TOFU). For MUSE-News Qwen only RMU sycophancy differs: FR@3 18.00 (N=200) versus 18.09 (N=199). Both variants are in `persistbench_frk_complete.tsv`; state which one a thesis number uses. MUSE-Books Llama-2 WGA is not evaluable (all outputs are dashes).
- Validity classifier false positives are not overridden. The substring `sign in` fires inside ordinary words (`de[sign in]dustry`); `github`, `repository` and `pull requests` fire on legitimate software-development answers. The `Notes` column of `generation_validity_complete.tsv` counts these. A scenario whose three identical generations are all flagged is dropped from the validity-aware denominator, so false positives can change N (for example the SatImp and SimNPO full-prompt rows with N=199).
- PrivacyLens: prompt variant `naive` in all 70 stored outputs. The Qwen chat template inserts its default system turn (`You are Qwen, created by Alibaba Cloud...`). Llama-2 has no chat template (raw text, mostly unparseable).
- Judge agreement, MUSE-News sycophancy: six-level exact agreement 37.17% (kappa 0.1091, N=3000); generation-binary 50.40% (kappa 0.0930, N=3000); scenario FR@3 47.95% (kappa 0.110, N=999, validity-aware; un-gated 47.90%, kappa 0.1096, N=1000). The pooled values (38.27%, kappa 0.1511, N=9000, sycophancy) are in separate rows labelled POOLED and must not be quoted as MUSE-News values.
- Temperature 0 is not bitwise reproducible. A diagnostic in `mechanistic/experiments/muse_news_sycophancy_final_mechanism/repro_check/` found that rerunning the original vLLM pipeline reproduces the July generations only about 55% of the time, so FR@2 and FR@3 exceeding FR@1 partly reflects non-determinism.

## Artifacts not to cite

| Artifact | Reason |
|---|---|
| `"repetition_penalty": 1.08` (with `top_p: 1.0`, `vllm_seed: 0`) in `mechanistic/privacy_collapse/persistbench_native/generations/*_generation0.jsonl`, `.../manifests/native_{cross_domain,sycophancy}_200_v1.json` and the copies under `mechanistic/outputs/muse_books_weekly_update_analysis/native_{cross_domain,sycophancy}/` | Metadata written after the fact from the later `STRICT_GENERATION_CONTROL` default. The true value is 1.05 (Qwen). The generated text is valid. Correction: `thesis/manifests/provenance/persistbench_generation_corrections.json`. The value 1.08 belongs to the out-of-scope WMDP-Cyber strict-generation runs. |
| Current `external/PersistBench/src/benchmark/utils.py` as a description of MUSE or TOFU generation | It contains the `STRICT_GENERATION_CONTROL` and forced-truncation blocks added on 2026-07-21, after all MUSE and TOFU generations. |
| The Gemma-2 documents in `thesis/analysis/judge_robustness/` (`README.md` stating the run stopped at the SLURM smoke test, `GEMMA_PROVENANCE_NOTE.md`, `gemma_availability_check.md`, `smoke_test/*`; in `thesis_archive.zip`) | Superseded. The judge used is `google/gemma-3-12b-it` (revision `96b6f1eccf38110c56df3a15bffe176da04bfd80`); full results exist for 15 files. |
| The statement in `thesis/docs/generation_provenance.md` of an earlier version that the Llama-2 repetition penalty is uncertain | Current text: no override line was logged, so the vLLM default is inferred (INFERRED). |
| `thesis/manifests/environment/pip_freeze_current_env.txt` as the training environment | It is the conda `base` (vLLM) environment. The training environment is `conda_unlearning.yml`. |
| Raw (non-validity-gated) FR@K tables where the thesis uses validity-aware FR@K: `presentation_figures_final/persistbench_all_methods_all_corpora.csv`, `persistbench_fr3_summary.csv`, `tofu_persistbench_fr3_summary.csv`, `thesis_defense_assets_bundle/data/persistbench_all_methods_all_corpora_qwen_judge.csv`, `thesis_defense_assets_bundle/tables/01_*` and `02_*`, `qwen_vs_gemma_frk.json` | These are official `failure_rates.py` numbers (column `exclusions: none`). Use `tables/persistbench_frk_complete.tsv` and select the validity-aware rows. Statements that invalid generations are excluded do not hold for these tables. |
| Pooled "privacy-context %" and strict/broad classifier outputs: `mechanistic/analyze_benchmark_paradox.py`, `mechanistic/outputs/benchmark_paradox/*`, `external/PersistBench/outputs/PERSISTBENCH_VALID_ONLY_PRIVACY_CONTEXT_COMPARISON.tsv`, `gemma_valid_only_{strict,broad}.csv`, and the `mean_score`, `score1_pct` and `personal_detail_injection_pct` columns of the validity summary TSVs (for example the "3.85% -> 4.92%" figure) | Not FR@K, and not comparable to the official metric. |
| MUSE-News official-target run: `external/PersistBench/outputs/muse_news_selected_full/`, `outputs/privacylens_muse_news_selected/`, `saves/final_muse_news_*`, `research_history/04_muse_track_a/` (archive) | Superseded by the Qwen2.5-7B run. Listed in `model_checkpoints.tsv` and `generation_configurations.tsv` for completeness; none of its numbers belong in the main results. |
| MUSE-Books Qwen fine-tune-time MUSE evaluations (`saves/finetune/muse_books_qwen25_7b_instruct_target/checkpoint-*/evals/*`) | They ran on the News split because of a config bug. Use the unlearn step-0 log. |
| `external/PersistBench/outputs/{qwen25_7b_full,llama31_8b_full}/*.json` (non-`_localjudge` copies), `muse_books_qwen25_selected_full/backup_before_rejudge_20260712_150634/`, `outputs/*wmdp*`, `external/PersistBench/outputs/wmdp_*` | Unjudged or partly judged originals, backups, and out-of-scope WMDP-Cyber runs. |
| `mechanistic/outputs/muse_news_sycophancy_mechanistic/` case selection (`continuation_cases_v1.json`) | Earlier case set, superseded by `mechanistic/experiments/muse_news_sycophancy_paradox/`. |
| `thesis/scripts/privacylens/eval_privacylens_mcq_local_strict.py`, `..._forced_choice.py`, and the Llama-2 forced-choice outputs | Never run or degenerate; not canonical. |

## Re-verifying the tables

```bash
# reads existing results; rewrites only thesis/appendix_material/tables
PYTHONDONTWRITEBYTECODE=1 python3 -B thesis/appendix_material/reproducibility/export_scripts/compute_tables.py
```

The script prints any stored-versus-recomputed mismatch (currently none) and the four MUSE-News agreement figures quoted above. It needs the frozen outputs under `external/PersistBench/outputs/`, which are not in the repository.
