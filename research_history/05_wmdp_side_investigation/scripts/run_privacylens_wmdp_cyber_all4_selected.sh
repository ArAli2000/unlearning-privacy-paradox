#!/bin/bash
#SBATCH --job-name=plens_wmdp
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=180G
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00
#SBATCH --array=0-9%1
#SBATCH --output=logs/plens_wmdp_%A_%a.out
#SBATCH --error=logs/plens_wmdp_%A_%a.err

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
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

module load cuda/12.2 || true

export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

SELECTED_ROOT="saves/final_wmdp_cyber_all4_selection/selected_checkpoints"

LABELS=(
  "wmdp_cyber_llama2_7b_before"
  "wmdp_cyber_llama2_7b_rmu_selected"
  "wmdp_cyber_llama2_7b_wga_selected"
  "wmdp_cyber_llama2_7b_simnpo_selected"
  "wmdp_cyber_llama2_7b_satimp_selected"
  "wmdp_cyber_qwen25_7b_before"
  "wmdp_cyber_qwen25_7b_rmu_selected"
  "wmdp_cyber_qwen25_7b_wga_selected"
  "wmdp_cyber_qwen25_7b_simnpo_selected"
  "wmdp_cyber_qwen25_7b_satimp_selected"
)

MODEL_PATHS=(
  "NousResearch/Llama-2-7b-hf"
  "${SELECTED_ROOT}/llama2_7b_rmu_selected"
  "${SELECTED_ROOT}/llama2_7b_wga_selected"
  "${SELECTED_ROOT}/llama2_7b_simnpo_selected"
  "${SELECTED_ROOT}/llama2_7b_satimp_selected"
  "Qwen/Qwen2.5-7B-Instruct"
  "${SELECTED_ROOT}/qwen25_7b_rmu_selected"
  "${SELECTED_ROOT}/qwen25_7b_wga_selected"
  "${SELECTED_ROOT}/qwen25_7b_simnpo_selected"
  "${SELECTED_ROOT}/qwen25_7b_satimp_selected"
)

TOKENIZER_PATHS=(
  "NousResearch/Llama-2-7b-hf"
  "NousResearch/Llama-2-7b-hf"
  "NousResearch/Llama-2-7b-hf"
  "NousResearch/Llama-2-7b-hf"
  "NousResearch/Llama-2-7b-hf"
  "Qwen/Qwen2.5-7B-Instruct"
  "Qwen/Qwen2.5-7B-Instruct"
  "Qwen/Qwen2.5-7B-Instruct"
  "Qwen/Qwen2.5-7B-Instruct"
  "Qwen/Qwen2.5-7B-Instruct"
)

LABEL=${LABELS[$SLURM_ARRAY_TASK_ID]}
MODEL_PATH=${MODEL_PATHS[$SLURM_ARRAY_TASK_ID]}
TOKENIZER_PATH=${TOKENIZER_PATHS[$SLURM_ARRAY_TASK_ID]}

INPUT_PATH="external/privacy-collapse/benchmarks/privacylens/data/main_data.json"
OUT_ROOT="outputs/privacylens_wmdp_cyber_all4_selected"
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

# Before models are HuggingFace IDs. Selected models are local symlinked checkpoints.
if [[ "$LABEL" != *"_before" ]]; then
  if [ ! -d "$MODEL_PATH" ]; then
    echo "ERROR: model path does not exist:"
    echo "$MODEL_PATH"
    exit 1
  fi

  if ! find -L "$MODEL_PATH" -maxdepth 1 \( -type f -o -type l \) \( -name "*.safetensors" -o -name "pytorch_model*.bin" -o -name "model.safetensors.index.json" \) | grep -q .; then
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
