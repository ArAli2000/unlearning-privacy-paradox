# Gemma-3-12B independent judge -- supervisor results (Gemma-only)

**Independent judge robustness evaluation.** All numbers below are computed directly from the 15 Gemma-3-judged result files under `external/PersistBench/outputs_gemma3_judge/`, re-derived fresh for this report (not copied from prior prose). Qwen appears only in a short note near the end.

## 1. Executive answer

Under the independent Gemma-3-12B judge, **9/12 (75.0%)** of BASE-to-unlearning cross-domain comparisons show a WORSE (higher) failure rate than BASE; 2 improve; 1 are unchanged. See section 11 for the full conservative interpretation.

## 2. Exact cross-domain results

**Metric definition** (`external/PersistBench/analysis/failure_rates.py`, imported and used directly, not reimplemented): FR@K = % of entries where max(score of first K generations) >= 3 (higher = worse)

**Primary K used in this report**: FR@1 (generation index 0 only). Chosen because: (a) it matches the per-entry N reported below exactly (one score per entry, no aggregation across multiple generations); (b) it matches the generation-index-0 convention already used by the existing mechanistic transition-group manifest (sycophancy_transitions.json); (c) the earlier qwen_vs_gemma_frk.json/.md already reports FR@1/FR@2/FR@3 side by side for anyone who wants the 3-generation view -- this report does not replace that file, it adds an exact, Gemma-only, N-corrected view at K=1.

| Dataset | Model | Method | N | BASE failures | BASE rate % | Method failures | Method rate % | Delta (pp) | Direction |
|---|---|---|---|---|---|---|---|---|---|
| MUSE-News | Qwen2.5-7B-Instruct | RMU | 200 | 58 | 29.00% | 71 | 35.50% | +6.50 | WORSE |
| MUSE-News | Qwen2.5-7B-Instruct | WGA | 200 | 58 | 29.00% | 67 | 33.50% | +4.50 | WORSE |
| MUSE-News | Qwen2.5-7B-Instruct | SimNPO | 200 | 58 | 29.00% | 70 | 35.00% | +6.00 | WORSE |
| MUSE-News | Qwen2.5-7B-Instruct | SatImp | 200 | 58 | 29.00% | 71 | 35.50% | +6.50 | WORSE |
| MUSE-Books | Llama-2-7B | RMU | 200 | 122 | 61.00% | 160 | 80.00% | +19.00 | WORSE |
| MUSE-Books | Llama-2-7B | WGA | 200 | 122 | 61.00% | 57 | 28.50% | -32.50 | BETTER |
| MUSE-Books | Llama-2-7B | SimNPO | 200 | 122 | 61.00% | 140 | 70.00% | +9.00 | WORSE |
| MUSE-Books | Llama-2-7B | SatImp | 200 | 122 | 61.00% | 117 | 58.50% | -2.50 | BETTER |
| MUSE-Books | Qwen2.5-7B-Instruct | RMU | 200 | 60 | 30.00% | 86 | 43.00% | +13.00 | WORSE |
| MUSE-Books | Qwen2.5-7B-Instruct | WGA | 200 | 60 | 30.00% | 64 | 32.00% | +2.00 | WORSE |
| MUSE-Books | Qwen2.5-7B-Instruct | SimNPO | 200 | 60 | 30.00% | 68 | 34.00% | +4.00 | WORSE |
| MUSE-Books | Qwen2.5-7B-Instruct | SatImp | 200 | 60 | 30.00% | 60 | 30.00% | +0.00 | SAME |

## 3. Cross-domain consistency counts

- Total evaluable BASE->unlearning comparisons: **12**
- WORSEN: **9** (75.0%)
- IMPROVE: **2**
- UNCHANGED: **1**

**Every exception to worsening:**

| Dataset | Model | Method | BASE % | Method % | Delta (pp) | Direction |
|---|---|---|---|---|---|---|
| MUSE-Books | Llama-2-7B | WGA | 61.00% | 28.50% | -32.50 | BETTER |
| MUSE-Books | Llama-2-7B | SatImp | 61.00% | 58.50% | -2.50 | BETTER |
| MUSE-Books | Qwen2.5-7B-Instruct | SatImp | 30.00% | 30.00% | +0.00 | SAME |

## 4. Per-track summary (cross-domain)

| Dataset | Model | RMU | WGA | SimNPO | SatImp | Overall track pattern |
|---|---|---|---|---|---|---|
| MUSE-News | Qwen2.5-7B-Instruct | ↑ | ↑ | ↑ | ↑ | 4/4 worsen |
| MUSE-Books | Llama-2-7B | ↑ | ↓ | ↑ | ↓ | 2/4 worsen |
| MUSE-Books | Qwen2.5-7B-Instruct | ↑ | ↑ | ↑ | = | 3/4 worsen |

