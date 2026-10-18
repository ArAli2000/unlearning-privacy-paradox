#!/bin/bash
#SBATCH --job-name=pb_syc_patch_clean
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=120G
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --output=logs/pb_syc_patch_clean_%j.out
#SBATCH --error=logs/pb_syc_patch_clean_%j.err

set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-pb-syc-patch-clean-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"
nvidia-smi -L

SCRIPT_DIR=mechanistic/experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit

python "$SCRIPT_DIR/run_activation_patching_clean.py" --direction unlearned_recipient
python "$SCRIPT_DIR/run_activation_patching_clean.py" --direction base_recipient
