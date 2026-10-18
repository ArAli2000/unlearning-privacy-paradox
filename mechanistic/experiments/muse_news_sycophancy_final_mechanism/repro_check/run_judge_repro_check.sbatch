#!/bin/bash
#SBATCH --job-name=exp1_repro_judge
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --nodelist=minerva
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=100G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-exp1-reprojudge-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"

python mechanistic/experiments/muse_news_sycophancy_final_mechanism/repro_check/judge_repro_check.py
