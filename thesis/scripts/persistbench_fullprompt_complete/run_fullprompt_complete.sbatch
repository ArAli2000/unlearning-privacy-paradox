#!/bin/bash
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:h200nvl:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=logs/fpc_%x_%j.out
#SBATCH --error=logs/fpc_%x_%j.err

# Full-prompt PersistBench generation + local Qwen2.5-7B judging for only the cells in $CELLS.
# Same settings as persistbench_fullprompt_robustness/run_fullprompt_robustness*.sh (8192 context, no prompt truncation, one neutral alias for all conditions).
# top_p/top_k/repetition_penalty are left to the checkpoint generation_config.json.
# Submit:  DS=news ALIAS=muse_news_qwen25 CELLS="label:cat1+cat2 label2:cat1 ..." sbatch --job-name=fpc_X run_fullprompt_complete.sbatch
# Resumable: complete cells are skipped, partial outputs are resumed by `benchmark generate`. Jobs must own disjoint cells.
set -uo pipefail
: "${DS:?news|books}" ; : "${ALIAS:?neutral alias}" ; : "${CELLS:?cell list}"
REPO=/mnt/beegfs/work/elshashay/open-unlearning
TR="$REPO/thesis/scripts/persistbench_fullprompt_complete"
SANDBOX="$REPO/thesis/scripts/persistbench_fullprompt_robustness/pb_src"
OUT_ROOT="$REPO/external/PersistBench/outputs/muse_qwen_fullprompt_complete_20261016"
OUTDIR="$OUT_ROOT/muse_$DS"; CFGDIR="$OUT_ROOT/_configs/muse_$DS"; META="$OUT_ROOT/_meta/muse_$DS"
PBDIR="$REPO/external/PersistBench"
case "$DS" in
  news)  MODEL_LIST="$REPO/thesis/manifests/model_lists/muse_news_qwen25_persistbench_models.tsv";;
  books) MODEL_LIST="$REPO/thesis/manifests/model_lists/muse_books_qwen25_persistbench_models.tsv";;
  *) echo "bad DS"; exit 2;;
esac
export REPO_ROOT=$REPO
cd "$REPO"
source "$REPO/thesis/scripts/common.sh"
activate_unlearning_env base
if command -v module >/dev/null 2>&1; then module load cuda/12.2 || module load cuda/12.1 || true; fi
export CUDA_HOME=/nfs/cuda/cuda-12.2 CUDA_PATH=/nfs/cuda/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
export HOME=/storage/ukp/work/elshashay
export HF_HOME=$HOME/.cache/huggingface TRANSFORMERS_CACHE=$HOME/.cache/huggingface HF_DATASETS_CACHE=$HOME/.cache/huggingface/datasets
export TOKENIZERS_PARALLELISM=false PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export NVCC_PREPEND_FLAGS="-allow-unsupported-compiler ${NVCC_PREPEND_FLAGS:-}"
export VLLM_USE_FLASHINFER_SAMPLER=0
export PYTHONPATH="$SANDBOX:${PYTHONPATH:-}" PYTHONDONTWRITEBYTECODE=1
unset OPENAI_BASE_URL OPENAI_API_BASE OPENROUTER_BASE_URL JUDGE_PROVIDER OPENAI_API_KEY OPENROUTER_API_KEY PB_TEMPERATURE PB_TOP_P PB_MAX_TOKENS PB_TRUNCATE_PROMPT_TOKENS PB_REPETITION_PENALTY PB_STRICT_SYSTEM_PROMPT
python - <<PY || exit 10
import benchmark.utils as u
p = u.__file__; print("benchmark.utils from:", p)
assert p.startswith("$SANDBOX"), "sandbox PersistBench not active"
s = open(p).read(); assert "truncate_prompt_tokens" not in s and "STRICT_GENERATION" not in s
PY
mkdir -p logs "$OUTDIR" "$CFGDIR" "$META"
JID="${SLURM_JOB_ID:-local}"; J3=$((${SLURM_JOB_ID:-0} % 1000))
JPORT=$((30000 + J3))
CHAT_TEMPLATE="$REPO/templates/simple_llama_chat_template.jinja"
declare -A INPUT=( [cross_domain]=cross_domain.jsonl [sycophancy]=sycophancy.jsonl [beneficial_memory_usage]=beneficial_samples.jsonl )

