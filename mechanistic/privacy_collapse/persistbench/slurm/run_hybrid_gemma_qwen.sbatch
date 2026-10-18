#!/bin/bash
#SBATCH --job-name=pb_pair_judge
#SBATCH --output=logs/pb_pair_judge_%j.out
#SBATCH --error=logs/pb_pair_judge_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=100G
#SBATCH --time=08:00:00

set -euo pipefail
REPO="${REPO:-${SLURM_SUBMIT_DIR:-$PWD}}"
JUDGE=/mnt/beegfs/work/elshashay/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28
CONFIG="$REPO/mechanistic/privacy_collapse/persistbench/configs/hybrid_gemma_qwen.json"
PYTHON=/mnt/beegfs/work/elshashay/miniconda3/bin/python
VLLM=/mnt/beegfs/work/elshashay/miniconda3/bin/vllm
cd "$REPO"
mkdir -p logs
test -n "${OPENROUTER_API_KEY:-}" || { echo "OPENROUTER_API_KEY is not set"; exit 2; }
test -d "$JUDGE"
case "$JUDGE" in *muse*|*MUSE*) echo "Refusing experimental MUSE checkpoint"; exit 3;; esac

"$VLLM" serve "$JUDGE" \
  --served-model-name local-persistbench-judge \
  --host 127.0.0.1 --port 8001 \
  --dtype bfloat16 --trust-remote-code \
  --gpu-memory-utilization 0.85 \
  --max-model-len 32768 --enforce-eager &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 120); do
  curl -sf http://127.0.0.1:8001/v1/models >/dev/null && break
  sleep 5
done
curl -sf http://127.0.0.1:8001/v1/models >/dev/null

"$PYTHON" mechanistic/privacy_collapse/persistbench/run_remote.py \
  --config "$CONFIG" --phase run --openrouter-request-budget 49
