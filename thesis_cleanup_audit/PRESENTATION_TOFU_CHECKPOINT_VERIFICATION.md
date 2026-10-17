# TOFU Checkpoint-Selection Verification — Qwen2.5-3B, 10-method Phase-1 sweep

Read-only forensic verification. No code, config, checkpoint, or historical artifact was modified to produce this report. All commands run were read-only (`cat`, `ls`, `find`, `git diff`/`git log` with no write flags, `python3 -c "..."` reading JSON files).

Working directories inspected: `/mnt/beegfs/work/elshashay/open-unlearning` and `/storage/ukp/work/elshashay/open-unlearning` — these resolve to the **same filesystem path** (`realpath` on both returns `/mnt/beegfs/work/elshashay/open-unlearning`), so there is only one copy of the repository, not two independent ones.

---

## A. Verdict

| Slide claim | Verdict |
|---|---|
| Slide 1: "For Qwen2.5-3B + SatImp, the best checkpoint by Agg was ckpt-13 (Agg≈0.4833, Mem≈0.4668, Priv≈0.3302, Util≈0.9647)" | **VERIFIED** — exact match to 10 significant figures, independently recomputed from raw per-checkpoint metrics, excluding the pre-training checkpoint-0 from the candidate pool (see §C, §H). |
| Slide 2: "Best checkpoint per method, all 10 Qwen2.5-3B TOFU methods, ranked by Agg" | **VERIFIED WITH ONE CAVEAT** — all 10 Agg values and all 10 selected checkpoints match the existing claim exactly (see §D), *provided* checkpoint-0 (the pre-unlearning baseline, identical across all 10 methods) is excluded from checkpoint-selection candidates. This exclusion is not written down anywhere in the repository as an explicit rule — it is inferred from the fact that including ckpt-0 would make it win for 5 of the 10 methods (CEU, GradAscent, GradDiff, NPO, UNDIAL), which contradicts the existing claim and would be a methodologically meaningless result (see §H). |
| Implicit claim: "RMU/WGA/SatImp/SimNPO were the top-4 Qwen2.5-3B methods by Agg" | **NOT VERIFIED — CONTRADICTED.** PDU ranks 4th (Agg=0.470808), above RMU, which ranks 5th (Agg=0.464969). Do not say the four carried-forward methods were literally "the top 4 by Agg" on this model (see §D, §H). |
| "Checkpoint selection was performed automatically during Phase-1 training" | **NOT VERIFIED — CONTRADICTED.** `trainer_state.json` for every one of the 10 runs has `best_metric`, `best_global_step`, `best_model_checkpoint` all `null`. The Agg/Mem/Priv/Util fields do not appear anywhere in Phase-1's `trainer_state.json` log_history. The formula that computes them did not exist in `src/trainer/base.py` until 2026-06-14 — three weeks after these Phase-1 runs (checkpoint mtimes: 2026-05-25). See §G. |

---

## B. Raw provenance

### B.1 Canonical Phase-1 Qwen2.5-3B `f10` full-metrics runs (all 10 methods)

All 10 live under `saves/unlearn/paper_qwen25_3b_<method>_f10_a180_fullmetrics/`:

| Method | Run directory | Checkpoints on disk | Trained to completion? |
|---|---|---|---|
| CEU | `saves/unlearn/paper_qwen25_3b_ceu_f10_a180_fullmetrics` | 0,13,26,39,52,65,78,91,104,117,120 | Yes — `global_step`=`max_steps`=120, final log entry has `train_runtime` |
| GradAscent | `saves/unlearn/paper_qwen25_3b_gradascent_f10_a180_fullmetrics` | same 11 | Yes |
| GradDiff | `saves/unlearn/paper_qwen25_3b_graddiff_f10_a180_fullmetrics` | same 11 | Yes |
| NPO | `saves/unlearn/paper_qwen25_3b_npo_f10_a180_fullmetrics` | same 11 | Yes |
| PDU | `saves/unlearn/paper_qwen25_3b_pdu_f10_a180_fullmetrics` | same 11 | Yes |
| RMU | `saves/unlearn/paper_qwen25_3b_rmu_f10_a180_fullmetrics` | same 11 | Yes |
| SatImp | `saves/unlearn/paper_qwen25_3b_satimp_f10_a180_fullmetrics` | same 11 | Yes |
| SimNPO | `saves/unlearn/paper_qwen25_3b_simnpo_f10_a180_fullmetrics` | same 11 | Yes |
| UNDIAL | `saves/unlearn/paper_qwen25_3b_undial_f10_a180_fullmetrics` | same 11 | Yes |
| WGA | `saves/unlearn/paper_qwen25_3b_wga_f10_a180_fullmetrics` | same 11 | Yes |

