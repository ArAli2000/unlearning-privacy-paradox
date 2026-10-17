# Truncated PersistBench replication (MUSE) — report

Experiment: repeat the ORIGINAL 2048-context / 1800-token left-truncation MUSE PersistBench evaluation under the same configuration and measure how repeatable the behavioural results are.
4 settings × 5 conditions × 1,300 generations = **26,000 generations, all generated and judged**. Original outputs were not touched. The thesis was not edited. No further experiment was launched.
Interpretation rules were written to `decision_rules.md` **before any replication output existed** (timestamp inside).
Primary metric: validity-aware FR@K with the **unmodified v1 classifier**, as instructed. FR@3 (FR@1 for beneficial memory), Δ = FR(unlearned) − FR(Target) within the same run, in pp.

---

## 1. Executive verdict

**Partially replicated: the qualitative picture holds, the individual effect sizes are noisy.**

- **Direction of Target→Unlearned deltas:** 35 of 45 preserved (78%). On the two main categories alone (cross-domain + sycophancy, 30 comparisons) 24 are preserved (80%). 6 comparisons flip sign outright. All are small effects (≤3 pp).
- **Run-to-run noise is large relative to most effects.** FR@3 differs between the two runs by a median 0.8 pp (mean 1.4, max 6.0 pp). The Target condition alone, with no treatment involved, moved by up to 3.0 pp. Most single-run deltas of 2–5 pp therefore cannot be reliably distinguished from repeat noise.
- **What reproduced clearly:** RMU's broad increases (direction preserved in 11 of 12 comparisons, 0 flips). Books-Qwen RMU cross-domain is statistically significant in both runs (28–32 vs 1–5 discordant scenarios). Llama-2 sycophancy is positive for every unlearned condition in both runs. The Books Llama-2 WGA collapse reproduced exactly.
- **What did not reproduce:** the News-Llama-2 cross-domain SimNPO effect (+9.5 → +0.5 pp), Books-Qwen RMU sycophancy (+5.5 → 0.0), and the claim that SimNPO/SatImp *improve* cross-domain on News-Qwen (SimNPO −1.5 → +0.5).
- **SatImp (primary mechanistic case):** classified **A (strong replication)** by the pre-registered rule, but by a thin margin and without statistical significance in either run (§10).
- **Important confound:** the replication ran on **H200 NVL**, the originals on **A100 80 GB**. Only 38% of generations are byte-identical. The divergence pattern is consistent with floating-point non-determinism (§8). This experiment cannot separate "different hardware" from "same-hardware rerun".

---

## 2. Job summary

| Setting | SLURM job | GPU | State | Elapsed | Output path |
|---|---|---|---|---|---|
| A MUSE-News Qwen2.5-7B | 466261 | NVIDIA H200 NVL 143,771 MiB (`lenny`) | COMPLETED 0:0 | 02:20:58 | `external/PersistBench/outputs/truncated_replication_20261016/muse_news_qwen25/` |
| B MUSE-Books Qwen2.5-7B | 466262 | H200 NVL (`nelson`) | COMPLETED 0:0 | 01:51:34 | `…/muse_books_qwen25/` |
| C MUSE-News Llama-2-7B | 466263 | H200 NVL (`nelson`) | COMPLETED 0:0 | 02:20:10 | `…/muse_news_llama2/` |
| D MUSE-Books Llama-2-7B | 466264 | H200 NVL (`lenny`) | COMPLETED 0:0 | 02:20:02 | `…/muse_books_llama2/` |

Each job: 5 conditions generated, completeness gate, then judging with the primary Qwen2.5-7B judge. Details in `job_summary.tsv`.

**GPU history.** The jobs were first submitted for A100-class `a180` (466257–466260) and sat pending on priority. They were cancelled before any output existed, and resubmitted on the highest-end GPU available (H200 NVL), at your instruction. Host RAM was requested at 48 GB instead of 180 GB because the H200 nodes lacked 180 GB free; this does not affect results.

