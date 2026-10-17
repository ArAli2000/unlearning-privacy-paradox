# Thesis Results Cheatsheet — MUSE-News Sycophancy Mechanism

Short, citation-ready reference for writing the thesis. For full context see
`EXPERIMENT_INDEX.md`; for provenance/status of every underlying file see
`RESULTS_REGISTRY.csv`.

---

### Behavioral starting point (PrivacyLens vs PersistBench dissociation)

**Result:** PrivacyLens (explicit MCQ recognition): 92.29% (BASE) → 91.89%
(SatImp) / 91.68% (SimNPO), ~stable. PersistBench sycophancy FR@1/2/3: 9.5/12.5/12.5%
(BASE) → 12.0/17.0/17.0% (SatImp), 11.5/15.0/15.0% (SimNPO), worsens at every K,
on a 100%-valid 200-row population.

**Means:** explicit privacy-norm knowledge and contextual generative privacy
behavior move in different directions after unlearning on this specific
dataset/category.

**Does not mean:** this holds for MUSE-News cross-domain (it *improves*) or
MUSE-Books (does not replicate) — the effect is category-and-dataset-specific,
not a general unlearning property.

**Source:**
`mechanistic/experiments/muse_news_sycophancy_paradox/report/FINAL_REPORT.md`

**Suggested section:** Results → Behavioral motivation / case selection.

---

### Manual failure audit

**Result:** 27 candidate SAFE→FAILURE transitions manually reviewed → 10
HIGH_CONFIDENCE_FAILURE, 9 LIKELY_JUDGE_NOISE, 8 AMBIGUOUS. 10 (model, case)
treatment instances = 8 unique PersistBench IDs (SatImp 6, SimNPO 4, 2 shared).

**Means:** the mechanistic experiments below run on a small, manually-verified,
genuine-failure set — not an automatically-thresholded, possibly-noisy one.

**Does not mean:** 10/27 (~37%) is the population-level sycophancy failure rate
— this is a filtered set of clear cases, not a random or representative sample.

**Source:**
`mechanistic/experiments/muse_news_sycophancy_paradox/audit/manual_transition_audit.csv`,
`.../analysis/activation_patching_clean_audit/clean_selection.json`

**Suggested section:** Methods → Case selection.

---

### Clean teacher-forced BASE↔unlearned activation patching

**Result:** forward patch (donor=BASE, recipient=unlearned), L21-27: SatImp
+0.138 mean shift, CI[0.119,0.158], 6/6 cases in predicted direction; SimNPO
+0.111, CI[0.077,0.143], 4/4. Reverse patch (donor=unlearned, recipient=BASE),
L21-27: SatImp -0.141, CI[-0.161,-0.123], 6/6; SimNPO -0.113,
CI[-0.144,-0.078], 4/4 — mirrors the forward result with the opposite sign.
L14-20 comparable magnitude to L21-27 in both directions.

