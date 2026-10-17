# Code quality review

Read-only review of the thesis-specific code (`mechanistic/`, root launchers, `external/PersistBench` patches, `src/trainer/base.py` modifications). Findings only — nothing has been changed. Ordered roughly by how much it matters for grading/reproducibility.

## 1. A vendored upstream tool was hand-patched in place with no diff tracked anywhere

`external/PersistBench/src/benchmark/{config.py, execution/judgment.py, providers/openrouter.py, utils.py}` are all locally modified relative to that repo's own git history (confirmed: `git status` inside `external/PersistBench` shows 4 files `M` against its own HEAD `302ea2f`). The only record of what changed is 6 loose `.bak_*`/`.before_*` files sitting next to the current versions:

- `config.py.bak_local_judge` — judge backend switched from a hosted OpenRouter model to a local vLLM server
- `execution/judgment.py.bak_schema_judge` — added a schema-forced local-judge call path
- `providers/openrouter.py.bak_local_judge` — API key/base-URL now overridable via env vars to point at a local server
- `utils.py.bak_before_vllm_truncation`, `utils.py.bak_schema_judge`, `utils.py.before_strict_generation_patch` — three sequential snapshots showing an incrementally-applied "strict generation control" patch (forces temperature=0, top_p=1, caps max_tokens, sets repetition_penalty, adds prompt truncation)

**Why it matters:** every PersistBench result in the thesis implicitly depends on these patches. If `external/PersistBench` were ever re-cloned fresh, results would silently stop being reproducible with no error — the tool would just run with different generation settings and a different judge backend. **Recommend:** write a single markdown doc (or a real `git diff`/patch file) summarizing these 4 changes and check it into the thesis's own docs, rather than relying on loose `.bak` files as the only record. This is a real reproducibility gap, not just a tidiness issue.

## 2. The trainer's best-checkpoint-selection logic is undocumented outside two loose backup files

`src/trainer/base.py` (tracked upstream file, modified in place) adds two capabilities across two sequential patches, whose only record is `src/trainer/base.py.bak_before_agg_proxy` and `src/trainer/base.py.bak_before_bestagg_patch`:

1. An `Agg_proxy` metric — harmonic mean of a memorization-proxy and privacy-proxy composite over `extraction_strength`, `exact_memorization`, `forget_Q_A_Prob`, `forget_truth_ratio`, 4 MIA scores, `model_utility`, `forget_Q_A_gibberish`.
2. A `best_agg`/`BEST_AGG_MUSE_SELECTION_PATCH` block — harmonic mean of `retain_knowmem_ROUGE` (utility) and `1 - mean(forget_knowmem_ROUGE, forget_verbmem_ROUGE, extraction_strength)` (forgetting), stored as `eval_best_agg` for HF Trainer's `metric_for_best_model`.

This is the mechanism behind essentially every `*_savebest`/`bestagg_*` checkpoint directory name in `saves/unlearn/` and every file in `supervisor_update/code_settings/trainer_states/`. **It is currently the single most load-bearing thesis-specific modification to the framework, and it is documented nowhere except by diffing two accidental `.bak` files.** Strongly recommend a short methodology note (`thesis/docs/trainer_patch.md`) explaining exactly what `Agg_proxy` and `best_agg` compute and why, since a thesis committee will very likely ask about checkpoint selection methodology and the only current answer lives in an untracked backup file's diff.

## 3. Two non-identical MUSE-News result tracks, only one ever combined into a final table — **RESOLVED**

See `DEPENDENCY_MAP.md` §2 for the original finding and `MUSE_NEWS_TRACK_RESOLUTION.md` for the definitive resolution: Track A (official HF target) produced the only existing `FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv` but is superseded and not cited; Track B (locally-finetuned Qwen2.5-7B-Instruct target) is confirmed canonical — it is the track every mechanistic-analysis artifact and the News-vs-Books comparison is built on, proven via embedded checkpoint metadata in the generation files themselves. Track A is preserved as genuine historical research under `research_history/04_muse_track_a/` (see `PROPOSED_STRUCTURE.md`/`MIGRATION_PLAN.md`), not discarded — it is a complete, real result, just not the one the thesis cites. No further action needed beyond the migration itself.

## 3b. `repetition_penalty = 1.08` documentation claim is confirmed incorrect

