# Proposed thesis-specific structure (revised)

Read-only proposal — nothing has been moved. The upstream `open-unlearning` tree (`src/`, `configs/` framework defaults, `docs/`, `data/`, `community/`, etc.) is **not** touched or reorganized. `external/PersistBench/` and `external/privacy-collapse/` (vendored external tools, each their own git repo) are likewise left in place, not reorganized — see `DEPENDENCY_MAP.md` §5.

**Revision note**: this replaces the single `archive/` tree from the first version of this document with **`research_history/`**, per explicit instruction that earlier TOFU, model-scaling, checkpoint-selection-development, MUSE Track-A, and WMDP work are genuine research phases that document how the final thesis design was reached — not "obsolete scripts" to be dumped in an undifferentiated archive. The three top-level trees now have a clear, distinct purpose:

- **`thesis/`** — only what is needed to reproduce or understand the final reported MUSE-News/MUSE-Books experiments.
- **`research_history/`** — earlier experiments, organized by research phase, no longer part of the final pipeline but important for understanding how the thesis got there. Nothing here is junk; each phase folder represents completed, real research.
- **`outputs/`** — generated artifacts. Not source-controlled except small curated summaries.

A genuinely small residual category — content that is byte-identical duplication, corrupted, or otherwise carries no unique research information — is called **DELETE CANDIDATE**, never "archive" or "obsolete," and is listed separately in `MIGRATION_PLAN.md` §4.