---

## 3. Configuration verification (original vs replication)

All checks were automated from primary evidence: original output metadata, the original vLLM logs, the canonical manifests, and the replication logs (`configuration_audit.tsv`, `replication_config_verification.tsv`, `dataset_identity.tsv`, `truncation_check.tsv`).

| Parameter | Original | Replication | Same? |
|---|---|---|---|
| temperature / max new tokens | 0.0 / 96 | 0.0 / 96 | yes |
| max_model_len | 2048 | 2048 | yes |
| truncate_prompt_tokens, side | 1800, left | 1800, left | yes |
| chat template | `templates/simple_llama_chat_template.jinja` | same file, same sha | yes |
| generations 3/3/1, scenarios 200/200/100 | yes | yes | yes |
| Qwen effective defaults | rep 1.05, top_p 0.8, top_k 20 (server override line) | identical override line | yes (1.05, not 1.08) |
| Llama-2 effective defaults | no override line (vLLM defaults; checkpoint generation_config has no sampling keys) | no override line | yes (inherited, nothing guessed) |
| served model name, dtype, GPU mem util | per-condition label, bf16, 0.90 | identical | yes |
| vLLM / torch / transformers | 0.23.0 / 2.11.0 / 5.12.1 (installed 2026-06-23) | same environment | yes |
| 20 checkpoint paths, tokenizers | manifests | same manifests; path == original log path for all 20 | yes |
| Scenario IDs (md5 of memories+query), order | benchmark input | identical set and order for 60 setting×condition×category checks | yes |
| Judge | Qwen2.5-7B-Instruct as `local-judge`, 0.85 mem, 32768 ctx, eager, guided JSON, T=0, 256 tokens | same flags; Books-Qwen `--concurrency 3` as originally | yes |
| **GPU** | **A100 80 GB (`a180`: penelope/rubeus)** | **H200 NVL 141 GB** | **NO, unavoidable** |
| KV-cache size | e.g. 1.04 M tokens | 2.04 M tokens | consequence of GPU |

Runtime confirmation on all 20 live servers: the truncation probe returned **prompt_tokens = 1800 for all three categories**, so truncation was active. Offline, all 2,000 prompts (500 × 4 settings) exceed 1,800 tokens (raw range 4,762–6,065), all memories and the query survive in the retained window, and the persona header with the alias never does.

**Differences, all disclosed:**
1. **GPU:** H200 NVL vs A100 80 GB. This is not a hardware-controlled replication.
2. **Isolated PersistBench code copy.** The live `utils.py` gained a `STRICT_GENERATION_CONTROL` block on 2026-07-21 (after the originals) that would force `repetition_penalty=1.08`, `top_p=1.0` and inject a system prompt. Replication used a copy at the generation-time state (`CODE_PROVENANCE.txt`; every other file byte-identical to live; the only diff is that block). This difference is necessary to *reproduce* the original.
3. Three one-token probe requests per condition (never stored as data), and judging inside the same SLURM job.
4. The Llama-2 tokenizer-only snapshot directory (`NousResearch/Llama-2-7b-hf`) was touched on 2026-07-17, after the originals; I could not verify that the tokenizer files are byte-identical to July. Weights and sampling defaults come from the MUSE checkpoints, so I expect no effect.

---

## 4. Completeness

- 20/20 files complete and judged, **26,000/26,000 generations** (`completeness.tsv`).
- 500 scenarios per file in the benchmark order, no duplicate entries; 3/3/1 generations per scenario; **0 API errors, 0 empty responses, 0 unjudged generations**.
- No condition was regenerated after a failure; no failure occurred.

---

## 5. Validity (`validity.tsv`)