See `GENERATION_PROVENANCE.md` for the full forensic trace. `mechanistic/outputs/muse_books_weekly_update_analysis/README.md` states the canonical Qwen MUSE-News/MUSE-Books PersistBench generations used `repetition_penalty = 1.08`. This is **incorrect**: the actual vLLM server logs from the generation jobs themselves (`logs/vllm_muse_{news,books}_qwen25_*.log`) show the effective value was `1.05` (the Qwen checkpoints' own `generation_config.json`, auto-applied by vLLM since no request explicitly overrode it). The `1.08` figure is traced to a hardcoded literal in two later, unrelated repackaging scripts (`mechanistic/privacy_collapse/persistbench_native/prepare_native_200.py:208`, `prepare_native_sycophancy_200.py:243`) that copied the value from `external/PersistBench/utils.py`'s `STRICT_GENERATION_CONTROL` default — a patch added 2026-07-21, nine days after the MUSE-News generation it's wrongly attributed to, and actually correct only for the later, out-of-scope WMDP-cyber "strict generation" runs. This is a documentation-accuracy issue, not a validity issue — the generated text itself is unaffected — and is scheduled for a controlled, later correction (see `MIGRATION_PLAN.md` §5b), not fixed in this read-only pass.

## 4. The same small library is reimplemented from scratch three times

`mechanistic/privacy_collapse/persistbench_mcq/common.py` (81 lines, PEP8-formatted) and `persistbench_sycophancy_mcq/common.py` (41 lines, dense one-liner style) independently implement the identical pattern: `ROOT`/`HERE`/`SOURCE`/`MANIFEST` path constants, a SAFE/violating label dict, a `sha256`/`file_sha256` helper, a chat-prompt builder, and a tokenize-pair helper. `persistbench_native/` has no `common.py` at all and inlines the same logic again per-script. None of this is copy-pasted (each was written independently), which is arguably worse — it means any future bugfix to, say, the sha256/provenance-hashing convention has to be found and applied in three separate places by hand. **Recommend**, if there is time before submission, extracting one shared `mcq_common.py`; not required for correctness since all three pipelines currently work and produce distinct, real outputs (MCQ privacy-judgment, MCQ sycophancy with A/B label-swap, native hidden-state extraction).

Similarly, the 5 stress-test scripts under `mechanistic/privacy_collapse/persistbench/run_local_{matched_rewrite,minimal_edit,simple,target,smoke}_stress.py` each reimplement their own sha256/atomic-write helper and duplicate a 3-item case-ID list (`pb-paired-008-cda672613fff`, `026-c24dc8d5a24c`, `036-d75dbf84413d`) verbatim across files.

## 5. Scripts that are simultaneously CLI entry points and imported libraries

`mechanistic/extract_single_privacylens.py` is run directly (has `argparse`/`__main__`) **and** imported by `build_population_manifest.py` and `extract_privacylens_positions.py` via bare same-directory imports (`from extract_single_privacylens import DATA_PATH, MODEL_PATHS, ...`). Likewise `analyze_benchmark_paradox.py` is imported by `prepare_paradox_mechanistic_candidates.py`. This works today only because all these files sit flat in the same directory; it is fragile against any reorganization (including the one this audit proposes) and against running any of these scripts from a different working directory. Not a correctness bug as the code stands, but worth flagging before any file move — see `MIGRATION_PLAN.md` §5.

## 6. Hardcoded, machine-specific absolute paths

Confirmed by direct grep/read, not by pattern-matching alone:

- `mechanistic/build_position_manifest.py`: `BASE_PATH = Path("/storage/ukp/work/elshashay/open-unlearning/saves/finetune/tofu_Qwen2.5-7B-Instruct_full")`
- `mechanistic/extract_single_privacylens.py`: multiple absolute paths under `/storage/ukp/work/elshashay/open-unlearning/saves/{finetune,unlearn}/...`
- `mechanistic/privacy_collapse/persistbench/run_remote.py`: `/mnt/beegfs/work/elshashay/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/snapshots/a09a35458c702b33eeacc393d103063234e8bc28` (×2)
- `run_muse_news_remaining_methods.sbatch` and several other `.sbatch` files: absolute `/storage/ukp/work/elshashay/...` paths
- `meeting_updates/wmdp_followup_2026_08_12/WMDP_followup_diagnostic_update.md`: references `/storage/ukp/work/elshashay/open-unlearning`, which is a **different filesystem than the current working tree** (`/mnt/beegfs/work/elshashay/open-unlearning`) — the repo appears to have moved between two cluster storage locations at some point, and not every hardcoded path was updated when that happened. This is worth checking broadly: any script still referencing `/storage/ukp/...` may be silently stale if the canonical location is now `/mnt/beegfs/...` (or vice versa; both `/mnt/beegfs/work/elshashay/open-unlearning` and `/storage/ukp/work/elshashay/open-unlearning` are listed as working directories for this session, so both may currently be valid, but any script hardcoding one specific one is not portable).

None of these are wrong today, but every one silently breaks (produces a `FileNotFoundError` at best, or loads the wrong checkpoint at worst) the moment the repo is cloned elsewhere, the HF cache is cleared, or files are moved per the migration plan. Recommend converting to environment-variable-configurable paths or paths relative to a computed repo root before archiving/submitting.

## 7. `.gitignore` rules with unintended blast radius (already confirmed live, not hypothetical)

Two existing unanchored `.gitignore` rules currently hide thesis content that looks like it was meant to be tracked:

- `saves*/` (no leading slash, matches at any depth) hides `supervisor_update/code_settings/hydra_configs/saves__unlearn__<run>/...` — 108 files, 1.7 MB of small frozen Hydra config snapshots — purely because their directory names start with `saves__`.
- `env/` (no leading slash) hides `supervisor_update/code_settings/env/` — a conda env yaml, pip freeze, and git commit/status snapshot, i.e. exactly the kind of environment-reproducibility record a thesis should keep, not silently drop.

Both were confirmed with `git check-ignore -v`. See `PROPOSED_STRUCTURE.md` "Gitignore recommendations" for the fix (anchor with a leading `/`); not applied here per the read-only constraint.

## 8. An untracked, uncompressible-sized, and actually corrupted archive sits at repo root

`tofu_qwen15_npo_f10_fixed.tar.gz` (2.25 GB) is at the repo root, is **not** covered by any `.gitignore` pattern (the `saves*/` rule only matches paths containing that segment; a root-level `.tar.gz` isn't caught), and — independently of scope — `tar -tzf` on it throws `gzip: unexpected end of file` after listing only 49 entries, i.e. **the archive itself is truncated/corrupted**. This is a concrete accidental-commit risk sitting one `git add -A` away from being pushed, and even if committed would not be a usable artifact.

## 9. A prior automated audit pass corrupted its own output

Not a thesis-code issue, but worth recording for provenance: an earlier run of `thesis_cleanup_audit/build_inventory.py` (before this session) contained a string literal with garbled/non-ASCII text spliced into it (`CLASSES = [..., "experiment_rbσίαςaardlish Nusantara competingста fillers://launcher", ...]`, immediately overwritten by `CLASSES[1] = "experiment launcher"` on the next line, plus a dead `for pat in [...]: pass` loop) and — more substantively — walked `external/PersistBench/.venv/` (a ~1.1 GB, ~28,000-file installed virtualenv), which inflated its "source code" count to 15,251 files and manufactured a fake 950-file "duplicate group" from trivially-identical empty stub files. This session rewrote `build_inventory.py` to exclude `.venv`/`.git`/`__pycache__`/`*.egg-info` from every walk and re-scoped it to the directories actually named in the audit request; the corrected run reports 1,638 files. If this script is rerun again in the future, verify its output sanity-checks against directory sizes (`du -sh`) before trusting large counts.

## 10. Inconsistent formatting across the `mechanistic/` codebase

Roughly half the scripts (e.g. `persistbench_mcq/common.py`) are PEP8-formatted with normal spacing; the other half (e.g. `persistbench_sycophancy_mcq/*.py`, `analyze_position_pca.py`) are written in a dense, unspaced one-liner style throughout. `mechanistic/extract_privacy_branch_counterfactuals.py` is 1,037 lines with no internal module split — the largest file in the tree by a wide margin. Neither is a functional bug, but a thesis codebase that will be graded on structure benefits from a single `black`/`ruff format` pass before submission, and the 1000+-line file is a candidate for splitting if time allows.

## 11. Minor: a silently-patched typo

`mechanistic/prepare_single_persistbench_case.py` contains a dict literal for `FILES['WGA']` that is overwritten one line later with a corrective comment ("historical output spells 'tofufull' consistently"). It works, but silently patching a typo in-place rather than fixing it at the naming source is a small landmine for whoever edits this file next without noticing the override.

## Summary — top issues by severity

| # | Issue | Severity |
|---|---|---|
| 1 | Vendored PersistBench hand-patched with no tracked diff | High — reproducibility |
| 2 | Trainer `Agg_proxy`/`best_agg` patch undocumented outside `.bak` files | High — reproducibility & methodology |
| 3 | Two non-identical MUSE-News tracks | **Resolved** — see `MUSE_NEWS_TRACK_RESOLUTION.md` |
| 3b | `repetition_penalty=1.08` documentation claim confirmed incorrect (actual: 1.05) | High — until corrected, correctness/citation risk; correction scheduled, not yet applied |
| 6 | Hardcoded machine-specific absolute paths (incl. a storage-location split: `/storage/ukp/...` vs `/mnt/beegfs/...`) | Medium — portability |
| 7 | `.gitignore` unanchored rules hiding real content (`saves*/`, `env/`) | Medium — data loss risk on fresh clone |
| 8 | Corrupted 2.25 GB tarball at root, not gitignored | Medium — accidental-commit risk |
| 5 | Entry-point scripts doubling as import libraries | Medium — migration fragility |
| 4 | 3x reimplemented shared MCQ/probe library code | Low-medium — maintainability |
| 10 | Inconsistent formatting, one 1000+-line file | Low — grading polish |
| 9 | Prior audit script self-corruption (already fixed this session) | Informational |
| 11 | Silently-patched typo in one script | Informational |
