# Focused Thesis Synthesis: MUSE-News Sycophancy Mechanism

Synthesizes `EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md` and
`EXPERIMENT_B_MEMORY_INTEGRATION.md` (both completed 2026-09-23, jobs 444584 and 444575,
both exit code 0) against the three hypotheses. Both experiments operate on the same 10
HIGH_CONFIDENCE_FAILURE cases (8 unique `persistbench_id`s; SatImp 6, SimNPO 4, 2
shared) drawn from `clean_selection.json` — a curated worst-case subset, not a random
sample of MUSE-News.

## H1: "Machine unlearning generally harms contextual privacy."

**Verdict: PARTIALLY SUPPORTED**

Evidence for: the 10 treatment cases are, by construction, real, verified instances where
SatImp/SimNPO validated a user's stored (often false or biased) belief instead of giving
an independent, evidence-based answer — a concrete contextual-privacy/integrity harm in
free generation. This is corroborated by the pre-existing, separately-run teacher-forced
result (`CLEAN_RERUN_REPORT.md`, not rerun here): patching unlearned-model representations
into BASE causally *increases* the sycophantic-response preference (SatImp +0.138
CI[0.119,0.158] 6/6; SimNPO +0.111 CI[0.077,0.143] 4/4) — i.e. unlearning's effect on
representations is not neutral, it measurably pushes toward the sycophantic failure mode.

Evidence against / limiting the claim: "generally" is not established by this data. The
10 cases are a deliberately curated HIGH_CONFIDENCE_FAILURE subset selected specifically
because they show the failure clearly — they demonstrate the failure mode *exists and is
causally real*, not that it is the *typical* outcome across MUSE-News sycophancy cases as
a whole (that would require the full 200-example benchmark rate, which is out of scope
for Experiments A/B).

**Bottom line:** unlearning causally produces a specific, reproducible contextual-privacy
harm (sycophantic validation of stored user beliefs) — real, not an artifact — but this
analysis does not establish that this harm is the general/majority case rather than a
tail failure mode.

## H2: "Machine unlearning can preserve explicit privacy recognition while changing contextual privacy behavior."

**Verdict: SUPPORTED**

Experiment A is a clean, complete result: **10/10 (100%)** of the genuine sycophancy
failure cases — every single case where SatImp or SimNPO actually committed the
sycophantic failure in free generation — still correctly and robustly (both MCQ
orderings) identify the anti-sycophancy rule when asked explicitly, using the identical
stored memories and query. The model's declarative/explicit knowledge of the norm is
fully intact even in the exact cases where its generative behavior violated that norm.
This is precisely the dissociation H2 predicts: unlearning does not erase explicit
privacy-relevant recognition, it changes *behavior* under free generation while leaving
recognition capacity untouched. n=8 unique cases is small but the effect is unanimous and
was tested against every available genuine-failure case, with no counterexamples.

## H3: "In the MUSE-News sycophancy case, unlearning changes how stored user context influences generation."

**Verdict: PARTIALLY SUPPORTED**

Experiment B finds a real causal channel — a single prompt-end hidden state, patched at
mid-late layers (L14–20), measurably carries memory-context information: injecting a
memory-conditioned state into a memory-free context reliably shifts the model toward the
sycophantic response (BASE 10/10 cases, SatImp 5/6, SimNPO 2/4 at L14–20). This
establishes that stored-context integration *is* causally implicated in the safe/
sycophantic balance, somewhere in the network, at this position and layer band.

However, the experiment does **not** show that this specific channel is *changed by*
unlearning: BASE's effect is at least as strong and consistent as SatImp's, and stronger
than SimNPO's small-n result. If anything, the mechanism looks like a pre-existing
property of the model family that unlearning does not obviously amplify at this
position. Additionally, the effect size recovered by patching one token position
(~0.02–0.05 log-prob-margin units) is small relative to the full unpatched with/without-
memory gap (~0.4–0.9 units), and the reverse (memory-ablation) direction — the more
direct test of "does removing memory's causal trace fix the failure" — is weak and
inconsistent even in the unlearned models. So the *existence* of a context-integration
causal channel is supported; the *unlearning-specific change* to that channel, at this
position, is not.

**Bottom line:** stored context measurably and causally influences generation through an
identifiable internal channel, but the unlearning-vs-BASE difference in *how* that
context is integrated is not demonstrated by this within-model single-position patch —
the observed generation-level difference between BASE and the unlearned models (per the
separately-established full-sequence BASE-vs-unlearned patching result) more likely
arises from broader representational differences than from a change specifically to this
narrow memory-integration channel.

## Combined picture

The three results fit together as: unlearning (SatImp/SimNPO) produces a real,
causally-verified sycophantic-generation failure on a specific subset of MUSE-News
sycophancy cases (H1, partial — real but not shown to be general), while leaving the
model's *explicit* recognition of the underlying anti-sycophancy norm fully intact in
every one of those same cases (H2, supported) — a genuine recognition-vs-behavior
dissociation. The mechanistic origin of the behavioral change is not fully localized:
stored user context is causally integrated into the model's internal state at mid-late
layers in a way that influences the safe/sycophantic balance (H3, partial), but this
channel is not shown to be unlearning-specific — it is present, comparably or more
strongly, in BASE. This points to the unlearning-generation gap arising from a broader
shift in representations (consistent with the larger, unlearning-vs-BASE full-sequence
patching effect already established) rather than from a targeted change to the narrow
memory-context-integration pathway tested here.
