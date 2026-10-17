# MUSE-News Qwen2.5-7B Privacy Collapse pilot

This additive pilot compares the MUSE-News target checkpoint (BASE) with SatImp
and SimNPO. It implements the paper's primary layer-wise direction exactly as
`mean(h_safe) - mean(h_leaky)` independently within each model. No PCA direction
is used. Models are loaded sequentially.

## Frozen inputs and semantics

`manifests/privacy_lens_50.json` freezes 50 model-independent PrivacyLens IDs
using Python `random.Random(260115220).sample`. Privacy-safe is stored explicitly
as `B = No`; privacy-violating is `A = Yes`. `prepared_examples.json` stores raw
and Qwen-chat-formatted prompts, exact prompt/completion IDs and hashes, semantic
labels, answer positions, and sufficient information for a later label swap.

The control is the intended 20-question binary commonsense/answer-selection set
released in `steering_task_vector.py`. It is not GSM8K. The upstream list misses
a comma between two questions; this implementation restores the intended split
and records it in static provenance.

## Qwen logit lens

The installed Transformers `Qwen2Model.forward` saves states 0..L-1 before their
blocks, then applies the final RMSNorm and saves state L. The logit lens applies
each checkpoint's own final RMSNorm to states 0..L-1, uses state L directly, and
then applies that checkpoint's own untied `lm_head`. Thus the final state is not
double-normalized. Static validation requires clean single-token A/B alternatives
at the exact Qwen assistant boundary; extraction refuses to silently score only a
first subtoken if future formatting changes this invariant.

## Output schema

Output root: `mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/`

- `prepared_examples.json`: exact frozen prompt/answer/token records.
- `static_validation.json`: CPU validation and checkpoint/tokenizer provenance.
- `output_schema.json`: exact table columns and tensor keys/shapes.
- `models/<MODEL>/logit_lens_per_example.csv`: one row per model, dataset,
  example, and residual state; probabilities, log probabilities, single-token
  logit difference, and JSON token-rank/logit arrays.
- `models/<MODEL>/{privacy,control}_directions.pt`: example IDs,
  `[N,29,3584]` individual safe-minus-leaky differences, `[29,3584]` mean
  direction, `[29]` norms, state labels, and answer position.
- `logit_lens_per_example_all_models.csv`: combined per-example table.
- `logit_lens_summary.csv`: mean/median/std/count trajectories.
- `direction_norms_and_cosines.csv`: norms and BASE-to-modified cosine by state.
- `gpu_extraction_provenance.json`, `analysis_validation.json`: provenance and
  validation records.
- Primary probability-trajectory and direction-cosine PNGs for privacy and the
  binary commonsense control.
- Presentation PNGs add the PrivacyLens raw-logit difference trajectory,
  correctly name the commonsense control as correct-minus-incorrect, and combine
  privacy/control direction alignment in one figure. The original PNGs remain
  unchanged for provenance.

## Commands

CPU/static preparation and validation:

```bash
python mechanistic/privacy_collapse/prepare_manifest.py
python mechanistic/privacy_collapse/validate_static.py
```

Proposed GPU pilot (not submitted during implementation):

```bash
sbatch mechanistic/privacy_collapse/slurm/run_muse_news_qwen25_7b_pilot.sbatch
```
