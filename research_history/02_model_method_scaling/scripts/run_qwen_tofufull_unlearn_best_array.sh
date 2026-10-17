#!/bin/bash
#SBATCH --job-name=qwen_tofufull_unlearn
#SBATCH --output=logs/qwen_tofufull_unlearn_%A_%a.out
#SBATCH --error=logs/qwen_tofufull_unlearn_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=24:00:00
#SBATCH --array=0-7%1

set -euo pipefail

cd /mnt/beegfs/work/elshashay/open-unlearning

source /storage/ukp/work/elshashay/miniconda3/etc/profile.d/conda.sh
conda activate unlearning

# Load CUDA toolkit for DeepSpeed.
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
echo "CUDA_HOME: $CUDA_HOME"
which nvcc
nvcc --version
echo "HOME: $HOME"
echo "HF_HOME: $HF_HOME"
echo "TRITON_CACHE_DIR: $TRITON_CACHE_DIR"
echo "===================================="

nvidia-smi

MODELS=(
  "Qwen2.5-3B-Instruct"
  "Qwen2.5-3B-Instruct"
  "Qwen2.5-3B-Instruct"
  "Qwen2.5-3B-Instruct"

  "Qwen2.5-7B-Instruct"
  "Qwen2.5-7B-Instruct"
  "Qwen2.5-7B-Instruct"
  "Qwen2.5-7B-Instruct"
)

MODEL_SHORTS=(
  "qwen25_3b"
  "qwen25_3b"
  "qwen25_3b"
  "qwen25_3b"

  "qwen25_7b"
  "qwen25_7b"
  "qwen25_7b"
  "qwen25_7b"
)

BASE_DIRS=(
  "saves/finetune/tofu_Qwen2.5-3B-Instruct_full"
  "saves/finetune/tofu_Qwen2.5-3B-Instruct_full"
  "saves/finetune/tofu_Qwen2.5-3B-Instruct_full"
  "saves/finetune/tofu_Qwen2.5-3B-Instruct_full"

  "saves/finetune/tofu_Qwen2.5-7B-Instruct_full"
  "saves/finetune/tofu_Qwen2.5-7B-Instruct_full"
  "saves/finetune/tofu_Qwen2.5-7B-Instruct_full"
  "saves/finetune/tofu_Qwen2.5-7B-Instruct_full"
)

METHODS=(
  "SimNPO"
  "RMU"
  "WGA"
  "SatImp"

  "SimNPO"
  "RMU"
  "WGA"
  "SatImp"
)

MODEL=${MODELS[$SLURM_ARRAY_TASK_ID]}
MODEL_SHORT=${MODEL_SHORTS[$SLURM_ARRAY_TASK_ID]}
BASE_DIR=${BASE_DIRS[$SLURM_ARRAY_TASK_ID]}
METHOD=${METHODS[$SLURM_ARRAY_TASK_ID]}
METHOD_LOWER=${METHOD,,}

has_weights() {
  local d="$1"
  find "$d" -maxdepth 1 \( -name "*.safetensors" -o -name "model.safetensors.index.json" -o -name "pytorch_model*.bin" \) 2>/dev/null | grep -q .
}

resolve_model_dir() {
  local base="$1"

  if [ -d "$base" ] && has_weights "$base"; then
    echo "$base"
    return 0
  fi

  local latest_ckpt
  latest_ckpt=$(find "$base" -maxdepth 1 -type d -name "checkpoint-*" 2>/dev/null | sort -V | tail -n 1 || true)

  if [ -n "$latest_ckpt" ] && has_weights "$latest_ckpt"; then
    echo "$latest_ckpt"
    return 0
  fi

  echo "ERROR: Could not find model weights in $base or its checkpoint-* folders." >&2
  exit 1
}

PRETRAIN=$(resolve_model_dir "$BASE_DIR")

# Usually tokenizer is available in the base fine-tune folder.
# If not, use the checkpoint folder.
if [ -f "$BASE_DIR/tokenizer.json" ] || [ -f "$BASE_DIR/tokenizer_config.json" ]; then
  TOKENIZER="$BASE_DIR"
else
  TOKENIZER="$PRETRAIN"
fi

TASK_NAME="proper_${MODEL_SHORT}_${METHOD_LOWER}_from_tofufull_selectionproxy_savebest"

echo "Running corrected TOFU-full unlearning"
echo "Model: $MODEL"
echo "Model short: $MODEL_SHORT"
echo "Method: $METHOD"
echo "TOFU-full base dir: $BASE_DIR"
echo "Resolved pretrained model path: $PRETRAIN"
echo "Tokenizer path: $TOKENIZER"
echo "Task name: $TASK_NAME"

python src/train.py \
  --config-name=unlearn.yaml \
  experiment=unlearn/tofu/default \
  model=$MODEL \
  forget_split=forget10 \
  retain_split=retain90 \
  trainer=$METHOD \
  task_name=$TASK_NAME \
  model.model_args.pretrained_model_name_or_path="$PRETRAIN" \
  model.tokenizer_args.pretrained_model_name_or_path="$TOKENIZER" \
  model.model_args.attn_implementation=sdpa \
  trainer.args.per_device_train_batch_size=1 \
  trainer.args.per_device_eval_batch_size=4 \
  trainer.args.gradient_accumulation_steps=32 \
  eval.tofu.batch_size=8 \
  ++trainer.args.eval_strategy=steps \
  ++trainer.args.eval_steps=26 \
  ++trainer.args.save_strategy=steps \
  ++trainer.args.save_steps=26 \
  ++trainer.args.load_best_model_at_end=true \
  ++trainer.args.metric_for_best_model=eval_Selection_proxy \
  ++trainer.args.greater_is_better=true \
  ++trainer.args.save_total_limit=3 \
  ++trainer.args.save_safetensors=true

RUN_DIR="saves/unlearn/${TASK_NAME}"

echo "Training finished."
echo "Run dir: $RUN_DIR"

if [ -f "$RUN_DIR/trainer_state.json" ]; then
  python - <<PY
import json
p = "$RUN_DIR/trainer_state.json"
with open(p) as f:
    s = json.load(f)
print("best_model_checkpoint:", s.get("best_model_checkpoint"))
print("best_metric:", s.get("best_metric"))
print("global_step:", s.get("global_step"))
PY
else
  echo "WARNING: trainer_state.json not found."
fi
