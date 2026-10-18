#!/bin/bash
#SBATCH --job-name=pb_patch_fwd
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --output=logs/pb_patch_fwd_%j.out
#SBATCH --error=logs/pb_patch_fwd_%j.err

set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-pb-patchfwd-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"
nvidia-smi

python mechanistic/muse_news/muse_news_activation_patching.py \
  --max-per-method 3 --max-cross-domain 3
