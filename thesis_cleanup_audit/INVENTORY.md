# Thesis cleanup inventory

This audit is read-only with respect to the existing repository; nothing outside `thesis_cleanup_audit/` was created, moved, or modified. The inventory below is scoped to the thesis author's own additions/modifications: `mechanistic/`, `external/PersistBench/` and `external/privacy-collapse/` (vendored tool trees, excluding their internal `.venv`/`.git`), `supervisor_update/`, `meeting_updates/`, `tmp_paths/`, root-level `run_*.sh`/`*.sbatch`/`make_*.py` launchers, `scripts/eval_privacylens*`, the modified/added `configs/` and `src/trainer/base.py` files, and the two `.tar.gz` bundles. It deliberately **excludes** the rest of the upstream open-unlearning tree (which should not be reorganized) and excludes the multi-terabyte `saves/`, `logs/`, `outputs/`, `data/` directories that are already covered by the repository's existing `.gitignore` (`saves*/`, `logs/`, `output*/`, `data/`) — those are addressed qualitatively in `PROPOSED_STRUCTURE.md` rather than enumerated file-by-file.

**Correction vs. an earlier pass of this audit**: a prior inventory run (still visible in git history of this script, if kept) accidentally walked `external/PersistBench/.venv/` (a ~1.1&nbsp;GB installed Python virtualenv with ~28,000 files) and counted it as "PersistBench" thesis content, which inflated "source code" to 15,251 files and manufactured a fake "950-file duplicate group" out of trivially-identical empty `__init__.py`/`py.typed` stub files. That data has been discarded; this version excludes `.venv`, `.git`, `__pycache__`, and `*.egg-info` from every walk. `tracked_upstream=yes` means Git currently tracks the path; it does not mean the content is scientifically upstream (e.g. `configs/eval/tofu.yaml` and `src/trainer/base.py` are tracked upstream files the thesis modified in place).

## Summary

- Actual thesis source/reusable Python files: **75**
- Experiment and SLURM launchers: **98** (72 shell launchers; 26 SLURM scripts)
- Generated results/plots/logs: **874**
- Backups: **60**
- Checkpoint/model/cache files (metadata only; large binaries not read): **24**
- Temporary/debug files: **33**
- Likely obsolete experiment files: **14**
- Vendored external/upstream files (kept in place, not thesis code): **162**
- Exact duplicate groups (non-empty files <=5&nbsp;MB, excluding logs/checkpoints/vendored code): **45**
- Total files inventoried: **1,638**

## Classification counts

- source code: 54
- experiment launcher: 72
- SLURM script: 26
- configuration: 170
- reusable utility: 21
- frozen manifest: 128
- generated result: 685
- plot: 174
- log: 15
- temporary/debug: 33
- obsolete experiment: 14
- backup: 60
- duplicate/near-duplicate: 0
- external/upstream code: 162
- checkpoint/model data: 24

## Proposed-action counts

- GENERATED OUTPUT / DO NOT COMMIT: 898
- IMPORT/PATH UPDATE REQUIRED: 305
- KEEP IN PLACE: 200
- SAFE MOVE: 128
- ARCHIVE: 60
- DELETE CANDIDATE (but DO NOT delete): 47

## Domain counts

- broader thesis/legacy: 445
- PrivacyLens/representations: 309
- PersistBench: 251
- supervisor bundle/documentation: 143
- TOFU (legacy/broader, out of final scope): 112
- WMDP side-investigation (out of final scope): 96
- external dependency (privacy-collapse): 74
- MUSE-Books: 70
- controlled MCQ/A-B probe: 67
- native hidden states/sycophancy: 51
- MUSE-News: 11
- comparison/reconciliation: 9

## Archive bundle contents (listed only, not extracted)

- `supervisor_update/code_settings_bundle.tar.gz` (285,390 bytes): 147 members
- `supervisor_update/code_settings_bundle_full.tar.gz` (509,045 bytes): 337 members
- `tofu_qwen15_npo_f10_fixed.tar.gz` (2,251,292,672 bytes): could not list

## Interpretation

Counts are audit classifications, not deletion instructions. Generated artifacts that are small and thesis-critical may be selectively published, but raw benchmark JSONs, tensors, logs, and checkpoints should remain outside the source commit. See `inventory.csv` for every path and proposed action, `DUPLICATION_REPORT.md` for duplicate groups, and `MIGRATION_PLAN.md` for the per-file CURRENT -> PROPOSED mapping.