Each run's `.hydra/overrides.yaml` (e.g. SatImp's) confirms: `experiment=unlearn/tofu/default`, `model=Qwen2.5-3B-Instruct`, `forget_split=forget10`, `retain_split=retain90`, `trainer=<Method>`, `model.model_args.pretrained_model_name_or_path=Qwen/Qwen2.5-3B-Instruct`. Split: **TOFU forget10 / retain90** (the `f10` in the directory name is confirmed correct by the actual Hydra override, not just the folder name). Checkpoint set matches exactly the expected `0,13,26,39,52,65,78,91,104,117,120`. All 10 runs completed (`global_step == max_steps == 120` in every `trainer_state.json`, with a final `log_history` entry containing `train_runtime`/`train_loss`).

### B.2 Duplicate / noncanonical Qwen2.5-3B TOFU runs found — and why they are excluded

| Directory pattern | What it is | Why excluded |
|---|---|---|
| `saves/unlearn/tofu_qwen25_3b_{ceu,pdu,satimp,simnpo,undial,wga}_f10_a100` | Same model/split, but **alpha=100** not 180, and only 6 of the 10 methods present (no GradAscent/GradDiff/NPO/RMU) | Different forget-loss coefficient (`a100` vs `a180`); incomplete method coverage — not the run referenced by the "10 methods" claim |
| `saves/unlearn/tofu_qwen25_15b_*` | **Qwen2.5-1.5B**, not 3B (`15b` = "1.5B", not "15B") | Wrong model size entirely |
| `saves/unlearn/bestagg_qwen25_3b_{rmu,satimp,simnpo,wga}_savebest` | Later (Phase-2, 2026-06-14 to 06-17) checkpoint-selection **development** runs, only 4 of the 10 methods, using the *in-training* `Agg_proxy`/`metric_for_best_model` mechanism that did not exist during Phase-1 | Different phase, different (later, automatic) selection mechanism, incomplete method set |
| `saves/unlearn/proper_qwen25_3b_{rmu,satimp,simnpo,wga}_from_tofufull_selectionproxy_savebest` | Later scaling runs on the **full** TOFU forget set (not the `f10`/10% subset), using `Selection_proxy` (2-way, no privacy term) as `metric_for_best_model` | Different forget split (`tofufull` vs `f10`), different phase, different selection criterion |
| `saves/unlearn/paper_qwen25_7b_{satimp,simnpo,wga}_f10_a180_fullmetrics` | Same naming convention but **Qwen2.5-7B**, not 3B | Wrong model size |

This matches `thesis_cleanup_audit/EXPERIMENT_HISTORY.md` §2, which independently documents: *"scale the unlearning methods up ... and — the key methodological development of this phase — build a principled checkpoint-selection metric, since **phase 1 had none**."* The `paper_qwen25_3b_*_f10_a180_fullmetrics` directories are Phase-1; everything else above is later, out-of-scope, or the wrong model size.

### B.3 Where the raw checkpoint-level metrics actually live

