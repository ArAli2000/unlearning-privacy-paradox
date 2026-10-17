#!/bin/bash
#SBATCH --job-name=wmdp_cyb_rmu_qwen
#SBATCH --output=logs/wmdp_cyber_qwen25_7b_rmu_test_%j.out
#SBATCH --error=logs/wmdp_cyber_qwen25_7b_rmu_test_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=02:00:00

set -euo pipefail

REPO="/storage/ukp/work/elshashay/open-unlearning"
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

echo "======================================"
echo "WMDP-Cyber RMU test"
echo "Model: Qwen/Qwen2.5-7B-Instruct"
echo "Node: $(hostname)"
echo "Date: $(date)"
echo "======================================"

python src/train.py --config-name=unlearn.yaml \
  experiment=unlearn/wmdp/default \
  data_split=cyber \
  task_name=wmdp_cyber_qwen25_7b_rmu_test \
  model.model_args.pretrained_model_name_or_path=Qwen/Qwen2.5-7B-Instruct \
  model.tokenizer_args.pretrained_model_name_or_path=Qwen/Qwen2.5-7B-Instruct \
  trainer.args.max_steps=20 \
  trainer.args.eval_strategy=no \
  trainer.args.save_strategy=steps \
  +trainer.args.save_steps=20 \
  trainer.args.per_device_train_batch_size=1 \
  trainer.args.gradient_accumulation_steps=16
