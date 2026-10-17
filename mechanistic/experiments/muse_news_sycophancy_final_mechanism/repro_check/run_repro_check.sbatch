#!/bin/bash
#SBATCH --job-name=exp1_repro_check
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --nodelist=minerva
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=100G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#
# Regenerates the unpatched BASE/unlearned responses of the 10
# HIGH_CONFIDENCE_FAILURE cases with offline vLLM, 3 sequential calls per prompt
# (temperature=0.0, other settings from the checkpoint's generation_config.json).
# See run_repro_check.py for why these settings.

set -euo pipefail

REPO_ROOT="$(cd "${SLURM_SUBMIT_DIR:-$PWD}" && git rev-parse --show-toplevel)"
source "$REPO_ROOT/thesis/scripts/common.sh"
cd "$REPO_ROOT"

activate_unlearning_env base

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME="$HOME/.cache"
export HF_HOME="$XDG_CACHE_HOME/huggingface"
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR="$HOME/.triton/autotune"
export VLLM_USE_FLASHINFER_SAMPLER=0
mkdir -p "$XDG_CACHE_HOME" "$HF_HOME" "$TRITON_CACHE_DIR" logs

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"

python mechanistic/experiments/muse_news_sycophancy_final_mechanism/repro_check/run_repro_check.py
