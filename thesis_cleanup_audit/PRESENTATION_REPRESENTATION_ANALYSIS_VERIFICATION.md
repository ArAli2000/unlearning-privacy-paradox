# Representation-Analysis Verification (Privacy Collapse–inspired sections)

Read-only forensic verification of the exploratory representation-analysis
material proposed for the thesis-defense brief. No repository files were
modified. All models/checkpoints below are Qwen2.5-7B-Instruct MUSE-News:
BASE = `saves/finetune/muse_news_qwen25_7b_instruct_target`; SatImp/SimNPO =
`saves/unlearn/muse_news_qwen25_7b_instruct_{satimp,simnpo}/checkpoint-459`
(confirmed via `mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/gpu_extraction_provenance.json`
and `mechanistic/experiments/muse_news_sycophancy_final_mechanism/EXPERIMENT_INDEX.md`).

Behavioral labels throughout this tree use `legacy_local_qwen_judge`
(`Qwen/Qwen2.5-7B-Instruct`) — **not** the canonical PersistBench/Kimi-K2
judgment — every source file states this explicitly. Say "legacy local Qwen
judge" whenever citing a PersistBench score in the defense.

---

## 1. VERIFIED claims

1. **PrivacyLens final-layer cosine ≈0.937 (SatImp) / ≈0.938 (SimNPO), "highly aligned."**
   Reconstructed independently from
   `mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/direction_norms_and_cosines.csv`,
   `dataset=privacy` rows, `state_index=28` (final layer): SatImp
   `cosine_to_base=0.9365862563846288`, SimNPO `0.9380604092632567`. Exact
   match to the claim. Method (from
   `mechanistic/privacy_collapse/README.md`): direction = `mean(h_safe) − mean(h_leaky)`
   computed independently per model (no shared/BASE-frozen direction, no PCA),
   at the last prompt token, across all 29 residual states (embedding + L1–L28).
   The reported number is the cosine between each unlearned model's own
   direction vector and BASE's, at the final state.
   **Wording constraint honored:** do not call 0.937/0.938 "unchanged" or
   "identical" — use "highly aligned." The values are also 8–9 points of
   cosine *below* the two controlled MCQ probes below (0.977, 0.964/0.962),
   so "highly aligned but the least-preserved of the three controlled
   directions" is the most precise framing.
   Layerwise curve plot: `mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/privacy_safe_minus_leaky_logit_difference.png`
   (logit-difference trajectory) and `combined_direction_alignment.png`
   (privacy + control direction-cosine curves together). The raw per-layer
   cosine table for the full curve is `direction_norms_and_cosines.csv` itself
   (rows `state_index=0..28`).

2. **MUSE-News sycophancy generation-0 transition counts.**
   SatImp: 166/15/10/9 (SAFE→SAFE / SAFE→FAILURE / FAILURE→SAFE / FAILURE→FAILURE).
   SimNPO: 169/12/8/11. Exact match to the claim. Source: computed by
   `mechanistic/privacy_collapse/persistbench_native/analyze_sycophancy.py`
   from `manifests/native_sycophancy_200_v1.json` (200 frozen rows, judge
   scores per model), written to
   `analysis/sycophancy/sycophancy_transitions.json` /
   `sycophancy_transitions.csv` and documented in
   `analysis/sycophancy/README.md` §4. Failure = judge score ≥3 (repository
   FR@K rubric; score 3 is "both-sides hedging," already counted as a
   failure even though the literal rubric label "Sycophantic" is reserved for
   score 4 — worth knowing if pressed).

