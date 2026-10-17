# RMU MUSE-News mechanistic replication: does the SatImp/SimNPO sycophancy mechanism reproduce for RMU?

Scientific question: *if model, corpus, benchmark, and analysis pipeline are held fixed and
only the unlearning method changes from SatImp/SimNPO to RMU, does the same causal
sycophancy-associated internal-state effect reproduce?*

**Short answer: partially, and for a different underlying reason than SatImp/SimNPO.** RMU
shows the same descriptive late-layer localization and the same bidirectional causal
reversibility, but its causal mechanism is architecturally different -- concentrated
entirely in layers 0-7 rather than distributed across mid-to-late layers -- and this is not
an artifact of the analysis, it is a directly verified property of the checkpoint's weights.

All computation reported here ran once, on job 447330 (7m49s, exit 0), submitted by the
user directly (background/forked sessions are gated from cluster submission). No existing
SatImp/SimNPO file was modified; every new script and output lives under
`mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/`.

## A. Model/checkpoint verification

- BASE: `saves/finetune/muse_news_qwen25_7b_instruct_target`
- RMU: `saves/unlearn/muse_news_qwen25_7b_instruct_rmu/checkpoint-459`

Verified against `thesis/manifests/model_lists/muse_news_qwen25_persistbench_models.tsv`,
the exact manifest consumed by the launcher that produced the verified PersistBench
sycophancy FR@3=18.0% result for RMU. The top-level
`saves/unlearn/muse_news_qwen25_7b_instruct_rmu/*.safetensors` files are byte-identical in
size to `checkpoint-459/*.safetensors`, confirming this is the final selected checkpoint.
A second, unrelated RMU run exists at `saves/unlearn/muse_news_rmu_ckpts_bs1_gc_sbatch/`
(different shard count, different dates) -- explicitly ruled out, not used anywhere in
this analysis.

## B. Behavioral transitions

Generation index 0, threshold >=3, 200 sycophancy rows (identical convention to the
canonical SatImp/SimNPO transition classification):

| Transition | Count |
|---|---:|
| SAFE -> SAFE | 168 |
| SAFE -> FAILURE | 13 |
| FAILURE -> SAFE | 9 |
| FAILURE -> FAILURE | 10 |

(SatImp: 166/15/10/9; SimNPO: 169/12/8/11 -- RMU's population is the same order of
magnitude, not an outlier.)

## C. Manual audit

Full case-by-case reasoning: `rmu_clean_audit/RMU_AUDIT.md`.

- 13 BASE-SAFE -> RMU-FAILURE candidates audited
- **8 HIGH_CONFIDENCE_FAILURE** (genuine, used as causal-patching treatment)
- 3 LIKELY_JUDGE_NOISE (judge reasoning contradicted or was unsupported by the actual
  stored response text -- e.g. one candidate's judge reasoning describes content about
  tire-plug permanence that never appears anywhere in the stored 96-token generation)
- 2 AMBIGUOUS (real but thin signal -- e.g. one response is cut off before any
  substantive claim is made)

8 genuine cases is well above the SatImp (6) / SimNPO (4) precedent -- no stopping
condition triggered. Matched 8-case SAFE_TO_SAFE control set built with the identical
greedy nearest-neighbor procedure (exact BASE judge score, then closest response/memory/
prompt length) used for SatImp/SimNPO; response-length matches were within 0-19 characters.

**Disclosed protocol deviation for section D (not section C):** the manual audit itself
follows the identical philosophy used for SatImp/SimNPO. The deviation is in how the
*descriptive* layer-localization analysis uses this audit -- see section D.

## D. Representation result (descriptive)

Script: `rmu_clean_audit/analyze_sycophancy_rmu.py`. Same token position (last token of the
effective prompt), same residual-stream extraction (all 29 hidden states,
`output_hidden_states=True`), same bootstrap CI method (1000 reps, basic bootstrap for
norms) as the canonical `analyze_sycophancy.py`.

**Disclosed, intentional protocol difference:** the canonical SatImp/SimNPO run used ALL
raw (unaudited) BASE-SAFE -> method-FAILURE transitions as the failure group (15 for
SatImp, 12 for SimNPO). Per explicit instruction, this RMU run uses only the 8
manually-audited HIGH_CONFIDENCE_FAILURE cases as the failure group. The stable group is
the full raw SAFE->SAFE population (N=168) in both cases, since neither version audits the
stable side. This makes RMU's number a smaller-N, higher-precision-per-case estimate, not a
like-for-like population -- a real difference, not papered over.

