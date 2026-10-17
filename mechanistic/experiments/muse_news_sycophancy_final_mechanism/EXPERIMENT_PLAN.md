# EXPERIMENT_PLAN.md

Phase 0 reconstruction for the final MUSE-News / Qwen2.5-7B-Instruct sycophancy mechanism
experiments (recognition-vs-generation gap, causal generation test, memory-integration test,
thesis-wide forgetting-vs-privacy correlation). Written before any new job is run. Source of
truth for examples is the cleaned HIGH_CONFIDENCE_FAILURE audit, not the old noisy selection.

## 0. Canonical source of truth

`mechanistic/experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit/`
  - `clean_selection.json` — full provenance per example (query, memories, both model
    responses, judge scores, manual_audit_reason). **This is the file every new script in
    this experiment must read from.**
  - `CLEAN_RERUN_REPORT.md` — narrative report of the existing teacher-forced result.
  - `audit/manual_transition_audit.csv` — full 27-candidate manual audit
    (HIGH_CONFIDENCE_FAILURE / AMBIGUOUS / LIKELY_JUDGE_NOISE), with the documented
    "task-compliance confound" that drove most exclusions.

Confirmed existing result (verified against `CLEAN_RERUN_REPORT.md` §A, matches user brief
exactly): SatImp L21-27 forward patch +0.138 CI[0.119,0.158] 6/6; SimNPO +0.111
CI[0.077,0.143] 4/4; reverse patch negative; L14-20 comparable. **This is a teacher-forced,
fixed-continuation likelihood contrast — the report itself already flags that free
generation has not been tested on this clean set, and independently ranks "autoregressive
regeneration on the clean set" and "with/without-memory patching" as the top two follow-ups.**
We are executing exactly those two, plus the recognition-probe and macro-correlation
questions the report doesn't address.

### 10 HIGH_CONFIDENCE_FAILURE examples (8 unique `persistbench_id`s, 2 shared across methods)

SatImp (6): `aa71a70f...d71f`, `3ccf8e85...36e2b`, `3c6606c5...985b0`, `b934289e...87a2d`,
`7b1e0198...813873`, `7079a34e...981adde`

SimNPO (4): `2740209d...5bb662`, `aa71a70f...d71f` (shared with SatImp), `e549f564...bfea903d`,
`7079a34e...981adde` (shared with SatImp)

(Full untruncated IDs live in `clean_selection.json`; truncated here only for readability.)

### Matched SAFE→SAFE controls (same file, `clean_selection.json`)

SatImp (6): `085ee466...26ebb`, `860a1058...9cace`, `618ce56a...36a522`, `6c265af3...5194a2`,
`d8e59be4...22ad`, `87081fca...607c3`

SimNPO (4): `67752451...232d`, `085ee466...26ebb` (shared), `9eda9b27...4984a`,
`87081fca...607c3` (shared)

Matching criterion (documented in `clean_selection.md`): greedy nearest-neighbor, no
replacement, on exact BASE judge score → min |Δ base_response_chars| → tie-break
memory_chars → prompt_token_len. Reused as-is; no re-matching needed.

## 1. Checkpoints (verified to exist on disk, 2026-09-23)

| Model | Path |
|---|---|
| BASE | `saves/finetune/muse_news_qwen25_7b_instruct_target` |
| SatImp | `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459` |
| SimNPO | `saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459` |

Source: `MODEL_PATHS` dict in `run_activation_patching_clean.py`. All three directories
confirmed present via `ls`. No stochastic seed is used anywhere in this pipeline: the
teacher-forced scoring is a deterministic forward pass, and generation (Experiments 1 and 3)
uses greedy decoding (temperature 0), so results are reproducible without a seed.

## 2. Layer ranges (0-indexed, canonical)

`L0-6`, `L7-13`, `L14-20`, `L21-27` (from `run_activation_patching_clean.py`, hooks on
`model.model.layers[j]` directly). The older autoregressive script
(`mechanistic/muse_news/muse_news_activation_patching.py`) uses 1-indexed labels (`early=1-7,
early_middle=8-14, middle_late=15-21, late=22-28`) via `layers[index-1]` — **verified by
direct inspection these resolve to the identical 0-indexed layers**, just a different
labeling convention. We standardize all new reporting on the 0-indexed `L14-20`/`L21-27`
labels.

## 3. Decoding settings (for matching original PersistBench generation)

From `persistbench_native/prepare_native_sycophancy_200.py`: `temperature=0.0` (greedy),
`top_p=0.8` (moot under greedy), `max_tokens=96`, `repetition_penalty=1.05`.
**Documented deviation:** the existing autoregressive patching script uses HF `transformers`
generation with no KV cache (donor must be recomputed every step — see §4), not vLLM. Under
greedy decoding this does not change the sampled output, only speed.

## 4. Existing code — what's reused vs. what's new

### Fully reused, no changes

- **Teacher-forced Phase-9 result itself**: already complete and clean
  (`run_activation_patching_clean.py` + `clean_selection.json` + `CLEAN_RERUN_REPORT.md`).
  Not rerun.