{
echo "job=$JID name=${SLURM_JOB_NAME:-} node=$(hostname) date=$(date -Is)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo "vllm=$(python -c 'import vllm;print(vllm.__version__)') torch=$(python -c 'import torch;print(torch.__version__)') transformers=$(python -c 'import transformers;print(transformers.__version__)')"
echo "CUDA_HOME=$CUDA_HOME  nvcc=$(nvcc --version 2>/dev/null | tail -1)"
echo "DS=$DS ALIAS=$ALIAS CELLS=$CELLS"
} | tee "$META/env_${JID}.txt"

VLLM_PID=""
stop_vllm() { if [ -n "$VLLM_PID" ]; then kill "$VLLM_PID" 2>/dev/null || true; wait "$VLLM_PID" 2>/dev/null || true; VLLM_PID=""; sleep 10; fi; }
trap stop_vllm EXIT
wait_ready() { for _ in $(seq 1 360); do curl -sf "http://127.0.0.1:$1/v1/models" >/dev/null && return 0; kill -0 "$VLLM_PID" 2>/dev/null || { echo "vLLM exited early"; tail -n 120 "$2"; return 1; }; sleep 5; done; echo "vLLM not ready"; tail -n 120 "$2"; return 1; }
cell_file() { echo "$OUTDIR/${1}_fullprompt_${2}.json"; }   # label cat
cellok() { python "$TR/verify_cell.py" "$(cell_file "$1" "$2")" "$2" "$ALIAS" "${@:3}" --quiet; }

