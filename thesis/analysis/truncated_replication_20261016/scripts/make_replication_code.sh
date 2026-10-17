#!/usr/bin/env bash
# Builds an ISOLATED copy of the PersistBench package whose generation behaviour equals the code state at the time of the original
# MUSE generations (2026-07-05..12): upstream HEAD + judge patches + the two inert early utils.py layers, WITHOUT the 2026-07-21
# STRICT_GENERATION_CONTROL block (which would force repetition_penalty=1.08, top_p=1.0 and inject a system prompt).
# The live external/PersistBench tree is NOT modified. Output: ../persistbench_code/
set -euo pipefail
R=/mnt/beegfs/work/elshashay/open-unlearning
HERE="$(cd "$(dirname "$0")/.." && pwd)"
DST="$HERE/persistbench_code"
SRC="$R/external/PersistBench/src/benchmark"
SNAP="$SRC/utils.py.before_strict_generation_patch"
rm -rf "$DST"; mkdir -p "$DST/src/benchmark"
( cd "$SRC" && find . -name '*.py' ! -name '*.bak*' | while read -r f; do mkdir -p "$DST/src/benchmark/$(dirname "$f")"; cp "$f" "$DST/src/benchmark/$f"; done )
# the thesis docs copy and the in-tree snapshot must be identical
cmp "$SNAP" "$R/thesis/docs/persistbench_patch_history/utils.py.before_strict_generation_patch"
cp "$SNAP" "$DST/src/benchmark/utils.py"
{
  echo "replication code provenance ($(date -Is))"
  echo "base: external/PersistBench @ $(git -C $R/external/PersistBench rev-parse HEAD) + local patches present before 2026-07-05"
  echo "utils.py := utils.py.before_strict_generation_patch  sha256=$(sha256sum "$DST/src/benchmark/utils.py" | cut -c1-64)"
  echo "live utils.py                                         sha256=$(sha256sum "$SRC/utils.py" | cut -c1-64)"
  echo; echo "--- every non-utils .py file is byte-identical to the live tree:"
  ( cd "$DST/src/benchmark" && for f in $(find . -name '*.py' ! -name utils.py); do cmp -s "$f" "$SRC/$f" && echo "same  $f" || echo "DIFF  $f"; done )
  echo; echo "--- diff replication utils.py -> live utils.py (should be ONLY the STRICT_GENERATION_CONTROL block):"
  diff "$DST/src/benchmark/utils.py" "$SRC/utils.py" || true
} > "$HERE/CODE_PROVENANCE.txt"
if grep -q "DIFF " "$HERE/CODE_PROVENANCE.txt"; then echo "ERROR: unexpected differences"; exit 1; fi
if grep -q "STRICT_GENERATION_CONTROL" "$DST/src/benchmark/utils.py"; then echo "ERROR: strict block present"; exit 1; fi
echo "ok -> $DST"; cat "$HERE/CODE_PROVENANCE.txt" | sed -n 1,12p