- Mean absolute validity difference between original and replication: **0.07 pp**, max 1.0 pp.
- All Qwen conditions ≥ 99.5% valid except Books-Qwen RMU beneficial memory (98.0%, identical to the original).
- **MUSE-Books Llama-2 WGA: 0 of 1,300 valid in both runs** (collapse 600/600/100).
- Other Llama-2 invalids are real collapses: D RMU sycophancy 98.0% (11 collapsed), SimNPO cross-domain 97.5% (12 collapse + 3 web), SatImp cross-domain 98.5%.
- Zero-valid scenarios for Books Llama-2 WGA: 200/200 at every K.

Note: v1 has the known false-positive problem on "sign in" substrings and the single-token repetition rule only (see `thesis/analysis/final_validity_audit/REPORT.md`). It was used unchanged as instructed. Those flaws affect original and replication identically.

---

## 6. Original vs replication FR@3 (K=3; N shown when ≠200)

| Setting | Category | Cond | Orig | Repl | |diff| | Δ orig | Δ repl | Dir kept |
|---|---|---|---|---|---|---|---|---|
| A News-Qwen | cross | Target | 3.50 | 4.00 | 0.5 | ref | ref | |
| | | RMU | 4.50 | 7.50 | 3.0 | +1.0 | +3.5 | yes |
| | | WGA | 5.50 | 6.50 | 1.0 | +2.0 | +2.5 | yes |
| | | SatImp | 3.00 | 3.50 | 0.5 | −0.5 | −0.5 | yes |
| | | SimNPO | 2.00 | 4.50 | 2.5 | −1.5 | +0.5 | **no** |
| | syc | Target | 12.50 | 15.00 | 2.5 | ref | ref | |
| | | RMU | 18.09 (199) | 17.50 | 0.6 | +5.6 | +2.5 | yes |
| | | WGA | 13.00 | 12.50 | 0.5 | +0.5 | −2.5 | **no** |
| | | SatImp | 17.00 | 17.50 | 0.5 | +4.5 | +2.5 | yes |
| | | SimNPO | 15.00 | 17.50 | 2.5 | +2.5 | +2.5 | yes |
| B Books-Qwen | cross | Target | 4.50 | 3.50 | 1.0 | ref | ref | |
| | | RMU | 18.00 | 17.00 | 1.0 | +13.5 | +13.5 | yes |
| | | WGA | 2.50 | 3.00 | 0.5 | −2.0 | −0.5 | yes |
| | | SatImp | 4.00 | 5.00 | 1.0 | −0.5 | +1.5 | **no** |
| | | SimNPO | 4.50 | 4.50 | 0.0 | 0.0 | +1.0 | no |
| | syc | Target | 10.50 | 13.50 | 3.0 | ref | ref | |
| | | RMU | 16.00 | 13.50 | 2.5 | +5.5 | 0.0 | no |
| | | WGA | 10.00 | 10.50 | 0.5 | −0.5 | −3.0 | yes |
| | | SatImp | 9.50 | 11.00 | 1.5 | −1.0 | −2.5 | yes |
| | | SimNPO | 10.00 | 10.00 | 0.0 | −0.5 | −3.5 | yes |
| C News-Llama2 | cross | Target | 7.00 | 10.00 | 3.0 | ref | ref | |
| | | RMU | 9.50 | 15.00 | 5.5 | +2.5 | +5.0 | yes |
| | | WGA | 10.00 | 9.00 | 1.0 | +3.0 | −1.0 | **no** |
| | | SatImp | 14.00 | 13.50 | 0.5 | +7.0 | +3.5 | yes |
| | | SimNPO | 16.50 | 10.50 | 6.0 | +9.5 | +0.5 | yes (+0.5 sits exactly at the tolerance edge; effectively vanished) |
| | syc | Target | 11.00 | 12.00 | 1.0 | ref | ref | |
| | | RMU | 20.00 | 18.50 | 1.5 | +9.0 | +6.5 | yes |
| | | WGA | 17.00 | 16.50 | 0.5 | +6.0 | +4.5 | yes |
| | | SatImp | 19.00 | 17.00 | 2.0 | +8.0 | +5.0 | yes |
| | | SimNPO | 15.50 | 19.00 | 3.5 | +4.5 | +7.0 | yes |
| D Books-Llama2 | cross | Target | 31.50 | 30.00 | 1.5 | ref | ref | |
| | | RMU | 44.00 | 43.50 | 0.5 | +12.5 | +13.5 | yes |
| | | WGA | NA (N=0) | NA (N=0) | | | | collapse reproduced |
| | | SatImp | 29.15 (199) | 29.44 (197) | 0.3 | −2.4 | −0.6 | yes |
| | | SimNPO | 36.22 (196) | 35.90 (195) | 0.3 | +4.7 | +5.9 | yes |
| | syc | Target | 27.64 (199) | 30.65 (199) | 3.0 | ref | ref | |
| | | RMU | 37.88 (198) | 37.06 (197) | 0.8 | +10.2 | +6.4 | yes |
| | | WGA | NA (N=0) | NA (N=0) | | | | collapse reproduced |
| | | SatImp | 31.50 | 32.00 | 0.5 | +3.9 | +1.4 | yes |
| | | SimNPO | 40.00 | 40.70 (199) | 0.7 | +12.4 | +10.1 | yes |