```
thesis/
    README.md                      # orientation: what each subfolder is, links to research_history/README.md
    configs/                       # thesis-added Hydra-style configs and PersistBench configs_local content, currently in final use
        eval/                      #   tofu.yaml delta notes (the tracked upstream file itself stays in configs/eval/)
        persistbench/              #   documentation pointer/index into external/PersistBench/configs_local/* (tool itself stays put)
    scripts/                       # experiment launchers actually in the final MUSE-News/MUSE-Books chain
        muse_news/ muse_books/ persistbench/ privacylens/ tables/
    analysis/
        behavioral/ representations/ probes/    # (unchanged from the first version — see prior MIGRATION_PLAN §2 for the full file list)
    slurm/                         # every *.sbatch actually in the final chain, grouped to mirror scripts/ above
    manifests/
        selection/                 #   SELECTED_MODEL_PATHS.tsv for the canonical MUSE-News (Track B) and both MUSE-Books targets
        trainer_states/            #   the subset of supervisor_update/code_settings/trainer_states/*.json for FINAL checkpoints only
        annotations/                #   mechanistic/privacy_collapse/persistbench/annotations/*, persistbench_mcq manifests
        model_lists/                #   the tmp_paths/*.tsv actually referenced by final-scope launchers
        environment/                #   supervisor_update/code_settings/env/{conda_unlearning.yml,pip_freeze_current_env.txt,git_commit.txt,git_status.txt} (repo-wide environment snapshot, relevant regardless of phase)
    docs/
        experiment_history.md       #   PROMOTED from thesis_cleanup_audit/EXPERIMENT_HISTORY.md — the high-level timeline connecting every
                                     #   research_history/ phase to the final thesis pipeline; this becomes the canonical, citable version
        experiment_history.csv      #   PROMOTED from thesis_cleanup_audit/experiment_history.csv (machine-readable companion)
        trainer_patch.md            #   explains the best_agg patch to src/trainer/base.py; cites research_history/03_checkpoint_selection_development/
                                     #   for the pre-patch snapshots
        persistbench_patch.md       #   explains the 4 active in-place patches to external/PersistBench (local judge routing, schema-forced
                                     #   parsing, generation-determinism controls) — this infrastructure is used by the FINAL thesis results,
                                     #   so it stays documented under thesis/, not research_history/, even though it was also used by the
                                     #   (historical) WMDP work
            persistbench_patch_history/   # small text-file copies of the 6 external/PersistBench *.bak_*/.before_* snapshots, for reference
                                          # alongside persistbench_patch.md (originals stay untouched next to the vendored tool itself)
        generation_provenance.md    #   PROMOTED from thesis_cleanup_audit/GENERATION_PROVENANCE.md — the confirmed generation settings
                                     #   (temperature=0.0, max_tokens=96, truncate_prompt_tokens=1800, max_model_len=2048, 3/3/1 generations
                                     #   per category, repetition_penalty=1.05 for Qwen-family runs) and the repetition_penalty=1.08
                                     #   documentation-error correction — see "Generation-provenance correction" section below
        mechanistic_readmes/        #   mechanistic/README.md, privacy_collapse/README.md, persistbench/README.md,
                                     #   persistbench_sycophancy_mcq/analysis/README.md, native_direction_inventory/README.md

research_history/
    README.md                       # top-level index: what this tree is, why it exists, one line per phase, explicit "this is not junk" statement,
                                     # points to thesis/docs/experiment_history.md for the full connected narrative

    01_tofu_baselines/
        README.md                   # see draft content below
        scripts/                    #   run_qwen15_methods_a180.sh, run_llama1b_paper_methods_a180.sh,
                                     #   run_llama1b_other_methods_fullmetrics_a180.sh, run_qwen3b_selected_methods_a100.sh,
                                     #   run_qwen3b_all_methods_fullmetrics_a180.sh
        manifests/                  #   trainer_state.json snapshots for the 20 paper_llama32_1b_*_f10_a180[_fullmetrics] runs

    02_model_method_scaling/
        README.md                   # see draft content below
        scripts/                    #   run_7bscale_top3_fullmetrics_a180.sh, run_llama32_3b_qwen7b_top3_fullmetrics_a180.sh,
                                     #   run_privacylens_full_before_after.sh, run_qwen_tofu_full_finetune_array.sh,
                                     #   run_qwen_tofufull_unlearn_best_array.sh, run_llama31_8b_tofufull_unlearn_{4methods_clean,
                                     #   best_array,remaining3_aggproxy}.sh, run_qwen25_14b_tofufull_{finetune,
                                     #   unlearn_4methods_aggproxy,unlearn_remaining_wga_satimp_h200}.sh,
                                     #   run_privacylens_{llama32_3b,llama31_8b,qwen,qwen25_14b}_tofufull_methods.sh
        configs/                    #   configs/model/Qwen2.5-14B-Instruct.yaml
        manifests/                  #   trainer_states + model_lists + hydra_configs snapshots for the bestagg_*/proper_*_from_tofufull_*
                                     #   runs (~82 trainer_state files + 5 model-list files + the 108-file hydra_configs snapshot)
        privacylens_results_snapshot/  # the 40 supervisor_update/code_settings/results/*.json PrivacyLens result files for this phase's
                                     #   models — kept here (not deleted) because this is the only committed copy of this phase's PrivacyLens
                                     #   results (the canonical outputs/ location is gitignored); see MIGRATION_PLAN §3 for the reasoning

    03_checkpoint_selection_development/
        README.md                   # see draft content below
        scripts/                    #   run_test_qwen7b_simnpo_save_bestagg.sh, run_4models_4methods_save_bestagg.sh
                                     #   (+ its .bak_before_tofufull_llama32_3b prior version)
        trainer_snapshots/           #   src/trainer/base.py.bak_before_agg_proxy, src/trainer/base.py.bak_before_bestagg_patch
                                     #   (the only surviving record of the trainer's pre-patch states; the live, patched
                                     #   src/trainer/base.py itself stays in place — see thesis/docs/trainer_patch.md)

    04_muse_track_a/
        README.md                   # see draft content below
        scripts/                    #   run_muse_news_remaining_methods.sbatch, run_muse_news_simnpo.sbatch,
                                     #   run_persistbench_muse_news_judge.sh, run_persistbench_muse_news_judge_like_tofu.sh,
                                     #   run_persistbench_muse_news_selected.sh, run_privacylens_muse_news_selected.sh,
                                     #   select_muse_news_best_checkpoints.py, make_muse_news_selected_table.py,
                                     #   make_final_muse_news_combined_table.py
        manifests/                  #   saves/final_muse_news_openunlearning_selection/{SELECTED_MODEL_PATHS.tsv,
                                     #   FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv, MUSE_News_all_methods_checkpoint_selection.csv,
                                     #   MUSE_News_selected_methods_summary.csv}, saves/final_muse_news_simnpo_openunlearning_selection/*
                                     #   (small csv/json pointer records ONLY — the multi-GB checkpoints themselves stay in saves/,
                                     #   already gitignored, not copied here)

    05_wmdp_side_investigation/
        README.md                   # see draft content below
        scripts/                    #   every run_wmdp_*.sh, run_persistbench_wmdp_*.sh, run_privacylens_wmdp_cyber_all4_selected.sh,
                                     #   run_persistbench_qwen25_7b_{full_generate,test}.sh, run_persistbench_qwen_wga_ckpt*.sh,
                                     #   run_persistbench_{full_generate_from_list,judge_array}.sh — INCLUDING the smoke-test scripts
                                     #   (run_wmdp_cyber_all4_smoke_array.sh, _nonrmu_smoke_fixed_array.sh, run_wmdp_cyber_qwen25_7b_rmu_test.sh,
                                     #   run_persistbench_wmdp_cyber_test0{,_anygpu}.sh, run_persistbench_qwen25_7b_test.sh) — these document
                                     #   a real smoke→fixed→sweep→real debugging iteration and are NOT delete candidates, per the "don't call
                                     #   real experimental history junk" principle
        docs/                       #   meeting_updates/wmdp_followup_2026_08_12/*, meeting_updates_wmdp_safety_summary.csv

outputs/                            # generated results — NEVER source-controlled except small curated summaries; see .gitignore recommendations below
    muse_news/                      #   Track B (canonical) only, now that MUSE_NEWS_TRACK_RESOLUTION.md has resolved which track is cited;
                                     #   Track A's outputs are recorded via research_history/04_muse_track_a/manifests/ instead of duplicated here
    muse_books/
        llama2_track/ qwen25_instruct_track/
    comparisons/                    # muse_news_category_comparison_validated.*, metric_reconciliation.*, cross_domain_*
    representations/                # *.pt tensors — never git-committed
    plots/                          # the 6 .png files currently mixed into the analysis tree

(external/, src/, saves/, logs/, data/ — unchanged from the first version of this document; see "Notes on things that deliberately do NOT move" below)
```

