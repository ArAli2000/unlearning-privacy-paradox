#!/bin/bash
#SBATCH --job-name=mech_pl_pop
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=logs/mech_pl_pop_%j.out
#SBATCH --error=logs/mech_pl_pop_%j.err

set -euo pipefail
set --

PROJECT_ROOT=/storage/ukp/work/elshashay/open-unlearning
export XDG_CACHE_HOME=/storage/ukp/work/elshashay/.cache
export TRITON_CACHE_DIR=/storage/ukp/work/elshashay/.triton/autotune
export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE="$HF_HOME"
mkdir -p "$PROJECT_ROOT/logs" "$TRITON_CACHE_DIR" "$HF_HOME"

module load cuda/12.2 || true
export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"

cd "$PROJECT_ROOT"
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID:-unset}"
echo "WORKDIR: $(pwd)"
nvidia-smi

python mechanistic/extract_privacylens_population.py
