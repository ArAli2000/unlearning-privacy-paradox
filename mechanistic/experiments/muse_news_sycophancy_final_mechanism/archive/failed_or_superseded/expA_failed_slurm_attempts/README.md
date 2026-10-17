# Archived: failed Experiment A SLURM attempts

Two SLURM job attempts for `expA_mcq/extract_missing_5.py` failed with ordinary
engineering bugs before the successful rerun (job 444584, see
`../../EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md`). Archived here for provenance;
not scientific data, not referenced by any script.

- **Job 444563** (FAILED, `ModuleNotFoundError: No module named 'common'`): the
  script's `sys.path.insert` for the MCQ helper module ran after the job's working
  directory context wasn't what the script assumed. Fixed in the version that ran
  as job 444584 (`common.py` import path corrected).
- **Job 444574** (FAILED, `RuntimeError: Inference tensors cannot be saved for
  backward`): the logit-lens projection through `model.lm_head` was run inside a
  `torch.inference_mode()` context incompatible with the later autograd-adjacent
  op. Fixed in job 444584 by adjusting the inference context.
- **Job 444584** (COMPLETED, exit code 0, 2026-09-23 18:41–18:42): successful
  rerun. Its output (`../../expA_mcq/missing5_readout.csv`,
  `../../expA_mcq/missing5_prepared.json`) is the canonical Experiment A data.

No scientific conclusions changed between attempts — 444563 and 444574 never
produced output; only the code was fixed between attempts.
