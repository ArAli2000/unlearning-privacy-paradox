# Method-Selection Table (10 → 4 methods) — Read-Only Audit

Scope: evidence for carrying RMU, WGA, SatImp and SimNPO forward instead of the other six screened methods (CEU, GradAscent, GradDiff, NPO, PDU, UNDIAL), and specifically RMU instead of PDU, across Llama-3.2-1B-Instruct, Llama-3.2-3B-Instruct and Qwen2.5-3B-Instruct.
Nothing was modified or re-run. All numbers below were **recomputed by me from raw per-checkpoint eval outputs** with the formulas in `src/trainer/base.py` (`add_proxy_scores`, lines 47–119, uncommitted working-tree code). Slides were not used. The Qwen2.5-3B Stage-A numbers agree with the earlier audit `thesis_cleanup_audit/PRESENTATION_TOFU_CHECKPOINT_VERIFICATION.md` §D (e.g. PDU 0.4708, RMU 0.4650).

## 0. Findings that change the premise (read first)

1. **The three models were never screened with the same method set.** The 10-method screen exists for **Llama-3.2-1B and Qwen2.5-3B only**. Llama-3.2-3B has just SatImp, SimNPO and WGA in the same screen (`saves/unlearn/paper_llama32_3b_{satimp,simnpo,wga}_f10_a180_fullmetrics`). **RMU and PDU were never run on Llama-3.2-3B in the 10-method screen**, and PDU was never run on Llama-3.2-3B at all. (Consistent with `UNRESOLVED.md` row 1 and `CANONICAL_EXPERIMENTAL_SETUP.md` §"TOFU method × model coverage".)
2. **RMU, WGA, SatImp and SimNPO *were* run on all three models** — but at a later stage (B1, 2026-06-14..16, `bestagg_*`), after the four had already been hard-coded in the launch script (`research_history/03_checkpoint_selection_development/scripts/run_4models_4methods_save_bestagg.sh`). Llama-3.2-1B in B1 **crashed** (`saves/unlearn/bestagg_llama32_1b_*_savebest/` contain only `<M>.log`, no `trainer_state.json`). So there is **no stage and no score on which all five of RMU/WGA/SatImp/SimNPO/PDU exist on all three models**.
3. **The stage-dependent metric definitions differ and must not be merged** (§1).
4. **The statement "RMU was retained instead of PDU because it was more consistent across the three model settings" has no historical backing and cannot be tested on three models** (PDU exists on two). It is only qualitatively supported, and on the formal `Agg` score it is partly contradicted (§4).

## 1. Stages and metric definitions (not interchangeable)

| Stage | Runs | Selection of "best checkpoint" | Metric available |
|---|---|---|---|
| **A** (screen, 2026-05-22..25; Llama-3B 05-31) | `saves/unlearn/paper_{llama32_1b,qwen25_3b}_<m>_f10_a180_fullmetrics` (10 methods each); `paper_llama32_3b_{satimp,simnpo,wga}_f10_a180_fullmetrics` (3 methods). TOFU forget10, start = base Instruct, 120 steps, evals every 13 steps (ckpts 13…120) | **None at run time** (`best_metric` null). Post-hoc: I take argmax of `Agg` over checkpoints > 0 (ckpt-0 = untouched model, excluded; this exclusion is inferred, not written in the repo — see earlier audit §H) | Raw TOFU metrics only. `Mem/Priv/Util/Agg/Selection` are **derived by me** post-hoc. Per-checkpoint weights do not exist (`checkpoint-N/` hold only `evals/`) |
| **B1** (2026-06-14..16) | `saves/unlearn/bestagg_{llama32_3b,qwen25_3b}_<m>_savebest` (RMU/SatImp/SimNPO/WGA). Start = base Instruct | In-training, `load_best_model_at_end`, `metric_for_best_model = eval_Agg_proxy` (step 0 not selectable) | `eval_*_proxy` logged in `trainer_state.json` `log_history` |
| **B2** (2026-06-17..23) | `saves/unlearn/proper_{llama32_3b,qwen25_3b}_<m>_from_tofufull_*savebest`. Start = **TOFU-full-finetuned** model (different baseline) | Llama-3B: `Agg_proxy`; Qwen-3B: **`Selection_proxy`** (different criterion) | as B1 |

