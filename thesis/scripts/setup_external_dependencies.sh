#!/usr/bin/env bash
# Clone/pin/patch the vendored external tool dependencies documented in
# thesis/manifests/external_dependencies/external_dependencies.tsv.
#
# This script is safe to run on a fresh clone of this repository (where
# external/PersistBench and external/privacy-collapse do not yet exist) and
# is idempotent: if a target already exists, it is inspected and left alone
# rather than overwritten, unless it is already correctly set up (in which
# case the script reports that and exits cleanly).
#
# It performs NO destructive operations on an existing checkout: it never
# runs `git reset --hard`, `git clean`, or deletes an existing directory.
set -euo pipefail

# --- 1. Determine repository root dynamically -------------------------------
# Prefer `git rev-parse --show-toplevel` (works regardless of where this
# script physically lives); fall back to a path relative to this script's own
# location only if that fails (e.g. run outside of a git checkout).
if REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  :
else
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
fi

TSV="${REPO_ROOT}/thesis/manifests/external_dependencies/external_dependencies.tsv"

if [ ! -f "${TSV}" ]; then
  echo "ERROR: dependency manifest not found at ${TSV}" >&2
  exit 1
fi

echo "Repository root: ${REPO_ROOT}"
echo "Dependency manifest: ${TSV}"
echo

STATUS=0

# --- 2-4. Process each row of the manifest ----------------------------------
# Skip the header line; tab-separated: name, repository_url, commit,
# local_path, modified_for_thesis, patch_file, notes
while IFS=$'\t' read -r NAME REPO_URL COMMIT LOCAL_PATH MODIFIED PATCH_FILE NOTES; do
  [ -z "${NAME:-}" ] && continue
  TARGET="${REPO_ROOT}/${LOCAL_PATH}"
  echo "=== ${NAME} ==="
  echo "  repository: ${REPO_URL}"
  echo "  pinned commit: ${COMMIT}"
  echo "  target path: ${TARGET}"

  if [ -e "${TARGET}" ]; then
    if [ -d "${TARGET}/.git" ]; then
      CURRENT_COMMIT="$(git -C "${TARGET}" rev-parse HEAD 2>/dev/null || echo "unknown")"
      DIRTY="$(git -C "${TARGET}" status --porcelain 2>/dev/null || echo "?")"
      if [ "${CURRENT_COMMIT}" = "${COMMIT}" ] && [ -z "${DIRTY}" ]; then
        echo "  OK: already present at the pinned commit, clean working tree. Nothing to do."
      else
        echo "  SKIP (not modifying): a working tree already exists at ${TARGET}."
        echo "    current commit: ${CURRENT_COMMIT}"
        [ -n "${DIRTY}" ] && echo "    working tree has local changes (expected if the thesis patch below is already applied)."
        echo "    This script never overwrites, resets, or cleans an existing checkout."
        echo "    If you intend to (re)apply the thesis patch, do so manually; if you intend to"
        echo "    start over, remove ${TARGET} yourself first, then re-run this script."
      fi
    else
      echo "  FAIL: ${TARGET} exists but is not a git checkout (no .git/ directory)."
      echo "        Refusing to touch it. Move or remove it yourself, then re-run this script."
      STATUS=1
    fi
    echo
    continue
  fi

  echo "  Cloning ${REPO_URL} -> ${TARGET} ..."
  if ! git clone "${REPO_URL}" "${TARGET}"; then
    echo "  FAIL: clone failed for ${NAME}." >&2
    STATUS=1
    echo
    continue
  fi

  echo "  Checking out pinned commit ${COMMIT} ..."
  if ! git -C "${TARGET}" checkout --quiet "${COMMIT}"; then
    echo "  FAIL: could not check out ${COMMIT} for ${NAME}. Left the fresh clone in place for inspection." >&2
    STATUS=1
    echo
    continue
  fi

  if [ "${MODIFIED}" = "yes" ] && [ -n "${PATCH_FILE}" ] && [ "${PATCH_FILE}" != "(none)" ]; then
    PATCH_PATH="${REPO_ROOT}/${PATCH_FILE}"
    echo "  Applying thesis patch: ${PATCH_PATH}"
    if [ ! -f "${PATCH_PATH}" ]; then
      echo "  FAIL: patch file ${PATCH_PATH} not found." >&2
      STATUS=1
    elif git -C "${TARGET}" apply --check "${PATCH_PATH}" 2>/dev/null; then
      git -C "${TARGET}" apply "${PATCH_PATH}"
      echo "  Patch applied cleanly."
    else
      echo "  FAIL: patch does not apply cleanly against the freshly-cloned pinned commit." >&2
      echo "        This should not happen if the pinned commit matches what the patch was" >&2
      echo "        generated against; inspect ${PATCH_PATH} manually." >&2
      STATUS=1
    fi
  else
    echo "  No thesis patch recorded for ${NAME}; using it unmodified."
  fi
  echo
done < <(tail -n +2 "${TSV}")

if [ "${STATUS}" -ne 0 ]; then
  echo "One or more dependencies were not fully set up; see FAIL/SKIP messages above." >&2
  exit 1
fi

echo "External dependency setup complete."
echo "Note: this script does not recreate the run-time-generated content (external/PersistBench/configs_local/, outputs/, logs/) -- those are produced fresh by thesis/scripts/persistbench/*.sh when you actually run them."
