# Complete full-prompt PersistBench evaluation — MUSE-Qwen2.5-7B-Instruct (News + Books)

All numbers come from stored artifacts and were recomputed with the frozen validity classifier v2 (`thesis/scripts/validation/create_persistbench_validity_summary_v2.py`, `repetition_rule=False`, imported unmodified). FR@K, failure rules and exact-fraction deltas are identical to the truncated-replication v2 analysis. Hardware/judge/decoding details are in §4–§6. Hash check: no input artifact changed during the analysis (`analysis_fullprompt_stdout.log`).

## 1. Executive summary
- **The complete full-prompt Qwen matrix now exists**: 2 datasets × 5 conditions × 3 categories = 30 cells, **13,000 generations**, all judged by the primary Qwen2.5-7B local judge, all generated at `max_model_len 8192` with no truncation, all on H200 NVL. 4,800 generations (8 News cells) were reused; **8,200 were newly generated**, exactly the planned count.
- **Validity is essentially perfect** under v2: 12,999 / 13,000 generations valid (one generation-collapse, Books RMU sycophancy).
- **What survives full-prompt evaluation:** RMU is the dominant, robust effect and it *strengthens* with the full prompt (Books cross-domain +13.5 / +13.5 → **+18.0 pp**, p < 0.0001; Books sycophancy +5.5 / 0.0 → **+8.5**, p = 0.002; Books beneficial memory +5.1 / +6.1 → **+10.0**, p = 0.006). Almost everything else is small (|Δ| ≲ 5 pp), mostly non-significant, and changes sign or ±0.5 pp band between evaluation regimes.
- **MUSE-News SatImp** keeps its direction: sycophancy Δ = **+4.5 (original truncated) / +2.5 (replicated truncated) / +3.0 (full prompt)** pp; cross-domain Δ = −0.5 / −0.5 / **+1.5**. The sycophancy-over-cross-domain contrast persists (+3.0 vs +1.5) but is narrower, and the paired test is **not significant in any regime** (p = 0.108 / 0.458 / 0.286).
- **SimNPO does not support that pattern at full prompt**: cross-domain +3.5 pp (nominal p = 0.039) exceeds sycophancy +1.0 pp (p = 0.83).
- **MUSE-Books conclusions are not the same under full prompts for the weak methods**: sycophancy deltas of WGA / SatImp / SimNPO were −0.5 to −3.5 pp (truncated) and become **+4.5 / +2.5 / +2.5** pp. Part of this is a lower Target baseline (9.0 vs 10.5 / 13.5), which is shared by all three comparisons, so they are not independent evidence; none of the three is significant (p = 0.078 / 0.30 / 0.30).
- **Prompt completeness matters beyond rerun noise at the scenario level**: 8.9 % of scenario classifications change between truncated and full prompt (both original-truncated and replicated-truncated give 8.9 %), versus 4.95 % between the original and replicated truncated runs of the same Qwen settings. At the aggregate level the shifts are modest (mean |Δ of delta| 2.0 pp orig→full; 2.7 pp replicated→full; 1.4 pp orig→replicated).
- **Recommendation:** make the complete full-prompt results the primary MUSE-Qwen evidence; keep the original truncated results plus the independent replication as a robustness appendix; keep MUSE Llama-2 truncated as a secondary comparison with its 2,048-token limitation stated (§21).

## 2. Reused vs newly generated artifacts
| | cells | generations | source |
|---|---|---|---|
| News Target/RMU/SatImp/SimNPO cross-domain + sycophancy | 8 | 4,800 | **reused**, `external/PersistBench/outputs/muse_news_qwen25_fullprompt_robustness{,_crossdomain}/` (verified: 200 scenarios, 600 generations, 600 judgments, alias `muse_news_qwen25`, `temperature 0.0, max_tokens 96`, no truncation parameter) |
| News WGA (3 categories) | 3 | 1,300 | new, job 466336 |
| News beneficial memory, Target/RMU/SatImp/SimNPO | 4 | 400 | new, job 466336 |
| Books Target + RMU (3 categories each) | 6 | 2,600 | new, job 466337 |
| Books WGA + SatImp (3 categories each) | 6 | 2,600 | new, job 466338 |
| Books SimNPO (3 categories) | 3 | 1,300 | new, job 466339 |
| **total** | **30** | **13,000** (8,200 new + 4,800 reused) | `fullprompt_manifest.tsv` lists the file and SHA-256 of every cell |

New files: `external/PersistBench/outputs/muse_qwen_fullprompt_complete_20261016/{muse_news,muse_books}/`. No existing artifact was overwritten.

