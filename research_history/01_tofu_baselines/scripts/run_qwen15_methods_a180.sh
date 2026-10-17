#!/bin/bash
#SBATCH --job-name=qwen15_methods
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=256G
#SBATCH --cpus-per-task=16
#SBATCH --array=0-7
#SBATCH --output=logs/qwen15_%A_%a.out
#SBATCH --error=logs/qwen15_%A_%a.err

METHODS=(SimNPO DPO RMU WGA CEU PDU UNDIAL SatImp)
METHOD=${METHODS[$SLURM_ARRAY_TASK_ID]}
METHOD_LOWER=$(echo "$METHOD" | tr '[:upper:]' '[:lower:]')

export HOME=/storage/ukp/work/elshashay
mkdir -p $HOME/.triton/autotune
mkdir -p logs

module load cuda/12.2
export CUDA_HOME=/nfs/cuda/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

cd /storage/ukp/work/elshashay/open-unlearning
source /storage/ukp/work/elshashay/miniconda3/bin/activate
conda activate unlearning

python src/train.py --config-name=unlearn.yaml experiment=unlearn/tofu/default \
  model=Qwen2.5-1.5B-Instruct \
  forget_split=forget10 retain_split=retain90 trainer=${METHOD} \
  task_name=tofu_qwen25_15b_${METHOD_LOWER}_f10 \
  model.model_args.pretrained_model_name_or_path=Qwen/Qwen2.5-1.5B-Instruct \
  model.tokenizer_args.pretrained_model_name_or_path=Qwen/Qwen2.5-1.5B-Instruct \
  model.model_args.attn_implementation=sdpa
