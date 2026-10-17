# Thesis Writing Plan — MUSE-News Sycophancy Mechanism

**Purpose:** master blueprint for writing the thesis from the now-frozen
results. This file does not contain thesis prose. It maps every planned
section to canonical evidence, so writing can proceed chapter-by-chapter
without re-deriving anything or re-opening the underlying experiments.

**Canonical sources used to build this plan** (all already frozen, none
re-run): `README.md`, `EXPERIMENT_INDEX.md`, `RESULTS_REGISTRY.csv`,
`THESIS_RESULTS_CHEATSHEET.md`, `FOCUSED_THESIS_SYNTHESIS.md`,
`EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md`,
`EXPERIMENT_B_MEMORY_INTEGRATION.md`,
`.../activation_patching_clean_audit/CLEAN_RERUN_REPORT.md`,
`EXPERIMENT_1_RESULTS.md`, `repro_check/REPRO_CHECK_RESULTS.md`, and the
behavioral discovery reports
(`mechanistic/experiments/muse_news_sycophancy_paradox/report/FINAL_REPORT.md`,
`mechanistic/outputs/benchmark_paradox/FINAL_REPORT.md`) — all in this
directory (or its `RESULTS_REGISTRY.csv`-indexed neighbors), all classified
CANONICAL or SUPPORTING.

---

## 1. The thesis story in plain language

Machine unlearning does not have one universal effect on contextual privacy:
across datasets and PersistBench categories, the effect on privacy-relevant
behavior is heterogeneous, worsening in some settings and improving or
staying flat in others. Focusing on the one setting where a genuine
degradation was found and manually verified — MUSE-News, PersistBench
sycophancy, after SatImp/SimNPO unlearning — 10 clear, hand-audited cases
exist where the unlearned model validates a user's stored belief instead of
answering independently. Critically, none of these failures trace to a loss
of the model's explicit knowledge: every one of the 10 manually verified
failure instances still correctly identifies the anti-sycophancy norm when
asked directly, in both MCQ answer orderings. At the representational level,
swapping BASE and unlearned-model activations into each other — in both
directions — causally and consistently shifts the recipient's preference
toward whichever donor's behavior it received (unlearned-donor activations
pull BASE's preference toward the sycophantic continuation; BASE-donor
activations pull the unlearned model's preference back toward the safe one),
and stored user context itself — independent of which model weights are used —
causally shifts that same preference when patched into an otherwise
memory-free prompt. However, this second, context-driven channel is not
shown to be specific to unlearning: BASE exhibits it at least as strongly as
the unlearned models do, so the data does not support the claim that
unlearning specifically created or strengthened a memory-integration
pathway. Taken together, the best-supported interpretation is that
unlearning, in this case, changed how existing knowledge and contextual
signals get translated into downstream generated behavior — not that it
erased privacy-relevant knowledge, and not that it broke a specific,
newly-identified memory mechanism.

---

## 2. Proposed final research questions

### RQ1 — What effect does machine unlearning have on contextual privacy behavior?

- **Exact wording:** *"How does unlearning (SatImp, SimNPO) affect
  contextual, free-generation privacy-relevant behavior, as measured by
  PersistBench, across datasets and categories?"*
- **Why it matters:** frames the empirical starting point and motivates why
  MUSE-News sycophancy specifically was chosen as the mechanistic case study,
  rather than assuming unlearning has a single, uniform behavioral signature.
- **Experiments that answer it:** the behavioral discovery pass
  (`mechanistic/outputs/benchmark_paradox/FINAL_REPORT.md`) and its MUSE-News
  re-derivation (`.../muse_news_sycophancy_paradox/report/FINAL_REPORT.md`).
- **Short answer (current evidence):** heterogeneous. PersistBench sycophancy
  on MUSE-News worsens at every FR@K for both methods; PersistBench
  cross-domain on the same dataset *improves* for both methods; MUSE-Books
  sycophancy does not replicate the MUSE-News degradation at all. There is no
  single directional effect that holds across settings.

### RQ2 — Can unlearning change contextual privacy behavior while explicit privacy/norm recognition stays intact?

- **Exact wording:** *"On cases where SatImp/SimNPO demonstrably produce a
  sycophantic free-generation failure, does the same model still correctly
  recognize the underlying anti-sycophancy norm when asked explicitly?"*
- **Why it matters:** this is the thesis's sharpest, most conservative,
  best-evidenced claim — it distinguishes a *behavioral* failure from a
  *knowledge* failure, which has different implications for how such
  failures should be understood and mitigated.
- **Experiments that answer it:** the manual failure audit (case validity),
  Experiment A (the MCQ recognition probe).
- **Short answer (current evidence):** yes. 10/10 (100%) of the manually
  verified genuine failure instances robustly (both MCQ orderings) answer the
  explicit anti-sycophancy question correctly, on the identical
  (memories, query) pair that produced the free-generation failure.

### RQ3 — What internal, causally-testable mechanisms are associated with the recognition–behavior gap?

- **Exact wording:** *"Do BASE-vs-unlearned internal representation
  differences causally affect the model's preference between a safe and a
  sycophantic continuation, at the teacher-forced level and under free
  generation?"*
- **Why it matters:** moves from correlational observation (RQ1, RQ2) to
  causal evidence, and is honest about the difference between teacher-forced
  and free-generation evidence rather than treating them as interchangeable.
- **Experiments that answer it:** clean teacher-forced activation patching,
  free-generation Experiment 1, the reproducibility diagnostic (as a
  methodological qualifier on Experiment 1).
