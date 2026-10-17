#!/bin/bash
#SBATCH --job-name=exp1_gemma_judge
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --nodelist=minerva
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=03:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#
# Second-judge (Gemma-3-12b-it) pass over the Experiment 1 generations. Same
# vLLM server + gemma_judge.py setup as
# thesis/analysis/judge_robustness/run_gemma3_judge_full.sbatch, but on this
# experiment's single generation file.

set -euo pipefail

REPO_ROOT="$(cd "${SLURM_SUBMIT_DIR:-$PWD}" && git rev-parse --show-toplevel)"
source "$REPO_ROOT/thesis/scripts/common.sh"
cd "$REPO_ROOT"

activate_unlearning_env base

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

EXP_DIR="mechanistic/experiments/muse_news_sycophancy_final_mechanism"
GEN_DIR="$EXP_DIR/exp1_generation"
SCHEMA_FILE="$GEN_DIR/exp1_generations_gemma_schema.json"
GEMMA_OUT="$GEN_DIR/exp1_generations_gemma_schema.gemma3.json"

if [ ! -f "$GEN_DIR/exp1_generations_qwen_judged.json" ]; then
  echo "ERROR: expected Qwen-judged generations not found at $GEN_DIR/exp1_generations_qwen_judged.json" >&2
  echo "       Run run_exp1_qwen_judge.sbatch first." >&2
  exit 1
fi

echo "Building Gemma-schema input from Qwen-judged generations..."
python "$EXP_DIR/exp1_to_gemma_schema.py"

PORT=8002
JOB_TAG="${SLURM_JOB_ID:-manual}"

echo "Starting Gemma-3 judge server on port ${PORT}..."
vllm serve "${GEMMA_LOCAL_PATH}" \
  --served-model-name gemma3-judge \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 16384 \
  > "$REPO_ROOT/logs/vllm_exp1_gemma3_judge_${JOB_TAG}.log" 2>&1 &
VLLM_PID=$!

cleanup() {
  echo "Stopping Gemma-3 vLLM server if still running..."
  kill "$VLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for Gemma-3 judge server to become ready..."
READY=0
for i in $(seq 1 90); do
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
  cat "$REPO_ROOT/logs/vllm_exp1_gemma3_judge_${JOB_TAG}.log" >&2
  exit 1
fi

echo "Judging $SCHEMA_FILE -> $GEMMA_OUT"
python thesis/analysis/judge_robustness/gemma_judge.py \
  --input "$SCHEMA_FILE" \
  --output "$GEMMA_OUT" \
  --base-url "http://127.0.0.1:${PORT}/v1" \
  --concurrency 8

echo "Merging Gemma judgments back into main exp1 record format..."
python "$EXP_DIR/merge_gemma_judgments.py"

echo "Done."