- **Autoregressive patching mechanism**: `mechanistic/muse_news/muse_news_activation_patching.py`
  (`ActivationDonor`, `generate()`, `apply_repetition_penalty()`). At every decoding step it
  reruns the donor model from scratch over the recipient's actual generated-so-far sequence
  and patches only the donor's last-position activation into the recipient's current step —
  this is a technically sound solution to the growing-sequence alignment problem (no stale
  full-sequence donor tensor from a diverged trajectory). Both forward and reverse patch
  directions already exist (`--direction` flag). **This satisfies Experiment 1's "critical
  methodological requirement" without new patching machinery.**
- **Legacy local Qwen judge**: `simplified_local_judge_score()` in the same file
  (Qwen2.5-7B-Instruct, JSON `{"score": int}` rubric, ≥3 = FAILURE on a 1-4 scale) — the
  judge used throughout the clean audit, kept for direct comparability.
- **Second judge (Gemma-3)**: a complete, already-built pipeline at
  `thesis/analysis/judge_robustness/` (`gemma_judge.py`, sbatch, comparison scripts). Reused
  by pointing at the new generations; no new judge infra needed.
- **MCQ construction**: `mechanistic/privacy_collapse/persistbench_sycophancy_mcq/common.py`
  (`QUESTION`/`SWAPPED_QUESTION` templates, `build_manifest.build_prompt`). Confirmed
  dataset-agnostic — takes only `memories` + `query`.
- **WITH_MEMORY / NO_MEMORY manifests**: already exist as a paired 1:1 set —
  `native_sycophancy_200_v1.json` vs `native_sycophancy_200_no_memory_v1.json`
  (`mechanistic/experiments/muse_news_sycophancy_paradox/prepare_no_memory_manifest.py`,
  building NO_MEMORY by passing `memories=[]` into the same prompt builder, not a
  text-deletion hack).
- **Prompt-end alignment for NO_MEMORY**: `extract_no_memory_prompt_end.py` already extracts
  hidden states at the last token of the memory-ablated effective prompt, mirroring the
  with-memory extraction in `persistbench_native/extract_prompt_end_hidden_states.py`. This
  is exactly the semantic-position (not raw-index) alignment Experiment 3 needs.
- **Slurm budget precedent**: single `gpu:a180:1`, 120-160G mem, 3-8h wall time per job
  (`run_patching_full.sbatch`, `run_clean_patching.sbatch`,
  `run_muse_news_no_memory_extraction.sbatch`). New jobs sized similarly (small example
  counts, same model).

### New, but thin (glue/selection code, not new methodology)

- **Exp 1 driver**: point `mechanistic/muse_news/muse_news_activation_patching.py`'s case selection at
  `clean_selection.json` (10 treatment + 10 matched controls) instead of the old
  `continuation_cases_v1.json` (9 cases, judge-score-jump selected, includes cross_domain).
  Resolve `prompt_token_ids` per `persistbench_id` from
  `persistbench_native/manifests/native_sycophancy_200_v1.json` (same manifest the clean
  teacher-forced script uses). Existing stored outputs in
  `mechanistic/outputs/muse_news_sycophancy_mechanistic/patching/` are on the wrong (old,
  noisy) example set and cannot be reused for the treatment-set numbers — they must be
  regenerated on the clean set. No new patching/generation code is required, only the
  case-list plug-in.
- **Exp 2 MCQ gap-fill**: existing MCQ manifest
  (`manifests/persistbench_sycophancy_mcq_clear_no_50_v1.json`) covers only 3 of the 8 unique
  HIGH_CONFIDENCE_FAILURE IDs (`aa71a70f...`, `2740209d...`, `3c6606c5...`). The remaining 5
  (`3ccf8e85...`, `b934289e...`, `7b1e0198...`, `7079a34e...`, `e549f564...`) need MCQ probes
  built with the identical template/logic — cheap, since `memories`+`query` are already in
  `clean_selection.json`. Not a new probe design, just applying the existing one to more IDs.
- **Exp 3 within-model memory patching**: no existing script patches WITH_MEMORY↔NO_MEMORY
  representations within the same model. This reuses `ActivationDonor`/`generate()` from the
  Exp-1 pipeline but with donor=NO_MEMORY run / recipient=WITH_MEMORY run (same model
  weights, different prompt), patching at the aligned prompt-end position (and layer ranges
  L14-20/L21-27) rather than BASE-vs-unlearned. This is new orchestration code, built from
  already-existing primitives (no new alignment mechanism).
- **Second-judge wiring**: a small script mirroring `simplified_local_judge_score()`'s
  call pattern but invoking `thesis/analysis/judge_robustness/gemma_judge.py`'s
  scoring function on the new generations.

### New, and requiring real (bounded) compute for Experiment 4 only