Beneficial memory (K=1, N=100) is in `original_vs_replication_frk.tsv`: sign kept in 11 of 15, mean |diff| 1.5 pp, small single-digit-percent rates.

---

## 7. Replication deltas vs Target

| Subset | Comparisons | Sign preserved (±0.5 pp band) | Outright flips | Mean / median / max \|FR@3 diff\| (pp) |
|---|---|---|---|---|
| **All** | 45 | **0.78** | 6 | 1.43 / 0.82 / 6.0 |
| Qwen | 24 | 0.71 | 3 | 0.84 / 0.50 / 3.0 |
| Llama-2 | 21 | 0.86 | 3 | 2.11 / 1.00 / 6.0 |
| MUSE-News | 24 | 0.71 | 5 | 2.07 / 1.00 / 6.0 |
| MUSE-Books | 21 | 0.86 | 1 | 0.71 / 0.50 / 2.5 |
| cross-domain | 15 | 0.73 | 3 | 1.57 / 1.00 / 6.0 |
| sycophancy | 15 | 0.87 | 1 | 1.21 / 0.70 / 3.5 |
| beneficial memory | 15 | 0.73 | 2 | 1.51 / 1.00 / 6.0 |
| by condition: RMU / SatImp / SimNPO / WGA | 12 / 12 / 12 / 9 | **0.92** / 0.83 / 0.75 / 0.56 | 0 / 2 / 1 / 3 | |

Strict exact-zero tolerance gives the same 0.78. Full breakdown: `replication_summary.json`.

**Noise calibration:** Target-only |orig − repl| at FR@3 for cross-domain/sycophancy ranges 0.5–3.0 pp (sorted: 0.5, 1.0, 1.0, 1.5, 2.5, 3.0, 3.0, 3.02). Target sycophancy FR@3 rose in **all four** replications (+2.5, +3.0, +1.0, +3.0 pp). That is suggestive of a small systematic shift (probability 1/8 under a symmetric coin flip), not proof. Because every Δ is measured against Target, a higher replicated Target reference shrinks most sycophancy deltas: e.g. SatImp's own FR@3 barely moved (17.0 → 17.5) while Δ fell from +4.5 to +2.5.

---

## 8. Scenario-level repeatability

Original vs replication classification (SAFE/FAILURE at K=3, validity-aware), same scenario IDs (`original_replication_transitions.tsv`):

| Group | Scenario classifications compared | Changed (S↔F) | Rate | Byte-identical generations |
|---|---|---|---|---|
| **Overall** | 9,481 | 703 | **7.4%** | **38.0%** |
| Qwen | 4,997 | 209 | 4.2% | 28.0% |
| Llama-2 | 4,484 | 494 | 11.0% | 48.1% |
| MUSE-News | 4,999 | 351 | 7.0% | 34.9% |
| MUSE-Books | 4,482 | 352 | 7.9% | 41.1% |
| cross-domain / sycophancy / beneficial | | | 7.1% / 7.5% / 7.8% | |

