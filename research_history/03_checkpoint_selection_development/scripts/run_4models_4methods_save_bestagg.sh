#!/bin/bash
#SBATCH --job-name=bestagg_4x4
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=192G
#SBATCH --cpus-per-task=16
#SBATCH --time=48:00:00
#SBATCH --array=8-11%1
#SBATCH --output=logs/bestagg_4x4_%A_%a.out
#SBATCH --error=logs/bestagg_4x4_%A_%a.err

set -e

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME=$HOME/.cache
export TRITON_CACHE_DIR=$HOME/.triton/autotune
export HF_HOME=$HOME/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME

mkdir -p logs
mkdir -p $TRITON_CACHE_DIR
mkdir -p $HF_HOME

module load cuda/12.2 || true

export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

cd /mnt/beegfs/work/elshashay/open-unlearning

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

echo "===================================="
echo "HOSTNAME: $(hostname)"
echo "JOB ID: $SLURM_JOB_ID"
echo "ARRAY TASK: $SLURM_ARRAY_TASK_ID"
echo "WORKDIR: $(pwd)"
echo "HOME: $HOME"
echo "HF_HOME: $HF_HOME"
echo "TRITON_CACHE_DIR: $TRITON_CACHE_DIR"
echo "===================================="

nvidia-smi

MODELS=(
  "Llama-3.2-1B-Instruct"
  "Llama-3.2-1B-Instruct"
  "Llama-3.2-1B-Instruct"
  "Llama-3.2-1B-Instruct"

  "Qwen2.5-3B-Instruct"
  "Qwen2.5-3B-Instruct"
  "Qwen2.5-3B-Instruct"
  "Qwen2.5-3B-Instruct"

  "Llama-3.2-3B-Instruct"
  "Llama-3.2-3B-Instruct"
  "Llama-3.2-3B-Instruct"
  "Llama-3.2-3B-Instruct"

  "Qwen2.5-7B-Instruct"
  "Qwen2.5-7B-Instruct"
  "Qwen2.5-7B-Instruct"
  "Qwen2.5-7B-Instruct"
)

MODEL_SHORTS=(
  "llama32_1b"
  "llama32_1b"
  "llama32_1b"
  "llama32_1b"

  "qwen25_3b"
  "qwen25_3b"
  "qwen25_3b"
  "qwen25_3b"

  "llama32_3b"
  "llama32_3b"
  "llama32_3b"
  "llama32_3b"

  "qwen25_7b"
  "qwen25_7b"
  "qwen25_7b"
  "qwen25_7b"
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
METHOD=${METHODS[$SLURM_ARRAY_TASK_ID]}
METHOD_LOWER=${METHOD,,}

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

if [ "$MODEL" = "Llama-3.2-1B-Instruct" ]; then
  PRETRAIN=$(find_model_snapshot "*Llama-3.2-1B-Instruct*config.json" "meta-llama/Llama-3.2-1B-Instruct")
elif [ "$MODEL" = "Llama-3.2-3B-Instruct" ]; then
  PRETRAIN="/storage/ukp/work/elshashay/.cache/huggingface/models--open-unlearning--tofu_Llama-3.2-3B-Instruct_full/snapshots/24f31ca19f6966dcb6f6b29abc511cce71222d4a"
elif [ "$MODEL" = "Qwen2.5-3B-Instruct" ]; then
  PRETRAIN=$(find_model_snapshot "*Qwen2.5-3B-Instruct*config.json" "Qwen/Qwen2.5-3B-Instruct")
elif [ "$MODEL" = "Qwen2.5-7B-Instruct" ]; then
  PRETRAIN=$(find_model_snapshot "*Qwen2.5-7B-Instruct*config.json" "Qwen/Qwen2.5-7B-Instruct")
else
  echo "Unknown model: $MODEL"
  exit 1
fi

TASK_NAME="proper_${MODEL_SHORT}_${METHOD_LOWER}_from_tofufull_savebest"

echo "Running model: $MODEL"
echo "Running method: $METHOD"
echo "Pretrained path: $PRETRAIN"
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
  model.tokenizer_args.pretrained_model_name_or_path="$PRETRAIN" \
  model.model_args.attn_implementation=sdpa \
  trainer.args.per_device_train_batch_size=1 \
  trainer.args.per_device_eval_batch_size=4 \
  trainer.args.gradient_accumulation_steps=32 \
  eval.tofu.batch_size=8 \
  ++trainer.args.eval_strategy=steps \
  ++trainer.args.eval_steps=13 \
  ++trainer.args.save_strategy=steps \
  ++trainer.args.save_steps=13 \
  ++trainer.args.load_best_model_at_end=true \
  ++trainer.args.metric_for_best_model=eval_Agg_proxy \
  ++trainer.args.greater_is_better=true \
  ++trainer.args.save_total_limit=3 \
  ++trainer.args.save_safetensors=true

echo "Training finished."

RUN_DIR="saves/unlearn/${TASK_NAME}"

echo "Reading trainer_state..."
python - <<PY
import json
from pathlib import Path

run = Path("$RUN_DIR")
state = json.load(open(run / "trainer_state.json"))

print("global_step:", state.get("global_step"))
print("best_metric:", state.get("best_metric"))
print("best_model_checkpoint:", state.get("best_model_checkpoint"))

print("\\nAgg_proxy values:")
for item in state.get("log_history", []):
    if "Agg_proxy" in item or "eval_Agg_proxy" in item:
        print(
            "step =", item.get("step"),
            "Agg_proxy =", item.get("Agg_proxy"),
            "eval_Agg_proxy =", item.get("eval_Agg_proxy"),
        )
PY

BEST_CHECKPOINT=$(python - <<PY
import json
import os
from pathlib import Path

run = Path("$RUN_DIR")
state = json.load(open(run / "trainer_state.json"))
best = state.get("best_model_checkpoint")

if best is None:
    raise SystemExit("No best_model_checkpoint found.")

print(os.path.abspath(best))
PY
)

echo "Best checkpoint is:"
echo "$BEST_CHECKPOINT"

echo "Checking best checkpoint files:"
find "$BEST_CHECKPOINT" -maxdepth 1 -type f | head -30

if find "$BEST_CHECKPOINT" -maxdepth 1 -type f \( -name "*.safetensors" -o -name "pytorch_model*.bin" -o -name "model.safetensors.index.json" \) | grep -q .; then
  echo "SUCCESS: best checkpoint contains model weights."

  echo "Deleting non-best checkpoints to save space..."
  for ckpt in "$RUN_DIR"/checkpoint-*; do
    if [ -d "$ckpt" ]; then
      ABS_CKPT=$(readlink -f "$ckpt")
      ABS_BEST=$(readlink -f "$BEST_CHECKPOINT")

      if [ "$ABS_CKPT" != "$ABS_BEST" ]; then
        echo "Deleting $ckpt"
        rm -rf "$ckpt"
      fi
    fi
  done

  echo "Deleting parent duplicated model shards if they exist..."
  rm -f "$RUN_DIR"/model-*.safetensors
  rm -f "$RUN_DIR"/model.safetensors.index.json
  rm -f "$RUN_DIR"/pytorch_model*.bin

else
  echo "WARNING: best checkpoint does not contain model weights. Not deleting anything."
fi

echo "Final run directory size:"
du -h --max-depth=1 "$RUN_DIR" | sort -h | tail

echo "Done."
