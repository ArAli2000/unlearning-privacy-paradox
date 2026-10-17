# Dependency map

Read-only audit — describes dependencies as they exist today; nothing has been changed. This matters for the migration plan because several of these dependencies are **path-fragile**: they assume today's exact directory layout and would silently break (not error loudly) if files were moved without updating them.

## 1. Training → checkpoint-selection → evaluation pipeline (the critical path)

```
run_muse_news_remaining_methods.sbatch (WGA/RMU/SatImp)  ┐
run_muse_news_simnpo.sbatch (SimNPO)                     ┴─→ saves/unlearn/muse_news_<method>_ckpts_bs1_gc_sbatch/checkpoint-*/evals/MUSE_SUMMARY.json
                                                                        │
                                                                        ▼
                                              select_muse_news_best_checkpoints.py  (picks best checkpoint per method)
                                                                        │
                                                                        ▼
                                              make_muse_news_selected_table.py  ──→ saves/final_muse_news_openunlearning_selection/SELECTED_MODEL_PATHS.tsv
                                                                        │
                        ┌───────────────────────────────────────────────┼───────────────────────────────────────────────┐
                        ▼                                               ▼                                               ▼
     run_privacylens_muse_news_selected.sh                run_persistbench_muse_news_selected.sh          (MUSE standard metrics already in MUSE_SUMMARY.json)
     (hardcodes checkpoint-500/500/459/357 paths!)         + run_persistbench_muse_news_judge_like_tofu.sh
                        │                                               │
                        ▼                                               ▼
     outputs/privacylens_muse_news_selected/*/privacy_mcq_all493.json   external/PersistBench/outputs/muse_news_selected_full/*.json
                        │                                               │
                        └───────────────────────┬───────────────────────┘
                                                 ▼
                              make_final_muse_news_combined_table.py
                                                 ▼
                saves/final_muse_news_openunlearning_selection/FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv   ← the only "FINAL_" combined MUSE-News table that exists on disk
```

The MUSE-Books chain is structurally analogous but has **no checkpoint-name-pattern coupling** (single track, see §3):

```
run_muse_books_llama2_7b_unlearn_selected_methods.sh (official Llama-2 target, clean single run)
run_muse_books_qwen25_7b_instruct_finetune.sh → run_muse_books_qwen25_7b_instruct_unlearn_after_ft.sh (locally finetuned Qwen target)
        │
        ▼
saves/final_muse_books_{llama2_7b,qwen25_7b_instruct}_selection/SELECTED_MODEL_PATHS.tsv
        │
        ├─→ run_persistbench_muse_books_llama2_selected.sh / _judge_like_tofu.sh          → external/PersistBench/outputs/muse_books_llama2_selected_full/
        ├─→ run_persistbench_muse_books_qwen25_selected.sh / _localjudge.sh               → external/PersistBench/outputs/muse_books_qwen25_selected_full/
        └─→ run_privacylens_muse_books_llama2_selected.sh / _forced_choice.sh
            run_privacylens_muse_books_qwen25_selected.sh                                 → outputs/privacylens_muse_books_*_selected/
```

## 2. ⚠ Two non-identical MUSE-News tracks — reproducibility ambiguity that code alone cannot resolve

The audit found **two parallel, self-consistent MUSE-News pipelines** that both produce "selected"/"final"-named artifacts, and only one of them was ever carried through to a combined MUSE+PrivacyLens table:

