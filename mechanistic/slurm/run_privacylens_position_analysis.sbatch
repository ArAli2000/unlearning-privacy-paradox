#!/bin/bash
#SBATCH --job-name=mech_pos_cpu
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --qos=gpu-small
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
#SBATCH --output=logs/mech_pos_cpu_%j.out
#SBATCH --error=logs/mech_pos_cpu_%j.err
set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
cd "$PROJECT_ROOT"
source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env
export CUDA_VISIBLE_DEVICES=''
export MPLCONFIGDIR=/tmp/mech-mpl-${SLURM_JOB_ID}
export XDG_CACHE_HOME=/tmp/mech-cache-${SLURM_JOB_ID}
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" logs
python -u mechanistic/privacylens/analyze_privacylens_positions.py
