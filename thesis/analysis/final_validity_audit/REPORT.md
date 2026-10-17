# Final validity audit — PersistBench FR@K and the generation-validity gate

Scope: existing artifacts only. No generation, judging, training, unlearning, SLURM job or mechanistic experiment was run, and no existing file was modified.
New files only: this directory, plus `thesis/scripts/validation/create_persistbench_validity_summary_v2.py`. The original classifier is untouched.
Rebuild everything with `scripts/run_all.sh` (read-only on `external/PersistBench/outputs*`).

Audited population: **43,800 generations** = 25 final conditions × 1,300 (32,500) + 8 full-prompt robustness runs (4,800) + MUSE-News Llama-2 (6,500; only part of the 24-condition paradox scan, not of the 25-condition FR@K tables).

---

## 1. Executive conclusion

1. **Recommended canonical procedure: C, validity-aware FR@K with the corrected validator v2.** Not A (official), not B (v1).
2. **The v1 gate has a systematic false-positive defect, so v2 is necessary.** 97 of the 106 non-collapse "web contamination" flags are ordinary, coherent answers (91.5%). The causes are substring matching ("sign in" inside "de**sign in**dustry") and treating `github` / `repository` / `pull requests` as evidence by themselves. After the fix, v2 has 0 false positives on the 137 manually audited responses and keeps 38 of the 40 genuinely invalid ones.
3. **No thesis conclusion changes under any of the three procedures.** Across 168 non-WGA cell×K values the three procedures differ by at most 0.94 pp. There are no significance changes, and no direction changes beyond two ±0.5 pp threshold-edge artifacts (n.s. everywhere). Every headline claim I could check holds under all of them (§9).
4. **Official FR@K cannot be canonical.** It contradicts the thesis methodology: it scores 1,300 identical dash strings from MUSE-Books Llama-2 WGA and reports FR@3 of 10.00% (cross-domain) and 43.00% (sycophancy) for a condition whose model produced no answer at all.
5. **Two things are not decided by this audit and need your call (§5, §12):**
   - v1 also *under*-detects collapse: looping outputs it calls valid, concentrated in Llama-2 (`v2r` sensitivity below).
   - The thesis's own "7 of 16" paradox count becomes **8 of 16** under v2, from a single ±0.1 pp sign flip.
6. **No new experiment is required.**

---

## 2. Official vs validity-aware discrepancy

**Which artifacts use which variant** (from the stored provenance of `appendix_material/tables/persistbench_frk_complete.tsv`):

| Variant | Artifacts |
|---|---|
| **Official FR@K** (upstream `failure_rates.py`; any non-null score counts) | `presentation_figures_final/persistbench_all_methods_all_corpora.csv` (and the copy in `thesis_defense_assets_bundle/data/`): MUSE-News Qwen, MUSE-Books Qwen, TOFU Qwen. `thesis/analysis/judge_robustness/qwen_vs_gemma_frk.json`: all MUSE tracks, both judges, including Books Llama-2. The official rows of the appendix FR@K table. `MASTER_THESIS_MAP.md` §5 defines FR@K as the official one. |
| **Validity-aware v1** | `mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_category_comparison_validated.csv` ("validated-clean" view, MUSE-News Qwen). `mechanistic/outputs/muse_books_weekly_update_analysis/persistbench_fr_at_k.csv` (Books Qwen). Full-prompt `analysis_results.json` (FR@3, transitions, sign p). Appendix `generation_validity_complete.tsv`, `fullprompt_robustness.tsv` and the validity-aware agreement row. `mechanistic/analyze_benchmark_paradox.py` carries its **own verbatim copy** of the v1 `classify`, so all strict/broad/validity-% numbers and quadrant labels in `mechanistic/outputs/benchmark_paradox/` are v1-gated too. |
| **Neither stored** | There is no stored validity-aware FR@K for TOFU (either model) or Books Llama-2; those validity-aware rows exist only as recomputations in the appendix tables. |

So one thesis chapter currently mixes variants, and the methodology sentence "invalid generations are removed before behavioural interpretation" is false for every table in the first row.

**The 29 of 75 cells** (`frk_official_vs_validity_v1.tsv`, column "cell in differing set"): a (dataset, model, condition, category) cell counts as differing if any K has a different FR value (27 cells) or only a different N (2 cells).

