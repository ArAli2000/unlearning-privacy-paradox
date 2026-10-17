# Pre-commit validation (post-fix pass, 2026-09-14)

Scope: resolve the MUST FIX items and cheap SHOULD FIX items from `FINAL_GRADING_REVIEW.md`, then revalidate. No broad refactor, no `mechanistic/` reorganization, no experiments/GPU jobs, nothing committed or pushed.

## 1. Fixes performed

| # | Fix | Files touched |
|---|---|---|
| 1 | Moved the 2 `.bak` files out of `thesis/scripts/muse_news/` into `research_history/03_checkpoint_selection_development/scripts/` (content inspected first: one is the pre-`best_agg` state of this exact launcher, the other tunes the save/eval-step grid to land on checkpoint-459) | 2 files moved (sha256-verified); `research_history/03_checkpoint_selection_development/README.md` updated |
| 2 | Fixed the placeholder upstream link in `thesis/README.md` §2, using `git remote -v` (confirmed `origin` = `https://github.com/locuslab/open-unlearning.git`, the true upstream, not a fork) | `thesis/README.md` |
| 3 | Inspected both nested external repos (`git remote -v`, commit, branch, status) and implemented the ignore-plus-provenance-manifest-plus-patch-plus-setup-script strategy | new: `thesis/manifests/external_dependencies/external_dependencies.tsv`, `thesis/patches/persistbench.patch`, `thesis/scripts/setup_external_dependencies.sh`; `.gitignore` updated; `thesis/README.md` §5/§17 updated |
| 4 | Replaced hardcoded absolute cluster paths in all 19 affected `thesis/scripts/*.sh` launchers with a shared `thesis/scripts/common.sh` helper (`REPO_ROOT` via `git rev-parse --show-toplevel`, `activate_unlearning_env` for conda) | new: `thesis/scripts/common.sh`; 19 launcher scripts edited; also `thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py` (a hardcoded `ROOT = Path("/storage/...")` found during the path audit, same class of issue, fixed the same way) |
| 5 | Resolved `configs/eval/tofu_partial_backup.yaml` (moved to `research_history/01_tofu_baselines/configs/`, provenance documented in that phase's README) and re-verified `configs/model/sedxTQNOq` (0 bytes, unreferenced, left in place, entry refreshed in `DELETE_CANDIDATES_FINAL.md`) | 1 file moved; `research_history/01_tofu_baselines/README.md` and `thesis_cleanup_audit/DELETE_CANDIDATES_FINAL.md` updated |
| 6 | Diffed the diverged `supervisor_update` copy of `run_persistbench_qwen25_7b_test.sh` against its `research_history` counterpart; found genuine unique content (a FlashInfer-sampler-compilation workaround, `--max-model-len` 4096→8192) and preserved it under a differentiating filename instead of treating it as redundant | 1 file moved; `research_history/05_wmdp_side_investigation/README.md` and `DELETE_CANDIDATES_FINAL.md` updated |
| 7 | Inlined the verified canonical PersistBench generation settings into `thesis/README.md` §9 (table: temperature, max_tokens, truncation, max_model_len, repetition_penalty, generation counts; plus seed/greedy-decoding note and the local-judge caveat), explicitly not claiming the uncertain Llama-2 values | `thesis/README.md` |
| 8 | `thesis_cleanup_audit/FINAL_GRADING_REVIEW.md` updated with a post-fix reassessment section and per-item resolution annotations | `thesis_cleanup_audit/FINAL_GRADING_REVIEW.md` |

## 2. Checks passed / failed

| Check | Result |
|---|---|
| A. `find thesis -name '*.bak*'` | Returns 5 files, **all** in `thesis/docs/persistbench_patch_history/` (the pre-existing, already-approved reference copies from the earlier migration — unrelated to the 2 files this pass removed). **The originally-flagged files are confirmed gone.** If you intended this check to mean "zero results, full stop," note that literal outcome and this distinction explicitly, since the check as worded doesn't by itself distinguish the two groups. |
| B. `bash -n` over all `thesis/scripts/**/*.sh`/`*.sbatch` | **PASS** — 0 failures across all files, including the 19 edited launchers and the new `setup_external_dependencies.sh` |
| C. `python3 -m py_compile` over all `thesis/**/*.py` | **PASS** — 0 failures, including the edited `create_persistbench_validity_summary_with_muse.py` |
| D. External dependency safety | **PASS** — `git add --dry-run external/` produces no output (previously: 2 "embedded repository" warnings); `external_dependencies.tsv` records exact URL+commit for both; `thesis/patches/persistbench.patch` reverse-applies cleanly against the current (patched) PersistBench working tree, confirming it exactly represents the pinned-commit→current diff; `privacy-collapse` confirmed to need no patch (clean `git status`) |
| E. Path audit | See §3 below — all repo-root/conda hardcoding removed from executable scripts; cache/HOME paths and the environment snapshot's own recorded prefix remain, out of this pass's scope, listed with justification |
| F. Secret audit | **PASS** — no API-key/password/bearer-token/private-key-shaped strings found in `thesis/` or `research_history/`; every `API_KEY`-like assignment found is the literal placeholder `"dummy"` |
| G. Git dry-run | **PASS** — no embedded-repository warnings anywhere; nothing under `.venv`, `model_cache/`, `*.safetensors`, or actual checkpoint binaries would be staged. Rows matching a naive `checkpoint-[0-9]` grep are all small `trainer_state.json` provenance manifests whose *filename* contains that substring (by design, to identify which checkpoint they document) — not checkpoint weights |

## 3. Path audit detail (task step 8E)

Every remaining `/storage/ukp/work/elshashay/open-unlearning` or `/mnt/beegfs/work/elshashay/open-unlearning` occurrence under `thesis/`, after the fix:

| Location | Context | Justified? |
|---|---|---|
| `thesis/README.md` (1 line) | Prose explaining what was fixed and what the old hardcoded values were | Yes — descriptive text, not executable |
| `thesis/scripts/common.sh` (2 lines) | Comment illustrating the problem this file solves | Yes — descriptive text, not executable |

No other occurrence of the **repo-root path** remains in any executable script. Separately, the following remain and are **explicitly out of this pass's scope** (the task named "hardcoded cluster repository paths" and the conda environment as the two things to fix; these are a different category — cache/toolkit/home locations, not the repo path):

- `HF_HOME=/storage/ukp/work/elshashay/.cache/huggingface`, `TRANSFORMERS_CACHE=/storage/ukp/work/elshashay/.cache/huggingface`, `CUDA_HOME=/nfs/cuda/cuda-12.2`, `HOME=/storage/ukp/work/elshashay` — present in most of the 19 launchers, unchanged.
- `thesis/manifests/environment/conda_unlearning.yml:246: prefix: /storage/ukp/work/elshashay/miniconda3/envs/unlearning` — this is a **factual historical record** (the conda-env export literally recorded where the environment was installed at the time), not a bug; changing it would falsify the provenance snapshot rather than fix anything.

Historical scripts under `research_history/` were **not** touched, per the task's explicit instruction — they still contain the original hardcoded paths, which is correct: they document the exact environment they actually ran in.

## 4. Remaining MUST FIX issues

**None.** All 3 items from `FINAL_GRADING_REVIEW.md` are resolved (see §1 above and the annotated original review).

## 5. Remaining SHOULD FIX issues

**None from the original list** — all 4 were resolved in this pass. One new, narrower item surfaced by this pass's own path audit:

- `HF_HOME`/`TRANSFORMERS_CACHE`/`CUDA_HOME`/`HOME` cache/toolkit paths in the 19 launchers are still hardcoded to the original cluster (§3 above). Lower priority than the items just fixed (these don't prevent understanding the pipeline the way the repo-root hardcoding did, since they're cache locations, not "where is the code" locations), but a future pass could extend `common.sh` with the same override-with-historical-default pattern used for `UNLEARNING_CONDA_ACTIVATE`.

## 6. Files still awaiting deletion approval

Unchanged in kind from `DELETE_CANDIDATES_FINAL.md`, updated in this pass to reflect the two items that turned out to have unique content (removed from the candidate list, preserved instead) and the two re-verifications (`sedxTQNOq`, the `supervisor_update` scripts bulk row). Full current list: `thesis_cleanup_audit/DELETE_CANDIDATES_FINAL.md`. Nothing has been deleted.

## 7. Safe to commit?

**Yes, with respect to the three specific risks the grading review identified** — the stray `.bak` files, the broken link, and the `external/` embedded-repository risk are all resolved and re-verified. Combined with the earlier `PRE_MIGRATION_STATE.txt`/`POST_MIGRATION_VALIDATION.md` checks (checkpoints unchanged, frozen JSONL artifacts byte-identical, no secrets, no oversized files), there is no remaining reason found in this review to hold off on committing `thesis/`, `research_history/`, `.gitignore`, `configs/eval/tofu.yaml`, or `src/trainer/base.py`.

Two things are unchanged from before and remain the user's decision, not a blocker:
- Whether to commit `mechanistic/` now (its own analysis/result files, ~31MB, not gitignored beyond `model_cache/`/`representations/` — see `FINAL_GRADING_REVIEW.md`'s addendum) or treat that as a separate, deliberate step.
- Whether/when to act on `DELETE_CANDIDATES_FINAL.md` (nothing there blocks committing the rest; it's `.gitignore`d so it can't be committed by accident either way).

See `thesis_cleanup_audit/COMMIT_PLAN.md` for the proposed commit sequence — it should be re-read in light of these fixes: commit 3 ("Reorganize final MUSE-News/MUSE-Books experiment launchers") now also includes `thesis/scripts/common.sh` and the 19 edited launchers, and "pre-commit decision A" (external/) in that plan is now resolved (ignore, don't add) rather than open.
