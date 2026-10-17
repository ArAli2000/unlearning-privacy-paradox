#!/bin/bash
#SBATCH --job-name=qwen14_tofu_full
#SBATCH --output=logs/qwen14_tofu_full_%j.out
#SBATCH --error=logs/qwen14_tofu_full_%j.err
#SBATCH --partition=gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=256G
#SBATCH --time=24:00:00

set -euo pipefail

cd /mnt/beegfs/work/elshashay/open-unlearning

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

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

export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TOKENIZERS_PARALLELISM=false
export HOME=/storage/ukp/work/elshashay

mkdir -p logs
mkdir -p saves/finetune
mkdir -p tmp_paths

MODEL="Qwen2.5-14B-Instruct"
OUT_DIR="saves/finetune/tofu_Qwen2.5-14B-Instruct_full"

echo "======================================"
echo "Qwen2.5-14B TOFU-full finetune"
echo "Model: $MODEL"
echo "Output dir: $OUT_DIR"
echo "CUDA_HOME=${CUDA_HOME:-NOT_SET}"
which nvcc || true
nvcc --version || true
echo "======================================"

python src/train.py \
  experiment=finetune/tofu/default \
  model="$MODEL" \
  trainer=finetune \
  data=finetune \
  task_name="tofu_Qwen2.5-14B-Instruct_full" \
  paths.output_dir="$OUT_DIR" \
  ++model.model_args.attn_implementation=sdpa \
  ++trainer.args.output_dir="$OUT_DIR" \
  ++trainer.args.save_strategy=epoch \
  ++trainer.args.save_total_limit=1 \
  ++trainer.args.load_best_model_at_end=false \
  ++trainer.args.bf16=true \
  ++trainer.args.fp16=false \
  ++trainer.args.gradient_checkpointing=true \
  ++trainer.args.per_device_train_batch_size=1 \
  ++trainer.args.per_device_eval_batch_size=2 \
  ++trainer.args.gradient_accumulation_steps=32 \
  ++eval.tofu.batch_size=2 \
  ++trainer.args.report_to=none

echo "$OUT_DIR" > research_history/02_model_method_scaling/manifests/qwen25_14b_tofufull_path.txt

echo "Finished Qwen2.5-14B TOFU-full finetune."
echo "Saved path:"
cat research_history/02_model_method_scaling/manifests/qwen25_14b_tofufull_path.txt
