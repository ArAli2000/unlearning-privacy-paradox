#!/bin/bash
#SBATCH --job-name=muse_qwen_books_ft
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=160G
#SBATCH --time=24:00:00

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
cd "$REPO_ROOT"

activate_unlearning_env

export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE=/storage/ukp/work/elshashay/.cache/huggingface
export CUDA_HOME=/nfs/cuda/cuda-12.2
export TOKENIZERS_PARALLELISM=false

echo "Node: $(hostname)"
echo "Date: $(date)"
echo "Starting MUSE-Books Qwen2.5-7B-Instruct fine-tuning"

python src/train.py --config-name=train.yaml \
  experiment=finetune/muse/default \
  model=Qwen2.5-7B-Instruct \
  +model.tokenizer_args.padding_side=left \
  model.model_args.attn_implementation=sdpa \
  trainer.args.per_device_train_batch_size=1 \
  trainer.args.gradient_accumulation_steps=16 \
  trainer.args.gradient_checkpointing=True \
  +model.model_args.use_cache=False \
  data_split=Books \
  task_name=muse_books_qwen25_7b_instruct_target