(↑ = worse, ↓ = better, = = unchanged)

## 5. Per-method summary (cross-domain, aggregated across the 3 tracks)

| Method | # worse | # better | # same | Total | % worse |
|---|---|---|---|---|---|
| RMU | 3 | 0 | 0 | 3 | 100.0% |
| WGA | 2 | 1 | 0 | 3 | 66.7% |
| SimNPO | 3 | 0 | 0 | 3 | 100.0% |
| SatImp | 1 | 1 | 1 | 3 | 33.3% |

Most consistent contextual-privacy degradation under Gemma: **RMU** (3/3 tracks worsen). No claim of statistical significance is made from this table alone (see section 7).

## 6. Sycophancy results

**Metric**: FR@K = % of entries where max(score of first K generations) >= 3 (higher = worse)

| Dataset | Model | Method | BASE % | Method % | Delta (pp) | Direction |
|---|---|---|---|---|---|---|
| MUSE-News | Qwen2.5-7B-Instruct | RMU | 48.00% | 65.00% | +17.00 | WORSE |
| MUSE-News | Qwen2.5-7B-Instruct | WGA | 48.00% | 56.00% | +8.00 | WORSE |
| MUSE-News | Qwen2.5-7B-Instruct | SimNPO | 48.00% | 55.50% | +7.50 | WORSE |
| MUSE-News | Qwen2.5-7B-Instruct | SatImp | 48.00% | 54.00% | +6.00 | WORSE |
| MUSE-Books | Llama-2-7B | RMU | 68.50% | 79.00% | +10.50 | WORSE |
| MUSE-Books | Llama-2-7B | WGA | 68.50% | 37.00% | -31.50 | BETTER |
| MUSE-Books | Llama-2-7B | SimNPO | 68.50% | 83.50% | +15.00 | WORSE |
| MUSE-Books | Llama-2-7B | SatImp | 68.50% | 69.00% | +0.50 | WORSE |
| MUSE-Books | Qwen2.5-7B-Instruct | RMU | 45.50% | 53.50% | +8.00 | WORSE |
| MUSE-Books | Qwen2.5-7B-Instruct | WGA | 45.50% | 54.50% | +9.00 | WORSE |
| MUSE-Books | Qwen2.5-7B-Instruct | SimNPO | 45.50% | 51.50% | +6.00 | WORSE |
| MUSE-Books | Qwen2.5-7B-Instruct | SatImp | 45.50% | 51.00% | +5.50 | WORSE |

Sycophancy worsens in **11/12** BASE->method comparisons under Gemma.

## 7. Beneficial-memory-usage results

**Metric (semantics differ from the other two categories -- read carefully)**: FR@K = 100% - (% of entries where max(score of first K generations) >= 2); i.e. a row's underlying pass criterion is score>=2 (good/beneficial memory use), and the reported rate counts rows that do NOT reach that -- higher reported rate still means WORSE (more rows failing to use memory beneficially), but the per-row flag being counted is inverted relative to the other two categories.

| Dataset | Model | Method | BASE % | Method % | Delta (pp) | Direction |
|---|---|---|---|---|---|---|
| MUSE-News | Qwen2.5-7B-Instruct | RMU | 4.00% | 2.00% | -2.00 | BETTER |
| MUSE-News | Qwen2.5-7B-Instruct | WGA | 4.00% | 4.00% | +0.00 | SAME |
| MUSE-News | Qwen2.5-7B-Instruct | SimNPO | 4.00% | 2.00% | -2.00 | BETTER |
| MUSE-News | Qwen2.5-7B-Instruct | SatImp | 4.00% | 1.00% | -3.00 | BETTER |
| MUSE-Books | Llama-2-7B | RMU | 81.00% | 86.00% | +5.00 | WORSE |
| MUSE-Books | Llama-2-7B | WGA | 81.00% | 35.00% | -46.00 | BETTER |
| MUSE-Books | Llama-2-7B | SimNPO | 81.00% | 86.00% | +5.00 | WORSE |
| MUSE-Books | Llama-2-7B | SatImp | 81.00% | 83.00% | +2.00 | WORSE |
| MUSE-Books | Qwen2.5-7B-Instruct | RMU | 4.00% | 17.00% | +13.00 | WORSE |
| MUSE-Books | Qwen2.5-7B-Instruct | WGA | 4.00% | 3.00% | -1.00 | BETTER |
| MUSE-Books | Qwen2.5-7B-Instruct | SimNPO | 4.00% | 4.00% | +0.00 | SAME |
| MUSE-Books | Qwen2.5-7B-Instruct | SatImp | 4.00% | 7.00% | +3.00 | WORSE |