For every canonical run and every checkpoint `N`:
- `saves/unlearn/paper_qwen25_3b_<method>_f10_a180_fullmetrics/checkpoint-N/evals/TOFU_SUMMARY.json` — the 12 scalar summary metrics for that checkpoint (`exact_memorization`, `extraction_strength`, `forget_Q_A_Prob`, `forget_Q_A_ROUGE`, `forget_Q_A_gibberish`, `forget_truth_ratio`, `mia_loss`, `mia_min_k`, `mia_min_k_plus_plus`, `mia_zlib`, `model_utility`, `privleak`).
- `saves/unlearn/paper_qwen25_3b_<method>_f10_a180_fullmetrics/checkpoint-N/evals/TOFU_EVAL.json` — the full per-example evaluator output these summary numbers were aggregated from (larger file, ~2MB for SatImp/ckpt-13; contains `forget_Q_A_PARA_Prob`, `retain_Q_A_ROUGE`, `wf_*`, `ra_*` per-question-set breakdowns).
- `saves/unlearn/paper_qwen25_3b_<method>_f10_a180_fullmetrics/trainer_state.json` → `log_history`, filtered to entries where `"model_utility"` is a key (the eval-log entries, interleaved with pure-training-loss entries every 5 steps) → one entry per checkpoint step, containing the **exact same 12 values** as that checkpoint's `TOFU_SUMMARY.json`.

**Verified byte-for-byte identity**: for SatImp checkpoint-0 and checkpoint-13, every one of the 12 fields in `checkpoint-N/evals/TOFU_SUMMARY.json` is numerically identical (to full float precision, e.g. `exact_memorization: 0.6156122466176748` at ckpt-13 in both files) to the corresponding `log_history` entry at `step: N` in `trainer_state.json`. This means `trainer_state.json`'s `log_history` is populated directly from the same evaluator output as the per-checkpoint summary files — they are the same raw source, not independently-derived numbers. The reconstruction in §C/§D reads from `trainer_state.json` (one file per run, faster to parse than 11 separate `TOFU_SUMMARY.json` files); this is evidenced to be equivalent to reading the per-checkpoint files directly.

`best_metric`, `best_global_step`, `best_model_checkpoint` are `null` in every one of the 10 runs' `trainer_state.json` — HF Trainer's own `load_best_model_at_end` bookkeeping was never engaged for these runs (see §G).

---

## C. SatImp checkpoint trajectory (Qwen2.5-3B, `f10`, alpha=180)