## Phase README drafts (content to write when the migration executes; not created on disk yet)

Each phase README below follows the 6-point structure requested: (1) question investigated, (2) dataset/models/methods, (3) key scripts/configs, (4) what was learned, (5) why the thesis moved on, (6) influence on final methodology.

### `research_history/README.md` (top-level index)

> This tree preserves the thesis's earlier research phases — work that is no longer part of the final reported MUSE-News/MUSE-Books pipeline (which lives in `thesis/`), but that documents how the final scope, models, methods, and checkpoint-selection methodology were reached. **Nothing here is obsolete clutter**: every phase folder represents genuine, completed research with real results, kept for grading and reproducibility. Large generated outputs, model checkpoints, and tensors are **not** copied here — only the scripts, configs, and small provenance records (manifests, frozen selection tables, trainer-state snapshots) needed to understand and, in principle, reproduce each phase. See `thesis/docs/experiment_history.md` for the full narrative timeline connecting every phase below to the final thesis work.
>
> - `01_tofu_baselines/` — the first working unlearning pipeline: all 10 open-unlearning methods on TOFU, small models.
> - `02_model_method_scaling/` — scaling the same methods to larger models (up to 14B) and the full TOFU forget set; PrivacyLens introduced.
> - `03_checkpoint_selection_development/` — where the harmonic-mean utility/forgetting checkpoint-selection metric (ancestor of the final `best_agg`) was invented and first validated.
> - `04_muse_track_a/` — the first complete MUSE-News result, using the official HF target directly; superseded by the locally-finetuned-target track used in the final thesis, but a real, working result in its own right.
> - `05_wmdp_side_investigation/` — a safety-generalization side investigation on WMDP-cyber/bio that directly motivated the pivot to the mechanistic-interpretability phase.

### `research_history/01_tofu_baselines/README.md`

> **Question**: does the open-unlearning framework correctly run all standard unlearning methods end-to-end, and what do their baseline results look like at small model scale, before any thesis-specific extension exists?
> **Dataset/models/methods**: TOFU (`f10`, 10%-forget split); Llama-3.2-1B, Qwen2.5-1.5B, Qwen2.5-3B; all 10 upstream methods — CEU, GradAscent, GradDiff, NPO, PDU, RMU, SatImp, SimNPO, UNDIAL, WGA.
> **Key scripts/manifests**: `run_qwen15_methods_a180.sh`, `run_llama1b_paper_methods_a180.sh`, `run_llama1b_other_methods_fullmetrics_a180.sh`, `run_qwen3b_selected_methods_a100.sh`, `run_qwen3b_all_methods_fullmetrics_a180.sh`; `manifests/` holds the 20 frozen `trainer_state.json` snapshots for these runs.
> **What was learned**: all 10 methods run correctly on this codebase; established the standard TOFU metric set (ROUGE-based knowledge/verbatim memorization, `extraction_strength`, `exact_memorization`, `forget_Q_A_Prob`, `forget_truth_ratio`, 4 MIA scores, `model_utility`) as the baseline before any custom selection logic existed.
> **Why the thesis moved on**: no checkpoint-selection mechanism existed yet (checkpoints were saved on a schedule, not selected by a metric); model sizes (1B–3B) and the 10%-forget split were too small to support the thesis's eventual larger-scale claims.
> **Influence on final methodology**: direct precursor establishing which methods (SatImp/SimNPO/RMU/WGA) were viable candidates carried into every subsequent phase.