Results (`rmu_clean_audit/representations_analysis/rmu_analysis_summary.json`):

- Peak layer: **L27**
- Top-5 layers: L24, L25, L26, L27, L28
- Pearson r vs. SatImp's profile: **0.978**
- Pearson r vs. SimNPO's profile: **0.975**

Wording used throughout: **"descriptive failure-associated divergence"** -- never causal.
Figure: `presentation_figures_final/rmu_mechanistic_replication/rmu_sycophancy_failure_localization.png`.

Interpretation caveat: this high correlation reflects that hidden-state divergence between
BASE and any perturbed model tends to grow through the residual stream regardless of where
the perturbation originates -- see section D's link to section E below. It does *not* by
itself imply RMU's actual causal locus is late-layer; section E shows the opposite.

## E. Activation patching (the core experiment)

Scripts: `rmu_clean_audit/run_activation_patching_rmu.py` (patching),
`rmu_clean_audit/analyze_clean_patching_rmu.py` (statistics). Identical layer blocks
(L0-6/L7-13/L14-20/L21-27, 0-indexed into `model.model.layers`), identical teacher-forced
mean-log-prob-difference scoring, identical bootstrap statistics (2000 reps, seed 20260919)
as the canonical `run_activation_patching_clean.py`/`analyze_clean_patching.py`. Predicted
direction read directly from that code, not assumed: `predicted_positive = direction ==
"unlearned_recipient"` -- i.e. BASE-donor patching (BASE->RMU) is predicted to shift the
score positive (toward the safe continuation); RMU-donor patching into BASE
(RMU->BASE) is predicted to shift negative (toward the sycophantic continuation). Both
directions were run and verified, not assumed.

### Summary table (HIGH_CONFIDENCE_FAILURE group, n=8)

| Layer block | BASE->RMU mean shift | 95% CI | predicted-direction cases | RMU->BASE mean shift | 95% CI | predicted-direction cases |
|---|---:|---|---:|---:|---|---:|
| L0-6 | +0.2667 | [0.1893, 0.3505] | 8/8 | -0.2231 | [-0.2967, -0.1538] | 8/8 |
| L7-13 | +0.2904 | [0.2064, 0.3823] | 8/8 | -0.2904 | [-0.3823, -0.2064] | 8/8 |
| L14-20 | +0.2904 | [0.2064, 0.3823] | 8/8 | -0.2904 | [-0.3823, -0.2064] | 8/8 |
| L21-27 | +0.2904 | [0.2064, 0.3823] | 8/8 | -0.2904 | [-0.3823, -0.2064] | 8/8 |

The SAFE_TO_SAFE_MATCHED_CONTROL group shows the identical qualitative pattern at smaller
magnitude (e.g. BASE->RMU: L0-6 +0.1235, L7-13=L14-20=L21-27 +0.1318) -- full numbers in
`rmu_clean_audit/rmu_clean_activation_patching_summary.csv`.

### Critical finding: L7-13, L14-20, and L21-27 are bit-identical, and this is real, not a bug

Every one of the 16 examples (8 treatment + 8 control), both directions, gives *exactly*
the same floating-point score for patched_early_mid_L7-13, patched_mid_late_L14-20, and
patched_late_L21-27 -- e.g. one example gives 0.3045298457145691 for all three,
to 16 significant figures. This was verified NOT to be a code bug: the RMU patching script
is line-for-line identical in logic to the canonical script (`diff` confirms this), and the
same code produces genuinely distinct values per layer block for SatImp/SimNPO (e.g. SatImp
BASE->method: L7-13=+0.094, L14-20=+0.136, L21-27=+0.138 -- close but real and distinct).

**Root cause, directly verified by diffing the actual checkpoint weights** (see
`rmu_clean_audit/RMU_WEIGHT_LOCALITY_VERIFICATION.md` for the full byte-level diff): **this
RMU checkpoint's weights differ from BASE only in layers 0-7** (MLP down_proj relative
diff 0.85%-1.8%, peak at layer 7; attention o_proj similarly nonzero only in layers 0-7).
**Layers 8-27, the final norm, and the LM head are bit-identical to BASE** (diff_norm=0.0
exactly). Given this, a forward hook that overwrites any layer's output at or after layer 7
with the donor's captured activation discards whatever the recipient's own (possibly
RMU-modified) earlier layers computed, and every layer downstream of that point is
weight-identical between donor and recipient -- so the remaining computation exactly
reproduces the donor's own natural forward pass, *regardless of which specific later block
is nominally patched*. Only L0-6 (which does not fully cover layer 7) leaves RMU's actual
modification partially in the causal path, which is why it alone gives a distinct,
intermediate result.

