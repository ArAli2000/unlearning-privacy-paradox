#!/bin/bash
#SBATCH --job-name=qwen_tofu_full_ft
#SBATCH --output=logs/qwen_tofu_full_ft_%A_%a.out
#SBATCH --error=logs/qwen_tofu_full_ft_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=24:00:00
#SBATCH --array=0-1%1

set -euo pipefail

cd /mnt/beegfs/work/elshashay/open-unlearning

source /storage/ukp/work/elshashay/miniconda3/etc/profile.d/conda.sh
conda activate unlearning

# Load CUDA toolkit for DeepSpeed.
# DeepSpeed needs CUDA_HOME/nvcc even if nvidia-smi works.
if [ -f /etc/profile.d/modules.sh ]; then
  source /etc/profile.d/modules.sh
fi

module load cuda/12.2 || module load cuda/12.1 || module load cuda/13.1 || true

if command -v nvcc >/dev/null 2>&1; then
  export CUDA_HOME=$(dirname "$(dirname "$(which nvcc)")")
  export PATH="$CUDA_HOME/bin:$PATH"
  export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
else
  echo "ERROR: nvcc not found. CUDA module did not load correctly."
  echo "Try: module avail cuda"
  exit 1
fi

echo "CUDA_HOME: $CUDA_HOME"
which nvcc
nvcc --version


export HOME=/storage/ukp/work/elshashay
export HF_HOME=$HOME/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_HUB_CACHE=$HF_HOME/hub
export TRITON_CACHE_DIR=$HOME/.triton/cache

mkdir -p logs
mkdir -p "$TRITON_CACHE_DIR"

echo "===================================="
echo "JOB ID: ${SLURM_JOB_ID}"
echo "ARRAY ID: ${SLURM_ARRAY_TASK_ID}"
echo "NODE: $(hostname)"
echo "WORKDIR: $(pwd)"
echo "HOME: $HOME"
echo "HF_HOME: $HF_HOME"
echo "TRITON_CACHE_DIR: $TRITON_CACHE_DIR"
echo "===================================="

nvidia-smi

MODELS=(
  "Qwen2.5-3B-Instruct"
  "Qwen2.5-7B-Instruct"
)

MODEL_SHORTS=(
  "qwen25_3b"
  "qwen25_7b"
)

MODEL=${MODELS[$SLURM_ARRAY_TASK_ID]}
MODEL_SHORT=${MODEL_SHORTS[$SLURM_ARRAY_TASK_ID]}

find_model_snapshot() {
  local pattern="$1"
  local fallback="$2"

  local found
  found=$(find /storage/ukp/work/elshashay/.cache/huggingface /storage/ukp/shared/shared_model_weights \
    -path "$pattern" 2>/dev/null | head -n 1 || true)

  if [ -n "$found" ]; then
    dirname "$found"
  else
    echo "$fallback"
  fi
}

if [ "$MODEL" = "Qwen2.5-3B-Instruct" ]; then
  PRETRAIN=$(find_model_snapshot "*Qwen2.5-3B-Instruct*config.json" "Qwen/Qwen2.5-3B-Instruct")
elif [ "$MODEL" = "Qwen2.5-7B-Instruct" ]; then
  PRETRAIN=$(find_model_snapshot "*Qwen2.5-7B-Instruct*config.json" "Qwen/Qwen2.5-7B-Instruct")
else
  echo "Unknown model: $MODEL"
  exit 1
fi

TASK_NAME="tofu_${MODEL}_full"

echo "Running TOFU full fine-tuning"
echo "Model: $MODEL"
echo "Pretrained path: $PRETRAIN"
echo "Task name: $TASK_NAME"

python src/train.py \
  --config-name=train.yaml \
  experiment=finetune/tofu/default \
  model=$MODEL \
  task_name=$TASK_NAME \
  model.model_args.pretrained_model_name_or_path="$PRETRAIN" \
  model.tokenizer_args.pretrained_model_name_or_path="$PRETRAIN" \
  model.model_args.attn_implementation=sdpa \
  trainer.args.per_device_train_batch_size=1 \
  trainer.args.per_device_eval_batch_size=4 \
  trainer.args.gradient_accumulation_steps=32 \
  ++trainer.args.save_safetensors=true

echo "Fine-tuning finished."
echo "Expected output:"
echo "saves/finetune/${TASK_NAME}"
