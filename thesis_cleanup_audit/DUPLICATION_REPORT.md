# Duplication report

Read-only audit. Nothing was moved or deleted. This report combines (a) automated SHA-256 exact-duplicate detection over the corrected thesis-scoped file set (see `build_inventory.py` / raw group list in `DUPLICATION_REPORT_AUTO.md`) and (b) content-level near-duplicate analysis of scripts that differ byte-for-byte but do the same job. A prior pass of this audit accidentally hashed `external/PersistBench/.venv/` (a vendored virtualenv) and reported a bogus 950-file "duplicate group" of trivially-identical empty stub files; that data is discarded. The corrected automated pass found **45 exact-duplicate groups**, all of them meaningful (no vendor noise).

## 1. Exact duplicates (byte-identical, SHA-256 verified)

### 1a. Root script ↔ `supervisor_update/code_settings/` mirror (the dominant pattern)

`supervisor_update/code_settings/{scripts,configs}/` is a **point-in-time snapshot bundle** the author copied out for sharing with a supervisor. Of its 17 scripts + 13 configs (30 files), **29 are byte-identical** to the live root/`configs/` copy. Examples confirmed by hash:

- `run_privacylens_full_before_after.sh` — identical in 3 places: root, root `.bak_raw_base`, and `supervisor_update/code_settings/scripts/`
- `configs/eval/tofu.yaml` == `supervisor_update/code_settings/configs/eval/tofu.yaml`
- `configs/model/Qwen2.5-14B-Instruct.yaml` == `supervisor_update/code_settings/configs/model/Qwen2.5-14B-Instruct.yaml`
- ...and 26 more pairs of the same shape (every file in `supervisor_update/code_settings/scripts/` and `supervisor_update/code_settings/configs/` except one, see 1b).

**Implication:** the entire `supervisor_update/code_settings/{scripts,configs}/` subtree (30 files) is redundant with content that already lives in the canonical locations. It should not be treated as a second source of truth — see `MIGRATION_PLAN.md` (ARCHIVE, not KEEP).

### 1b. The one script that *broke* from its supervisor-bundle copy

`run_persistbench_qwen25_7b_test.sh` (root) and `supervisor_update/code_settings/scripts/run_persistbench_qwen25_7b_test.sh` are **not** identical (10 diff lines) — the live root version was edited after the bundle was made. This means the bundle is not just redundant, it is **already stale/inconsistent** with the live tree, which is exactly the failure mode of hand-copied snapshots instead of version control.

### 1c. Redundant archive bundling

`supervisor_update/code_settings_bundle.tar.gz` (147 members) and `supervisor_update/code_settings_bundle_full.tar.gz` (337 members) both archive the same `code_settings/` directory tree sitting unpacked right next to them; `bundle_full` is confirmed a strict superset of `bundle`. That is three copies of the same content (unpacked dir + 2 tarballs) inside one folder.

### 1d. `external/PersistBench/outputs/` cross-listing

`external/PersistBench/outputs/final_tofu_persistbench_localjudge/llama31_8b_after_rmu_from_tofufull_localjudge.json` is byte-identical to `external/PersistBench/outputs/llama31_8b_full/llama31_8b_after_rmu_from_tofufull_localjudge.json` — the same TOFU/Llama-3.1-8B result was written into two output folders. Out of final MUSE-News/MUSE-Books scope, but flags that PersistBench's `outputs/` naming convention isn't authoritative-single-copy.

### 1e. `tmp_paths/` near-identical model lists

`tmp_paths/muse_news_qwen25_persistbench_models.tsv`, `muse_news_qwen25_privacylens_models.tsv`, and `muse_news_qwen25_selected_models.tsv` are byte-identical to each other — three differently-named copies of the same one model-path list, each apparently made ad hoc for a different consuming script rather than referenced once from a single file.

Full machine-readable group list: `DUPLICATION_REPORT_AUTO.md` (45 groups) and `inventory.csv`.

## 2. Near-duplicate scripts (content-level, not byte-identical)

These were identified by direct reading/diffing (see fork reports) and are the higher-value finding for cleanup, since exact-hash matching can't catch them.