Under this report's higher-reported-rate-is-worse convention (see metric note above), beneficial-memory-usage failure worsens in **5/12** and improves in **5/12** BASE->method comparisons. Recall: a row's underlying per-row criterion here is the OPPOSITE polarity of cross_domain/sycophancy (pass = score>=2, i.e. good memory use), so this table is not directly comparable row-for-row to the cross_domain/sycophancy tables above without keeping that in mind.

## 7b. Uncertainty (Wilson 95% CIs, N; McNemar exact test, cross-domain only)

All N here are per-condition entry counts (matched pairs use the intersection of valid BASE and method entry IDs). CIs are independent per-condition Wilson score intervals -- not a paired test. McNemar's exact test below IS the paired test, on the discordant BASE<->method transitions.

| Dataset | Model | Method | N | Failures | Rate % | Wilson 95% CI |
|---|---|---|---|---|---|---|
| MUSE-News | Qwen2.5-7B-Instruct | BASE | 200 | 58 | 29.00% | [23.15, 35.64] |
| MUSE-News | Qwen2.5-7B-Instruct | RMU | 200 | 71 | 35.50% | [29.20, 42.35] |
| MUSE-News | Qwen2.5-7B-Instruct | WGA | 200 | 67 | 33.50% | [27.32, 40.30] |
| MUSE-News | Qwen2.5-7B-Instruct | SimNPO | 200 | 70 | 35.00% | [28.73, 41.84] |
| MUSE-News | Qwen2.5-7B-Instruct | SatImp | 200 | 71 | 35.50% | [29.20, 42.35] |
| MUSE-Books | Llama-2-7B | BASE | 200 | 122 | 61.00% | [54.09, 67.49] |
| MUSE-Books | Llama-2-7B | RMU | 200 | 160 | 80.00% | [73.91, 84.95] |
| MUSE-Books | Llama-2-7B | WGA | 200 | 57 | 28.50% | [22.70, 35.12] |
| MUSE-Books | Llama-2-7B | SimNPO | 200 | 140 | 70.00% | [63.32, 75.93] |
| MUSE-Books | Llama-2-7B | SatImp | 200 | 117 | 58.50% | [51.57, 65.11] |
| MUSE-Books | Qwen2.5-7B-Instruct | BASE | 200 | 60 | 30.00% | [24.07, 36.68] |
| MUSE-Books | Qwen2.5-7B-Instruct | RMU | 200 | 86 | 43.00% | [36.33, 49.93] |
| MUSE-Books | Qwen2.5-7B-Instruct | WGA | 200 | 64 | 32.00% | [25.93, 38.75] |
| MUSE-Books | Qwen2.5-7B-Instruct | SimNPO | 200 | 68 | 34.00% | [27.79, 40.81] |
| MUSE-Books | Qwen2.5-7B-Instruct | SatImp | 200 | 60 | 30.00% | [24.07, 36.68] |

**McNemar's exact test, BASE vs. each method (cross-domain, paired by entry ID):**

| Dataset | Model | Method | N paired | n01 (BASE safe -> fail) | n10 (BASE fail -> safe) | Exact p-value |
|---|---|---|---|---|---|---|
| MUSE-News | Qwen2.5-7B-Instruct | RMU | 200 | 33 | 20 | 0.098371 |
| MUSE-News | Qwen2.5-7B-Instruct | WGA | 200 | 35 | 26 | 0.305677 |
| MUSE-News | Qwen2.5-7B-Instruct | SimNPO | 200 | 32 | 20 | 0.126347 |
| MUSE-News | Qwen2.5-7B-Instruct | SatImp | 200 | 34 | 21 | 0.104789 |
| MUSE-Books | Llama-2-7B | RMU | 200 | 55 | 17 | 8e-06 |
| MUSE-Books | Llama-2-7B | WGA | 200 | 17 | 82 | 0.0 |
| MUSE-Books | Llama-2-7B | SimNPO | 200 | 46 | 28 | 0.047393 |
| MUSE-Books | Llama-2-7B | SatImp | 200 | 28 | 33 | 0.608921 |
| MUSE-Books | Qwen2.5-7B-Instruct | RMU | 200 | 46 | 20 | 0.001858 |
| MUSE-Books | Qwen2.5-7B-Instruct | WGA | 200 | 29 | 25 | 0.683489 |
| MUSE-Books | Qwen2.5-7B-Instruct | SimNPO | 200 | 22 | 14 | 0.242985 |
| MUSE-Books | Qwen2.5-7B-Instruct | SatImp | 200 | 17 | 17 | 1.0 |

These McNemar tests are exploratory/secondary, reported alongside the raw effect sizes above, not in place of them.

## 8. Gemma judge methodology (independent judge robustness evaluation)

- Model: `google/gemma-3-12b-it` (Gemma3ForConditionalGeneration, `bfloat16`)
- Judging server `--max-model-len`: 16384
- Measured maximum real prompt length across all judgment requests: 9249 tokens
- Required context with 256 output tokens: 9505
- Truncation occurred: **False**
- Total judgment requests across all 15 files: 19500
- Request errors: 0; unparseable outputs: 0
- Self-repair: 1500 succeeded, 0 failed
- All completed judgments parseable: **True**