| | Track A — "openunlearning_selection" | Track B — "qwen25_7b_instruct" |
|---|---|---|
| Target model | Official HF `muse-bench/MUSE-News_target` (Llama-2-7b), no local finetune | Locally finetuned Qwen2.5-7B-Instruct (`run_muse_news_qwen25_7b_instruct_finetune.sh`) |
| Unlearn scripts | `run_muse_news_remaining_methods.sbatch`, `run_muse_news_simnpo.sbatch` | `run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh` + `_unlearn_retry_after_rmu.sh` (3 of 4 methods OOM'd and were retried — confirmed by `saves/unlearn/muse_news_qwen25_7b_instruct_{satimp,simnpo,wga}_failed_oom_before_retry_20260706_231334` on disk) |
| Selection artifact | `saves/final_muse_news_openunlearning_selection/SELECTED_MODEL_PATHS.tsv` (2026-07-04) | `saves/final_muse_news_qwen25_7b_instruct_selection/SELECTED_MODEL_PATHS.tsv` (2026-07-08, later) |
| PersistBench | ✅ `external/PersistBench/outputs/muse_news_selected_full` | ✅ `external/PersistBench/outputs/muse_news_qwen25_selected_full` (2026-07-08) |
| PrivacyLens | ✅ `run_privacylens_muse_news_selected.sh` → `outputs/privacylens_muse_news_selected/` | ✅ `run_privacylens_muse_news_qwen25_selected.sh` → `outputs/privacylens_muse_news_qwen25_selected/` |
| Combined MUSE+PrivacyLens table | ✅ `make_final_muse_news_combined_table.py` → **the only `FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv` that exists** | ❌ no equivalent combiner script found — this track dead-ends after PersistBench/PrivacyLens, never combined |

**This is chronologically later (Track B, 2026-07-08) but methodologically the odd one out (Track A used the official HF target directly, matching the MUSE benchmark's own convention; Track B mirrors the MUSE-Books methodology of finetuning-your-own-target).** Track A is what the one existing "FINAL" CSV actually reports. **This cannot be resolved from the file evidence alone — it requires the thesis author to state which track the thesis text actually cites**, and the migration/cleanup should not silently pick one and archive the other without that confirmation. See `MIGRATION_PLAN.md` §"Needs author decision."

MUSE-Books has no equivalent ambiguity — one track per base model, cleanly.

## 3. Path-fragile couplings (would break silently on a naive file move)

| Dependent | Depends on (exact string/path) | Risk if moved |
|---|---|---|
| `run_privacylens_muse_news_selected.sh` | Hardcodes absolute checkpoint paths `saves/unlearn/muse_news_{rmu,wga,simnpo,satimp}_ckpts_bs1_gc_sbatch/checkpoint-{500,357,459,500}` | If `select_muse_news_best_checkpoints.py` is ever rerun and picks different checkpoint numbers, this script goes stale silently (no error, just evaluates the wrong checkpoint) |
| `mechanistic/build_position_manifest.py` | `BASE_PATH = Path("/storage/ukp/work/elshashay/open-unlearning/saves/finetune/tofu_Qwen2.5-7B-Instruct_full")` (absolute, machine-specific) | Breaks outright on any other machine/user, including the `/mnt/beegfs/...` path this repo is currently checked out under |
| `mechanistic/extract_single_privacylens.py` (also imported as a library by `build_population_manifest.py` and `extract_privacylens_positions.py`) | Absolute paths under `/storage/ukp/work/elshashay/open-unlearning/saves/{finetune,unlearn}/...` | Same machine-specific breakage; additionally this is a script-with-`__main__` being imported as a module by siblings — moving it without also updating the importing files' `sys.path`/relative-import assumptions will break both |
| `mechanistic/privacy_collapse/persistbench/run_remote.py` | `/mnt/beegfs/work/elshashay/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28` (×2, absolute HF cache snapshot hash) | Breaks if the HF cache is ever cleared/redownloaded (snapshot hash changes) or on another machine |
| `mechanistic/persistbench_native/analysis/native_direction_inventory/build_inventory.py` | Reads `external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_{before,satimp,simnpo}.json` by hardcoded relative dict | Tied to Track B's PersistBench output naming; would need updating if Track A/B ambiguity (§2) is resolved by renaming |
| `mechanistic/persistbench_sycophancy_mcq/finalize.py` | Reads `mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_category_comparison_validated.json` (cross-links two of the three parallel probe pipelines) | Any reorg that separates `persistbench_native/` from `persistbench_sycophancy_mcq/` into different top-level dirs (e.g. `representations/` vs `probes/` per the proposed structure) must preserve or update this relative path |
| `mechanistic/prepare_paradox_mechanistic_candidates.py`, `prepare_single_persistbench_case.py` | Read `external/PersistBench/outputs/final_tofu_persistbench_localjudge/*` | TOFU-scoped, out of final thesis focus but still a live dependency if these scripts are ever rerun |
| Most `run_persistbench_*.sh` scripts | `templates/simple_llama_chat_template.jinja` (root-level) | Fine as long as `templates/` stays at repo root or the scripts' relative path is updated together |
| `run_persistbench_*.sh`, `run_privacylens_*.sh` scripts referencing `tmp_paths/*.tsv` | 20 of 25 `tmp_paths/*` list files are actively read by specific root launchers (verified by grep); 5 are orphaned (`llama31_8b_persistbench_models.tsv`, `muse_news_qwen25_privacylens_models.tsv`, `muse_news_qwen25_selected_models.tsv`, `persistbench_validity_all_datasets.py`, `qwen25_14b_finetune_cfg_preview.yaml`) | Moving `tmp_paths/` requires updating every referencing launcher in lockstep; safe to archive only the 5 orphaned files independently |
| `src/trainer/base.py` (`Agg_proxy`, `best_agg`/`BEST_AGG_MUSE_SELECTION_PATCH` additions) | Upstream-tracked file, modified in place; consumed implicitly by every `run_*.sh`/`.sbatch` that sets `metric_for_best_model`/`load_best_model_at_end` to select the best MUSE checkpoint (the whole `*_savebest`/`bestagg_*` naming convention across `saves/unlearn/` depends on this) | This is the single most load-bearing thesis modification to upstream code; must stay in place (KEEP IN PLACE), but should be documented (a checked-in diff/patch or methodology note), since the only record of "before" is the two loose `.bak_*` files |
| `external/PersistBench` (vendored tool) `src/benchmark/{config,utils,execution/judgment,providers/openrouter}.py` | Hand-patched in place (local-judge routing, strict generation-determinism controls, prompt truncation) vs. the tool's own git history (`external/PersistBench/.git`, HEAD `302ea2f`) — confirmed via `git status` inside that nested repo: 4 files show as modified, 7 `.bak_*`/new dirs (`configs_local/`, `outputs/`, `templates/`) show as untracked | Every `run_persistbench_*.sh` script implicitly depends on these local patches (deterministic generation, local judge) being present; if `external/PersistBench` were ever re-cloned fresh from upstream, all PersistBench results would silently stop being reproducible without reapplying these patches from the `.bak_*` diffs |
| `mechanistic/privacy_collapse/common.py` | `external/privacy-collapse/benchmarks/privacylens/data/main_data.json` (separate vendored repo, not PersistBench) | Confirms `external/privacy-collapse` is a live data dependency, not just a reference clone — must stay in place |

## 4. Import-fragility inside `mechanistic/`

Several scripts double as both an entry point (`if __name__ == "__main__"`) **and** a same-directory-import library for siblings, which only works because they currently sit in the same flat directory:

- `extract_single_privacylens.py` → imported by `build_population_manifest.py` (for `DATA_PATH, MODEL_PATHS, build_prompt`) and `extract_privacylens_positions.py` (for `DATA_PATH, MODEL_PATHS, REPO_ROOT, build_prompt, build_prompt_text`)
- `analyze_benchmark_paradox.py` → imported by `prepare_paradox_mechanistic_candidates.py`

Any migration that moves these files into different subdirectories (e.g. splitting "behavioral" vs "representations" per the proposed structure) **must** either keep each import pair together or convert the shared functions into a proper `_lib.py`/package module first. This is flagged again in `CODE_QUALITY_REVIEW.md` and is the main reason `MIGRATION_PLAN.md` marks most `mechanistic/*.py` files as "IMPORT/PATH UPDATE REQUIRED" rather than "SAFE MOVE."

## 5. External tool boundary

- `external/PersistBench/` and `external/privacy-collapse/` are each their **own git repositories** (nested `.git`, not registered as submodules of the parent repo — the parent's `.gitignore`/tracking has no knowledge of them; `git status` shows each as one opaque `??` line). Recommend documenting exact commit hashes and install commands (e.g. `uv sync` against the pinned `uv.lock`) rather than moving any of their files, and formalizing them as git submodules if reproducibility needs to survive a fresh clone.
- `external/PersistBench/configs_local/` and `external/PersistBench/outputs/`/`logs/`/`templates/` are thesis-specific *usage* of the vendored tool (config inputs and result outputs), but must stay inside `external/PersistBench/` because the tool resolves them relative to its own root — they cannot be "SAFE MOVE"d into `thesis/` without breaking the tool, even though they are conceptually thesis artifacts.
