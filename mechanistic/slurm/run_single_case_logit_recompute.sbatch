#!/bin/bash
#SBATCH --job-name=mech_pb_lens
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=80G
#SBATCH --cpus-per-task=4
#SBATCH --time=01:00:00
#SBATCH --output=logs/mech_pb_lens_%j.out
#SBATCH --error=logs/mech_pb_lens_%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$PWD}"
source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env
module load cuda/12.2 || true
export CUDA_HOME="${CUDA_HOME:-/nfs/cuda/cuda-12.2}"  # cluster default; override for your CUDA toolkit
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
echo "HOSTNAME: $(hostname)"; echo "JOB ID: ${SLURM_JOB_ID}"
python mechanistic/persistbench/recompute_single_case_logit_lens.py
