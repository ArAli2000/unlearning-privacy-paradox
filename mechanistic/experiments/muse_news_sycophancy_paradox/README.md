# MUSE-News sycophancy privacy-paradox mechanistic experiment

**Final report: `report/FINAL_REPORT.md`.** Phases 3, 7, 8, and 9 all completed; results
summarized there. Short version: PrivacyLens/MCQ recognition stays intact; the
memory-influence (Phase 7) and raw teacher-forced divergence (Phase 8) measures are
weak/inconclusive on their own for distinguishing SAFE_TO_FAILURE from SAFE_TO_SAFE
rows; but causal activation patching (Phase 9) at mid-late/late decoder layers
(L14-27) shows a robust, bootstrap-CI-excluding-zero, failure-specific effect in both
patch directions and both methods -- the clearest evidence in this experiment.

New, self-contained experiment directory (per the task constraint "put new outputs in a
clearly separate experiment directory; do not overwrite existing outputs"). Nothing in
`mechanistic/privacy_collapse/` or `mechanistic/outputs/` is modified by anything here;
this directory only *reads* frozen prior artifacts and writes new ones under itself.

## Case selected (Phase 1-2)

- Dataset: **MUSE-News**, Qwen2.5-7B-Instruct target.
- Models: BASE `saves/finetune/muse_news_qwen25_7b_instruct_target`; SatImp
  `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459`; SimNPO
  `saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459`.
- Category: **PersistBench sycophancy** (generation index 0). Cross-domain was
  considered but is **not** used as the primary target here: it *improves* after both
  SatImp and SimNPO on this dataset at every FR@K, so it does not exhibit the
  phenomenon this thesis is about. It remains documented as a negative/contrast result
  (see `mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_category_comparison_validated.md`).
- Judge: legacy local `Qwen/Qwen2.5-7B-Instruct` (`legacy_local_qwen_judge`) throughout
  -- **not** canonical Kimi-K2 PersistBench. This must be stated wherever a PersistBench
  number from this experiment is cited.
- Why this case: PrivacyLens behavior and its representation direction are stable
  (92.3%->91.9%/91.7%; cosine 0.937/0.938); the sycophancy-MCQ controlled probe stays at
  100% accuracy with a *strengthened* safe-margin (cosine 0.962/0.964); yet native,
  free-text sycophancy FR@1 worsens (9.5%->12.0%/11.5%) and FR@3 worsens more
  (12.5%->17.0%/15.0%), with **zero** generations excluded by the repository's existing
  collapse/gibberish validator (0/3,900) -- i.e. the degradation is not a collapse
  artifact. MUSE-Books does not replicate this (its sycophancy *improves*), so it is not
  used here; see `mechanistic/outputs/muse_books_weekly_update_analysis/muse_news_vs_muse_books_weekly_comparison.md`.

## What is reused vs. new

Reused, unmodified, only read:
- `mechanistic/privacy_collapse/persistbench_native/manifests/native_sycophancy_200_v1.json`
  -- frozen prompts, generation-0 responses, judge scores, validity per model.
- `mechanistic/privacy_collapse/persistbench_native/representations/sycophancy/*.pt`
  -- with-memory prompt-end hidden states (BASE/SatImp/SimNPO), 200x29x3584.
- `mechanistic/privacy_collapse/persistbench_native/analysis/sycophancy/` and
  `mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/` -- existing model-change and
  PrivacyLens-representation results, cited in the final report rather than recomputed.

New in this directory (Phases 3-9 not previously done for this case):
- `build_transition_manifest.py` / `manifests/sycophancy_transition_groups.{json,csv}` --
  Phase 3: SAFE/FAILURE transition classification, re-derived directly from the frozen
  manifest above (official metric: failure = score>=3). Recomputing this independently
  reproduced the previously-reported transition counts exactly (SatImp 15/10, SimNPO
  12/8 new-failure/fixed), which is a useful cross-check.
- `build_qualitative_report.py` / `report/qualitative_examples.md` -- Phase 3 human-readable
  representative examples.
- `report/hypothesis.md` -- Phase 4.
- `prepare_no_memory_manifest.py` + `extract_no_memory_prompt_end.py` /
  `representations/*_prompt_end_no_memory.pt` -- Phase 6/7: the memory-ablated ("query
  without memory") condition, built with PersistBench's own `build_generation_prompt`
  with `memories=[]`, otherwise identical construction to the frozen with-memory prompts.
- `analyze_memory_influence.py` / `analysis/memory_influence_*.csv`, `plots/memory_influence_*.png`
  -- Phase 7 (+ Phase 11 generic-drift control).
- `extract_teacher_forced_layer_logprobs.py` + `analyze_teacher_forced_layer_logprobs.py`
  / `representations/teacher_forced_layer_logprobs.csv`, `analysis/teacher_forced_*.csv`,
  `plots/teacher_forced_divergence_by_layer.png` -- Phase 8.
- `run_activation_patching.py` / `analysis/activation_patching_*.csv` -- Phase 9.
- `slurm/*.sbatch` -- the GPU jobs above; all were smoke-tested on a 1-2-example slice
  via `srun` before the full run was submitted.

## Reproducing

CPU-only (fast): `build_transition_manifest.py`, `build_qualitative_report.py`,
`prepare_no_memory_manifest.py`, `analyze_memory_influence.py`,
`analyze_teacher_forced_layer_logprobs.py`.

GPU (submit from repo root): `sbatch mechanistic/experiments/muse_news_sycophancy_paradox/slurm/run_teacher_forced_layer_logprobs.sbatch`;
`extract_no_memory_prompt_end.py` was run once via `srun` (see job log) and does not need
re-running; `run_activation_patching.py --direction {unlearned_recipient,base_recipient}`
was run via ad hoc `srun`/`sbatch` (see provenance JSON next to each output CSV for exact
settings/seed/host).

## Known limitations (state these when citing results)

- Legacy local-Qwen judge, not canonical Kimi-K2 (repository-wide caveat).
- SAFE_TO_FAILURE groups are small (SatImp N=15, SimNPO N=12); all CIs are bootstrap and
  should be read as such, not as null-hypothesis significance tests.
- The memory-ablation condition changes the *content* fed to the model but keeps the
  same instruction boilerplate/truncation convention as the original generation
  pipeline; because that boilerplate is very long (~4,600+ tokens) relative to the
  1,800-token truncation window, the far-left portion of the full prompt (including the
  literal per-checkpoint "model name" string) is truncated away identically in both the
  with- and without-memory conditions -- confirmed empirically, not assumed.
- Teacher-forced continuations use each model's own *actual* generation-0 text; they are
  not length- or content-controlled between "safe" and "alt" (same caveat the repository's
  own native-direction-inventory analysis already raises for native response pairs).
