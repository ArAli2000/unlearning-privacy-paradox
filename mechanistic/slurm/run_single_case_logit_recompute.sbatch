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
cd /storage/ukp/work/elshashay/open-unlearning
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning
module load cuda/12.2 || true
export CUDA_HOME=/nfs/cuda/cuda-12.2
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
echo "HOSTNAME: $(hostname)"; echo "JOB ID: ${SLURM_JOB_ID}"
python mechanistic/recompute_single_case_logit_lens.py
