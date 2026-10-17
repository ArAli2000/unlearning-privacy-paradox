#!/bin/bash
#SBATCH --job-name=gemma_judge
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=12:00:00
#SBATCH --array=0-14
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#
# Re-judges the 15 canonical, frozen PersistBench generation files (5 methods
# x 3 model-family tracks) with a locally-served google/gemma-2-9b-it judge,
# writing to a completely separate output tree. Never touches
# external/PersistBench/outputs/ (the existing Qwen-judged files).
#
# Uses a verified local copy of the model weights -- no Hugging Face
# authentication and no download are needed. Canonical model identity
# (google/gemma-2-9b-it) is recorded in provenance regardless of the physical
# path used to serve it. See gemma_availability_check.md for the full
# completeness/instruction-tuned verification of this local copy.
#
# One array task per input file (15 total): task index maps to the file list
# below via bash array indexing.

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../../scripts/common.sh"
cd "$REPO_ROOT"

activate_unlearning_env base   # vllm lives in the base conda env on this cluster, not "unlearning" -- see gemma_availability_check.md §4

GEMMA_MODEL_IDENTITY="google/gemma-2-9b-it"
GEMMA_LOCAL_PATH="/storage/ukp/shared/shared_model_weights/models--google--gemma-2-9b-it"

if [ ! -f "${GEMMA_LOCAL_PATH}/config.json" ]; then
  echo "ERROR: verified local Gemma path not found or moved: ${GEMMA_LOCAL_PATH}" >&2
  echo "       This script relies on the specific shared-cluster copy verified in" >&2
  echo "       gemma_availability_check.md -- re-verify before changing this path." >&2
  exit 1
fi

MODEL_NAME="${GEMMA_LOCAL_PATH}"   # served from the verified local path; canonical identity ${GEMMA_MODEL_IDENTITY} is recorded in provenance by gemma_judge.py
PORT=8002   # deliberately different from the Qwen judge server's 8001, so both could in principle run side by side
JOB_TAG="${SLURM_ARRAY_JOB_ID:-manual}_${SLURM_ARRAY_TASK_ID:-0}"

INPUTS=(
  "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_before.json"
  "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_satimp.json"
  "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_simnpo.json"
  "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_rmu.json"
  "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_wga.json"
  "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_before.json"
  "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_satimp.json"
  "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_simnpo.json"
  "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_rmu.json"
  "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_wga.json"
  "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_before.json"
  "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_satimp.json"
  "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_simnpo.json"
  "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_rmu.json"
  "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_wga.json"
)
OUTPUTS=(
  "external/PersistBench/outputs_gemma_judge/muse_news/muse_news_qwen25_before.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_news/muse_news_qwen25_satimp.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_news/muse_news_qwen25_simnpo.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_news/muse_news_qwen25_rmu.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_news/muse_news_qwen25_wga.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_books/muse_books_llama2_before.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_books/muse_books_llama2_satimp.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_books/muse_books_llama2_simnpo.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_books/muse_books_llama2_rmu.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_books/muse_books_llama2_wga.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_books/muse_books_qwen25_before.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_books/muse_books_qwen25_satimp.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_books/muse_books_qwen25_simnpo.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_books/muse_books_qwen25_rmu.gemma.json"
  "external/PersistBench/outputs_gemma_judge/muse_books/muse_books_qwen25_wga.gemma.json"
)

IDX="${SLURM_ARRAY_TASK_ID:-0}"
IN="${INPUTS[$IDX]}"
OUT="${OUTPUTS[$IDX]}"

if [ ! -f "$IN" ]; then
  echo "ERROR: expected canonical generation file not found: $IN" >&2
  echo "       Per the task instructions, do NOT regenerate it -- stop and report instead." >&2
  exit 1
fi

echo "Starting Gemma judge server (google/gemma-2-9b-it) on port ${PORT}..."
vllm serve "$MODEL_NAME" \
  --served-model-name gemma-judge \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 2048 \
  > "$REPO_ROOT/logs/vllm_gemma_judge_${JOB_TAG}.log" 2>&1 &
VLLM_PID=$!

cleanup() {
  echo "Stopping Gemma vLLM server if still running..."
  kill "$VLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for Gemma judge server to become ready..."
for i in $(seq 1 60); do
  if curl -s "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "Gemma judge server ready after ${i}0s."
    break
  fi
  sleep 10
done

python thesis/analysis/judge_robustness/gemma_judge.py \
  --input "$IN" \
  --output "$OUT" \
  --base-url "http://127.0.0.1:${PORT}/v1" \
  --concurrency 8