Formulas (`src/trainer/base.py:47-109`): `Mem = HM(1−extraction_strength, 1−exact_memorization, 1−forget_Q_A_Prob, 1−forget_truth_ratio)`; `Priv = HM(mia_loss, mia_zlib, mia_min_k, mia_min_k_plus_plus)` (MIA AUCs, **a leakage proxy, not contextual privacy; higher = more membership leakage yet rewarded by `Agg`** — direction intent UNKNOWN, `UNRESOLVED.md` row 3); `Util = HM(min(model_utility/MU0, 1), forget_Q_A_gibberish)` with MU0 = `model_utility` at ckpt-0 of the same run; `Agg = HM(Mem, Priv, Util)`; `Selection_proxy = HM(Mem, Util)` (no MIA term).

Consequences: (i) Stage-A `Agg` is a post-hoc score; B1/B2 scores are in-training scores; (ii) B2 starts from a different model, so its values are not comparable with A/B1; (iii) the ckpt-0 baseline `Agg` is already ≈0.46–0.49 (Llama-1B 0.4879, Qwen-3B 0.4636; Llama-3B B1 0.4928), so **best-`Agg` differences among the top methods are small (≤0.02) and `Agg` is not a forgetting measure by itself**.

## 2. Raw evidence per model setting

Common path pattern. Stage A: `saves/unlearn/paper_<run>_f10_a180_fullmetrics/checkpoint-<N>/evals/TOFU_SUMMARY.json` (values) with `checkpoint-0/evals/TOFU_SUMMARY.json` (MU0). The same raw numbers are frozen in `research_history/01_tofu_baselines/manifests/saves__unlearn__paper_<run>_f10_a180_fullmetrics__trainer_state.json` (spot-check: Llama-1B PDU ckpt-104 `model_utility` 0.28348 in both) and, for Qwen-3B / Llama-3B, `research_history/02_model_method_scaling/manifests/saves__unlearn__paper_<run>__trainer_state.json`.

### 2a. Stage A — Llama-3.2-1B-Instruct (all 10 run; run = `llama32_1b`; ckpt-0 `Agg` 0.4879)

Best checkpoint = argmax `Agg` over ckpts 13–120. "Sel-rank" = rank by best `Selection_proxy` (own argmax; ckpt in brackets). "Last Agg" = ckpt-120. "#ckpt Agg<0.05" = number of the 10 evaluated checkpoints in which the model had effectively collapsed.

| Rank (Agg) | Method | Best ckpt | Mem | Priv | Util | **Agg** | Selection (at best-Agg ckpt) | Sel-rank [ckpt, value] | Last Agg | Last model_utility | #ckpt Agg<0.05 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | SimNPO | 52 | 0.4577 | 0.3401 | 0.9608 | 0.4866 | 0.6200 | 6 [39, 0.6210] | 0.4854 | 0.389 | 0 |
| 2 | SatImp | 52 | 0.4573 | 0.3403 | 0.9590 | 0.4864 | 0.6193 | 7 [78, 0.6210] | 0.4856 | 0.389 | 0 |
| 3 | WGA | 13 | 0.4547 | 0.3297 | 0.9608 | 0.4782 | 0.6173 | 5 [117, 0.6294] | 0.4630 | 0.388 | 0 |
| 4 | **RMU** | 13 | 0.5282 | 0.3143 | 0.8299 | 0.4778 | 0.6456 | 3 [78, 0.6905] | 0.2336 | 0.284 | 0 |
| 5 | UNDIAL | 13 | 0.4851 | 0.3028 | 0.9622 | 0.4685 | 0.6450 | 4 [117, 0.6788] | 0.4071 | 0.271 | 0 |
| 6 | **PDU** | 104 | 0.4436 | 0.3121 | 0.9684 | 0.4622 | 0.6084 | 8 [104, 0.6084] | 0.4620 | 0.295 | **5** |
| 7 | GradDiff | 13 | 0.5117 | 0.2611 | 0.9098 | 0.4359 | 0.6550 | 1 [39, 0.7517] | 0.0233 | 0.207 | 4 |
| 8 | NPO | 13 | 0.5134 | 0.2716 | 0.6616 | 0.4201 | 0.5782 | 2 [65, 0.7095] | 0.0106 | 0.330 | 6 |
| 9 | CEU | 13 | 0.4565 | 0.3264 | 0.3279 | 0.3613 | 0.3817 | 9 [13, 0.3817] | 0.0000 | 0.000 | 9 |
| 10 | GradAscent | 13 | 0.6873 | 0.3433 | 0.0053 | 0.0155 | 0.0105 | 10 [13, 0.0105] | 0.0000 | 0.000 | 10 |

