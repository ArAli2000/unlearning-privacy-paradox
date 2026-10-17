#!/bin/bash
#SBATCH --job-name=pbench_judge
#SBATCH --output=logs/pbench_judge_%A_%a.out
#SBATCH --error=logs/pbench_judge_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=10:00:00
#SBATCH --array=0-9%1

set -euo pipefail

cd /mnt/beegfs/work/elshashay/open-unlearning

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate base

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "ERROR: OPENROUTER_API_KEY is not set."
  exit 1
fi

FILE_LIST="research_history/05_wmdp_side_investigation/manifests/persistbench_judge_files.txt"
FILE=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$FILE_LIST")

if [ -z "$FILE" ]; then
  echo "ERROR: No file found for task $SLURM_ARRAY_TASK_ID"
  exit 1
fi

cd /mnt/beegfs/work/elshashay/open-unlearning/external/PersistBench

echo "======================================"
echo "PersistBench judge"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "File: $FILE"
echo "OPENROUTER_API_KEY is set"
echo "======================================"

benchmark judge "$FILE"

echo "Done judging:"
echo "$FILE"
ls -lh "$FILE"
