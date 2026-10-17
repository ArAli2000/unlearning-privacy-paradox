# Supervisor update material: independent PersistBench judge validation

This folder contains slide-ready figures generated only from checked-in result files. Run `python thesis/analysis/judge_robustness/build_supervisor_update_figures.py` from the repository root to reproduce them.

## Figure provenance

| Figure | Exact source file | Values used |
|---|---|---|
| `gemma_cross_domain_base_vs_unlearning.{png,pdf}` | `thesis/analysis/judge_robustness/gemma_only_exact_results.csv` | Rows where `category=cross_domain`; `base_rate` and `method_rate` |
| `qwen_vs_gemma_agreement.{png,pdf}` | `thesis/analysis/judge_robustness/qwen_vs_gemma_agreement.json` | `overall.*.exact_match_rate` and `cohens_kappa_unweighted` |
| `gemma_method_consistency.{png,pdf}` | `thesis/analysis/judge_robustness/gemma_only_exact_results.csv` | Rows where `category=cross_domain`; counts of `direction` by `method` |
| `mechanistic_transition_reclassification.{png,pdf}` | `thesis/analysis/judge_robustness/qwen_vs_gemma_mechanistic_transitions.json` | `n_reclassified` / `n_total_checked` for SatImp and SimNPO |

## Table provenance

| Slide table | Exact source file |
|---|---|
| Gemma cross-domain FR@1 table (12 BASE→method comparisons) | `thesis/analysis/judge_robustness/gemma_only_exact_results.csv` (`category=cross_domain`) |
| Judge agreement table | `thesis/analysis/judge_robustness/qwen_vs_gemma_agreement.json` (`overall`) |
| Gemma verification/context table | `thesis/analysis/judge_robustness/gemma3_prompt_length_analysis.json` (`overall`) plus `thesis/analysis/judge_robustness/GEMMA_ONLY_SUPERVISOR_RESULTS.md` section 8 for run/parse status |
| Mechanistic transition warning | `thesis/analysis/judge_robustness/qwen_vs_gemma_mechanistic_transitions.json` |

The raw Gemma-judged outputs are under `external/PersistBench/outputs_gemma3_judge/` (15 result files, stored in track subdirectories). The report generator identifies `external/PersistBench/analysis/failure_rates.py` as the metric implementation.
