#!/bin/bash
#SBATCH --job-name=gemma3_judge_full
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#
# Re-judges all 15 canonical, frozen PersistBench generation files (5 methods
# x 3 model-family tracks) with a locally-served google/gemma-3-12b-it judge.
# Never reads or writes external/PersistBench/outputs/ (the existing,
# Qwen-judged, frozen files) except as read-only input; writes to a
# completely separate tree, external/PersistBench/outputs_gemma3_judge/.
#
# Design: ONE persistent vLLM server for the whole run, looping
# gemma_judge.py over all 15 input/output pairs sequentially, instead of a
# 15-task SLURM array. The Gemma-3 smoke test (job 438808) needed ~550s just
# for model loading -- an array would pay that cost 15 times; this pays it
# once. This also uses only 1 of the 2 A100s that were idle on the original cluster node,
# leaving cluster capacity for other users rather than requesting up to 15
# concurrent GPUs.
#
# Runtime fixes proven by the Gemma-2/Gemma-3 smoke-test debugging, carried over:
#   - $SLURM_SUBMIT_DIR (not ${BASH_SOURCE[0]}) to locate the repo.
#   - a writable HOME override + VLLM_USE_FLASHINFER_SAMPLER=0 to avoid the FlashInfer
#     JIT PermissionError.
#   - (original run only) a fixed compute node, because other nodes had unrelated
#     cluster-level problems at the time; not needed elsewhere.
#
# Portability (changes relative to the launcher used for the reported runs; the judge
# model, vLLM arguments, prompts and scoring are unchanged):
#   - The SLURM account and node directives were removed. Provide your own, e.g.
#       sbatch --account=<ACCOUNT> [--nodelist=<NODE>] thesis/analysis/judge_robustness/run_gemma3_judge_full.sbatch
#     Partition, GPU type, memory and time below are the values of the original run; override
#     them on the command line (--partition, --gres, --mem, --time) if your cluster differs.
#   - Submit from the repository root, with a logs/ directory present (SLURM opens the
#     --output/--error files before the script starts): mkdir -p logs
#   - Cluster-specific locations are now variables (defaults in parentheses):
#       GEMMA_LOCAL_PATH   optional: a local snapshot of google/gemma-3-12b-it at revision
#                          96b6f1eccf38110c56df3a15bffe176da04bfd80. If unset, vLLM downloads
#                          the public model google/gemma-3-12b-it at exactly that revision
#                          (a gated Hugging Face model: accept its licence and set HF_TOKEN).
#       GEMMA_JUDGE_HOME   writable directory used as $HOME for caches   ($HOME)
#       GEMMA_JUDGE_PORT   port of the local vLLM server                 (8002)
#       UNLEARNING_CONDA_ACTIVATE, UNLEARNING_CONDA_ENV: see thesis/scripts/common.sh
#   - Provenance: the reported runs served a local snapshot of this same revision from an institutional
#     shared directory (/storage/ukp/shared/shared_model_weights/models--google--gemma-3-12b-it). That
#     path is not usable elsewhere and is no longer a default; the revision is the identity that counts.
#
# --max-model-len 16384: per gemma3_prompt_length_analysis.json / job 438796,
# the real maximum required context across all 19,500 real judgment requests
# in these 15 files is 9,505 tokens (9,249 max input + 256 output) -- 16384
# gives ample headroom while staying far under the model's native 131072.

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "${SLURM_SUBMIT_DIR:-$PWD}" && git rev-parse --show-toplevel)}"
source "$REPO_ROOT/thesis/scripts/common.sh"
cd "$REPO_ROOT"

activate_unlearning_env base

export HOME="${GEMMA_JUDGE_HOME:-$HOME}"
export XDG_CACHE_HOME="$HOME/.cache"
export HF_HOME="$XDG_CACHE_HOME/huggingface"
export TRANSFORMERS_CACHE="$HF_HOME"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
export TRITON_CACHE_DIR="$HOME/.triton/autotune"
export FLASHINFER_WORKSPACE_DIR="$XDG_CACHE_HOME/flashinfer"
export VLLM_USAGE_STATS_DIR="$HOME/.cache/vllm/usage"
export VLLM_USE_FLASHINFER_SAMPLER=0
mkdir -p "$XDG_CACHE_HOME" "$HF_HOME" "$HF_DATASETS_CACHE" "$TRITON_CACHE_DIR" "$FLASHINFER_WORKSPACE_DIR" "$VLLM_USAGE_STATS_DIR"