Note: no method exceeds the untouched model's `Agg` (0.4879) here, and RMU's `Agg` decays monotonically 0.478 → 0.234 (Priv 0.314 → 0.101: MIA AUC falls far below 0.5; MU 0.21 → 0.28 → 0.28). PDU's checkpoints 26/39/52/65/78 have `model_utility` 0.000 (utility collapse) and it only recovers by ckpt-91 (`Agg` 0.451).

### 2b. Stage A — Qwen2.5-3B-Instruct (all 10 run; run = `qwen25_3b`; ckpt-0 `Agg` 0.4636)

| Rank (Agg) | Method | Best ckpt | Mem | Priv | Util | **Agg** | Selection (at best-Agg ckpt) | Sel-rank [ckpt, value] | Last Agg | Last model_utility | #ckpt Agg<0.05 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | SatImp | 13 | 0.4668 | 0.3302 | 0.9647 | 0.4833 | 0.6291 | 8 [13, 0.6291] | 0.4669 | 0.415 | 0 |
| 2 | SimNPO | 13 | 0.4666 | 0.3299 | 0.9645 | 0.4830 | 0.6290 | 9 [13, 0.6290] | 0.4665 | 0.415 | 0 |
| 3 | WGA | 13 | 0.4667 | 0.3287 | 0.9673 | 0.4824 | 0.6296 | 7 [13, 0.6296] | 0.4513 | 0.416 | 0 |
| 4 | **PDU** | 13 | 0.4847 | 0.3049 | 0.9716 | 0.4708 | 0.6467 | 6 [13, 0.6467] | 0.4673 | 0.328 | **3** |
| 5 | **RMU** | 52 | 0.5484 | 0.2801 | 0.9452 | 0.4650 | 0.6941 | 3 [52, 0.6941] | 0.4629 | 0.258 | 0 |
| 6 | GradDiff | 13 | 0.5368 | 0.2623 | 0.9510 | 0.4460 | 0.6862 | 1 [117, 0.7777] | 0.4230 | 0.270 | 0 |
| 7 | UNDIAL | 13 | 0.5532 | 0.2668 | 0.8213 | 0.4429 | 0.6611 | 4 [117, 0.6892] | 0.4345 | 0.235 | 0 |
| 8 | CEU | 13 | 0.5163 | 0.2646 | 0.8806 | 0.4378 | 0.6510 | 5 [13, 0.6510] | 0.0000 | 0.000 | 8 |
| 9 | NPO | 13 | 0.5598 | 0.2652 | 0.4647 | 0.3891 | 0.5078 | 2 [120, 0.7033] | 0.2368 | 0.244 | 0 |
| 10 | GradAscent | 13 | 0.6077 | 0.2914 | 0.0919 | 0.1881 | 0.1597 | 10 [13, 0.1597] | 0.0000 | 0.000 | 9 |

Note: PDU's `model_utility` is 0.038 (ckpt-26), 0.000 (ckpt-52, 65) and recovers to 0.207 at ckpt-78 and 0.328 at ckpt-120. RMU is flat (`Agg` 0.463–0.465 at every checkpoint).

### 2c. Llama-3.2-3B-Instruct

**Stage A (only 3 methods; RMU, PDU and the six others not run):** run = `paper_llama32_3b_<m>_f10_a180_fullmetrics`, MU0 0.2716.

