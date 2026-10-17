# Experiment Index — MUSE-News Sycophancy Mechanism

This is the main map for the entire mechanistic investigation into MUSE-News
sycophancy after unlearning (SatImp / SimNPO, Qwen2.5-7B-Instruct). It is meant to
let someone unfamiliar with the repository understand the experiment sequence in
5–10 minutes, and to point at the exact canonical file for every claim. For the
full artifact-by-artifact classification (CANONICAL / SUPPORTING / SUPERSEDED /
FAILED / DEBUG), see `RESULTS_REGISTRY.csv` in this directory. For the short
"what do I cite for each thesis result" reference, see
`THESIS_RESULTS_CHEATSHEET.md`.

No files referenced below were reorganized into new subdirectories — see
`README.md` § "Why the directory layout was not restructured" for why, and where
things physically live.

---

## Behavioral starting point

**Phenomenon:** after SatImp/SimNPO unlearning on MUSE-News (Qwen2.5-7B-Instruct),
explicit privacy-norm recognition (PrivacyLens MCQ) stays approximately stable
(92.29% BASE → 91.89% SatImp / 91.68% SimNPO), while contextual, free-generation
privacy behavior on PersistBench **sycophancy** worsens at every FR@K (9.5/12.5/12.5%
BASE → 12.0/17.0/17.0% SatImp, 11.5/15.0/15.0% SimNPO), on a 100%-valid,
non-collapsed 200-row population. Cross-domain PersistBench, by contrast,
*improves* for both methods, and MUSE-Books does not replicate the effect —
neither is pursued mechanistically.

**Datasets/models/methods:** MUSE-News, Qwen2.5-7B-Instruct, BASE
(`saves/finetune/muse_news_qwen25_7b_instruct_target`) vs. SatImp / SimNPO
(`saves/unlearn/muse_news_qwen25_7b_instruct_{satimp,simnpo}/checkpoint-459`).

**Canonical location:**
`mechanistic/experiments/muse_news_sycophancy_paradox/report/FINAL_REPORT.md`
(independently re-derives, and matches exactly, the numbers first reported in
`mechanistic/outputs/muse_news_sycophancy_mechanistic/FINAL_REPORT.md`, which is
SUPERSEDED for anything downstream of case selection — see next section — but
whose behavioral FR@K numbers themselves are not disputed).

The upstream motivation for selecting this specific dataset/category as the
thesis case study is `mechanistic/outputs/benchmark_paradox/FINAL_REPORT.md`
(a broader, multi-dataset PrivacyLens-vs-PersistBench dissociation scan;
out of scope for this index, left in place).

---

## Manual failure audit

**Original candidates:** 27 SAFE→FAILURE transition candidates across SatImp and
SimNPO were manually reviewed.

**Classification:** 10 `HIGH_CONFIDENCE_FAILURE`, 9 `LIKELY_JUDGE_NOISE`, 8
`AMBIGUOUS`. The dominant reason for exclusion was a documented "task-compliance
confound" (the model still substantively answers the query while also
validating the user's stated belief — judge-score-noisy, not a clean sycophancy
failure).

**10 model-case instances / 8 unique PersistBench IDs:** SatImp treatment n=6,
SimNPO treatment n=4, with 2 `persistbench_id`s (`aa71a70f…`, `7079a34e…`)
shared across both methods → 8 unique IDs, 10 (model, case) instances. Each
treatment case has a matched SAFE→SAFE control (greedy nearest-neighbor on BASE
judge score, then response-length, then prompt length).

**Canonical path to clean selection:**
`mechanistic/experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit/clean_selection.json`
(full provenance per example: query, memories, both models' responses, judge
scores, manual audit reason) built from
`mechanistic/experiments/muse_news_sycophancy_paradox/audit/manual_transition_audit.csv`
(the full 27-candidate audit) via
`.../activation_patching_clean_audit/build_clean_selection.py`.
Narrative selection tables: `.../activation_patching_clean_audit/clean_selection.md`.

**Do not use for thesis numbers:** the older, pre-audit 9-case selection at
`mechanistic/outputs/muse_news_sycophancy_mechanistic/manifests/continuation_cases_v1.json`
(judge-score-jump selected, includes cross_domain, never manually audited).

---

## Clean teacher-forced activation patching

**Purpose:** test, at the teacher-forced (fixed-continuation likelihood) level,
whether patching activations between BASE and unlearned models — in both
directions (donor=BASE→recipient=unlearned, and donor=unlearned→recipient=BASE)
— at different layer ranges shifts the safe-vs-sycophantic response
preference, on the clean, manually-audited 10-case set.

**Canonical report:**
`mechanistic/experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit/CLEAN_RERUN_REPORT.md`

**Canonical result files:**
`clean_per_example_shifts.csv`, `clean_activation_patching_summary.csv`,
`activation_patching_clean_{base,unlearned}_recipient.csv` (all in the same
`activation_patching_clean_audit/` directory).

**One-sentence result:** BASE→unlearned activation patching (donor=BASE,
recipient=unlearned) shifts the fixed-continuation preference toward the
BASE/safe response (forward: SatImp L21-27 +0.138 CI[0.119,0.158] 6/6, SimNPO
+0.111 CI[0.077,0.143] 4/4); the reverse direction (donor=unlearned,
recipient=BASE) mirrors this with the opposite sign (SatImp -0.141
CI[-0.161,-0.123] 6/6, SimNPO -0.113 CI[-0.144,-0.078] 4/4), i.e. shifts BASE's
preference toward the sycophantic response; L14-20 comparable magnitude to
L21-27 in both directions — this is a BASE-vs-unlearned weight-space
comparison, a different causal axis from Experiment B's within-model
memory-context comparison below.