| Dataset / model | Differing cells |
|---|---|
| MUSE-Books Llama-2 | 11 (3 of them WGA) |
| TOFU Qwen2.5-7B | 8 |
| TOFU Llama-3.1-8B | 7 |
| MUSE-Books Qwen2.5-7B | 2 |
| MUSE-News Qwen2.5-7B | 1 (RMU sycophancy: 18.09 vs 18.00 at K=3) |

By condition: RMU 8, WGA 7, SimNPO 6, SatImp 4, Target 4. The largest single FR difference is 0.88 pp. Most differences are denominator effects (one or two scenarios dropped).

---

## 3. Invalid generation counts

| | v1 | v2 |
|---|---|---|
| 25 conditions (32,500 gens) | 1,428 invalid | 1,338 |
| – of which MUSE-Books Llama-2 WGA (total collapse) | 1,300 | 1,300 |
| – all other 24 conditions (31,200 gens) | **128 (0.41%)** | **38 (0.12%)** |
| 8 full-prompt runs (4,800 gens) | 9 | 0 |
| MUSE-News Llama-2 (6,500 gens) | 0 | 0 |
| zero-valid scenarios, 25 conditions | 520 (500 WGA + 20) | 512 (500 WGA + 12) |

**Class A, total collapse (`invalid_generations_v1.tsv`, class column).** WGA on Books Llama-2: 1,300 of 1,300 generations are *one single string* (a dash loop), flagged by the alpha-ratio rule. The judge nonetheless assigned a spread of scores to this identical string (1: 882, 4: 192, 5: 107, 0: 60, 2: 47, 3: 12), which is why official FR@K produces numbers for it. It is summarised, not individually inspected.

**Class B, everything else (137 responses).** v1 labels 106 as web/page contamination, 30 as collapse and 1 as tool/schema.
By condition, v1 invalid counts are:
- TOFU: 81, all web flags.
- MUSE-Books Llama-2: 37 (RMU 12, SimNPO 18, Target 4, SatImp 3).
- MUSE-Books Qwen: 7.
- MUSE-News Qwen: 3, all RMU.
- Full-prompt: 9.

---

## 4. False-positive analysis

Blind manual audit (`invalid_manual_audit.tsv`). The 137 responses were shuffled behind anonymous IDs so decisions rest on text only. For 8 borderline cases I additionally read the query. The key linking IDs to conditions is `invalid_manual_audit_key.tsv`, which was opened only after decisions were frozen (`scripts/manual_labels.json`).

| | n |
|---|---|
| Truly invalid | **40**: 30 labelled collapse, 9 labelled web (4 genuine page/UI chrome, 3 looping dialogue that is collapse not web, 2 borderline off-task tool-list loop), 1 tool-call JSON. **7 of the 40 are borderline** |
| **False positives (coherent, interpretable answers)** | **97**, all labelled web: |
| – "sign in" matched only as a substring | 46 |
| – github / repository / pull requests only | 47 (repository 33, github 19, pull requests 8; some responses contain several terms) |
| – both mechanisms in one response | 1 |
| – tool-wrapped deliverables ("to=bio" + code/JSON block), kept valid but borderline | 3 (two via `repository`, one via a substring "sign in") |

- 97 of 106 web flags (91.5%) and 97 of 137 non-collapse flags (70.8%) are false positives.
- 88 of the 97 are in the 25 main conditions (TOFU 81, Books-Qwen 4, News-Qwen 3). The other 9 are in the full-prompt runs.
- **Every whole-word "sign in" match (7 of 7) was genuine.** Every genuine web-chrome case is caught by whole-phrase matching.

**Why "design industry" triggers "sign in".** v1 tests `"sign in" in text.lower()` with no word boundaries. "design industry" is `de` + `sign in` + `dustry`: a word ending in *-sign* followed by a word starting with *in-*. This fires on "design industry", "design inspired", "design intuitive", "design in the …", "assign in …". 48 of the 55 "sign in" flags are of this kind.

**`github`, `repository`, `pull requests`** are used as standalone evidence. They occur in coherent software answers (SOPs, CI/CD, code review) and in non-software ones ("a repository of knowledge": Library of Alexandria, Great Pyramid, museum archives). Of the 64 flag attributions to these terms (github 21, repository 35, pull requests 8), only 2 fall in genuinely invalid responses: the `github` hits inside a looping tool list (borderline, A036/A042).