| Method | Best ckpt | Mem | Priv | Util | Agg | Selection | Last Agg |
|---|---|---|---|---|---|---|---|
| SimNPO | 52 | 0.4561 | 0.3293 | 0.9617 | 0.4786 | 0.6187 | 0.4767 |
| SatImp | 52 | 0.4558 | 0.3293 | 0.9593 | 0.4782 | 0.6180 | 0.4767 |
| WGA | 13 | 0.4580 | 0.3218 | 0.9661 | 0.4743 | 0.6214 | 0.4371 |
| RMU / PDU | not run | | | | | | |

**B1 (4 methods, in-training `Agg_proxy` selection; ckpt-0 `Agg` 0.4928):** values read from `log_history` of `saves/unlearn/bestagg_llama32_3b_<m>_savebest/trainer_state.json` at `best_global_step` (identical to `selected_checkpoints.tsv` rows).

| Method | Selected ckpt | Mem | Priv | Util | Agg | Selection |
|---|---|---|---|---|---|---|
| RMU | 13 | 0.5026 | 0.3276 | 0.9444 | 0.4917 | 0.6560 |
| SatImp | 52 | 0.4546 | 0.3283 | 0.9580 | 0.4770 | 0.6166 |
| SimNPO | 52 | 0.4551 | 0.3277 | 0.9601 | 0.4769 | 0.6175 |
| WGA | 13 | 0.4580 | 0.3218 | 0.9661 | 0.4743 | 0.6214 |

### 2d. B1 — Qwen2.5-3B-Instruct (same four; ckpt-0 `Agg` 0.4634), from `saves/unlearn/bestagg_qwen25_3b_<m>_savebest/trainer_state.json`

| Method | Selected ckpt | Mem | Priv | Util | Agg | Selection |
|---|---|---|---|---|---|---|
| SatImp | 13 | 0.4668 | 0.3306 | 0.9653 | 0.4837 | 0.6293 |
| SimNPO | 13 | 0.4672 | 0.3302 | 0.9652 | 0.4835 | 0.6297 |
| WGA | 13 | 0.4671 | 0.3297 | 0.9682 | 0.4833 | 0.6301 |
| RMU | 39 | 0.5470 | 0.2805 | 0.9410 | 0.4647 | 0.6918 |

### 2e. B2 (TOFU-full-finetuned start; **different baseline, different criterion for Qwen — shown only as supporting context**)

| Model | Method | Selected ckpt | Mem | Priv | Util | Agg | Selection | Criterion | Source dir (`saves/unlearn/`) |
|---|---|---|---|---|---|---|---|---|---|
| Llama-3B | RMU | 52 | 0.4970 | 0.7596 | 0.9086 | 0.6773 | 0.6425 | Agg | `proper_llama32_3b_rmu_from_tofufull_savebest` |
| Llama-3B | WGA | 117 | 0.3694 | 0.9354 | 0.9219 | 0.6172 | 0.5274 | Agg | `…wga…` |
| Llama-3B | SimNPO | 117 | 0.0873 | 0.9913 | 0.9239 | 0.2214 | 0.1595 | Agg | `…simnpo…` |
| Llama-3B | SatImp | 52 | 0.0373 | 0.9981 | 0.9213 | 0.1037 | 0.0716 | Agg | `…satimp…` |
| Qwen-3B | RMU | 78 | 0.4409 | 0.4170 | 0.9557 | 0.5251 | 0.6034 | Selection | `proper_qwen25_3b_rmu_from_tofufull_selectionproxy_savebest` |
| Qwen-3B | WGA | 104 | 0.4395 | 0.4124 | 0.9613 | 0.5226 | 0.6032 | Selection | `…wga…` |
| Qwen-3B | SimNPO | 78 | 0.4361 | 0.4354 | 0.9599 | 0.5327 | 0.5997 | Selection | `…simnpo…` |
| Qwen-3B | SatImp | 78 | 0.4357 | 0.4362 | 0.9584 | 0.5328 | 0.5991 | Selection | `…satimp…` |

