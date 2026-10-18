#!/bin/bash
#SBATCH --job-name=pb_mcq_qwen7b
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=08:00:00
#SBATCH --output=logs/persistbench_mcq_qwen7b_%j.out
#SBATCH --error=logs/persistbench_mcq_qwen7b_%j.err

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$PWD}"
mkdir -p logs
export TRITON_CACHE_DIR=/tmp/triton-${SLURM_JOB_ID}
mkdir -p "$TRITON_CACHE_DIR"
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning
module load cuda/12.2 || true

python mechanistic/privacy_collapse/persistbench_mcq/validate_static.py
python mechanistic/privacy_collapse/persistbench_mcq/extract.py
python mechanistic/privacy_collapse/persistbench_mcq/validate_outputs.py
python mechanistic/privacy_collapse/persistbench_mcq/analyze.py
