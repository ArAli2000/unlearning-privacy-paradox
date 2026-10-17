# Checkpoint-selection patch (`src/trainer/base.py`)

Read-only analysis. `base.py` was **not modified** by this investigation. All evidence below comes from `git diff HEAD -- src/trainer/base.py`, direct `diff` between the three on-disk states (upstream-tracked HEAD, `.bak_before_agg_proxy`, `.bak_before_bestagg_patch`, current), `stat` mtimes, and cross-referencing `trainer_state.json`/`SELECTED_MODEL_PATHS.tsv` files on disk.

## 1. What was changed from upstream — exact functions/lines

`git diff HEAD -- src/trainer/base.py` is **147 insertions, 0 deletions** — the patch is purely additive; no upstream `FinetuneTrainer` behavior was removed or altered, only new code was inserted. Two independent additions, made at different times (see §7 chronology):

### Addition 1 — module-level proxy-metric helpers (lines 14–115 in current file)

```
src/trainer/base.py:14   def _harmonic_mean(values, eps=1e-12)
src/trainer/base.py:28   def _get_metric(metrics, key)
src/trainer/base.py:39   def _set_proxy_metric(metrics, key, value)
src/trainer/base.py:47   def add_proxy_scores(metrics, baseline_model_utility=None)
```

`add_proxy_scores` requires **10** specific metric keys to all be present (`extraction_strength`, `exact_memorization`, `forget_Q_A_Prob`, `forget_truth_ratio`, `mia_loss`, `mia_zlib`, `mia_min_k`, `mia_min_k_plus_plus`, `model_utility`, `forget_Q_A_gibberish`) — these are **TOFU-eval-specific** metric names (MIA scores and TOFU's memorization/probability metrics). If any is missing it returns the metrics dict untouched (line 57: `if any(_get_metric(metrics, key) is None for key in required_keys): return metrics`). When present, it computes and writes back six new metrics (both bare and `eval_`-prefixed, per the comment at line 36-38 explaining why: "`Agg_proxy` appears clearly in `trainer_state.json`... `eval_Agg_proxy` works reliably with `metric_for_best_model`"):

- `Mem_proxy` = harmonic mean of `(1-extraction_strength, 1-exact_memorization, 1-forget_Q_A_Prob, 1-forget_truth_ratio)`
- `Privacy_proxy` = harmonic mean of the 4 MIA scores
- `Utility_proxy` = harmonic mean of `(scaled_model_utility, forget_Q_A_gibberish)`, where `scaled_model_utility = min(model_utility / baseline_model_utility, 1.0)` if a baseline is known
- `Agg_proxy` = harmonic mean of `(Mem_proxy, Privacy_proxy, Utility_proxy)` — the 3-way memorization/privacy/utility aggregate
- `Selection_proxy` = harmonic mean of `(Mem_proxy, Utility_proxy)` — a 2-way variant that **omits** the MIA-derived privacy term
- `scaled_model_utility_proxy` = the scaled utility value itself

### Addition 2 — inline `best_agg` block inside `FinetuneTrainer.evaluate()` (lines 163–188)

```
src/trainer/base.py:135  def evaluate(...)
src/trainer/base.py:163      # BEST_AGG_MUSE_SELECTION_PATCH
src/trainer/base.py:190      if not hasattr(self, "_proxy_baseline_model_utility"): ...
src/trainer/base.py:196      eval_metrics = add_proxy_scores(eval_metrics, baseline_model_utility=self._proxy_baseline_model_utility)
```

This block is explicitly labeled by its own comment: *"Add an aggregate checkpoint-selection metric for **MUSE-style runs**. Higher is better."* It reads `retain_knowmem_ROUGE`, `forget_knowmem_ROUGE`, `forget_verbmem_ROUGE`, `extraction_strength` — **MUSE-eval-specific** metric names (no MIA/TOFU keys needed) — and only if all four are present computes:

```
utility_proxy = clamp(retain_knowmem_ROUGE, 0, 1)
memory_proxy  = clamp(1 - mean(forget_knowmem_ROUGE, forget_verbmem_ROUGE, extraction_strength), 0, 1)
best_agg      = 2 * utility_proxy * memory_proxy / (utility_proxy + memory_proxy)   # harmonic mean, guarded against 0/0
```

written to both `eval_metrics["best_agg"]` and `eval_metrics["eval_best_agg"]`, then calls `add_proxy_scores(...)` immediately after (this is the same call regardless of whether the run is TOFU or MUSE; for MUSE runs `add_proxy_scores` is a guaranteed no-op since the 10 TOFU keys it needs aren't present — see §5).

**In plain terms: this file now contains two independent, non-interacting checkpoint-quality metrics** — `Agg_proxy`/`Selection_proxy` (TOFU-oriented, needs MIA scores) and `best_agg` (MUSE-oriented, needs MUSE knowmem/verbmem/extraction metrics) — bolted onto the same `evaluate()` method. Both exist purely so that HF `Trainer`'s built-in `load_best_model_at_end`/`metric_for_best_model`/`greater_is_better` machinery has a single scalar to select the best checkpoint on, since neither TOFU nor MUSE evaluation in the upstream framework ships one out of the box.

## 2. Why the change was introduced (inferred from code + usage, not stated anywhere in prose)

No design-rationale comment or doc exists anywhere in the repo explaining *why* this was needed — the only in-code explanation is the two comments quoted above and the metric names themselves. Based on how the metrics are actually used (§3) and how open-unlearning's eval framework works, the reasoning is:

- HF `Trainer.evaluate()` returns a flat metrics dict; `load_best_model_at_end` needs exactly one named scalar in `metric_for_best_model`, and it must be **higher-is-better or lower-is-better consistently** (`greater_is_better`). Open-unlearning's stock TOFU/MUSE evaluators report many individual metrics (ROUGE scores, extraction strength, MIA AUCs, truth ratios, etc.) but no single "how good is this unlearning checkpoint" number.
- Unlearning inherently trades off two goals that pull in opposite directions — forgetting the target data vs. retaining general utility — so a naive single metric (e.g. just "lowest forget-ROUGE") would pick a checkpoint that forgets everything, including how to speak. A harmonic mean of a utility term and a forgetting term is a standard way to force *both* to be simultaneously decent before a checkpoint scores well (a harmonic mean collapses toward zero if either term is bad), which is exactly what `best_agg` and `Agg_proxy`/`Selection_proxy` do.
- Two variants exist because TOFU evaluation exposes MIA-style privacy metrics that MUSE evaluation does not — `Agg_proxy` (with `Privacy_proxy`) is the TOFU-era metric; `best_agg` (MUSE-only inputs) was added later specifically for MUSE, per its own comment. `Selection_proxy` is a TOFU variant that drops the MIA/privacy term, likely used where MIA scores were noisy/unavailable during a particular TOFU sweep.

## 3. Which experiments depended on it — confirmed by grepping every launcher for `metric_for_best_model`

| `metric_for_best_model` value | Used by | In final MUSE-News/Books scope? |
|---|---|---|
| `best_agg` | `run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh`, `run_muse_news_qwen25_7b_instruct_unlearn_retry_after_rmu.sh`, `run_muse_books_qwen25_7b_instruct_unlearn_after_ft.sh`, `run_muse_books_llama2_7b_unlearn_selected_methods.sh` | **Yes — all 4 of these are exactly the canonical checkpoint-producing runs** (Track B MUSE-News + both MUSE-Books tracks, per `MUSE_NEWS_TRACK_RESOLUTION.md`) |
| `eval_Agg_proxy` | `run_4models_4methods_save_bestagg.sh`, `run_llama31_8b_tofufull_unlearn_remaining3_aggproxy.sh`, `run_qwen25_14b_tofufull_unlearn_4methods_aggproxy.sh`, `run_qwen25_14b_tofufull_unlearn_remaining_wga_satimp_h200.sh`, `run_test_qwen7b_simnpo_save_bestagg.sh` | No — all TOFU-full, out of final scope |
| `eval_Selection_proxy` | `run_llama31_8b_tofufull_unlearn_4methods_clean.sh`, `run_llama31_8b_tofufull_unlearn_best_array.sh`, `run_qwen_tofufull_unlearn_best_array.sh` | No — all TOFU-full, out of final scope |
| (none — no `metric_for_best_model` override) | `run_muse_news_remaining_methods.sbatch`, `run_muse_news_simnpo.sbatch` (the Track-A official-target MUSE-News run) | Superseded track; selected its checkpoints post-hoc via `select_muse_news_best_checkpoints.py` reading `MUSE_SUMMARY.json` across all saved checkpoints, **not** via this in-training patch at all |

**This cleanly confirms: `best_agg` is used exclusively by, and only by, the four launcher scripts that produced the canonical MUSE-News (Track B) and both MUSE-Books checkpoints.** `Agg_proxy`/`Selection_proxy` are TOFU-only and irrelevant to the final thesis results. Track A's MUSE-News run didn't use in-training best-checkpoint selection at all — it saved on a fixed schedule and picked the best after the fact.

## 4. Which final checkpoints were selected using it — proven, not inferred

Read directly from the checkpoint's own `trainer_state.json` (this is HF Trainer's own record of what it did, not a script's claim about what it intended to do):

```
$ python3 -c "import json; d=json.load(open('saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459/trainer_state.json')); print(d['best_metric'], d['best_global_step'], d['best_model_checkpoint'])"
0.19242792501682263 459 ./saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459
```

The log-history entry at step 459 shows `{'best_agg': 0.19242792501682263, 'eval_best_agg': 0.19242792501682263, 'step': 459}` — an exact match to `best_metric`, and an exact match to the `best_metric` column value recorded independently in `saves/final_muse_news_qwen25_7b_instruct_selection/SELECTED_MODEL_PATHS.tsv` (`SATIMP ... 0.19242792501682263`). This is a closed loop of independent confirmation: the patch computed the number, HF Trainer used it to pick checkpoint-459 as best and recorded that fact in `trainer_state.json`, and the separate selection manifest recorded the identical number. **The `best_agg` patch is literally, mechanically, the reason checkpoint-459 (not checkpoint-500, which also exists on disk for both SatImp and SimNPO) was selected as the canonical MUSE-News SatImp/SimNPO checkpoint.** The same applies to every other `best_agg`-selected checkpoint (MUSE-News RMU/WGA, both MUSE-Books tracks' SatImp/SimNPO/RMU/WGA).

## 5. Does the current implementation contain obsolete/debug code?

- **`add_proxy_scores`/`Agg_proxy`/`Selection_proxy` (Addition 1, lines 14–115) are dead weight for every MUSE-News/MUSE-Books experiment.** They are still executed on every single `evaluate()` call regardless of dataset (line 196 calls `add_proxy_scores` unconditionally), but for MUSE runs the required-keys guard always fails silently and the call is a no-op. This is not a bug (nothing breaks), but it means roughly half the patch (~102 of 147 added lines) is irrelevant to the final thesis experiments and exists only to support the earlier, out-of-scope TOFU-full sweeps.
- **No genuinely obsolete/debug code was found** in the `best_agg` block itself (Addition 2) — it is small, self-contained, and every line is load-bearing for the final results.
- **Minor code smell, not a bug**: `_bestagg_float_metric` (an inline closure) is redefined from scratch on every single `evaluate()` call rather than being a module-level function like `_get_metric` right above it — functionally harmless, just inconsistent style within the same file.
- **Minor smell**: `self._proxy_baseline_model_utility` is set as an instance attribute via `hasattr`/manual-init rather than in `__init__`, which works but is easy to miss when reading the class definition.

## 6. Can this be expressed as a documented configuration option instead of an undocumented patch?

**Yes, cleanly**, and this is the single highest-value cleanup opportunity: the trainer patch is a form of "which combination of eval metrics counts as best" policy, which the open-unlearning framework already has a natural extension point for — its Hydra-configured `evaluator`/metric system. Two viable clean designs (elaborated in `METHODOLOGY_PRESERVATION_PLAN.md`):

1. Keep `best_agg`/`Agg_proxy`/`Selection_proxy` computation exactly as-is, but move it out of `FinetuneTrainer.evaluate()` into a small, named, documented module (e.g. `src/trainer/checkpoint_selection.py`) that `base.py` imports and calls with one line — same behavior, but the *definition* of these metrics lives somewhere a grader can find by name instead of by reading the whole trainer file. This requires touching `base.py` (a one-line import + one-line call swap for the ~147 lines currently inline), which is a "small, documented modification to upstream," not zero-touch.
2. Additionally expose `metric_for_best_model` policy as a first-class Hydra config field (e.g. `configs/trainer/muse_selection.yaml` documenting `metric_for_best_model: best_agg` alongside a comment explaining the harmonic-mean formula), so a grader reading configs (rather than shell scripts with `++trainer.args.metric_for_best_model=...` overrides) sees the selection policy declared explicitly per experiment.

Given `best_agg` is genuinely load-bearing for reproducing the exact final checkpoints (§4), it **must remain functionally identical** — this is a refactor-for-clarity recommendation, not a request to change behavior, and should only be done as a deliberate, reviewed step (see `METHODOLOGY_PRESERVATION_PLAN.md` for sequencing), not silently during the file-moving phase of cleanup.

## 7. Chronology (for context, not required by the task, but explains the two `.bak` files)

| State | File | mtime | Contains |
|---|---|---|---|
| Upstream | `git show HEAD:src/trainer/base.py` | (tracked) | Neither addition |
| Snapshot 1 | `src/trainer/base.py.bak_before_agg_proxy` | 2026-06-14 13:01 | Neither addition (identical in content terms to upstream for the purposes of this patch) |
| Snapshot 2 | `src/trainer/base.py.bak_before_bestagg_patch` | 2026-07-06 21:27 | Addition 1 only (`Agg_proxy`/`Selection_proxy`), not yet Addition 2 |
| Current | `src/trainer/base.py` | 2026-07-06 21:27 (same minute as snapshot 2 — both edits happened in one sitting) | Both additions |

This confirms: `Agg_proxy`/`Selection_proxy` (TOFU-era) predates `best_agg` (MUSE-era) by roughly three weeks, consistent with the thesis's TOFU-full work happening first and the MUSE-News/Books-specific selection metric being added when that work began — both patches were applied in the same file on the same day (2026-07-06), immediately before the MUSE unlearning runs that used `best_agg` were launched (`run_muse_news_qwen25_7b_instruct_unlearn_after_ft.sh` etc. run shortly after this date, per `saves/finetune/muse_news_qwen25_7b_instruct_target`'s 2026-07-06 mtime).
