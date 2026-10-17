#!/bin/bash
#SBATCH --job-name=pbench_fullprompt
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=10:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

# FULL-PROMPT ROBUSTNESS RUN (MUSE-News, Qwen2.5-7B-Instruct, PersistBench sycophancy only)
#
# Derived from thesis/scripts/persistbench/run_persistbench_muse_news_qwen25_selected.sh
# (generation) and run_persistbench_muse_news_qwen25_judge_like_tofu.sh +
# run_local_judge_server_penelope.sh (judging).
#
# Intended differences vs. the original run (and ONLY these):
#   1. vllm serve --max-model-len 8192   (original: 2048)
#   2. no truncate_prompt_tokens         (original: 1800, left truncation)
# Additional, deliberate and reported deviations:
#   3. served-model alias is the same neutral string for all 4 conditions
#      ("muse_news_qwen25") instead of muse_news_qwen25_<condition>. PersistBench puts the
#      alias into the persona prompt ("You are {model_name}"); in the original run that text
#      was truncated away, but with the full prompt it would leak the method name
#      (before/rmu/satimp/simnpo) into the input.
#   4. store_raw_api_responses=true (storage only; lets us verify vLLM's prompt_tokens).
#   5. the PersistBench package is the sandbox copy in ./pb_src whose utils.py is
#      utils.py.bak_before_vllm_truncation (identical to the generation-time utils.py minus the
#      forced truncate_prompt_tokens=1800 lines; the STRICT_GENERATION_CONTROL block is absent,
#      exactly as it was at original generation time). The original external/PersistBench/src
#      is not modified.
# Unchanged: temperature 0.0, max_tokens 96, 3 generations (PersistBench default for
# sycophancy), simple_llama_chat_template.jinja, bf16, gpu-mem-util 0.90, concurrency 1,
# same checkpoints/tokenizer, same persona prompt (prompts.py), same scenario order,
# same judge (Qwen/Qwen2.5-7B-Instruct as local-judge, same server flags, same judge code).

set -euo pipefail

export REPO_ROOT=/mnt/beegfs/work/elshashay/open-unlearning   # sbatch copies this script, so no relative lookup
source "$REPO_ROOT/thesis/scripts/common.sh"
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

# Sandbox PersistBench package (see header, item 5). PB_* strict-generation variables are
# intentionally NOT set.
SANDBOX="$REPO/thesis/scripts/persistbench_fullprompt_robustness/pb_src"
export PYTHONPATH="$SANDBOX:${PYTHONPATH:-}"
export PYTHONDONTWRITEBYTECODE=1
python - <<PY
import benchmark.utils as u
p = u.__file__
print("benchmark.utils from:", p)
assert p.startswith("$SANDBOX"), "sandbox PersistBench not active"
s = open(p).read()
assert "truncate_prompt_tokens" not in s and "STRICT_GENERATION" not in s
PY

mkdir -p logs

MODEL_LIST="$REPO/thesis/manifests/model_lists/muse_news_qwen25_persistbench_models.tsv"
OUT_SUBDIR="muse_news_qwen25_fullprompt_robustness"
ALIAS="muse_news_qwen25"
CHAT_TEMPLATE="$REPO_ROOT/templates/simple_llama_chat_template.jinja"

# original tsv label -> output file stem
declare -A STEM=(
  [muse_news_qwen25_before]=muse_news_qwen25_before_fullprompt
  [muse_news_qwen25_rmu]=muse_news_qwen25_rmu_fullprompt
  [muse_news_qwen25_satimp]=muse_news_qwen25_satimp_fullprompt
  [muse_news_qwen25_simnpo]=muse_news_qwen25_simnpo_fullprompt
)
ORDER=(muse_news_qwen25_before muse_news_qwen25_rmu muse_news_qwen25_satimp muse_news_qwen25_simnpo)

echo "======================================"
echo "Full-prompt robustness run  SLURM job: ${SLURM_JOB_ID:-none}"
echo "Node: $(hostname)   Date: $(date)"
nvidia-smi -L || true
echo "======================================"

cd "$REPO/external/PersistBench"
mkdir -p "outputs/${OUT_SUBDIR}" "configs_local/${OUT_SUBDIR}"

is_complete () {  # $1 = json file; $2 = "gen" (all responses present) or "judge" (all judged)
  python - "$1" "$2" <<'PY'
import json, sys, os
p, mode = sys.argv[1], sys.argv[2]
if not os.path.exists(p): sys.exit(1)
d = json.load(open(p)); n = 0
for e in d["entries"].values():
    for r in e["results"].values():
        for g in r["generations"]:
            n += 1
            if not g.get("memory_response"): sys.exit(1)
            if mode == "judge" and (g.get("judge") is None or g["judge"].get("score") is None): sys.exit(1)
sys.exit(0 if n == 600 and len(d["entries"]) == 200 else 1)
PY
}

