#!/bin/bash
#SBATCH --job-name=pb_native_prompt_end
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=08:00:00
#SBATCH --output=logs/pb_native_prompt_end_%j.out
#SBATCH --error=logs/pb_native_prompt_end_%j.err

set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-pb-native-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"
nvidia-smi

python mechanistic/privacy_collapse/persistbench_native/prepare_native_200.py
python mechanistic/privacy_collapse/persistbench_native/extract_prompt_end_hidden_states.py
python mechanistic/privacy_collapse/persistbench_native/validate_outputs.py
