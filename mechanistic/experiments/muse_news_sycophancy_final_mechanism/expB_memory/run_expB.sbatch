#!/bin/bash
#SBATCH --job-name=expB_memory_patch
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --nodelist=minerva
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=100G
#SBATCH --time=01:30:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail
PROJECT_ROOT=/mnt/beegfs/work/elshashay/open-unlearning
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME=/storage/ukp/work/elshashay/.cache
export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-expB-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"

python mechanistic/experiments/muse_news_sycophancy_final_mechanism/expB_memory/run_expB_memory_patch.py