**Means:** at the teacher-forced (fixed-continuation likelihood) level,
BASE→unlearned activation patching shifts the fixed-continuation preference
toward the BASE/safe response; the reverse direction (unlearned activations
substituted into BASE) shifts BASE's preference toward the sycophantic
response by a comparable margin. This does not by itself identify *what*
representational difference is doing this (not shown to be memory-specific —
that is Experiment B's separate question) or guarantee it would repair actual
free generation (see Experiment 1 below).

**Does not mean:** this necessarily reproduces in free generation (see
Experiment 1 below — it only partially does), that it is specific to memory
context (see Experiment B — this is a BASE-vs-unlearned weight-space
comparison, a different axis), or that it identifies the mechanism/circuit
responsible (the patch is coarse and whole-model-state).

**Source:**
`mechanistic/experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit/CLEAN_RERUN_REPORT.md`

**Suggested section:** Results → Mechanistic causal evidence (teacher-forced).

---

### Free-generation Experiment 1

**Result:** only 3/6 SatImp and 0/4 SimNPO treatment cases reproduce as a
FAILURE under fresh greedy free generation at all. Of the 3 SatImp cases that
do fail, 1 is confidently (both-judges-agreed) repaired by forward-patching at
L14-20. Judge agreement (Qwen vs Gemma-3) is only 59%.

**Means:** activation patching causally alters actual free-generation
behavior in at least one clean, bidirectional, both-judges-agreed example
(`aa71a70f`, SatImp, L14-20) — real positive causal evidence, not just a
teacher-forced artifact.

**Does not mean:** a consistent, judge-robust repair effect across the full
SatImp treatment set, any repair effect for SimNPO, or that L21-27 is a
cleaner intervention than L14-20 (the opposite appears true — L21-27 can
approach donor-output copying). This is existence-proof-level evidence, not a
population-level effect.

**Source:**
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/EXPERIMENT_1_RESULTS.md`

**Suggested section:** Results → Mechanistic causal evidence (free generation) +
Limitations.

---

### Reproducibility diagnostic

**Result:** a fresh rerun of the literal original vLLM generation pipeline
(same checkpoints, same settings, same tokens) matches its own July results
only 55% of the time; Experiment 1's HF approximation matches 70% of the time.

**Means:** the non-reproduction problem in Experiment 1 is predominantly
genuine model/environment behavioral instability (vLLM/CUDA/kernel drift since
July, compounding with real stochasticity), not a bug in how Experiment 1's
generation code was written.

**Does not mean:** Experiment 1's HF pipeline is bug-free in general, or that
sycophancy classifications should be trusted as single frozen labels going
forward — the diagnostic's own recommendation is to treat failure as
probabilistic across repeated generations.

**Source:**
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/repro_check/REPRO_CHECK_RESULTS.md`

**Suggested section:** Methods → Limitations / Threats to validity.

---

### Recognition–behavior gap (Experiment A)

**Result:** 10/10 (100%) genuine sycophancy-failure (model, case) instances —
every case where SatImp or SimNPO actually committed the failure in free
generation — robustly (both MCQ answer-orderings) answer the explicit
anti-sycophancy MCQ correctly.

**Means:** explicit, verbalizable norm recognition is preserved despite the
observed behavioral failure, in every genuine failure case tested — a clean,
unanimous dissociation between "knowing" and "doing."

**Does not mean:** the effect prevalence is 100% across the entire benchmark
(n=8 unique cases is a small, curated worst-case subset) or that this
generalizes to other datasets/categories beyond MUSE-News sycophancy.

**Source:**
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md`

**Suggested section:** Results → Recognition vs. behavior. (Supports H2.)

---

### Within-model memory-context patching (Experiment B)

**Result:** injecting a WITH_MEMORY prompt-end hidden state into a NO_MEMORY
context shifts preference toward the sycophantic response most consistently at
L14-20 (BASE 10/10 cases, SatImp 5/6, SimNPO 2/4 — small n); the reverse
(ablating memory) direction is weak/inconsistent everywhere.

**Means:** stored user context is causally integrated into the model's
internal state at a specific position/layer band, and this measurably affects
the safe/sycophantic balance — a real, if partial (small effect size relative
to the full with/without-memory gap), causal channel.

**Does not mean:** this channel is unlearning-specific. BASE shows the effect
at least as strongly as SatImp and more consistently than SimNPO, so this
experiment does **not** show unlearning created or amplified this particular
memory-integration pathway.

**Source:**
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/EXPERIMENT_B_MEMORY_INTEGRATION.md`

**Suggested section:** Results → Memory/context integration mechanism.
(Partially supports H3 — supports the "context integration is causal" half,
not the "unlearning changed it" half.)

---

### Final hypothesis verdicts

| Hypothesis | Verdict |
|---|---|
| H1: unlearning generally harms contextual privacy | PARTIALLY SUPPORTED — real, causal harm on this subset; "generally" not established |
| H2: unlearning can preserve explicit recognition while changing behavior | SUPPORTED — 10/10, unanimous |
| H3: unlearning changes how stored context influences generation | PARTIALLY SUPPORTED — context integration is causal; unlearning-specificity of *this* channel is not shown |

**Source:**
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/FOCUSED_THESIS_SYNTHESIS.md`

**Suggested section:** Discussion → Hypothesis evaluation.
