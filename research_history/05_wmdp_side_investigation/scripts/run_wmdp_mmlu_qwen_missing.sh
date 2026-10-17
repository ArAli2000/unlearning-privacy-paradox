#!/bin/bash
#SBATCH --job-name=wmdp_mmlu_qwen_missing
#SBATCH --output=logs/wmdp_mmlu_qwen_missing_%A_%a.out
#SBATCH --error=logs/wmdp_mmlu_qwen_missing_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=02:00:00
#SBATCH --array=0-1

set -euo pipefail

REPO="/storage/ukp/work/elshashay/open-unlearning"
MANIFEST="$REPO/research_history/05_wmdp_side_investigation/manifests/wmdp_mmlu_qwen_missing.tsv"

cd "$REPO"

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME=$HOME/.cache
export HF_HOME=$HOME/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME
export HF_DATASETS_CACHE=$HF_HOME/datasets
export TRITON_CACHE_DIR=$HOME/.triton/autotune
mkdir -p "$XDG_CACHE_HOME" "$HF_HOME" "$HF_DATASETS_CACHE" "$TRITON_CACHE_DIR"

LABEL=$(awk -F $'\t' -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $1}' "$MANIFEST")
MODEL_PATH=$(awk -F $'\t' -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $2}' "$MANIFEST")
TOKENIZER_PATH=$(awk -F $'\t' -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $3}' "$MANIFEST")

echo "======================================"
echo "MMLU utility rerun for missing Qwen WMDP methods"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Label: $LABEL"
echo "Model: $MODEL_PATH"
echo "Tokenizer: $TOKENIZER_PATH"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================"

python src/eval.py --config-name=eval.yaml \
  experiment=eval/wmdp/default \
  data_split=cyber \
  task_name=wmdp_mmlu_utility_${LABEL}_limit50 \
  "model.model_args.pretrained_model_name_or_path=$MODEL_PATH" \
  "model.tokenizer_args.pretrained_model_name_or_path=$TOKENIZER_PATH" \
  'eval.lm_eval.tasks=[mmlu]' \
  eval.lm_eval.simple_evaluate_args.batch_size=4 \
  '+eval.lm_eval.simple_evaluate_args.limit=50' \
  eval.lm_eval.overwrite=true