*(This result was already complete before the final-mechanism work began and
was not rerun; the superseded pre-audit version of the same patching, plus the
correction record `old_vs_clean_comparison.csv`, remain on disk in the parent
`analysis/` directory only because `analyze_clean_patching.py` reads the old
CSV to build that comparison — see `RESULTS_REGISTRY.csv`.)*

---

## Free-generation Experiment 1

**Purpose:** test whether the same BASE↔unlearned patching causally changes
actual **free-generation** sycophancy behavior (not just teacher-forced
likelihood), on the same clean 10-case set, at L0-6 (control)/L14-20/L21-27,
scored by two independent judges (legacy local Qwen2.5-7B-Instruct + Gemma-3-12b-it).

**Canonical report:**
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/EXPERIMENT_1_RESULTS.md`

**Major limitation about failure reproduction:** only 3 of 6 SatImp and 0 of 4
SimNPO treatment examples actually reproduce as a FAILURE (judge score ≥3) under
fresh greedy free generation of the unpatched unlearned model — the other 7
examples' manually-audited sycophantic continuation (frozen from the original
PersistBench run) simply does not recur on a fresh regeneration. This halves
the effective SatImp treatment set and empties the SimNPO treatment set for any
"did we repair the failure" reading, independent of the patching itself. Judge
agreement between Qwen and Gemma-3 is only 59% overall.

**One-sentence result:** tentatively supported for SatImp (one full,
both-judges-agreed, bidirectional repair at L14-20, `aa71a70f`), unsupported /
not testable for SimNPO (no treatment case reproduces as a failure to repair in
the first place) — an existence-proof-level result, not a population-level
effect.

---

## Reproducibility diagnostic

**Canonical report:**
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/repro_check/REPRO_CHECK_RESULTS.md`
(run *before* Experiments A/B, specifically to determine whether Experiment 1's
non-reproduction problem above was a pipeline bug or genuine behavioral
instability).

**One-sentence conclusion:** exact historical generations are not reliably
reproducible even under the literal original vLLM pipeline rerun today (it
matches the frozen July original only 55% of the time, versus 70% for
Experiment 1's HF approximation) — so this is predominantly
environment/behavioral drift (vLLM/CUDA/attention-kernel changes since July,
compounding with genuine model stochasticity), **not primarily an
Experiment-1 HF-vs-vLLM implementation bug**.

---

## Experiment A

**Recognition-vs-behavior gap:** an explicit MCQ probe, on the identical
(memories, query) pair as each genuine sycophancy failure, asking whether the
model should let stored user beliefs bias its answer. Tested in both answer
orderings for position-bias control.

**Canonical report:**
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md`

**Canonical data:**
`expA_mcq/missing5_readout.csv` + `expA_mcq/missing5_prepared.json` (5 of the 8
unique IDs, newly extracted here) combined with
`mechanistic/privacy_collapse/persistbench_sycophancy_mcq/analysis/mcq_readout_per_example.csv`
(the other 3 unique IDs, reused unmodified from a pre-existing 50-example MCQ
run).

**Result:** **10/10 (100%)** genuine sycophancy-failure (model, case) instances
— every case where SatImp or SimNPO actually committed the failure in free
generation — robustly (both orderings) answer the explicit anti-sycophancy MCQ
correctly.

*(Provenance note: the successful run was job 444584. Two earlier attempts,
444563 and 444574, failed on ordinary engineering bugs before that — archived
at `archive/failed_or_superseded/expA_failed_slurm_attempts/`.)*

---

## Experiment B

**Within-model memory/context patching:** a causal test, same model weights,
that patches a single prompt-end hidden state between a WITH_MEMORY and
NO_MEMORY version of the same prompt (donor tensors already pre-extracted, no
live donor forward pass), at L14-20/L21-27, on the clean 10-case set.

**Canonical report:**
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/EXPERIMENT_B_MEMORY_INTEGRATION.md`

**Canonical data:**
`expB_memory/expB_scores.csv` + `expB_memory/expB_provenance.json`.

**Result:** memory context is causally relevant — injecting a memory-conditioned
hidden state into a memory-free context reliably shifts the model toward the
sycophantic response, strongest and most consistent in the **reverse
(inject-memory) direction at L14-20** (BASE 10/10 cases, SatImp 5/6, SimNPO
2/4 — small n). But **the tested channel is not shown to be unlearning-specific:
BASE exhibits it at least as strongly as SatImp and more consistently than
SimNPO**, so this experiment does not establish that unlearning specifically
created or amplified this particular memory-integration pathway.

---

## Final interpretation

See `FOCUSED_THESIS_SYNTHESIS.md` for the full H1/H2/H3 verdicts (H1 partially
supported, H2 supported, H3 partially supported) and how Experiments A and B
combine with the upstream teacher-forced/free-generation/reproducibility work
above into one coherent picture. See also `README.md` for the plain-language
research question and directory map, and `THESIS_RESULTS_CHEATSHEET.md` for a
short, citation-ready summary of every individual number.
