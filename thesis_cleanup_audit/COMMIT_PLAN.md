# Commit plan (proposed — nothing staged or committed)

Based on the actual `git status --short` / `git diff --stat` / `git diff` inspected in `FINAL_GRADING_REVIEW.md` §5, and the `git add --dry-run` checks run in this review. Two items are called out as **pre-commit decisions** rather than folded into the sequence, because committing them without a decision first risks a broken or premature result (see `FINAL_GRADING_REVIEW.md` MUST FIX #1 and #3).

## Pre-commit decisions (resolve before commit 1, not part of the sequence)

**A. `external/` — do not `git add -A` over it.** `external/PersistBench/` and `external/privacy-collapse/` are nested git repositories; a plain add creates dangling "embedded repository" gitlinks that silently produce an empty directory for anyone who clones this repo afterward (`git add --dry-run external/` prints this exact warning). Resolve one of:
   - Register both as proper `git submodule add <url> external/<name>` entries (pins an exact commit, clones correctly elsewhere), or
   - Deliberately exclude `external/` from version control (add it to `.gitignore`) and rely on `thesis/docs/persistbench_patch.md` + install instructions to re-clone/patch it.
   Until this is decided, do not stage anything under `external/`.

**B. The 2 stray `.bak` files in `thesis/scripts/muse_news/`.** They are currently silently skipped by `.gitignore` if you `git add thesis/`, which means committing `thesis/` as-is will quietly omit them — not wrong, but worth a conscious choice: either relocate them to `research_history/03_checkpoint_selection_development/` first (recommended, matches their sibling `.bak` files there) or add an explicit `.gitignore` exception if they should stay in `thesis/`.

## Proposed sequence

### Commit 1 — Trainer and eval-config methodology changes (the actual experimental code change, not a reorg)
**Files**: `src/trainer/base.py`, `configs/eval/tofu.yaml`
**Why its own commit**: these are the only two upstream-tracked files with real content changes (the `best_agg`/`Agg_proxy` checkpoint-selection patch and its required TOFU eval-metric additions) — genuinely different in kind from every other commit here, which is pure reorganization/documentation/config-tracking. Keeping it separate makes `git log` and `git blame` tell the true story: this commit is "what changed in the method," everything after is "how the repo is organized to explain and reproduce it."
**Suggested message**:
```
Add best_agg/Agg_proxy checkpoint-selection metrics to FinetuneTrainer

Adds a harmonic-mean checkpoint-selection metric (best_agg) for MUSE
runs and its TOFU-era precursor (Agg_proxy/Selection_proxy), plus the
TOFU eval-metric config entries Agg_proxy needs (exact_memorization,
MIA scores, forget_Q_A_gibberish). See thesis/docs/trainer_patch.md
for the full methodology writeup and thesis_cleanup_audit/
CHECKPOINT_SELECTION_PATCH.md for the evidence trail.
```

### Commit 2 — Preserve thesis research history
**Files**: `research_history/` (all 5 phases + top-level `README.md`)
**Why its own commit**: self-contained, doesn't depend on or get depended on by the `thesis/` reorganization; keeping it separate lets a reviewer see "here is the preserved evolution" as one coherent diff.
**Suggested message**:
```
Preserve thesis research history (TOFU baselines through MUSE-News
Track A and the WMDP side investigation)

Organizes earlier, no-longer-active research phases into
research_history/{01_tofu_baselines,02_model_method_scaling,
03_checkpoint_selection_development,04_muse_track_a,
05_wmdp_side_investigation}/, each with a README explaining what was
investigated, what was learned, and how it shaped the final thesis
design. Nothing here is discarded; every phase documents a real,
completed piece of work.
```

### Commit 3 — Reorganize final MUSE-News/MUSE-Books experiment launchers
**Files**: `thesis/scripts/`, `templates/` (the chat template these scripts reference)
**Precondition**: pre-commit decision B resolved for the 2 `.bak` files.
**Why its own commit**: this is the "active code" reorganization proper — separating it from the manifests/docs commits below keeps this diff reviewable as "which scripts moved where."
**Suggested message**:
```
Reorganize final MUSE-News/MUSE-Books experiment launchers into thesis/

Moves the ~23 root-level launcher scripts that produced the canonical
MUSE-News (locally-finetuned Qwen2.5-7B-Instruct target) and both
MUSE-Books results into thesis/scripts/{muse_news,muse_books,
persistbench,privacylens,validation}/. One import fixed
(eval_privacylens_mcq_forced_choice.py's sibling import, since it
moved together with eval_privacylens_mcq_local.py); 33 scripts had an
internal tmp_paths/... path reference updated to its new location.
See thesis_cleanup_audit/MIGRATION_PLAN.md for the full mapping and
thesis_cleanup_audit/POST_MIGRATION_VALIDATION.md for the
py_compile/bash -n verification.
```

### Commit 4 — Add reproducibility manifests
**Files**: `thesis/manifests/selection/`, `thesis/manifests/trainer_states/`, `thesis/manifests/model_lists/`, `thesis/manifests/environment/`
**Why its own commit**: these are data, not code — separating them from commit 3 means a reviewer checking "did any script change" doesn't have to wade through manifest diffs, and vice versa.
**Suggested message**:
```
Add reproducibility manifests (checkpoint selection, trainer states,
model lists, environment snapshot)

Small, frozen records only -- no checkpoints or large tensors. Every
checkpoint path in the selection manifests was verified to exist on
disk (thesis_cleanup_audit/POST_MIGRATION_VALIDATION.md #9).
```

### Commit 5 — Add thesis documentation
**Files**: `thesis/README.md`, `thesis/docs/`
**Suggested message**:
```
Add thesis README and methodology documentation

thesis/README.md is the grader-facing entry point. thesis/docs/
contains the promoted experiment-history timeline, the trainer/
PersistBench patch writeups, and the generation-provenance record.
```

### Commit 6 — Correct PersistBench generation-provenance metadata and documentation
**Files**: `mechanistic/outputs/muse_books_weekly_update_analysis/README.md`, `mechanistic/privacy_collapse/persistbench_native/prepare_native_200.py`, `mechanistic/privacy_collapse/persistbench_native/prepare_native_sycophancy_200.py`, `thesis/manifests/provenance/persistbench_generation_corrections.json`
**Why its own commit**: this is a correction to existing (mostly-untracked-until-now) content, distinct in kind from the additions above — isolating it makes the fix independently reviewable and revertible.
**Suggested message**:
```
Correct PersistBench generation-provenance metadata (repetition_penalty
1.08 -> 1.05)

The vLLM server logs from the actual MUSE-News/MUSE-Books generation
jobs confirm repetition_penalty=1.05 was in effect (the Qwen
checkpoints' own generation_config.json default), not 1.08 as two
repackaging scripts and one README incorrectly stated. The 1.08 figure
is real and correct for the later, unrelated WMDP-cyber work
(research_history/05_wmdp_side_investigation/) -- it was mistakenly
backfilled onto the earlier MUSE description. The 9 frozen generation
JSONL files that inherited the wrong metadata are NOT modified; a
sidecar correction record is added instead (thesis/manifests/
provenance/persistbench_generation_corrections.json). See
thesis_cleanup_audit/GENERATION_PROVENANCE.md for the full evidence
trail.
```

### Commit 7 — Fix `.gitignore` rules
**Files**: `.gitignore`
**Why last, and separate**: the `.gitignore` changes reference paths created by commits 2-6 (e.g. the `research_history/03.../trainer_snapshots/` exception), so putting it last means every path it mentions already exists in the history, and a reviewer can `git show` this commit alone to see exactly what tracking behavior changed and why.
**Suggested message**:
```
Fix .gitignore: anchor saves*//env/ rules, add rules for thesis
cleanup artifacts

Anchors two previously-unanchored rules (saves*/, env/) that were
silently hiding real, trackable content (a 108-file Hydra config
snapshot, a 4-file environment snapshot) at any depth, not just repo
root. Adds new rules for mechanistic/**/model_cache/,
mechanistic/**/representations/, the now-fully-redundant
supervisor_update/ snapshot bundle, and root-level .tar.gz archives
(one of which is confirmed corrupted). Adds a general *.bak*/
*.before_* rule with explicit exceptions for the two locations this
thesis deliberately keeps such snapshots tracked.
```

### Not included in this sequence (separate decisions, see `FINAL_GRADING_REVIEW.md` / `DELETE_CANDIDATES_FINAL.md`)

- `external/` — blocked on pre-commit decision A above.
- `mechanistic/` (the ~65 source `.py` files plus ~74 small result/analysis files a dry run shows would be staged) — not included here because it wasn't part of this migration's scope to decide; recommend a deliberate, separate commit once you've confirmed the ~31MB of result/analysis files inside it (see `FINAL_GRADING_REVIEW.md` addendum) is what you want tracked.
- `configs/eval/tofu_partial_backup.yaml`, `configs/model/sedxTQNOq` — undecided (SHOULD FIX item), hold until resolved.
- `tmp_paths/` — recommend holding off until the delete-candidate review in `thesis_cleanup_audit/DELETE_CANDIDATES_FINAL.md` is acted on, so as not to commit content you may delete next.
- `thesis_cleanup_audit/` itself — recommend a final commit of its own once everything else above is settled, since several of its documents (this one included) describe the commits that would by then already exist; committing it last keeps its own claims accurate at commit time.