3. **Naturally-occurring cross-domain mixed-outcome counts BASE=0, SatImp=5, SimNPO=2.**
   Exact match. This is the *cross-domain* mixed-outcome count (a model/prompt
   with at least one valid safe score and one valid failure score across
   generation indices 0–2), from
   `mechanistic/privacy_collapse/persistbench_native/analysis/native_direction_inventory/README.md`
   §"Mixed-outcome inventory": Cross-domain BASE=0/194 safe/7 failure→0 mixed,
   SatImp=194 safe/1 failure→5 mixed, SimNPO=196 safe/2 failure→2 mixed. These
   are **not** privacy-safe/leaky pairs in the PrivacyLens sense — they are
   PersistBench cross-domain safe-vs-failure judge-score pairs, assessed for
   feasibility of a native (real-generation) direction comparison, not for a
   direction that was ever actually computed. State this distinction if used.

4. **Controlled sycophancy MCQ probe: ~0.96 alignment, sign flip on label swap, label/token confound.**
   Verified in full from
   `mechanistic/privacy_collapse/persistbench_sycophancy_mcq/analysis/README.md`.
   Exact experiment: 50 PersistBench-sycophancy rows, forced A/B MCQ answer
   ("should stored beliefs bias the answer?"), final-token (L28) direction
   `mean(h_non-sycophantic − h_sycophantic)`. Original label order
   (`A=Yes/B=No`): BASE→SatImp cosine **0.9638** [0.9566, 0.9678], BASE→SimNPO
   **0.9622** [0.9554, 0.9663] — the "looked promising ~0.96" result. After
   swapping labels (`A=No/B=Yes`): cosine between the **original-order** and
   **swapped-order** direction (same model) is **anti-aligned**: BASE −0.647,
   SatImp −0.555, SimNPO −0.557. "Flipped sign" is literally correct — this is
   a genuine sign reversal, not a rounding artifact. All models chose the
   semantically-correct (non-sycophantic) answer 50/50 in both orders (100%
   accuracy both ways), so the *behavior* is robust; only the *raw endpoint
   vector* is lexically confounded by which token (A vs B) encodes "safe."
   **Recommendation: backup slide only, not main deck.** It is a genuine and
   interesting confound finding, but its main use is methodological (a
   cautionary tale about answer-token directions), not a positive result to
   headline.

5. **PersistBench cross-domain MCQ ~0.977 / sycophancy MCQ ~0.964/0.962 / PrivacyLens ~0.937/0.938 ordering.**
   Confirmed in the same README (§"Comparison with controlled probes"): this
   is a real, monotonic ordering across three independently-computed
   controlled directions, from least to most representation drift:
   cross-domain MCQ > sycophancy MCQ > PrivacyLens. Safe to cite as a ranked
   comparison, not just three isolated numbers.

---

## 2. VERIFIED WITH CAVEATS

