# PersistBench-MCQ

PersistBench-MCQ is an explicit privacy-judgment probe derived from frozen
PersistBench contexts. It is **not** the original PersistBench evaluation.

PersistBench-MCQ measures “explicit recognition of whether using/revealing a
particular stored memory is privacy-appropriate in the current context.” The
original PersistBench measures “whether the model actually leaks contextual
private information during open-ended generation.” These measurements are
related but distinct.

A future hypothesis is that an unlearned model could improve at explicitly
recognizing the privacy boundary (PersistBench-MCQ / PrivacyLens) while becoming
worse at respecting it during open-ended PersistBench generation. This is a
hypothesis, not a result.

## Frozen construction

The source is
`persistbench/manifests/cross_domain_simple_50_v1.json`, SHA-256
`94b16f53180a20d9683dae9f4bc169c0834a55d3e40a14ac0f12d5aa61a90b57`.
The builder copies all 50 IDs, queries, memories, target indices/text, and domain
fields without modification. Every item has `B / No` as privacy-safe and `A /
Yes` as privacy-violating. No free-text response is generated.

```bash
python mechanistic/privacy_collapse/persistbench_mcq/build_manifest.py
python mechanistic/privacy_collapse/persistbench_mcq/validate_static.py
```

Static validation writes exact Qwen-chat-formatted token sequences and token
hashes under
`mechanistic/outputs/privacy_collapse_persistbench_mcq_muse_news_qwen25_7b/`.
It verifies identical tokenizer artifacts and architecture across BASE, SatImp,
and SimNPO. With the frozen tokenizer, `A` is token 32 and `B` is token 33 at
the assistant completion boundary; no EOS is appended.

## PrivacyLens-compatible extraction

The future GPU extraction follows the existing whole-model PrivacyLens method:

- readout logits come from the last prompt token predicting the one-token A/B
  completion;
- directions use the last answer-completion token in `<prompt>B` and
  `<prompt>A`;
- each model's direction is `mean_i(h_safe_i - h_leaky_i)`;
- states are embedding plus L1–L28;
- per-layer logit projection applies that model's final RMSNorm to states 0–27,
  uses already-normalized state 28 directly, and then uses that model's own
  `lm_head`.

`P(A)` and `P(B)` are full-vocabulary softmax probabilities. The principal
behavioral readout is `logit(B) - logit(A)`. The analysis compares only
within-benchmark BASE-to-unlearned direction preservation; it does not compare
raw PrivacyLens and PersistBench-MCQ vectors.

The GPU job is implemented but must be explicitly submitted later:

```bash
sbatch mechanistic/privacy_collapse/persistbench_mcq/slurm/run_muse_news_qwen25_7b.sbatch
```
