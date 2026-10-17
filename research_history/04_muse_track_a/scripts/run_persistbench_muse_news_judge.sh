#!/bin/bash
#SBATCH --job-name=pbench_judge_muse
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --nodelist=penelope
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=12:00:00
#SBATCH --array=0-4%1

set -euo pipefail

REPO="/storage/ukp/work/elshashay/open-unlearning"
cd "$REPO"

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate base

export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE=/storage/ukp/work/elshashay/.cache/huggingface
export CUDA_HOME=/nfs/cuda/cuda-12.2
export JUDGE_PROVIDER=openrouter

JUDGE_MODEL="Qwen/Qwen2.5-7B-Instruct"
JUDGE_NAME="local-judge"
PORT=8001
JOB_TAG="${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"

FILES=(
  "outputs/muse_news_selected_full/muse_news_before.json"
  "outputs/muse_news_selected_full/muse_news_rmu_selected.json"
  "outputs/muse_news_selected_full/muse_news_wga_selected.json"
  "outputs/muse_news_selected_full/muse_news_simnpo_selected.json"
  "outputs/muse_news_selected_full/muse_news_satimp_selected.json"
)

FILE="${FILES[$SLURM_ARRAY_TASK_ID]}"

echo "======================================"
echo "PersistBench local judge"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "File: $FILE"
echo "Judge model: $JUDGE_MODEL"
echo "Judge name: $JUDGE_NAME"
echo "Port: $PORT"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================"

cd "$REPO/external/PersistBench"

echo "Starting local judge vLLM..."
vllm serve "$JUDGE_MODEL" \
  --served-model-name "$JUDGE_NAME" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --trust-remote-code \
  --gpu-memory-utilization 0.90 \
  --max-model-len 32768 \
  > "$REPO/logs/local_judge_vllm_${JOB_TAG}.log" 2>&1 &

VLLM_PID=$!

cleanup() {
  echo "Stopping local judge vLLM if still running..."
  kill "$VLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for local judge vLLM..."
for i in {1..180}; do
  if curl -s "http://127.0.0.1:${PORT}/v1/models" >/tmp/judge_models_${JOB_TAG}.json 2>/dev/null; then
    echo "Local judge vLLM is ready."
    cat /tmp/judge_models_${JOB_TAG}.json
    break
  fi
  sleep 5
done

if ! curl -s "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
  echo "ERROR: local judge vLLM did not start."
  tail -n 200 "$REPO/logs/local_judge_vllm_${JOB_TAG}.log" || true
  exit 1
fi

echo "Running PersistBench judge..."
benchmark judge "$FILE"

echo "Done judging: $FILE"
