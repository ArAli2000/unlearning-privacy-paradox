#!/bin/bash
#SBATCH --job-name=wmdp_bio_test
#SBATCH --output=logs/wmdp_bio_test_%j.out
#SBATCH --error=logs/wmdp_bio_test_%j.err
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=04:00:00

set -euo pipefail

cd /storage/ukp/work/elshashay/open-unlearning

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

python src/eval.py --config-name=eval.yaml \
  experiment=eval/wmdp/default \
  data_split=bio \
  task_name=wmdp_bio_muse_books_qwen25_before \
  model.model_args.pretrained_model_name_or_path=saves/finetune/muse_books_qwen25_7b_instruct_target \
  model.tokenizer_args.pretrained_model_name_or_path=saves/finetune/muse_books_qwen25_7b_instruct_target \
  eval.lm_eval.tasks=[wmdp_bio] \
  eval.lm_eval.simple_evaluate_args.batch_size=4
