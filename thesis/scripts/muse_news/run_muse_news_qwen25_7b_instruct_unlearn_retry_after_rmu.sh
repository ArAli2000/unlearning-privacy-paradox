#!/bin/bash
#SBATCH --job-name=muse_qwen_retry
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --nodelist=penelope
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=24:00:00
#SBATCH --array=0-2%1

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
cd "$REPO_ROOT"

activate_unlearning_env

export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}}"
export CUDA_HOME="${CUDA_HOME:-/nfs/cuda/cuda-12.2}"  # cluster default; override for your CUDA toolkit
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

METHODS=("WGA" "SimNPO" "SatImp")
METHOD="${METHODS[$SLURM_ARRAY_TASK_ID]}"
METHOD_LC=$(echo "$METHOD" | tr '[:upper:]' '[:lower:]')

TARGET_CKPT="saves/finetune/muse_news_qwen25_7b_instruct_target"

echo "======================================"
echo "MUSE-News Qwen2.5-7B-Instruct unlearning retry after RMU"
echo "Method: $METHOD"
echo "Target checkpoint: $TARGET_CKPT"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "Memory: 120G"
echo "Array mode: one method at a time"
echo "======================================"

python src/train.py --config-name=unlearn.yaml \
  experiment=unlearn/muse/default \
  model=Qwen2.5-7B-Instruct \
  trainer="$METHOD" \
  data_split=News \
  task_name="muse_news_qwen25_7b_instruct_${METHOD_LC}" \
  model.model_args.pretrained_model_name_or_path="$TARGET_CKPT" \
  model.tokenizer_args.pretrained_model_name_or_path="$TARGET_CKPT" \
  +model.tokenizer_args.padding_side=left \
  model.model_args.attn_implementation=sdpa \
  +model.model_args.use_cache=False \
  trainer.args.per_device_train_batch_size=1 \
  trainer.args.gradient_accumulation_steps=16 \
  trainer.args.gradient_checkpointing=True \
  ++trainer.args.max_steps=500 \
  ++trainer.args.save_strategy=steps \
  ++trainer.args.eval_strategy=steps \
  ++trainer.args.save_steps=51 \
  ++trainer.args.eval_steps=51 \
  ++trainer.args.save_safetensors=True \
  ++trainer.args.save_only_model=True \
  ++trainer.args.save_total_limit=2 \
  ++trainer.args.load_best_model_at_end=True \
  ++trainer.args.metric_for_best_model=best_agg \
  ++trainer.args.greater_is_better=True