## 3. Exact generation count
8,200 new generations were planned (News 1,700; Books 6,500) and 8,200 were generated and judged: News 1,700, Books 6,500. Per condition and dataset: 600 + 600 + 100 = 1,300. Pre-run audit scripts and tables: `scripts/prerun_audit.py`, `existing_artifact_audit.tsv`, `missing_scope.tsv`.

## 4. Configuration verification
- **Identical to the existing full-prompt News run:** vLLM `--max-model-len 8192`, **no** `truncate_prompt_tokens`, `temperature 0.0`, `max_tokens 96`, `simple_llama_chat_template.jinja` (not the native Qwen template), bf16, `--gpu-memory-utilization 0.90`, concurrency 1, 3 / 3 / 1 generations (cross-domain / sycophancy / beneficial), the sandbox package `pb_src` (no forced truncation, no strict-generation block), `store_raw_api_responses = true`.
- **Effective sampling:** top_p 0.8, top_k 20, repetition_penalty 1.05, taken by vLLM from each checkpoint's `generation_config.json` (identical in all ten checkpoints). Not set explicitly, exactly as in the existing run; the vLLM "sampling parameters overridden" line is present and identical in all 30 cells' logs (`generation_config.tsv`).
- **Checkpoints** (`checkpoint_verification.tsv`): News — Target (fine-tuned), RMU 459, WGA 306, SatImp 459, SimNPO 459; Books — Target, RMU 102, WGA 102, SatImp 51, SimNPO 51. All exist, all come from the canonical model-list manifests, and every one equals the model path logged by the original truncated evaluation's own vLLM server (not inferred from memory). Other `checkpoint-500` directories exist on disk and were not used.
- **Dataset identity** (`dataset_identity_prelaunch.tsv`): per-category benchmark files have 200 / 200 / 100 scenarios; scenario hash IDs and their order are identical to the original truncated outputs, the existing full-prompt outputs and the `full_benchmark.jsonl` subsets. Nothing was regenerated or edited.
- **Neutral aliases:** `muse_news_qwen25` (same as the existing run) and `muse_books_qwen25`, one string shared by all five conditions of a dataset. PersistBench inserts it as `model: {alias}` / `You are {alias}, a large language model.` in the system prompt, so no condition name (before/rmu/wga/satimp/simnpo) is exposed. The alias is also the key under which results are stored; every cell has exactly that single key.
- **Judge:** the same primary judge as the existing run, `Qwen/Qwen2.5-7B-Instruct` served as `local-judge` with identical server flags and the same PersistBench judge code, rubrics and JSON schema (temperature 0). One difference: the new jobs used the default judging concurrency, like the existing full-prompt News run; the *original truncated* Books judge run used `--concurrency 3`. Judging is temperature 0, so I do not expect an effect, but it is a difference.

## 5. Prompt-length / no-truncation verification
Reconstructed from the PersistBench prompt builder, the Qwen tokenizer and the chat template for **all 1,200 scenario prompts** (600 per dataset) before launch (`prompt_length_audit.tsv`, `prompt_samples.md`):

| category | scenarios | min | median | max | max + 96 | fits 8,192 |
|---|---|---|---|---|---|---|
| cross-domain | 200 | 4,771 | 4,945 | 5,124 | 5,220 | yes |
| sycophancy | 200 | 4,835 | 4,936 | 5,127 | 5,223 | yes |
| beneficial memory | 100 | 4,762 | 4,874 | 5,075 | 5,171 | yes |

News and Books prompts are identical in length (same scenarios, same-length alias). Every prompt starts with the full system header, contains all tool sections and closing instructions, the complete memories block and the complete query. The actual vLLM-reported `prompt_tokens` of all 13,000 generations (stored raw responses) are 4,760–5,125, confirming no truncation and sitting 2 tokens above my reconstruction (special tokens). **All prompts are about 2.7× the old 1,800-token limit.** The old truncation removed the persona/tool header (≈3,100 tokens) and kept the memories block and query in all 600 scenarios, i.e. what the old runs lost was system text, not the user's memories or question.

## 6. Hardware
All 30 cells were generated on **H200 NVL** (`generation_config.tsv`): the 8 reused News cells on node `lenny` (jobs 466200, 466206), the 22 new cells on node `nelson`. Same vLLM 0.23.0, torch 2.11.0+cu130, transformers 5.12.1, CUDA 12.2 environment (`_meta/*/env_*.txt`). **The complete full-prompt Qwen suite is hardware-consistent.** The original truncated runs used A100 80 GB (`a180`); the independent truncated replication used H200. Consequently:
- *original truncated vs full prompt* differs in **prompt/context and hardware**;
- *replicated truncated vs full prompt* differs **only in prompt/context (hardware family held constant)** — the cleanest isolation available;
- *original vs replicated truncated* differs only in hardware (plus rerun noise).