**Why only 38% identical text under greedy decoding?** I checked where the texts diverge (`scripts/diagnose_divergence.py`). A systematic prompt or sampling difference would split them in the first tokens, but only 9% diverge within 10 characters. The median first differing character is ≈133, and 59% diverge after character 100. This matches floating-point non-determinism compounding over ~96 tokens (different GPU architecture and kernels), not a configuration difference. Supporting evidence: Books Llama-2 WGA's deterministic collapsed output is **100% byte-identical**, so the pipeline is exact wherever the model itself is deterministic. I cannot distinguish "A100 vs H200" from "any rerun" here (no same-hardware rerun exists, and the hard-stop rule forbids one), so treat these as cross-hardware repeatability figures.

---

## 9. MUSE-News Qwen three-way (FR@3, %; `muse_news_qwen_three_way.tsv`)

Full-prompt values read from the stored `analysis_results.json` artifacts (validity-aware; N=199 for SatImp/SimNPO cross-domain and SatImp sycophancy).

| Category | Condition | Original truncated | Replicated truncated | Full prompt |
|---|---|---|---|---|
| cross-domain | Target | 3.50 | 4.00 | 1.50 |
| | RMU | 4.50 | 7.50 | 2.50 |
| | WGA | 5.50 | 6.50 | not run |
| | SatImp | 3.00 | 3.50 | 3.02 |
| | SimNPO | 2.00 | 4.50 | 5.03 |
| sycophancy | Target | 12.50 | 15.00 | 12.50 |
| | RMU | 18.09 | 17.50 | 14.50 |
| | WGA | 13.00 | 12.50 | not run |
| | SatImp | 17.00 | 17.50 | 15.58 |
| | SimNPO | 15.00 | 17.50 | 13.50 |

| Δ vs Target (pp) | Original | Replication | Full prompt |
|---|---|---|---|
| cross · RMU | +1.0 | +3.5 | +1.0 |
| cross · WGA | +2.0 | +2.5 | not run |
| cross · SatImp | −0.5 | −0.5 | +1.5 |
| cross · SimNPO | −1.5 | +0.5 | +3.5 |
| syc · RMU | +5.6 | +2.5 | +2.0 |
| syc · WGA | +0.5 | −2.5 | not run |
| syc · SatImp | +4.5 | +2.5 | +3.1 |
| syc · SimNPO | +2.5 | +2.5 | +1.0 |

All sycophancy deltas for RMU, SatImp and SimNPO are positive in all three runs. The difference between original-truncated and full-prompt deltas (e.g. SatImp sycophancy +4.5 vs +3.1) is smaller than the difference between two truncated runs of the same configuration (+4.5 vs +2.5). The full-prompt "robustness" check therefore cannot be told apart from repeat noise, and its qualitative reading stands.

---

## 10. SatImp verdict (rule fixed in `decision_rules.md`)

| MUSE-News Qwen, K=3 | cross-domain Δ | sycophancy Δ |
|---|---|---|
| Original | −0.5 | +4.5 |
| Replication | −0.5 | +2.5 (K=1/2/3: +3.0 / +2.5 / +2.5) |
| Full prompt | +1.5 | +3.1 |

Rule: A requires ds_r ≥ 1.0, ds_r > dc_r, sign agreement with the original, and ratio ds_r/ds_o ∈ [0.5, 2.0]. Here ds_r = 2.5 > dc_r = −0.5, ratio = 0.56. **Verdict: A (strong replication) by the rule.**

Caveats that matter more than the letter:
- The ratio 0.56 is just above the 0.5 bound; the effect shrank by about 45%.
- **Not statistically significant in either run:** original S→F 17 / F→S 8 (p = 0.108); replication 17 / 12 (p = 0.458). The "replication" is a consistent sign and a modest magnitude, not a confirmed effect.
- SatImp's sycophancy FR itself was stable (17.0 → 17.5). The smaller Δ is mostly the higher Target reference (§7).
- In the replication RMU and SimNPO have the same +2.5 pp sycophancy shift, so SatImp is not distinguished from them by magnitude. It is distinguished by cross-domain staying flat (−0.5) while RMU's rises (+3.5).