GEMMA_MODEL_ID="google/gemma-3-12b-it"
GEMMA_REVISION="96b6f1eccf38110c56df3a15bffe176da04bfd80"
if [ -n "${GEMMA_LOCAL_PATH:-}" ]; then
  if [ ! -f "${GEMMA_LOCAL_PATH}/config.json" ]; then
    echo "ERROR: GEMMA_LOCAL_PATH has no config.json: ${GEMMA_LOCAL_PATH}" >&2
    echo "       Point it at a snapshot of ${GEMMA_MODEL_ID} (revision ${GEMMA_REVISION}) or unset it to download the public model." >&2
    exit 1
  fi
  GEMMA_SERVE_ARGS=("${GEMMA_LOCAL_PATH}")
else
  GEMMA_SERVE_ARGS=("${GEMMA_MODEL_ID}" --revision "${GEMMA_REVISION}")
fi

PORT="${GEMMA_JUDGE_PORT:-8002}"
mkdir -p "$REPO_ROOT/logs"
JOB_TAG="${SLURM_JOB_ID:-manual}"

echo "Starting Gemma-3 judge server on port ${PORT}..."
vllm serve "${GEMMA_SERVE_ARGS[@]}" \
  --served-model-name gemma3-judge \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 16384 \
  > "$REPO_ROOT/logs/vllm_gemma3_judge_full_${JOB_TAG}.log" 2>&1 &
VLLM_PID=$!

cleanup() {
  echo "Stopping Gemma-3 vLLM server if still running..."
  kill "$VLLM_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for Gemma-3 judge server to become ready..."
READY=0
for i in $(seq 1 90); do
  if curl -s "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    echo "Gemma-3 judge server ready after $((i * 10))s."
    READY=1
    break
  fi
  sleep 10
done
if [ "$READY" -ne 1 ]; then
  echo "ERROR: Gemma-3 judge server did not become ready in time." >&2
  echo "---- vLLM server log ----" >&2
  cat "$REPO_ROOT/logs/vllm_gemma3_judge_full_${JOB_TAG}.log" >&2
  exit 1
fi

INPUTS=(
  "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_before.json"
  "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_satimp.json"
  "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_simnpo.json"
  "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_rmu.json"
  "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_wga.json"
  "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_before.json"
  "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_satimp.json"
  "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_simnpo.json"
  "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_rmu.json"
  "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_wga.json"
  "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_before.json"
  "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_satimp.json"
  "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_simnpo.json"
  "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_rmu.json"
  "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_wga.json"
)
OUTPUTS=(
  "external/PersistBench/outputs_gemma3_judge/muse_news/muse_news_qwen25_before.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_news/muse_news_qwen25_satimp.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_news/muse_news_qwen25_simnpo.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_news/muse_news_qwen25_rmu.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_news/muse_news_qwen25_wga.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_llama2_before.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_llama2_satimp.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_llama2_simnpo.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_llama2_rmu.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_llama2_wga.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_qwen25_before.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_qwen25_satimp.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_qwen25_simnpo.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_qwen25_rmu.gemma3.json"
  "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_qwen25_wga.gemma3.json"
)

for idx in "${!INPUTS[@]}"; do
  IN="${INPUTS[$idx]}"
  OUT="${OUTPUTS[$idx]}"
  if [ ! -f "$IN" ]; then
    echo "ERROR: expected canonical generation file not found: $IN" >&2
    echo "       Per the task instructions, do NOT regenerate it -- stop and report instead." >&2
    exit 1
  fi
  if [ -f "$OUT" ]; then
    echo "[$idx/15] SKIP (already judged, output exists): $OUT"
    continue
  fi
  echo "[$idx/15] Judging $IN -> $OUT"
  python thesis/analysis/judge_robustness/gemma_judge.py \
    --input "$IN" \
    --output "$OUT" \
    --base-url "http://127.0.0.1:${PORT}/v1" \
    --concurrency 8
  echo "[$idx/15] done."
done

echo "All 15 Gemma-3 judging tasks complete."