## 7. Generation completeness
30/30 cells `COMPLETE+JUDGED` (`generation_completeness.tsv`): 200 / 200 / 100 scenarios, 600 / 600 / 100 generations, 0 generation errors, 0 empty responses, 13,000 judgments present, judge model `local-judge`. Every job ended `COMPLETED 0:0` on the first attempt (466336 1h05, 466337 1h06, 466338 1h06, 466339 0h36); no resumption was needed.

## 8. Validity (v2)
12,999 / 13,000 generations valid (99.99 %). The single invalid generation is a `gibberish_or_generation_collapse` (rule `top-token>30%`) in **Books RMU sycophancy, generation position 1**; every other cell is 100 % valid. **No condition collapsed** at full prompt (unlike MUSE Books Llama-2 WGA). Every FR@K cell is evaluable with N = 200 (100 for beneficial memory); the only exception is Books RMU sycophancy FR@1 with N = 199 (FR@2 and FR@3 stay at N = 200 because a later valid generation exists). Per-generation labels and rules: `generation_validity_v2.tsv` (13,000 rows).

## 9. Complete MUSE-News Qwen full-prompt FR@K
FR@1 / FR@2 / FR@3 (%), N in parentheses; beneficial memory has a single generation, so only FR@1 exists (FR@2/3 are not reported, matching the thesis convention). Δ = FR@3 − Target FR@3 (beneficial: FR@1).

| category | condition | FR@1 | FR@2 | FR@3 | validity % | Δ vs Target (pp) |
|---|---|---|---|---|---|---|
| cross_domain | Target | 0.50 (200) | 1.50 (200) | 1.50 (200) | 100.00 | ref |
| sycophancy | Target | 11.50 (200) | 12.50 (200) | 12.50 (200) | 100.00 | ref |
| beneficial_memory_usage | Target | 1.00 (100) | n/a (1 generation) | n/a (1 generation) | 100.00 | ref |
| cross_domain | RMU | 2.50 (200) | 2.50 (200) | 2.50 (200) | 100.00 | 1.00 |
| sycophancy | RMU | 12.50 (200) | 14.50 (200) | 14.50 (200) | 100.00 | 2.00 |
| beneficial_memory_usage | RMU | 0.00 (100) | n/a (1 generation) | n/a (1 generation) | 100.00 | -1.00 |
| cross_domain | WGA | 3.50 (200) | 6.00 (200) | 6.50 (200) | 100.00 | 5.00 |
| sycophancy | WGA | 11.00 (200) | 13.00 (200) | 13.00 (200) | 100.00 | 0.50 |
| beneficial_memory_usage | WGA | 1.00 (100) | n/a (1 generation) | n/a (1 generation) | 100.00 | 0.00 |
| cross_domain | SatImp | 3.00 (200) | 3.00 (200) | 3.00 (200) | 100.00 | 1.50 |
| sycophancy | SatImp | 14.50 (200) | 15.50 (200) | 15.50 (200) | 100.00 | 3.00 |
| beneficial_memory_usage | SatImp | 1.00 (100) | n/a (1 generation) | n/a (1 generation) | 100.00 | 0.00 |
| cross_domain | SimNPO | 3.50 (200) | 5.00 (200) | 5.00 (200) | 100.00 | 3.50 |
| sycophancy | SimNPO | 12.00 (200) | 13.00 (200) | 13.50 (200) | 100.00 | 1.00 |
| beneficial_memory_usage | SimNPO | 2.00 (100) | n/a (1 generation) | n/a (1 generation) | 100.00 | 1.00 |

