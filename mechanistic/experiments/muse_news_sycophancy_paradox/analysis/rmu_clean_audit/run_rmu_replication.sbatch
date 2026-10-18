#!/bin/bash
#SBATCH --job-name=rmu_syc_replication
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --output=logs/rmu_syc_replication_%j.out
#SBATCH --error=logs/rmu_syc_replication_%j.err

set -euo pipefail
PROJECT_ROOT="${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}"
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-rmu-syc-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source "${PROJECT_ROOT:-${SLURM_SUBMIT_DIR:-$PWD}}/thesis/scripts/common.sh"
activate_unlearning_env
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"
nvidia-smi -L

SCRIPT_DIR=mechanistic/experiments/muse_news_sycophancy_paradox/analysis/rmu_clean_audit

echo "=== Step 1: RMU prompt-end hidden state extraction ==="
python "$SCRIPT_DIR/extract_rmu_prompt_end_hidden_states.py"

echo "=== Step 2: descriptive layer-localization analysis ==="
python "$SCRIPT_DIR/analyze_sycophancy_rmu.py"

echo "=== Step 3a: clean activation patching, BASE->RMU (unlearned_recipient) ==="
python "$SCRIPT_DIR/run_activation_patching_rmu.py" --direction unlearned_recipient

echo "=== Step 3b: clean activation patching, RMU->BASE (base_recipient) ==="
python "$SCRIPT_DIR/run_activation_patching_rmu.py" --direction base_recipient

echo "Done."
