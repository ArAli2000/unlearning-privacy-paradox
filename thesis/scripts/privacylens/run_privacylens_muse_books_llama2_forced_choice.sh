#!/bin/bash
#SBATCH --job-name=plens_books_llama_fc
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=180G
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --array=0-4%1
#SBATCH --output=logs/plens_books_llama_fc_%A_%a.out
#SBATCH --error=logs/plens_books_llama_fc_%A_%a.err

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
cd "$REPO_ROOT"
mkdir -p logs

export HOME="${UNLEARNING_HOME:-$HOME}"
export XDG_CACHE_HOME=$HOME/.cache
export TRITON_CACHE_DIR=$HOME/.triton/autotune
export HF_HOME=$HOME/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

module load cuda/12.2 || true

export CUDA_HOME="${CUDA_HOME:-/nfs/cuda/cuda-12.2}"  # cluster default; override for your CUDA toolkit
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}

activate_unlearning_env

LABELS=(
  "muse_books_llama2_before"
  "muse_books_llama2_rmu"
  "muse_books_llama2_wga"
  "muse_books_llama2_simnpo"
  "muse_books_llama2_satimp"
)

MODEL_PATHS=(
  "muse-bench/MUSE-Books_target"
  "$(awk -F'\t' '$1=="RMU"{print $2}' saves/final_muse_books_llama2_7b_selection/SELECTED_MODEL_PATHS.tsv)"
  "$(awk -F'\t' '$1=="WGA"{print $2}' saves/final_muse_books_llama2_7b_selection/SELECTED_MODEL_PATHS.tsv)"
  "$(awk -F'\t' '$1=="SIMNPO"{print $2}' saves/final_muse_books_llama2_7b_selection/SELECTED_MODEL_PATHS.tsv)"
  "$(awk -F'\t' '$1=="SATIMP"{print $2}' saves/final_muse_books_llama2_7b_selection/SELECTED_MODEL_PATHS.tsv)"
)

LABEL=${LABELS[$SLURM_ARRAY_TASK_ID]}
MODEL_PATH=${MODEL_PATHS[$SLURM_ARRAY_TASK_ID]}
TOKENIZER_PATH="NousResearch/Llama-2-7b-hf"

INPUT_PATH="external/privacy-collapse/benchmarks/privacylens/data/main_data.json"
OUT_ROOT="outputs/privacylens_muse_books_llama2_forced_choice"
OUT_DIR="${OUT_ROOT}/${LABEL}"
mkdir -p "$OUT_DIR"

echo "======================================================"
echo "Forced-choice PrivacyLens"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Label: $LABEL"
echo "Model path: $MODEL_PATH"
echo "Tokenizer path: $TOKENIZER_PATH"
echo "Output dir: $OUT_DIR"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================================"

python "$REPO_ROOT/thesis/scripts/privacylens/eval_privacylens_mcq_forced_choice.py" \
  --input-path "$INPUT_PATH" \
  --output-path "${OUT_DIR}/privacy_mcq_forced_choice_all493.json" \
  --model-path "$MODEL_PATH" \
  --tokenizer-path "$TOKENIZER_PATH" \
  --model-label "$LABEL" \
  --prompt-type naive

echo "Done: $LABEL"
