#!/bin/bash
#SBATCH --job-name=local_judge
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#SBATCH --partition=gpu
#SBATCH --nodelist=penelope
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=12:00:00

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
REPO="$REPO_ROOT"
cd "$REPO"

activate_unlearning_env base

export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}}"
export CUDA_HOME="${CUDA_HOME:-/nfs/cuda/cuda-12.2}"  # cluster default; override for your CUDA toolkit

# Avoid FlashInfer JIT sampling build. It fails with the current GCC/CUDA combo.
export VLLM_USE_FLASHINFER_SAMPLER=0

cd "$REPO/external/PersistBench"

echo "Starting local judge server on $(hostname)"
echo "Date: $(date)"
echo "Model: Qwen/Qwen2.5-7B-Instruct"
echo "Served name: local-judge"
echo "Port: 8001"

vllm serve "Qwen/Qwen2.5-7B-Instruct" \
  --served-model-name "local-judge" \
  --host 127.0.0.1 \
  --port 8001 \
  --dtype bfloat16 \
  --trust-remote-code \
  --gpu-memory-utilization 0.85 \
  --max-model-len 32768 \
  --enforce-eager
