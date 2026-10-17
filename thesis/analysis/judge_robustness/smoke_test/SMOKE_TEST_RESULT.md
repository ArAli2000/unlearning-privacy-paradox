# Gemma judge smoke test — result log

## Attempt 1 — jobs 438606–438610 (node `penelope`)

FAILED before any user code ran. Root cause: node-specific SLURM launch
failure (`RaisedSignal:53`), isolated to node `penelope` via a minimal control
test on a different node (`rubeus`, job 438611, succeeded immediately with an
identical header). See `SLURM_DIAGNOSIS.md`. Fix: pinned the job to `rubeus`
via `#SBATCH --nodelist=rubeus`.

## Attempt 2 — job 438612 (node `rubeus`, `--nodelist` fix only)

FAILED in <1s. Cause: `${BASH_SOURCE[0]}`-based self-location broke because
SLURM copies the submitted script into a spool directory
(`/var/spool/slurm/slurmd/job438612/slurm_script`) before running it, so the
relative path to `thesis/scripts/common.sh` no longer resolved. Fix: resolve
`REPO_ROOT` via `$SLURM_SUBMIT_DIR` + `git rev-parse --show-toplevel` instead.
See `SLURM_DIAGNOSIS.md`.

## Attempt 3 — job 438615 (node `rubeus`, path-resolution fix applied)

Ran 10m14s — real progress. vLLM started, correctly resolved
`Gemma2ForCausalLM`, initialized CUDA/NCCL distributed state
(`world_size=1 rank=0`), then the **engine-core GPU worker crashed 3 seconds
later** with:

```
PermissionError: [Errno 13] Permission denied: '/home/elshashay'
```

raised from FlashInfer's JIT module import (`flashinfer/jit/core.py`,
`os.makedirs(jit_env.FLASHINFER_WORKSPACE_DIR, exist_ok=True)`), because the
script never overrode `$HOME`/cache directories the way every other
successful vLLM-serving script in this repo already does. **Not a model,
GPU, CUDA, or memory problem.** Full analysis: `GEMMA_VLLM_DIAGNOSIS.md`.

Fix applied: added the standard `HOME`/`XDG_CACHE_HOME`/`HF_HOME`/
`TRITON_CACHE_DIR`/`FLASHINFER_WORKSPACE_DIR`/`VLLM_USE_FLASHINFER_SAMPLER=0`
environment block (copied verbatim from
`thesis/scripts/persistbench/run_persistbench_muse_books_qwen25_localjudge.sh`'s
proven pattern) to `run_gemma_judge_smoketest.sbatch`. No vLLM flag, model
choice, or judging code changed.

## Attempt 4 — job 438633 (node `rubeus`, HOME/FlashInfer fix applied)

Submitted 2026-09-14. **Status: pending / in progress — this section will be
updated once the job completes.**
