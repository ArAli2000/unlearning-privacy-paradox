#!/bin/bash
#SBATCH --job-name=mech_pl_single
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=logs/mech_pl_single_%j.out
#SBATCH --error=logs/mech_pl_single_%j.err

set -euo pipefail

# Capture the batch-script argument before sourcing Conda. Sourced shell scripts
# inherit the caller's positional parameters unless they are cleared.
if [ "$#" -gt 1 ]; then
  echo "Usage: sbatch $0 [sample-id]" >&2
  exit 2
fi
SAMPLE_ID_TO_RUN="${1:-${SAMPLE_ID:-main1}}"
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

echo "PRIVACYLENS SAMPLE: $SAMPLE_ID_TO_RUN"

python mechanistic/privacylens/extract_single_privacylens.py \
  --sample-id "$SAMPLE_ID_TO_RUN"
