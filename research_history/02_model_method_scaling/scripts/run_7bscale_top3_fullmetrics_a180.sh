#!/bin/bash
#SBATCH --job-name=top3_7bscale
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=192G
#SBATCH --cpus-per-task=16
#SBATCH --time=48:00:00
#SBATCH --array=0-5%1
#SBATCH --output=logs/top3_7bscale_%A_%a.out
#SBATCH --error=logs/top3_7bscale_%A_%a.err

set -e

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME=$HOME/.cache
export TRITON_CACHE_DIR=$HOME/.triton/autotune
export HF_HOME=$HOME/.cache/huggingface

mkdir -p $TRITON_CACHE_DIR
mkdir -p $HF_HOME
mkdir -p logs

module load cuda/12.2 || true

export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

cd /mnt/beegfs/work/elshashay/open-unlearning

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

echo "===================================="
echo "HOSTNAME: $(hostname)"
echo "JOB ID: $SLURM_JOB_ID"
echo "ARRAY TASK: $SLURM_ARRAY_TASK_ID"
echo "WORKDIR: $(pwd)"
echo "HOME: $HOME"
echo "TRITON_CACHE_DIR: $TRITON_CACHE_DIR"
echo "CUDA_HOME: $CUDA_HOME"
echo "===================================="

nvidia-smi

METHODS=("SatImp" "SimNPO" "WGA" "SatImp" "SimNPO" "WGA")
MODELS=("Llama-3.1-8B-Instruct" "Llama-3.1-8B-Instruct" "Llama-3.1-8B-Instruct" "Qwen2.5-7B-Instruct" "Qwen2.5-7B-Instruct" "Qwen2.5-7B-Instruct")

METHOD=${METHODS[$SLURM_ARRAY_TASK_ID]}
MODEL=${MODELS[$SLURM_ARRAY_TASK_ID]}

if [ "$MODEL" = "Llama-3.1-8B-Instruct" ]; then
  PRETRAIN="/storage/ukp/shared/shared_model_weights/models--meta-llama--Llama-3.1-8B-Instruct"
  TASK_PREFIX="paper_llama31_8b"
else
  LOCAL_QWEN="/storage/ukp/shared/shared_model_weights/models--Qwen--Qwen2.5-7B-Instruct"
  if [ -d "$LOCAL_QWEN" ]; then
    PRETRAIN="$LOCAL_QWEN"
  else
    PRETRAIN="Qwen/Qwen2.5-7B-Instruct"
  fi
  TASK_PREFIX="paper_qwen25_7b"
fi

TASK_NAME="${TASK_PREFIX}_${METHOD,,}_f10_a180_fullmetrics"

echo "Running model: $MODEL"
echo "Running method: $METHOD"
echo "Pretrained path: $PRETRAIN"
echo "Task name: $TASK_NAME"

python src/train.py \
  --config-name=unlearn.yaml \
  experiment=unlearn/tofu/default \
  model=$MODEL \
  forget_split=forget10 \
  retain_split=retain90 \
  trainer=$METHOD \
  task_name=$TASK_NAME \
  model.model_args.pretrained_model_name_or_path=$PRETRAIN \
  model.tokenizer_args.pretrained_model_name_or_path=$PRETRAIN \
  model.model_args.attn_implementation=sdpa \
  trainer.args.per_device_train_batch_size=1 \
  trainer.args.per_device_eval_batch_size=4 \
  trainer.args.gradient_accumulation_steps=32 \
  eval.tofu.batch_size=8
