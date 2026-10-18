#!/bin/bash
#SBATCH --job-name=mech_pl_pos
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=logs/mech_pl_pos_%j.out
#SBATCH --error=logs/mech_pl_pos_%j.err
set -euo pipefail
set --
PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-$HOME/.triton/autotune}"
export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME"
mkdir -p "$PROJECT_ROOT/logs" "$TRITON_CACHE_DIR" "$HF_HOME"
module load cuda/12.2 || true
export CUDA_HOME="${CUDA_HOME:-/nfs/cuda/cuda-12.2}"  # cluster default; override for your CUDA toolkit
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
cd "$PROJECT_ROOT"
source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env
echo "HOSTNAME: $(hostname)"; echo "JOB ID: ${SLURM_JOB_ID:-unset}"; nvidia-smi
python mechanistic/privacylens/extract_privacylens_positions.py