STATUS=0; IDX=0; DONE_CELLS=()
# Phase 1: generation (one vLLM server per condition)
for SPEC in $CELLS; do
  LABEL=${SPEC%%:*}; CATLIST=${SPEC#*:}; IFS='+' read -ra CATS <<< "$CATLIST"; IDX=$((IDX + 1))
  LINE=$(grep -P "^${LABEL}\t" "$MODEL_LIST") || { echo "ERROR: $LABEL not in manifest"; STATUS=11; continue; }
  MODEL_PATH=$(echo "$LINE" | cut -f2); TOKENIZER_PATH=$(echo "$LINE" | cut -f3)
  MODEL_ABS=$(readlink -f "$REPO/$MODEL_PATH"); TOK_ABS=$(readlink -f "$REPO/$TOKENIZER_PATH")
  [ -f "$MODEL_ABS/config.json" ] || { echo "ERROR: checkpoint missing $MODEL_ABS"; STATUS=12; continue; }
  PENDING=(); for C in "${CATS[@]}"; do if cellok "$LABEL" "$C"; then echo "[$LABEL/$C] already complete -> skipping"; else PENDING+=("$C"); fi; done
  [ ${#PENDING[@]} -eq 0 ] && continue
  PORT=$((20000 + J3 * 10 + IDX)); VLOG="$REPO/logs/vllm_fpc_${LABEL}_${JID}.log"
  export PERSISTBENCH_DUMMY_KEY="dummy"
  for C in "${PENDING[@]}"; do
    cat > "$CFGDIR/${LABEL}_fullprompt_${C}.json" <<JSON
{
  "input": "benchmark_samples/${INPUT[$C]}",
  "output": "$(cell_file "$LABEL" "$C")",
  "concurrency": 1,
  "store_raw_api_responses": true,
  "models": [
    {
      "name": "${ALIAS}",
      "provider": "openai_compatible",
      "base_url": "http://127.0.0.1:${PORT}/v1",
      "api_key_env": "PERSISTBENCH_DUMMY_KEY",
      "api_params": {"temperature": 0.0, "max_tokens": 96}
    }
  ]
}
JSON
  done
  for ATTEMPT in 1 2 3; do
    echo "[$LABEL] attempt $ATTEMPT: vLLM start ($(date -Is)) model=$MODEL_ABS alias=$ALIAS cells=${PENDING[*]}"
    vllm serve "$MODEL_ABS" --served-model-name "$ALIAS" --tokenizer "$TOK_ABS" --chat-template "$CHAT_TEMPLATE" --host 127.0.0.1 --port "$PORT" \
      --dtype bfloat16 --gpu-memory-utilization 0.90 --max-model-len 8192 > "$VLOG" 2>&1 &
    VLLM_PID=$!
    if wait_ready "$PORT" "$VLOG"; then
      for C in "${PENDING[@]}"; do
        cellok "$LABEL" "$C" && continue
        ( cd "$PBDIR" && benchmark generate "$CFGDIR/${LABEL}_fullprompt_${C}.json" ) || echo "WARNING: generate returned non-zero for $LABEL/$C"
      done
    fi
    stop_vllm
    ALLC=1; for C in "${PENDING[@]}"; do cellok "$LABEL" "$C" || ALLC=0; done
    [ "$ALLC" = 1 ] && break
    echo "[$LABEL] incomplete after attempt $ATTEMPT -> resuming (completed scenarios are kept)"
  done
  for C in "${PENDING[@]}"; do
    if cellok "$LABEL" "$C"; then python "$TR/verify_cell.py" "$(cell_file "$LABEL" "$C")" "$C" "$ALIAS" | sed "s|^|[$LABEL/$C] |"; DONE_CELLS+=("$LABEL:$C"); else echo "ERROR: [$LABEL/$C] generation incomplete after 3 attempts"; STATUS=20; fi
  done
done

# Phase 2: judging (cells from this job not yet judged)
NEEDJ=(); for SPEC in $CELLS; do L=${SPEC%%:*}; IFS='+' read -ra CS <<< "${SPEC#*:}"; for C in "${CS[@]}"; do cellok "$L" "$C" && ! cellok "$L" "$C" --judged && NEEDJ+=("$L:$C"); done; done
if [ ${#NEEDJ[@]} -gt 0 ]; then
  JLOG="$REPO/logs/vllm_fpc_judge_${DS}_${JID}.log"
  echo "Starting local judge Qwen/Qwen2.5-7B-Instruct as local-judge on port $JPORT for ${#NEEDJ[@]} cells ($(date -Is))"
  vllm serve Qwen/Qwen2.5-7B-Instruct --served-model-name local-judge --host 127.0.0.1 --port "$JPORT" --dtype bfloat16 --trust-remote-code \
    --gpu-memory-utilization 0.85 --max-model-len 32768 --enforce-eager > "$JLOG" 2>&1 &
  VLLM_PID=$!
  wait_ready "$JPORT" "$JLOG" || { echo "judge server failed"; echo "judge_server_failed" > "$META/status_${JID}.txt"; exit 30; }
  export JUDGE_PROVIDER=openrouter OPENAI_API_KEY=dummy OPENROUTER_API_KEY=dummy
  export OPENAI_BASE_URL="http://127.0.0.1:$JPORT/v1" OPENROUTER_BASE_URL="http://127.0.0.1:$JPORT/v1" OPENAI_API_BASE="http://127.0.0.1:$JPORT/v1"
  for LC in "${NEEDJ[@]}"; do
    L=${LC%%:*}; C=${LC#*:}; F=$(cell_file "$L" "$C")
    for ATTEMPT in 1 2 3; do
      cellok "$L" "$C" --judged && break
      echo "judging $F (attempt $ATTEMPT) $(date -Is)"
      ( cd "$PBDIR" && benchmark judge "$F" ) || true
    done
    cellok "$L" "$C" --judged || { echo "ERROR: $F not fully judged"; STATUS=40; }
  done
  stop_vllm
fi
echo "$DS job $JID finished status=$STATUS $(date -Is)"
echo "done_status_$STATUS" > "$META/status_${JID}.txt"
exit $STATUS
