#!/bin/bash
#SBATCH --job-name=pb_syc_patch
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=120G
#SBATCH --cpus-per-task=8
#SBATCH --time=06:00:00
#SBATCH --output=logs/pb_syc_patch_%j.out
#SBATCH --error=logs/pb_syc_patch_%j.err

set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME=/storage/ukp/work/elshashay/.cache
export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-pb-syc-patch-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"
nvidia-smi -L

python mechanistic/experiments/muse_news_sycophancy_paradox/run_activation_patching.py --direction unlearned_recipient
python mechanistic/experiments/muse_news_sycophancy_paradox/run_activation_patching.py --direction base_recipient
python mechanistic/experiments/muse_news_sycophancy_paradox/analyze_activation_patching.py
