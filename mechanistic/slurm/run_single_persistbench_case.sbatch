#!/bin/bash
#SBATCH --job-name=mech_pb_case
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --output=logs/mech_pb_case_%j.out
#SBATCH --error=logs/mech_pb_case_%j.err
set -euo pipefail
PROJECT_ROOT=/storage/ukp/work/elshashay/open-unlearning
export XDG_CACHE_HOME=/storage/ukp/work/elshashay/.cache
export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE="$HF_HOME"
export MPLCONFIGDIR=/tmp/mpl-mech-pb-${SLURM_JOB_ID}
module load cuda/12.2 || true
export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
cd "$PROJECT_ROOT"
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning
echo "HOSTNAME: $(hostname)"; echo "JOB ID: ${SLURM_JOB_ID}"; nvidia-smi
python mechanistic/persistbench/extract_single_persistbench_case.py
