# Post-migration validation

All checks below were run after the migration completed. Every check that could be verified without GPU/model access was actually executed (commands and outputs summarized, not asserted).

## 1. No canonical checkpoint directories changed

```
$ ls -ld saves/finetune/muse_news_qwen25_7b_instruct_target
$ ls -ld saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459
$ ls -ld saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459
```
All three present, unmodified (nothing under `saves/` was moved, copied-into, or written to by this migration — only read from, to make small metadata copies elsewhere).

## 2. No canonical generated outputs changed, except the one approved README correction

- `external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_before.json` re-hashed post-migration: `5fb093dbec8e0b05662d767e74cee783230f721ab3c92276871ef2c528efbc57` — matches the value recorded in this file's own embedded metadata and in `thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md` from before this migration began. Unchanged.
- `mechanistic/outputs/muse_books_weekly_update_analysis/README.md` — **the one approved, explicit correction** (repetition_penalty prose claim: 1.08 → 1.05, with a cited justification and pointer to the sidecar).
- **Two source files, not "generated outputs," were also edited** per the explicit task instruction: `mechanistic/privacy_collapse/persistbench_native/prepare_native_200.py` and `prepare_native_sycophancy_200.py` — a hardcoded `generation_settings` literal (`repetition_penalty`, `top_p`, `vllm_seed`) corrected, with an inline comment explaining why. These are Python source files that construct metadata when repackaging already-existing generations; they are not themselves generated output, and no generated output they previously produced was altered by this edit (nothing was rerun).

## 3. Frozen JSONL generation artifacts are byte-identical (pre/post hash comparison)

All 9 files recorded in `thesis/manifests/provenance/persistbench_generation_corrections.json` were re-hashed after every other migration step (including the two `.py` source edits above) and compared against the hashes recorded before those edits:

```
mechanistic/privacy_collapse/persistbench_native/generations/base_generation0.jsonl                                                    OK
mechanistic/privacy_collapse/persistbench_native/generations/satimp_generation0.jsonl                                                  OK
mechanistic/privacy_collapse/persistbench_native/generations/simnpo_generation0.jsonl                                                   OK
mechanistic/privacy_collapse/persistbench_native/generations/sycophancy_base_generation0.jsonl                                          OK
mechanistic/privacy_collapse/persistbench_native/generations/sycophancy_satimp_generation0.jsonl                                        OK
mechanistic/privacy_collapse/persistbench_native/generations/sycophancy_simnpo_generation0.jsonl                                        OK
mechanistic/outputs/muse_books_weekly_update_analysis/native_sycophancy/generations/sycophancy_base_generation0.jsonl                   OK
mechanistic/outputs/muse_books_weekly_update_analysis/native_sycophancy/generations/sycophancy_satimp_generation0.jsonl                 OK
mechanistic/outputs/muse_books_weekly_update_analysis/native_sycophancy/generations/sycophancy_simnpo_generation0.jsonl                 OK
```
All 9: byte-identical, confirmed twice (immediately after the `.py` edits, and again in this final validation pass).

## 4. Active Python files compile

`python3 -m py_compile` run over every `.py` file under `thesis/` and `research_history/` (all moved + newly-authored files): **all pass**, zero failures. (`__pycache__` byproducts removed afterward.)

## 5. Active shell scripts pass `bash -n`

`bash -n` run over every `.sh`/`.sbatch` file under `thesis/` and `research_history/`: **all pass**, zero failures — including the 33 scripts that had their internal `tmp_paths/...` literal references patched to new locations.

## 6. Active paths resolve