Per-rule counts, unique outputs, false-positive mechanisms and recommendations are in `validator_rules_audit.tsv`. Notable results:
- 22 of the rules never fire in the thesis data (all empty-JSON rules, 6 of the 10 web terms, 3 of the 5 tool terms, all 10 gibberish tokens, `len<30`).
- `));` is a latent risk on code-heavy answers (0 hits observed).
- The collapse rules are clean: alpha-ratio flags 1,310 (1,300 WGA + 10, all genuine) and top-token flags 20 (all genuine).

---

## 5. Validator rule changes (v2)

`thesis/scripts/validation/create_persistbench_validity_summary_v2.py`: text-only, so it uses no judge score, model, category or privacy outcome.

| Change | Rationale |
|---|---|
| **W1** web/page phrases are word-bounded (`"sign in"`, `skip to content`, …) | fixes the substring defect; all 7 genuine whole-word hits kept |
| **W2** `github`, `repository`, `pull requests` removed as standalone evidence | ordinary vocabulary; genuine GitHub-page scrapes still trip `skip to content` / `toggle navigation` etc. |
| empty, tool/schema, all collapse rules | **verbatim from v1** |

**Validation against the blind audit:** TP 38, FN 2, **FP 0**, TN 97. The 2 misses are the borderline off-task tool list (A036/A042). v2 never flags anything v1 did not (0 newly invalid). 99 generations move from invalid to valid, namely the 97 false positives plus the two borderline loops. A v1 re-implementation used for these checks reproduces the original `classify` on every generation (assertion in `audit_lib.py`).

**Known residual limits of v2:**
- A legitimate whole-word "sign in" sentence (e.g. an answer about login flows) would still be flagged. None occurs in the data.
- The three tool-wrapped deliverables (`to=bio` + `canmore.create_textdoc` / JSON "updates") are kept valid because their content is interpretable. This is a judgement call, flagged borderline.

**Not changed, but important (v1 false negatives, `v2r` sensitivity).** The thesis definition lists "repetitive" outputs as invalid, and v1 has only a single-token-share rule. Many looping outputs pass as valid, for example `'Angles'. 'Angles'. …` or a refusal followed by a runaway "User: … Assistant: …" self-dialogue. I pre-specified a sensitivity rule (R1: ≥50% repeated word-trigrams in ≥20 words) and kept it **out of canonical v2**:

| | extra invalid under v2r |
|---|---|
| MUSE-Books Llama-2: Target 10, RMU 32, SatImp 6, SimNPO 41 | 89 |
| MUSE-Books Qwen RMU | 1 |
| MUSE-News Llama-2 (RMU 283, Target 121, WGA 92, SimNPO 74, SatImp 56) | 626 |

v2r changes **no direction and no conclusion** (largest shift ≈1.7 pp, e.g. News Llama-2 Target sycophancy 11.00 → 12.72, N 200 → 173). It does show that Llama-2 numbers are more loop-contaminated than any gate currently reports (§12).

---

## 6. Final validity counts (v2)

Full table: `validity_v2.tsv` (per condition × category, with v1, v2 and v2r side by side).

| Condition group | v1 invalid → v2 invalid | zero-valid scenarios v1 → v2 |
|---|---|---|
| TOFU Qwen (all 5) | 47 → 0 | 4 → 0 |
| TOFU Llama-3.1 (all 5) | 34 → 0 | 2 → 0 |
| MUSE-News Qwen | 3 (RMU) → 0 | 1 → 0 |
| MUSE-Books Qwen | 7 (RMU 6, SatImp 1) → 3 (RMU) | 2 → 1 |
| MUSE-Books Llama-2: Target / RMU / SatImp / SimNPO | 4 / 12 / 3 / 18 → 4 / 10 / 3 / 18 | 2 / 4 / 1 / 4 → unchanged |
| MUSE-Books Llama-2 WGA | 1,300 → 1,300 | 500 → 500 |
| everything else | 0 → 0 | 0 |

