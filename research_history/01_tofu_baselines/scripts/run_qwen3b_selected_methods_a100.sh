#!/bin/bash
#SBATCH --job-name=qwen3b_selected
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a100:1
#SBATCH --mem=256G
#SBATCH --cpus-per-task=16
#SBATCH --time=18:00:00
#SBATCH --array=0-5
#SBATCH --output=logs/qwen3b_selected_%A_%a.out
#SBATCH --error=logs/qwen3b_selected_%A_%a.err

set -e

export HOME=/storage/ukp/work/elshashay
mkdir -p $HOME/.triton/autotune

module load cuda/12.2 || true

export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

cd /storage/ukp/work/elshashay/open-unlearning
mkdir -p logs

source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

echo "HOSTNAME: $(hostname)"
echo "JOB ID: $SLURM_JOB_ID"
echo "ARRAY TASK: $SLURM_ARRAY_TASK_ID"
nvidia-smi

METHODS=("SimNPO" "AltPO" "SatImp" "WGA" "CEU" "PDU")
METHOD=${METHODS[$SLURM_ARRAY_TASK_ID]}

TASK_NAME="tofu_qwen25_3b_${METHOD,,}_f10_a100"

echo "Running method: $METHOD"
echo "Task name: $TASK_NAME"

python src/train.py \
  --config-name=unlearn.yaml \
  experiment=unlearn/tofu/default \
  model=Qwen2.5-3B-Instruct \
  forget_split=forget10 \
  retain_split=retain90 \
  trainer=$METHOD \
  task_name=$TASK_NAME \
  model.model_args.pretrained_model_name_or_path=Qwen/Qwen2.5-3B-Instruct \
  model.tokenizer_args.pretrained_model_name_or_path=Qwen/Qwen2.5-3B-Instruct \
  model.model_args.attn_implementation=sdpa
