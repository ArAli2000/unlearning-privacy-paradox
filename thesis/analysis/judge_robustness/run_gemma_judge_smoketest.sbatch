#!/bin/bash
#SBATCH --job-name=gemma_judge_smoke
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --nodelist=minerva
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#
# NOTE (2026-09-14): --nodelist=rubeus added after diagnosing a node-specific
# SLURM launch failure on the auto-assigned node "penelope" (RaisedSignal:53
# on every attempt, including a byte-for-byte replica of the previously
# successful run_local_judge_server_penelope.sh header). A trivial diagnostic
# job with an otherwise-identical header succeeded immediately on "rubeus".
# See thesis/analysis/judge_robustness/smoke_test/SLURM_DIAGNOSIS.md.
#
# NOTE (2026-09-14, later): rubeus's 8 a180 GPUs were all fully allocated by
# other users at submission time (`scontrol show node rubeus` showed
# AllocTRES gres/gpu:a180=8), so job 438638 sat PENDING(Resources) with a
# backfill ETA of ~3 days. Re-checked penelope with a trivial GPU diagnostic
# (job 438650): it still fails identically (ExitCode 0:53, no output files),
# so the earlier launch issue there is NOT resolved and it remains unusable.
# Switched instead to "minerva" -- same Ampere GPU generation, gpu:a100:1
# (40GB, still far more than Gemma-2-9B-IT's ~18.5GB weights + KV cache at
# max-model-len 2048 need), confirmed healthy/idle via `scontrol show node`
# (5 of 8 A100s free at the time) and via a trivial diagnostic (job 438652,
# COMPLETED, real nvidia-smi output). No vLLM flag changed -- 40GB VRAM is
# ample at the same --gpu-memory-utilization 0.90.
#
# Smoke test for the Gemma judge pipeline: judges a 4-row / 10-generation
# subset (covering all 3 PersistBench rubrics: cross_domain, sycophancy,
# beneficial_memory_usage) extracted from an existing frozen generation file.
# The subset file (smoke_test/subset_input.json) is a standalone copy created
# without touching the original; output goes to smoke_test/subset_output.json.

set -euo pipefail

# NOTE (2026-09-14): SLURM on this cluster copies the submitted script into a
# spool directory (/var/spool/slurm/slurmd/job<N>/slurm_script) before running
# it, so ${BASH_SOURCE[0]}-based self-location (as common.sh's own sourcing
# convention normally uses) resolves to that spool path, not this file's real
# location -- "../../scripts/common.sh" then does not exist. SLURM_SUBMIT_DIR
# (the directory `sbatch` was invoked from, always the repo root by this
# codebase's own convention) is unaffected by that copy, so it is used here
# instead for this one hop only; common.sh itself is unaffected once reached.
REPO_ROOT="$(cd "${SLURM_SUBMIT_DIR:-$PWD}" && git rev-parse --show-toplevel)"
source "$REPO_ROOT/thesis/scripts/common.sh"
cd "$REPO_ROOT"

activate_unlearning_env base

