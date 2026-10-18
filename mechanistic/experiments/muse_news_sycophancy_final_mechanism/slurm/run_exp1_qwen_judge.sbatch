#!/bin/bash
#SBATCH --job-name=exp1_qwen_judge
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=120G
#SBATCH --cpus-per-task=8
#SBATCH --time=02:30:00
#SBATCH --output=logs/exp1_qwen_judge_%j.out
#SBATCH --error=logs/exp1_qwen_judge_%j.err

set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME=/storage/ukp/work/elshashay/.cache
export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-exp1-qwenjudge-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"

python mechanistic/experiments/muse_news_sycophancy_final_mechanism/run_exp1_qwen_judge.py