Gemma-3-12B is used here as an **independent judge for robustness evaluation**, not as ground truth.

## 9. Qwen robustness note (very short)

This is a secondary robustness note, not the main result. Verified directly from `qwen_vs_gemma_agreement.json`:

| Category | Exact match | Kappa (unweighted) | Kappa (linear-weighted) |
|---|---|---|---|
| cross_domain | 62.3% | 0.2527 | 0.2644 |
| sycophancy | 38.3% | 0.1511 | 0.1552 |
| beneficial_memory_usage | 66.6% | 0.4921 | 0.5704 |

Directional robustness (recomputed fresh from `qwen_vs_gemma_frk.json`'s FR@1 values): **11/36** method x category x track BASE->method comparisons reverse direction between the two judges. This does not mean either judge is "correct" -- it quantifies how much the qualitative BASE->method story depends on which judge is used.

## 10. Mechanistic transition-group warning

The existing MUSE-News sycophancy BASE->SatImp/SimNPO generation-0 transition groups (`mechanistic/privacy_collapse/persistbench_native/analysis/sycophancy/sycophancy_transitions.json`) were originally defined using **Qwen** judgments. Re-checked against Gemma-3 scores for the identical rows:

- **SatImp**: 130/200 rows (65.0%) change transition bucket under Gemma.
- **SimNPO**: 124/200 rows (62.0%) change transition bucket under Gemma.

Because case membership is judge-sensitive, the existing mechanistic case selection should be described as **"Qwen-defined transition groups"** specifically, not as a judge-agnostic ground truth, unless the mechanistic experiment is repeated with Gemma-defined groups.

## 11. Supervisor-ready conclusion

1. **Does Gemma independently support the claim that unlearning can worsen contextual privacy?** Yes -- Gemma independently shows contextual-privacy (cross-domain) degradation in 9/12 BASE->unlearning comparisons.
2. **Is the effect universal?** No -- it is not universal: there are 3 exceptions listed in section 3.
3. **On how many exact cross-domain comparisons does it worsen?** 9 of 12 (75.0%).
4. **Which datasets/models/methods are the exceptions?** MUSE-Books/Llama-2-7B/WGA; MUSE-Books/Llama-2-7B/SatImp; MUSE-Books/Qwen2.5-7B-Instruct/SatImp (see section 3 for exact deltas).
5. **Is the finding method-dependent?** See section 5 for exact per-method worsening rates; note whether they are uniform or vary before treating the effect as method-independent.
6. **Does the independent judge strengthen or weaken the thesis's main claim?** Gemma independently reproduces a contextual-privacy degradation signal under unlearning at the aggregate cross-domain level, which is directionally consistent with (though not a carbon copy of) the Qwen-judged story -- see section 9 for exactly how often the two judges agree and disagree on the specific BASE->method direction. This strengthens the claim that the degradation is not solely an artifact of the Qwen judge sharing a model family with the Qwen-derived evaluated checkpoints (since the effect also appears on the Llama-2 track, which shares no family with either judge), while the disagreement rate in section 9 means the *exact magnitude and case-level membership* should not be treated as judge-independent.
7. **What should I NOT claim?** Do NOT claim "unlearning always worsens contextual privacy" as an unconditional/universal law unless section 3's exception list is empty. Do NOT claim Gemma is ground truth. Do NOT claim the mechanistic transition-group case selection is judge-agnostic (section 10). Do NOT treat the Wilson CIs or McNemar p-values in section 7b as adjusted for multiple comparisons across the 12 cross-domain tests.

## 12. Provenance / source files

- Primary source (read-only): the 15 files under `external/PersistBench/outputs_gemma3_judge/`.
- Metric code (read-only, imported not reimplemented): `external/PersistBench/analysis/failure_rates.py`.
- Cross-checked existing analysis files (read-only): `qwen_vs_gemma_agreement.json`, `qwen_vs_gemma_mechanistic_transitions.json`, `qwen_vs_gemma_frk.json` (its FR@K percentages were reused/reverified; its `n` field was found to be incorrect and was NOT reused -- see the module docstring of `build_gemma_only_supervisor_report.py`).
- Full-run judging log (read-only): `logs/gemma3_judge_full_438810.err`.
- This report's generator script: `thesis/analysis/judge_robustness/build_gemma_only_supervisor_report.py`.
- Outputs: `GEMMA_ONLY_SUPERVISOR_RESULTS.md` (this file), `gemma_only_exact_results.csv`, `gemma_only_exact_results.json`.
- No existing file was modified. No LLM inference was run to produce this report. Nothing was committed or pushed.

