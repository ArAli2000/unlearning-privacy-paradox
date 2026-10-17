# MUSE-News Sycophancy Mechanism — Final Investigation

**Status: frozen.** This is the final, thesis-ready state of the MUSE-News
sycophancy mechanistic investigation. No new experiments, retraining, or
benchmark regeneration should happen against this directory — it has been
organized for writing the thesis, not for further active research. If a new
question comes up, it belongs in a new experiment directory, not edited into
these results.

## Research question

After SatImp/SimNPO unlearning on MUSE-News (Qwen2.5-7B-Instruct): does the
model's *explicit* recognition of a privacy/anti-sycophancy norm survive, even
in cases where its *free-generation behavior* violates that norm — and, if
stored user context is implicated, is that a causal, unlearning-specific
mechanism or a general property of the model?

## Canonical starting point

Start at `EXPERIMENT_INDEX.md` — it maps the full experiment sequence
(behavioral discovery → manual failure audit → clean teacher-forced patching →
free-generation Experiment 1 → reproducibility diagnostic → Experiment A →
Experiment B → synthesis) with exact file paths and one-sentence results for
each stage. For a citation-ready list of every individual thesis number, use
`THESIS_RESULTS_CHEATSHEET.md`. For the full artifact-by-artifact provenance
classification, use `RESULTS_REGISTRY.csv`.

## Final experiment sequence

1. Behavioral discovery (PrivacyLens stable, PersistBench sycophancy worsens) —
   `mechanistic/experiments/muse_news_sycophancy_paradox/report/FINAL_REPORT.md`
2. Manual failure audit (27 candidates → 10 HIGH_CONFIDENCE_FAILURE) —
   `mechanistic/experiments/muse_news_sycophancy_paradox/audit/` +
   `.../analysis/activation_patching_clean_audit/clean_selection.json`
3. Clean teacher-forced BASE↔unlearned activation patching —
   `.../analysis/activation_patching_clean_audit/CLEAN_RERUN_REPORT.md`
4. Free-generation Experiment 1 (same patch, free generation, two judges) —
   `EXPERIMENT_1_RESULTS.md`
5. Reproducibility diagnostic (why Experiment 1 didn't reproduce every audited
   failure) — `repro_check/REPRO_CHECK_RESULTS.md`
6. **Experiment A** — recognition-vs-behavior gap (explicit MCQ probe) —
   `EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md`
7. **Experiment B** — within-model WITH_MEMORY↔NO_MEMORY patching —
   `EXPERIMENT_B_MEMORY_INTEGRATION.md`
8. **Synthesis** — H1/H2/H3 verdicts — `FOCUSED_THESIS_SYNTHESIS.md`

## Directory map

```
muse_news_sycophancy_final_mechanism/
├── README.md                              <- you are here
├── EXPERIMENT_INDEX.md                    <- main map, start here
├── RESULTS_REGISTRY.csv                   <- every artifact, CANONICAL/SUPPORTING/SUPERSEDED
├── THESIS_RESULTS_CHEATSHEET.md           <- short, citation-ready result list
├── EXPERIMENT_PLAN.md                     <- phase-0 provenance/planning record (not a result)
├── EXPERIMENT_1_RESULTS.md                <- Experiment 1 (free-generation patching)
├── EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md
├── EXPERIMENT_B_MEMORY_INTEGRATION.md
├── FOCUSED_THESIS_SYNTHESIS.md
├── exp1_generation/                       <- Experiment 1 raw generations + judging
├── exp1_analysis/                         <- Experiment 1 per-condition analysis
├── repro_check/                           <- reproducibility diagnostic report + data
├── expA_mcq/                              <- Experiment A data (5 of 8 unique IDs)
├── expB_memory/                           <- Experiment B data (all 10 treatment cases)
├── slurm/                                 <- Experiment 1 sbatch scripts
└── archive/failed_or_superseded/          <- failed SLURM attempts, kept for provenance
```

Upstream canonical artifacts this directory depends on but does **not**
duplicate (left in their original locations — see "Why the directory layout
was not restructured" below):

- `mechanistic/experiments/muse_news_sycophancy_paradox/` — manual audit,
  `clean_selection.json`, clean teacher-forced patching, NO_MEMORY
  manifest/representations.
- `mechanistic/privacy_collapse/persistbench_native/` — WITH_MEMORY manifest
  and prompt-end representations.
- `mechanistic/privacy_collapse/persistbench_sycophancy_mcq/` — the
  pre-existing 50-example MCQ readout (3 of Experiment A's 8 unique IDs).

## Why the directory layout was not restructured

A `01_reproducibility/ … 05_synthesis/` style reorganization was considered
and deliberately **not** applied. Every script in this directory and its
upstream dependencies (`expA_mcq/extract_missing_5.py`,
`expB_memory/run_expB_memory_patch.py`, and the `activation_patching_clean_audit/`
scripts) computes its project root as a fixed number of `.parent`/`.parents[N]`
steps up from `__file__`. Moving any of these files into a new nesting level
would silently break that root computation (or require re-auditing and editing
every script's path logic, which risks changing runnable — if frozen —
experiment code, against this task's explicit "do not change experiment
logic" constraint). Since this is a freeze/cleanup pass, not a refactor, the
existing flat structure was kept and `EXPERIMENT_INDEX.md` +
`RESULTS_REGISTRY.csv` serve as the organizing layer instead. The only files
physically moved were failed SLURM logs with zero code/doc references, into
`archive/failed_or_superseded/`.

## Exact main conclusions

1. Contextual-privacy effects of unlearning are heterogeneous: they worsen for
   MUSE-News sycophancy but not for MUSE-News cross-domain or MUSE-Books, and
   are not uniform across the full PersistBench population even within the
   sycophancy category.
2. MUSE-News contains genuine, manually verified sycophancy failures after
   SatImp/SimNPO unlearning (10 HIGH_CONFIDENCE_FAILURE instances / 8 unique
   PersistBench IDs, out of 27 manually reviewed candidates).
3. All 10/10 genuine failure instances preserve explicit anti-sycophancy
   recognition under an MCQ probe, in both answer orderings — a complete,
   reproducible recognition-behavior gap on every case tested.
4. BASE↔unlearned activation differences causally affect the safe-vs-sycophantic
   continuation preference, both at the teacher-forced level (clean, strong
   effect) and, more weakly and only for SatImp, under free generation itself.
5. User memory/context itself causally affects this preference: injecting a
   memory-conditioned internal state into a memory-free context reliably shifts
   the model toward the sycophantic response, most consistently at layers
   L14–20.
6. That memory-context pathway is also strong in BASE — Experiment B does
   **not** establish that unlearning specifically created or amplified it.
7. Therefore the evidence supports a recognition–behavior gap and a downstream
   behavioral change caused by unlearning, but **not** a simple "privacy
   knowledge was erased" explanation (recognition is intact) and **not** a
   simple "unlearning broke the memory gate" explanation (the memory→behavior
   channel tested here pre-exists in BASE).
