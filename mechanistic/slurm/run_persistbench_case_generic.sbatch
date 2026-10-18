#!/bin/bash
#SBATCH --job-name=mech_pb_generic
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail

CASE_DIR="${1:?Usage: sbatch run_persistbench_case_generic.sbatch CASE_DIR}"

PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"

export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME"
export MPLCONFIGDIR=/tmp/mpl-mech-pb-${SLURM_JOB_ID}
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"

module load cuda/12.2 || true
export CUDA_HOME="${CUDA_HOME:-/nfs/cuda/cuda-12.2}"  # cluster default; override for your CUDA toolkit
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"

cd "$PROJECT_ROOT"

source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"
echo "CASE DIR: ${CASE_DIR}"
nvidia-smi

python mechanistic/persistbench/extract_persistbench_case_generic.py \
    --case-dir "$CASE_DIR"
