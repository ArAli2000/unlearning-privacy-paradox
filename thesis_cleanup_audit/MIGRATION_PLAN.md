# Migration plan (revised)

Read-only proposal. **Nothing in this plan has been executed** — no files were moved, renamed, deleted, or edited outside `thesis_cleanup_audit/`.

**Revision note**: earlier TOFU, model-scaling, checkpoint-selection-development, MUSE Track-A, and WMDP work were previously routed to a generic `archive/` tree with labels like `obsolete_scripts`. Per explicit instruction, these are genuine research phases, not obsolete clutter, and are now routed to **`research_history/<phase>/`** (matching `PROPOSED_STRUCTURE.md` and `thesis_cleanup_audit/EXPERIMENT_HISTORY.md`). The term "obsolete" is no longer used anywhere in this plan. **DELETE CANDIDATE** is reserved strictly for content confirmed to carry no unique research information (byte-identical duplicates, corrupted archives, confirmed-orphaned files) — never for a real experimental phase.

Action vocabulary (unchanged):

- **SAFE MOVE** — relocating the file does not require editing its contents or any other file.
- **IMPORT/PATH UPDATE REQUIRED** — the file (or something that reads it) contains a path/import that must be updated in lockstep with the move.
- **KEEP IN PLACE** — do not move (tracked-upstream file modified in place, or vendored external tool).
- **ARCHIVE → research_history/** — move to the named phase folder; genuine historical research, not part of the active pipeline.
- **GENERATED OUTPUT / DO NOT COMMIT** — derived artifact; belongs in `outputs/`, gitignored.
- **DELETE CANDIDATE (but DO NOT delete)** — confirmed to carry no unique research information; author must confirm, this audit does not delete anything.

The full per-file machine-readable mapping is in `inventory.csv`.

## 1. Root-level launchers in the final thesis chain → `thesis/` (unchanged from the first version)

Same as before — see the earlier revision's §1a for the complete table (all `run_muse_news_qwen25_*`, `run_muse_books_*`, `run_persistbench_muse_*`, `run_privacylens_muse_*`, `scripts/eval_privacylens_mcq_*.py`, the three `make_*`/`select_*` table scripts, `run_local_judge_server_penelope.sh`). Nothing here changes in this revision.

## 2. Research-history phases (revised — replaces the old §1b "out of final thesis scope" table)

These ~50 root scripts and their associated small manifests are **not** part of the final MUSE-News/MUSE-Books pipeline, but they are real, completed research phases, routed to `research_history/`, not to a generic archive.

### 2a. `research_history/01_tofu_baselines/`

| CURRENT PATH | PROPOSED PATH | Action |
|---|---|---|
| run_qwen15_methods_a180.sh | research_history/01_tofu_baselines/scripts/run_qwen15_methods_a180.sh | ARCHIVE → research_history |
| run_llama1b_paper_methods_a180.sh | research_history/01_tofu_baselines/scripts/run_llama1b_paper_methods_a180.sh | ARCHIVE → research_history |
| run_llama1b_other_methods_fullmetrics_a180.sh | research_history/01_tofu_baselines/scripts/run_llama1b_other_methods_fullmetrics_a180.sh | ARCHIVE → research_history |
| run_qwen3b_selected_methods_a100.sh | research_history/01_tofu_baselines/scripts/run_qwen3b_selected_methods_a100.sh | ARCHIVE → research_history |
| run_qwen3b_all_methods_fullmetrics_a180.sh | research_history/01_tofu_baselines/scripts/run_qwen3b_all_methods_fullmetrics_a180.sh | ARCHIVE → research_history |
| supervisor_update/code_settings/trainer_states/saves__unlearn__paper_llama32_1b_*_f10_a180[_fullmetrics]__trainer_state.json (20 files) | research_history/01_tofu_baselines/manifests/ | SAFE MOVE — small, frozen provenance of this phase's actual training runs |

### 2b. `research_history/02_model_method_scaling/`

| CURRENT PATH | PROPOSED PATH | Action |
|---|---|---|
| run_7bscale_top3_fullmetrics_a180.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| run_llama32_3b_qwen7b_top3_fullmetrics_a180.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| run_privacylens_full_before_after.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history — first appearance of PrivacyLens in the thesis |
| run_qwen_tofu_full_finetune_array.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| run_qwen_tofufull_unlearn_best_array.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| run_llama31_8b_tofufull_unlearn_4methods_clean.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history — step 1 of the documented Selection_proxy→Agg_proxy iteration |
| run_llama31_8b_tofufull_unlearn_best_array.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history — step 2 of the same iteration |
| run_llama31_8b_tofufull_unlearn_remaining3_aggproxy.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history — step 3 (the metric switch itself) |
| run_qwen25_14b_tofufull_finetune.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| run_qwen25_14b_tofufull_unlearn_4methods_aggproxy.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| run_qwen25_14b_tofufull_unlearn_remaining_wga_satimp_h200.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| run_privacylens_llama32_3b_tofufull_methods.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| run_privacylens_llama31_8b_tofufull_methods.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| run_privacylens_qwen_tofufull_methods.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| run_privacylens_qwen25_14b_tofufull_methods.sh | research_history/02_model_method_scaling/scripts/... | ARCHIVE → research_history |
| configs/model/Qwen2.5-14B-Instruct.yaml | research_history/02_model_method_scaling/configs/Qwen2.5-14B-Instruct.yaml | ARCHIVE → research_history (IMPORT/PATH UPDATE REQUIRED if any script still actively references it — verify before moving) |
| supervisor_update/code_settings/trainer_states/saves__unlearn__{bestagg,test_bestagg}_*.json and proper_*_from_tofufull_*.json (~82 files) | research_history/02_model_method_scaling/manifests/ | SAFE MOVE |
| supervisor_update/code_settings/model_lists/*.tsv,*.txt (5 files) | research_history/02_model_method_scaling/manifests/ | SAFE MOVE |
| supervisor_update/code_settings/hydra_configs/ (108 files, run names observed match this phase's `bestagg_*`/`proper_*` runs) | research_history/02_model_method_scaling/manifests/hydra_configs/ | SAFE MOVE — currently silently gitignored by the unanchored `saves*/` rule; verify no run name here actually belongs to a different phase before the final move |
| supervisor_update/code_settings/results/*.json (40 files, PrivacyLens results for this phase's models) | research_history/02_model_method_scaling/privacylens_results_snapshot/ | SAFE MOVE — **reclassified from the first version's "ARCHIVE, not canonical location" note**: since the canonical `outputs/` location is gitignored and not committed, this snapshot is the *only* surviving committed copy of this phase's PrivacyLens results; kept, not discarded (see §3) |

### 2c. `research_history/03_checkpoint_selection_development/`

| CURRENT PATH | PROPOSED PATH | Action |
|---|---|---|
| run_test_qwen7b_simnpo_save_bestagg.sh | research_history/03_checkpoint_selection_development/scripts/run_test_qwen7b_simnpo_save_bestagg.sh | ARCHIVE → research_history — first smoke test of metric-driven checkpoint selection |
| run_4models_4methods_save_bestagg.sh | research_history/03_checkpoint_selection_development/scripts/run_4models_4methods_save_bestagg.sh | ARCHIVE → research_history — first systematic application at scale |
| run_4models_4methods_save_bestagg.sh.bak_before_tofufull_llama32_3b | research_history/03_checkpoint_selection_development/scripts/run_4models_4methods_save_bestagg.sh.bak_before_tofufull_llama32_3b | ARCHIVE → research_history — prior iteration of the same script |
| src/trainer/base.py.bak_before_agg_proxy | research_history/03_checkpoint_selection_development/trainer_snapshots/base.py.bak_before_agg_proxy | SAFE MOVE — small text file, not a checkpoint; the only surviving pre-`Agg_proxy` snapshot |
| src/trainer/base.py.bak_before_bestagg_patch | research_history/03_checkpoint_selection_development/trainer_snapshots/base.py.bak_before_bestagg_patch | SAFE MOVE — the only surviving pre-`best_agg` snapshot |

**Note**: the live `src/trainer/base.py` itself is **not** moved — it stays `KEEP IN PLACE` (§4 of the original plan, unchanged), since it is a tracked-upstream file load-bearing for the final thesis pipeline. Only its historical pre-patch snapshots move here.

### 2d. `research_history/04_muse_track_a/`

| CURRENT PATH | PROPOSED PATH | Action |
|---|---|---|
| run_muse_news_remaining_methods.sbatch | research_history/04_muse_track_a/scripts/run_muse_news_remaining_methods.sbatch | ARCHIVE → research_history |
| run_muse_news_simnpo.sbatch | research_history/04_muse_track_a/scripts/run_muse_news_simnpo.sbatch | ARCHIVE → research_history |
| run_persistbench_muse_news_judge.sh | research_history/04_muse_track_a/scripts/run_persistbench_muse_news_judge.sh | ARCHIVE → research_history — earlier draft of the judge script within this same track, kept as a documented iteration step (**reclassified from the first version's `superseded_iterations` label — this is Track-A history, not junk**) |
| run_persistbench_muse_news_judge_like_tofu.sh | research_history/04_muse_track_a/scripts/run_persistbench_muse_news_judge_like_tofu.sh | ARCHIVE → research_history |
| run_persistbench_muse_news_selected.sh | research_history/04_muse_track_a/scripts/run_persistbench_muse_news_selected.sh | ARCHIVE → research_history |
| run_privacylens_muse_news_selected.sh | research_history/04_muse_track_a/scripts/run_privacylens_muse_news_selected.sh | ARCHIVE → research_history |
| select_muse_news_best_checkpoints.py | research_history/04_muse_track_a/scripts/select_muse_news_best_checkpoints.py | ARCHIVE → research_history |
| make_muse_news_selected_table.py | research_history/04_muse_track_a/scripts/make_muse_news_selected_table.py | ARCHIVE → research_history |
| make_final_muse_news_combined_table.py | research_history/04_muse_track_a/scripts/make_final_muse_news_combined_table.py | ARCHIVE → research_history — produced the one complete, real Track-A result |
| saves/final_muse_news_openunlearning_selection/{SELECTED_MODEL_PATHS.tsv, FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv, MUSE_News_all_methods_checkpoint_selection.csv, MUSE_News_selected_methods_summary.csv} | research_history/04_muse_track_a/manifests/ | SAFE MOVE — small csv/tsv files only; the checkpoints themselves stay in `saves/` (gitignored, not copied) |
| saves/final_muse_news_simnpo_openunlearning_selection/*.{csv,json} | research_history/04_muse_track_a/manifests/simnpo_precursor/ | SAFE MOVE — the single-method precursor selection, one day before the full 4-method one |

**Note**: per `MUSE_NEWS_TRACK_RESOLUTION.md`, Track A is confirmed superseded/not-cited, so none of this is `thesis/` — but it is a complete, real result, hence `research_history/`, not `DELETE CANDIDATE`.

### 2e. `research_history/05_wmdp_side_investigation/`

| CURRENT PATH | PROPOSED PATH | Action |
|---|---|---|
| run_wmdp_bio_test_qwen_books_before.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_wmdp_cyber_before_eval.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_wmdp_cyber_qwen25_7b_rmu_test.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — **reclassified from DELETE CANDIDATE**: documents a real debugging step in the smoke→real chain |
| run_wmdp_cyber_all4_smoke_array.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — **reclassified from DELETE CANDIDATE**: step 1 of the smoke→fixed→sweep→real chain |
| run_wmdp_cyber_nonrmu_smoke_fixed_array.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — **reclassified from DELETE CANDIDATE**: step 2 of the same chain |
| run_wmdp_cyber_all4_sweep300_array.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — step 3 |
| run_wmdp_cyber_rmu_real_array.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — step 4, the "real" run |
| run_wmdp_mmlu_qwen_missing.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_wmdp_mmlu_qwen_small.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_wmdp_mmlu_qwen_wga_sweep.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_persistbench_qwen25_7b_full_generate.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_persistbench_qwen25_7b_test.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — **reclassified from DELETE CANDIDATE**: a real (if smoke-test-shaped) debugging step; note it DIVERGED from its `supervisor_update` copy — the `supervisor_update` copy is the one that becomes a delete candidate (§3), not this live one |
| run_persistbench_qwen_wga_ckpt160_judge.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_persistbench_qwen_wga_ckpt_sweep_generate.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_persistbench_wmdp_cyber_all4_generate.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_persistbench_wmdp_cyber_all4_generate_rerun_1_9.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_persistbench_wmdp_cyber_all4_judge.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_persistbench_wmdp_cyber_qwen_strict_generate.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — **the actual origin of `PB_REPETITION_PENALTY=1.08`** (`export PB_REPETITION_PENALTY=1.08` at line 18), see `GENERATION_PROVENANCE.md` |
| run_persistbench_wmdp_cyber_qwen_strict_generate_limit50.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — same `PB_REPETITION_PENALTY=1.08` origin |
| run_persistbench_wmdp_cyber_qwen_strict_limit50_judge.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_persistbench_wmdp_cyber_test0.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — **reclassified from DELETE CANDIDATE** |
| run_persistbench_wmdp_cyber_test0_anygpu.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — **reclassified from DELETE CANDIDATE** |
| run_persistbench_full_generate_from_list.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history — generic helper used by this phase's sweeps |
| run_persistbench_judge_array.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| run_privacylens_wmdp_cyber_all4_selected.sh | research_history/05_wmdp_side_investigation/scripts/... | ARCHIVE → research_history |
| meeting_updates/wmdp_followup_2026_08_12/* (3 files) | research_history/05_wmdp_side_investigation/docs/ | SAFE MOVE — this is the document that records *why* the thesis moved on to interpretability work |
| meeting_updates_wmdp_safety_summary.csv (root) | research_history/05_wmdp_side_investigation/docs/meeting_updates_wmdp_safety_summary.csv | SAFE MOVE |

## 3. Genuine delete candidates (revised — much shorter list; reserved strictly for zero-unique-information content)

| CURRENT PATH | Why this one, and not the phase it's near | Action |
|---|---|---|
| run_privacylens_full_before_after.sh.bak_raw_base | Byte-identical to the live `run_privacylens_full_before_after.sh` (which itself moves to `research_history/02_model_method_scaling/`) — literally zero additional information | DELETE CANDIDATE (but DO NOT delete) |
| configs/model/sedxTQNOq | Confirmed 0-byte, garbled/accidental filename, referenced nowhere | DELETE CANDIDATE (but DO NOT delete) |
| tofu_qwen15_npo_f10_fixed.tar.gz | Confirmed **corrupted** (`tar -tzf` fails partway) independent of scope; not a usable artifact even as a historical record | DELETE CANDIDATE (but DO NOT delete) |
| supervisor_update/code_settings/scripts/* (17 files) | 16 of 17 are byte-identical copies of scripts that, after this migration, live in `thesis/` or `research_history/`; the 1 diverged copy (`run_persistbench_qwen25_7b_test.sh`) needs author review of the divergence before its delete status is finalized, but the file itself is a redundant snapshot either way | DELETE CANDIDATE (but DO NOT delete) — review the one divergence first |
| supervisor_update/code_settings/configs/* (13 files) | All byte-identical to live/upstream configs that stay in place | DELETE CANDIDATE (but DO NOT delete) |
| supervisor_update/code_settings_bundle.tar.gz | Confirmed a strict subset of `code_settings_bundle_full.tar.gz`, itself redundant with the unpacked directory | DELETE CANDIDATE (but DO NOT delete) |
| supervisor_update/code_settings_bundle_full.tar.gz | Redundant archive of a directory that, after this migration, is distributed across `research_history/` and `thesis/` in useful pieces already | DELETE CANDIDATE (but DO NOT delete) |
| tmp_paths/llama31_8b_persistbench_models.tsv, muse_news_qwen25_privacylens_models.tsv, muse_news_qwen25_selected_models.tsv, persistbench_validity_all_datasets.py, qwen25_14b_finetune_cfg_preview.yaml (5 files) | Confirmed unreferenced by any script anywhere; not tied to any documented phase or decision | DELETE CANDIDATE (but DO NOT delete) |
| tmp_paths/*.py (9 debug/analysis scripts) | None referenced by any launcher; author should confirm none contain unique analysis not reproduced elsewhere before discarding | DELETE CANDIDATE (but DO NOT delete) |

**Everything previously listed under `archive/backups/` for genuine parameter-iteration `.bak` files (e.g. `run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh.bak_before_bestagg`, `.bak_same_ckpt_diff`, `configs/eval/tofu_partial_backup.yaml`) is unchanged in kind but retargeted to the relevant `research_history/` phase folder or `thesis/docs/` rather than a generic `archive/backups/`** — these are small parameter/config snapshots, not junk; see the per-file rows in `inventory.csv` for exact destinations, unchanged from the first version except for the path prefix.

## 4. Root-level launchers already in `thesis/` scope — unchanged

See §1 above (identical to the prior version of this plan).

## 5. Deliberate, later, code-editing steps — NOT part of this file-moving migration

Two categories of code correction are planned but explicitly deferred to their own separately-reviewed step, not bundled into the migration:

### 5a. Methodology documentation extraction (from `METHODOLOGY_PRESERVATION_PLAN.md`, unchanged)

1. Write `thesis/docs/trainer_patch.md` and `thesis/docs/persistbench_patch.md`.
2. Extract `checkpoint_selection.py` out of `src/trainer/base.py` and (optionally) `local_judge.py` out of `external/PersistBench/src/benchmark/execution/judgment.py`, each as its own reviewed, tested change.
3. Remove the two confirmed-dead code blocks in `external/PersistBench/src/benchmark/utils.py` (the vestigial local-judge max-tokens cap and the redundant `FORCE_VLLM_TRUNCATE_PROMPT_PATCH`).

### 5b. Generation-provenance correction (from `GENERATION_PROVENANCE.md`, new in this revision)

1. Correct the "repetition penalty 1.08" claim in `mechanistic/outputs/muse_books_weekly_update_analysis/README.md` to the confirmed `1.05` (Qwen-family runs).
2. Correct the hardcoded `"repetition_penalty": 1.08` / `"top_p": 1.0` / `"vllm_seed": 0` literals in `mechanistic/privacy_collapse/persistbench_native/prepare_native_200.py:208` and `prepare_native_sycophancy_200.py:243`.
3. Add a corrective note to the 9 affected JSONL files' `generation_settings` metadata (`mechanistic/privacy_collapse/persistbench_native/generations/*.jsonl` and their 3 Books-side copies) — **the actual generated text in these files is untouched**, only the metadata describing it is corrected.
4. Promote `thesis_cleanup_audit/GENERATION_PROVENANCE.md` to `thesis/docs/generation_provenance.md`.

Both 5a and 5b require the author's sign-off on the exact wording/values before editing, per the read-only constraint of every audit step so far — they are documented here as committed next steps, not executed.

## 6. Needs author decision before finalizing (unchanged from the first version, minus the now-resolved MUSE-News track question)

1. ~~Which MUSE-News track is canonical~~ — **resolved**, see `MUSE_NEWS_TRACK_RESOLUTION.md`.
2. `extract_single_privacylens.py`'s dual role as entry point and imported library — resolve before moving (§5 of `DEPENDENCY_MAP.md`).
3. Whether `configs/model/Qwen2.5-14B-Instruct.yaml` and its TOFU-14B experiment family are still active (affects whether it's referenced from `thesis/` in addition to living in `research_history/02_model_method_scaling/`).
4. Whether the 5 orphaned `tmp_paths/*` files and 9 `tmp_paths/*.py` debug scripts contain any unique analysis worth preserving before being treated as delete candidates.
5. Whether `configs/eval/tofu_partial_backup.yaml`, `run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh.bak_before_bestagg`, and `.bak_same_ckpt_diff` should live under `research_history/02_model_method_scaling/` or a small `thesis/docs/` backups note — either is defensible; not decided here.

## 7. Out of per-file scope (unchanged)

`saves/` (4.2 TB, gitignored), `logs/` (452 MB), upstream `outputs/` (6.3 MB), `data/` (959 MB) — see the first version of this plan §6 for the full reasoning, unchanged by this revision.
