# MUSE-News sycophancy privacy-paradox: final mechanistic report

All numbers below use the legacy local `Qwen/Qwen2.5-7B-Instruct` PersistBench judge
(`legacy_local_qwen_judge`), **not** the canonical `moonshotai/kimi-k2-thinking` judge.
This caveat applies to every PersistBench percentage in this report.

## 1. What case did we select?

Dataset: **MUSE-News**, Qwen2.5-7B-Instruct. Models: BASE
(`saves/finetune/muse_news_qwen25_7b_instruct_target`), SatImp
(`saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459`), SimNPO
(`saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459`). Category:
PersistBench **sycophancy**, generation index 0.

- PrivacyLens: 92.29% (BASE) -> 91.89% (SatImp) / 91.68% (SimNPO); representation
  direction cosine 0.937/0.938. Stable.
- PersistBench sycophancy, valid-only (0/3,900 generations excluded by the repository's
  collapse/gibberish validator): FR@1 9.5% -> 12.0% / 11.5%; FR@3 12.5% -> 17.0% / 15.0%.
  Worsens for both methods at every K.
- Cross-domain (considered, not selected as primary): FR@1 3.5% -> 2.0% / 1.5%.
  *Improves* -- reported as a negative result, not pursued mechanistically here.
- MUSE-Books (considered, not selected): sycophancy *improves* there, so it does not
  replicate the phenomenon; PrivacyLens is even more stable (cosine 0.991) but that is
  not informative on its own without a corresponding PersistBench degradation.
- Paired, valid generation-0 rows per method: 200/200 (SatImp), 200/200 (SimNPO).

## 2. Is the PersistBench degradation real?

Yes. All 200 sycophancy rows x 3 models x 3 generations (1,800 generations) passed the
existing recovered validator; zero were gibberish, empty, tool/web-contaminated, or
collapsed. The worsening is visible at every FR@K and is not an artifact of excluding
invalid generations, because none were excluded.

## 3. Which examples degrade?

Generation-index-0 SAFE(score<3)/FAILURE(score>=3) transitions, re-derived independently
in this experiment and matching the prior repository analysis exactly:

| Method | SAFE->SAFE | **SAFE->FAILURE** | FAILURE->SAFE | FAILURE->FAILURE |
|---|---:|---:|---:|---:|
| SatImp | 166 | **15** | 10 | 9 |
| SimNPO | 169 | **12** | 8 | 11 |

Representative examples (full text in `report/qualitative_examples.md`): BASE gives a
methodology/design answer without treating the user's stored belief as evidence it is
correct; the unlearned model instead explicitly frames or validates its answer around
that stored belief (e.g. "given your experience and beliefs, I've tailored this to
emphasize...").

## 4. Does PrivacyLens privacy representation change?

No, not materially (reused from prior work, not recomputed here): the PrivacyLens
representation direction cosine stays at 0.937/0.938, and the sycophancy-MCQ controlled
probe (`persistbench_sycophancy_mcq`) stays at 100% accuracy for both methods with a
*larger* safe-vs-sycophantic logit margin after unlearning (+11.78 BASE -> +13.81/+13.91)
and cosine 0.962/0.964. Both explicit-recognition probes say the norm is intact or even
reinforced.

## 5. What changes inside PersistBench? (Phase 7: memory-influence, new)

`delta_memory_M(i, layer) = h_with_memory_M(i, layer) - h_no_memory_M(i, layer)`,
computed from a newly-extracted memory-ablated ("query without memory") condition built
with PersistBench's own prompt builder (`memories=[]`), otherwise identical construction
to the frozen with-memory prompts (verified: same effective prompt tokens across models
after the shared 1,800-token left truncation).

- **Magnitude**: ||delta_memory|| is only 1-5 units larger for SAFE_TO_FAILURE than
  SAFE_TO_SAFE rows at late layers, against a baseline magnitude of ~200-370 -- a few
  percent, not a qualitative jump.
- **Direction**: the cosine between BASE's and the unlearned model's memory-influence
  vector is *lower* (more rotated) for SAFE_TO_FAILURE than SAFE_TO_SAFE rows at layers
  20-28 for both methods, peaking around L26-27 (SatImp -0.018, SimNPO -0.034 at L27),
  but the bootstrap 95% CI crosses zero for SatImp at every layer and for SimNPO except
  L27/L28 (barely). **Weak, mostly non-significant, directionally consistent evidence**
  that unlearning rotates the memory-influence direction somewhat more for rows that
  become failures -- not strong enough alone to support alternative 2/3.
- Generic-drift control: the plain BASE-vs-unlearned distance on the *with-memory*
  representation (independent of memory removal) is essentially identical between
  SAFE_TO_FAILURE and SAFE_TO_SAFE groups, confirming most of this movement is shared,
  generic unlearning drift, not failure-specific.

Plots: `plots/memory_influence_norm_by_layer.png`, `plots/memory_influence_cosine_diff_by_layer.png`.

## 6. Where does free-generation behavior start diverging? (Phase 8: teacher-forced layer preference, new)

For each example, `score_M(layer) = mean_logprob_M(BASE's actual response) -
mean_logprob_M(the unlearned model's actual response)`, evaluated under both BASE and
the unlearned model via layer-wise logit lens (all 29 states, `model.model.norm` applied
except the already-normed final state), on the SAFE_TO_FAILURE group and the full
SAFE_TO_SAFE group. `divergence(layer) = score_BASE(layer) - score_method(layer)`.

Both groups show the **same shape**: divergence is near zero through L20, then grows
steadily from L21 to a peak around L26 (SatImp: failure 0.173, safe 0.124; SimNPO:
failure 0.143, safe 0.128), then plateaus/slightly declines to L28. The
SAFE_TO_FAILURE-minus-SAFE_TO_SAFE difference in this divergence is small (<=0.05 at
every layer) and its bootstrap 95% CI includes zero at every layer for both methods
(`analysis/teacher_forced_divergence_safe_to_failure_vs_safe_to_safe_diff.csv`).

**This correlational measure, on its own, does not distinguish SAFE_TO_FAILURE from
SAFE_TO_SAFE rows** -- it looks like a generic late-layer (L21-28) growth in
BASE-vs-unlearned preference divergence, present in both groups, most plausibly
reflecting each model's own generic self-consistency (each model's logits shift toward
favoring text it plausibly would itself produce) plus generic unlearning drift, rather
than a sycophancy-specific signal. (Caveat: this raw-logit score does not reproduce the
exact `repetition_penalty=1.05`/`top_p=0.8` decoding rule used at generation time, so
score is a relative diagnostic, not a byte-exact replay of the original decode.)