## 10. Complete MUSE-Books Qwen full-prompt FR@K
| category | condition | FR@1 | FR@2 | FR@3 | validity % | Δ vs Target (pp) |
|---|---|---|---|---|---|---|
| cross_domain | Target | 4.00 (200) | 4.50 (200) | 4.50 (200) | 100.00 | ref |
| sycophancy | Target | 7.50 (200) | 9.00 (200) | 9.00 (200) | 100.00 | ref |
| beneficial_memory_usage | Target | 1.00 (100) | n/a (1 generation) | n/a (1 generation) | 100.00 | ref |
| cross_domain | RMU | 17.00 (200) | 22.50 (200) | 22.50 (200) | 100.00 | 18.00 |
| sycophancy | RMU | 11.56 (199) | 17.50 (200) | 17.50 (200) | 99.83 | 8.50 |
| beneficial_memory_usage | RMU | 11.00 (100) | n/a (1 generation) | n/a (1 generation) | 100.00 | 10.00 |
| cross_domain | WGA | 1.50 (200) | 2.00 (200) | 2.00 (200) | 100.00 | -2.50 |
| sycophancy | WGA | 10.50 (200) | 13.50 (200) | 13.50 (200) | 100.00 | 4.50 |
| beneficial_memory_usage | WGA | 1.00 (100) | n/a (1 generation) | n/a (1 generation) | 100.00 | 0.00 |
| cross_domain | SatImp | 2.00 (200) | 2.00 (200) | 2.00 (200) | 100.00 | -2.50 |
| sycophancy | SatImp | 10.00 (200) | 11.50 (200) | 11.50 (200) | 100.00 | 2.50 |
| beneficial_memory_usage | SatImp | 1.00 (100) | n/a (1 generation) | n/a (1 generation) | 100.00 | 0.00 |
| cross_domain | SimNPO | 2.00 (200) | 4.00 (200) | 4.00 (200) | 100.00 | -0.50 |
| sycophancy | SimNPO | 8.50 (200) | 11.50 (200) | 11.50 (200) | 100.00 | 2.50 |
| beneficial_memory_usage | SimNPO | 1.00 (100) | n/a (1 generation) | n/a (1 generation) | 100.00 | 0.00 |

## 11. Target-to-unlearned deltas
All K and the ±0.5 pp band per cell: `target_unlearned_deltas.tsv`. Full-prompt Δ (primary K), pp:

| | RMU | WGA | SatImp | SimNPO |
|---|---|---|---|---|
| News cross-domain | +1.0 | **+5.0** | +1.5 | **+3.5** |
| News sycophancy | +2.0 | +0.5 | +3.0 | +1.0 |
| News beneficial | −1.0 | 0.0 | 0.0 | +1.0 |
| Books cross-domain | **+18.0** | −2.5 | −2.5 | −0.5 |
| Books sycophancy | **+8.5** | +4.5 | +2.5 | +2.5 |
| Books beneficial | **+10.0** | 0.0 | 0.0 | 0.0 |

## 12. Paired scenario transitions (Target vs unlearned, full prompt)
Exact two-sided McNemar/binomial p on discordant pairs; beneficial memory uses its single generation and the thesis failure rule (valid score < 2). **No multiplicity correction**; 24 tests, ≈1.2 expected below 0.05 by chance.

| dataset | category | vs Target | S→F | F→S | paired N | non-eval. | Δ (pp) | exact p |
|---|---|---|---|---|---|---|---|---|
| MUSE-News | cross_domain | RMU | 4 | 2 | 200 | 0 | 1.00 | 0.6875 |
| MUSE-News | cross_domain | WGA | 11 | 1 | 200 | 0 | 5.00 | 0.0063 * |
| MUSE-News | cross_domain | SatImp | 5 | 2 | 200 | 0 | 1.50 | 0.4531 |
| MUSE-News | cross_domain | SimNPO | 8 | 1 | 200 | 0 | 3.50 | 0.0391 * |
| MUSE-News | sycophancy | RMU | 15 | 11 | 200 | 0 | 2.00 | 0.5572 |
| MUSE-News | sycophancy | WGA | 8 | 7 | 200 | 0 | 0.50 | 1.0000 |
| MUSE-News | sycophancy | SatImp | 14 | 8 | 200 | 0 | 3.00 | 0.2863 |
| MUSE-News | sycophancy | SimNPO | 12 | 10 | 200 | 0 | 1.00 | 0.8318 |
| MUSE-News | beneficial_memory_usage | RMU | 0 | 1 | 100 | 0 | -1.00 | 1.0000 |
| MUSE-News | beneficial_memory_usage | WGA | 0 | 0 | 100 | 0 | 0.00 | 1.0000 |
| MUSE-News | beneficial_memory_usage | SatImp | 0 | 0 | 100 | 0 | 0.00 | 1.0000 |
| MUSE-News | beneficial_memory_usage | SimNPO | 1 | 0 | 100 | 0 | 1.00 | 1.0000 |
| MUSE-Books | cross_domain | RMU | 40 | 4 | 200 | 0 | 18.00 | < 0.0001 * |
| MUSE-Books | cross_domain | WGA | 2 | 7 | 200 | 0 | -2.50 | 0.1797 |
| MUSE-Books | cross_domain | SatImp | 1 | 6 | 200 | 0 | -2.50 | 0.1250 |
| MUSE-Books | cross_domain | SimNPO | 6 | 7 | 200 | 0 | -0.50 | 1.0000 |
| MUSE-Books | sycophancy | RMU | 23 | 6 | 200 | 0 | 8.50 | 0.0023 * |
| MUSE-Books | sycophancy | WGA | 15 | 6 | 200 | 0 | 4.50 | 0.0784 |
| MUSE-Books | sycophancy | SatImp | 10 | 5 | 200 | 0 | 2.50 | 0.3018 |
| MUSE-Books | sycophancy | SimNPO | 10 | 5 | 200 | 0 | 2.50 | 0.3018 |
| MUSE-Books | beneficial_memory_usage | RMU | 11 | 1 | 100 | 0 | 10.00 | 0.0063 * |
| MUSE-Books | beneficial_memory_usage | WGA | 0 | 0 | 100 | 0 | 0.00 | 1.0000 |
| MUSE-Books | beneficial_memory_usage | SatImp | 0 | 0 | 100 | 0 | 0.00 | 1.0000 |
| MUSE-Books | beneficial_memory_usage | SimNPO | 0 | 0 | 100 | 0 | 0.00 | 1.0000 |

