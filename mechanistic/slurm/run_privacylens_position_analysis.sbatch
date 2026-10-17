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
PROJECT_ROOT=/storage/ukp/work/elshashay/open-unlearning
cd "$PROJECT_ROOT"
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning
export CUDA_VISIBLE_DEVICES=''
export MPLCONFIGDIR=/tmp/mech-mpl-${SLURM_JOB_ID}
export XDG_CACHE_HOME=/tmp/mech-cache-${SLURM_JOB_ID}
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" logs
python -u mechanistic/analyze_privacylens_positions.py
