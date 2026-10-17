# Thesis: MUSE-News / MUSE-Books unlearning — behavioral and mechanistic analysis

## 1. Goal

This thesis studies LLM unlearning on the **MUSE-News** and **MUSE-Books** benchmarks: standard unlearning evaluation, black-box privacy/robustness behavior (PrivacyLens, PersistBench), and a mechanistic-interpretability layer examining what unlearning changes at the hidden-state level (native prompt-end representations, sycophancy transitions, controlled MCQ probes, A/B label-swap robustness).

## 2. Relationship to upstream `open-unlearning`

This repository is a local checkout of the [locuslab/open-unlearning](https://github.com/locuslab/open-unlearning) framework (confirmed via `git remote -v`: `origin` points directly at `https://github.com/locuslab/open-unlearning.git` — there is no separate fork remote in this checkout's git configuration) with this thesis's work added as local, currently-uncommitted changes. The framework itself (`src/`, upstream `configs/`, `docs/`, `data/`) is **not** reorganized by this thesis's cleanup — only two upstream files are modified in place, both documented in `docs/`:

- `src/trainer/base.py` — adds the `best_agg` checkpoint-selection metric (`docs/trainer_patch.md`).
- `configs/eval/tofu.yaml` — minor eval-metric additions (tracked, modified; no separate doc, see `git diff`).

Everything else under `thesis/` and `research_history/` is thesis-added code, organized by this migration; upstream open-unlearning code was not touched.

## 3. Final datasets

- **MUSE-News** — the canonical track uses a **locally-finetuned Qwen2.5-7B-Instruct target** (not the official HF target directly). An earlier track using the official target directly (`muse-bench/MUSE-News_target`, Llama-2-7b) produced a complete, real result but is **not** the one cited in the final thesis — see `docs/experiment_history.md` §3–4 and `../thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md` for the full evidence-based resolution. That earlier track is preserved at `../research_history/04_muse_track_a/`.
- **MUSE-Books** — two tracks, both canonical: the official Llama-2-7b target, and a locally-finetuned Qwen2.5-7B-Instruct target.

## 4. Final unlearning methods

**BASE** (no unlearning), **SatImp**, **SimNPO** — the three models used in every mechanistic-analysis artifact. **RMU** and **WGA** are additionally evaluated at the behavioral (PrivacyLens/PersistBench standard-metric) layer for both datasets, but were not carried into the mechanistic hidden-state/probe pipelines.

## 5. Repository structure

```
thesis/
  README.md            <- this file
  scripts/              experiment launchers actually in the final MUSE-News/MUSE-Books chain
    common.sh            shared helper: robust repo-root detection + conda-env activation (see §17)
    muse_news/ muse_books/ persistbench/ privacylens/ validation/
    setup_external_dependencies.sh   clones/pins/patches external/PersistBench + external/privacy-collapse (§17)
  manifests/            small, frozen, reproducibility-critical records (never large checkpoints/tensors)
    selection/          SELECTED_MODEL_PATHS.tsv for every canonical checkpoint family
    trainer_states/      trainer_state.json snapshots for the canonical MUSE-News checkpoints
    model_lists/          the tmp_paths/*.tsv model-path lists actually used by the scripts above
    environment/          conda env / pip freeze / git commit-status snapshot
    provenance/            the generation-parameter correction record (see §15)
    external_dependencies/  external_dependencies.tsv: exact URL/commit/patch provenance for external/ (§17)
  patches/               thesis-specific patch(es) against pinned external/ commits (§17)
  docs/                  methodology and history documentation (this file's companions)

research_history/         earlier research phases -- NOT obsolete, see research_history/README.md
  01_tofu_baselines/ 02_model_method_scaling/ 03_checkpoint_selection_development/
  04_muse_track_a/ 05_wmdp_side_investigation/

mechanistic/               mechanistic-analysis SOURCE CODE for the final thesis results -- intentionally
                            left in its original location by this migration (see §11); every script here
                            computes its own path to the repo root via `Path(__file__).resolve().parents[N]`
                            with N hardcoded to its current directory depth. Reorganizing these ~68 files
                            into thesis/analysis/ would require recalculating N per file with no automated
                            way to test the result (nothing is being re-run), so this was deliberately
                            deferred as its own, separately-verified follow-up task rather than risked here.

external/PersistBench/    vendored tool (its own git repo), NOT reorganized, NOT committed to this repo's
                            git history (see §17 -- committing it directly would create broken embedded-repo
                            gitlinks). 4 files patched in place -- see docs/persistbench_patch.md.
external/privacy-collapse/  vendored tool (its own git repo), NOT reorganized, NOT committed (§17). Clean,
                            unmodified relative to its pinned commit.

saves/, logs/, data/, upstream outputs/   large generated artifacts, already gitignored, not enumerated here.
```

## 6. Canonical checkpoints

| Dataset | Track | BASE | SatImp | SimNPO |
|---|---|---|---|---|
| MUSE-News | Qwen2.5-7B-Instruct (canonical) | `saves/finetune/muse_news_qwen25_7b_instruct_target` | `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459` | `saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459` |
| MUSE-Books | Llama-2-7b | `muse-bench/MUSE-Books_target` (official HF) | `saves/unlearn/muse_books_llama2_7b_satimp/checkpoint-153` | `saves/unlearn/muse_books_llama2_7b_simnpo/checkpoint-408` |
| MUSE-Books | Qwen2.5-7B-Instruct | `saves/finetune/muse_books_qwen25_7b_instruct_target` | `saves/unlearn/muse_books_qwen25_7b_instruct_satimp/checkpoint-51` | `saves/unlearn/muse_books_qwen25_7b_instruct_simnpo/checkpoint-51` |

Full manifests (all methods, incl. RMU/WGA, and the exact `best_agg` metric value each checkpoint was selected on): `thesis/manifests/selection/*_SELECTED_MODEL_PATHS.tsv`. Every path above was verified to exist on disk as of this migration (2026-09-14).

## 7. How standard unlearning evaluation was performed

Checkpoints were trained via open-unlearning's standard `FinetuneTrainer`, with `metric_for_best_model=best_agg` (`docs/trainer_patch.md`) selecting the best checkpoint automatically during training via `load_best_model_at_end`. Launchers: `thesis/scripts/muse_news/run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh` (+ its OOM retry), `thesis/scripts/muse_books/run_muse_books_{llama2_7b_unlearn_selected_methods,qwen25_7b_instruct_unlearn_after_ft}.sh`. Standard MUSE metrics (ROUGE-based knowledge/verbatim memorization, `extraction_strength`, `model_utility`, etc.) are computed by open-unlearning's own evaluator during/after training.

## 8. How PrivacyLens was evaluated

`thesis/scripts/privacylens/eval_privacylens_mcq_local.py` (+ `_local_strict.py`, `_forced_choice.py` variants) against the frozen `external/privacy-collapse/benchmarks/privacylens/data/main_data.json` input, invoked by `thesis/scripts/privacylens/run_privacylens_muse_{news_qwen25,books_llama2,books_qwen25}_selected.sh`. Outputs: `outputs/privacylens_muse_{news_qwen25,books_llama2,books_qwen25}_selected/` (generated, not committed — see §13).

## 9. How PersistBench was evaluated

Generation via `thesis/scripts/persistbench/run_persistbench_muse_{news_qwen25,books_llama2,books_qwen25}_selected.sh` (vLLM-served checkpoint, `external/PersistBench`'s `openai_compatible` provider), judged locally via `run_local_judge_server_penelope.sh` + `run_persistbench_muse_{news_qwen25,books_llama2,books_qwen25}_{judge_like_tofu,localjudge}.sh`.

**Verified canonical generation settings** (Qwen-family MUSE-News and MUSE-Books runs; confirmed from the actual vLLM server logs of the generation jobs themselves, not assumed from current code — full evidence in `docs/generation_provenance.md`):

| Setting | Value |
|---|---|
| `temperature` | `0.0` |
| `max_tokens` | `96` |
| Prompt truncation | last `1800` tokens |
| `max_model_len` | `2048` |
| `repetition_penalty` | `1.05` |
| Generations per item — cross-domain | `3` |
| Generations per item — sycophancy | `3` |
| Generations per item — beneficial-memory | `1` |

A `seed` was not explicitly set anywhere (no `--seed` flag, no `seed` request parameter); this is inconsequential because `temperature=0.0` forces greedy/argmax decoding, which involves no sampling and is therefore deterministic regardless of seed. **These values are confirmed for the Qwen-family runs only** — the equivalent settings for the Llama-2-7b MUSE-Books track (specifically `repetition_penalty`/`top_p`/`top_k`) could not be established from available evidence (no matching vLLM override-log line was found for that model family) and are correctly left as unclaimed/uncertain in `docs/generation_provenance.md` rather than assumed to match the Qwen values.

**Judge caveat (important)**: the judge used for every PersistBench result in this repository — both datasets, all tracks — is a locally-served `Qwen/Qwen2.5-7B-Instruct` model, **not** the canonical PersistBench judge (`moonshotai/kimi-k2-thinking`). State this explicitly wherever PersistBench numbers are reported; see §15 and `docs/persistbench_patch.md`.

Full evidence trail, including how the `repetition_penalty` value was verified and a documentation error it corrected: `docs/generation_provenance.md`.

## 10. How mechanistic analyses were performed

Source code: `mechanistic/` (left in its original location, see §5/§11). Pipeline: native prompt-end hidden-state extraction and sycophancy-transition analysis (`mechanistic/privacy_collapse/persistbench_native/`), controlled MCQ privacy-judgment probes (`mechanistic/privacy_collapse/persistbench_mcq/`), controlled MCQ sycophancy probes with A/B label-swap robustness testing (`mechanistic/privacy_collapse/persistbench_sycophancy_mcq/`). All three pipelines operate on the canonical MUSE-News Qwen2.5-7B-Instruct checkpoints (§6), confirmed via each pipeline's own `gpu_extraction_provenance.json`. The MUSE-Books replication of this same analysis is at `mechanistic/outputs/muse_books_weekly_update_analysis/`.

## 11. How to reproduce analyses without rerunning model generation

Every PersistBench/PrivacyLens generation already exists on disk as frozen JSON/JSONL (see §13 for locations). To reproduce a downstream **analysis** without regenerating text:
- Native hidden-state / sycophancy analysis: rerun `mechanistic/privacy_collapse/persistbench_native/analyze_sycophancy.py` etc. against the existing `generations/*.jsonl` (no GPU needed for the CPU-only analysis scripts; the extraction scripts themselves need a GPU and are not required if you only want to re-derive the published tables/plots from the already-extracted `representations/*.pt` tensors).
- Metric reconciliation / category comparison: `mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_persistbench_metric_reconciliation.{json,md}` is a frozen analysis output, re-derivable from the existing judged JSON files via `external/PersistBench/analysis/failure_rates.py` (official, unmodified) without any new generation.
- Generation validation: `thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py` reads existing generation/judgment JSON, no GPU required.

**This README does not claim any specific command has been re-executed and verified working end-to-end in this migration** — only that the frozen inputs each script needs are confirmed present on disk (§9 of `thesis_cleanup_audit/POST_MIGRATION_VALIDATION.md`).

## 12. Which tasks require SLURM/GPU

Everything that calls `vllm serve` (all PersistBench generation and local judging, `thesis/scripts/persistbench/*.sh`), all model training/finetuning (`thesis/scripts/muse_news/*.sh`, `thesis/scripts/muse_books/*.sh`), and all hidden-state extraction in `mechanistic/` (any script under `.../persistbench_native/`, `persistbench_mcq/`, `persistbench_sycophancy_mcq/` whose name starts with `extract_`). CPU-only: PrivacyLens *behavioral* scoring (not its representation/logit-lens variant), the analysis/reconciliation scripts listed in §11, and all table-generation scripts.

## 13. Generated-output locations

- `outputs/privacylens_muse_*_selected/`, `external/PersistBench/outputs/muse_*_selected_full/` — behavioral eval results (gitignored, not committed).
- `mechanistic/outputs/`, `mechanistic/privacy_collapse/*/analysis/`, `mechanistic/privacy_collapse/*/representations/` — mechanistic analysis results and tensors (gitignored, not committed; see `.gitignore`'s `mechanistic/**/representations/` rule).
- `saves/` — model checkpoints (gitignored, 4.2 TB, not committed).
None of these were relocated by this migration (see `thesis_cleanup_audit/PROPOSED_STRUCTURE.md` Phase 6 reasoning) — they remain exactly where the scripts above already write them.

## 14. Research-history link

Earlier TOFU baselines, model/method scaling, checkpoint-selection-metric development, the superseded MUSE-News official-target track, and a WMDP-cyber/bio safety side-investigation are preserved, organized by phase, at `../research_history/` — **not obsolete clutter**, see `../research_history/README.md` and `docs/experiment_history.md` for how each phase shaped the final thesis design.

## 15. Known provenance caveats

- **Local Qwen PersistBench judge, not canonical Kimi-K2**: every PersistBench judgment in this repository (both MUSE-News and MUSE-Books, all tracks) was produced by a locally-served `Qwen/Qwen2.5-7B-Instruct` judge, never the canonical `moonshotai/kimi-k2-thinking`. State this explicitly wherever PersistBench numbers are reported. See `docs/persistbench_patch.md` and `thesis_cleanup_audit/PERSISTBENCH_MODIFICATIONS.md` §6.
- **Historical generation `repetition_penalty=1.05`, not 1.08**: the canonical Qwen-family MUSE-News/MUSE-Books PersistBench generations used an effective `repetition_penalty=1.05` (confirmed via the actual vLLM server logs from the generation jobs), not `1.08` as an earlier internal document incorrectly stated. See `docs/generation_provenance.md`.
- **Frozen-artifact metadata correction sidecar**: 9 existing generation JSONL files contain an incorrect `repetition_penalty: 1.08` in their own metadata (inherited from the same error). These files were **not edited** (their generated text is valid and unchanged) — the correction is recorded separately at `thesis/manifests/provenance/persistbench_generation_corrections.json`. Any future consumer of these files' `generation_settings` field should cross-check against that sidecar.
- **MUSE-News track**: see §3 — do not cite the official-target track's numbers as "the" MUSE-News result without checking `thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md`.
- **`mechanistic/` source code was not reorganized** in this migration (see §5/§10) — a deliberate, documented deferral, not an oversight.

## 16. Environment / reproducibility information

A snapshot of the conda environment, `pip freeze`, and the git commit/status at the time of the original experiments is at `thesis/manifests/environment/` (`conda_unlearning.yml`, `pip_freeze_current_env.txt`, `git_commit.txt`, `git_status.txt`). `external/PersistBench/uv.lock` pins that vendored tool's exact dependency versions. Note (per `thesis_cleanup_audit/PERSISTBENCH_MODIFICATIONS.md`/`docs/persistbench_patch.md`): `external/PersistBench`'s code has since been modified again (2026-07-21, after the canonical generations) relative to what was live when the canonical generations ran — exact bit-for-bit regeneration of the original PersistBench responses is not possible even with today's code; the existing frozen output files are the authoritative record.

## 17. External dependency strategy and running scripts on another machine

`external/PersistBench/` and `external/privacy-collapse/` are each their own git repository. They are **not** committed into this repository's git history (a plain `git add external/` would silently create broken "embedded repository" gitlinks — confirmed via `git add --dry-run`, see `thesis_cleanup_audit/FINAL_GRADING_REVIEW.md`). Instead:

- `thesis/manifests/external_dependencies/external_dependencies.tsv` records, for each: its exact repository URL, the exact commit this thesis pinned it to, whether it was modified for the thesis, and (if so) which patch file captures the modification.
- `thesis/patches/persistbench.patch` is the exact `git diff` of PersistBench's 4 modified files against its pinned commit (`302ea2f`) — the same modifications documented narratively in `docs/persistbench_patch.md`. `external/privacy-collapse/` needed no patch (confirmed clean against its pinned commit via `git status`).
- `thesis/scripts/setup_external_dependencies.sh` reads that TSV and, for each dependency not already present, clones it, checks out the pinned commit, and applies its patch if one exists. It never overwrites or resets an existing checkout — it reports and stops if one is already present, so it's safe to run on a machine that already has these set up.

**Every `thesis/scripts/*.sh` launcher was also fixed in this pass to stop hardcoding one specific cluster path.** They now `source thesis/scripts/common.sh`, which determines the repository root via `git rev-parse --show-toplevel` (falling back to a path relative to the script's own location) instead of assuming `/storage/ukp/work/elshashay/open-unlearning` or `/mnt/beegfs/work/elshashay/open-unlearning`. The conda environment activation path/name (`UNLEARNING_CONDA_ACTIVATE`, `UNLEARNING_CONDA_ENV`) remains genuinely machine-specific by nature (conda is installed per-user) and defaults to the historical values, overridable via those two environment variables on another machine. `HF_HOME`/`TRANSFORMERS_CACHE`/`CUDA_HOME`/`HOME` exports inside these scripts are still hardcoded to the original cluster's paths — fixing those was out of scope for this pass; see `thesis_cleanup_audit/PRE_COMMIT_VALIDATION.md` for the full remaining-path audit.