No new model training or generation is planned for Experiment 4's core comparison
(MUSE-News vs MUSE-Books, Qwen2.5-7B-Instruct, BASE/SatImp/SimNPO): all four required
numbers (forget metric, PersistBench cross-domain, PersistBench sycophancy) already exist as
computed values in `MUSE_SUMMARY.json` per checkpoint and
`muse_news_category_comparison_validated.json` (News) / README text table (Books — needs
transcription into a CSV, not recomputation). Optional stretch items (TOFU PersistBench
category split, RMU/WGA PersistBench category split) would reuse already-generated raw
outputs and only need a judging/aggregation pass — flagged as optional, not required for the
core H1/H2 questions.

One correction from the reconnaissance: there is **no existing clean join** of forget-quality
× contextual-privacy metrics for the canonical Qwen2.5-7B-Instruct tracks. The one file that
looked like it (`FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv`) is for a different track
(Llama-2-7b MUSE-News) and is marked superseded in the experiment history — it will be
excluded from the main analysis and, if included at all, shown only as a labeled sensitivity
row.

## 5. Jobs actually needed (execution order)

1. **Exp 1 case-selection glue + generation run** (SatImp + SimNPO, 10 treatment + 10
   control examples, conditions A/B/C/D, layer ranges L14-20 and L21-27) — 1 GPU job,
   ~3-4h based on precedent (`run_patching_full.sbatch` budget: `gpu:a180:1`, 160G, 3h;
   likely needs the 8h budget used for the no-memory extraction job since donor recompute
   has no KV cache — will size conservatively).
2. **Exp 1 judging**: legacy Qwen judge (reused function, minutes) + Gemma-3 judge (reused
   pipeline, similar order of a GPU job) + manual inspection of the 10 treatment examples
   (no compute, human/LLM-assisted review of already-generated text).
3. **Exp 1 analysis + STOP for review** before proceeding, per the execution order in the
   brief.
4. **Exp 2 MCQ gap-fill + inference** for the 5 missing unique IDs, reusing existing MCQ
   representation-extraction code — small job, likely shares a GPU job with existing MCQ
   infra (minutes to ~1h).
5. **Exp 3 within-model memory-patching run**: SatImp + SimNPO WITH_MEMORY↔NO_MEMORY, both
   directions, L14-20/L21-27, plus an optional BASE control repeat — 1 GPU job, similar
   budget to Exp 1.
6. **Exp 4 aggregation**: no GPU job; pulls already-computed MUSE-News/MUSE-Books numbers
   into one canonical CSV + 3 plots + correlations. TOFU/RMU/WGA category-split stretch
   items are optional and separately time-boxed.
7. **FINAL_MECHANISTIC_SYNTHESIS.md**.

## 6. Expected compute (order of magnitude)

- Exp 1: 20 cases total (10 treatment + 10 control; each case already belongs to exactly one
  method, SatImp or SimNPO — this count is NOT multiplied by "number of methods" a second time).
  Per case: 2 unpatched generations (A, B) + 2 patch directions (C, D) × 3 layer ranges (L0-6,
  L14-20, L21-27) = 8 generations/case, 160 generations total, each up to 96 tokens with
  no-KV-cache donor recompute. **Actual measured cost** (job 444474, 2026-09-23): 1 GPU
  (a100-80GB), 68 minutes wall-clock for all 160 generations (~200s/case), well under the
  3h budget sized from the smoke test (job 444457, 2 cases in ~13 min including model
  loading). Qwen judging (job 444504): 160 judge calls, 30 minutes. Gemma-3-12b-it second
  judge via vLLM (job 444515): ~10 min server startup + judging, well under its 3h budget.
- Exp 2: <1 GPU-hour (5 new MCQ forward passes + reuse of existing 3).
- Exp 3: 1 GPU, likely similar order of magnitude to Exp 1's actual ~70 min core generation
  time (same 7B models, same no-KV-cache mechanism, same ~10-case scale), plus judging.
- Exp 4: no GPU compute for the core comparison; CPU-only aggregation/plotting.

Total: Exp 1 actually completed in under 2 hours of GPU time across all three jobs, well
within the "no broad new benchmark sweep" constraint — all new compute is scoped to the
existing 10/8-example clean set plus a
handful of MCQ probes.

## 7. Exact examples involved (recap)

8 unique `persistbench_id`s across the 10 treatment (SatImp 6 / SimNPO 4, 2 shared) +
8 unique matched-control `persistbench_id`s across the 10 controls (SatImp 6 / SimNPO 4, 2
shared). No other examples are in scope for Experiments 1-3. Full IDs, memories, queries,
and both models' original responses are already embedded in `clean_selection.json` — new
outputs will cite that file's records by ID rather than duplicating the text.

## 8. Explicit non-goals for this plan (per user brief)

- No broad new benchmark sweep.
- No overwriting of `analysis/activation_patching_clean_audit/*` outputs — all new outputs
  go under this directory (`mechanistic/experiments/muse_news_sycophancy_final_mechanism/`).
- No reuse of the old noisy 9-case `continuation_cases_v1.json` selection for any reported
  treatment-set number.
- No new model training for Experiment 4.
