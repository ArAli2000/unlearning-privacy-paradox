#!/bin/bash
#SBATCH --job-name=gemma3_promptlen
#SBATCH --account=ukp-student
#SBATCH --partition=cpu
#SBATCH --qos=cpu
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#
# CPU-only, tokenizer-only measurement of the real Gemma-3 judge prompt sizes
# (one real generation -> its own real category's rubric -> its real judge
# request), superseding the earlier all-rubrics-per-generation scans. No GPU,
# no model weights loaded -- AutoTokenizer only. See
# measure_gemma3_prompt_lengths.py for the full method.

set -euo pipefail

# SLURM copies the submitted script into a per-job spool directory before
# running it, so a ${BASH_SOURCE[0]}-relative path does not resolve to this
# file's real repo location. Use $SLURM_SUBMIT_DIR (the directory `sbatch`
# was invoked from) instead, per the lesson recorded in
# smoke_test/SLURM_DIAGNOSIS.md.
REPO_ROOT="$(cd "${SLURM_SUBMIT_DIR:-$PWD}" && git rev-parse --show-toplevel)"
source "$REPO_ROOT/thesis/scripts/common.sh"
cd "$REPO_ROOT"

# NOTE: the default "unlearning" env's installed `anthropic` package is
# incompatible with its installed `pydantic` (ImportError: cannot import name
# 'ModelField' from 'pydantic.fields'), and importing
# external/PersistBench/src/benchmark/prompts triggers benchmark/__init__.py,
# which imports the full benchmark_runner chain including the anthropic
# provider -- confirmed by a direct dry run. gemma_judge.py has only ever been
# run under "base" (see run_gemma_judge.sbatch / run_gemma_judge_smoketest.sbatch),
# which does not hit this; use the same env here for the same imports.
activate_unlearning_env base

# Writable HOME/cache paths for the compute node (the login-node $HOME is not
# writable from compute nodes on this cluster -- see
# smoke_test/GEMMA_VLLM_DIAGNOSIS.md). Not strictly required for a
# local-path-only tokenizer load, but set for safety/consistency with every
# other job in this directory.
export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME="$HOME/.cache"
export HF_HOME="$XDG_CACHE_HOME/huggingface"
export TRANSFORMERS_CACHE="$HF_HOME"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
mkdir -p "$XDG_CACHE_HOME" "$HF_HOME" "$HF_DATASETS_CACHE"

export HF_HUB_OFFLINE=1          # local path only; must not attempt any network access
export TRANSFORMERS_OFFLINE=1

python thesis/analysis/judge_robustness/measure_gemma3_prompt_lengths.py