---

## 11. SimNPO verdict (kept separate from SatImp)

- **Reproduces:** sycophancy increases. News-Qwen +2.5 → +2.5; Books-Llama-2 +12.4 → +10.1 (significant in both runs, p = 0.006 → 0.030); News-Llama-2 +4.5 → +7.0 (replication-only significance, p = 0.049, original 0.176).
- **Does not reproduce:** cross-domain effects. News-Qwen −1.5 → +0.5 (sign flip). News-Llama-2 +9.5 → +0.5 (original significant, p = 0.0026 → replication p = 1.0).
- Books-Qwen: sycophancy −0.5 → −3.5 (same direction, larger); cross-domain 0.0 → +1.0 (stable).
- **Reading:** SimNPO's sycophancy pattern is repeatable, but its cross-domain pattern is not. Its original "improves cross-domain on News-Qwen" should not be claimed.

## 12. RMU verdict

- RMU is the most repeatable: direction preserved in **11 of 12 comparisons, 0 flips, mean |FR@3 diff| 1.9 pp**.
- Books-Qwen cross-domain RMU **+13.5 → +13.5** (28–32 discordant scenarios vs 1–5), significant in both runs. Books-Llama-2 cross-domain +12.5 → +13.5, significant in both runs.
- News-Llama-2 sycophancy +9.0 → +6.5, significant in both runs (p = 0.006 → 0.047).
- Weaker or non-reproducing: News-Qwen sycophancy +5.6 → +2.5 (p = 0.071 → 0.487), Books-Qwen sycophancy +5.5 → 0.0 (p = 0.061 → 1.0), Books-Llama-2 sycophancy +10.2 → +6.4 (p = 0.021 → 0.154).
- **RMU remains a useful contrast.** The broad cross-category degradation is real on Books; the News-Qwen sycophancy increase is directionally stable but small.

---

## 13. Llama-2

- **Books-Llama-2 WGA collapse reproduced exactly:** 0 of 1,300 valid in both runs, every generation identical to the original (100% byte-identical, a single dash string), zero-valid scenarios 200/200. The original collapse is repeatable; WGA remains non-evaluable.
- Llama-2 shows larger absolute repeat noise than Qwen (mean |diff| 2.1 vs 0.8 pp) and more scenario-level change (11.0% vs 4.2%), driven by News-Llama-2 (mean |diff| 3.1 pp, max 6.0). Books-Llama-2 is stable (9 comparisons, 0 flips, sign kept 9/9).
- News-Llama-2 is Track A, the superseded setting; it was not used in the main thesis results. I would treat its large cross-domain discrepancies as a data-quality note, not a finding.
- These are secondary model-family comparisons and are not elevated to primary evidence.

---

## 14. Statistical tests

Exact two-sided paired sign tests (Target vs unlearned, K=3, discordant scenarios) are in `target_unlearned_transitions.tsv`. There are 32 tests per run, uncorrected. About 1.6 false positives per run are expected at α = 0.05.

| Result | Count | Which |
|---|---|---|
| Significant in **both** runs | 4 | Books-Qwen RMU cross-domain (32/5 → 28/1); News-Llama-2 RMU sycophancy (18 → 13 net, p 0.006 → 0.047); Books-Llama-2 RMU cross-domain (p 0.003 → 0.002); Books-Llama-2 SimNPO sycophancy (p 0.006 → 0.030) |
| Significant in original only | 5 | all Llama-2: News cross SatImp, cross SimNPO, sycophancy SatImp, sycophancy WGA; Books sycophancy RMU |
| Significant in replication only | 1 | News-Llama-2 sycophancy SimNPO (p = 0.049) |
| MUSE-News Qwen | 0 of 8 significant in either run | closest: RMU sycophancy p = 0.071 (orig) / 0.487 (repl) |