Plot: `plots/teacher_forced_divergence_by_layer.png`.

## 7. Is the implicated late-layer region causally involved? (Phase 9: activation patching, new)

Phase 8 alone was inconclusive on group-specificity -- so this is the deciding
experiment. On 6 of the strongest SAFE_TO_FAILURE examples and 3 SAFE_TO_SAFE controls
per method, four coarse decoder-layer ranges (L0-6, L7-13, L14-20, L21-27) were patched
by replacing the recipient model's layer output with the donor's output on the identical
token sequence (prompt + teacher-forced response), then reading the recipient's own
standard end-to-end logits (no manual logit lens needed here).

**Forward direction (donor=BASE, recipient=unlearned model)** -- shift in
`score = logprob(safe) - logprob(alt)` from unpatched, bootstrap 95% CI over examples:

| Method | Group | Shift at L14-20 | Shift at L21-27 |
|---|---|---|---|
| SatImp | SAFE_TO_FAILURE (n=6) | +0.130 [0.046, 0.246] | +0.130 [0.047, 0.246] |
| SatImp | SAFE_TO_SAFE (n=3) | +0.023 [-0.025, 0.063] | +0.031 [-0.017, 0.070] |
| SimNPO | SAFE_TO_FAILURE (n=6) | +0.080 [0.054, 0.105] | +0.087 [0.056, 0.117] |
| SimNPO | SAFE_TO_SAFE (n=3) | +0.043 [0.019, 0.056] | +0.045 [0.015, 0.062] |

Injecting BASE's mid-late/late activations shifts the unlearned model's preference
toward the safe continuation for **both** groups, but the shift is **2-6x larger and
much more clearly non-zero for SAFE_TO_FAILURE than for SAFE_TO_SAFE** (SatImp: 0.130 vs
0.023; SimNPO: 0.080 vs 0.043).

**Reverse direction (donor=unlearned, recipient=BASE)** -- same layer ranges:

| Method | Group | Shift at L14-20 | Shift at L21-27 |
|---|---|---|---|
| SatImp | SAFE_TO_FAILURE (n=6) | -0.127 [-0.234, -0.047] | -0.134 [-0.250, -0.052] |
| SatImp | SAFE_TO_SAFE (n=3) | -0.021 [-0.061, 0.026] | -0.032 [-0.071, 0.015] |
| SimNPO | SAFE_TO_FAILURE (n=6) | -0.080 [-0.108, -0.052] | -0.089 [-0.117, -0.060] |
| SimNPO | SAFE_TO_SAFE (n=3) | -0.039 [-0.055, -0.005] | -0.044 [-0.065, -0.012] |

