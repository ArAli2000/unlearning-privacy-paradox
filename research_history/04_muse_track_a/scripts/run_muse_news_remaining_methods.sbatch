#!/bin/bash
#SBATCH --job-name=muse_news_methods
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --mem=128G
#SBATCH --cpus-per-task=8
#SBATCH --time=08:00:00
#SBATCH --array=0-2
#SBATCH --chdir=/storage/ukp/work/elshashay/open-unlearning
#SBATCH --output=logs/muse_news_%A_%a.out
#SBATCH --error=logs/muse_news_%A_%a.err

set -euo pipefail

METHODS=("WGA" "RMU" "SatImp")
METHOD="${METHODS[$SLURM_ARRAY_TASK_ID]}"

case "$METHOD" in
  WGA) TASK_METHOD="wga" ;;
  RMU) TASK_METHOD="rmu" ;;
  SatImp) TASK_METHOD="satimp" ;;
esac

TASK_NAME="muse_news_${TASK_METHOD}_ckpts_bs1_gc_sbatch"

source /storage/ukp/work/elshashay/miniconda3/etc/profile.d/conda.sh
conda activate unlearning

module load cuda/12.2 || true
if command -v nvcc >/dev/null 2>&1; then
  export CUDA_HOME=$(dirname "$(dirname "$(which nvcc)")")
  export PATH="$CUDA_HOME/bin:$PATH"
  export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
fi

export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME=/storage/ukp/work/elshashay/.cache
export TRITON_CACHE_DIR=/storage/ukp/work/elshashay/.cache/triton
export HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/storage/ukp/work/elshashay/.cache/huggingface/hub
export TORCH_HOME=/storage/ukp/work/elshashay/.cache/torch
export TMPDIR=/storage/ukp/work/elshashay/tmp
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

mkdir -p "$XDG_CACHE_HOME" "$TRITON_CACHE_DIR" "$HF_HOME" "$HUGGINGFACE_HUB_CACHE" "$TORCH_HOME" "$TMPDIR" logs

echo "Host: $(hostname)"
echo "Method: $METHOD"
echo "Task name: $TASK_NAME"
nvidia-smi

python - <<'PY'
import torch
print("cuda available:", torch.cuda.is_available())
print("gpu:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
PY

python src/train.py --config-name=unlearn.yaml \
  experiment=unlearn/muse/default \
  data_split=News \
  trainer="$METHOD" \
  task_name="$TASK_NAME" \
  model.tokenizer_args.pretrained_model_name_or_path=NousResearch/Llama-2-7b-hf \
  trainer.args.save_strategy=epoch \
  +trainer.args.save_total_limit=10 \
  trainer.args.per_device_train_batch_size=1 \
  trainer.args.per_device_eval_batch_size=4 \
  trainer.args.gradient_accumulation_steps=8 \
  trainer.args.gradient_checkpointing=true
