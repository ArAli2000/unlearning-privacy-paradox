#!/bin/bash
#SBATCH --job-name=pbench_muse_news
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=12:00:00
#SBATCH --array=0-4%1
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
REPO="$REPO_ROOT"
cd "$REPO"

activate_unlearning_env base

if command -v module >/dev/null 2>&1; then
  module load cuda/12.2 || module load cuda/12.1 || true
fi

export CUDA_HOME=/nfs/cuda/cuda-12.2
export CUDA_PATH=$CUDA_HOME
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}

export HOME=/storage/ukp/work/elshashay
export HF_HOME=$HOME/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

export NVCC_PREPEND_FLAGS="-allow-unsupported-compiler ${NVCC_PREPEND_FLAGS:-}"
export VLLM_USE_FLASHINFER_SAMPLER=0

mkdir -p logs

MODEL_LIST="thesis/manifests/model_lists/muse_books_qwen25_persistbench_models.tsv"
OUT_SUBDIR="muse_books_qwen25_selected_full"

LINE=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$MODEL_LIST")

LABEL=$(echo "$LINE" | cut -f1)
MODEL_PATH=$(echo "$LINE" | cut -f2)
TOKENIZER_PATH=$(echo "$LINE" | cut -f3)

if [ -z "$LABEL" ] || [ -z "$MODEL_PATH" ] || [ -z "$TOKENIZER_PATH" ]; then
  echo "ERROR: Could not read model entry for task $SLURM_ARRAY_TASK_ID"
  echo "LINE=$LINE"
  exit 1
fi

# If MODEL_PATH is a local directory, verify weights.
# If it is a Hugging Face id, skip local directory check.
if [ -d "$MODEL_PATH" ]; then
  MODEL_PATH_ABS=$(readlink -f "$MODEL_PATH")

  if ! find "$MODEL_PATH_ABS" -maxdepth 1 \( -type f -o -type l \) \( -name "*.safetensors" -o -name "pytorch_model*.bin" -o -name "model.safetensors.index.json" \) | grep -q .; then
    echo "ERROR: local model path has no model weights:"
    echo "$MODEL_PATH_ABS"
    exit 1
  fi
else
  MODEL_PATH_ABS="$MODEL_PATH"
fi

if [ -d "$TOKENIZER_PATH" ]; then
  TOKENIZER_PATH_ABS=$(readlink -f "$TOKENIZER_PATH")
else
  TOKENIZER_PATH_ABS="$TOKENIZER_PATH"
fi

BASE_ID="${SLURM_ARRAY_JOB_ID:-$SLURM_JOB_ID}"
JOB_TAG="${BASE_ID}_${SLURM_ARRAY_TASK_ID}"
PORT=$((8100 + BASE_ID % 1000 + SLURM_ARRAY_TASK_ID))

echo "======================================"
echo "PersistBench MUSE-News full generation"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Label: $LABEL"
echo "Model path: $MODEL_PATH_ABS"
echo "Tokenizer path: $TOKENIZER_PATH_ABS"
echo "Output subdir: $OUT_SUBDIR"
echo "Port: $PORT"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "CUDA_HOME=$CUDA_HOME"
echo "======================================"

cd "$REPO/external/PersistBench"

mkdir -p "outputs/${OUT_SUBDIR}" "configs_local/${OUT_SUBDIR}"

if [ "${FRESH:-0}" = "1" ]; then
  rm -f "outputs/${OUT_SUBDIR}/${LABEL}.json"
fi

cat > "configs_local/${OUT_SUBDIR}/${LABEL}_full.json" <<JSON
{
  "input": "benchmark_samples/full_benchmark.jsonl",
  "output": "outputs/${OUT_SUBDIR}/${LABEL}.json",
  "concurrency": 1,
  "models": [
    {
      "name": "$LABEL",
      "provider": "openai_compatible",
      "base_url": "http://127.0.0.1:$PORT/v1",
      "api_key_env": "PERSISTBENCH_DUMMY_KEY",
      "api_params": {
        "temperature": 0.0,
        "max_tokens": 96,
        "extra_body": {"truncate_prompt_tokens": 1800}
      }
    }
  ]
}
JSON

export PERSISTBENCH_DUMMY_KEY="dummy"


echo "Starting vLLM..."

CHAT_TEMPLATE="$REPO_ROOT/templates/simple_llama_chat_template.jinja"

vllm serve "$MODEL_PATH_ABS" \
  --served-model-name "$LABEL" \
  --tokenizer "$TOKENIZER_PATH_ABS" \
  --chat-template "$CHAT_TEMPLATE" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 2048 \
  > "$REPO/logs/vllm_${LABEL}_${JOB_TAG}.log" 2>&1 &

VLLM_PID=$!

cleanup() {
  echo "Stopping vLLM if still running..."
  kill $VLLM_PID 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for vLLM server..."
READY=0
for i in $(seq 1 360); do
  if curl -s "http://127.0.0.1:$PORT/v1/models" >/dev/null; then
    READY=1
    echo "vLLM server is ready."
    break
  fi
  sleep 5
done

if [ "$READY" != "1" ]; then
  echo "ERROR: vLLM server did not start."
  echo "===== vLLM LOG ====="
  tail -n 240 "$REPO/logs/vllm_${LABEL}_${JOB_TAG}.log"
  exit 1
fi

curl -s "http://127.0.0.1:$PORT/v1/models"
echo

echo "Running PersistBench full generation..."
benchmark generate "configs_local/${OUT_SUBDIR}/${LABEL}_full.json"

echo "Done."
ls -lh "outputs/${OUT_SUBDIR}/${LABEL}.json"
