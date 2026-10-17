#!/bin/bash
#SBATCH --job-name=gemma3_judge_smoke
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
# Gemma-3-12B-IT judge smoke test. Distinct from the earlier Gemma-2 smoke
# test (run_gemma_judge_smoketest.sbatch, jobs 438633/438653/438655/438656):
# that script is kept as-is, unmodified, as provenance of the Gemma-2 attempt
# (see GEMMA3_MODEL_SELECTION.md). This is a new script, not an edit of that
# one, so the Gemma-2 evidence trail stays intact.
#
# Runtime lessons carried over from the Gemma-2 smoke-test debugging
# (smoke_test/SLURM_DIAGNOSIS.md, smoke_test/GEMMA_VLLM_DIAGNOSIS.md):
#   - node "penelope" has an unresolved cluster-level SLURM launch failure
#     (RaisedSignal:53) unrelated to this job -- avoided by pinning to
#     "minerva" (proven healthy for this exact job shape: 438652/438653/
#     438655/438656 all completed there).
#   - $SLURM_SUBMIT_DIR (not ${BASH_SOURCE[0]}) must be used to locate the
#     repo, since SLURM runs jobs from a spool copy of this script.
#   - $HOME must be overridden to a writable path before vLLM starts, or
#     FlashInfer's JIT module import crashes with PermissionError; the same
#     env block also sets VLLM_USE_FLASHINFER_SAMPLER=0, independently
#     confirmed sufficient to skip that import path entirely.
#
# Uses the category-aware Gemma-3 prompt-length findings
# (gemma3_prompt_length_analysis.json / GEMMA3_CONTEXT_CHECK.md, job 438796):
# real max required context across all 3 categories is 9505 tokens
# (9249 max input + 256 output); --max-model-len 16384 below gives generous
# headroom while staying far under the model's native 131072 ceiling.
#
# Reuses the existing smoke_test/subset_input.json (already covers all three
# PersistBench categories -- 2x cross_domain, 1x sycophancy, 1x
# beneficial_memory_usage -- drawn from real frozen
# muse_news_qwen25_before.json generations, unmodified). Output goes to a
# NEW file (subset_output_gemma3.json), so the Gemma-2 smoke-test output
# (subset_output.json) is preserved untouched.

set -euo pipefail

REPO_ROOT="$(cd "${SLURM_SUBMIT_DIR:-$PWD}" && git rev-parse --show-toplevel)"
source "$REPO_ROOT/thesis/scripts/common.sh"
cd "$REPO_ROOT"

activate_unlearning_env base   # vllm lives in the base conda env on this cluster

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

GEMMA_LOCAL_PATH="/storage/ukp/shared/shared_model_weights/models--google--gemma-3-12b-it"
if [ ! -f "${GEMMA_LOCAL_PATH}/config.json" ]; then
  echo "ERROR: verified local Gemma-3 path not found: ${GEMMA_LOCAL_PATH}" >&2
  exit 1
fi

PORT=8002
JOB_TAG="${SLURM_JOB_ID:-manual}"

echo "Starting Gemma-3 judge server (smoke test) on port ${PORT}..."
vllm serve "${GEMMA_LOCAL_PATH}" \
  --served-model-name gemma3-judge \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 16384 \
  > "$REPO_ROOT/logs/vllm_gemma3_judge_smoke_${JOB_TAG}.log" 2>&1 &
VLLM_PID=$!

cleanup() {
  echo "Stopping Gemma-3 vLLM server if still running..."
  kill "$VLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for Gemma-3 judge server to become ready..."
READY=0
for i in $(seq 1 60); do
  if curl -s "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "Gemma-3 judge server ready after $((i * 10))s."
    READY=1
    break
  fi
  sleep 10
done
if [ "$READY" -ne 1 ]; then
  echo "ERROR: Gemma-3 judge server did not become ready in time." >&2
  echo "---- vLLM server log ----" >&2
  cat "$REPO_ROOT/logs/vllm_gemma3_judge_smoke_${JOB_TAG}.log" >&2
  exit 1
fi

python thesis/analysis/judge_robustness/gemma_judge.py \
  --input thesis/analysis/judge_robustness/smoke_test/subset_input.json \
  --output thesis/analysis/judge_robustness/smoke_test/subset_output_gemma3.json \
  --base-url "http://127.0.0.1:${PORT}/v1" \
  --concurrency 4

echo "Gemma-3 smoke test judging complete."