### `research_history/02_model_method_scaling/README.md`

> **Question**: do the same methods and results hold up at much larger model scale (up to 14B), on the full (100%) TOFU forget set rather than the 10% subset, and does PrivacyLens as a second evaluation axis change the picture?
> **Dataset/models/methods**: TOFU (`f10`, then full/100% forget); Llama-3.1-8B, Llama-3.2-3B, Qwen2.5-3B/7B/14B; narrowed to a top method subset (SatImp/SimNPO/RMU/WGA).
> **Key scripts/configs**: `run_7bscale_top3_fullmetrics_a180.sh`, `run_llama32_3b_qwen7b_top3_fullmetrics_a180.sh`, `run_privacylens_full_before_after.sh` (first PrivacyLens use), `run_qwen_tofu_full_finetune_array.sh`, `run_qwen_tofufull_unlearn_best_array.sh`, `run_llama31_8b_tofufull_unlearn_{4methods_clean,best_array,remaining3_aggproxy}.sh`, `run_qwen25_14b_tofufull_{finetune,unlearn_4methods_aggproxy,unlearn_remaining_wga_satimp_h200}.sh`, `run_privacylens_{llama32_3b,llama31_8b,qwen,qwen25_14b}_tofufull_methods.sh`; `configs/model/Qwen2.5-14B-Instruct.yaml`.
> **What was learned**: the top-4-method subset scales cleanly to 14B; documents a deliberate switch from `Selection_proxy` (no privacy term) to `Agg_proxy` (with an MIA-derived privacy term) for checkpoint selection within a single day of experimentation (`_clean`/`_best_array` → `_remaining3_aggproxy`).
> **Why the thesis moved on**: TOFU is a synthetic benchmark; the thesis needed a more realistic, citable unlearning benchmark (MUSE) for its central claims.
> **Influence on final methodology**: the harmonic-mean utility/forgetting selection idea validated here for TOFU (`Agg_proxy`/`Selection_proxy`) is the direct conceptual ancestor of `best_agg`, the metric that selected every canonical MUSE-News/MUSE-Books checkpoint (see `03_checkpoint_selection_development/` and `thesis/docs/trainer_patch.md`).

### `research_history/03_checkpoint_selection_development/README.md`

