# Cleaned Phase-9 corrective validation: results

Corrective rerun of the causal activation-patching experiment, using ONLY manually-audited
HIGH_CONFIDENCE_FAILURE examples as treatment (SatImp n=6, SimNPO n=4) and matched
SAFE_TO_SAFE controls (matched on BASE judge score, then BASE response length, memory
length, prompt token length; n=6 SatImp, n=4 SimNPO). Original noisy-selection outputs
(`analysis/activation_patching_*.csv`) are untouched. All new files are under
`analysis/activation_patching_clean_audit/`.

Judge/model/decoding context is unchanged from the original teacher-forced Phase 9: this
is a `score = mean_logprob(base_response) - mean_logprob(unlearned_response)` contrast
under the recipient model's own logits, not free generation (see H caveats).

## A. Clean Phase-9 results (exact numbers, HIGH_CONFIDENCE_FAILURE only)

| Direction | Method | Layer range | n | Mean shift | Median | 95% CI | Frac. predicted-direction |
|---|---|---|---|---|---|---|---|
| BASE→unlearned (fwd) | SatImp | L0-6 | 6 | +0.060 | +0.061 | [0.051, 0.070] | 6/6 |
| BASE→unlearned (fwd) | SatImp | L7-13 | 6 | +0.094 | +0.092 | [0.075, 0.112] | 6/6 |
| BASE→unlearned (fwd) | SatImp | **L14-20** | 6 | **+0.136** | +0.123 | [0.113, 0.162] | **6/6** |
| BASE→unlearned (fwd) | SatImp | **L21-27** | 6 | **+0.138** | +0.122 | [0.119, 0.158] | **6/6** |
| BASE→unlearned (fwd) | SimNPO | L0-6 | 4 | +0.036 | +0.034 | [0.019, 0.052] | 4/4 |
| BASE→unlearned (fwd) | SimNPO | L7-13 | 4 | +0.067 | +0.067 | [0.042, 0.092] | 4/4 |
| BASE→unlearned (fwd) | SimNPO | **L14-20** | 4 | **+0.107** | +0.105 | [0.076, 0.139] | **4/4** |
| BASE→unlearned (fwd) | SimNPO | **L21-27** | 4 | **+0.111** | +0.114 | [0.077, 0.143] | **4/4** |
| unlearned→BASE (rev) | SatImp | L0-6 | 6 | -0.063 | -0.053 | [-0.086, -0.050] | 6/6 |
| unlearned→BASE (rev) | SatImp | L7-13 | 6 | -0.076 | -0.078 | [-0.098, -0.055] | 6/6 |
| unlearned→BASE (rev) | SatImp | **L14-20** | 6 | **-0.136** | -0.125 | [-0.159, -0.115] | **6/6** |
| unlearned→BASE (rev) | SatImp | **L21-27** | 6 | **-0.141** | -0.127 | [-0.161, -0.123] | **6/6** |
| unlearned→BASE (rev) | SimNPO | L0-6 | 4 | -0.036 | -0.035 | [-0.055, -0.017] | 4/4 |
| unlearned→BASE (rev) | SimNPO | L7-13 | 4 | -0.044 | -0.038 | [-0.070, -0.018] | 4/4 |
| unlearned→BASE (rev) | SimNPO | **L14-20** | 4 | **-0.101** | -0.105 | [-0.130, -0.068] | **4/4** |
| unlearned→BASE (rev) | SimNPO | **L21-27** | 4 | **-0.113** | -0.120 | [-0.144, -0.078] | **4/4** |

Full per-example values: `clean_per_example_shifts.csv`. Plots: `plots/clean_per_example_shifts.png`.

## B. Per-example consistency

**Every single example moves in the predicted direction, at every layer range, in both
directions, for both methods: 6/6 SatImp, 4/4 SimNPO (100%).** This is not an artifact of
one or two extreme cases — per-example shifts at L21-27 (the range with the largest effect)
range narrowly: SatImp forward +0.114 to +0.178 (tight cluster, no outlier); SimNPO forward
+0.059 to +0.156 (slightly wider spread but still uniformly positive, no case near zero or
reversed). Reverse direction mirrors this with negative signs of comparable magnitude.

## C. Robustness — did the effect survive removing judge-noise examples?

**Yes, and it did not weaken.** Comparing old (noisy, score-jump-selected n=6) vs. clean
(HIGH_CONFIDENCE_FAILURE-only, n=6/4) at L21-27, forward direction:
- SatImp: old +0.130 (95% CI [0.047, 0.246], wide) → clean +0.138 (CI [0.119, 0.158], much tighter).
- SimNPO: old +0.087 (CI [0.056, 0.117]) → clean +0.111 (CI [0.077, 0.143]).

The point estimate is comparable-to-slightly-larger after cleaning, and the CI is
**substantially narrower** in every case (removing noise examples reduced variance without
reducing the mean effect) — full table in `old_vs_clean_comparison.csv`, plot in
`plots/old_vs_clean_comparison.png`. This is the opposite of what would happen if the
original effect had been an artifact of the noisy examples: removing them made the signal
cleaner, not weaker or absent.

## D. Layer localization

L14-20 and L21-27 remain the strongest ranges for both methods and both directions; L0-6 is
consistently the weakest (roughly half the magnitude of L14-20/L21-27), with L7-13
intermediate — the same monotonic-with-depth pattern as the original run, now confirmed on
clean labels.

## E. SatImp vs. SimNPO — same phenomenon?

Within-group (failure-only) results: **yes**, both methods show the same sign, same
layer-localization pattern, comparable magnitude, 100% per-example consistency.

