#!/usr/bin/env bash
# Shared helpers for the thesis/scripts launchers.
# Usage (after `set -euo pipefail`):
#   source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"
#   cd "$REPO_ROOT"
#   activate_unlearning_env          # or: activate_unlearning_env base
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

# Conda location is machine-specific, so it is not auto-detected; override on other machines.
: "${UNLEARNING_CONDA_ACTIVATE:=/storage/ukp/work/elshashay/miniconda3/bin/activate}"
: "${UNLEARNING_CONDA_ENV:=unlearning}"
export UNLEARNING_CONDA_ACTIVATE UNLEARNING_CONDA_ENV

# activate_unlearning_env [env_name]: default $UNLEARNING_CONDA_ENV; the judge-server scripts pass "base".
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
