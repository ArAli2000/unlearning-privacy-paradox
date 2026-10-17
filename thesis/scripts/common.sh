#!/usr/bin/env bash
# Shared helper for thesis/scripts/**/*.sh launchers.
#
# Replaces the pattern (previously hardcoded identically in ~19 launcher
# scripts) of assuming the repository lives at one specific absolute cluster
# path (e.g. /storage/ukp/work/elshashay/open-unlearning or
# /mnt/beegfs/work/elshashay/open-unlearning) and that conda is installed at
# one specific absolute path for one specific user.
#
# Usage, near the top of a launcher (after `set -euo pipefail`):
#
#   source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
#   cd "$REPO_ROOT"
#   activate_unlearning_env          # or: activate_unlearning_env base
#
# Every value this file defines can be overridden by exporting the same-named
# environment variable before running a launcher, e.g.:
#
#   REPO_ROOT=/some/other/checkout UNLEARNING_CONDA_ENV=myenv sbatch thesis/scripts/muse_news/run_muse_news_qwen25_7b_instruct_finetune.sh

# --- Repository root --------------------------------------------------------
# Prefer `git rev-parse --show-toplevel` (robust to the repo being checked
# out anywhere); fall back to a path computed from this file's own location
# (thesis/scripts/common.sh -> two levels up is the repo root), which still
# works if the repo is copied without its .git directory. Respect a
# pre-exported REPO_ROOT if the caller already set one.
if [ -z "${REPO_ROOT:-}" ]; then
  if command -v git >/dev/null 2>&1 && REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)"; then
    :
  else
    REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  fi
fi
export REPO_ROOT

# --- Conda environment -------------------------------------------------------
# UNLEARNING_CONDA_ACTIVATE / UNLEARNING_CONDA_ENV are genuinely
# machine-specific (conda is installed per-user/per-cluster), so they are
# NOT auto-detected -- they default to the exact values these experiments
# were originally run with, and must be overridden via environment variables
# on any other machine.
: "${UNLEARNING_CONDA_ACTIVATE:=/storage/ukp/work/elshashay/miniconda3/bin/activate}"
: "${UNLEARNING_CONDA_ENV:=unlearning}"
export UNLEARNING_CONDA_ACTIVATE UNLEARNING_CONDA_ENV

# activate_unlearning_env [env_name]: source the conda activate script and
# activate the given environment (default: $UNLEARNING_CONDA_ENV, i.e.
# "unlearning"; pass "base" explicitly for the judge-server scripts that
# activate base conda rather than the unlearning env).
activate_unlearning_env() {
  local env_name="${1:-${UNLEARNING_CONDA_ENV}}"
  if [ ! -f "${UNLEARNING_CONDA_ACTIVATE}" ]; then
    echo "ERROR: conda activate script not found at ${UNLEARNING_CONDA_ACTIVATE}" >&2
    echo "       Set UNLEARNING_CONDA_ACTIVATE to the correct path for this machine, e.g.:" >&2
    echo "       export UNLEARNING_CONDA_ACTIVATE=/path/to/miniconda3/bin/activate" >&2
    return 1
  fi
  # shellcheck disable=SC1090
  source "${UNLEARNING_CONDA_ACTIVATE}"
  conda activate "${env_name}"
}