BASE_ID="${SLURM_JOB_ID:-0}"
IDX=0
for LABEL in "${ORDER[@]}"; do
  IDX=$((IDX + 1))
  STEM_NAME="${STEM[$LABEL]}"
  OUT="outputs/${OUT_SUBDIR}/${STEM_NAME}.json"
  LINE=$(grep -P "^${LABEL}\t" "$MODEL_LIST")
  MODEL_PATH=$(echo "$LINE" | cut -f2)
  TOKENIZER_PATH=$(echo "$LINE" | cut -f3)
  MODEL_PATH_ABS=$(readlink -f "$REPO/$MODEL_PATH")
  TOKENIZER_PATH_ABS=$(readlink -f "$REPO/$TOKENIZER_PATH")

  if is_complete "$OUT" gen; then
    echo "[$LABEL] generation already complete -> skipping"
    continue
  fi

  PORT=$((8300 + BASE_ID % 500 + IDX))
  echo "--------------------------------------"
  echo "[$LABEL] model=$MODEL_PATH_ABS tokenizer=$TOKENIZER_PATH_ABS alias=$ALIAS port=$PORT out=$OUT"

  cat > "configs_local/${OUT_SUBDIR}/${STEM_NAME}_full.json" <<JSON
{
  "input": "benchmark_samples/sycophancy.jsonl",
  "output": "${OUT}",
  "concurrency": 1,
  "store_raw_api_responses": true,
  "models": [
    {
      "name": "${ALIAS}",
      "provider": "openai_compatible",
      "base_url": "http://127.0.0.1:${PORT}/v1",
      "api_key_env": "PERSISTBENCH_DUMMY_KEY",
      "api_params": {
        "temperature": 0.0,
        "max_tokens": 96
      }
    }
  ]
}
JSON
  export PERSISTBENCH_DUMMY_KEY="dummy"

  vllm serve "$MODEL_PATH_ABS" \
    --served-model-name "$ALIAS" \
    --tokenizer "$TOKENIZER_PATH_ABS" \
    --chat-template "$CHAT_TEMPLATE" \
    --host 127.0.0.1 \
    --port "$PORT" \
    --dtype bfloat16 \
    --gpu-memory-utilization 0.90 \
    --max-model-len 8192 \
    > "$REPO/logs/vllm_fullprompt_${LABEL}_${BASE_ID}.log" 2>&1 &
  VLLM_PID=$!

  READY=0
  for i in $(seq 1 360); do
    if curl -s "http://127.0.0.1:${PORT}/v1/models" >/dev/null; then READY=1; break; fi
    if ! kill -0 $VLLM_PID 2>/dev/null; then break; fi
    sleep 5
  done
  if [ "$READY" != "1" ]; then
    echo "ERROR: vLLM did not start for $LABEL"; tail -n 120 "$REPO/logs/vllm_fullprompt_${LABEL}_${BASE_ID}.log"
    kill $VLLM_PID 2>/dev/null || true; exit 1
  fi
  curl -s "http://127.0.0.1:${PORT}/v1/models"; echo

  benchmark generate "configs_local/${OUT_SUBDIR}/${STEM_NAME}_full.json" || echo "WARNING: generate returned non-zero for $LABEL"

  kill $VLLM_PID 2>/dev/null || true
  wait $VLLM_PID 2>/dev/null || true
  sleep 15
  is_complete "$OUT" gen || { echo "ERROR: generation incomplete for $LABEL"; exit 1; }
  echo "[$LABEL] generation complete: $(date)"
done

# ------------------------------------------------------------------ judging (same Qwen local judge)
echo "======================================"
echo "Starting local judge server (identical flags to run_local_judge_server_penelope.sh): $(date)"
vllm serve "Qwen/Qwen2.5-7B-Instruct" \
  --served-model-name "local-judge" \
  --host 127.0.0.1 \
  --port 8001 \
  --dtype bfloat16 \
  --trust-remote-code \
  --gpu-memory-utilization 0.85 \
  --max-model-len 32768 \
  --enforce-eager \
  > "$REPO/logs/vllm_fullprompt_localjudge_${BASE_ID}.log" 2>&1 &
JUDGE_PID=$!
trap 'kill $JUDGE_PID 2>/dev/null || true' EXIT

READY=0
for i in $(seq 1 360); do
  if curl -s "http://127.0.0.1:8001/v1/models" >/dev/null; then READY=1; break; fi
  if ! kill -0 $JUDGE_PID 2>/dev/null; then break; fi
  sleep 5
done
[ "$READY" = "1" ] || { echo "ERROR: judge server did not start"; tail -n 120 "$REPO/logs/vllm_fullprompt_localjudge_${BASE_ID}.log"; exit 1; }

export JUDGE_PROVIDER=openrouter
export OPENAI_API_KEY=dummy
export OPENROUTER_API_KEY=dummy
export OPENAI_BASE_URL=http://127.0.0.1:8001/v1
export OPENROUTER_BASE_URL=http://127.0.0.1:8001/v1

for LABEL in "${ORDER[@]}"; do
  OUT="outputs/${OUT_SUBDIR}/${STEM[$LABEL]}.json"
  if is_complete "$OUT" judge; then echo "[$LABEL] already judged -> skipping"; continue; fi
  echo "[$LABEL] judging $OUT: $(date)"
  benchmark judge "$OUT" || echo "WARNING: judge returned non-zero for $LABEL"
  is_complete "$OUT" judge || { echo "ERROR: judging incomplete for $LABEL"; exit 1; }
done

echo "ALL DONE: $(date)"
ls -lh "outputs/${OUT_SUBDIR}/"
