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
PROJECT_ROOT=/mnt/beegfs/work/elshashay/open-unlearning
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME=/storage/ukp/work/elshashay/.cache
export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-pb-syc-patch-clean-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"
nvidia-smi -L

SCRIPT_DIR=mechanistic/experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit

python "$SCRIPT_DIR/run_activation_patching_clean.py" --direction unlearned_recipient
python "$SCRIPT_DIR/run_activation_patching_clean.py" --direction base_recipient
