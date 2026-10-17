#!/bin/bash
#SBATCH --job-name=pb_syc_tf_logprobs
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=120G
#SBATCH --cpus-per-task=8
#SBATCH --time=06:00:00
#SBATCH --output=logs/pb_syc_tf_logprobs_%j.out
#SBATCH --error=logs/pb_syc_tf_logprobs_%j.err

set -euo pipefail
PROJECT_ROOT=/mnt/beegfs/work/elshashay/open-unlearning
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME=/storage/ukp/work/elshashay/.cache
export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-pb-syc-tf-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"
nvidia-smi -L

python mechanistic/experiments/muse_news_sycophancy_paradox/extract_teacher_forced_layer_logprobs.py
python mechanistic/experiments/muse_news_sycophancy_paradox/analyze_teacher_forced_layer_logprobs.py
