#!/bin/bash
#SBATCH --job-name=pb_wga_judge160
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=180G
#SBATCH --cpus-per-task=8
#SBATCH --time=08:00:00
#SBATCH --array=0-0%1
#SBATCH --output=logs/pb_wga_judge160_%A_%a.out
#SBATCH --error=logs/pb_wga_judge160_%A_%a.err

set -euo pipefail

REPO=/storage/ukp/work/elshashay/open-unlearning
PBENCH="$REPO/external/PersistBench"
MANIFEST="$REPO/research_history/05_wmdp_side_investigation/manifests/persistbench_qwen_wga_ckpt160.tsv"

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME=$HOME/.cache
export HF_HOME=$HOME/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TRITON_CACHE_DIR=$HOME/.triton/autotune
export FLASHINFER_WORKSPACE_DIR=$HOME/.cache/flashinfer
export VLLM_USAGE_STATS_DIR=$HOME/.cache/vllm/usage
export VLLM_USE_FLASHINFER_SAMPLER=0

mkdir -p "$XDG_CACHE_HOME" "$HF_HOME" "$HF_DATASETS_CACHE" "$TRITON_CACHE_DIR" "$FLASHINFER_WORKSPACE_DIR" "$VLLM_USAGE_STATS_DIR"
mkdir -p "$REPO/logs"

source /storage/ukp/work/elshashay/miniconda3/etc/profile.d/conda.sh
conda activate base

LABEL=$(awk -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $1}' "$MANIFEST")

SRC="$PBENCH/outputs/wmdp_cyber_qwen_wga_ckpt_sweep_full/${LABEL}.json"
OUTDIR="$PBENCH/outputs/wmdp_cyber_qwen_wga_ckpt_sweep_full_localjudge"
DST="$OUTDIR/${LABEL}_localjudge.json"

PORT=$((8900 + SLURM_ARRAY_TASK_ID))

export OPENAI_API_KEY=EMPTY
export OPENAI_BASE_URL="http://127.0.0.1:${PORT}/v1"
export OPENAI_API_BASE="http://127.0.0.1:${PORT}/v1"
export OPENROUTER_API_KEY=EMPTY
export OPENROUTER_BASE_URL="http://127.0.0.1:${PORT}/v1"

mkdir -p "$OUTDIR"

if [[ ! -f "$SRC" ]]; then
  echo "Missing source generation file: $SRC"
  exit 1
fi

cp "$SRC" "$DST"

echo "======================================================"
echo "PersistBench WMDP-Cyber judging"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Label: $LABEL"
echo "Input: $SRC"
echo "Judged output: $DST"
echo "Port: $PORT"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================================"

cd "$PBENCH"

vllm serve "Qwen/Qwen2.5-7B-Instruct" \
  --served-model-name "local-judge" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --trust-remote-code \
  --gpu-memory-utilization 0.85 \
  --max-model-len 32768 \
  --enforce-eager > "$REPO/logs/vllm_judge_${LABEL}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log" 2>&1 &

VLLM_PID=$!

cleanup() {
  echo "Stopping judge vLLM PID $VLLM_PID"
  kill "$VLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for local judge vLLM..."
for i in {1..180}; do
  if curl -s "http://127.0.0.1:${PORT}/v1/models" >/tmp/vllm_judge_models_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.json 2>/dev/null; then
    echo "Judge vLLM is ready."
    cat /tmp/vllm_judge_models_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.json
    break
  fi
  sleep 5
done

if ! curl -s "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
  echo "ERROR: judge vLLM did not start."
  tail -n 120 "$REPO/logs/vllm_judge_${LABEL}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log" || true
  exit 1
fi

echo "Running PersistBench judge..."
benchmark judge "$DST"

echo "Done judging: $LABEL"
echo "Output: $DST"
