#!/bin/bash
#SBATCH --job-name=test_books_target
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#SBATCH --partition=gpu
#SBATCH --nodelist=penelope
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=80G
#SBATCH --time=01:00:00

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
cd "$REPO_ROOT"
activate_unlearning_env

export HF_HOME="${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}"
export TRANSFORMERS_CACHE=$HF_HOME
export CUDA_HOME="${CUDA_HOME:-/nfs/cuda/cuda-12.2}"  # cluster default; override for your CUDA toolkit
export TOKENIZERS_PARALLELISM=false

python src/eval.py --config-name=eval.yaml \
  experiment=eval/muse/default \
  data_split=Books \
  task_name=test_muse_books_target_before_eval \
  model.model_args.pretrained_model_name_or_path=muse-bench/MUSE-Books_target \
  model.tokenizer_args.pretrained_model_name_or_path=NousResearch/Llama-2-7b-hf
