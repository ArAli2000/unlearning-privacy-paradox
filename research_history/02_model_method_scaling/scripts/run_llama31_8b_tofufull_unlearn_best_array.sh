#!/bin/bash
#SBATCH --job-name=llama31_8b_unlearn
#SBATCH --output=logs/llama31_8b_unlearn_%A_%a.out
#SBATCH --error=logs/llama31_8b_unlearn_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=220G
#SBATCH --time=24:00:00
#SBATCH --array=0-3%1

set -euo pipefail

cd /mnt/beegfs/work/elshashay/open-unlearning

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

# CUDA_HOME fix for DeepSpeed
if command -v module >/dev/null 2>&1; then
  module load cuda/12.2 || module load cuda/12.1 || true
fi

if [ -z "${CUDA_HOME:-}" ]; then
  if command -v nvcc >/dev/null 2>&1; then
    export CUDA_HOME="$(dirname "$(dirname "$(which nvcc)")")"
  elif [ -d /usr/local/cuda ]; then
    export CUDA_HOME=/usr/local/cuda
  fi
fi

if [ -n "${CUDA_HOME:-}" ]; then
  export PATH="$CUDA_HOME/bin:$PATH"
  export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
fi

echo "CUDA_HOME=${CUDA_HOME:-NOT_SET}"
which nvcc || true
nvcc --version || true


export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TOKENIZERS_PARALLELISM=false
export HOME=/storage/ukp/work/elshashay

mkdir -p logs

METHODS=(
  "SimNPO"
  "RMU"
  "WGA"
  "SatImp"
)

METHOD="${METHODS[$SLURM_ARRAY_TASK_ID]}"
METHOD_LOWER=$(echo "$METHOD" | tr '[:upper:]' '[:lower:]')

MODEL="Llama-3.1-8B-Instruct"
MODEL_SHORT="llama31_8b"

PRETRAIN=$(cat research_history/02_model_method_scaling/manifests/llama31_8b_tofufull_path.txt)

if [ ! -d "$PRETRAIN" ]; then
  echo "ERROR: PRETRAIN path does not exist:"
  echo "$PRETRAIN"
  exit 1
fi

TASK_NAME="proper_${MODEL_SHORT}_${METHOD_LOWER}_from_tofufull_selectionproxy_savebest"
OUT_DIR="saves/unlearn/${TASK_NAME}"

echo "======================================"
echo "Model: $MODEL"
echo "Method: $METHOD"
echo "Pretrain: $PRETRAIN"
echo "Task name: $TASK_NAME"
echo "Output dir: $OUT_DIR"
echo "======================================"

python src/train.py \
  experiment=unlearn/tofu/default \
  mode=unlearn \
  model="$MODEL" \
  trainer="$METHOD" \
  data=unlearn \
  task_name="$TASK_NAME" \
  paths.output_dir="$OUT_DIR" \
  ++forget_split=forget10 \
  ++retain_split=retain90 \
  ++eval.tofu.forget_split=forget10 \
  ++eval.tofu.retain_split=retain90 \
  ++model.model_args.pretrained_model_name_or_path="$PRETRAIN" \
  ++model.tokenizer_args.pretrained_model_name_or_path="$PRETRAIN" \
  ++model.model_args.attn_implementation=sdpa \
  ++trainer.args.output_dir="$OUT_DIR" \
  ++trainer.args.save_strategy=epoch \
  ++trainer.args.save_total_limit=1 \
  ++trainer.args.load_best_model_at_end=true \
  ++trainer.args.metric_for_best_model=eval_Selection_proxy \
  ++trainer.args.greater_is_better=true \
  ++trainer.args.bf16=true \
  ++trainer.args.fp16=false \
  ++trainer.args.report_to=none

echo "Finished $TASK_NAME"