- `templates/simple_llama_chat_template.jinja` (referenced by every moved PersistBench launcher) — confirmed present, unmoved.
- All 20 relocated `tmp_paths/*` model-list files spot-checked at their new locations (`thesis/manifests/model_lists/`, `research_history/{02,04,05}_*/manifests/`) — all present; the 33 scripts referencing them were patched to the new path and pass `bash -n`.
- `thesis/scripts/privacylens/eval_privacylens_mcq_forced_choice.py`'s import of its sibling `eval_privacylens_mcq_local.py` — both files confirmed co-located after the move; import statement updated from a repo-root package import (`from scripts.eval_privacylens_mcq_local import ...`, which would have broken since both files moved out of the root-level `scripts/` package) to a same-directory import; `py_compile` passes.

## 7. Thesis history files exist

`thesis/docs/experiment_history.md`, `experiment_history.csv`, `trainer_patch.md`, `persistbench_patch.md`, `generation_provenance.md` — all present (promoted/authored during this migration).

## 8. All five `research_history/` phases exist

`01_tofu_baselines/`, `02_model_method_scaling/`, `03_checkpoint_selection_development/`, `04_muse_track_a/`, `05_wmdp_side_investigation/` — each with its own `README.md` (all 5 confirmed present) plus its `scripts/`/`manifests/`/`docs/`/`configs/` content as applicable.

## 9. Selected-model manifests still point to valid checkpoint paths

Every row of all three `thesis/manifests/selection/*_SELECTED_MODEL_PATHS.tsv` files was checked with `os.path.exists()` (HF-hub IDs like `muse-bench/MUSE-Books_target` excluded, correctly, from the filesystem check): **every local checkpoint path referenced resolves to an existing directory on disk.** No stale references introduced by this migration.

## 10. README references resolve

`thesis/README.md` cites: `docs/trainer_patch.md` ✓, `docs/persistbench_patch.md` ✓, `docs/generation_provenance.md` ✓, `thesis/manifests/selection/` (3 files) ✓, `thesis/manifests/provenance/persistbench_generation_corrections.json` ✓, `thesis/manifests/environment/` (4 files) ✓, `research_history/README.md` ✓, `thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md` ✓ (pre-existing, unchanged), `.gitignore`'s new rules ✓ (verified via `git check-ignore`, see below). All resolve.

## `.gitignore` before/after (`git check-ignore` verification)

| Path | Before | After |
|---|---|---|
| `research_history/02_model_method_scaling/manifests/hydra_configs/saves__finetune__...` | would have been ignored by unanchored `saves*/` if not for the anchor fix | tracked (not ignored) — **correct** |
| `thesis/manifests/environment/` | n/a (didn't exist at old unanchored-`env/`-affected path) | tracked (not ignored) |
| `mechanistic/**/model_cache/` | not ignored (a gap) | ignored — new rule |
| `mechanistic/**/representations/` | not ignored (a gap) | ignored — new rule |
| `supervisor_update/` (remaining redundant content) | not ignored | ignored — new rule, files not deleted |
| `tofu_qwen15_npo_f10_fixed.tar.gz`, `supervisor_update/*.tar.gz` | not ignored (accidental-commit risk) | ignored — new rule |
| `research_history/03_checkpoint_selection_development/trainer_snapshots/*.bak_*` | n/a | tracked (not ignored) — explicit exception to the new general `*.bak*` rule |
| `thesis/docs/persistbench_patch_history/*.bak_*` | n/a | tracked (not ignored) — explicit exception |
| `research_history/02_model_method_scaling/scripts/run_privacylens_full_before_after.sh.bak_raw_base` (a true delete candidate) | not ignored | ignored — caught by the new general `*.bak*` rule (no exception applies) |

## Not independently re-verified in this pass (disclosed, not hidden)

- The exact `vLLM`/Python package versions pinned in `external/PersistBench/uv.lock` were not cross-checked against `thesis/manifests/environment/pip_freeze_current_env.txt` line-by-line.
- `mechanistic/`'s own internal correctness (its `Path(__file__).resolve().parents[N]` dependencies) was **not** exercised by re-running anything in `mechanistic/` — consistent with this migration's decision not to move or edit that subtree's structure, and with the task's prohibition on rerunning experiments.
