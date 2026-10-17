#!/bin/bash
#SBATCH --job-name=pbench_qbooks_judge
#SBATCH --output=logs/pbench_qbooks_judge_%j.out
#SBATCH --error=logs/pbench_qbooks_judge_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=04:00:00

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
REPO="$REPO_ROOT"
PBENCH="$REPO/external/PersistBench"
OUTPUT_DIR="$PBENCH/outputs/muse_books_qwen25_selected_full"

cd "$PBENCH"

activate_unlearning_env base

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


# Use writable directories on compute nodes.
export HOME="/storage/ukp/work/elshashay"
export XDG_CACHE_HOME="$HOME/.cache"
export HF_HOME="$XDG_CACHE_HOME/huggingface"
export TRANSFORMERS_CACHE="$HF_HOME"
export FLASHINFER_WORKSPACE_DIR="$XDG_CACHE_HOME/flashinfer"
export VLLM_NO_USAGE_STATS=1
export DO_NOT_TRACK=1

mkdir -p \
    "$XDG_CACHE_HOME" \
    "$HF_HOME" \
    "$FLASHINFER_WORKSPACE_DIR"


export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE="$HF_HOME"
export CUDA_HOME=/nfs/cuda/cuda-12.2

# Avoid the FlashInfer sampling problem encountered previously.
export VLLM_USE_FLASHINFER_SAMPLER=0

# Use a job-specific port to avoid conflicts with another vLLM server.
PORT=$((8000 + SLURM_JOB_ID % 1000))
VLLM_LOG="$REPO/logs/vllm_qbooks_judge_${SLURM_JOB_ID}.log"

echo "======================================"
echo "PersistBench MUSE-Books Qwen judge"
echo "Node: $(hostname)"
echo "Job: $SLURM_JOB_ID"
echo "Port: $PORT"
echo "Output directory: $OUTPUT_DIR"
echo "Date: $(date)"
echo "======================================"

mapfile -t FILES < <(
    find "$OUTPUT_DIR" \
        -maxdepth 1 \
        -type f \
        -name "muse_books_qwen25_*.json" \
        | sort
)

if [ "${#FILES[@]}" -ne 5 ]; then
    echo "ERROR: Expected 5 JSON files, found ${#FILES[@]}"
    printf '%s\n' "${FILES[@]}"
    exit 1
fi

printf 'Files to judge:\n'
printf '  %s\n' "${FILES[@]}"

echo
echo "Starting Qwen2.5-7B local judge."

vllm serve Qwen/Qwen2.5-7B-Instruct \
    --served-model-name local-judge \
    --host 127.0.0.1 \
    --port "$PORT" \
    --dtype bfloat16 \
    --gpu-memory-utilization 0.85 \
    --max-model-len 32768 \
    --trust-remote-code \
    --enforce-eager \
    > "$VLLM_LOG" 2>&1 &

VLLM_PID=$!

cleanup() {
    echo "Stopping local judge."
    kill "$VLLM_PID" 2>/dev/null || true
    wait "$VLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Checking judge server readiness."

READY=0
for _ in $(seq 1 180); do
    if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null; then
        READY=1
        break
    fi

    if ! kill -0 "$VLLM_PID" 2>/dev/null; then
        echo "ERROR: vLLM exited before becoming ready."
        tail -n 150 "$VLLM_LOG"
        exit 1
    fi

    sleep 5
done

if [ "$READY" -ne 1 ]; then
    echo "ERROR: Judge server did not become ready."
    tail -n 150 "$VLLM_LOG"
    exit 1
fi

echo "Local judge is ready."

export OPENAI_API_KEY="dummy"
export OPENROUTER_API_KEY="dummy"
export OPENAI_BASE_URL="http://127.0.0.1:${PORT}/v1"
export OPENAI_API_BASE="http://127.0.0.1:${PORT}/v1"
export JUDGE_PROVIDER="openrouter"

OVERALL_STATUS=0

for FILE_ABS in "${FILES[@]}"; do
    FILE_REL="${FILE_ABS#$PBENCH/}"

    echo
    echo "======================================"
    echo "Judging: $FILE_REL"
    echo "Started: $(date)"
    echo "======================================"

    if .venv/bin/benchmark judge \
        "$FILE_REL" \
        --judge-provider openrouter \
        --concurrency 3
    then
        echo "Completed: $FILE_REL"
    else
        echo "WARNING: Judge command reported remaining failures for $FILE_REL"
        OVERALL_STATUS=1
    fi
done

echo
echo "======================================"
echo "All five files were processed."
echo "Finished: $(date)"
echo "======================================"

exit "$OVERALL_STATUS"
