#!/bin/bash
#SBATCH --job-name=plens_l31_8b
#SBATCH --output=logs/plens_llama31_8b_%A_%a.out
#SBATCH --error=logs/plens_llama31_8b_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=220G
#SBATCH --time=12:00:00
#SBATCH --array=0-4%1

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

MODEL_LIST="research_history/02_model_method_scaling/manifests/llama31_8b_privacylens_models.tsv"

LINE=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$MODEL_LIST")

LABEL=$(echo "$LINE" | cut -f1)
MODEL_PATH=$(echo "$LINE" | cut -f2-)
TOKENIZER_PATH="$MODEL_PATH"

if [ -z "$LABEL" ] || [ -z "$MODEL_PATH" ]; then
  echo "ERROR: Could not read model entry for task $SLURM_ARRAY_TASK_ID"
  exit 1
fi

if [ ! -d "$MODEL_PATH" ]; then
  echo "ERROR: model path does not exist:"
  echo "$MODEL_PATH"
  exit 1
fi

if [ ! -d "$TOKENIZER_PATH" ]; then
  echo "ERROR: tokenizer path does not exist:"
  echo "$TOKENIZER_PATH"
  exit 1
fi

if ! find "$MODEL_PATH" -maxdepth 1 \( -type f -o -type l \) \( -name "*.safetensors" -o -name "pytorch_model*.bin" -o -name "model.safetensors.index.json" \) | grep -q .; then
  echo "ERROR: model path has no model weights."
  exit 1
fi

INPUT_PATH="external/privacy-collapse/benchmarks/privacylens/data/main_data.json"
OUT_ROOT="outputs/privacylens_llama31_8b_tofufull_methods"
OUT_DIR="${OUT_ROOT}/${LABEL}"

mkdir -p "$OUT_DIR"

echo "======================================"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Label: $LABEL"
echo "Model path: $MODEL_PATH"
echo "Tokenizer path: $TOKENIZER_PATH"
echo "Input path: $INPUT_PATH"
echo "Output dir: $OUT_DIR"
echo "======================================"

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