6. **Sycophancy failure-contrast layer range "L24–28."**
   Supported, with a sharper peak than the rounded range suggests. From
   `mechanistic/privacy_collapse/persistbench_native/analysis/sycophancy/README.md`
   §5 (source: `sycophancy_layer_metrics.csv`, `sycophancy_model_change.json`):
   failure-contrast norm peaks at **L27 (18.96) for SatImp** and **L28 (20.04)
   for SimNPO** — both inside L24–28, and the top-5 layers by contrast norm
   are exactly L24–L28 for both methods (`analysis_summary.json.top_layers`).
   **Caveat:** 95% bootstrap CIs at the peak are wide relative to the point
   estimate (SatImp L27: [4.10, 16.30]; SimNPO L28: [1.00, 20.40]) — the
   *location* of the peak (L24–28) is well-supported, but the *magnitude* has
   substantial uncertainty given N=15/N=12 failure-transition examples. Say
   "diverges most strongly in late layers, L24–28, peaking around L27–L28,"
   not a single precise layer.
   **Descriptive vs. causal:** explicitly descriptive/correlational — the
   README states this in as many words ("association, not evidence that the
   contrast vector causally produces sycophancy"). Confirmed, as expected.
   Plots: `layerwise_model_change_norm.png` (raw generating script:
   `analyze_sycophancy.py::save_plot`, y-axis = mean delta norm
   `‖h_unlearned − h_BASE‖` per group, x-axis = state index 0–28, groups =
   SatImp/SimNPO × {non→non, non→syc}), `group_mean_cosine.png` (y-axis =
   cosine between the two groups' mean deltas), `sycophancy_failure_contrast_norm.png`
   (y-axis = norm of `mean(non→syc delta) − mean(non→non delta)`). Data
   source for all three: the same 200-row frozen manifest and prompt-end
   tensors (`[200, 29, 3584]` per model), N(non→non)=166 SatImp/169 SimNPO,
   N(non→syc)=15 SatImp/12 SimNPO — sample sizes above the repo's own N≥5
   "do not proceed" threshold, but still small for a bootstrap CI.

7. **Cross-domain vs. sycophancy: "similar late-layer region, not mirror images."**
   Supported, partially quantitatively stronger than the pasted framing.
   Source: `analysis/sycophancy/README.md` §6 + `cross_domain_comparison.json`.
   Top-5 layers overlap **5/5** for both methods (both exactly L24–L28),
   profile Pearson correlation SatImp **0.986**, SimNPO **0.969** — this is a
   very strong "same late-layer region" result, stronger than a qualitative
   "roughly involves L24-28" claim. Cosine between the cross-domain-fixed mean
   delta and the sycophancy-failure mean delta *declines* across L24→L28:
   SatImp 0.713→0.540, SimNPO 0.655→0.464 — positive throughout, confirming
   "not opposite," but drifting apart at the very last layers rather than
   staying flat. **Caveat, already flagged in-repo:** the cross-domain
   "fixed" group is small — **SatImp N=6, SimNPO N=4** — below the N≥5
   threshold for SimNPO specifically, so the README itself calls this
   comparison "exploratory even though the sycophancy groups themselves
   exceed N=5." Cite the SimNPO N=4 caveat explicitly if this plot appears.
   Plot: `cross_domain_sycophancy_layer_comparison.png` (y-axis = layer-wise
   vector norm, two series per method: syc-failure-contrast norm and
   cross-fixed mean-delta norm — a profile-shape comparison, not a
   cosine-similarity plot).

8. **Teacher-forced BASE↔unlearned activation patching "strongest around L21–27."**
   **Partially supported — the "strongest" framing needs softening.** Source:
   `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit/CLEAN_RERUN_REPORT.md`
   and `THESIS_RESULTS_CHEATSHEET.md`. Exact numbers on the clean,
   manually-audited 10-case set (SatImp n=6, SimNPO n=4 genuine
   HIGH_CONFIDENCE_FAILURE cases — see item 10 below): forward patch
   (donor=BASE→recipient=unlearned), **L21-27**: SatImp +0.138 CI[0.119,0.158]
   6/6 in predicted direction, SimNPO +0.111 CI[0.077,0.143] 4/4; reverse
   patch mirrors with opposite sign. The report states explicitly:
   **"L14-20 comparable magnitude to L21-27 in both directions."** So L21-27
   is a real, well-supported effect region, but it is not shown to be
   *stronger* than L14-20 — both bands show comparable causal shifts at the
   teacher-forced level. Say "a real causal effect is present across L14-27,
   including L21-27" rather than "strongest at L21-27."

9. **Memory/context patching (Experiment B) strongest at "L14-20."**
   Verified as stated. Source:
   `mechanistic/experiments/muse_news_sycophancy_final_mechanism/EXPERIMENT_B_MEMORY_INTEGRATION.md`
   + cheatsheet: injecting a WITH_MEMORY hidden state into a NO_MEMORY context
   shifts toward the sycophantic response "most consistently at L14-20" (BASE
   10/10, SatImp 5/6, SimNPO 2/4 — small n, especially SimNPO). **Major
   caveat already documented in-repo and essential for the defense:** "the
   tested channel is not shown to be unlearning-specific: BASE exhibits it at
   least as strongly as SatImp and more consistently than SimNPO." This
   experiment shows memory-context integration is causal, generically — it
   does **not** show unlearning created or amplified this pathway. Must be
   stated with this caveat, not as "unlearning changed memory integration."

10. **Free-generation repair, tentative, "around L14-20."**
    Verified as stated, with a strong existence-proof-only caveat. Source:
    `EXPERIMENT_1_RESULTS.md` + cheatsheet: only 3/6 SatImp and 0/4 SimNPO
    treatment cases even reproduce as a fresh judge-scored failure under
    greedy regeneration; of those, exactly **one** case (`aa71a70f`, SatImp)
    is repaired by forward-patching at L14-20, confirmed by both judges
    (legacy-Qwen and Gemma-3-12b-it, 59% inter-judge agreement overall). This
    is one clean bidirectional example, not a population-level effect — say
    "an existence-proof of causal repair in free generation, in one case, at
    L14-20" and nothing stronger.

---

## 3. Claims that need re-framing or should be dropped from the main deck

11. **The MCQ label-swap experiment (item 4) → backup slide only**, as stated
    above — it is a real and useful confound finding but reads as a negative
    methodological result, better suited to a "we checked and ruled this out"
    backup slide than the main narrative.

12. **The old, pre-audit "Phase 9" causal-patching selection must never be
    cited.** `mechanistic/experiments/muse_news_sycophancy_paradox/audit/manual_transition_audit.md`
    documents that the *original* "6 strongest transitions per method"
    selection (by raw judge-score jump, used in an earlier patching pass) was
    only **2/6 HIGH_CONFIDENCE_FAILURE per method** — 3/6 were
    LIKELY_JUDGE_NOISE, 1/6 AMBIGUOUS, for both SatImp and SimNPO. The
    **current, canonical** clean-audit selection (SatImp n=6, SimNPO n=4,
    used in items 8–10 above) is the HIGH_CONFIDENCE_FAILURE-only subset from
    the full 27-candidate manual audit, i.e. this problem has already been
    fixed in the numbers you'd actually cite — but if any *older* slide,
    spreadsheet, or draft references a "6 strongest" or "Phase 9" patching
    result, verify it is citing `activation_patching_clean_audit/`, not the
    original uncleaned run, before using it.

13. **Synthetic/generated safe-vs-leaky PersistBench pairs — never reached
    the SatImp/SimNPO comparison stage; consistent with "abandoned," but the
    repo does not use that word.** Location:
    `mechanistic/privacy_collapse/persistbench/` (the "PersistBench
    paired-response pilot"). Evidence of confound-driven attrition: manual
    adjudication of 27 candidate cross-domain PersistBench rows
    (`annotations/target_memory_human_adjudication_v1.md`) accepted a clean
    target memory for only **10/27**, found **no clean target for 5/27**, and
    **excluded 12/27 outright** — the dominant rejection reason recorded
    per-row is that every candidate "target" memory has high lexical/semantic
    overlap with the query domain itself (a content confound, exactly as
    claimed), making it impossible to cleanly isolate a privacy-only safe/leaky
    contrast. The pipeline's own README states it "does not run BASE, SatImp,
    or SimNPO inference" — the only executed runs are 3-example stress tests
    against a substitute local Mistral-7B-Instruct-v0.3 generator
    (`outputs/local_mistral_{simple,target,minimal_edit,matched_rewrite}_stress_v1/`),
    one of which (`minimal_edit_stress_v1`) shows 2/3 examples failing
    structural validation outright. **No full-scale synthetic safe/leaky
    dataset was ever generated against the actual unlearned models.**
    Say: "a synthetic matched-pair construction was piloted and a 27-example
    manual review found the great majority of candidate target memories too
    entangled with query content to isolate a clean privacy contrast; the
    approach was not scaled to the target models" — this is defensible from
    the repo. Do **not** say "abandoned because of length confounds" —
    length/word-ratio validation (`pair_validation.py`, 0.85–1.15 ratio check)
    exists and is part of the *design*, but the actual documented failure
    mode in the adjudication record is content/topic overlap, not length.

---

## 4. Exact graph paths (canonical, all under `mechanistic/`)

| Figure | Path |
|---|---|
| PrivacyLens logit-difference trajectory | `outputs/privacy_collapse_muse_news_qwen25_7b/privacy_safe_minus_leaky_logit_difference.png` |
| Control (commonsense) logit-difference trajectory | `outputs/privacy_collapse_muse_news_qwen25_7b/control_correct_minus_incorrect_logit_difference.png` |
| Combined privacy+control direction alignment | `outputs/privacy_collapse_muse_news_qwen25_7b/combined_direction_alignment.png` |
| Sycophancy failure-contrast norm | `privacy_collapse/persistbench_native/analysis/sycophancy/sycophancy_failure_contrast_norm.png` |
| Layerwise model-change norm | `privacy_collapse/persistbench_native/analysis/sycophancy/layerwise_model_change_norm.png` |
| Group-mean cosine (sycophancy) | `privacy_collapse/persistbench_native/analysis/sycophancy/group_mean_cosine.png` |
| Cross-domain vs. sycophancy layer comparison | `privacy_collapse/persistbench_native/analysis/sycophancy/cross_domain_sycophancy_layer_comparison.png` |
| Controlled MCQ direction comparison | `privacy_collapse/persistbench_sycophancy_mcq/plots/controlled_probe_direction_comparison.png` |
| MCQ safe-minus-syc logit | `privacy_collapse/persistbench_sycophancy_mcq/plots/sycophancy_mcq_safe_minus_syc_logit.png` |
| MCQ direction cosine (orig vs. swapped) | `privacy_collapse/persistbench_sycophancy_mcq/plots/sycophancy_mcq_direction_cosine.png` |
| Teacher-forced divergence by layer | `experiments/muse_news_sycophancy_paradox/plots/teacher_forced_divergence_by_layer.png` |
| Activation-patching score by layer range | `experiments/muse_news_sycophancy_paradox/plots/activation_patching_score_by_range.png` |
| Memory-influence norm / cosine-diff by layer | `experiments/muse_news_sycophancy_paradox/plots/memory_influence_norm_by_layer.png`, `memory_influence_cosine_diff_by_layer.png` |

## 5. Exact source data paths

- PrivacyLens: `outputs/privacy_collapse_muse_news_qwen25_7b/direction_norms_and_cosines.csv`, `logit_lens_summary.csv`, `logit_lens_per_example_all_models.csv`.
- Sycophancy transitions/model-change: `privacy_collapse/persistbench_native/analysis/sycophancy/{sycophancy_transitions.json,.csv, sycophancy_layer_metrics.csv, sycophancy_model_change.json, cross_domain_comparison.json, analysis_summary.json}`.
- Native-direction feasibility (item 3): `privacy_collapse/persistbench_native/analysis/native_direction_inventory/{mixed_outcome_counts.json, native_direction_feasibility.json, response_pair_confound_statistics.csv}`.
- MCQ probe: `privacy_collapse/persistbench_sycophancy_mcq/analysis/{behavioral_summary.json, layer_metrics.csv, bootstrap_intervals.csv, mcq_readout_per_example.csv}`.
- Manual audit: `experiments/muse_news_sycophancy_paradox/audit/{manual_transition_audit.csv,.md, all_27_full_text.json}`, clean selection `experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit/clean_selection.{json,md}`.
- Causal patching: `experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit/{CLEAN_RERUN_REPORT.md, clean_per_example_shifts.csv, clean_activation_patching_summary.csv}`.
- Experiment B: `experiments/muse_news_sycophancy_final_mechanism/expB_memory/{expB_scores.csv, expB_provenance.json}`.
- Experiment 1 (free-gen): `experiments/muse_news_sycophancy_final_mechanism/exp1_analysis/{exp1_summary.json, exp1_transition_rows.csv}`.

## 6. Exact scripts

- `mechanistic/privacy_collapse/prepare_manifest.py`, `extract_pilot.py`, `analyze_pilot.py` (PrivacyLens direction/logit-lens pipeline).
- `mechanistic/privacy_collapse/persistbench_native/analyze_sycophancy.py` (sycophancy transitions, model-change bootstrap, all 3 sycophancy plots + cross-domain comparison — full source reviewed in full above).
- `mechanistic/privacy_collapse/persistbench_native/analysis/native_direction_inventory/build_inventory.py` (mixed-outcome feasibility counts).
- `mechanistic/privacy_collapse/persistbench_sycophancy_mcq/{extract.py, analyze.py, plot_recognition.py}` (controlled MCQ probe, label swap).
- `mechanistic/privacy_collapse/persistbench/pair_validation.py`, `pipeline.py` (synthetic pair design/validation, never scaled to target models).
- `mechanistic/experiments/muse_news_sycophancy_paradox/{run_activation_patching.py, analyze_activation_patching.py, analyze_memory_influence.py, analyze_teacher_forced_layer_logprobs.py, build_transition_manifest.py}`.
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit/{build_clean_selection.py, run_activation_patching_clean.py, analyze_clean_patching.py}`.
- `mechanistic/experiments/muse_news_sycophancy_final_mechanism/{run_exp1_generate.py, run_exp1_qwen_judge.py, expB_memory/run_expB_memory_patch.py}`.

## 7. Exact sample sizes (all confirmed above; collected here for reference)

| Group | N |
|---|---:|
| Sycophancy population (per model) | 200 |
| Sycophancy non→non (SatImp / SimNPO) | 166 / 169 |
| Sycophancy non→syc failure (SatImp / SimNPO) | 15 / 12 |
| Cross-domain population (per model) | 200 |
| Cross-domain "fixed" (failure→safe, SatImp / SimNPO) | 6 / 4 |
| Manual audit candidates reviewed | 27 (15 SatImp + 12 SimNPO) |
| Manual audit → HIGH_CONFIDENCE_FAILURE | 10 (6 SatImp + 4 SimNPO) → 8 unique IDs |
| Old (pre-audit) "6 strongest" per method that were actually clean | 2/6 SatImp, 2/6 SimNPO |
| MCQ probe rows | 50 |
| Free-gen Experiment 1 treatment cases reproducing as failure | 3/6 SatImp, 0/4 SimNPO |
| Synthetic pair adjudication: accepted / no-clean-target / excluded | 10 / 5 / 12 (of 27) |

---

## 8. Defense-safe wording (one paragraph per result)

- **PrivacyLens direction:** "The privacy-aware representation direction
  (mean safe-minus-leaky hidden state, final layer) remains highly aligned
  between BASE and both unlearned models — cosine 0.937 (SatImp) and 0.938
  (SimNPO) — though this is somewhat less preserved than the two controlled
  MCQ directions (0.977 cross-domain, 0.96 sycophancy)."
- **Sycophancy failure contrast:** "New generation-0 sycophancy failures are
  associated with an additional, late-layer (roughly L24–28, peaking near
  L27–L28) component of the model-change vector; this is a descriptive,
  correlational finding, not causal evidence."
- **Cross-domain/sycophancy overlap:** "Cross-domain fixes and sycophancy
  failures concentrate in the same late-layer band (L24–28, top-5 layer
  overlap 5/5, correlation ≥0.97) but are positively — not oppositely —
  related, with the SimNPO cross-domain comparison group being very small
  (n=4) and therefore exploratory."
- **Causal patching (teacher-forced):** "Patching BASE activations into the
  unlearned model, and vice versa, causally shifts the fixed-continuation
  safe/sycophantic preference in the predicted direction across both L14-20
  and L21-27, on a manually-audited, judge-noise-filtered case set."
- **Experiment B:** "Injecting memory-conditioned representations causally
  shifts preference toward the sycophantic response, most consistently at
  L14-20 — but this channel is present in BASE at least as strongly as in
  the unlearned models, so it is not shown to be an unlearning-specific
  effect."
- **Free-generation repair:** "In one manually-verified, both-judges-agreed
  case, patching at L14-20 causally repairs an actual free-generation
  sycophancy failure — an existence proof of causal repair, not a
  population-level result."
- **Synthesis:** "descriptive late-layer localization → targeted causal
  interventions → a more nuanced, multi-stage/multi-band mechanism" is a fair
  one-line summary of the research arc **if** you drop the implication that
  L21-27 is uniquely privileged (L14-20 shows comparable causal effect sizes
  throughout) and keep the Experiment B caveat (context-integration causality
  ≠ unlearning-specific causality) attached whenever it is mentioned.

---

## 9. Discrepancies / uncertainties

- The pasted claim's phrase "strongest around L21–27" for teacher-forced
  patching is the one place the repo's own numbers do not fully back the
  framing — treat as "L14-27 broadly, including L21-27" (item 8).
- No repository file uses the literal word "abandoned" for the synthetic
  safe/leaky pair pipeline; the conclusion that it was not pursued to
  completion is an inference from (a) the README's explicit statement that no
  target-model inference was run, and (b) the high adjudication rejection
  rate — both solid, but this is inference, not a quoted decision.
- The controlled-MCQ "flipped sign" finding (item 4) technically compares the
  *original-label* direction against the *swapped-label* direction (same
  model), not a single direction recomputed before/after a swap on identical
  labels — this is the correct and only way to run this test, but phrase it
  precisely as "the direction reverses when the answer-token labels are
  swapped," not "the same direction changed sign over time."
- This report does not cover MUSE-Books (which the repo states does not
  replicate the sycophancy effect) or the `benchmark_paradox/` upstream
  dataset-selection scan — both exist and are referenced as motivation but
  were out of scope for the six numbered sections requested.

---

# SLIDE-SAFE FIGURES AND INTERPRETATIONS

Safe for the **main deck**:

1. `outputs/privacy_collapse_muse_news_qwen25_7b/combined_direction_alignment.png`
   with "highly aligned" wording and the 0.937/0.938 final-layer numbers.
2. `privacy_collapse/persistbench_native/analysis/sycophancy/sycophancy_failure_contrast_norm.png`
   and `layerwise_model_change_norm.png`, captioned as descriptive/correlational,
   L24–28 with peaks at L27 (SatImp) / L28 (SimNPO).
3. `privacy_collapse/persistbench_native/analysis/sycophancy/cross_domain_sycophancy_layer_comparison.png`,
   captioned with the SatImp N=6 / SimNPO N=4 exploratory caveat.
4. `experiments/muse_news_sycophancy_paradox/plots/teacher_forced_divergence_by_layer.png`
   and `activation_patching_score_by_range.png`, captioned with both L14-20
   and L21-27 numbers (not "L21-27 strongest").
5. `experiments/muse_news_sycophancy_final_mechanism/expB_memory/expB_scores.csv`-derived
   number (L14-20, BASE 10/10, SatImp 5/6, SimNPO 2/4) with the
   not-unlearning-specific caveat attached in the same breath.
6. The one-sentence Experiment 1 existence-proof result (`aa71a70f`, SatImp, L14-20).

**Backup slide only:**

7. The controlled sycophancy MCQ label-swap/sign-flip result
   (`plots/controlled_probe_direction_comparison.png`,
   `sycophancy_mcq_direction_cosine.png`) — genuine and correct, but a
   methodological caution rather than a positive finding.

**Not for any slide (repo evidence too thin / never completed):**

8. Any specific number from the synthetic safe/leaky PersistBench pair
   pipeline (`mechanistic/privacy_collapse/persistbench/`) — it never ran
   against BASE/SatImp/SimNPO and has no completed comparison to report.
9. Any patching result attributed to the original, pre-audit "6 strongest"
   selection — only the `activation_patching_clean_audit/` numbers are safe
   to cite.
