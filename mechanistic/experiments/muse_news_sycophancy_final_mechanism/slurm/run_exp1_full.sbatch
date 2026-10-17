#!/bin/bash
#SBATCH --job-name=exp1_generate_full
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --output=logs/exp1_generate_full_%j.out
#SBATCH --error=logs/exp1_generate_full_%j.err

set -euo pipefail
PROJECT_ROOT=/mnt/beegfs/work/elshashay/open-unlearning
cd "$PROJECT_ROOT"
mkdir -p logs
export XDG_CACHE_HOME=/storage/ukp/work/elshashay/.cache
export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE="$HF_HOME"
export TRITON_CACHE_DIR=/tmp/triton-exp1-full-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning
module load cuda/12.2 || true

echo "HOSTNAME: $(hostname)"
echo "JOB ID: ${SLURM_JOB_ID}"
nvidia-smi

# Smoke test (job 444457, 2026-09-23) validated correctness (BASE-donor
# forward patch qualitatively reproduces BASE's non-sycophantic framing;
# unlearned-donor reverse patch introduces sycophantic language into BASE's
# otherwise-safe response) and timed ~200s/case across all 8 conditions
# (A, B, C x 3 ranges, D x 3 ranges). 20 cases total -> ~70 min expected;
# 3h budget leaves generous margin. Checkpointed after every case, so a
# walltime kill loses at most one in-flight case and can be resumed by
# resubmitting this same script (it skips already-completed cases).
python mechanistic/experiments/muse_news_sycophancy_final_mechanism/run_exp1_generate.py
