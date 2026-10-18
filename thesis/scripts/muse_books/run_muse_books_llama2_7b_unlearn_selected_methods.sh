#!/bin/bash
#SBATCH --job-name=muse_books_llama_unlearn
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --nodelist=penelope
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=24:00:00
#SBATCH --array=0-3%1

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
cd "$REPO_ROOT"

activate_unlearning_env

export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE=$HF_HOME
export CUDA_HOME="${CUDA_HOME:-/nfs/cuda/cuda-12.2}"  # cluster default; override for your CUDA toolkit
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

METHODS=("RMU" "WGA" "SimNPO" "SatImp")
METHOD="${METHODS[$SLURM_ARRAY_TASK_ID]}"
METHOD_LC=$(echo "$METHOD" | tr '[:upper:]' '[:lower:]')

TARGET_CKPT="muse-bench/MUSE-Books_target"
TOKENIZER_PATH="NousResearch/Llama-2-7b-hf"

echo "======================================"
echo "MUSE-Books Llama2-7B official target unlearning"
echo "Method: $METHOD"
echo "Target checkpoint: $TARGET_CKPT"
echo "Tokenizer: $TOKENIZER_PATH"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================"

python src/train.py --config-name=unlearn.yaml \
  experiment=unlearn/muse/default \
  model=Llama-2-7b-hf \
  trainer="$METHOD" \
  data_split=Books \
  task_name="muse_books_llama2_7b_${METHOD_LC}" \
  model.model_args.pretrained_model_name_or_path="$TARGET_CKPT" \
  model.tokenizer_args.pretrained_model_name_or_path="$TOKENIZER_PATH" \
  +model.tokenizer_args.padding_side=left \
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