Original had 9 significant of 32; replication had 5 of 32. Only 4 of the 9 original significant results reproduce (and 1 new one appears), so significance in a single run should not be treated as repeatable; only the largest effects were. All the MUSE-News-Qwen effects used for the SatImp case are non-significant in both runs. Discordant counts are in the file next to every p value.

---

## 15. Thesis impact

- **Chapter 4 broad findings:** still supported at the level of direction for RMU (strongest, Books especially), for sycophancy increases under RMU/SatImp/SimNPO on News-Qwen, and for Llama-2. They are **not** supported as precise effect sizes. Treat deltas below ≈3 pp as within repeat noise.
- **Claims that should be softened:** "SatImp/SimNPO improve cross-domain on MUSE-News Qwen" (replication: SatImp −0.5 stable, SimNPO +0.5). The News-Llama-2 SimNPO cross-domain effect (original +9.5, p=0.003) did not repeat.
- **SatImp as main mechanistic case:** still justified under the pre-registered rule (A), but describe it as a *selected, consistent-sign, modest, non-significant* case, not a population effect. Its magnitude is not unique among RMU/SimNPO in the replication.
- **SimNPO:** remains supporting only. Its sycophancy pattern is repeatable, its cross-domain pattern is not.
- **RMU:** remains a useful contrast, and is the most repeatable condition.
- **Full-prompt robustness interpretation:** unchanged. The truncated-vs-full-prompt differences are smaller than the original-vs-replication differences of the *same* configuration.
- **Result tables:** no table needs replacement; the original run is one valid realisation. I recommend adding the replication as an appendix/robustness table and attaching a repeat-noise statement (≈ ±3 pp) wherever single-run deltas are quoted.
- **Another generation experiment:** not scientifically necessary for the thesis claims. The one open question (A100 vs H200 vs generic non-determinism) cannot be answered without a same-hardware rerun, which the hard-stop rule excludes; it should be stated as a limitation.

---

## 16. Thesis-ready paragraph (Chapter 4 robustness section or Appendix)

> To assess repeatability, the original truncated MUSE PersistBench evaluation (2048 context, left truncation to 1800 tokens, greedy decoding, 96 new tokens) was repeated once for all four MUSE settings and five conditions (26,000 generations), with identical checkpoints, scenarios, templates, server flags and judge. The only unavoidable difference was the GPU (H200 NVL instead of A100 80 GB); only 38% of generations were byte-identical, with divergence typically appearing mid-generation. The Target-to-unlearned direction was preserved in 78% of 45 comparisons (24 of 30 for cross-domain and sycophancy), with a median absolute FR@3 difference of 0.8 pp and a maximum of 6 pp; 7.4% of scenario classifications changed between runs. RMU's broad increases reproduced most consistently, and the Books Llama-2 WGA generation collapse reproduced exactly. The MUSE-News Qwen sycophancy increase for SatImp reproduced in sign (+4.5 → +2.5 pp) but was not significant in either run, and the cross-domain "improvements" for SatImp and SimNPO did not reproduce. We therefore interpret effects below about 3 pp as indistinguishable from run-to-run variation, and base our conclusions on direction and on effects that are large and repeated.

---

## Files

`configuration_audit.tsv`, `replication_config_verification.tsv`, `dataset_identity.tsv`, `truncation_check.tsv`, `CODE_PROVENANCE.txt`, `job_summary.tsv`, `completeness.tsv`, `original_verified_frk.tsv` (45/45 shared cells identical to the earlier appendix table), `replication_frk.tsv`, `original_vs_replication_frk.tsv`, `validity.tsv`, `target_unlearned_transitions.tsv`, `original_replication_transitions.tsv`, `muse_news_qwen_three_way.tsv`, `replication_summary.json`, `decision_rules.md`, `scripts/` (launcher, analysis, checks, diagnostics).
