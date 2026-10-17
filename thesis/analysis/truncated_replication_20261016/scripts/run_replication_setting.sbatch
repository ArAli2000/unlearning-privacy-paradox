#!/bin/bash
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=12:00:00
#SBATCH --output=logs/trunc_repl_%x_%j.out
#SBATCH --error=logs/trunc_repl_%x_%j.err
# One setting-level job: generation of all 5 conditions (original truncated config), completeness gate, then judging with the primary Qwen2.5-7B judge.
# Submit:  sbatch --job-name=trunc_repl_A --export=ALL,SETTING=A_muse_news_qwen25 run_replication_setting.sbatch
# Resumable: a condition whose output already passes verify_complete.py is skipped; partial outputs are resumed natively by `benchmark generate`. FRESH is never used.
set -uo pipefail

: "${SETTING:?set SETTING=A_muse_news_qwen25|B_muse_books_qwen25|C_muse_news_llama2|D_muse_books_llama2}"
REPO=/mnt/beegfs/work/elshashay/open-unlearning
TR="$REPO/thesis/analysis/truncated_replication_20261016"
SC="$TR/scripts"
CODE="$TR/persistbench_code"
BENCH_INPUT="$REPO/external/PersistBench/benchmark_samples/full_benchmark.jsonl"
OUT_ROOT="$REPO/external/PersistBench/outputs/truncated_replication_20261016"
cd "$REPO"
source "$REPO/thesis/scripts/common.sh"
activate_unlearning_env base

# ---- same environment exports as the original generation launcher -----------------------------------------------------------------------
if command -v module >/dev/null 2>&1; then module load cuda/12.2 || module load cuda/12.1 || true; fi
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

