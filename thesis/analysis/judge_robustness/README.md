# Judge-robustness experiment: Qwen judge vs. Gemma judge

**Status (2026-09-14, latest): STOPPED at the SLURM smoke test — an infrastructure-level job-launch failure (`RaisedSignal:53`), unrelated to Gemma/model availability. See `smoke_test/SMOKE_TEST_RESULT.md`. No Gemma inference has completed. No existing file was modified.**

**History**: Phase 0 (discovery) and Phase 1 (Gemma availability) are complete — `google/gemma-2-9b-it` was found locally at `/storage/ukp/shared/shared_model_weights/models--google--gemma-2-9b-it` (verified complete and instruction-tuned; no HF auth needed). The judging pipeline (`gemma_judge.py`, `run_gemma_judge.sbatch`) was updated to use this path. A required smoke test was then run before the full 15-task array, per instruction — and it failed for reasons unrelated to any of the above (see below).

## What this directory contains right now

- `discovery_report.md` — Phase 0, complete. Full audit of the existing PersistBench judging pipeline: exact checkpoints, exact generation files, exact judge prompts/schema/model, exact FR@K implementation, exact generation validator.
- `gemma_availability_check.md` — Phase 1, complete, and this is where the process stopped: `google/gemma-2-9b-it` cannot currently be loaded in this environment (see that file for the exact, verified reason).
- `gemma_judge.py`, `run_gemma_judge.sbatch` — Phase 2/3 preparation: a judging script and SLURM launcher, written and ready, adapted from the existing Qwen local-judge implementation, reusing the same prompts/schema/rubric/output shape. **Not yet run** — see the blocker below. Written now so that no time is lost once the blocker is resolved.

## Why Phases 2–10 were not attempted

The task's own instructions for Phase 1 state: *"If `google/gemma-2-9b-it` is unavailable or incompatible, STOP and report the specific reason before substituting another model. Do not silently choose a different Gemma model."* That condition is met (see `gemma_availability_check.md`) — proceeding to Phases 3–10 would require either fabricating Gemma judgments (not acceptable) or silently substituting a different, ungated model (explicitly forbidden). Neither is done here.

## What needs to happen to unblock this

One of:
1. An `HF_TOKEN` (or `HUGGING_FACE_HUB_TOKEN`) environment variable, belonging to an account that has requested and been granted access to `google/gemma-2-9b-it` on Hugging Face, made available in this environment; or
2. Confirmation that a different, already-accessible Gemma checkpoint should be used instead (this will **not** be chosen automatically — it needs your explicit instruction, per the task's own rule); or
3. The model weights pre-downloaded to this cluster by some other means (e.g. an admin-provided shared cache) and their exact local path.

Once any of the above is true, re-run this same task and Phases 2–10 will proceed using the prepared script/SLURM job below (adjusted if a different model path/name is confirmed).