# NOTE (2026-09-14): job 438615 reached engine-core startup on rubeus and
# failed with `PermissionError: [Errno 13] Permission denied: '/home/elshashay'`,
# raised from flashinfer/jit/core.py's `os.makedirs(jit_env.FLASHINFER_WORKSPACE_DIR)`
# (default value confirmed as $HOME/.cache/flashinfer/<version> via direct
# interpreter check). $HOME (/home/elshashay) is not writable from compute
# nodes in this cluster -- this is not a model/GPU/CUDA/memory issue. Every
# historically-successful local-judge/vLLM-serving script in this repo (e.g.
# thesis/scripts/persistbench/run_persistbench_muse_books_qwen25_localjudge.sh)
# already works around exactly this by overriding HOME to a writable path and
# setting VLLM_USE_FLASHINFER_SAMPLER=0. Confirmed via source inspection of
# vllm/v1/sample/ops/topk_topp_sampler.py::flashinfer_sampler_supported(): the
# VLLM_USE_FLASHINFER_SAMPLER check happens BEFORE the flashinfer package is
# imported, so this flag alone is sufficient to skip the crashing import path.
# See thesis/analysis/judge_robustness/smoke_test/GEMMA_VLLM_DIAGNOSIS.md.
export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME="$HOME/.cache"
export HF_HOME="$XDG_CACHE_HOME/huggingface"
export TRANSFORMERS_CACHE="$HF_HOME"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
export TRITON_CACHE_DIR="$HOME/.triton/autotune"
export FLASHINFER_WORKSPACE_DIR="$XDG_CACHE_HOME/flashinfer"
export VLLM_USAGE_STATS_DIR="$HOME/.cache/vllm/usage"
export VLLM_USE_FLASHINFER_SAMPLER=0
mkdir -p "$XDG_CACHE_HOME" "$HF_HOME" "$HF_DATASETS_CACHE" "$TRITON_CACHE_DIR" "$FLASHINFER_WORKSPACE_DIR" "$VLLM_USAGE_STATS_DIR"

GEMMA_LOCAL_PATH="/storage/ukp/shared/shared_model_weights/models--google--gemma-2-9b-it"
if [ ! -f "${GEMMA_LOCAL_PATH}/config.json" ]; then
  echo "ERROR: verified local Gemma path not found: ${GEMMA_LOCAL_PATH}" >&2
  exit 1
fi

PORT=8002
JOB_TAG="${SLURM_JOB_ID:-manual}"

echo "Starting Gemma judge server (smoke test) on port ${PORT}..."
# NOTE (2026-09-14): job 438653 (real judging, no more system-role/permission
# errors) hit `max_model_len=2048` being too small (observed: 1793 input +
# 256 output = 2049). Raised to 4096 based on a rough char-count proxy over
# raw memories/query/response text -- but job 438655 showed that proxy
# under-measured the REAL prompt (which also includes the judge system
# prompt + rubric instructions + STRICT_INSTRUCTION wrapper): one real
# request needed >=3841 input tokens, almost exhausting 4096 again. Rather
# than guess a third number, using google/gemma-2-9b-it's own hard ceiling
# from config.json (max_position_embeddings=8192) directly -- this is not
# an arbitrary guess, it is the model's actual native maximum, so no real
# prompt in this benchmark can exceed it. KV-cache cost for 8192 tokens is
# still trivial relative to the 40GB card (18.5GB weights + this KV cache
# comfortably fit under gpu-memory-utilization 0.90). No prompt/rubric text
# changed -- only the server's context-length ceiling.
vllm serve "${GEMMA_LOCAL_PATH}" \
  --served-model-name gemma-judge \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  > "$REPO_ROOT/logs/vllm_gemma_judge_smoke_${JOB_TAG}.log" 2>&1 &
VLLM_PID=$!

cleanup() {
  echo "Stopping Gemma vLLM server if still running..."
  kill "$VLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for Gemma judge server to become ready..."
READY=0
for i in $(seq 1 60); do
  if curl -s "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "Gemma judge server ready after $((i * 10))s."
    READY=1
    break
  fi
  sleep 10
done
if [ "$READY" -ne 1 ]; then
  echo "ERROR: Gemma judge server did not become ready in time." >&2
  echo "---- vLLM server log ----" >&2
  cat "$REPO_ROOT/logs/vllm_gemma_judge_smoke_${JOB_TAG}.log" >&2
  exit 1
fi

python thesis/analysis/judge_robustness/gemma_judge.py \
  --input thesis/analysis/judge_robustness/smoke_test/subset_input.json \
  --output thesis/analysis/judge_robustness/smoke_test/subset_output.json \
  --base-url "http://127.0.0.1:${PORT}/v1" \
  --concurrency 4

echo "Smoke test judging complete."