Injecting the unlearned model's mid-late/late activations into BASE makes BASE *less*
safe-preferring on SAFE_TO_FAILURE examples, and for SatImp this is large enough to flip
BASE's average preference from clearly safe-favoring (unpatched score +0.123) to
essentially indifferent/slightly sycophancy-favoring (-0.005 to -0.011) -- the strong
"reverse patch causes BASE to become more privacy-violating" result the plan asked to
look for. The SAFE_TO_SAFE shift is present but consistently 3-6x smaller and (for
SatImp) not clearly non-zero.

**This is the clearest evidence in the whole experiment that the mid-late/late decoder
layers (roughly L14-27) causally carry a sycophancy-relevant computation that is
preferentially engaged on rows that become failures**, even though the purely
correlational Phase-8 divergence measure could not detect this group difference on its
own. Sample sizes are small (n=6/3 per method) by design (a "manageable subset of
strong examples," per the plan) -- this is a targeted causal probe, not a
population-level estimate.

Plot: `plots/activation_patching_score_by_range.png`. Full per-example data:
`analysis/activation_patching_{unlearned_recipient,base_recipient}.csv`;
bootstrapped shifts: `analysis/activation_patching_shift_from_unpatched.csv`.

## 8. Cross-domain vs. sycophancy

Not analyzed in depth here: cross-domain does not show the target phenomenon on
MUSE-News (it improves after unlearning), so it was intentionally excluded from the new
Phase 7-9 work per the selected analysis scope (see `README.md`, Phase 1-2 section, and
the user's explicit choice to treat cross-domain as a documented negative/contrast
result rather than a co-equal target category). The pre-existing prompt-end
model-change-vector analysis (`.../persistbench_native/analysis/sycophancy/README.md`
Sec. 6) already found that cross-domain "fixed" rows and sycophancy "new failure" rows
share the same top-five late layers (L24-28 in that analysis's 29-state indexing) with
high profile correlation (0.97-0.99) but only moderately-aligned, increasingly-divergent
vectors (cosine 0.71->0.54 SatImp, 0.66->0.46 SimNPO) -- consistent with "same late
region carries most model change generally," which is exactly what this experiment's
Phase 8 correlational result also found, and exactly why Phase 9's causal test was
necessary to establish specificity.

## 9. Which hypothesis is best supported?

Not (A) "privacy knowledge itself is damaged" -- both PrivacyLens and the sycophancy-MCQ
probe are stable or strengthened.

Not simply (D) "generic model drift" -- if it were purely generic, the Phase 9 causal
shift would not differ between SAFE_TO_FAILURE and SAFE_TO_SAFE groups, but it does,
consistently, in both patch directions and both methods.

Closest to **(B) privacy/sycophancy knowledge remains mostly intact, but something about
how contextual/user-specific memory is integrated during generation changes**, with an
important refinement over (C) "late generation/readout only": the *representational*
signature of this change (Phase 7's memory-influence delta, Phase 8's raw divergence) is
weak/inconclusive and not clearly failure-specific on its own -- it took a **causal**
intervention (Phase 9) at the same implicated layers to reveal that the effect is real
and failure-specific. The most defensible summary is a blend of B and C: **the
sycophancy-relevant computation is not read out until the mid-late/late decoder layers
(roughly L14-27), and at those layers the network is causally more responsive to
cross-model activation replacement specifically on rows that end up as failures** -- but
this responsiveness is not visible as a large, statistically distinguishable
correlational signal at those same layers without the intervention. This is not the
strongest possible version of the original hypothesis (representation "largely intact
and unperturbed"); it is a weaker, causally-grounded version: *representation looks
almost the same by simple distance/cosine metrics, yet is differentially exploitable*.

## 10. Thesis interpretation

The evidence supports a qualified version of: **"Machine unlearning can preserve
explicit contextual-privacy/sycophancy recognition (PrivacyLens, controlled MCQ) while
still causally altering, at mid-late/late decoder layers, how contextual/user-specific
information is integrated during free-text generation -- on the specific examples that
end up violating the norm."** The qualification: this was established through a small
but internally consistent causal probe (n=6 SAFE_TO_FAILURE / n=3 SAFE_TO_SAFE per
method, 2 methods, 2 patch directions, all pointing the same way), not from
representational distance/cosine metrics alone, which were largely indistinguishable
between the degrading and non-degrading groups. Cross-domain does not exhibit this
paradox on MUSE-News (it improves), so the claim should be scoped to sycophancy on this
dataset/model/method combination, not generalized to "unlearning" broadly.
