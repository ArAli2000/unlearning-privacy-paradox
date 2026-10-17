#!/bin/bash
#SBATCH --job-name=pbench_judge_muse
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --nodelist=penelope
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=40G
#SBATCH --time=12:00:00
#SBATCH --array=0-4%1

set -euo pipefail

REPO="/storage/ukp/work/elshashay/open-unlearning"
cd "$REPO"

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate base

export JUDGE_PROVIDER=openrouter
export OPENAI_API_KEY=dummy
export OPENROUTER_API_KEY=dummy
export OPENAI_BASE_URL=http://127.0.0.1:8001/v1
export OPENROUTER_BASE_URL=http://127.0.0.1:8001/v1

FILES=(
  "outputs/muse_news_selected_full/muse_news_before.json"
  "outputs/muse_news_selected_full/muse_news_rmu_selected.json"
  "outputs/muse_news_selected_full/muse_news_wga_selected.json"
  "outputs/muse_news_selected_full/muse_news_simnpo_selected.json"
  "outputs/muse_news_selected_full/muse_news_satimp_selected.json"
)

FILE="${FILES[$SLURM_ARRAY_TASK_ID]}"

echo "======================================"
echo "PersistBench judge only, TOFU-style"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "File: $FILE"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================"

cd "$REPO/external/PersistBench"

echo "Checking local judge server..."
curl -s http://127.0.0.1:8001/v1/models || {
  echo "ERROR: local judge server is not reachable on this node."
  exit 1
}

echo
echo "Running benchmark judge..."
benchmark judge "$FILE"

echo "Done judging: $FILE"