> **Question**: how should HF `Trainer`'s `load_best_model_at_end` automatically pick the best unlearning checkpoint, given that unlearning has no single built-in "goodness" metric and trades off utility against forgetting (and, for TOFU, privacy/MIA)?
> **Dataset/models/methods**: cross-cutting — first validated on Qwen2.5-7B/SimNPO (TOFU), then applied across the whole model-scaling grid (phase 02) and, once adapted (`best_agg`), across every canonical MUSE run (`thesis/`).
> **Key scripts/files**: `run_test_qwen7b_simnpo_save_bestagg.sh` (first smoke test of metric-driven selection, same day as the trainer patch), `run_4models_4methods_save_bestagg.sh` (+ its `.bak_before_tofufull_llama32_3b` prior version — first systematic application at scale); `trainer_snapshots/src_trainer_base.py.bak_before_agg_proxy` and `.bak_before_bestagg_patch` — the only surviving record of the trainer's state before each patch. See `thesis_cleanup_audit/CHECKPOINT_SELECTION_PATCH.md` for the full technical diff and `thesis/docs/trainer_patch.md` for the citable summary.
> **What was learned**: a harmonic mean of a utility proxy and a forgetting proxy (`Agg_proxy`/`Selection_proxy` for TOFU) gives `metric_for_best_model` a principled single scalar; this pattern was later adapted into `best_agg` specifically for MUSE's different metric set (no MIA/exact-memorization scores available).
> **Why the thesis moved on**: once the thesis moved to MUSE (phase 04+), the TOFU-specific proxy metrics (`Agg_proxy`/`Selection_proxy`, which need MIA scores) no longer applied, requiring the MUSE-specific `best_agg` variant — but the underlying idea developed here carried over directly.
> **Influence on final methodology**: **direct and load-bearing** — `best_agg` (the direct adaptation of this phase's pattern) is the actual mechanism that selected every canonical MUSE-News and MUSE-Books checkpoint used in the reported thesis results, proven checkpoint-by-checkpoint in `CHECKPOINT_SELECTION_PATCH.md` §4.

### `research_history/04_muse_track_a/README.md`

> **Question**: does directly unlearning from the official MUSE-News HuggingFace target (Llama-2-7b, no local finetuning step) produce a complete, usable MUSE+PrivacyLens result?
> **Dataset/models/methods**: MUSE-News, official `muse-bench/MUSE-News_target` (Llama-2-7b); RMU, WGA, SimNPO, SatImp.
> **Key scripts/manifests**: `run_muse_news_remaining_methods.sbatch`, `run_muse_news_simnpo.sbatch`, `select_muse_news_best_checkpoints.py`, `make_muse_news_selected_table.py`, `make_final_muse_news_combined_table.py`, `run_privacylens_muse_news_selected.sh`, `run_persistbench_muse_news_{judge,judge_like_tofu,selected}.sh`; `manifests/` holds the small selection/summary tables, **not** the multi-GB checkpoints themselves.
> **What was learned**: this setup **fully worked end-to-end** — a real, complete combined MUSE+PrivacyLens result exists (`FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv`) for 4 unlearning methods. This is not a failed or abandoned experiment.
> **Why the thesis moved on**: the thesis shifted to a locally-finetuned Qwen2.5-7B-Instruct target instead (the canonical "Track B," in `thesis/`), for methodological consistency with how MUSE-Books was later done, and because the mechanistic-interpretability phase that followed was built specifically around the Qwen2.5-7B-Instruct model family. See `thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md` for the full resolution of why Track B, not this track, is the one cited in the final thesis text.
> **Influence on final methodology**: this track's checkpoint-selection and combined-table scripts are the direct template that Track B's own selection/reporting scripts were modeled on.

### `research_history/05_wmdp_side_investigation/README.md`

> **Question**: does the thesis's unlearning methodology (particularly RMU) generalize as a safety intervention on WMDP-cyber/bio, and can a robust generation/judging pipeline for it be established?
> **Dataset/models/methods**: WMDP-cyber, WMDP-bio; Qwen2.5-7B (various unlearned checkpoints); RMU and other methods; an MMLU utility follow-up.
> **Key scripts/docs**: the full smoke→fixed→sweep→real iteration (`run_wmdp_cyber_all4_smoke_array.sh` → `_nonrmu_smoke_fixed_array.sh` → `_all4_sweep300_array.sh` → `_rmu_real_array.sh`), `run_wmdp_cyber_before_eval.sh`, `run_wmdp_cyber_qwen25_7b_rmu_test.sh`, `run_wmdp_bio_test_qwen_books_before.sh`, `run_wmdp_mmlu_qwen_{small,missing,wga_sweep}.sh`, the `run_persistbench_wmdp_cyber_*.sh` generate/judge scripts (including the "strict generation" variants), `run_privacylens_wmdp_cyber_all4_selected.sh`; `docs/meeting_updates/wmdp_followup_2026_08_12/` and `meeting_updates_wmdp_safety_summary.csv`.
> **What was learned**: real validity/collapse issues were found in early WMDP results (documented in the meeting note itself), motivating the smoke→fixed→sweep→real debugging chain — every step in that chain is kept here together because each documents a real iteration, not because any one of them is "the" result.
> **Why the thesis moved on**: the meeting note explicitly records the decision to revisit WMDP once more, then pivot to interpretability work — the mechanistic analysis phase begins within days of the final WMDP meeting update.
> **Influence on final methodology**: this is where the `PB_REPETITION_PENALTY=1.08` setting (and the other `STRICT_GENERATION_CONTROL` defaults in `external/PersistBench/utils.py`) was actually introduced and used (2026-07-21/22) — directly relevant context for the generation-provenance correction below: `1.08` is a real, legitimate setting for this WMDP work, just incorrectly and later backfilled onto the description of the earlier (and unrelated) MUSE generation runs.

## Generation-provenance correction (from `GENERATION_PROVENANCE.md`) — included in the plan, not yet executed

The canonical Qwen-family MUSE-News (Track B) and MUSE-Books PersistBench generations are confirmed (via the actual `vLLM` server logs from the generation jobs themselves, not current code) to have used `temperature=0.0`, `max_tokens=96`, prompt truncated to the last 1800 tokens, `max_model_len=2048`, 3 generations per cross-domain/sycophancy item and 1 per beneficial-memory item, and an effective `repetition_penalty=1.05` (from the Qwen checkpoints' own `generation_config.json`, auto-applied by vLLM). The existing claim of `repetition_penalty=1.08` in `mechanistic/outputs/muse_books_weekly_update_analysis/README.md` is confirmed **incorrect** — traced to a hardcoded literal in two later repackaging scripts that never called a generation API and instead copied a value off the *current* (post-generation) state of `external/PersistBench/utils.py`.

This plan includes, as a **later, separately-executed, controlled correction** (not performed now):

1. Correct the "repetition penalty 1.08" line in `mechanistic/outputs/muse_books_weekly_update_analysis/README.md` to state `repetition_penalty=1.05 (Qwen-family runs; confirmed via vLLM server log)`.
2. Correct the hardcoded `"repetition_penalty": 1.08` (and the also-incorrect `"top_p": 1.0`, `"vllm_seed": 0`) literals in `mechanistic/privacy_collapse/persistbench_native/prepare_native_200.py:208` and `prepare_native_sycophancy_200.py:243`, either to the confirmed correct values or to a note that these are non-authoritative documentation, not measured provenance.
3. Add a corrective note (not a silent edit) to the 9 JSONL files whose `generation_settings` metadata field inherited the incorrect value (`mechanistic/privacy_collapse/persistbench_native/generations/*.jsonl` and their 3 Books-side copies under `mechanistic/outputs/muse_books_weekly_update_analysis/native_sycophancy/generations/`) — **the `generated_response`/`memory_response` text itself in these files must not be changed**, only the metadata describing it.
4. Promote `thesis_cleanup_audit/GENERATION_PROVENANCE.md` to `thesis/docs/generation_provenance.md` as the citable record of this correction.

None of this is executed in this revision pass — it is scheduled into `MIGRATION_PLAN.md` §5 as an explicit, deliberate, code-editing step distinct from the file-moving migration.

## Notes on things that deliberately do NOT move

- **`external/PersistBench/` and `external/privacy-collapse/`** stay exactly where they are, including `configs_local/`, `outputs/`, `logs/`, `templates/` beneath them.
- **`src/trainer/base.py`** and **`configs/eval/tofu.yaml`** stay in place — tracked upstream files modified in place; their *documentation* moves to `thesis/docs/`, and their *pre-patch history* (small text-file `.bak` snapshots only) moves to `research_history/03_checkpoint_selection_development/`.
- **`saves/`, `logs/`, `outputs/` (top-level, upstream), `data/`** are already covered by the existing `.gitignore` (`saves*/`, `logs/`, `output*/`, `data/`) and are out of scope for file-level enumeration — see "Gitignore recommendations" below.
- **The MUSE-News track question is now resolved** (`MUSE_NEWS_TRACK_RESOLUTION.md`): Track B is canonical and lives in `thesis/`/`outputs/muse_news/`; Track A is historical and lives in `research_history/04_muse_track_a/`, represented by small manifest/table files, not duplicated full outputs.

## Gitignore recommendations (not applied — the task says do not change `.gitignore` yet)

Unchanged from the first version of this document, with one addition: `research_history/` itself should **not** be gitignored — it is source-controlled documentation/scripts/small-manifests, the same as `thesis/`. Only the large-artifact exclusions below apply.

1. **Unanchored `saves*/` rule silently swallows unrelated thesis content** (`supervisor_update/code_settings/hydra_configs/saves__unlearn__<run>/...`, 108 files) — recommend anchoring to `/saves*/`.
2. **Unanchored `env/` rule silently hides `supervisor_update/code_settings/env/`** (a reproducibility-critical environment snapshot, not a virtualenv) — recommend anchoring to `/env/`.
3. New rules needed once the thesis dirs exist in their proposed locations: `outputs/` (thesis-specific), `mechanistic/**/model_cache/` (14 GB HF cache), `mechanistic/**/representations/**/*.pt`, `external/PersistBench/.venv/`, `external/PersistBench/outputs/`, `external/PersistBench/logs/`, `*.tar.gz` at repo root (would have caught the corrupted `tofu_qwen15_npo_f10_fixed.tar.gz`), any `*.bak*` pattern repo-wide outside `research_history/03_checkpoint_selection_development/trainer_snapshots/` and `thesis/docs/persistbench_patch_history/` (which are the two places `.bak` files are *meant* to live, deliberately tracked, not ignored).
