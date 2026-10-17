#!/bin/bash
#SBATCH --job-name=llama1b_fullmetrics
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=96G
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
#SBATCH --array=0-8%2
#SBATCH --output=logs/llama1b_fullmetrics_%A_%a.out
#SBATCH --error=logs/llama1b_fullmetrics_%A_%a.err

set -e

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME=$HOME/.cache
export TRITON_CACHE_DIR=$HOME/.triton/autotune
export HF_HOME=$HOME/.cache/huggingface

mkdir -p $TRITON_CACHE_DIR
mkdir -p $HF_HOME

module load cuda/12.2 || true

export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

cd /mnt/beegfs/work/elshashay/open-unlearning
mkdir -p logs

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

echo "===================================="
echo "HOSTNAME: $(hostname)"
echo "JOB ID: $SLURM_JOB_ID"
echo "ARRAY TASK: $SLURM_ARRAY_TASK_ID"
echo "WORKDIR: $(pwd)"
echo "CUDA_HOME: $CUDA_HOME"
echo "HOME: $HOME"
echo "TRITON_CACHE_DIR: $TRITON_CACHE_DIR"
echo "===================================="

nvidia-smi

METHODS=("SatImp" "WGA" "CEU" "NPO" "GradAscent" "GradDiff" "RMU" "UNDIAL" "PDU")
METHOD=${METHODS[$SLURM_ARRAY_TASK_ID]}

TASK_NAME="paper_llama32_1b_${METHOD,,}_f10_a180_fullmetrics"

echo "Running method: $METHOD"
echo "Task name: $TASK_NAME"

BASE_CMD="python src/train.py \
  --config-name=unlearn.yaml \
  experiment=unlearn/tofu/default \
  model=Llama-3.2-1B-Instruct \
  forget_split=forget10 \
  retain_split=retain90 \
  trainer=$METHOD \
  task_name=$TASK_NAME \
  model.model_args.pretrained_model_name_or_path=/storage/ukp/shared/shared_model_weights/models--meta-llama--Llama-3.2-1B-Instruct \
  model.tokenizer_args.pretrained_model_name_or_path=/storage/ukp/shared/shared_model_weights/models--meta-llama--Llama-3.2-1B-Instruct \
  model.model_args.attn_implementation=sdpa"

if [ "$METHOD" = "PDU" ]; then
  echo "Adding PDU-specific retain_loss_eps override"
  BASE_CMD="$BASE_CMD trainer.method_args.retain_loss_eps=0.1"
fi

echo "Command:"
echo "$BASE_CMD"

eval $BASE_CMD