**Practical consequence: for this RMU checkpoint, the causal patching experiment cannot
distinguish "L14-20 matters" from "L21-27 matters" from "everything from L7 onward
matters" -- they are mathematically the same intervention.** The genuinely informative
contrast is L0-6 (partial patch, RMU's real layer-7 effect still active) versus any
patch starting at or after layer 7 (full donor substitution). This is fundamentally
different from SatImp/SimNPO, which fine-tune all layers, so each layer block is an
independently meaningful intervention there.

Figure: `presentation_figures_final/rmu_mechanistic_replication/rmu_clean_activation_patching.png`
(the degeneracy is directly annotated on the figure, not hidden).

## F. Memory/context intervention (Experiment B)

**Not run.** This was explicitly optional and gated on cleanly reusing the existing
pipeline with minimal changes; given the compute budget was already spent confirming the
core patching result (and uncovering the weight-locality finding, which changes what a
memory-intervention result would even mean for RMU -- any patch that touches or is
downstream of layer 7 would show the same collapse-to-donor behavior described in
section E), this was not attempted. Flagged as a natural follow-up, not fabricated.

## G. Free-generation validation

**Not run**, for the same reason as F -- the original task treats this as optional and
conservative, and the canonical SatImp/SimNPO free-generation attempt (on the noisy
selection) was already reported elsewhere as inconsistent/reversed. Running it for RMU
would need fresh compute and a fresh go/no-go decision; not fabricated here.

## H. Comparison with SatImp/SimNPO

| Property | SatImp | SimNPO | RMU |
|---|---|---|---|
| MUSE-News sycophancy FR@3 | 17.0% | 15.0% | 18.0% |
| Genuine audited SAFE->FAIL cases | 6 | 4 | 8 |
| Descriptive peak layer | L27 | L28 | L27 |
| Descriptive profile correlation with each other / RMU | r=1.0 (SatImp vs SimNPO, from prior verification) | -- | r=0.978 vs SatImp, r=0.975 vs SimNPO |
| BASE->unlearned causal patching, L0-6 | +0.060 | +0.036 | +0.267 |
| BASE->unlearned causal patching, L21-27 | +0.138 | +0.111 | +0.290 (degenerate, = L7-13 = L14-20) |
| unlearned->BASE causal patching, L21-27 | -0.141 | -0.113 | -0.290 (degenerate, = L7-13 = L14-20) |
| Layer-block pattern | genuinely graded, rises L0-6 -> L21-27 | genuinely graded, rises L0-6 -> L21-27 | flat/degenerate from L7-13 onward (weight-locked) |
| Strongest supported causal range | L14-27 (both directions) | L14-27 (both directions) | **L0-7 is the only real locus; L7-27 patching is a trivial full-substitution artifact** |
| Predicted-direction consistency | 6/6 both directions, all blocks | 4/4 both directions, all blocks | 8/8 both directions, all blocks |

SatImp/SimNPO numbers are the existing verified canonical clean-audit values from
`../activation_patching_clean_audit/clean_activation_patching_summary.csv` /
`CLEAN_RERUN_REPORT.md` -- not the superseded pre-audit numbers.

**Does RMU reproduce the same qualitative causal pattern?** Partially:
- **Reproduces:** a genuine, bidirectional, 100%-consistent causal effect exists (patching
  shifts the recipient's safe-vs-sycophantic preference in the predicted direction for
  every example, both directions).
- **Does not reproduce:** the "distributed across mid-to-late layers" character of the
  effect. SatImp/SimNPO's effect genuinely grows from L0-6 through L21-27. RMU's effect is
  concentrated entirely in layers 0-7; everything reported for L7-13/L14-20/L21-27 is a
  mathematical restatement of "fully replace with donor," not evidence of a distributed
  mechanism.

## I. Strongest defensible conclusion

RMU causally reproduces BASE-vs-unlearned-model sycophancy-preference shifts in both
patch directions on its own manually-audited genuine failure cases (8/8 predicted-direction
consistency), but the verified weight-diff shows this checkpoint's entire behavioral change
is encoded in layers 0-7 -- a narrow, front-loaded mechanism -- in contrast to SatImp and
SimNPO, whose causal effect is genuinely distributed across mid-to-late layers (L14-27)
under full-model fine-tuning.

## J. What this experiment does NOT establish

- Does **not** establish a universal "sycophancy circuit" or "privacy circuit" -- three
  different unlearning methods produce three different depth-profiles for where the effect
  physically lives (RMU: L0-7 only; SatImp/SimNPO: distributed L0-27, strongest L14-27).
- Does **not** establish that RMU "shares the mechanism" with SatImp/SimNPO merely because
  its descriptive layer-profile correlates highly (r=0.98) with theirs -- that correlation
  is consistent with residual-stream accumulation of ANY early perturbation, not evidence of
  a shared causal locus (which section E's weight diff directly refutes: the causal locus is
  layers 0-7 for RMU vs. all layers for SatImp/SimNPO).
- Does **not** establish that teacher-forced patching results generalize to free generation
  -- not tested here (section G).
- Does **not** distinguish "memory-integration-specific" causal effects from general
  BASE-vs-RMU model-state differences -- Experiment B was not run (section F).
- BASE's own descriptive profile was not separately re-examined here for signs of the
  same late-layer sycophancy-correlated pattern in isolation; the existing SatImp/SimNPO
  reports already establish this is a BASE-relative *contrast* measure by construction
  (delta = method - BASE), so it cannot by definition show a "BASE-only" effect -- this
  is a structural feature of the metric, not a gap specific to this RMU run.
- Sample size is small (n=8 genuine cases, further limited to n=4 unique "true" layer
  conditions given the L7-27 degeneracy) -- stated prominently, not minimized.

## K. Defense-safe wording

*"RMU causally reproduces the bidirectional sycophancy-preference shift seen for
SatImp/SimNPO -- patching BASE-like states into RMU, and RMU-like states into BASE, moves
the model's safe-vs-sycophantic preference in the predicted direction for all 8
manually-audited genuine failure cases, in both directions. However, directly diffing the
checkpoint weights shows RMU's entire behavioral change is confined to layers 0-7, unlike
SatImp/SimNPO's full-model fine-tuning, which produces a genuinely graded effect through
layers 14-27. This means RMU's worsened sycophancy behavior and SatImp/SimNPO's likely
arise through different internal mechanisms, even though the surface behavioral metric
(PersistBench FR@3) worsens for all three methods and the descriptive late-layer
representation-divergence pattern looks superficially similar across all three."*

## Files created (this session)

All new; no existing SatImp/SimNPO file was modified (`git status` confirms only new
paths under `rmu_clean_audit/` and `presentation_figures_final/rmu_mechanistic_replication/`,
plus this report):

- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/RMU_AUDIT.md`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/clean_selection.json`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/sycophancy_transition_groups.json`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/extract_rmu_prompt_end_hidden_states.py`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/representations/rmu_prompt_end.pt`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/representations/extraction_metadata_rmu.json`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/analyze_sycophancy_rmu.py`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/representations_analysis/rmu_sycophancy_layer_metrics.csv`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/representations_analysis/rmu_analysis_summary.json`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/representations_analysis/rmu_vs_satimp_simnpo_failure_contrast_norm.png`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/run_activation_patching_rmu.py`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/activation_patching/activation_patching_rmu_unlearned_recipient.csv` (+ base_recipient.csv, + both provenance JSONs)
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/analyze_clean_patching_rmu.py`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/rmu_per_example_shifts.csv`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/rmu_clean_activation_patching_summary.csv`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/RMU_WEIGHT_LOCALITY_VERIFICATION.md`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/RMU_EXAMPLES_FOR_SLIDES.txt`
- `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit/run_rmu_replication.sbatch`
- `presentation_figures_final/rmu_mechanistic_replication/rmu_sycophancy_failure_localization.png` (+.svg/.pdf)
- `presentation_figures_final/rmu_mechanistic_replication/rmu_clean_activation_patching.png` (+.svg/.pdf)
- `presentation_figures_final/rmu_mechanistic_replication/rmu_vs_satimp_simnpo_mechanistic_summary.png` (+.svg/.pdf)
- `thesis_cleanup_audit/RMU_MUSE_NEWS_MECHANISTIC_REPLICATION.md` (this file)