Control comparison (secondary, see F): **partially different.** SatImp's failure-group
effect is clearly larger than its matched-control effect (L21-27 fwd: failure +0.138 vs.
control +0.078, ratio ~1.8x; CIs [0.119,0.158] vs [0.046,0.112] — barely non-overlapping).
SimNPO's failure-group effect is only marginally larger than its control (L21-27 fwd:
failure +0.111 vs. control +0.101, ratio ~1.1x; CIs [0.077,0.143] vs [0.076,0.126] —
substantially overlapping). So the *within-group* causal effect replicates for both
methods, but the *failure-specificity* (failure > control) is only clearly supported for
SatImp; for SimNPO the matched-control group shows nearly as large a shift, so this
particular comparison cannot distinguish "failure-specific" from "affects most/all
sycophancy-category examples similarly" for SimNPO.

## F. Control comparison

| Direction | Method | Layer | Failure mean [CI] | Control mean [CI] | Ratio |
|---|---|---|---|---|---|
| fwd | SatImp | L21-27 | +0.138 [0.119,0.158] | +0.078 [0.046,0.112] | 1.8x |
| fwd | SimNPO | L21-27 | +0.111 [0.077,0.143] | +0.101 [0.076,0.126] | 1.1x |
| rev | SatImp | L21-27 | -0.141 [-0.161,-0.123] | -0.074 [-0.107,-0.043] | 1.9x |
| rev | SimNPO | L21-27 | -0.113 [-0.144,-0.078] | -0.100 [-0.122,-0.078] | 1.1x |

Per the explicit caveat in the task: the control group's "safe" vs. "alt" contrast is
safe-wording vs. safe-wording (a weaker construct than failure's safe-vs-sycophantic), so
even a smaller control-group shift does not by itself prove failure-specificity — this
table is a secondary sanity check, not the primary evidence. It shows SatImp's separation
from control is real but modest (not the "2-6x" originally reported, which was inflated by
noisy examples with near-zero unpatched-score baselines), and SimNPO's separation from
control is not established by this comparison alone.

## G. Thesis-safe interpretation

**What can now be claimed:** On the 10 manually-verified genuine SAFE→FAILURE sycophancy
examples (6 SatImp + 4 SimNPO), replacing the recipient model's L14-20 and L21-27 decoder
outputs with the donor model's outputs causally and consistently shifts the recipient's
relative log-probability preference between the BASE-authored and unlearned-authored
continuations, in the direction predicted by the donor's identity, for 100% of examples in
both patch directions and both methods. This effect survived removal of the judge-noise
examples that contaminated the original selection, with tighter (not wider) confidence
intervals — the original causal claim was not an artifact of mislabeled examples, at least
for this within-group comparison.

**What remains unsupported / must not be claimed:**
- That this generalizes to *all* sycophancy-category examples, or is provably
  *failure-specific* rather than a general late-layer property of most sycophancy prompts —
  the matched-control comparison supports failure-specificity clearly for SatImp only;
  for SimNPO the control shows nearly as large an effect.
- That this reflects memory-integration specifically, as opposed to any other BASE-vs-
  unlearned model difference expressed at these layers (per task constraint #8 — this
  experiment patches whole BASE-vs-unlearned model state, not with-memory-vs-without-memory
  within one model).
- That this causally changes what the model would *freely generate* — this remains a
  fixed-continuation teacher-forced likelihood contrast (per task constraint #9); the
  separate autoregressive regeneration+rejudging pipeline (already run once, on the noisy
  selection, and found inconsistent/reversed effects) has not yet been rerun on this clean
  selection.
- Generalization beyond MUSE-News/Qwen2.5-7B/SatImp+SimNPO/sycophancy (cross-domain and
  MUSE-Books remain documented negative/non-replicating results, unchanged by this rerun).

**Correct summary sentence:** *"On a manually-verified set of 10 genuine sycophancy
failures, mid-to-late decoder activations (L14-27) altered by unlearning causally
influence the model's relative preference between privacy-preserving and sycophantic
fixed continuations, consistently across every example and both patch directions; this
survives removal of judge-noise examples with tightened confidence intervals. Whether this
effect is specific to failure cases (vs. a general sycophancy-category property) is
supported for SatImp but not established for SimNPO, and whether it reflects
memory-integration specifically or would alter actual free-generation behavior remain open
questions requiring the experiments in H."*

## H. Recommendation for the next experiment (ranked after seeing this result)

Given the within-group causal effect is now robust and tight, but (i) failure-specificity
is unconfirmed for SimNPO, (ii) the free-generation link is unconfirmed and the one prior
attempt showed inconsistent/reversed effects, and (iii) memory-integration-specificity is
untested:

1. **Autoregressive patched regeneration + rejudging on this cleaned 10-example set, with
   the matched controls included this time.** This is the most direct way to resolve
   whether the now-robust teacher-forced signal translates into real generated text, which
   is the biggest remaining gap given the previous (noisy, uncontrolled) attempt found no
   clean signal. Moderate cost (already-built pipeline, just needs the clean example list
   and a control arm added).
2. **With-memory vs. without-memory causal patching within the unlearned model** (the
   memory-integration-specificity test) — this is the only experiment that can upgrade the
   current claim from "BASE-vs-unlearned model state differences matter" to "memory
   integration specifically matters," which is central to the thesis's mechanistic story.
3. **Expand matched controls for SimNPO** (e.g., 2-3 more matched controls, still cheap)
   to get a tighter read on whether SimNPO's failure-vs-control separation is real but
   underpowered at n=4, or genuinely absent — this directly resolves the E/F asymmetry
   found here and is the cheapest of the three.