`*` p < 0.05, uncorrected.

Nominal p < 0.05: 5/24 — Books RMU cross-domain (p < 0.0001), Books RMU sycophancy (0.0023), Books RMU beneficial (0.0063), News WGA cross-domain (0.0063), News SimNPO cross-domain (0.039). Only the three Books-RMU results are strong; the News WGA/SimNPO cross-domain results are single nominal hits whose truncated counterparts were not significant (WGA 0.42 / 0.27, SimNPO 0.38 / 1.0) and should not be emphasised.

## 13. Original truncated (A100) vs full prompt
Per cell: `truncated_vs_fullprompt.tsv`. Summary over the 24 Target-to-unlearned comparisons (4 methods × 2 datasets × 3 categories):

| comparison | strict sign agree | strict flips | ±0.5 band agree | inc→dec | dec→inc | mean / median / max \|Δ of delta\| (pp) |
|---|---|---|---|---|---|---|
| original truncated → full | 14/24 | 5 | 14/24 | 0 | 2 | 1.98 / 1.50 / 5.0 |
| replicated truncated → full | 11/24 | 8 | 9/24 | 1 | 4 | 2.73 / 2.00 / 8.5 |
| *reference:* original → replicated truncated | 17/24 | 3 | 14/24 | 0 | 0 | 1.42 / 1.01 / 5.5 |

By method (strict-sign agreement, orig→full / repl→full): **RMU 6/6 / 5/6**, WGA 4/6 / 2/6, SatImp 2/6 / 1/6, SimNPO 2/6 / 3/6. By dataset: News 8/12 / 7/12, Books 6/12 / 4/12. Several "flips" are between a small positive and small negative delta and the three Books sycophancy ones share the same Target baseline.

## 14. Replicated truncated (H200) vs full prompt — the hardware-matched comparison
Per cell: `replicated_truncated_vs_fullprompt.tsv`; all three regimes side by side: `three_way_all_cells.tsv`.

| dataset | condition | category | original truncated Δ (A100) | replicated truncated Δ (H200) | full prompt Δ (H200) |
|---|---|---|---|---|---|
| MUSE-News | RMU | cross_domain | +1.00 | +3.50 | +1.00 |
| MUSE-News | WGA | cross_domain | +2.00 | +2.50 | +5.00 |
| MUSE-News | SatImp | cross_domain | -0.50 | -0.50 | +1.50 |
| MUSE-News | SimNPO | cross_domain | -1.50 | +0.50 | +3.50 |
| MUSE-News | RMU | sycophancy | +5.50 | +2.50 | +2.00 |
| MUSE-News | WGA | sycophancy | +0.50 | -2.50 | +0.50 |
| MUSE-News | SatImp | sycophancy | +4.50 | +2.50 | +3.00 |
| MUSE-News | SimNPO | sycophancy | +2.50 | +2.50 | +1.00 |
| MUSE-News | RMU | beneficial_memory_usage | -1.00 | -2.00 | -1.00 |
| MUSE-News | WGA | beneficial_memory_usage | +0.00 | -1.00 | +0.00 |
| MUSE-News | SatImp | beneficial_memory_usage | -1.00 | -1.00 | +0.00 |
| MUSE-News | SimNPO | beneficial_memory_usage | +0.00 | -1.00 | +1.00 |
| MUSE-Books | RMU | cross_domain | +13.50 | +13.50 | +18.00 |
| MUSE-Books | WGA | cross_domain | -2.00 | -0.50 | -2.50 |
| MUSE-Books | SatImp | cross_domain | -0.50 | +1.50 | -2.50 |
| MUSE-Books | SimNPO | cross_domain | +0.00 | +1.00 | -0.50 |
| MUSE-Books | RMU | sycophancy | +5.50 | +0.00 | +8.50 |
| MUSE-Books | WGA | sycophancy | -0.50 | -3.00 | +4.50 |
| MUSE-Books | SatImp | sycophancy | -1.00 | -2.50 | +2.50 |
| MUSE-Books | SimNPO | sycophancy | -0.50 | -3.50 | +2.50 |
| MUSE-Books | RMU | beneficial_memory_usage | +5.06 | +6.07 | +10.00 |
| MUSE-Books | WGA | beneficial_memory_usage | -1.00 | -1.00 | +0.00 |
| MUSE-Books | SatImp | beneficial_memory_usage | +1.00 | +1.00 | +0.00 |
| MUSE-Books | SimNPO | beneficial_memory_usage | +0.00 | +0.00 | +0.00 |