| Group | Files | Relationship | Canonical / keep |
|---|---|---|---|
| MUSE-News judge script pair | `run_persistbench_muse_news_judge.sh`, `run_persistbench_muse_news_judge_like_tofu.sh` | Same job name, same 5 output files; `_like_tofu` mirrors the naming convention used for the analogous MUSE-Books script | `_judge_like_tofu.sh` is canonical; plain `_judge.sh` is the earlier draft |
| MUSE-News generate script pair | `run_persistbench_muse_news_qwen25_selected.sh`, `run_persistbench_muse_news_selected.sh` | Same job name `pbench_muse_news` (collision risk on SLURM), differ only in the internal `OUT_SUBDIR` (Qwen25 track vs Llama2 track) | Not redundant — they are the two parallel model tracks — but the shared job name should be fixed to avoid confusion/log clobbering |
| MUSE-Books PrivacyLens pair | `run_privacylens_muse_books_llama2_forced_choice.sh`, `run_privacylens_muse_books_llama2_selected.sh` | Differ only in a forced-choice eval flag | Both legitimate (different eval protocol variants), keep both, document the difference |
| TOFU-8B unlearn iteration chain | `run_llama31_8b_tofufull_unlearn_4methods_clean.sh` → `_best_array.sh` → `_remaining3_aggproxy.sh` | Sequential iterations of the same experiment (clean → array-ified → rerun with Agg_proxy metric) | `_remaining3_aggproxy.sh` is latest; earlier two are superseded (out of final scope regardless — TOFU) |
| WMDP-cyber smoke-to-real chain | `run_wmdp_cyber_all4_smoke_array.sh` → `_nonrmu_smoke_fixed_array.sh` → `_sweep300_array.sh` → `_rmu_real_array.sh` | Clear smoke → fixed-smoke → real-sweep progression | Only `_rmu_real_array.sh`/`_sweep300_array.sh` are "real"; smoke variants are obsolete (out of final scope regardless — WMDP) |
| WMDP-cyber smoke-test pair | `run_persistbench_wmdp_cyber_test0.sh`, `run_persistbench_wmdp_cyber_test0_anygpu.sh` | Duplicate smoke tests, one GPU-agnostic | Both obsolete (out of final scope) |
| `saves/unlearn/muse_news_simnpo_ckpts*` (checkpoint dirs, not scripts) | `muse_news_simnpo_ckpts`, `muse_news_simnpo_ckpts_bs1_gc`, `muse_news_simnpo_ckpts_bs1_gc_sbatch` | Three superseded training iterations of the same method | Only the `_bs1_gc_sbatch` checkpoint is consumed by `select_muse_news_best_checkpoints.py` |
| `.bak` files that are true byte-duplicates | `run_privacylens_full_before_after.sh.bak_raw_base` | Byte-identical to the live script (see group 1a) — a pure copy with no informational value | Safe to archive/discard (unlike the other `.bak_*` files, which do encode a real prior parameter state) |

## 3. Reimplemented-independently code (not copy-paste, but should be one library)

Not hash-duplicates, but the strongest *structural* duplication finding in the codebase:

- **PersistBench single-case scripts**: `analyze_single_persistbench_case.py` / `extract_single_persistbench_case.py` are the hardcoded-RMU originals; `analyze_persistbench_case_generic.py` / `extract_persistbench_case_generic.py` are clean, argparse-driven, method-agnostic rewrites that supersede them. The "single" versions are not dead code — their frozen output already exists under `mechanistic/outputs/single_persistbench_case/` — so they are provenance artifacts, not duplicates to delete.
- **Three parallel MCQ/native probe pipelines** — `mechanistic/privacy_collapse/persistbench_mcq/`, `persistbench_native/`, `persistbench_sycophancy_mcq/` each independently implement the same pattern (path constants, SAFE/violating label dicts, sha256 helper, chat-prompt builder, tokenize-pair helper) with different variable names and no shared base module. `persistbench_mcq/common.py` and `persistbench_sycophancy_mcq/common.py` are the clearest case — structurally identical logic, written twice from scratch. This is a real "should have been one library" case, but each pipeline produces genuinely different, real results (MCQ privacy-judgment vs. MCQ sycophancy with A/B label-swap), so nothing here is deletable — it's a code-quality/maintainability finding, see `CODE_QUALITY_REVIEW.md`.
- **Five PersistBench stress-test scripts** — `mechanistic/privacy_collapse/persistbench/run_local_{matched_rewrite,minimal_edit,simple,target,smoke}_stress.py` each reimplement their own `sha256`/atomic-write helper and duplicate a 3-item `STRESS_TARGETS`/`CASES` case-ID list verbatim. All five represent genuinely different stress-test protocols (needed for provenance/robustness claims), so none is obsolete, but the boilerplate should be centralized into a shared `stress_common.py` if there is time before submission.

## 4. What this means for cleanup

- The `supervisor_update/code_settings/{scripts,configs}/` subtree and both `code_settings_bundle*.tar.gz` files are safe to **archive as a single dated snapshot**, not preserved as active code — nothing there is the canonical copy of anything (§1a-c), and the one file that did diverge (§1b) is exactly the risk of keeping copies around.
- No exact duplicate found anywhere involves the actual final-result-producing chain (see `DEPENDENCY_MAP.md`) losing information — every "final" script is a unique file.
- The near-duplicate iteration chains (§2) are useful evidence for `DUPLICATION_REPORT`/`MIGRATION_PLAN` classification as "obsolete experiment" vs "current," but none should be deleted outright per the task's DELETE-CANDIDATE-only policy.
