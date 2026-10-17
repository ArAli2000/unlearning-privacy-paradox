# THESIS FACTS (factual reference for writing; no interpretation, no new claims)

Generated 2026-10-16 from frozen artifacts by `scripts/build_handoff_data.py` and `scripts/build_handoff_materials.py`. Every number below was recomputed from per-generation validity-v2 labels and judge scores with exact fractions and cross-checked against the frozen analyses and against a fresh v2 classification of the raw JSON (see `integrity_check.txt`). "pp" = percentage points. Beneficial memory is called `beneficial_memory_usage` inside PersistBench files.

## Standing warnings
- **No multiple-comparison correction was applied anywhere.** All p-values are exact two-sided paired (McNemar/binomial on discordant scenarios) and *nominal*. 24 full-prompt comparisons were tested; about 1.2 nominal p < 0.05 are expected by chance alone.
- **Effects of about 3 pp or smaller should be interpreted cautiously.** Between the original and replicated truncated runs of the same models, 4.95% of scenario classifications change (198/4,000, cross-domain + sycophancy), and in 3 of 24 Target-to-unlearned comparisons the sign of the delta flips.
- The 24 Target-to-unlearned comparisons share their Target baselines, so counts of sign agreement are descriptive and not independent.
- All FR values are the **validity-aware** FR@K (frozen validity classifier v2, `repetition_rule=False`), not the official un-gated `failure_rates.py` value; they differ in exactly one (cell, K) pair of the full-prompt matrix (Books RMU sycophancy FR@1: 11.5578 [N=199] validity-aware vs 11.50 [N=200] un-gated).

## Complete full-prompt Qwen matrix (generation counts)

- 2 datasets x 5 conditions x 3 categories = 30 cells; **13,000 generations**, all judged by the primary judge (Qwen2.5-7B-Instruct as `local-judge`). Per condition and dataset: 600 cross-domain (200 scenarios x 3) + 600 sycophancy (200 x 3) + 100 beneficial memory (100 x 1) = 1,300; per dataset 6,500.
- **Reused: 4,800** generations = 8 existing News cells (Target, RMU, SatImp, SimNPO x cross-domain, sycophancy; 600 each) from `external/PersistBench/outputs/muse_news_qwen25_fullprompt_robustness/` (sycophancy, job 466200) and `..._crossdomain/` (cross-domain, job 466206). **Newly generated: 8,200** = News 1,700 (WGA 1,300 + beneficial memory for Target/RMU/SatImp/SimNPO 400; job 466336) + Books 6,500 (jobs 466337 Target+RMU, 466338 WGA+SatImp, 466339 SimNPO). New files: `external/PersistBench/outputs/muse_qwen_fullprompt_complete_20261016/{muse_news,muse_books}/`. Per-cell source file and SHA-256: `thesis/analysis/muse_qwen_fullprompt_complete_20261016/fullprompt_manifest.tsv`.
- Generation settings: `max_model_len` 8192, no `truncate_prompt_tokens`, temperature 0.0, max 96 new tokens, `simple_llama_chat_template.jinja`, neutral alias `muse_news_qwen25` / `muse_books_qwen25` shared by all five conditions of a dataset; effective top_p 0.8 / top_k 20 / repetition_penalty 1.05 inherited from the checkpoint `generation_config.json`.

## Validity (v2, repetition rule off)

- **12,999 / 13,000 generations valid (99.9923%).** The one invalid generation: MUSE-Books RMU sycophancy, scenario #30 of 200 in the category input order (hash `257a6d15c550b83754ed6f6f0cb84194`), generation position 1, label `gibberish_or_generation_collapse`, rule `collapse:top-token>30%`, judge score 0; file `external/PersistBench/outputs/muse_qwen_fullprompt_complete_20261016/muse_books/muse_books_qwen25_rmu_fullprompt_sycophancy.json`. Consequence: Books RMU sycophancy FR@1 has N = 199 (FR@2, FR@3: N = 200). Every other cell is 100% valid with full N.
- No full-prompt Qwen condition collapsed (contrast: MUSE-Books Llama-2 WGA, 1,300/1,300 invalid in both truncated runs).
- v2 differs from v1 only in the web/page-contamination rule (whole-phrase matching; `github`, `repository`, `pull requests` removed as evidence); source: module docstring of `thesis/scripts/validation/create_persistbench_validity_summary_v2.py` (SHA-256 `b6bc85e30d705f6bce39e4fb3d6086d285f3cf2f884329ed2b1fd5271d175bf7`).

## Hardware and software