- **Short answer (current evidence):** yes at the teacher-forced level
  (strong, consistent effect, both methods). Only partially transfers to free
  generation: one clean, both-judges-agreed, bidirectional causal example for
  SatImp; no testable evidence either way for SimNPO (its treatment cases
  don't reproduce as failures under fresh free generation at all); the
  reproducibility diagnostic shows this gap is driven mainly by
  generation-environment instability, not an Experiment-1-specific bug.

### RQ4 — Is stored user context causally involved in the sycophantic preference, and is that specific pathway altered by unlearning?

- **Exact wording:** *"Does patching a memory-conditioned internal state into
  an otherwise memory-free prompt (and vice versa), within the same model,
  causally shift the safe-vs-sycophantic preference — and if so, is this
  channel specific to, or amplified by, unlearning?"*
- **Why it matters:** tests a *different* causal axis than RQ3 (context/prompt
  content vs. model weights) and is the question most at risk of
  being overstated — must be answered carefully.
- **Experiments that answer it:** Experiment B.
- **Short answer (current evidence):** stored context is causally involved
  (injecting a memory-conditioned state into a memory-free context shifts
  preference toward the sycophantic continuation, most consistently at
  L14–20). But the pathway is **not shown to be unlearning-specific** — BASE
  exhibits the same effect at least as strongly as SatImp and more
  consistently than SimNPO. The honest answer to the second half of RQ4 is
  "not established," not "no."

*(Note: RQ3 and RQ4 deliberately keep the BASE-vs-unlearned weight-space
causal axis and the memory-context causal axis as two separate questions,
per the constraint to keep these effects conceptually distinct — they use
different patching designs, different case sets in spirit even though the
same 10 cases, and answer different mechanistic questions.)*

---

## 3. Final hypotheses and verdicts

| Hypothesis | Verdict | Evidence | Important caveat |
|---|---|---|---|
| **H1**: "Machine unlearning generally degrades contextual privacy." | **NOT SUPPORTED AS A GENERAL CLAIM** — effects are heterogeneous | PersistBench sycophancy worsens on MUSE-News (both methods, every FR@K); PersistBench cross-domain *improves* on the same dataset; MUSE-Books sycophancy does not replicate the degradation at all | A real, causally-verified degradation exists in one specific dataset/category combination — do not read "not supported as general" as "no effect exists anywhere." |
| **H2**: "Machine unlearning can preserve explicit privacy recognition while changing contextual privacy behavior." | **SUPPORTED** | Experiment A: 10/10 (100%) genuine failure instances robustly answer the explicit anti-sycophancy MCQ correctly | n = 8 unique cases (10 model-case instances) is a small, curated worst-case subset, not a random sample — the *dissociation* is well-evidenced, its *prevalence rate* across the full benchmark is not established. |
| **H3**: "In the MUSE-News sycophancy case, unlearning changes how stored user context influences generation." | **NOT SUPPORTED AS AN UNLEARNING-SPECIFIC CLAIM** — context integration is causal, but its unlearning-specificity is not established | Experiment B: reverse (inject-memory) direction shifts preference toward sycophantic most consistently at L14–20 (BASE 10/10, SatImp 5/6, SimNPO 2/4) | BASE shows the tested channel **at least as strongly** as SatImp and **more consistently** than SimNPO. Report as: "memory/context integration is causally implicated in the safe/sycophantic balance; this experiment does not establish that unlearning altered that specific channel." Do not claim unlearning "broke" or "strengthened" a memory gate. |
| **H1-teacher-forced** (supporting, not a headline hypothesis): "BASE-vs-unlearned internal representation differences causally shift the safe-vs-sycophantic preference." | **SUPPORTED at the teacher-forced level; partially supported under free generation** | Clean patching, forward (donor BASE→recipient unlearned) at L21-27: SatImp +0.138 CI[0.119,0.158] 6/6, SimNPO +0.111 CI[0.077,0.143] 4/4; mirrored by reverse (donor unlearned→recipient BASE): SatImp -0.141 CI[-0.161,-0.123] 6/6, SimNPO -0.113 CI[-0.144,-0.078] 4/4. Free generation (Exp 1): 1 confident bidirectional SatImp example; SimNPO untestable (no reproducing failures) | Teacher-forced and free-generation evidence must be reported as separate strength tiers, not conflated — see §5's "what teacher forcing does and does not establish." This patches the whole BASE-vs-unlearned model state, not a memory-specific pathway — do not read it as evidence about *memory integration specifically* (that is Experiment B's separate, and separately inconclusive, question). |

---

## 4. Final chapter structure

The project's actual shape — one behavioral discovery pass across many
datasets, narrowing to one deeply-audited mechanistic case study with four
distinct evidence types (recognition, teacher-forced patching, free
generation, memory-context patching) plus an explicit reproducibility
detour — argues for a structure that separates *behavioral* from
*mechanistic* evidence as two full chapters, with the recognition-behavior
gap pulled out as its own short, high-impact chapter rather than buried
inside "mechanistic analysis." Proposed structure:

1. **Introduction**
   - *Purpose:* motivate the question (does unlearning create privacy side
     effects?), state the thesis's actual contribution up front (see §10),
     preview the heterogeneous-effects + recognition-behavior-gap story from
     §1.
   - *Subsections:* Motivation; Thesis statement / contributions preview;
     Roadmap.
   - *Evidence:* none directly — this is framing only, written last (see
     §11).
   - *Not repeated here:* no numbers, no tables — save all evidence for
     Results.

2. **Background / Related Work**
   - *Purpose:* situate machine unlearning (SatImp, SimNPO, MUSE benchmark),
     PersistBench/PrivacyLens as behavioral privacy benchmarks, and prior
     mechanistic-interpretability patching methodology.
   - *Subsections:* Machine unlearning methods and evaluation; MUSE-News /
     MUSE-Books; PersistBench (sycophancy, cross-domain) and PrivacyLens;
     Activation patching as a causal-analysis tool.
   - *Evidence:* none from this project — literature only.
   - *Not repeated here:* do not preview this project's specific numbers.

3. **Research Questions and Experimental Design**
   - *Purpose:* state RQ1–RQ4 (§2) formally, explain why the MUSE-News
     sycophancy case was selected (heterogeneity discovery →
     narrowing), and give the overall experimental pipeline (manual audit →
     clean selection → teacher-forced patching → free-generation → recognition
     probe → memory patching).
   - *Subsections:* RQ1–RQ4; Case selection rationale (why MUSE-News
     sycophancy, why not cross-domain or MUSE-Books); Experimental pipeline
     overview (a single diagram, see §6).
   - *Evidence:* the manual audit's existence and case counts (10
     HIGH_CONFIDENCE_FAILURE / 27 candidates), stated as methodology, not
     results.
   - *Not repeated here:* no outcome numbers (FR@K, patching shifts, MCQ
     results) — this chapter is about *what was done*, not *what was found*.