Prompt completeness changes **scenario-level outcomes**: the classification change rate (FR@3, same scenarios) is **8.95 %** replicated→full (358 / 4,000) and **8.90 %** original→full (356 / 4,000), against **4.95 %** original vs replicated truncated for the same Qwen settings (198 / 4,000, truncated-replication v2 analysis). Because the two truncated runs (different GPUs) each differ from the full prompt by the *same* ≈ 8.9 %, while differing from each other by only 4.95 %, the excess is attributable to the prompt rather than to the A100/H200 difference. Beneficial memory (1 generation): 1.2–1.3 % change, i.e. nearly unaffected. (Mean |Δ of delta| of 2.7 pp replicated→full vs 2.0 orig→full vs 1.4 orig→repl is in the same direction, but with 24 correlated comparisons I do not read the sign-agreement differences — 11 vs 14 vs 17 of 24 — as statistically established.)

## 15. SatImp (MUSE-News Qwen)
| | cross-domain Δ | sycophancy Δ | beneficial Δ |
|---|---|---|---|
| original truncated (A100) | −0.5 | **+4.5** | −1.0 |
| replicated truncated (H200) | −0.5 | **+2.5** | −1.0 |
| full prompt (H200) | **+1.5** | **+3.0** | 0.0 |

Paired Target→SatImp (S→F / F→S, p): sycophancy 17/8 (0.108) → 17/12 (0.458) → 14/8 (0.286); cross-domain 4/5 (1.0) → 3/4 (1.0) → 5/2 (0.45); beneficial 0/1, 1/2, 0/0 (1.0). **The larger sycophancy shift relative to cross-domain remains under the full prompt** (+3.0 vs +1.5 pp, a 1.5 pp gap, versus gaps of 5.0 pp and 3.0 pp in the original and replicated truncated runs): the direction is preserved in all three regimes, the magnitude (+2.5 to +4.5 pp) is attenuated relative to the original, and cross-domain moves slightly positive. None of these differences is statistically supported by the paired tests; I would describe SatImp as a *consistent, small, non-significant* sycophancy increase rather than an established effect. In Books, SatImp has no robust effect (cross-domain −0.5 / +1.5 / −2.5; sycophancy −1.0 / −2.5 / **+2.5**; beneficial +1.0 / +1.0 / 0.0; all p ≥ 0.12).

## 16. SimNPO
News: cross-domain −1.5 / +0.5 / **+3.5** pp (p = 0.375 / 1.0 / **0.039**), sycophancy +2.5 / +2.5 / +1.0 pp (p = 0.41 / 0.38 / 0.83), beneficial 0.0 / −1.0 / +1.0. Under the full prompt SimNPO's cross-domain shift is larger than its sycophancy shift, which is the *opposite* of the SatImp pattern; **SimNPO does not support the SatImp category-specific story** and remains at most a supporting comparison. Books: cross-domain 0.0 / +1.0 / −0.5, sycophancy −0.5 / −3.5 / **+2.5** (p = 0.30), beneficial 0 / 0 / 0.

## 17. RMU
RMU is the most reproducible and most robust method. Books: cross-domain +13.5 / +13.5 / **+18.0** pp (p < 0.0001, S→F 40 vs F→S 4), sycophancy +5.5 / 0.0 / **+8.5** (p = 0.0023), beneficial memory +5.1 / +6.1 / **+10.0** (p = 0.0063) — the full prompt *amplifies* RMU's effect on Books in all three categories. News: cross-domain +1.0 / +3.5 / +1.0 and sycophancy +5.5 / +2.5 / +2.0 pp, small, non-significant, and attenuating, with beneficial −1.0 / −2.0 / −1.0. RMU's behaviour is broad (all categories on Books) and is not the category-specific sycophancy story of SatImp.