- **All 30 full-prompt cells: NVIDIA H200 NVL** (gres `h200nvl`; 8 reused News cells on node lenny, jobs 466200/466206; 22 new cells on node nelson, jobs 466336-466339). CUDA_HOME=/nfs/cuda/cuda-12.2  nvcc=Build cuda_12.2.r12.2/compiler.33053471_0; vllm=0.23.0 torch=2.11.0+cu130 transformers=5.12.1.
- Original truncated runs: **A100 80GB** (gres a180; News job 408558_0 node penelope; Books job 409517_0 node rubeus). Truncated replication: **H200 NVL** (News job 466261 node lenny; Books job 466262 node nelson). vLLM 0.23.0 in all runs.
- Therefore original-truncated vs full-prompt differs in prompt/context AND hardware; replicated-truncated vs full-prompt differs only in prompt/context (same GPU family); original vs replicated truncated differs only in hardware (plus rerun noise).

## Prompt length and the effect of the original truncation

- vLLM-reported `prompt_tokens` over all 13,000 full-prompt generations: **4,760 to 5,125** (min/median/max: cross-domain 4769/4943/5122, sycophancy 4833/4934/5125, beneficial memory 4760/4872/5073). News and Books prompts have identical lengths. Maximum 5,125 + 96 generated tokens = 5,221 < 8,192.
- The original truncation kept the last 1,800 prompt tokens, i.e. removed about **62.2% to 64.9%** of each prompt (shortest to longest prompt) (median prompts: cross-domain 63.6%, sycophancy 63.5%, beneficial memory 63.1%). What was removed is the persona/tool header (including the two `{model_name}` alias lines); the complete memories block and the query lay within the retained last 1,800 tokens in all 600 scenarios per dataset (pre-run reconstruction, `prompt_length_audit.tsv`). All 600 scenarios per dataset exceed 1,800 tokens.

## SatImp, MUSE-News Qwen (exact values; Delta = SatImp - Target, pp)

| regime | hardware | context / truncation | cross-domain Target / SatImp FR@3 | Delta | p | syc. Target / SatImp FR@3 | Delta | p | beneficial Target / SatImp FR@1 | Delta | p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| original | A100 | 2048 / last 1800 | 3.50 / 3.00 | -0.50 | 1.0000 | 12.50 / 17.00 | +4.50 | 0.1078 | 1.00 / 0.00 | -1.00 | 1.0000 |
| replicated | H200 | 2048 / last 1800 | 4.00 / 3.50 | -0.50 | 1.0000 | 15.00 / 17.50 | +2.50 | 0.4583 | 2.00 / 1.00 | -1.00 | 1.0000 |
| full | H200 | 8192 / none | 1.50 / 3.00 | +1.50 | 0.4531 | 12.50 / 15.50 | +3.00 | 0.2863 | 1.00 / 1.00 | 0.00 | 1.0000 |

Discordant scenarios (S->F / F->S): original cross-domain 4/5; original sycophancy 17/8; original beneficial memory 0/1; replicated cross-domain 3/4; replicated sycophancy 17/12; replicated beneficial memory 1/2; full cross-domain 5/2; full sycophancy 14/8; full beneficial memory 0/0. Exact values: `satimp_three_way.tsv`.

## SimNPO, MUSE-News Qwen

- Full prompt, cross-domain: Target FR@3 1.50, SimNPO 5.00, Delta +3.50 pp; S->F 8, F->S 1, N 200, p = 0.0391. Truncated Delta (original / replicated): -1.50 / +0.50 pp.
- Full prompt, sycophancy: Target FR@3 12.50, SimNPO 13.50, Delta +1.00 pp; S->F 12, F->S 10, N 200, p = 0.8318. Truncated Delta (original / replicated): +2.50 / +2.50 pp.
- Full prompt, beneficial memory: Target FR@1 1.00, SimNPO 2.00, Delta +1.00 pp; S->F 1, F->S 0, N 100, p = 1.0000. Truncated Delta (original / replicated): 0.00 / -1.00 pp.

## RMU, MUSE-Books Qwen (full prompt; truncated original / replicated Delta for reference)

- cross-domain: Target FR@3 4.50 -> RMU 22.50, Delta +18.00 pp; S->F 40, F->S 4, N 200, p = 1.71e-08; truncated Delta original +13.50 / replicated +13.50 pp.
- sycophancy: Target FR@3 9.00 -> RMU 17.50, Delta +8.50 pp; S->F 23, F->S 6, N 200, p = 0.00232; truncated Delta original +5.50 / replicated 0.00 pp.
- beneficial memory: Target FR@1 1.00 -> RMU 11.00, Delta +10.00 pp; S->F 11, F->S 1, N 100, p = 0.00635; truncated Delta original +5.06 / replicated +6.07 pp.

## MUSE-Books Qwen sycophancy, full prompt (Delta vs Target, FR@3, N = 200)

- Target FR@3: full prompt 9.00; original truncated 10.50; replicated truncated 13.50.
- WGA: full-prompt Delta +4.50 pp (S->F 15, F->S 6, p = 0.0784); truncated Delta original -0.50 / replicated -3.00 pp.
- SatImp: full-prompt Delta +2.50 pp (S->F 10, F->S 5, p = 0.3018); truncated Delta original -1.00 / replicated -2.50 pp.
- SimNPO: full-prompt Delta +2.50 pp (S->F 10, F->S 5, p = 0.3018); truncated Delta original -0.50 / replicated -3.50 pp.