**v2 validity is 100% everywhere except Books Llama-2 (SimNPO 98.6%, RMU 99.2%, WGA 0%, Target 99.7%, SatImp 99.8%) and Books-Qwen RMU (99.8%).** TOFU, which looked slightly impure under v1 (99.0–99.5%), is clean.

---

## 7. Final FR@1/2/3 (v2)

All cells: `frk_validity_v2.tsv`. Procedure: first K positions; drop invalid outputs within them; **no back-filling** from later positions; exclude a scenario from N_K only if nothing valid remains; apply the category criterion to valid outputs only (beneficial memory has a single generation, so only FR@1 exists).

MUSE-News Qwen2.5-7B-Instruct (FR@1 / FR@2 / FR@3, %, N=200; beneficial N=100). Because MUSE-News v2 validity is 100%, v2 equals official here:

| Condition | cross-domain | sycophancy | beneficial FR@1 |
|---|---|---|---|
| Target | 3.50 / 3.50 / 3.50 | 9.50 / 12.50 / 12.50 | 1.00 |
| RMU | 4.00 / 4.50 / 4.50 | 11.50 / 17.50 / 18.00 | 0.00 |
| WGA | 2.50 / 5.50 / 5.50 | 9.50 / 13.00 / 13.00 | 1.00 |
| SatImp | 2.00 / 3.00 / 3.00 | 12.00 / 17.00 / 17.00 | 0.00 |
| SimNPO | 1.50 / 2.00 / 2.00 | 11.50 / 15.00 / 15.00 | 1.00 |

For v1 the only differing cell is RMU sycophancy (11.56 / 17.59 / 18.09, N=199).

---

## 8. Main Target-to-Unlearned deltas

Δ = FR(condition) − FR(Target), in pp, FR@1 / @2 / @3. **MUSE-News Qwen: identical under official, v1 and v2.** Paired exact sign tests at K=3 are in `frk_three_way_comparison.tsv`.

| Condition | cross-domain Δ | p(K=3) | sycophancy Δ | p(K=3) |
|---|---|---|---|---|
| RMU | +0.5 / +1.0 / +1.0 | 0.69 | +2.0 / +5.0 / +5.5 | 0.071 |
| WGA | −1.0 / +2.0 / +2.0 | 0.42 | 0.0 / +0.5 / +0.5 | 1.00 |
| SatImp | −1.5 / −0.5 / −0.5 | 1.00 | +2.5 / +4.5 / +4.5 | 0.108 |
| SimNPO | −2.0 / −1.5 / −1.5 | 0.38 | +2.0 / +2.5 / +2.5 | 0.405 |

(Beneficial memory: RMU −1.0, SatImp −1.0, WGA 0, SimNPO 0 pp.)

**Observation independent of the validity choice:** the MUSE-News sycophancy increases for SatImp and SimNPO are consistent in sign at every K, but none of the Target-vs-condition paired tests reaches p<0.05. The thesis should describe them as a consistent direction, not a significant effect.

Other datasets are in the same file. Books Qwen: RMU is clearly worse (cross-domain +13.5 pp, sycophancy +5.5 pp), SatImp/SimNPO are ≤0. Books Llama-2: RMU +12.5 / +10.2, SimNPO +4.7 / +12.4, SatImp −2.4 / +3.9 pp. WGA is non-evaluable.

---

## 9. Sensitivity of conclusions