## 18. WGA
WGA did not collapse on Qwen (100 % valid). News: cross-domain +2.0 / +2.5 / **+5.0** pp (full-prompt p = 0.0063, S→F 11 vs F→S 1; truncated p = 0.42 / 0.27), sycophancy +0.5 / −2.5 / +0.5 (≈ 0), beneficial 0.0 / −1.0 / 0.0. Books: cross-domain −2.0 / −0.5 / −2.5, sycophancy −0.5 / −3.0 / **+4.5** (p = 0.078), beneficial −1.0 / −1.0 / 0.0. The News WGA cross-domain increase is the only WGA effect that strengthens with the full prompt, but it is a single nominal hit among 24 tests; the other WGA patterns reverse sign or stay near zero. WGA is the least reproducible method across regimes (sign agreement 4/6 and 2/6).

## 19. Beneficial memory
Beneficial memory has one generation per scenario (FR@1 only). With a Target failure rate of 1 % on both datasets the metric sits near its floor, so only large effects can show. Full prompt: News — no condition differs by more than 1 pp (−1.0 to +1.0; no transition has more than 1 discordant pair). Books — **RMU +10.0 pp** (11 → 1 discordant, p = 0.0063; FR 1.0 % → 11.0 %), all other methods 0.0 pp. Compared with the truncated runs, beneficial memory changes little: News deltas ≈ 0 in all regimes; Books RMU +5.1 / +6.1 → +10.0 (amplified); scenario-level change only 1.2–1.3 %. So beneficial memory does **not** materially change under the full prompt except that the one existing effect (Books RMU) becomes larger.

## 20. Thesis implications — answers
**A. Does removing truncation materially change the broad Qwen conclusions?** For the *dominant* conclusions, no: RMU is the strongest and most robust method and becomes stronger; the Target baselines move by a few points; News unlearned conditions stay within +5 pp of Target. For *small* effects, yes in detail: 10 of 24 delta signs and 10 of 24 ±0.5 pp bands differ between original-truncated and full prompt (vs 7 and 10 between the two truncated runs), and scenario-level classification changes ≈ 1.8× more than under rerun alone. So broad method ranking is robust; individual small deltas are not.

**B. Which original effects are robust?** RMU's increases (Books cross-domain, sycophancy, beneficial memory; News small positive in both categories); the near-zero beneficial-memory results for all non-RMU methods; SatImp News sycophancy direction (+4.5 / +2.5 / +3.0).

**C. Which disappear or reverse?** Books sycophancy for WGA / SatImp / SimNPO (−0.5 to −3.5 → +2.5 to +4.5; non-significant either way and sharing one Target baseline), SimNPO News cross-domain (−1.5 → +3.5), SatImp Books cross-domain (+1.5 → −2.5), WGA News sycophancy (≈ 0 in the original and full prompt; −2.5 in the replication). Attenuated: RMU News sycophancy (+5.5 → +2.0), SatImp News sycophancy (+4.5 → +3.0).

**D. Does News SatImp still show a larger sycophancy than cross-domain shift?** Yes, restrainedly: +3.0 vs +1.5 pp at full prompt, with the same direction as in both truncated runs; not statistically significant.

**E. Does SimNPO still support that pattern?** No — at full prompt SimNPO's cross-domain shift (+3.5, nominal p = 0.039) exceeds its sycophancy shift (+1.0).

**F. What happens to RMU?** It is preserved and amplified on Books (+18.0 / +8.5 / +10.0 pp) and small but same-signed on News.

**G. What happens to WGA?** Its News cross-domain increase grows to +5.0 pp (nominal p = 0.0063); every other WGA cell stays within ±5 pp and mostly near zero or sign-unstable. No special treatment was applied.

**H. Are MUSE Books conclusions materially different?** Partly: the RMU conclusion is unchanged (stronger); the sycophancy conclusion for the other three methods shifts from "slightly negative / none" to "slightly positive", driven by both a lower Target baseline (9.0 vs 10.5 / 13.5) and higher unlearned values; none of these three is significant. Books beneficial and cross-domain results for WGA/SatImp/SimNPO stay ≈ 0.

**I. Does beneficial memory materially change?** No, apart from Books RMU growing from +5–6 to +10 pp (§19).

**J. Baseline vs unlearned models?** Both. Target FR (primary K) full vs original / replicated truncated: News cross-domain 1.5 vs 3.5 / 4.0, News sycophancy 12.5 vs 12.5 / 15.0, Books cross-domain 4.5 vs 4.5 / 3.5, Books sycophancy 9.0 vs 10.5 / 13.5, beneficial 1.0 vs 1.0 / 2.0 (News) and 1.0 vs 1.0 / 1.0 (Books). Unlearned models moved on average +0.5 / −1.2 (News CD), −1.6 / −2.1 (News syc), +0.4 / +0.2 (Books CD), **+2.1 / +2.2 (Books syc)**. News: shifts are similar for Target and unlearned models (a general level change). Books sycophancy: Target moves down (−1.5 / −4.5) while unlearned models move up (+2.1 / +2.2), so the delta increases from both sides.

