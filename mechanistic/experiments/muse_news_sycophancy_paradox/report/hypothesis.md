# Phase 4 — mechanistic hypothesis and alternatives to be distinguished

## Case under study

MUSE-News, Qwen2.5-7B-Instruct. BASE `saves/finetune/muse_news_qwen25_7b_instruct_target`
vs. SatImp `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459` and SimNPO
`saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459`. Category: PersistBench
**sycophancy** (cross-domain does not show the target phenomenon on this dataset — it
*improves* after unlearning at every FR@K — so it is used only as a documented negative
result / contrast, not as a primary target here). Judge: legacy local
`Qwen/Qwen2.5-7B-Instruct` throughout; not canonical Kimi-K2.

## Working hypothesis (not assumed true)

"Unlearning may leave the model's contextual-privacy/sycophancy representation largely
intact — explaining stable PrivacyLens and stable controlled-MCQ recognition (50/50,
100% accuracy, cosine 0.96+ pre/post unlearning) — while altering how stored
user-specific memory influences downstream free-text generation, so the model still
recognizes the sycophancy norm when explicitly probed yet violates it more often when
actually generating an answer in the presence of that memory."

## Alternatives this experiment must distinguish

1. **Privacy/sycophancy representation itself is damaged.** Tested by Phase 6 reuse
   (`mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/`, PrivacyLens direction
   cosine ≈0.937–0.938) and the existing sycophancy-MCQ probe (cosine ≈0.962–0.964,
   accuracy 100/100 both methods) — argues against this alternative, but both are
   single-token/controlled-choice readouts, so this experiment adds a *native,
   multi-token* teacher-forced check (Phase 8) before accepting that conclusion.
2. **Representation intact, irrelevant/stored memory insufficiently suppressed.**
   Tested directly by the new memory-ablation delta (Phase 7): does the with-memory
   minus without-memory hidden-state shift grow specifically for SAFE→FAILURE rows
   relative to SAFE→SAFE rows, and specifically after unlearning?
3. **User-specific memory receives excessive weight during generation.** Same Phase 7
   measurement; distinguished from (2) mainly by direction/sign and by whether the
   effect is memory-magnitude-driven or memory-direction-driven.
4. **The change occurs only during late output formation (readout), not upstream
   representation.** Tested by Phase 8: at which layer does the teacher-forced
   safe-vs-sycophantic-continuation preference start to diverge between BASE and the
   unlearned model, for SAFE→FAILURE rows vs SAFE→SAFE controls?
5. **Generic representation drift unrelated to sycophancy.** Tested by the existing
   Phase-11-style control already computed by the prior sycophancy analysis: BASE→
   unlearned model-change-vector cosine is 0.89–0.94 for *both* SAFE→SAFE and
   SAFE→FAILURE rows at the implicated late layers — i.e. most drift is shared, and
   only a smaller residual component is failure-specific. This experiment's Phase 7/8
   analyses repeat this drift-vs-effect decomposition on the new measurements.
6. **Benchmark/task-format artifact, not a privacy-specific mechanism.** Mitigated by
   using the *same* checkpoints, *same* judge, and *same* prompts for PrivacyLens/MCQ
   and native PersistBench, and by keeping cross-domain (which does not show the
   effect) as an explicit within-benchmark contrast category.

## What would count as evidence for vs. against the working hypothesis

- **For:** SAFE→FAILURE rows show a larger/differently-directed memory-influence delta
  (Phase 7) than SAFE→SAFE rows, specifically in the unlearned models; the teacher-forced
  layer-wise preference for the model's own actual continuation over BASE's actual
  continuation (Phase 8) turns positive only in mid/late layers for SAFE→FAILURE rows,
  while staying flat for SAFE→SAFE rows; and (if attempted, Phase 9) patching BASE
  activations into the unlearned model over that layer range measurably reduces the
  sycophancy judge score / restores the non-sycophantic answer on held-out SAFE→FAILURE
  cases.
- **Against:** if the memory-influence delta and layer-of-divergence are indistinguishable
  between SAFE→FAILURE and SAFE→SAFE groups, the dissociation is better explained by
  generic drift (alternative 5) or by output-formatting noise rather than a
  sycophancy-specific mechanism.