(Each from `<dir>/trainer_state.json` `log_history` at `best_global_step`.) In Llama-3B B2 SatImp/SimNPO "selected" checkpoints barely forget (Mem 0.04/0.09 vs 0.50 for RMU) — the earlier audit already flags this.

## 3. Proposed thesis table (format B+C: within-model rank and status)

Format A (a single comparable aggregate) is **not defensible** (PDU/RMU/other six are absent on Llama-3B; B1/B2 differ; Llama-1B has no B1). Format B is defensible only inside a stage. I propose one compact table based on **Stage A, the only stage in which all ten methods exist** (Llama-1B, Qwen-3B), with Llama-3B shown only where a run exists, plus a status label derived from raw trajectories (my descriptive labels, not historical decisions).

Status labels (my descriptive rules, reproducible from §2a/§2b): **strong** = no evaluated checkpoint with `Agg` < 0.4 and ckpt-120 `Agg` ≥ 0.45; **stable** = same without the 0.45 requirement on a flat trajectory (RMU Qwen-3B); **decaying** = ckpt-120 `Agg` < 0.3 without any zero-utility checkpoint (RMU Llama-1B); **unstable** = ≥ 3 of 10 checkpoints with `Agg` < 0.05 but recovered by ckpt-120 (PDU); **collapsed** = ckpt-120 `model_utility` ≤ 0.05 or `Agg` ≤ 0.03; **intermediate** = the rest. Under these rules NPO/GradDiff on Qwen-3B are intermediate, and on Llama-1B they end collapsed.

| Method | Llama-3.2-1B rank (Agg) | Qwen2.5-3B rank (Agg) | Llama-3.2-3B | Status (Llama-1B / Qwen-3B) |
|---|---|---|---|---|
| SimNPO | 1 (0.4866) | 2 (0.4830) | 0.4786 (best of 3 run) | strong / strong |
| SatImp | 2 (0.4864) | 1 (0.4833) | 0.4782 | strong / strong |
| WGA | 3 (0.4782) | 3 (0.4824) | 0.4743 | strong / strong |
| RMU | 4 (0.4778) | 5 (0.4650) | not run in screen; B1 0.4917 (1st of 4) | decaying (last Agg 0.2336) / stable |
| PDU | 6 (0.4622) | 4 (0.4708) | not run | unstable (5/10 ckpts collapsed) / unstable (3/10) |
| UNDIAL | 5 (0.4685) | 7 (0.4429) | not run | intermediate / intermediate |
| GradDiff | 7 (0.4359) | 6 (0.4460) | not run | collapsed at end / intermediate |
| NPO | 8 (0.4201) | 9 (0.3891) | not run | collapsed at end / intermediate (declining) |
| CEU | 9 (0.3613) | 8 (0.4378) | not run | collapsed / collapsed |
| GradAscent | 10 (0.0155) | 10 (0.1881) | not run | collapsed / collapsed |

Provenance of every number: Llama-1B and Qwen-3B columns = §2a/§2b rows (`saves/unlearn/paper_llama32_1b_<m>_f10_a180_fullmetrics/checkpoint-{N}/evals/TOFU_SUMMARY.json`, `…/paper_qwen25_3b_<m>_f10_a180_fullmetrics/…`, N = best ckpt column, MU0 from `checkpoint-0`); Llama-3B screen = §2c (`saves/unlearn/paper_llama32_3b_<m>_f10_a180_fullmetrics/…`); Llama-3B B1 RMU = `saves/unlearn/bestagg_llama32_3b_rmu_savebest/trainer_state.json` (`log_history`, step 13, `eval_Agg_proxy` 0.4917).

**Alternative panel — the four carried-forward methods only (rank within the four), available for all three models but from different stages:**