**K. Should the thesis main Qwen tables now use full-prompt results?** Yes. The full prompt is the complete PersistBench protocol (the truncated runs removed ≈ 63 % of each prompt, including the whole persona/tool header), it is the only evaluation that covers all 30 Qwen cells in one hardware- and configuration-consistent suite, it is 99.99 % valid, and it avoids the Llama-2-inherited context limit for a model that does not need it.

**L. Should the truncated evaluation and its 26k replication move primarily to robustness/appendix?** Yes — as the robustness analysis showing which effects survive prompt completeness (RMU yes; small SatImp/SimNPO/WGA deltas only directionally) and quantifying run-to-run variability (7.3 % scenario-level change between truncated reruns; 8.9 % truncated→full).

## 21. Exact recommendation for Chapter 4
1. **Primary:** report the complete full-prompt MUSE-Qwen results (News and Books × five conditions × three categories, validity-aware FR@K with v2, paired transitions); state clearly that the prompt is untruncated (≈ 4.8–5.1 k tokens, `max_model_len 8192`), that Qwen's native sampling defaults from `generation_config.json` apply, and that the model alias is neutral.
2. **Robustness (appendix + short pointer):** the original truncated results (A100) and the independent truncated replication (H200, 26,000 generations) as evidence that large effects (RMU, MUSE-Books) are stable across prompt configuration and hardware, and that small deltas (≲ 3 pp) are within run-to-run and prompt-configuration variability.
3. **Secondary model comparison:** MUSE Llama-2 truncated results, with the 2,048-token context limitation (and 1,800-token left truncation) documented; do not present Llama-2 and Qwen full-prompt numbers as directly comparable evaluation conditions.
4. **Wording of mechanistic claims:** describe SatImp-on-News as a *consistent, small, non-significant* increase in sycophancy (+2.5 to +4.5 pp across three regimes), not as an established effect; do not describe SimNPO as an independent replication of SatImp; treat WGA effects as unstable; present RMU as the robust contrast. Any Chapter 4 statement that rests on a ≤ 3 pp delta, or on Books sycophancy for WGA/SatImp/SimNPO, should be rechecked against §11–§12 of this report (I have not read Chapter 4).
5. **Do not rewrite the thesis from this report automatically**; the tables above are in `frk_fullprompt_v2.tsv`, `target_unlearned_deltas.tsv`, `target_unlearned_transitions.tsv`, `truncated_vs_fullprompt.tsv`, `replicated_truncated_vs_fullprompt.tsv`.

## 22. Is further generation scientifically necessary?
No. The Qwen matrix is complete, valid and judged; the remaining uncertainty (small effects near the noise floor) cannot be resolved by more of the same single-run evaluation without changing the design (e.g. repeated runs), which is outside the stated scope. **Per the stop condition, no further generation, judging, replication, TOFU, Llama-2 full-prompt, temperature, token-limit or validity change was or will be launched.**

## Caveats
- Single run per cell: no run-to-run variance estimate exists for the full prompt itself; the truncated→truncated repeatability (4.95 % scenario-level change, Qwen) is the best available proxy.
- 24 comparisons between regimes share Target baselines and are therefore correlated; counts such as 14/24 or 11/24 are descriptive.
- Paired tests are uncorrected for multiplicity; only the Books-RMU results are strong.
- The original truncated Books judge used `--concurrency 3`; the new Books judge used default concurrency (§4).
- Job-log file names have a doubled `fpc_fpc_` prefix (cosmetic).

## Files
`fullprompt_manifest.tsv`, `generation_config.tsv`, `prompt_length_audit.tsv`, `generation_completeness.tsv`, `generation_validity_v2.tsv`, `frk_fullprompt_v2.tsv`, `target_unlearned_deltas.tsv`, `target_unlearned_transitions.tsv`, `truncated_vs_fullprompt.tsv`, `replicated_truncated_vs_fullprompt.tsv`, `three_way_all_cells.tsv`, `scenario_level_change_vs_fullprompt.tsv`, `fullprompt_summary_v2.json`, `checkpoint_verification.tsv`, `dataset_identity_prelaunch.tsv`, `existing_artifact_audit.tsv`, `missing_scope.tsv`, `prompt_samples.md`, `analysis_fullprompt_stdout.log`, `scripts/` (audit, launcher copy references in `thesis/scripts/persistbench_fullprompt_complete/`).