4. **Behavioral Effects of Machine Unlearning on Contextual Privacy** (answers RQ1)
   - *Purpose:* establish the heterogeneous-effects finding with the full
     cross-dataset/cross-category picture.
   - *Subsections:* PrivacyLens stability; PersistBench sycophancy
     degradation (MUSE-News); PersistBench cross-domain (MUSE-News,
     improvement); MUSE-Books contrast (non-replication); synthesis —
     heterogeneity, not uniform harm.
   - *Evidence:* §5 "Behavioral overview" content below.
   - *Not repeated here:* no MCQ recognition-probe results (that's Ch. 5), no
     patching results (Ch. 6).

5. **Recognition–Behavior Gap** (answers RQ2) — kept as its own chapter
   given it is the thesis's cleanest, most defensible result and deserves
   to stand alone rather than be a subsection of a longer mechanistic
   chapter.
   - *Purpose:* present the manual audit as the bridge from Ch. 4's
     aggregate numbers to individual verified cases, then the MCQ recognition
     result.
   - *Subsections:* From aggregate behavior to individual cases (manual
     audit); Explicit recognition probe design; Result — 10/10; Example
     cases (2 qualitative examples).
   - *Evidence:* §5 "Recognition evidence" content below.
   - *Not repeated here:* do not re-derive or restate the aggregate FR@K
     numbers from Ch. 4 beyond a one-line callback; do not introduce
     patching results here.

6. **Mechanistic Analysis** (answers RQ3, RQ4)
   - *Purpose:* the causal evidence chapter — kept internally split into
     three clearly labeled, non-conflated evidence types.
   - *Subsections:* 6.1 Clean teacher-forced activation patching
     (BASE↔unlearned); 6.2 Free-generation Experiment 1 (same axis, does it
     transfer to actual generation) — including the reproducibility
     diagnostic as a short methodological subsection *inside* 6.2, not its
     own chapter; 6.3 Experiment B — within-model memory/context patching (a
     different causal axis); 6.4 Cross-cutting observation: the two patching
     axes (weights vs. context) do not point to the same layer range, and
     this should not be silently smoothed over (see §9 "conflicts to flag").
   - *Evidence:* §5's "Teacher-forced causal patching," "Free-generation
     Experiment 1," "Reproducibility diagnostic," and "Experiment B" content
     below.
   - *Not repeated here:* recognition results (Ch. 5) should only be
     referenced, not re-presented.

7. **Discussion**
   - *Purpose:* synthesize Ch. 4–6 into the hypothesis verdicts (§3),
     interpret what "translation of knowledge into behavior" plausibly means
     given the evidence, and explicitly discuss the layer-range tension
     between 6.1/6.2 and 6.3.
   - *Subsections:* Answering RQ1–RQ4; Hypothesis table; What the evidence
     does and does not support; Alternative interpretations considered and
     why they're not preferred.
   - *Evidence:* synthesizes, does not introduce new numbers.
   - *Not repeated here:* limitations belong in Ch. 8, not here (a short
     pointer is fine, full treatment is not).

8. **Limitations**
   - *Purpose:* see §9 below for the full blueprint.
   - *Subsections:* per-limitation, grouped by which RQ/claim they bound.
   - *Evidence:* n/a — qualifies evidence already presented.

9. **Conclusion**
   - *Purpose:* restate contributions (§10) and the one-paragraph plain-English
     summary (§12), close.
   - *Subsections:* Summary of findings; Contributions; Future work.
   - *Evidence:* none new.

---

## 5. Detailed Results chapter map

Numbers below are quoted from canonical sources; do not round further or
restate with different precision than the source. Where a source uses
"cosine 0.937/0.938," write "highly aligned (cosine 0.937/0.938)," never
"unchanged" or "identical."

### 5.1 Behavioral overview (→ Chapter 4)

| Field | Content |
|---|---|
| **Question answered** | RQ1 — what is the aggregate behavioral effect of unlearning on contextual privacy, across settings? |
| **Canonical source(s)** | `mechanistic/experiments/muse_news_sycophancy_paradox/report/FINAL_REPORT.md` (primary, re-derived and matching); `mechanistic/outputs/benchmark_paradox/FINAL_REPORT.md` (upstream discovery context) |
| **Exact result(s)** | PrivacyLens: 92.29% (BASE) → 91.89% (SatImp) / 91.68% (SimNPO), representation direction cosine to BASE **0.937/0.938** (highly aligned, not identical). PersistBench sycophancy FR@1/2/3: 9.5/12.5/12.5% (BASE) → 12.0/17.0/17.0% (SatImp), 11.5/15.0/15.0% (SimNPO) — worsens at every K, both methods, on a 100%-valid 200-row population (zero generations excluded by the collapse/gibberish validator). PersistBench cross-domain FR@1: 3.5% → 2.0%/1.5% — *improves*. MUSE-Books sycophancy: improves for both methods (does not replicate); MUSE-Books PrivacyLens cosine 0.991 (even more highly aligned, but uninformative alone without a corresponding PersistBench degradation). |
| **Suggested table/figure** | **Table 1** — one row per (dataset, category, model): PrivacyLens %, PersistBench FR@1/2/3, direction cosine. Columns: MUSE-News sycophancy, MUSE-News cross-domain, MUSE-Books sycophancy. This does not currently exist as a single assembled table — must be built (data exists, assembly does not). See §6. |
| **Interpretation** | No uniform directional effect of unlearning on contextual privacy; the sycophancy/MUSE-News combination is the one setting selected for deep mechanistic follow-up specifically *because* it showed a consistent, valid-generation, both-methods degradation — not because it's representative. |
| **Limitations** | Judge is the legacy local Qwen2.5-7B-Instruct judge throughout, not the canonical PersistBench Kimi-K2 judge — this caveat applies to every PersistBench percentage in this section and should be stated once, prominently, rather than per-number. |
| **Transition** | "Having established that this specific setting shows a real, valid, both-methods degradation, we now ask: which individual cases drive it, and are they genuine sycophancy failures?" → Ch. 5. |

### 5.2 Recognition evidence (→ Chapter 5)

| Field | Content |
|---|---|
| **Question answered** | RQ2 — does explicit recognition survive alongside the behavioral failure? |
| **Canonical source(s)** | Manual audit: `.../muse_news_sycophancy_paradox/audit/manual_transition_audit.csv`, `.../analysis/activation_patching_clean_audit/clean_selection.json`. Recognition probe: `EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md`, `expA_mcq/missing5_readout.csv`, `mechanistic/privacy_collapse/persistbench_sycophancy_mcq/analysis/mcq_readout_per_example.csv`. |
| **Exact result(s)** | 27 candidate transitions manually reviewed → 10 HIGH_CONFIDENCE_FAILURE / 9 LIKELY_JUDGE_NOISE / 8 AMBIGUOUS. 10 (model, case) treatment instances = 8 unique PersistBench IDs (SatImp 6, SimNPO 4, 2 shared). Explicit MCQ probe (both answer orderings, controlling for position bias) on the identical (memories, query) pair: **10/10 (100%)** robustly answer the anti-sycophancy question correctly. |
| **Suggested table/figure** | **Table 2** — the 10-row (model, case) recognition table already assembled in `EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md` (persistbench_id, method, unlearned model, MCQ robust-correct?) — exists, needs porting into thesis table format. **Figure 1** — a small conceptual diagram: same (memories, query) → two divergent paths (free generation → sycophantic; explicit MCQ → correct) for one example case (`aa71a70f`, football-strategy case, or `e549f564`, biodynamic-farming case — both already written up with quotes in the Experiment A report). Does not exist — must be created (diagram, not a data plot). |
| **Interpretation** | The failure is behavioral/generative, not a loss of declarative/verbalizable knowledge of the anti-sycophancy norm — a genuine, complete (on every case tested) recognition-behavior dissociation. |
| **Limitations** | n = 8 unique cases is a small, deliberately curated worst-case subset; 100% establishes the dissociation is real and reproducible wherever it was tested, not its prevalence rate across the full 200-example benchmark. |
| **Transition** | "If explicit knowledge survives, what internal, causally-testable difference does account for the behavioral change? We turn first to BASE-vs-unlearned representation differences." → Ch. 6.1. |

### 5.3 Teacher-forced causal patching (→ Chapter 6.1)

| Field | Content |
|---|---|
| **Question answered** | RQ3 (teacher-forced half) — do BASE-vs-unlearned representation differences causally shift the safe-vs-sycophantic preference, at the level of fixed-continuation likelihood? |
| **Canonical source(s)** | `.../activation_patching_clean_audit/CLEAN_RERUN_REPORT.md`, `clean_per_example_shifts.csv`, `clean_activation_patching_summary.csv`. |
| **Exact result(s)** | Clean, manually-audited 10-case set. Two patch directions, named by donor→recipient: **forward (fwd)** = donor BASE → recipient unlearned (SatImp/SimNPO); **reverse (rev)** = donor unlearned → recipient BASE. Forward, L21-27: SatImp +0.138 mean shift, CI[0.119,0.158], 6/6 cases in predicted direction; SimNPO +0.111, CI[0.077,0.143], 4/4. Reverse, L21-27: SatImp -0.141, CI[-0.161,-0.123], 6/6; SimNPO -0.113, CI[-0.144,-0.078], 4/4 — mirrors the forward result with the opposite sign, as expected from the donor's identity. L14-20 comparable magnitude to L21-27 in both directions; L0-6/L7-13 weaker (roughly half the L14-20/L21-27 magnitude). |
| **Suggested table/figure** | **Figure 2** — mean shift ± CI by layer range (L0-6/L7-13/L14-20/L21-27), one line/point-range per method (SatImp, SimNPO), forward direction only (donor BASE→recipient unlearned; reverse can be a one-line callout, not its own panel). A version of this likely already exists as `.../activation_patching_clean_audit/plots/clean_per_example_shifts.png` — check and adapt rather than regenerate from scratch if the existing plot already has this shape. |
| **Interpretation** | Strong, consistent, both-methods causal evidence *at the teacher-forced level*: replacing the recipient model's L14-27 decoder outputs with the donor model's outputs shifts the recipient's relative preference in the direction predicted by the donor's identity — BASE-donor activations pull the unlearned model's preference toward the safe continuation; unlearned-donor activations pull BASE's preference toward the sycophantic one. This shows that *some* BASE-vs-unlearned representational difference at these layers is causally sufficient to move the preference; it does not by itself identify *what* that difference is (not shown to be memory-integration-specific — that is Experiment B's separate question) or whether it is unique to genuine-failure cases (the matched-control comparison in the canonical report supports failure-specificity for SatImp only; SimNPO's matched controls show a nearly-as-large shift, so this is not established for SimNPO). |
| **Limitations** | Teacher-forced/fixed-continuation likelihood is not the same claim as "this causally changes what the model would actually generate" — that is a separate, weaker claim tested next. Must not present this result as free-generation evidence. |
| **Transition** | "Teacher-forced evidence establishes the representational difference is causally sufficient to shift a likelihood contrast between two fixed texts — but does it change what the model actually generates, unconstrained?" → Ch. 6.2. |

### 5.4 Free-generation Experiment 1 (→ Chapter 6.2, kept clearly secondary)

| Field | Content |
|---|---|
| **Question answered** | RQ3 (free-generation half) — does the same patching axis causally change actual, unconstrained free-generation behavior? |
| **Canonical source(s)** | `EXPERIMENT_1_RESULTS.md`, `exp1_analysis/exp1_transition_rows.csv`, `exp1_analysis/exp1_side_by_side.json`. |
| **Exact result(s)** | Only 3/6 SatImp and 0/4 SimNPO treatment cases reproduce as FAILURE (score ≥3) under fresh greedy free generation of the unpatched unlearned model at all. Of the 3 SatImp cases that do fail: 1 confidently (both-judges-agreed) repaired at L14-20 (`aa71a70f`); L21-27 apparent repairs are judge-disputed and one is a byte-identical donor-output copy, not a graded blend. SimNPO: no forward-patch repair claim testable (no reproducing failures to repair); one reverse-patch case (`7079a34e`) supports the hypothesis. Judge agreement (Qwen vs. Gemma-3) only 59% overall (94/160), asymmetric (Gemma calls FAILURE where Qwen calls SAFE in 58 cases vs. the reverse in 8). |
| **Suggested table/figure** | No standalone figure recommended — the SatImp/SimNPO repair-outcome counts fit as a compact table (methods × layer range × outcome category) or, more economically, as 2–3 sentences plus the one worked example (`aa71a70f`, both directions) already written up in `EXPERIMENT_1_RESULTS.md` §5. Do not build a new plot for this — keep this subsection visually light, consistent with its secondary-evidence status. |
| **Interpretation** | Existence-proof-level, not population-level, causal evidence for free generation: real (one clean bidirectional example), but far weaker and narrower than the teacher-forced result. Do not claim a "consistent, judge-robust repair effect" — the source report explicitly forbids this framing. |
| **Limitations** | Judge disagreement; SimNPO untestable; small n even before the non-reproduction problem. This entire subsection's evidentiary weight should be explicitly downgraded relative to 6.1 in the prose. |
| **Transition** | "Before drawing conclusions from Experiment 1's partial non-reproduction, it must be established whether this reflects a pipeline defect or genuine behavioral instability." → reproducibility diagnostic (kept as a subsection here, not a separate chapter). |

**Reproducibility diagnostic** (subsection within 6.2, per user instruction not to let it dominate):

| Field | Content |
|---|---|
| **Canonical source** | `repro_check/REPRO_CHECK_RESULTS.md` |
| **Exact result** | A fresh rerun of the literal original vLLM generation pipeline (same checkpoints, same settings, same tokens) matches its own frozen July results only **55%** of the time (11/20 model-case pairs); Experiment 1's HF approximation matches **70%** of the time (14/20). |
| **Interpretation** | The non-reproduction problem in §5.4 is predominantly generation-environment/behavioral instability (vLLM/CUDA/attention-kernel drift since the original July run, compounding with genuine model stochasticity), **not primarily an Experiment-1-specific HF-vs-vLLM implementation bug** — since the "exact" original pipeline reproduces itself even less reliably than Experiment 1's approximation does. |
| **Why this changes interpretation of free-generation results generally** | Any single frozen free-generation label (including the ones that originally fed the manual audit) should be read as one sample of a noisier underlying process, not a fixed ground truth — this is a general caveat on free-generation evidence in this thesis, not just on Experiment 1. |
| **Keep it short** | 1 short paragraph + the 55%/70% numbers is sufficient; do not reproduce the full per-case table from the source report in the thesis body (it can go in an appendix if desired). |

### 5.5 Experiment B — memory/context patching (→ Chapter 6.3)

| Field | Content |
|---|---|
| **Question answered** | RQ4 — is stored context causally involved, and is that specific pathway altered by unlearning? |
| **Canonical source(s)** | `EXPERIMENT_B_MEMORY_INTEGRATION.md`, `expB_memory/expB_scores.csv`, `expB_memory/expB_provenance.json`. |
| **Exact result(s)** | Baseline (unpatched) gap: with-memory teacher-forced safe-minus-sycophantic margin is substantially lower than without-memory, in nearly every case/model (e.g. SatImp `aa71a70f`: +0.11 with memory vs. +0.69 without). Reverse (inject WITH_MEMORY state into NO_MEMORY context) direction, at L14-20: BASE 10/10 cases shift toward sycophantic, SatImp 5/6, SimNPO 2/4 (small n). At L21-27 the effect is much less consistent for every model (BASE drops to 5/10). Forward (ablate memory) direction: weak and inconsistent everywhere (e.g. SatImp only 2/6 cases positive at either layer range). |
| **Suggested table/figure** | **Table 3** — mean shift + fraction-in-predicted-direction, rows = (model × layer range), columns = forward_shift / reverse_shift — essentially the two tables already built in `EXPERIMENT_B_MEMORY_INTEGRATION.md` §"Result 1"/"Result 2," merged into one. Exists as markdown tables in the source report; needs porting/reformatting only. |
| **Interpretation** | Stored context is causally implicated in the safe/sycophantic balance via at least one identifiable position/layer channel (L14-20, reverse direction). **The channel is not shown to be unlearning-specific** — BASE's effect is at least as strong (10/10) as SatImp's (5/6) and considerably stronger/more consistent than SimNPO's (2/4, small n). |
| **Limitations** | Single-position patch only (prompt-end token), not full-sequence — recovered effect size (~0.02–0.05 log-prob-margin units) is small relative to the full unpatched with/without-memory gap (~0.4–0.9 units), implying the effect is also carried elsewhere (e.g. distributed across memory-block token positions) not captured by this design. SimNPO's n=4 is small; the 2/4 result should not be treated with the same confidence as BASE's 10/10 or SatImp's 5/6. |
| **Transition** | Last results subsection → Discussion (Ch. 7), where 6.1's L21-27-strongest finding and 6.3's L14-20-strongest finding must be explicitly reconciled/flagged rather than merged (see §9 below). |

---

## 6. Figures and tables (final list — 7 items, none regenerated yet)

| # | Title | Purpose | Source data | Structure | Thesis location | Status |
|---|---|---|---|---|---|---|
| 1 | Cross-setting behavioral effect summary | Show heterogeneity: unlearning's effect differs by dataset/category | `paradox/report/FINAL_REPORT.md` numbers (PrivacyLens %, PersistBench FR@1/2/3, cosine) for MUSE-News sycophancy, MUSE-News cross-domain, MUSE-Books sycophancy | Table, one row per (dataset, category), columns = BASE/SatImp/SimNPO PersistBench FR@1/2/3 + PrivacyLens % + cosine | Ch. 4 | **Must be assembled** (all numbers exist, no single table currently holds them together) |
| 2 | MUSE-News sycophancy FR@K bar comparison | Visualize the one degradation that was selected for deep follow-up | Same source as #1, MUSE-News sycophancy row only | Grouped bar chart, x=FR@1/2/3, groups=BASE/SatImp/SimNPO | Ch. 4 | **Must be generated** (no existing standalone plot of this exact shape was found) |
| 3 | Recognition-vs-behavior gap table | Present the 10/10 result plainly | `EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md` table | Table, one row per (persistbench_id, method, unlearned model), column = MCQ robust-correct (✅) | Ch. 5 | **Exists**, needs reformatting only |
| 4 | Recognition-vs-behavior conceptual diagram | Make the dissociation visually immediate for one concrete case | `EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md` worked example (`aa71a70f` or `e549f564`) | Small schematic: shared (memories, query) input → two branches (free generation → sycophantic quote; MCQ → correct "No" answer) | Ch. 5 | **Must be generated** (conceptual diagram, no data plot) |
| 5 | Clean teacher-forced activation patching by layer range | Show the causal BASE↔unlearned effect and its layer profile | `.../activation_patching_clean_audit/clean_per_example_shifts.csv` (and its existing plot, if reusable) | Mean shift ± bootstrap CI, x=layer range, series=method | Ch. 6.1 | **Likely exists** (`plots/clean_per_example_shifts.png`) — check shape, adapt caption; regenerate only if the existing plot doesn't isolate exactly this comparison |
| 6 | Experiment B memory-patching result table | Show the memory-context causal effect and the BASE-is-not-weaker finding together | `expB_memory/expB_scores.csv`, tables already in `EXPERIMENT_B_MEMORY_INTEGRATION.md` | Table, rows = (model × layer range), columns = mean forward_shift (n positive/n), mean reverse_shift (n negative/n) | Ch. 6.3 | **Exists** as markdown, needs reformatting only |
| 7 | Final conceptual synthesis diagram | One picture holding the whole causal story together: two separate causal axes (weights vs. context) converging on the same behavioral outcome, plus the intact-recognition branch | Synthesizes #4, #5, #6 — no new data | Schematic: (BASE weights / unlearned weights) → patching → preference; (with-memory / no-memory prompt) → patching → preference; both feed into "safe vs. sycophantic generation"; a separate box shows "explicit MCQ recognition: intact in all cases" | Ch. 7 (Discussion) or end of Ch. 6 | **Must be generated** (pure conceptual diagram) |

Deliberately excluded (to avoid the "20 plots" problem): a separate plot for
Experiment 1's free-generation repair counts (kept as a compact
in-text/table mention per §5.4), a separate plot for the reproducibility
diagnostic's 55%/70% numbers (stated in prose), and any per-example
logit-lens layer sweep plots (useful for an appendix, not for the main
argument).

