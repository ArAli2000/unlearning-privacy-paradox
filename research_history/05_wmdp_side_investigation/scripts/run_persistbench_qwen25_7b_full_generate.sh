#!/bin/bash
#SBATCH --job-name=pbench_q7_full
#SBATCH --output=logs/pbench_q7_full_%A_%a.out
#SBATCH --error=logs/pbench_q7_full_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=08:00:00
#SBATCH --array=0-4%1

set -euo pipefail

cd /mnt/beegfs/work/elshashay/open-unlearning

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate base

if command -v module >/dev/null 2>&1; then
  module load cuda/12.2 || module load cuda/12.1 || true
fi

export CUDA_HOME=/nfs/cuda/cuda-12.2
export CUDA_PATH=$CUDA_HOME
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}

export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TOKENIZERS_PARALLELISM=false
export HOME=/storage/ukp/work/elshashay
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# Needed because CUDA 12.2 rejects the cluster GCC version by default
export NVCC_PREPEND_FLAGS="-allow-unsupported-compiler ${NVCC_PREPEND_FLAGS:-}"

# Needed to avoid FlashInfer JIT sampler compilation issues
export VLLM_USE_FLASHINFER_SAMPLER=0

mkdir -p logs

MODEL_LIST="research_history/05_wmdp_side_investigation/manifests/qwen25_7b_persistbench_models.tsv"
LINE=$(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" "$MODEL_LIST")

LABEL=$(echo "$LINE" | cut -f1)
MODEL_PATH=$(echo "$LINE" | cut -f2-)
MODEL_PATH_ABS=$(readlink -f "$MODEL_PATH")

if [ -z "$LABEL" ] || [ -z "$MODEL_PATH_ABS" ]; then
  echo "ERROR: Could not read model entry for task $SLURM_ARRAY_TASK_ID"
  exit 1
fi

if [ ! -d "$MODEL_PATH_ABS" ]; then
  echo "ERROR: model path does not exist:"
  echo "$MODEL_PATH_ABS"
  exit 1
fi

PORT=$((8100 + SLURM_JOB_ID % 1000 + SLURM_ARRAY_TASK_ID))

echo "======================================"
echo "PersistBench full generation"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Label: $LABEL"
echo "Model path: $MODEL_PATH_ABS"
echo "Port: $PORT"
echo "CUDA_HOME=$CUDA_HOME"
echo "VLLM_USE_FLASHINFER_SAMPLER=$VLLM_USE_FLASHINFER_SAMPLER"
echo "NVCC_PREPEND_FLAGS=$NVCC_PREPEND_FLAGS"
echo "======================================"

cd /mnt/beegfs/work/elshashay/open-unlearning/external/PersistBench

mkdir -p outputs/qwen25_7b_full configs_local

cat > configs_local/${LABEL}_full.json <<JSON
{
  "input": "benchmark_samples/full_benchmark.jsonl",
  "output": "outputs/qwen25_7b_full/${LABEL}.json",
  "concurrency": 1,
  "models": [
    {
      "name": "$LABEL",
      "provider": "openai_compatible",
      "base_url": "http://127.0.0.1:$PORT/v1",
      "api_key_env": "PERSISTBENCH_DUMMY_KEY",
      "api_params": {
        "temperature": 1.0,
        "max_tokens": 512
      }
    }
  ]
}
JSON

export PERSISTBENCH_DUMMY_KEY="dummy"

echo "Starting vLLM..."
vllm serve "$MODEL_PATH_ABS" \
  --served-model-name "$LABEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  > "/mnt/beegfs/work/elshashay/open-unlearning/logs/vllm_${LABEL}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log" 2>&1 &

VLLM_PID=$!

echo "Waiting for vLLM server..."
for i in $(seq 1 360); do
  if curl -s "http://127.0.0.1:$PORT/v1/models" >/dev/null; then
    echo "vLLM server is ready."
    break
  fi
  sleep 5
done

curl -s "http://127.0.0.1:$PORT/v1/models" || {
  echo "ERROR: vLLM server did not start."
  echo "===== vLLM LOG ====="
  tail -n 240 "/mnt/beegfs/work/elshashay/open-unlearning/logs/vllm_${LABEL}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}.log"
  kill $VLLM_PID || true
  exit 1
}

echo "Running PersistBench full generation..."
benchmark generate configs_local/${LABEL}_full.json

echo "Stopping vLLM..."
kill $VLLM_PID || true

echo "Done."
ls -lh outputs/qwen25_7b_full/${LABEL}.json