| Method | Llama-1B (A, Agg) | Qwen-3B (A, Agg) | Llama-3B (B1, Agg) | Qwen-3B (B1, Agg) | Selection_proxy at the Agg-best ckpt: L1B / Q3B(A) / L3B(B1) / Q3B(B1) |
|---|---|---|---|---|---|
| SimNPO | 1 (0.4866) | 2 (0.4830) | 3 (0.4769) | 2 (0.4835) | 0.6200 / 0.6290 / 0.6175 / 0.6297 |
| SatImp | 2 (0.4864) | 1 (0.4833) | 2 (0.4770) | 1 (0.4837) | 0.6193 / 0.6291 / 0.6166 / 0.6293 |
| WGA | 3 (0.4782) | 3 (0.4824) | 4 (0.4743) | 3 (0.4833) | 0.6173 / 0.6296 / 0.6214 / 0.6301 |
| RMU | 4 (0.4778) | 4 (0.4650) | 1 (0.4917) | 4 (0.4647) | **0.6456 / 0.6941 / 0.6560 / 0.6918** |

RMU has the highest `Selection_proxy` of the four in all four settings (margin 0.026–0.065; driven by higher `Mem`), whereas the other three are within ≈0.01 of each other and their mutual order is not meaningful. RMU's `Agg` rank is 4, 4, 1, 4 (it is first only on Llama-3B B1, where all four are ≈ the untouched model's 0.4928). These patterns are properties of the numbers, **not** a criterion applied historically. Sources: §2a–§2d.

## 4. The claim: "RMU was retained instead of PDU because RMU was more consistent across the three settings"

**Historical evidence: none.** No script, config, doc or manifest states this reason. `UNRESOLVED.md` row 1, `CANONICAL_EXPERIMENTAL_SETUP.md` §7 item 4 and `MASTER_THESIS_MAP.md` (l.202: an earlier "methodological consistency" explanation was removed as unsupported) all say the rationale is UNKNOWN. On 2026-05-31 the "top3" = SatImp/SimNPO/WGA (RMU and PDU both absent); on 2026-06-14 the four were hard-coded with RMU re-added and no reason (`research_history/03_checkpoint_selection_development/scripts/run_4models_4methods_save_bestagg.sh`). No formal consistency measure existed. PDU also crashed in its first launches because `retain_loss_eps` was unset (run overrides now pass `trainer.method_args.retain_loss_eps=0.1`, e.g. `saves/unlearn/paper_qwen25_3b_pdu_f10_a180_fullmetrics/.hydra/overrides.yaml`).

**What the raw numbers say (post-hoc; I did not invent a score — only reading existing metrics):**

| Observation | RMU | PDU | Verdict on the claim |
|---|---|---|---|
| Rank by `Agg` (L1B / Q3B) | 4 / 5 | 6 / 4 | **Does not support**: PDU outranks RMU on Qwen-3B (0.4708 vs 0.4650); RMU outranks PDU on Llama-1B (0.4778 vs 0.4622). The order flips between models → neither is "more consistent" by `Agg` |
| Rank by `Selection_proxy` (L1B / Q3B) | 3 / 3 | 8 / 6 | **Supports**: RMU > PDU on both models (0.6456 vs 0.6084; 0.6941 vs 0.6467), RMU rank identical on both |
| Mem at best ckpt (L1B / Q3B) | 0.5282 / 0.5484 | 0.4436 / 0.4847 | RMU forgets more by `Mem` on both |
| Util at best ckpt | 0.8299 / 0.9452 | 0.9684 / 0.9716 | PDU higher |
| Trajectory stability (ckpts with `Agg`<0.05, of 10) | 0 / 0 | 5 / 3 | **Supports**: PDU passes through utility collapse (`model_utility` 0.000 at 26–78 on Llama-1B; 0.000 at 52–65 on Qwen-3B) then recovers; RMU never collapses |
| `Agg` at last ckpt (L1B / Q3B) | 0.2336 / 0.4629 | 0.4620 / 0.4673 | **Contradicts** on Llama-1B: RMU decays strongly (Priv 0.314→0.101); PDU is better at the end of training |
| Runs on Llama-3.2-3B | B1/B2 yes; screen no | none | PDU cannot be assessed on the third model |