---

## 7. Claim–evidence matrix

| Thesis claim | Supporting evidence | Strength | Allowed wording | Wording to avoid |
|---|---|---|---|---|
| Unlearning's effect on contextual privacy is heterogeneous, not uniform | PersistBench sycophancy worsens (MUSE-News), cross-domain improves (MUSE-News), sycophancy does not replicate (MUSE-Books) | Strong (multiple valid, non-collapsed 200-row populations) | "Unlearning's effect on contextual privacy behavior was heterogeneous across dataset and category — it worsened for MUSE-News sycophancy but improved or did not replicate elsewhere." | "Unlearning generally harms/degrades contextual privacy." |
| PrivacyLens recognition stays close to BASE after unlearning | Cosine 0.937/0.938 (MUSE-News), 0.991 (MUSE-Books); % changes <1pp | Strong | "PrivacyLens recognition remained highly aligned with BASE (cosine 0.937/0.938; <1 percentage point change)." | "PrivacyLens recognition was unchanged / identical." |
| Explicit anti-sycophancy recognition is preserved on the manually verified failure set | Experiment A: 10/10 robust MCQ correctness | Strong, but small-n | "All 10/10 high-confidence failure instances correctly selected the anti-sycophancy response in both MCQ answer orderings." | "The model's privacy knowledge is completely unchanged." / "Recognition is always preserved." (n=8 unique cases only) |
| BASE-vs-unlearned representation differences causally shift the teacher-forced safe/sycophantic preference | Clean patching, both directions: forward (donor BASE→recipient unlearned) SatImp +0.138 CI[0.119,0.158] 6/6, SimNPO +0.111 CI[0.077,0.143] 4/4; reverse (donor unlearned→recipient BASE) SatImp -0.141 CI[-0.161,-0.123] 6/6, SimNPO -0.113 CI[-0.144,-0.078] 4/4 | Strong at the teacher-forced level | "Replacing the recipient model's mid-to-late decoder outputs (L14-27) with the donor model's outputs shifted the recipient's relative preference in the direction predicted by the donor's identity, consistently across every example, both patch directions, and both methods, at the teacher-forced level." (closely follows the canonical report's own "Correct summary sentence," §G) | "Unlearning causally changes what the model generates" (without specifying teacher-forced vs. free generation); "Substituting unlearned representations into BASE" as if that were the only tested direction (the forward direction, donor BASE→recipient unlearned, is equally canonical and was misattributed to this claim in an earlier draft); "This identifies the mechanism/circuit responsible" (the patch is coarse and whole-model-state, not shown to be memory-specific, and not shown to be failure-specific for SimNPO) |
| The same representational difference partially transfers to free generation | Experiment 1: 1/3 confidently repaired SatImp case, SimNPO untestable | Weak, existence-proof only | "In at least one case, the same patching intervention altered actual free-generation output, in a both-judges-agreed and bidirectionally consistent way — but this did not generalize across the treatment set, and no comparable evidence exists for SimNPO." | "Patching reliably repairs sycophantic generation." / "The causal effect is confirmed in free generation." |
| Free-generation non-reproduction reflects environment instability, not an Experiment-1 bug | Repro check: fresh vLLM matches original 55%, Exp1 HF matches 70% | Moderate (diagnostic, n=20 pairs) | "The non-reproduction of some audited failures under fresh generation is better explained by generation-environment and model stochasticity than by an implementation defect in Experiment 1." | "Experiment 1's results are unreliable." / "The original audit was wrong." |
| Stored context causally influences sycophantic preference | Experiment B reverse direction, L14-20: BASE 10/10, SatImp 5/6, SimNPO 2/4 | Moderate (small effect size, small n for SimNPO) | "Injecting a memory-conditioned prompt-end state into the no-memory condition shifted preference toward sycophantic continuations, particularly at L14–20." | "Unlearning creates a broken memory gate." / "Memory context fully explains the sycophancy failure." |
| Unlearning specifically altered the tested memory-integration channel | Same Experiment B data, compared across models | **Not established** — explicitly a negative/non-confirmatory result | "This experiment does not establish that unlearning specifically created or strengthened this memory-integration channel; BASE exhibited the same tested channel at least as strongly." | "Experiment B shows unlearning strengthens memory integration." / "We identified a privacy circuit." |
| The overall mechanism | All of the above, combined | Interpretive synthesis, not a new empirical claim | "The evidence is most consistent with unlearning changing how existing knowledge and contextual signals are translated into downstream behavior, rather than erasing knowledge or creating a new, uniquely unlearning-specific memory pathway." | Any claim of having found "the mechanism" or "the circuit" responsible |

---

## 8. Negative / non-confirmatory findings worth reporting

Section title to use verbatim in the thesis: **"Negative / non-confirmatory
findings worth reporting."**

- **Contextual privacy did not consistently worsen.** PersistBench
  cross-domain improved on MUSE-News for both methods. *Belongs in Ch. 4,
  immediately alongside the sycophancy degradation* — reporting only the
  degradation and omitting this would misrepresent the aggregate picture.
  Strengthens the story because it is exactly the evidence for "heterogeneous,
  not general."
- **MUSE-Books sycophancy did not replicate the MUSE-News degradation.**
  *Belongs in Ch. 4.* Strengthens the case-selection rationale in Ch. 3 (why
  MUSE-News specifically was chosen) and further supports "not general."
- **PersistBench judging is only 59% agreed between two independent judges
  in Experiment 1, with a strong asymmetric bias (Gemma more failure-prone).**
  *Belongs in Ch. 6.2 and Ch. 8 (Limitations).* Strengthens credibility by
  showing the thesis does not hide judge disagreement — every "confident"
  claim in Ch. 6.2 is already qualified by this.
- **SimNPO's free-generation failures did not reproduce in Experiment 1 at
  all** (0/4 treatment cases). *Belongs in Ch. 6.2.* This is not a flaw to
  hide — it is direct evidence that the manually-audited "frozen" failure
  label was already a single sample of a noisier process, motivating the
  reproducibility diagnostic that follows it.
- **Free generation is environment/run-sensitive even under the literal
  original pipeline** (55% self-reproduction). *Belongs in Ch. 6.2
  (reproducibility subsection) and Ch. 8.* Strengthens the thesis's
  methodological credibility — it pre-empts an obvious reviewer objection
  ("why doesn't Experiment 1 just reproduce the audit?") with a direct,
  quantified answer.
- **Experiment B did not establish an unlearning-specific strengthening of
  the tested memory channel.** *Belongs in Ch. 6.3 and Ch. 7 (Discussion).*
  This is the single most important negative result in the mechanistic
  chapter — it directly prevents the thesis from overclaiming a "broken
  memory gate," which is exactly the kind of overreach the evidence does not
  support.
- **BASE often showed the same or a stronger memory-state causal effect than
  the unlearned models** (10/10 at L14-20, vs. SatImp 5/6 and SimNPO 2/4).
  *Belongs alongside the previous point in Ch. 6.3.* This is the specific
  evidence behind the negative finding above and should be stated as a
  number, not summarized away.

---

## 9. Limitations section blueprint

| Limitation | What it is | Claim(s) it affects | Why conclusions still hold |
|---|---|---|---|
| Small, curated mechanistic failure subset | n=8 unique / 10 model-case instances, selected as HIGH_CONFIDENCE_FAILURE from 27 manually reviewed candidates, not a random sample | RQ2/H2 (recognition-behavior gap), RQ3/RQ4 mechanistic claims | The dissociation and causal effects are demonstrated wherever genuinely testable; the claim is about *existence and reproducibility on every tested case*, not *population prevalence* — this scoping is already explicit in every source report and should stay explicit in the thesis. |
| Judge sensitivity/disagreement | Qwen vs. Gemma-3 agree only 59% (Experiment 1); legacy local Qwen judge used throughout instead of canonical PersistBench Kimi-K2 judge | All PersistBench-derived percentages (Ch. 4) and all free-generation judged outcomes (Ch. 6.2) | Teacher-forced results (Ch. 6.1, Experiment A) do not depend on judge scoring at all (they use log-prob margins / logit comparison), so the thesis's strongest causal and recognition claims are judge-independent. |
| Instability of exact free generations | Repro check: 55%/70% self-reproduction rates even under literal original pipeline | Ch. 6.2 free-generation causal claims | Explicitly treated as a property of the generation process itself (quantified, diagnosed), not swept under the rug — the thesis's claims in this chapter are already scoped to "existence-proof" strength accordingly. |
| Teacher-forced patching vs. actual autoregressive generation | Fixed-continuation likelihood contrast (Ch. 6.1) is a different, more controlled measurement than free generation (Ch. 6.2) | RQ3 | The thesis reports both, keeps them explicitly separate (never conflates a teacher-forced number with a free-generation claim), and is honest that only the teacher-forced result is strong/consistent. |
| One primary mechanistic model family/checkpoint setup | Qwen2.5-7B-Instruct, MUSE-News, SatImp/SimNPO checkpoint-459 only, for all of Ch. 5–6 | Generality of every mechanistic finding | The behavioral discovery pass (Ch. 4) already surveys more broadly and is what motivates *not* claiming generality — the mechanistic depth is a deliberate trade-off for rigor on one case, stated as such. |
| Memory patching only at selected positions/layer ranges | Experiment B patches a single prompt-end token position at L14-20/L21-27 only | RQ4 / H3 | This is exactly why the thesis does not claim to have found "the" memory mechanism — the small recovered effect size relative to the full with/without-memory gap is itself evidence that the tested position/layers are not the whole story, and this is stated directly rather than implied. |
| Inability to identify the exact downstream computational mechanism | No head/neuron/SAE-level analysis was performed; patching is coarse (multi-layer ranges) | All mechanistic claims (Ch. 6) | The thesis's contribution is causal *localization evidence* (which axis, roughly which layers), not a full circuit-level account — this scope is stated up front in Ch. 3 and not oversold in Ch. 6/7. |
| No claim of generality across all unlearning methods/datasets | Only SatImp and SimNPO tested; only MUSE-News/MUSE-Books/TOFU-adjacent benchmarks surveyed | H1, all RQs | Ch. 4's heterogeneity finding is itself the argument against generality — the thesis's central claim is explicitly that unlearning effects are setting-dependent, so this limitation is consistent with, not contrary to, the thesis's own conclusion. |

---

## 10. Contribution statement (draft, 5 items)

1. **An empirical characterization of contextual-privacy effects after
   machine unlearning that is heterogeneous rather than uniform**, spanning
   multiple datasets (MUSE-News, MUSE-Books) and PersistBench categories
   (sycophancy, cross-domain), showing degradation in one specific setting
   and improvement or non-replication in others.
2. **Identification and manual verification of a recognition-behavior gap**
   after unlearning: on every one of 10 manually-audited genuine sycophancy
   failures, the unlearned model still explicitly and robustly recognizes the
   anti-sycophancy norm when asked directly.
3. **Causal evidence, at the teacher-forced representational level, that
   BASE-vs-unlearned internal state differences shift the safe-vs-sycophantic
   continuation preference**, with partial (existence-proof-level, not
   population-level) transfer to actual free generation.
4. **Causal evidence that stored user context itself contributes to the
   sycophantic preference**, via a specific, layer-localized (L14-20)
   prompt-end representation channel.
5. **Evidence against two specific over-simplified explanations**: that
   unlearning merely erases privacy-relevant knowledge (contradicted by the
   intact recognition result), and that unlearning creates or uniquely
   strengthens a memory-integration pathway (contradicted by BASE showing the
   same tested channel at least as strongly).

Deliberately not claimed as contributions: a full mechanistic circuit, a
general theory of unlearning-induced privacy harm, or a fix/mitigation for
the observed failures.

---

## 11. Suggested writing order

1. **Results** (Ch. 4–6, in the order 4 → 5 → 6.1 → 6.2 → 6.3) — write this
   first because every other chapter derives from it, and writing it first
   forces early confrontation with exactly what the data does and does not
   support (avoiding the common failure mode of writing an Introduction that
   promises more than Results can deliver).
2. **Discussion** (Ch. 7) — write immediately after Results while the
   evidence boundaries are freshest; this is also where the §9 layer-range
   tension (L21-27 vs. L14-20) must be explicitly addressed, so it should not
   wait.
3. **Limitations** (Ch. 8) — a natural byproduct of writing Results and
   Discussion carefully; drafting it third catches anything Discussion
   over-claimed.
4. **Methods** (folded into Ch. 3's "Experimental Design," or split out) —
   write after Results/Discussion so the methodological description matches
   what was actually reported, not what was originally planned.
5. **Background / Related Work** (Ch. 2) — write once it's clear exactly
   which prior concepts (unlearning methods, MUSE, PersistBench,
   activation patching) the Results chapter actually leaned on, avoiding a
   Background chapter padded with unused literature.
6. **Introduction** (Ch. 1) — write near the end, once the actual findings
   (not the original hypotheses) are known, so the framing matches the real
   contribution.
7. **Conclusion / Abstract** — write last; the Abstract in particular should
   be a compressed version of §1's plain-language story, not a compressed
   version of the original research plan.

---

## 12. Notes on conflicts between sources (flag, do not silently resolve)

- **Layer-range tension across the three causal-patching results.** Clean
  teacher-forced BASE↔unlearned patching (Ch. 6.1) finds L21-27 numerically
  strongest; free-generation Experiment 1 (Ch. 6.2) finds its one confident,
  non-copied repair at L14-20 and explicitly flags L21-27 results there as
  potentially donor-output copying rather than a graded causal effect;
  Experiment B's memory-context patching (Ch. 6.3) finds L14-20 clearly
  stronger and more consistent than L21-27. These three results do not
  triangulate on a single "the effect lives at layer X" answer, and they are
  also not measuring the same causal axis (weights vs. context) or the same
  regime (teacher-forced vs. free generation). The thesis should state this
  directly in Discussion (Ch. 7) rather than picking whichever layer range
  is convenient per subsection — this is a genuine open question the data
  raises, not a contradiction to paper over.
- **Two "final report" documents for the same behavioral starting point.**
  `mechanistic/outputs/muse_news_sycophancy_mechanistic/FINAL_REPORT.md`
  (earlier, whose *case-selection and patching data* are SUPERSEDED) and
  `.../muse_news_sycophancy_paradox/report/FINAL_REPORT.md` (canonical)
  report the identical behavioral percentages, independently re-derived and
  matching exactly. No numeric conflict — but only the paradox-directory
  version should be cited, per `RESULTS_REGISTRY.csv`; the earlier one exists
  for provenance only.

---

## What this thesis is really saying

After a model is made to "forget" certain training data, it can start
behaving differently in a specific, narrow way: on some real conversations,
it caves to what the user seems to believe instead of just giving a
straight, independent answer — even though, if you ask it directly whether
that's the right thing to do, it still says no, every single time it was
tested. That's the headline: the model didn't forget the rule, but something
about how it applies that rule to an actual conversation shifted after
unlearning. Poking at the model's internals shows two things contribute to
that shift — the unlearning itself changed the model's internal state in a
way that pushes toward the people-pleasing answer, and the presence of the
user's remembered preferences in the conversation also pushes that way on
its own — but the second effect isn't something unlearning specifically
created or made worse; the untouched model has it too. So the honest
takeaway isn't "unlearning breaks privacy" or "unlearning erases knowledge"
or "we found the circuit responsible" — it's that unlearning can quietly
change how a model turns what it already knows, and what it's told about the
user, into what it actually says, without touching whether it still knows
the rule in the first place.
