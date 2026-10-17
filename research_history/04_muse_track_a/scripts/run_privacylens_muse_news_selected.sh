#!/bin/bash
#SBATCH --job-name=plens_muse_news
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=180G
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --array=0-4%1
#SBATCH --output=logs/plens_muse_news_%A_%a.out
#SBATCH --error=logs/plens_muse_news_%A_%a.err

set -euo pipefail

cd /storage/ukp/work/elshashay/open-unlearning
mkdir -p logs

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME=$HOME/.cache
export TRITON_CACHE_DIR=$HOME/.triton/autotune
export HF_HOME=$HOME/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TOKENIZERS_PARALLELISM=false

module load cuda/12.2 || true

export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

LABELS=(
  "muse_news_before"
  "muse_news_rmu_selected"
  "muse_news_wga_selected"
  "muse_news_simnpo_selected"
  "muse_news_satimp_selected"
)

MODEL_PATHS=(
  "muse-bench/MUSE-News_target"
  "/storage/ukp/work/elshashay/open-unlearning/saves/unlearn/muse_news_rmu_ckpts_bs1_gc_sbatch/checkpoint-500"
  "/storage/ukp/work/elshashay/open-unlearning/saves/unlearn/muse_news_wga_ckpts_bs1_gc_sbatch/checkpoint-357"
  "/storage/ukp/work/elshashay/open-unlearning/saves/unlearn/muse_news_simnpo_ckpts_bs1_gc_sbatch/checkpoint-459"
  "/storage/ukp/work/elshashay/open-unlearning/saves/unlearn/muse_news_satimp_ckpts_bs1_gc_sbatch/checkpoint-500"
)

LABEL=${LABELS[$SLURM_ARRAY_TASK_ID]}
MODEL_PATH=${MODEL_PATHS[$SLURM_ARRAY_TASK_ID]}

# For selected checkpoints, tokenizer is inside the checkpoint.
# For the MUSE target model, use the compatible ungated Llama-2 tokenizer.
if [ "$LABEL" = "muse_news_before" ]; then
  TOKENIZER_PATH="NousResearch/Llama-2-7b-hf"
else
  TOKENIZER_PATH="$MODEL_PATH"
fi

INPUT_PATH="external/privacy-collapse/benchmarks/privacylens/data/main_data.json"
OUT_ROOT="outputs/privacylens_muse_news_selected"
OUT_DIR="${OUT_ROOT}/${LABEL}"
mkdir -p "$OUT_DIR"

echo "======================================================"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Label: $LABEL"
echo "Model path: $MODEL_PATH"
echo "Tokenizer path: $TOKENIZER_PATH"
echo "Input path: $INPUT_PATH"
echo "Output dir: $OUT_DIR"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================================"

if [ "$LABEL" != "muse_news_before" ]; then
  if [ ! -d "$MODEL_PATH" ]; then
    echo "ERROR: model path does not exist:"
    echo "$MODEL_PATH"
    exit 1
  fi

  if ! find "$MODEL_PATH" -maxdepth 1 \( -type f -o -type l \) \( -name "*.safetensors" -o -name "pytorch_model*.bin" -o -name "model.safetensors.index.json" \) | grep -q .; then
    echo "ERROR: model path has no model weights."
    exit 1
  fi
fi

python scripts/eval_privacylens_mcq_local.py \
  --input-path "$INPUT_PATH" \
  --output-path "${OUT_DIR}/privacy_mcq_all493.json" \
  --model-path "$MODEL_PATH" \
  --tokenizer-path "$TOKENIZER_PATH" \
  --model-label "$LABEL"

echo "Done: $LABEL"
echo "Output: ${OUT_DIR}/privacy_mcq_all493.json"
