#!/bin/bash
#SBATCH --job-name=pbench_q7_test
#SBATCH --output=logs/pbench_q7_test_%j.out
#SBATCH --error=logs/pbench_q7_test_%j.err
#SBATCH --partition=gpu
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=04:00:00

set -euo pipefail

cd /mnt/beegfs/work/elshashay/open-unlearning

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate base

# CUDA/nvcc is needed by vLLM / FlashInfer JIT
if command -v module >/dev/null 2>&1; then
  module load cuda/12.2 || module load cuda/12.1 || true
fi

if [ -z "${CUDA_HOME:-}" ]; then
  if [ -d /nfs/cuda/cuda-12.2 ]; then
    export CUDA_HOME=/nfs/cuda/cuda-12.2
  elif [ -d /nfs/cuda/cuda-12.1 ]; then
    export CUDA_HOME=/nfs/cuda/cuda-12.1
  elif command -v nvcc >/dev/null 2>&1; then
    export CUDA_HOME="$(dirname "$(dirname "$(which nvcc)")")"
  elif [ -d /usr/local/cuda ]; then
    export CUDA_HOME=/usr/local/cuda
  fi
fi

if [ -n "${CUDA_HOME:-}" ]; then
  export CUDA_PATH="$CUDA_HOME"
  export PATH="$CUDA_HOME/bin:$PATH"
  export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
fi

echo "CUDA_HOME=${CUDA_HOME:-NOT_SET}"
which nvcc || true
nvcc --version || true

# Fix FlashInfer/vLLM JIT compilation with newer GCC
# CUDA 12.2 officially supports GCC <= 12, but cluster default GCC may be newer.
export NVCC_PREPEND_FLAGS="-allow-unsupported-compiler ${NVCC_PREPEND_FLAGS:-}"

# Avoid FlashInfer JIT sampler compilation problems with CUDA 12.2 + GCC 14
export VLLM_USE_FLASHINFER_SAMPLER=0
echo "VLLM_USE_FLASHINFER_SAMPLER=$VLLM_USE_FLASHINFER_SAMPLER"


echo "GCC info:"
which gcc || true
gcc --version | head -1 || true
which g++ || true
g++ --version | head -1 || true
echo "NVCC_PREPEND_FLAGS=$NVCC_PREPEND_FLAGS"



export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TOKENIZERS_PARALLELISM=false
export HOME=/storage/ukp/work/elshashay
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export PERSISTBENCH_DUMMY_KEY="dummy"

mkdir -p logs

MODEL_LIST="research_history/05_wmdp_side_investigation/manifests/qwen25_7b_persistbench_models.tsv"
LINE=$(sed -n "1p" "$MODEL_LIST")

LABEL=$(echo "$LINE" | cut -f1)
MODEL_PATH=$(echo "$LINE" | cut -f2-)
MODEL_PATH_ABS=$(readlink -f "$MODEL_PATH")

PORT=$((8000 + SLURM_JOB_ID % 1000))

echo "======================================"
echo "PersistBench small test"
echo "Label: $LABEL"
echo "Model path: $MODEL_PATH_ABS"
echo "Port: $PORT"
echo "======================================"

cd /mnt/beegfs/work/elshashay/open-unlearning/external/PersistBench

mkdir -p outputs configs_local

cat > configs_local/${LABEL}_test.json <<JSON
{
  "input": "benchmark_samples/full_benchmark.jsonl",
  "output": "outputs/${LABEL}_test.json",
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

echo "Starting vLLM..."
vllm serve "$MODEL_PATH_ABS" \
  --served-model-name "$LABEL" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  > "/mnt/beegfs/work/elshashay/open-unlearning/logs/vllm_${LABEL}_${SLURM_JOB_ID}.log" 2>&1 &

VLLM_PID=$!

echo "Waiting for vLLM server..."
for i in $(seq 1 180); do
  if curl -s "http://127.0.0.1:$PORT/v1/models" >/dev/null; then
    echo "vLLM server is ready."
    break
  fi
  sleep 5
done

curl -s "http://127.0.0.1:$PORT/v1/models" || {
  echo "ERROR: vLLM server did not start."
  echo "===== vLLM LOG ====="
  tail -n 200 "/mnt/beegfs/work/elshashay/open-unlearning/logs/vllm_${LABEL}_${SLURM_JOB_ID}.log"
  kill $VLLM_PID || true
  exit 1
}

echo "Running PersistBench dry run..."
benchmark generate configs_local/${LABEL}_test.json --dry-run --limit 1

echo "Running PersistBench limit=3..."
benchmark generate configs_local/${LABEL}_test.json --limit 3

echo "Stopping vLLM..."
kill $VLLM_PID || true

echo "Done."
ls -lh outputs/${LABEL}_test.json