# ---- isolated PersistBench code = original generation-time state (no STRICT_GENERATION_CONTROL) ------------------------------------------
export PYTHONPATH="$CODE/src:${PYTHONPATH:-}"
unset OPENAI_BASE_URL OPENAI_API_BASE OPENROUTER_BASE_URL JUDGE_PROVIDER OPENAI_API_KEY OPENROUTER_API_KEY PB_TEMPERATURE PB_TOP_P PB_MAX_TOKENS PB_TRUNCATE_PROMPT_TOKENS PB_REPETITION_PENALTY PB_STRICT_SYSTEM_PROMPT
BM_FILE=$(python -c "import benchmark;print(benchmark.__file__)")
case "$BM_FILE" in "$CODE"/*) ;; *) echo "ERROR: benchmark resolves to $BM_FILE, not the isolated copy"; exit 10;; esac
if grep -q STRICT_GENERATION_CONTROL "$CODE/src/benchmark/utils.py"; then echo "ERROR: strict generation block present"; exit 10; fi

# ---- per-setting parameters (from the canonical manifests used by the original launchers) -----------------------------------------------
JUDGE_CONC_ARGS=()
case "$SETTING" in
  A_muse_news_qwen25)  MODEL_LIST=thesis/manifests/model_lists/muse_news_qwen25_persistbench_models.tsv;  OUTSUB=muse_news_qwen25;;
  B_muse_books_qwen25) MODEL_LIST=thesis/manifests/model_lists/muse_books_qwen25_persistbench_models.tsv; OUTSUB=muse_books_qwen25; JUDGE_CONC_ARGS=(--concurrency 3);;  # original Books-Qwen judge run used --concurrency 3
  C_muse_news_llama2)  MODEL_LIST=research_history/04_muse_track_a/manifests/muse_news_persistbench_models.tsv; OUTSUB=muse_news_llama2;;
  D_muse_books_llama2) MODEL_LIST=thesis/manifests/model_lists/muse_books_llama2_persistbench_models.tsv;  OUTSUB=muse_books_llama2;;
  *) echo "unknown SETTING $SETTING"; exit 2;;
esac
CHAT_TEMPLATE="$REPO/templates/simple_llama_chat_template.jinja"
OUTDIR="$OUT_ROOT/$OUTSUB"; CFGDIR="$OUT_ROOT/_configs/$OUTSUB"; META="$OUT_ROOT/_meta/$OUTSUB"
mkdir -p "$OUTDIR" "$CFGDIR" "$META"
JID="${SLURM_JOB_ID:-local}"

echo "======================================"
echo "TRUNCATED REPLICATION  setting=$SETTING  job=$JID"
echo "Node: $(hostname)  Date: $(date -Is)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | tee "$META/gpu_${JID}.txt"
echo "benchmark module: $BM_FILE"
echo "vllm: $(python -c 'import vllm;print(vllm.__version__)')"
echo "======================================"

# ---- helper: start / stop a vLLM server -----------------------------------------------------------------------------------------------
VLLM_PID=""
stop_vllm() { if [ -n "$VLLM_PID" ]; then kill "$VLLM_PID" 2>/dev/null || true; wait "$VLLM_PID" 2>/dev/null || true; VLLM_PID=""; sleep 10; fi; }
trap stop_vllm EXIT
wait_ready() { # port logfile
  for _ in $(seq 1 360); do
    curl -sf "http://127.0.0.1:$1/v1/models" >/dev/null && return 0
    kill -0 "$VLLM_PID" 2>/dev/null || { echo "vLLM exited early"; tail -n 120 "$2"; return 1; }
    sleep 5
  done
  echo "vLLM not ready"; tail -n 120 "$2"; return 1
}

mapfile -t LINES < "$REPO/$MODEL_LIST"
N=${#LINES[@]}
[ "$N" -eq 5 ] || { echo "ERROR: manifest has $N lines"; exit 11; }
declare -a OUTFILES
STATUS=0

# =========================================== PHASE 1: GENERATION ===========================================
for IDX in $(seq 0 4); do
  LABEL=$(echo "${LINES[$IDX]}" | cut -f1); MODEL_PATH=$(echo "${LINES[$IDX]}" | cut -f2); TOKENIZER_PATH=$(echo "${LINES[$IDX]}" | cut -f3)
  FLABEL=${LABEL/_before/_target}
  OUTF="$OUTDIR/${FLABEL}_truncated_replication.json"; OUTFILES[$IDX]="$OUTF"
  if python "$SC/verify_complete.py" "$OUTF" --quiet; then echo "[$LABEL] already complete -> skipping generation"; continue; fi
  if [ -d "$MODEL_PATH" ]; then MODEL_ABS=$(readlink -f "$MODEL_PATH"); else MODEL_ABS="$MODEL_PATH"; fi
  if [ -d "$TOKENIZER_PATH" ]; then TOK_ABS=$(readlink -f "$TOKENIZER_PATH"); else TOK_ABS="$TOKENIZER_PATH"; fi
  PORT=$((8100 + JID % 1000 + IDX))
  VLOG="$REPO/logs/vllm_trunc_repl_${LABEL}_${JID}_${IDX}.log"
  cat > "$CFGDIR/${FLABEL}_truncated_replication.json" <<JSON
{
  "input": "$BENCH_INPUT",
  "output": "$OUTF",
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
  OK=0
  for ATTEMPT in 1 2 3; do
    echo "[$LABEL] attempt $ATTEMPT: starting vLLM ($(date -Is))  model=$MODEL_ABS"
    vllm serve "$MODEL_ABS" \
      --served-model-name "$LABEL" \
      --tokenizer "$TOK_ABS" \
      --chat-template "$CHAT_TEMPLATE" \
      --host 127.0.0.1 \
      --port "$PORT" \
      --dtype bfloat16 \
      --gpu-memory-utilization 0.90 \
      --max-model-len 2048 \
      > "$VLOG" 2>&1 &
    VLLM_PID=$!
    if wait_ready "$PORT" "$VLOG"; then
      python "$SC/probe_truncation.py" "$PORT" "$LABEL" "$META/truncation_probe_${FLABEL}.json" || echo "WARNING: truncation probe did not return 1800 for [$LABEL]"
      ( cd "$OUT_ROOT" && benchmark generate "$CFGDIR/${FLABEL}_truncated_replication.json" )
    fi
    stop_vllm
    if python "$SC/verify_complete.py" "$OUTF"; then OK=1; break; fi
    echo "[$LABEL] incomplete after attempt $ATTEMPT -> resuming (completed scenarios are kept)"
  done
  [ "$OK" = 1 ] || { echo "ERROR: [$LABEL] generation incomplete after 3 attempts; later conditions continue, judging is withheld"; STATUS=20; }
done

# =========================================== GATE: completeness before judging ===========================================
ALLOK=1
for IDX in $(seq 0 4); do python "$SC/verify_complete.py" "${OUTFILES[$IDX]}" --quiet || ALLOK=0; done
if [ "$ALLOK" != 1 ]; then echo "GATE FAILED: not all 5 conditions complete; judging withheld. Resubmit the same job to resume."; echo "gen_incomplete" > "$META/status_${JID}.txt"; exit 20; fi
echo "GATE PASSED: all 5 conditions complete (1300 generations each)"

# =========================================== PHASE 2: JUDGING (primary Qwen2.5-7B local judge) ===========================================
JPORT=$((8000 + JID % 1000)); JLOG="$REPO/logs/vllm_trunc_repl_judge_${SETTING}_${JID}.log"
need_judge=0; for IDX in $(seq 0 4); do python "$SC/verify_complete.py" "${OUTFILES[$IDX]}" --judged --quiet || need_judge=1; done
if [ "$need_judge" = 1 ]; then
  echo "Starting local judge: Qwen/Qwen2.5-7B-Instruct as local-judge on port $JPORT"
  vllm serve Qwen/Qwen2.5-7B-Instruct \
    --served-model-name local-judge \
    --host 127.0.0.1 \
    --port "$JPORT" \
    --dtype bfloat16 \
    --trust-remote-code \
    --gpu-memory-utilization 0.85 \
    --max-model-len 32768 \
    --enforce-eager \
    > "$JLOG" 2>&1 &
  VLLM_PID=$!
  wait_ready "$JPORT" "$JLOG" || { echo "judge server failed"; echo "judge_server_failed" > "$META/status_${JID}.txt"; exit 30; }
  export JUDGE_PROVIDER=openrouter OPENAI_API_KEY=dummy OPENROUTER_API_KEY=dummy
  export OPENAI_BASE_URL="http://127.0.0.1:$JPORT/v1" OPENROUTER_BASE_URL="http://127.0.0.1:$JPORT/v1" OPENAI_API_BASE="http://127.0.0.1:$JPORT/v1"
  for IDX in $(seq 0 4); do
    F="${OUTFILES[$IDX]}"
    for ATTEMPT in 1 2 3; do
      python "$SC/verify_complete.py" "$F" --judged --quiet && break
      echo "judging $F (attempt $ATTEMPT) $(date -Is)"
      ( cd "$OUT_ROOT" && benchmark judge "$F" --judge-provider openrouter "${JUDGE_CONC_ARGS[@]}" ) || true
    done
    python "$SC/verify_complete.py" "$F" --judged --quiet || { echo "ERROR: $F not fully judged"; STATUS=40; }
  done
  stop_vllm
fi

echo "$SETTING finished status=$STATUS $(date -Is)"
echo "done_status_$STATUS" > "$META/status_${JID}.txt"
exit $STATUS
