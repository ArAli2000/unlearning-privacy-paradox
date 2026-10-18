#!/bin/bash
#SBATCH --job-name=pc_mn_qwen7b
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=08:00:00
#SBATCH --output=logs/privacy_collapse_mn_qwen7b_%j.out
#SBATCH --error=logs/privacy_collapse_mn_qwen7b_%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:-$PWD}"
mkdir -p logs
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env
module load cuda/12.2 || true

python mechanistic/privacy_collapse/extract_pilot.py
python mechanistic/privacy_collapse/validate_outputs.py
python mechanistic/privacy_collapse/analyze_pilot.py
