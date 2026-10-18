#!/bin/bash
#SBATCH --job-name=pb_mistral_rewrite3
#SBATCH --output=logs/pb_mistral_rewrite3_%j.out
#SBATCH --error=logs/pb_mistral_rewrite3_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
set -euo pipefail
REPO="${REPO:-${SLURM_SUBMIT_DIR:-$PWD}}"
PYTHON=/mnt/beegfs/work/elshashay/miniconda3/bin/python
VLLM=/mnt/beegfs/work/elshashay/miniconda3/bin/vllm
SNAPSHOT="$REPO/mechanistic/privacy_collapse/persistbench/model_cache/models--mistralai--Mistral-7B-Instruct-v0.3/snapshots/c170c708c41dac9275d15a8fff4eca08d52bab71"
CONFIG="$REPO/mechanistic/privacy_collapse/persistbench/configs/local_mistral_qwen.json"
SERVER_LOG="$REPO/logs/pb_mistral_rewrite3_${SLURM_JOB_ID}_server.log"
GPU_LOG="$REPO/logs/pb_mistral_rewrite3_${SLURM_JOB_ID}_gpu.csv"
PORT=8002
cd "$REPO"; mkdir -p logs
nvidia-smi --query-gpu=timestamp,name,memory.used --format=csv -l 1 >"$GPU_LOG" & GPU_MON_PID=$!
export VLLM_USE_FLASHINFER_SAMPLER=0
"$VLLM" serve "$SNAPSHOT" --served-model-name local-persistbench-generator --host 127.0.0.1 --port "$PORT" --dtype bfloat16 --max-model-len 32768 --gpu-memory-utilization 0.75 --enforce-eager >"$SERVER_LOG" 2>&1 & SERVER_PID=$!
cleanup(){ kill "$GPU_MON_PID" 2>/dev/null || true; wait "$GPU_MON_PID" 2>/dev/null || true; kill "$SERVER_PID" 2>/dev/null || true; wait "$SERVER_PID" 2>/dev/null || true; }; trap cleanup EXIT
ready=0
for _ in $(seq 1 180); do if curl --silent --fail "http://127.0.0.1:${PORT}/v1/models" >/dev/null; then ready=1; break; fi; if ! kill -0 "$SERVER_PID" 2>/dev/null; then exit 1; fi; sleep 2; done
test "$ready" -eq 1
"$PYTHON" mechanistic/privacy_collapse/persistbench/run_local_matched_rewrite_stress.py --config "$CONFIG"
