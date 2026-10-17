#!/bin/bash
#SBATCH --job-name=wmdp_all4_smoke
#SBATCH --output=logs/wmdp_cyber_all4_smoke_%A_%a.out
#SBATCH --error=logs/wmdp_cyber_all4_smoke_%A_%a.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=02:00:00
#SBATCH --array=0-7

set -euo pipefail

REPO="/storage/ukp/work/elshashay/open-unlearning"
MANIFEST="$REPO/research_history/05_wmdp_side_investigation/manifests/wmdp_cyber_all4_models_methods.tsv"

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

LABEL=$(awk -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $1}' "$MANIFEST")
TRAINER_CONFIG=$(awk -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $2}' "$MANIFEST")
METHOD_LABEL=$(awk -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $3}' "$MANIFEST")
MODEL_PATH=$(awk -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $4}' "$MANIFEST")
TOKENIZER_PATH=$(awk -v i="$SLURM_ARRAY_TASK_ID" 'NR==i+1 {print $5}' "$MANIFEST")

echo "======================================"
echo "WMDP-Cyber all-4-method smoke test"
echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Label: $LABEL"
echo "Trainer: $TRAINER_CONFIG"
echo "Method label: $METHOD_LABEL"
echo "Model: $MODEL_PATH"
echo "Tokenizer: $TOKENIZER_PATH"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================"

python src/train.py --config-name=unlearn.yaml \
  experiment=unlearn/wmdp/default \
  trainer="$TRAINER_CONFIG" \
  data_split=cyber \
  task_name=wmdp_cyber_${LABEL}_${METHOD_LABEL}_smoke \
  model.model_args.pretrained_model_name_or_path="$MODEL_PATH" \
  model.tokenizer_args.pretrained_model_name_or_path="$TOKENIZER_PATH" \
  trainer.args.max_steps=5 \
  trainer.args.eval_strategy=no \
  trainer.args.save_strategy=steps \
  +trainer.args.save_steps=5 \
  trainer.args.per_device_train_batch_size=1 \
  trainer.args.gradient_accumulation_steps=1 \
  eval.lm_eval.tasks=[wmdp_cyber]
