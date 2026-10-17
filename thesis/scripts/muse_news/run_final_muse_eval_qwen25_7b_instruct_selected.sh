#!/bin/bash
#SBATCH --job-name=final_muse_qwen_eval
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --nodelist=penelope
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=80G
#SBATCH --time=08:00:00
#SBATCH --array=0-4%1

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
REPO="$REPO_ROOT"
cd "$REPO"

activate_unlearning_env

export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE=/storage/ukp/work/elshashay/.cache/huggingface
export CUDA_HOME=/nfs/cuda/cuda-12.2
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

MANIFEST="saves/final_muse_news_qwen25_7b_instruct_selection/SELECTED_MODEL_PATHS.tsv"
TOKENIZER_PATH="saves/finetune/muse_news_qwen25_7b_instruct_target"

# skip header, select line by array id
LINE=$(tail -n +2 "$MANIFEST" | sed -n "$((SLURM_ARRAY_TASK_ID + 1))p")

METHOD=$(echo "$LINE" | cut -f1)
MODEL_PATH=$(echo "$LINE" | cut -f2)

METHOD_LC=$(echo "$METHOD" | tr '[:upper:]' '[:lower:]')
TASK_NAME="final_muse_news_qwen25_7b_instruct_${METHOD_LC}"

echo "======================================"
echo "Final MUSE eval: Qwen2.5-7B-Instruct"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Method: $METHOD"
echo "Model path: $MODEL_PATH"
echo "Tokenizer path: $TOKENIZER_PATH"
echo "Task name: $TASK_NAME"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================"

python src/eval.py --config-name=eval.yaml \
  experiment=eval/muse/default \
  data_split=News \
  task_name="$TASK_NAME" \
  model=Qwen2.5-7B-Instruct \
  model.model_args.pretrained_model_name_or_path="$MODEL_PATH" \
  model.tokenizer_args.pretrained_model_name_or_path="$TOKENIZER_PATH" \
  +model.tokenizer_args.padding_side=left \
  model.model_args.attn_implementation=sdpa \
  +model.model_args.use_cache=False
