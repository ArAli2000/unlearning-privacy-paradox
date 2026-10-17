#!/bin/bash
#SBATCH --job-name=pb_wmdp_gen
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=180G
#SBATCH --cpus-per-task=8
#SBATCH --time=08:00:00
#SBATCH --array=0-0
#SBATCH --output=logs/pb_wmdp_gen_%A_%a.out
#SBATCH --error=logs/pb_wmdp_gen_%A_%a.err

set -euo pipefail

REPO="/storage/ukp/work/elshashay/open-unlearning"
MANIFEST="$REPO/research_history/05_wmdp_side_investigation/manifests/persistbench_wmdp_cyber_all4_models.tsv"
PBENCH="$REPO/external/PersistBench"

cd "$REPO"
mkdir -p logs

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate base

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME=$HOME/.cache
export HF_HOME=$HOME/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TRITON_CACHE_DIR=$HOME/.triton/autotune
export FLASHINFER_WORKSPACE_DIR=$HOME/.cache/flashinfer
export VLLM_USAGE_STATS_DIR=$HOME/.cache/vllm/usage
export VLLM_USE_FLASHINFER_SAMPLER=0
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}

mkdir -p "$XDG_CACHE_HOME" "$HF_HOME" "$HF_DATASETS_CACHE" "$TRITON_CACHE_DIR" "$FLASHINFER_WORKSPACE_DIR" "$VLLM_USAGE_STATS_DIR"

LABEL=$(awk -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $1}' "$MANIFEST")
MODEL_PATH=$(awk -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $2}' "$MANIFEST")
TOKENIZER_PATH=$(awk -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $3}' "$MANIFEST")

PORT=$((8800 + SLURM_ARRAY_TASK_ID))

# PersistBench uses the OpenAI client even for local vLLM.
# The key can be fake, but it must be set.
export OPENAI_API_KEY=EMPTY
export OPENAI_BASE_URL="http://127.0.0.1:${PORT}/v1"
export OPENAI_API_BASE="http://127.0.0.1:${PORT}/v1"
export OPENROUTER_API_KEY=EMPTY
export OPENROUTER_BASE_URL="http://127.0.0.1:${PORT}/v1"

OUT_SUBDIR="wmdp_cyber_all4_selected_full"

cd "$PBENCH"
mkdir -p "configs_local/${OUT_SUBDIR}" "outputs/${OUT_SUBDIR}"

CONFIG_PATH="configs_local/${OUT_SUBDIR}/${LABEL}_full.json"
OUTPUT_PATH="outputs/${OUT_SUBDIR}/${LABEL}.json"

cat > "$CONFIG_PATH" <<JSON
{
  "input": "benchmark_samples/full_benchmark.jsonl",
  "output": "${OUTPUT_PATH}",
  "models": [
    {
      "name": "${LABEL}",
      "provider": "openai",
      "model": "${LABEL}",
      "base_url": "http://127.0.0.1:${PORT}/v1",
      "api_key": "EMPTY"
    }
  ]
}
JSON

echo "======================================================"
echo "PersistBench WMDP-Cyber generation"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Label: $LABEL"
echo "Model path: $MODEL_PATH"
echo "Tokenizer path: $TOKENIZER_PATH"
echo "Port: $PORT"
echo "Config: $CONFIG_PATH"
echo "Output: $OUTPUT_PATH"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================================"

CHAT_TEMPLATE_ARGS=()
if [[ "$LABEL" == wmdp_cyber_llama2_7b* ]]; then
  CHAT_TEMPLATE_ARGS=(--chat-template "$PBENCH/templates/simple_llama_chat_template.jinja")
fi

vllm serve "$MODEL_PATH" \
  --served-model-name "$LABEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --trust-remote-code \
  --gpu-memory-utilization 0.85 \
  --max-model-len 4096 \
  --tokenizer "$TOKENIZER_PATH" \
  "${CHAT_TEMPLATE_ARGS[@]}" \
  --enforce-eager > "$REPO/logs/vllm_${LABEL}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log" 2>&1 &

VLLM_PID=$!

cleanup() {
  echo "Stopping vLLM PID $VLLM_PID"
  kill "$VLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for vLLM..."
for i in {1..180}; do
  if curl -sf "http://127.0.0.1:${PORT}/v1/models" >/dev/null; then
    echo "vLLM is ready."
    break
  fi
  sleep 10
done

curl -sf "http://127.0.0.1:${PORT}/v1/models" || {
  echo "ERROR: vLLM did not start."
  tail -n 120 "$REPO/logs/vllm_${LABEL}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log"
  exit 1
}

echo "Running PersistBench full generation..."
benchmark generate "$CONFIG_PATH" --limit 3

echo "Done generation: $LABEL"
echo "Output: $PBENCH/$OUTPUT_PATH"
