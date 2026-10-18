#!/bin/bash
#SBATCH --job-name=pb_syc_mcq
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=08:00:00
#SBATCH --output=logs/pb_syc_mcq_%j.out
#SBATCH --error=logs/pb_syc_mcq_%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$PWD}"
mkdir -p logs
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID};mkdir -p "$TRITON_CACHE_DIR"
source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env
module load cuda/12.2 || true
python mechanistic/privacy_collapse/persistbench_sycophancy_mcq/validate_static.py
python mechanistic/privacy_collapse/persistbench_sycophancy_mcq/extract.py
python mechanistic/privacy_collapse/persistbench_sycophancy_mcq/analyze.py