| Check | Result |
|---|---|
| Max |v2 − official|, |v2 − v1|, |v1 − official| over 168 non-WGA cell×K values | 0.94, 0.50, 0.88 pp |
| Target→Unlearned direction (tolerance 0.5 pp, the thesis's band) | **0 genuine changes.** 2 threshold-edge flags (TOFU Llama sycophancy: Δ −0.50 vs −0.59 and +0.50 vs +0.55; p = 1.0 in all variants). |
| Significance (paired exact sign test) | **0 changes** |
| Claim: MUSE-News Qwen sycophancy worsens at every K for SatImp and SimNPO | holds under official, v1, v2 and v2r |
| Claim: MUSE-News Qwen cross-domain improves for SatImp and SimNPO at every K | holds under all four |
| Claim: MUSE-Books Qwen sycophancy does not replicate (SatImp/SimNPO ≤ 0) | holds under all four |
| Full-prompt sycophancy robustness | RMU +2.00 (p 0.557), SatImp +3.08 → +3.00 (p 0.286), SimNPO +1.00 (p 0.832): same under v1/v2 apart from SatImp N 199 → 200 |
| Full-prompt cross-domain robustness | RMU +1.00 (p 0.688), SatImp +1.52 → +1.50 (p 0.453), SimNPO +3.53 → +3.50 (**p 0.039**, significant under all variants) |
| MUSE-Books Llama-2 WGA | official FR@3 = 10.00 (cross-domain) and 43.00 (sycophancy), N=200, "better/worse" vs Target; v1 and v2: N=0, non-evaluable. This is the only place where the choice changes what is *reported*. |
| Judge robustness (Qwen vs Gemma) | 210/210 stored official values reproduced. 6 of 154 Target-delta values move ≥0.5 pp (max 0.94, all Books RMU, due to genuine invalids); no direction flips |
| Scenario-level Qwen–Gemma FR@3 agreement (MUSE-News sycophancy) | official 47.90% (κ 0.1096, N=1000); v1 47.95% (κ 0.110, N=999); **v2 47.90% (κ 0.1096, N=1000)** |
| Paradox-analysis (strict/broad valid-only), 24 conditions | my v1 recomputation reproduces the stored CSV **24/24**. Max change in strict Δ: 0.23 pp. TOFU Qwen RMU "strongest example": +1.45 → +1.46 pp, validity 99.08/99.46% → 100/100%. **One quadrant flips: TOFU Qwen SimNPO strict Δ −0.08 → +0.15 pp, "both_improve" → "privacy_paradox"; the paradox count goes 7 of 16 → 8 of 16.** |
| `v2r` (repetition sensitivity) | 0 direction changes, ≤1.7 pp shifts |

Interpretation: the validity gate matters for *correctness of the method description* and for WGA, not for any result. The one fragile statement is the sign-based quadrant count, which depends on 0.1 pp differences. I recommend re-reading that count with the thesis's existing ±0.5 pp stability band rather than strict signs.

---

## 10. Recommended canonical procedure

**C. Validity-aware FR@K with the corrected validator v2**, applied to every FR@K, validity table, robustness table and paradox table.

- **Against A (official):** it ignores validity. It scores a collapsed model as 10% / 43% failure and cannot support the stated purpose of the gate (never read broken output as either privacy success or failure). It is retained only as the upstream reference column.
- **Against B (v1):** it implements the right procedure with a defective rule. 91.5% of its non-collapse web flags are false, concentrated asymmetrically (e.g. 3 of the 3 MUSE-News flags are in RMU only), so it perturbs the Target-vs-condition comparison it is meant to protect. Keeping it would force the thesis to disclose a known defect.
- **For C:** v2 = v1 minus two documented false-positive mechanisms, so every genuine detection is preserved. It is verified against a blind audit, text-only (outcome independent), and moves results by <1 pp. The rules were derived from the text audit before any FR@K was recomputed, and the change set is exactly those two mechanisms.
- **Reporting rule:** report official FR@K alongside as a robustness column. All headline conclusions are invariant, which is itself a useful sentence for the thesis.

---

## 11. Exact thesis tables that must change

I do not have the Chapter 4 LaTeX in the repository, so this is expressed against the stored/appendix tables. `thesis_impact_changes.tsv` lists every changed cell (143 rows: current number → final number, difference, whether the interpretation changes). `fullprompt_robustness_v1_vs_v2.tsv` has the full-prompt side by side.

| Table / artifact | Cells that change (current → final) | Interpretation |
|---|---|---|
| Appendix `generation_validity_complete.tsv` + any validity table | 22 condition×category rows. E.g. TOFU Qwen Target sycophancy valid 588/600 (98.00%) → 600/600, zero-valid scenarios 1 → 0; MUSE-News RMU sycophancy 597/600 → 600/600, zero-valid 1 → 0; Books Qwen RMU sycophancy 596/600 → 598/600 | none |
| Appendix `persistbench_frk_complete.tsv`, validity-aware rows | 32 cell rows. E.g. MUSE-News RMU sycophancy FR@1/2/3 11.56 / 17.59 / 18.09 (N=199) → 11.50 / 17.50 / 18.00 (N=200) | none |
| Official FR@K tables (`persistbench_all_methods_all_corpora.csv`, bundle copy, appendix official rows, Qwen judge JSON) | 24 rows. All genuine-invalid effects ≤0.94 pp. **Books Llama-2 WGA: a number → "not evaluable"** | none, except WGA |
| Appendix `fullprompt_robustness.tsv` | 4 rows. SatImp sycophancy full-prompt FR@3 15.58 (N=199) → 15.50 (N=200), Δ +3.08 → +3.00, validity 597/600 → 600/600. SatImp cross-domain 3.02 → 3.00 (Δ +1.52 → +1.50), SimNPO cross-domain 5.03 → 5.00 (Δ +3.53 → +3.50), both 597/600 → 600/600. RMU sycophancy original 18.09 (199) → 18.00 (200) | none; p values and transitions unchanged |
| Appendix `judge_agreement.tsv` | scenario-level row 47.95 / κ 0.110 / N=999 → 47.90 / κ 0.1096 / N=1000. The pooled and exact-score rows do not depend on the gate | none |
| Appendix `judge_robustness.tsv` | 48 rows, ≤0.9 pp (Books RMU, genuine invalids); WGA rows → NA | none |
| Benchmark-paradox outputs (`condition_level_results`, `strict_paradox_classification`, `validity_summary`, `intersection_valid_results`, quadrant figures) | 12 conditions shift in validity % or strict Δ (≤0.23 pp). TOFU Qwen SimNPO strict Δ −0.08 → +0.15 pp; quadrant "both_improve" → "privacy_paradox"; counts 7/16 → 8/16 | **label change, not evidence change** |
| `mechanistic/.../muse_news_category_comparison_validated.csv`, `muse_books_weekly_update_analysis/persistbench_fr_at_k.csv` | RMU rows only, ≤0.94 pp | none |

**Chapter 3 wording.** Yes, it needs a change. It should state the operational definition, not only the intent. Suggested content, which I did not apply:
- Validity is decided per generation from the response text alone, by four rules: empty or effectively empty; collapse (a fixed gibberish-token list, <30 characters, <25% alphabetic, or one token >30% of ≥30 words); page-navigation boilerplate matched as whole phrases; tool/schema JSON. State that ordinary software vocabulary is not treated as contamination.
- Define FR@K as above (first K, drop invalid, no back-filling, exclude scenarios with no valid output from N_K) and say N_K is reported with every FR@K.
- Do not claim that the *stored official* FR@K tables exclude invalid generations; they do not.
- Disclose that repetition loops are only partly covered (single-token share), with the `v2r` sensitivity.

---

## 12. Is another generation experiment required?

**No.** Everything in this audit is a recomputation on stored generations. Judge scores are retained: validity depends only on response text, so the same flags apply to both judges.

Decisions for you (not experiments):
1. **Repetition loops.** Whether to extend the gate to cover looping outputs (`v2r`, or a better detector). It changes no conclusion, but it affects the Llama-2 validity numbers you will quote (MUSE-News Llama-2 RMU would drop to ~78% valid).
2. **Seven borderline manual calls** (IDs in `invalid_manual_audit.tsv`, column "borderline"; the three tool-wrapped ones are kept valid). The audit was done by one reviewer. I recommend a quick spot-check of those.
3. **Paradox count.** Keep strict-sign quadrants (8/16) or use the ±0.5 pp stability band.

## Files

| File | Content |
|---|---|
| `frk_official_vs_validity_v1.tsv` | Step 1; 29 differing cells flagged |
| `invalid_generations_v1.tsv` | Step 2; all 1,437 v1-invalid generations (class A / B) |
| `validator_rules_audit.tsv` | Step 3; every v1 rule |
| `invalid_manual_audit.tsv`, `invalid_manual_audit_key.tsv` | Step 4; blind audit and the ID key |
| `validity_v2.tsv`, `frk_validity_v2.tsv` | Steps 6–7 |
| `frk_three_way_comparison.tsv`, `headline_conclusion_checks.tsv` | Step 8 |
| `fullprompt_robustness_v1_vs_v2.tsv`, `judge_robustness_v2.tsv`, `paradox_strict_broad_v1_vs_v2.tsv`, `thesis_impact_changes.tsv` | Step 10 support |
| `scripts/` | `run_all.sh` rebuilds everything; `manual_labels.json` is the frozen audit record |
