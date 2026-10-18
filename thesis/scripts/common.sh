#!/usr/bin/env bash
# Shared helpers for the thesis/scripts launchers.
# Usage (after `set -euo pipefail`):
#   source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
#   cd "$REPO_ROOT"
#   activate_unlearning_env          # or: activate_unlearning_env base  (see the conda section below)
# Every variable below can be overridden from the environment, e.g.
#   REPO_ROOT=/some/checkout UNLEARNING_CONDA_ENV=myenv sbatch <launcher>

# Repo root: git first, else two levels up from this file (works without .git).
if [ -z "${REPO_ROOT:-}" ]; then
  if command -v git >/dev/null 2>&1 && REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)"; then
    :
  else
    REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  fi
fi
export REPO_ROOT

# Conda environment selection. Nothing machine-specific is assumed. Order of precedence:
#   1. UNLEARNING_CONDA_ACTIVATE, if set: path to your conda `activate` script
#      (e.g. /path/to/miniconda3/bin/activate); it is sourced and the environment is activated by name.
#   2. The conda environment that is already active when the launcher starts, if it is the environment
#      requested (name match), or if UNLEARNING_USE_ACTIVE_ENV=1 (accept whatever environment is active).
#      `sbatch` passes the submitting shell's environment on, so `conda activate <env>` before `sbatch` works.
#   3. Otherwise the launcher stops with an error that says what to configure.
# Requested names: UNLEARNING_CONDA_ENV (default "unlearning") for training/evaluation launchers;
# the vLLM serving/judging launchers request "base" (see thesis/manifests/environment/ for both environments).
: "${UNLEARNING_CONDA_ENV:=unlearning}"
export UNLEARNING_CONDA_ENV

# activate_unlearning_env [env_name]: default $UNLEARNING_CONDA_ENV; the judge-server scripts pass "base".
activate_unlearning_env() {
  local env_name="${1:-${UNLEARNING_CONDA_ENV}}"
  if [ -n "${UNLEARNING_CONDA_ACTIVATE:-}" ]; then
    if [ ! -f "${UNLEARNING_CONDA_ACTIVATE}" ]; then
      echo "ERROR: UNLEARNING_CONDA_ACTIVATE does not point to a file: ${UNLEARNING_CONDA_ACTIVATE}" >&2
      return 1
    fi
    # shellcheck disable=SC1090
    source "${UNLEARNING_CONDA_ACTIVATE}"
    conda activate "${env_name}"
    return
  fi
  if [ -n "${CONDA_PREFIX:-}" ] && { [ "${CONDA_DEFAULT_ENV:-}" = "${env_name}" ] || [ "${UNLEARNING_USE_ACTIVE_ENV:-0}" = "1" ]; }; then
    echo "Using the active conda environment: ${CONDA_DEFAULT_ENV:-$CONDA_PREFIX}" >&2
    return 0
  fi
  echo "ERROR: no conda environment configured for this launcher (requested: ${env_name})." >&2
  echo "       Do ONE of the following before running it:" >&2
  echo "         - export UNLEARNING_CONDA_ACTIVATE=/path/to/miniconda3/bin/activate   (the launcher then activates '${env_name}')" >&2
  echo "         - run 'conda activate ${env_name}' in the shell that submits the job" >&2
  echo "         - export UNLEARNING_USE_ACTIVE_ENV=1 to accept the currently active environment, whatever its name" >&2
  echo "       Active environment now: ${CONDA_DEFAULT_ENV:-none}" >&2
  return 1
}
