#!/bin/bash
#SBATCH --job-name=plens_llama32_3b
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=160G
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --array=0-4%1
#SBATCH --output=logs/plens_llama32_3b_%A_%a.out
#SBATCH --error=logs/plens_llama32_3b_%A_%a.err

set -e

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME=$HOME/.cache
export TRITON_CACHE_DIR=$HOME/.triton/autotune
export HF_HOME=$HOME/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME

mkdir -p logs
mkdir -p "$TRITON_CACHE_DIR"
mkdir -p "$HF_HOME"

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
echo "HF_HOME: $HF_HOME"
echo "===================================="

nvidia-smi

LABELS=(
  "llama32_3b_tofufull_before"
  "llama32_3b_after_simnpo_from_tofufull"
  "llama32_3b_after_rmu_from_tofufull"
  "llama32_3b_after_wga_from_tofufull"
  "llama32_3b_after_satimp_from_tofufull"
)

MODEL_KEYS=(
  "llama32_3b"
  "llama32_3b"
  "llama32_3b"
  "llama32_3b"
  "llama32_3b"
)

KINDS=(
  "before"
  "after"
  "after"
  "after"
  "after"
)

RUN_NAMES=(
  "NONE"
  "proper_llama32_3b_simnpo_from_tofufull_savebest"
  "proper_llama32_3b_rmu_from_tofufull_savebest"
  "proper_llama32_3b_wga_from_tofufull_savebest"
  "proper_llama32_3b_satimp_from_tofufull_savebest"
)

LABEL=${LABELS[$SLURM_ARRAY_TASK_ID]}
MODEL_KEY=${MODEL_KEYS[$SLURM_ARRAY_TASK_ID]}
KIND=${KINDS[$SLURM_ARRAY_TASK_ID]}
RUN_NAME=${RUN_NAMES[$SLURM_ARRAY_TASK_ID]}

QWEN25_3B_BEFORE="/storage/ukp/shared/shared_model_weights/models--Qwen2.5-3B-Instruct"
LLAMA32_3B_BEFORE="/storage/ukp/work/elshashay/.cache/huggingface/models--open-unlearning--tofu_Llama-3.2-3B-Instruct_full/snapshots/24f31ca19f6966dcb6f6b29abc511cce71222d4a"
QWEN25_7B_BEFORE="/storage/ukp/shared/shared_model_weights/models--Qwen2.5-7B-Instruct"

echo "Label: $LABEL"
echo "Model key: $MODEL_KEY"
echo "Kind: $KIND"
echo "Run name: $RUN_NAME"

find_required_snapshot() {
  local pattern="$1"
  local label="$2"

  local found
  found=$(find /storage/ukp/work/elshashay/.cache/huggingface /storage/ukp/shared/shared_model_weights \
    -path "$pattern" 2>/dev/null | head -n 1 || true)

  if [ -z "$found" ]; then
    echo "ERROR: Could not find local snapshot for $label"
    echo "Search pattern: $pattern"
    exit 1
  fi

  dirname "$found"
}

get_base_tokenizer_path() {
  local model_key="$1"

  if [ "$model_key" = "qwen25_3b" ]; then
    find_required_snapshot "*models--Qwen--Qwen2.5-3B-Instruct*/snapshots/*/tokenizer_config.json" "Qwen2.5-3B tokenizer"
  elif [ "$model_key" = "qwen25_7b" ]; then
    find_required_snapshot "*models--Qwen--Qwen2.5-7B-Instruct*/snapshots/*/tokenizer_config.json" "Qwen2.5-7B tokenizer"
  elif [ "$model_key" = "llama32_3b" ]; then
    if [ -f "$LLAMA32_3B_BEFORE/tokenizer_config.json" ]; then
      echo "$LLAMA32_3B_BEFORE"
    else
      find_required_snapshot "*models--meta-llama--Llama-3.2-3B-Instruct*/snapshots/*/tokenizer_config.json" "Llama3.2-3B tokenizer"
    fi
  else
    echo "ERROR: Unknown model key for tokenizer: $model_key"
    exit 1
  fi
}


get_before_model_path() {
  local model_key="$1"

  if [ "$model_key" = "qwen25_3b" ]; then
    echo "$QWEN25_3B_BEFORE"
  elif [ "$model_key" = "qwen25_7b" ]; then
    echo "$QWEN25_7B_BEFORE"
  elif [ "$model_key" = "llama32_3b" ]; then
    echo "$LLAMA32_3B_BEFORE"
  else
    echo "ERROR: Unknown model key for before/base model: $model_key" >&2
    exit 1
  fi
}

get_after_model_path() {
  local run_name="$1"
  local run_dir="saves/unlearn/${run_name}"

  python - <<PY
import json
import os
from pathlib import Path

run = Path("$run_dir")
state_path = run / "trainer_state.json"

if not state_path.exists():
    raise SystemExit(f"Missing trainer_state.json: {state_path}")

state = json.load(open(state_path))
best = state.get("best_model_checkpoint")

if best is None:
    raise SystemExit(f"Missing best_model_checkpoint in {state_path}")

print(os.path.abspath(best))
PY
}

if [ "$KIND" = "before" ]; then
  MODEL_PATH=$(get_before_model_path "$MODEL_KEY")

  if [ -f "${MODEL_PATH}/tokenizer_config.json" ]; then
    TOKENIZER_PATH="$(realpath "$MODEL_PATH")"
  else
    TOKENIZER_PATH=$(get_base_tokenizer_path "$MODEL_KEY")
  fi
else
  MODEL_PATH=$(get_after_model_path "$RUN_NAME")

  RUN_DIR="saves/unlearn/${RUN_NAME}"

  if [ -f "${RUN_DIR}/tokenizer_config.json" ]; then
    TOKENIZER_PATH="$(realpath "$RUN_DIR")"
  else
    TOKENIZER_PATH=$(get_base_tokenizer_path "$MODEL_KEY")
  fi
fi

echo "Model path: $MODEL_PATH"
echo "Tokenizer path: $TOKENIZER_PATH"

if [ ! -d "$MODEL_PATH" ]; then
  echo "ERROR: model path does not exist."
  exit 1
fi

if [ ! -d "$TOKENIZER_PATH" ]; then
  echo "ERROR: tokenizer path does not exist."
  exit 1
fi

if ! find "$MODEL_PATH" -maxdepth 1 \( -type f -o -type l \) \( -name "*.safetensors" -o -name "pytorch_model*.bin" -o -name "model.safetensors.index.json" \) | grep -q .; then
  echo "ERROR: model path has no model weights."
  exit 1
fi

INPUT_PATH="external/privacy-collapse/benchmarks/privacylens/data/main_data.json"
OUT_ROOT="outputs/privacylens_llama32_3b_tofufull_methods"
OUT_DIR="${OUT_ROOT}/${LABEL}"

mkdir -p "$OUT_DIR"

python scripts/eval_privacylens_mcq_local.py \
  --input-path "$INPUT_PATH" \
  --output-path "${OUT_DIR}/privacy_mcq_all493.json" \
  --model-path "$MODEL_PATH" \
  --tokenizer-path "$TOKENIZER_PATH" \
  --model-label "$LABEL" \
  --prompt-type "naive" \
  --start-index 0 \
  --limit -1 \
  --max-new-tokens 20 \
  --temperature 1.0

echo "Finished PrivacyLens full evaluation for $LABEL"