Conclusion: the statement is, at best, **qualitatively and partially** supportable: RMU is consistently preferable under the memorisation+utility score and never shows PDU's mid-training collapse, but it is **not** supported by `Agg`, is contradicted by RMU's late-training decay on Llama-1B, and cannot be checked on three models. Recommended thesis wording: *"PDU was screened but not carried forward; its checkpoints showed transient utility collapse on both screened models. RMU, a representation-based method, was retained for method diversity and for its consistently higher memorisation-proxy removal; the choice is a qualitative judgement, not the outcome of a formal ranking."* ("method diversity" is my suggested rationale — **it is not documented in the repository**; use only if the author confirms it, otherwise drop that clause.)

## 5. Caption, interpretation, caveats

**Caption (for the Stage-A table):** *Post-hoc screening of ten unlearning methods on TOFU forget10 (120 steps, base-Instruct start). Rank = rank by the best post-unlearning checkpoint's aggregate proxy Agg = HM(Mem, Priv, Util), with the untouched checkpoint excluded; Priv is a membership-inference leakage proxy. Status labels summarise the checkpoint trajectory. Llama-3.2-3B was screened with three methods only.*

**How to read it (2–4 sentences):** SimNPO, SatImp and WGA occupy ranks 1–3 on Llama-3.2-1B and Qwen2.5-3B and are the only methods with stable trajectories on both; their `Agg` values differ by ≤ 0.002 and should be treated as tied. RMU and PDU sit at ranks 4–6 with different orderings on the two models, so the `Agg` ranking does not by itself justify keeping RMU over PDU. CEU, GradAscent (and, at the end of training, GradDiff/NPO on Llama-1B) collapse utility. The table is a screening summary, not the rule that produced the four-method set.

**Caveats that must be stated:**
1. No selection rule exists in the repository; the narrowing was a hard-coded method list (2026-06-14) — a qualitative triage.
2. Stage-A best checkpoints were chosen post hoc by me with an `Agg` formula that postdates the runs (the code first appears 2026-06-14, runs 2026-05-22..25); ckpt-0 exclusion is an inference; checkpoint weights for Stage A no longer exist (only `evals/`).
3. `Priv` is an MIA leakage proxy, not contextual privacy, and in `Agg` a higher MIA AUC (more leakage) *raises* the score (intent unresolved). Stage-A best `Agg` is ≤ the untouched model on Llama-1B (all methods) — `Agg` mostly measures preservation. Differences between ranks 1–3 are ≤ 0.002 (single seed, one evaluation each; no seed variance available).
4. Llama-3.2-3B has no RMU/PDU screening run; Llama-1B has no B1 run (crash). No stage covers all five key methods on all three models. B1 uses in-training `Agg_proxy`; B2 starts from a different model and (Qwen) selects with `Selection_proxy` — do not mix with Stage A.
5. Stage A used 13-step evaluation (10 checkpoints), a coarse grid; PDU's collapse windows could be partly grid-dependent. The "stable/unstable" labels and the `Selection_proxy` rank-within-four pattern are descriptive statistics I computed, not historical decision criteria.
6. Plain 7-metric and `fullmetrics` Llama-1B runs are near-duplicates; only `fullmetrics` (which logs the MIA metrics needed for `Priv`) is used. Qwen2.5-3B also has an `a100` batch (alpha 100, 6 methods) — not used. Qwen2.5-1.5B (8/10, PDU crashed, RMU incomplete) is not one of the three settings and was excluded.
7. `src/trainer/base.py` proxy code is uncommitted; commit it (or cite `thesis_cleanup_audit/CHECKPOINT_SELECTION_PATCH.md`) before citing the formula.

## 6. Reproduction

All values computed with a short Python script (kept outside the repo) that, for each run, loads `checkpoint-N/evals/TOFU_SUMMARY.json` for N = 0, 13, …, 120, applies `add_proxy_scores` logic (HM floored at 1e-12, `Util` scaled by ckpt-0 `model_utility`), and takes argmax over N > 0. B1/B2 values are read directly from `eval_*_proxy` keys in `log_history` of each `trainer_state.json` at `best_global_step`; they agree with `thesis/docs/experimental_setup_audit/selected_checkpoints.tsv`.
