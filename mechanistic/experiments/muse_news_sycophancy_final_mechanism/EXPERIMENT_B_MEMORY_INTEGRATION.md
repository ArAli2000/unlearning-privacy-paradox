# Experiment B: Within-Model WITH_MEMORY ↔ NO_MEMORY Patching

**Status:** Complete. SLURM job 444575 (`expB_memory_patch`), COMPLETED, exit code 0,
2026-09-23 18:38–18:40.

**Outputs:**
- `expB_memory/expB_scores.csv` (40 rows: 10 treatment cases × up to 3 models
  [SatImp/SimNPO on their own cases, BASE on all 10] × 2 layer ranges)
- `expB_memory/expB_provenance.json`

## What the experiment measures

This is a **within-model** test (same weights; only the prompt differs), distinct from
the BASE-vs-unlearned representation patching already established elsewhere in this repo
(`CLEAN_RERUN_REPORT.md`: SatImp forward patch +0.138 CI[0.119,0.158] 6/6, SimNPO +0.111
CI[0.077,0.143] 4/4 — a *different* comparison, injecting unlearned-model representations
into BASE, not analyzed here).

For each of the 10 HIGH_CONFIDENCE_FAILURE cases, on the *same* model, two prompt
variants exist: WITH_MEMORY (stored user beliefs in context) and NO_MEMORY (memories
stripped out, same query). The readout is the teacher-forced mean-logprob margin
(safe response − sycophantic response); higher = model prefers the safe continuation.

Four conditions per case/model/layer-range:
- **A** WITH_MEMORY unpatched
- **B** WITH_MEMORY, patched at the single prompt-end token position with the NO_MEMORY
  hidden state at that same case ("forward": does erasing memory's trace from the
  internal state push the model toward the safe answer?)
- **C** NO_MEMORY unpatched
- **D** NO_MEMORY, patched at the prompt-end position with the WITH_MEMORY hidden state
  ("reverse": does injecting memory's trace into a memory-free context push the model
  toward the sycophantic answer?)

`forward_shift = B − A`, `reverse_shift = D − C`. Layer ranges: `mid_late_L14-20`,
`late_L21-27` (0-indexed).

## Baseline (unpatched) with/without-memory gap

Across nearly every case and model, `unpatched_score_no_memory` is substantially higher
(more safe-favoring) than `unpatched_score_with_memory` — e.g. SatImp `aa71a70f`: +0.69
without memory vs. +0.11 with memory; SimNPO `e549f564`: +0.66 vs. −0.085. This confirms
the premise: simply having the stored memories in the prompt, independent of any
patching, already collapses most of the model's safe-vs-sycophantic preference margin.
The question Experiment B asks is whether a **single prompt-end hidden state** carries
enough of that effect to move the needle causally.

## Result 1 — does replacing WITH_MEMORY state with NO_MEMORY state move the model toward safe? Weak and inconsistent.

| model | layer range | n cases | mean forward_shift | cases with forward_shift > 0 |
|---|---|---|---|---|
| SatImp | L14–20 | 6 | +0.0054 | 2/6 |
| SatImp | L21–27 | 6 | +0.0119 | 2/6 |
| SimNPO | L14–20 | 4 | +0.0295 | 3/4 |
| SimNPO | L21–27 | 4 | +0.0064 | 2/4 |
| BASE | L14–20 | 10 | +0.0285 | 6/10 |
| BASE | L21–27 | 10 | +0.0041 | 4/10 |

**For SatImp: no, not reliably.** Mean shift is small and positive but only 2/6 cases
move in the predicted direction at either layer range — this is not a consistent causal
effect, it is closer to noise.

**For SimNPO: marginally, at L14–20 only.** 3/4 cases move positive (mean +0.0295), but
n=4 is very small and the L21–27 result for the same model is weak (2/4, +0.0064).

Compare these shifts (~0.005–0.03) to the unpatched with/without-memory gap itself
(~0.4–0.9 in the same units, see above): even where the forward effect is directionally
consistent, a single-token patch recovers only a small fraction of the total gap.

## Result 2 — does injecting WITH_MEMORY state into a NO_MEMORY context push toward sycophancy? Stronger and more consistent, layer-dependent.

| model | layer range | n cases | mean reverse_shift | cases with reverse_shift < 0 |
|---|---|---|---|---|
| SatImp | L14–20 | 6 | −0.0421 | 5/6 |
| SatImp | L21–27 | 6 | −0.0302 | 3/6 |
| SimNPO | L14–20 | 4 | −0.0240 | 2/4 |
| SimNPO | L21–27 | 4 | −0.0028 | 1/4 |
| BASE | L14–20 | 10 | −0.0483 | **10/10** |
| BASE | L21–27 | 10 | −0.0212 | 5/10 |

**This is the stronger, more reliable effect.** At L14–20 specifically: BASE is
perfectly consistent (10/10 cases shift toward sycophantic), SatImp is 5/6, SimNPO is
2/4 (small n, weaker). At L21–27 the effect is much less consistent for every model
(BASE drops to 5/10).

## Which layer range is stronger: L14–20 vs L21–27?

**L14–20 (mid-late) is clearly the stronger and more consistent range** for the
reverse-injection effect — this holds for BASE (10/10 vs 5/10), SatImp (5/6 vs 3/6), and
in mean-magnitude terms for SimNPO (−0.024 vs −0.003). This matches the direction (not
magnitude) of the plan's cited teacher-forced result, which found the *different*
BASE-vs-unlearned patch effect concentrated at L21–27 — so the two causal channels
(unlearning-weight-space vs. memory-context) are not obviously localized to the same
layer band.

## How does BASE compare to SatImp/SimNPO?

**BASE shows the same causal channel, at least as strongly as the unlearned models — not
more weakly.** The reverse-injection effect at L14–20 is *most* consistent in BASE
(10/10), comparable in SatImp (5/6), and weakest/noisiest in SimNPO (2/4, small n). This
means Experiment B does **not** show the unlearned models have a stronger or newly
created memory→sycophancy causal pathway at this specific position/layer than BASE
already has. The pathway (stored-context information reaching the prompt-end
representation and nudging the safe/sycophantic balance) appears to be a general
property of this model family already present pre-unlearning; unlearning's effect on
final generation behavior (established elsewhere, in free-generation and full-sequence
representation patching) is not shown by this single-position test to come from
amplifying this particular channel.

## Does this support "memory/context integration is causally involved"?

**Partially.** There is a real, directionally consistent, layer-localized (L14–20) causal
signal: injecting a memory-conditioned hidden state at the prompt-end position measurably
shifts the safe/sycophantic preference, and it is far more reliable in the reverse
(inject-memory) direction than the forward (ablate-memory) direction. That asymmetry
itself is informative — it suggests the prompt-end representation is a sufficient (if
partial) carrier of the memory-context effect, but not the sole necessary one (ablating
it alone doesn't reliably restore safety, implying the effect is also carried elsewhere,
e.g. distributed across the memory-block token positions rather than concentrated only at
the prompt end).

What it does **not** show: that this specific causal channel is *changed by* unlearning
— BASE's effect size and consistency at L14–20 meets or exceeds SatImp's and SimNPO's.
