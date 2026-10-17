#!/bin/bash
#SBATCH --job-name=test_q7_simnpo_best
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=192G
#SBATCH --cpus-per-task=16
#SBATCH --time=48:00:00
#SBATCH --output=logs/test_q7_simnpo_best_%j.out
#SBATCH --error=logs/test_q7_simnpo_best_%j.err

set -e

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME=$HOME/.cache
export TRITON_CACHE_DIR=$HOME/.triton/autotune
export HF_HOME=$HOME/.cache/huggingface
export TRANSFORMERS_CACHE=$HF_HOME

mkdir -p logs
mkdir -p $TRITON_CACHE_DIR
mkdir -p $HF_HOME

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
echo "WORKDIR: $(pwd)"
echo "HOME: $HOME"
echo "HF_HOME: $HF_HOME"
echo "TRITON_CACHE_DIR: $TRITON_CACHE_DIR"
echo "===================================="

nvidia-smi

MODEL="Qwen2.5-7B-Instruct"
METHOD="SimNPO"
PRETRAIN="/storage/ukp/work/elshashay/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28"
TASK_NAME="test_bestagg_qwen25_7b_simnpo_savebest"

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
  eval.tofu.batch_size=8 \
++trainer.args.eval_strategy=steps \
++trainer.args.eval_steps=13 \
++trainer.args.save_strategy=steps \
++trainer.args.save_steps=13 \
++trainer.args.load_best_model_at_end=true \
++trainer.args.metric_for_best_model=eval_Agg_proxy \
++trainer.args.greater_is_better=true \
++trainer.args.save_total_limit=3 \
++trainer.args.save_safetensors=true
echo "Training finished."
RUN_DIR="saves/unlearn/${TASK_NAME}"

echo "Checking trainer_state:"
grep -n '"best_metric"\|"best_model_checkpoint"\|"Agg_proxy"\|"eval_Agg_proxy"' "$RUN_DIR/trainer_state.json" | tail -50 || true

echo "Checking saved model files in parent run folder:"
find "$RUN_DIR" -maxdepth 1 -type f \( -name "*.safetensors" -o -name "model.safetensors.index.json" -o -name "config.json" -o -name "tokenizer.json" \) -print

echo "Done."