Source: `saves/unlearn/paper_qwen25_3b_satimp_f10_a180_fullmetrics/trainer_state.json`, `log_history` entries with `model_utility` present. `MU0` (baseline model utility used for `Util` scaling) = `model_utility` at checkpoint-0 = **0.26346992759504356**, read from the *first* eval-metrics entry the trainer logs (see §E for why checkpoint-0's value is the one used as the baseline).

| checkpoint | Mem | Priv | Util | Agg |
|---:|---:|---:|---:|---:|
| 0 (pre-unlearning) | 0.5383006394 | 0.2807792963 | 0.9506282498 | 0.4635961127 |
| 13 | 0.4667640824 | 0.3302183490 | 0.9646835049 | **0.4833004670** |
| 26 | 0.4495607006 | 0.3098420787 | 0.9601513105 | 0.4620113605 |
| 39 | 0.4439042395 | 0.3190451886 | 0.9607902751 | 0.4667153966 |
| 52 | 0.4425596195 | 0.3186422651 | 0.9592681598 | 0.4658125019 |
| 65 | 0.4408065033 | 0.3204900114 | 0.9653186790 | 0.4669465322 |
| 78 | 0.4416320515 | 0.3184562834 | 0.9591306529 | 0.4653263853 |
| 91 | 0.4405773176 | 0.3190226948 | 0.9619878234 | 0.4655611535 |
| 104 | 0.4405683268 | 0.3204617916 | 0.9622826012 | 0.4666001352 |
| 117 | 0.4403420871 | 0.3203972973 | 0.9627192249 | 0.4665041417 |
| 120 | 0.4406307190 | 0.3208569143 | 0.9618956075 | 0.4668721534 |

`argmax(Agg)` **among trained checkpoints (excluding the untrained checkpoint-0 baseline) = checkpoint-13**, Agg = 0.4833004670.

If checkpoint-0 were included in the candidate pool, it would score Agg=0.4636 — lower than checkpoint-13, so it does not change the argmax for SatImp specifically (it does for 5 of the other 9 methods — see §D, §H).

**Comparison to the old claim** (best=ckpt-13, Agg≈0.4833004670, Mem≈0.4667640824, Priv≈0.3302183490, Util≈0.9646835049):

**EXACT MATCH to all 10 significant figures given.** Independently recomputed from raw `TOFU_SUMMARY.json`/`trainer_state.json` values and the formula in `src/trainer/base.py` (§E), with no numbers taken from any existing spreadsheet/CSV/PPTX.

**Was this selection automatic or post-hoc?** `trainer_state.json`'s `best_metric`/`best_global_step`/`best_model_checkpoint` are all `null` for this run — Hugging Face `Trainer`'s built-in best-checkpoint bookkeeping never ran. No `Mem_proxy`/`Agg_proxy`/`Privacy_proxy`/`Utility_proxy` key appears anywhere in this run's `log_history` (only the 12 raw TOFU metrics + `epoch`/`step` do). The `add_proxy_scores`/`Agg_proxy` code did not exist in `src/trainer/base.py` at all until **2026-06-14** (`thesis_cleanup_audit/CHECKPOINT_SELECTION_PATCH.md` §7, confirmed by `.bak_before_agg_proxy` file mtime), whereas this run's checkpoints were written **2026-05-25** (`stat` on `checkpoint-13/evals/TOFU_SUMMARY.json` → `2026-05-25 02:07:35`). **Conclusion: checkpoint-13 was NOT selected automatically during training. Agg was computed post-hoc, after the fact, from the raw saved per-checkpoint metrics, using a formula that (as currently written in the working tree) is bit-identical to whatever formula produced this specific number — but the formula itself did not exist in the codebase at the time training ran.**

---

## D. All-10-method table (Qwen2.5-3B, `f10`, alpha=180)

Best checkpoint per method by `argmax(Agg)`, **excluding checkpoint-0** from the candidate pool (see §H for why this exclusion is necessary and how strongly it is evidenced):

| Rank | Method | Best checkpoint | Agg | Mem | Priv | Util | Matches old claim? |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | SatImp | 13 | 0.483300 | 0.466764 | 0.330218 | 0.964684 | Exact |
| 2 | SimNPO | 13 | 0.482978 | 0.466625 | 0.329862 | 0.964463 | Exact |
| 3 | WGA | 13 | 0.482425 | 0.466681 | 0.328736 | 0.967273 | Exact |
| 4 | PDU | 13 | 0.470808 | 0.484681 | 0.304913 | 0.971645 | Exact |
| 5 | RMU | 52 | 0.464969 | 0.548421 | 0.280064 | 0.945173 | Exact |
| 6 | GradDiff | 13 | 0.445960 | 0.536793 | 0.262285 | 0.951019 | Exact |
| 7 | UNDIAL | 13 | 0.442914 | 0.553247 | 0.266788 | 0.821338 | Exact |
| 8 | CEU | 13 | 0.437844 | 0.516308 | 0.264593 | 0.880639 | Exact |
| 9 | NPO | 13 | 0.389126 | 0.559833 | 0.265160 | 0.464677 | Exact |
| 10 | GradAscent | 13 | 0.188059 | 0.607720 | 0.291440 | 0.091948 | Exact |

All 10 Agg values, all 10 best-checkpoint steps, and (spot-checked for the top 5) all Mem/Priv/Util components match the existing claim to 6 decimal places.

**Part 8 flag — method-selection ≠ checkpoint-selection ranking**: the four methods later carried forward to MUSE/scaling (**RMU, WGA, SatImp, SimNPO**) are **not** the top 4 rows of this table. **PDU ranks 4th (0.470808), strictly above RMU which ranks 5th (0.464969)**, yet PDU was not carried forward while RMU was. Do not describe the four carried-forward methods as "the top 4 Qwen2.5-3B methods by Agg" — that claim is directly contradicted by this table. What the repository *can* prove about the actual reason: `thesis_cleanup_audit/EXPERIMENT_HISTORY.md` §2 and `FINAL_DEFENSE_SLIDE_BLUEPRINT.md` (Slide 6) both independently describe the four-method set as surviving a **separate, later, larger-scale evaluation phase** (Llama-3.2-1B/Qwen2.5-1.5B/Qwen2.5-3B → Llama-3.1-8B/Qwen2.5-7B → Qwen2.5-14B, on the full TOFU forget set), not as a direct readout of this Phase-1 Qwen2.5-3B Agg ranking. **This repository does not contain an explicit, single decision artifact ("we picked these 4 because...") — the precise historical selection rule for going from 10 methods to 4 is not fully reconstructable from raw data alone; the best evidence is the scaling-phase run manifests plus the blueprint's own framing. Do not invent a cleaner rule than that.**

---

## E. Formula verification

All four proxy metrics are computed by `add_proxy_scores()` in `src/trainer/base.py:47-119` (plus helpers `_harmonic_mean` at line 14, `_get_metric` at line 28, `_set_proxy_metric` at line 39).

```python
def _harmonic_mean(values, eps=1e-12):          # base.py:14
    clean_values = [max(float(v), eps) for v in values]   # any None -> whole call returns None
    return len(clean_values) / sum(1.0 / v for v in clean_values)

# base.py:77-105
mem_proxy = _harmonic_mean([1-extraction_strength, 1-exact_memorization,
                             1-forget_q_a_prob, 1-forget_truth_ratio])          # Mem
privacy_proxy = _harmonic_mean([mia_loss, mia_zlib, mia_min_k, mia_min_k_plus_plus])  # Priv
scaled_model_utility = min(model_utility / baseline_model_utility, 1.0)   # if baseline known, else raw
utility_proxy = _harmonic_mean([scaled_model_utility, forget_q_a_gibberish])    # Util
agg_proxy = _harmonic_mean([mem_proxy, privacy_proxy, utility_proxy])           # Agg
selection_proxy = _harmonic_mean([mem_proxy, utility_proxy])                   # 2-way variant, no Priv
```

This exactly matches the historical description:
- `Mem = HM(1-ES, 1-EM, 1-Prob, 1-TruthRatio)` — **confirmed**, field-for-field (`extraction_strength`→ES, `exact_memorization`→EM, `forget_Q_A_Prob`→Prob, `forget_truth_ratio`→TruthRatio).
- `Priv = HM(MIA-Loss, ZLib, MinK, MinK++)` — **confirmed**, field-for-field (`mia_loss`, `mia_zlib`, `mia_min_k`, `mia_min_k_plus_plus`). This is the OpenUnlearning membership-inference/leakage proxy, computed entirely from the TOFU evaluator's MIA scores — it has no relationship to PrivacyLens or PersistBench contextual privacy, which are separate evaluation pipelines (`outputs/privacylens_*`, `thesis/analysis/...`) not touched anywhere in this formula.
- `Util = HM(min(MU/MU0, 1), Fluency)` — **confirmed**: `model_utility`→MU, `forget_Q_A_gibberish`→Fluency (a gibberish-detector score, higher = more fluent), `MU0` = `baseline_model_utility`, clipped at 1.0 via `min(...)`. **`MU0` is set once per training run, from whichever evaluation is logged first** (`base.py:190-194`: `if self._proxy_baseline_model_utility is None and model_utility is not None: self._proxy_baseline_model_utility = model_utility`). Since checkpoint-0 (the pre-unlearning eval) is always logged first, **`MU0` = the pre-unlearning model's own `model_utility`**, fixed for the whole run — it is not recomputed or re-scaled at every checkpoint. Epsilon handling: every harmonic-mean input is floored at `eps=1e-12` (line 20) before averaging, so a literal 0 input does not raise a division error; no other zero/negative handling exists (values are assumed already in a sane range from the evaluator).
- `Agg = HM(Mem, Priv, Util)` — **confirmed**, exactly as described, 3-way harmonic mean of the three proxies above.

**Formula version history** (from `git diff`/`git log` + `thesis_cleanup_audit/CHECKPOINT_SELECTION_PATCH.md`, independently corroborated):
- `git log --oneline -- src/trainer/base.py` shows only 4 commits, none of which introduce `add_proxy_scores`/`_harmonic_mean`/`Mem_proxy`/etc. `git diff HEAD -- src/trainer/base.py` shows this entire block (147 lines) as **uncommitted, working-tree-only** additions on top of the last commit (`a456aa2`).
- File-mtime evidence (`src/trainer/base.py.bak_before_agg_proxy`, dated 2026-06-14 13:01) shows the `Agg_proxy`/`Mem_proxy`/`Privacy_proxy`/`Utility_proxy`/`Selection_proxy` code was **added on 2026-06-14** — i.e., **after** the Phase-1 Qwen2.5-3B 10-method sweep being verified here (checkpoint mtimes 2026-05-25).
- A second, unrelated addition (`best_agg`, MUSE-specific, `base.py:163-189`) was added later the same day as a second edit (`.bak_before_bestagg_patch`, also 2026-07-06 per the audit — this is a separate metric for MUSE runs and plays no role in this TOFU verification).

**Which version applies to the Phase-1 results being verified**: since the formula did not exist yet when Phase-1 ran, there is no "version in effect at the time" — the numbers in the old claim table must have been produced by applying **some** version of this formula to the already-saved raw metrics, after the fact. The current, uncommitted `add_proxy_scores()` reproduces the old claim's SatImp numbers to 10 significant figures and all 10 methods' numbers to 6 decimal places (§C, §D), so whatever formula was actually used to build the original claim is either this exact function or numerically identical to it. The formula itself is fully verified; its *application history* (was it run via a one-off script, a notebook, manually) is not reconstructable from the repository — no such script survives on disk (see §H).

---

## F. Summary-file comparison

**None of the four named summary artifacts exist anywhere in this repository or in the user's home directory on this machine:**
- `last_week_all_methods_results.xlsx` — not found
- `top3_trajectory_scores.csv` — not found
- `last_week_all_methods_best_by_agg.csv` — not found
- any `UnlearningResults*.pptx` — not found (a `find` for all `*.xlsx`/`*.pptx` in the repository turned up exactly one PowerPoint file total: `thesis/analysis/judge_robustness/supervisor_update_2026-09-16/gemma_judge_validation_supervisor_update.pptx`, which is unrelated — a judge-robustness supervisor update, not a TOFU checkpoint results deck)
- A "July midterm presentation" was searched for (`find -iname "*midterm*"`) and not found either.

**This cross-check (§F / Part 6) cannot be performed** — there is nothing in the repository to compare the reconstruction against except the numeric claims already supplied in the task prompt, which (per §C/§D) match the independent reconstruction exactly. If these spreadsheet/deck files exist, they are not on this machine/repository; they would need to be supplied directly for a real file-level cross-check. Nothing here should be read as "the spreadsheets agree" — only that the *numbers you already believe are in them* agree with the raw-artifact reconstruction.

One genuine, repository-internal selection-criterion distinction was found and is worth stating precisely: `src/trainer/base.py` defines **both** `Agg_proxy` (3-way, includes `Privacy_proxy`) and `Selection_proxy` (2-way, `HM(Mem, Util)` only, **no privacy/MIA term**). Later scaling-phase runs (`proper_*_from_tofufull_selectionproxy_savebest`, `run_llama31_8b_tofufull_unlearn_4methods_clean.sh`, `run_qwen_tofufull_unlearn_best_array.sh`) used `eval_Selection_proxy` as `metric_for_best_model`, while others (`run_4models_4methods_save_bestagg.sh`, `_aggproxy` runs) used `eval_Agg_proxy`. **The table in §D above is unambiguously the `Agg` (3-way, with privacy) version, not `Selection` — this matches the task's stated formula (`Agg = HM(Mem, Priv, Util)`) and the old claim's own Priv column values, which could not be reproduced under `Selection_proxy` (that variant has no privacy term at all).** Do not mix the two: if a different table elsewhere in your materials was built with `Selection_proxy`, it will show different (higher, since it's a 2-way not 3-way HM and structurally different) numbers for the same checkpoints, and is not directly comparable to this one.

---

## G. Historical-methodology wording

Evidence-based answers:

1. **Was a best checkpoint automatically selected during the Phase-1 sweep?** No. Every one of the 10 runs has `best_metric`/`best_global_step`/`best_model_checkpoint` = `null` in `trainer_state.json`. HF Trainer's `load_best_model_at_end`/`metric_for_best_model` machinery was not engaged.
2. **Were checkpoints merely saved at intervals and evaluated later?** Yes — checkpoints were saved every 13 steps (0,13,26,...,120) per the fixed `save_steps`/eval cadence visible in `trainer_state.json`, each evaluated in-line during training by the custom `FinetuneTrainer.evaluate()` (writing `checkpoint-N/evals/TOFU_SUMMARY.json` + `TOFU_EVAL.json`, and logging the same values into `trainer_state.json`'s `log_history`), but no aggregate "which one is best" score was computed or used to pick a winner at training time.
3. **When was `Agg_proxy` introduced?** 2026-06-14 (`src/trainer/base.py.bak_before_agg_proxy` mtime; `thesis_cleanup_audit/CHECKPOINT_SELECTION_PATCH.md` §7), roughly three weeks after this Phase-1 Qwen2.5-3B sweep (checkpoint mtimes 2026-05-25).
4. **When was `Selection_proxy` introduced?** Same code addition, same day (2026-06-14) — both are written by the same `add_proxy_scores()` function added in one commit-equivalent edit.
5. **What exactly was used for the table being verified?** The raw per-checkpoint TOFU metrics saved during Phase-1 training (`TOFU_SUMMARY.json`/`trainer_state.json`), with the `Agg = HM(Mem, Priv, Util)` formula (as it exists in the current, uncommitted `src/trainer/base.py`) applied **after the fact** to those saved numbers — not computed during training, and not read out of any pre-existing summary spreadsheet (none could be found, §F).
6. **Is it accurate to say "For every method I evaluated its saved checkpoints and selected the checkpoint with the highest aggregate score"?** **Mostly, with one necessary addition**: this is accurate only if you also say the pre-unlearning checkpoint (step 0) was excluded from consideration — otherwise the sentence is false for 5 of the 10 methods (CEU, GradAscent, GradDiff, NPO, UNDIAL), where the untrained baseline checkpoint has a higher raw Agg than every trained checkpoint (see §H).
7. **More accurate wording**: *"For each method, checkpoints were saved and evaluated on TOFU at fixed intervals during training; no automatic best-checkpoint mechanism existed yet at this stage of the project. I later defined an aggregate score, Agg = harmonic-mean(Mem, Priv, Util), and applied it retrospectively to the saved per-checkpoint metrics to select the best **trained** checkpoint for each method, excluding the pre-unlearning baseline checkpoint from consideration. This post-hoc, formula-based selection mechanism was only built into the training loop itself later, starting with the model/method scaling phase."* This is the safe, historically precise sentence — it does not claim more rigor than the repository can prove, and it correctly flags that Phase-1 selection was retrospective, not live.

---

## H. Discrepancies / uncertainties

1. **Checkpoint-0 exclusion is inferred, not documented.** No script, README, or manifest anywhere in the repository states "exclude step 0 from checkpoint-selection candidates" in those words. This exclusion is inferred purely from numeric necessity: including checkpoint-0 changes the argmax (and thus the claimed best-checkpoint/Agg value) for 5 of the 10 methods, which would contradict the given claim table; excluding it reproduces the claim exactly for all 10 methods with no exceptions. This is about as strong as circumstantial numeric evidence gets, but it is still an inference, not a documented rule — say so if asked directly in the defense.
2. **The exact post-hoc computation process (script, notebook, or manual spreadsheet formula) that originally produced these numbers no longer exists in the repository.** The *formula* is fully verified (bit-identical output), but *how* it was run — one-off Python script, Jupyter notebook, manual Excel formula — is not recoverable. No such script was found under `thesis_cleanup_audit/`, `research_history/`, or `thesis/scripts/`.
3. **The four-method scaling decision (RMU/WGA/SatImp/SimNPO) is not fully reconstructable as a single explicit rule.** The repository proves these four went through a further scaling phase (§D) and proves PDU numerically outranks RMU on this specific Qwen2.5-3B/Agg table, but there is no single artifact stating the precise decision criterion used to narrow from 10 to 4 (or why PDU specifically was dropped despite ranking above RMU here). Do not present a cleaner story than this.
4. **Summary-file cross-check (Part 6) could not be run at all** — none of the four named artifacts exist in the repository or home directory (§F). All comparisons in this report are reconstruction-vs-stated-claim, not reconstruction-vs-actual-spreadsheet-file.
5. **`add_proxy_scores()` is currently uncommitted, working-tree-only code** (confirmed via `git diff HEAD -- src/trainer/base.py`, `git log` showing none of the last 4 commits touch this code). This does not affect the numeric verification (the formula reproduces the claimed numbers exactly regardless of commit status), but if this branch's uncommitted changes are ever lost, the formula's *definition* — as opposed to the numbers already computed from it — would no longer be recoverable from `src/trainer/base.py` alone; it would still be recoverable from `thesis_cleanup_audit/CHECKPOINT_SELECTION_PATCH.md`, which independently transcribes the same code.

---

# FINAL SLIDE-SAFE NUMBERS

Independently verified from raw repository artifacts (`saves/unlearn/paper_qwen25_3b_<method>_f10_a180_fullmetrics/trainer_state.json` + `checkpoint-N/evals/TOFU_SUMMARY.json`) and the exact `Agg = HM(Mem, Priv, Util)` formula in `src/trainer/base.py`. Best-checkpoint selection excludes the pre-unlearning checkpoint-0 baseline (see §H.1).

**Qwen2.5-3B + SatImp (Slide 1 example):**
- Best checkpoint: **checkpoint-13**
- Agg = **0.4833004670**, Mem = **0.4667640824**, Priv = **0.3302183490**, Util = **0.9646835049**

**All 10 Qwen2.5-3B TOFU methods, ranked by Agg (Slide 2):**

| Rank | Method | Best ckpt | Agg | Mem | Priv | Util |
|---:|---|---:|---:|---:|---:|---:|
| 1 | SatImp | 13 | 0.483300 | 0.466764 | 0.330218 | 0.964684 |
| 2 | SimNPO | 13 | 0.482978 | 0.466625 | 0.329862 | 0.964463 |
| 3 | WGA | 13 | 0.482425 | 0.466681 | 0.328736 | 0.967273 |
| 4 | PDU | 13 | 0.470808 | 0.484681 | 0.304913 | 0.971645 |
| 5 | RMU | 52 | 0.464969 | 0.548421 | 0.280064 | 0.945173 |
| 6 | GradDiff | 13 | 0.445960 | 0.536793 | 0.262285 | 0.951019 |
| 7 | UNDIAL | 13 | 0.442914 | 0.553247 | 0.266788 | 0.821338 |
| 8 | CEU | 13 | 0.437844 | 0.516308 | 0.264593 | 0.880639 |
| 9 | NPO | 13 | 0.389126 | 0.559833 | 0.265160 | 0.464677 |
| 10 | GradAscent | 13 | 0.188059 | 0.607720 | 0.291440 | 0.091948 |

**Safe defense-room sentence on methodology** (§G.7): *"For each method, checkpoints were saved and evaluated on TOFU at fixed intervals; the aggregate Agg = HM(Mem, Priv, Util) score was applied retrospectively to select the best trained checkpoint per method, excluding the pre-unlearning baseline. This post-hoc selection approach predates the automatic, in-training checkpoint-selection mechanism I built for the later scaling phase."*

**Do not say**: that RMU/WGA/SatImp/SimNPO were "the top 4 Qwen2.5-3B methods by Agg" — PDU outranks RMU in this exact table (§D, §H.3).