## Beneficial memory (one generation per scenario; FR@1; failure = valid judge score < 2)

- MUSE-News full prompt: Target 1.00; RMU 0.00 (Delta -1.00, p = 1); WGA 1.00 (Delta 0.00, p = 1); SatImp 1.00 (Delta 0.00, p = 1); SimNPO 2.00 (Delta +1.00, p = 1).
- MUSE-Books full prompt: Target 1.00; RMU 11.00 (Delta +10.00, p = 0.006348); WGA 1.00 (Delta 0.00, p = 1); SatImp 1.00 (Delta 0.00, p = 1); SimNPO 1.00 (Delta 0.00, p = 1).
- FR@2 and FR@3 of beneficial memory equal FR@1 only because a single generation exists per scenario (the earlier frozen analysis tables mark them `NA`; the handoff master table repeats FR@1 in those columns and says so in its `note` column).

## Scenario-level classification change (denominators = paired scenarios evaluable in both runs; changed = SAFE<->FAILURE)

- original truncated vs replicated truncated: cross-domain + sycophancy 198/4000 = 4.95%; beneficial memory 11/999 = 1.10% (1 scenario excluded as non-evaluable).
- original truncated vs full prompt: cross-domain + sycophancy 356/4000 = 8.90%; beneficial memory 12/999 = 1.20% (1 scenario excluded as non-evaluable).
- replicated truncated vs full prompt: cross-domain + sycophancy 358/4000 = 8.95%; beneficial memory 13/999 = 1.30% (1 scenario excluded as non-evaluable).
- Same-sign counts among the 24 Target-to-unlearned deltas: original truncated vs full prompt: 14/24 (strict flips 5); replicated truncated vs full prompt: 11/24 (strict flips 8); original truncated vs replicated truncated: 17/24 (strict flips 3). Mean |difference of deltas| (pp): original truncated vs full: 1.98; replicated truncated vs full: 2.73; original truncated vs replicated: 1.42.

## Original vs replication repeatability (truncated runs)
- All four settings (News/Books x Qwen/Llama-2), cross-domain + sycophancy: 556/7587 = 7.33% classifications changed (S->F 294, F->S 262); only 38.21% of generations byte-identical. Qwen News + Books only: 198/4,000 = 4.95%. Source: `thesis/analysis/truncated_replication_20261016_v2/`.
- Replication ran on H200 versus A100 for the original; the two cannot be separated (no same-hardware rerun exists).

## Results with nominal p < 0.05 in the complete full-prompt matrix (uncorrected; 5 of 24 tests)

- MUSE-Books RMU cross-domain: Delta +18.00 pp, S->F 40 / F->S 4, N 200, p = 1.71e-08
- MUSE-Books RMU sycophancy: Delta +8.50 pp, S->F 23 / F->S 6, N 200, p = 0.00232
- MUSE-News WGA cross-domain: Delta +5.00 pp, S->F 11 / F->S 1, N 200, p = 0.00635
- MUSE-Books RMU beneficial memory: Delta +10.00 pp, S->F 11 / F->S 1, N 100, p = 0.00635
- MUSE-News SimNPO cross-domain: Delta +3.50 pp, S->F 8 / F->S 1, N 200, p = 0.0391
- All other 19 full-prompt comparisons have nominal p >= 0.05 (e.g. News SatImp sycophancy p = 0.2863, Books WGA sycophancy p = 0.0784).

## Source-document caveats (facts about existing documents)

- `thesis/appendix_material/tables/{fullprompt_robustness,persistbench_frk_complete,generation_validity_complete}.tsv` and the validity-gate rule list in `thesis/appendix_material/README.md` were built with the **v1** classifier (per that README). Only `fullprompt_robustness.tsv` was numerically compared here: 4 of its News cells differ from v2 (listed in `integrity_check.txt`; e.g. SatImp full-prompt FR@3 15.58 with N = 199 under v1 vs 15.50 with N = 200 under v2). Do not take numbers from these three tables; use the handoff tables.
- `thesis/appendix_material/configs/generation_configurations.tsv` still describes the full-prompt run as "MUSE-News only, 4 conditions, beneficial memory not run"; superseded by `final_generation_configs.tsv`.
- `prompts/persistbench_generator_exact.txt` header names only the News neutral alias `muse_news_qwen25`; the Books full-prompt runs used `muse_books_qwen25`.
- TOFU behavioural evaluations loaded each run directory's top-level weights; the selected `checkpoint-N` is recorded in the manifests, but the two were not byte-compared (audited-table note). No selection was changed.
- MUSE-News Llama-2 is the official-target "Track A" setting, labelled SUPERSEDED in `thesis/appendix_material/README.md`; it was nevertheless included in the truncated replication as setting C (`research_history/04_muse_track_a/manifests/muse_news_persistbench_models.tsv`).
