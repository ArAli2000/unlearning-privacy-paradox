# MASTER THESIS MAP

Read-only reconstruction. Nothing was moved, renamed, deleted, modified, or rerun to produce
this document. Every fact below is sourced from an existing file in this repository — a
script, a config, a `trainer_state.json`, a frozen report, or a manifest — and every non-obvious
claim names that source inline. Where the repository does not contain evidence for something,
this is stated as **NEEDS USER CONFIRMATION** rather than filled in from the prompt's summary.

This map deliberately supersedes nothing that is already frozen under
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/` — Section 8 integrates that
work by reference, it does not redo or reinterpret it.

**Primary sources reconciled to build this map** (all pre-existing, all read in full):
`research_history/README.md` + all 5 phase READMEs, `thesis/README.md`,
`thesis_cleanup_audit/EXPERIMENT_HISTORY.md` + `experiment_history.csv`,
`thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md`, `CHECKPOINT_SELECTION_PATCH.md`,
`PERSISTBENCH_MODIFICATIONS.md`, `PROPOSED_STRUCTURE.md`, `DELETE_CANDIDATES_FINAL.md`,
`thesis/docs/{trainer_patch,persistbench_patch,generation_provenance}.md`,
`mechanistic/outputs/benchmark_paradox/FINAL_REPORT.md`,
`mechanistic/experiments/muse_news_sycophancy_paradox/report/FINAL_REPORT.md`,
`mechanistic/experiments/muse_news_sycophancy_final_mechanism/{README,EXPERIMENT_INDEX,
EXPERIMENT_PLAN,RESULTS_REGISTRY.csv,THESIS_RESULTS_CHEATSHEET,THESIS_WRITING_PLAN,
FOCUSED_THESIS_SYNTHESIS}.md`, `mechanistic/outputs/muse_books_weekly_update_analysis/`,
plus direct reads of `research_history/01_tofu_baselines/manifests/*.json` (raw
`trainer_state.json` eval-metric log entries) and `git diff` against `src/trainer/base.py` /
`configs/eval/tofu.yaml`.

**Source-access note (this revision, 2026-09-24 second pass)**: this revision was asked to
integrate the original thesis Exposé
(`Aly_Elshashay_Expose_Writing_Final_Highlighted (2).pdf`) and the July midterm presentation
(`Unlearning_Privacy_Paradox_Midterm_v7(3) (1).pptx`). **Neither file could be located or
opened by this session** — a search of the repository, the user's home directory, and the
broader accessible filesystem found no matching PDF/PPTX. Per the task's own fallback
instruction, the facts about these two documents supplied in the task prompt are incorporated
below **as the user's own reported historical context**, not as independently verified primary
sources. Every such claim is tagged **EXPOSE-DOCUMENTED** or **MIDTERM-DOCUMENTED** to preserve
the distinction the user asked for ("this was in the original planning documents" vs. "this is
present-day recollection") — but these tags mean *"the user states this document contained
this,"* not *"this session opened the file and confirmed it."* Claims sourced from direct
repository inspection remain tagged **REPO-VERIFIED**; claims the user supplied from memory
with no document attribution are tagged **USER-CONFIRMED**; this map's own reasoning from
evidence, not a quoted source, remains tagged **INFERRED**.

---

## 0. Correction to the prompt's working summary (read this first)

The 14-step summary supplied in the prompt is a reasonable first approximation of the shape
of the project, but the repository's own evidence differs from it in three concrete,
load-bearing ways:

1. **It was not "~12 methods."** Phase 1 (`research_history/01_tofu_baselines/`) tested
   exactly **10** open-unlearning methods: CEU, GradAscent, GradDiff, NPO, PDU, RMU, SatImp,
   SimNPO, UNDIAL, WGA. There is no evidence anywhere in the repository of a broader,
   ~12-method sweep.
2. **The narrowing was not a single "10 → 4" step, it was two separate narrowings, and
   neither is explained by a written rationale document.** Phase 2 first narrows to an
   inferred "top 3" (script name `run_7bscale_top3_fullmetrics_a180.sh`; the identity of
   these 3 is not stated anywhere and must be inferred — see §2/§3), then a systematic
   4-method grid (`run_4models_4methods_save_bestagg.sh`) explicitly uses **SatImp, SimNPO,
   RMU, WGA** — these 4 are the ones carried through TOFU-full scaling and into MUSE-News/
   MUSE-Books. Then, separately, at the mechanistic-analysis stage, the "core" narrows a
   **second time**, from 4 down to **2** (SatImp, SimNPO) — RMU and WGA continue to appear
   only at the behavioral (PrivacyLens/PersistBench) layer, never in the mechanistic
   hidden-state/probe pipelines (`thesis/README.md` §4, `thesis_cleanup_audit/EXPERIMENT_HISTORY.md`
   §3/§7). **No file anywhere states an explicit rationale for either narrowing** —
   `EXPERIMENT_HISTORY.md` says this outright ("not stated explicitly in any file... no
   design-rationale document exists"). §3 below gives the strongest evidence-based
   reconstruction available, built from actual TOFU eval numbers, but it is a reconstruction,
   not a quoted decision.
3. **MUSE-News was run twice, on two different base targets, and the first, complete run was
   quietly abandoned, not built upon.** "Track A" (official HuggingFace Llama-2-7b target)
   produced a complete result end-to-end on 2026-07-01–04 and was then never touched again;
   "Track B" (a locally-finetuned Qwen2.5-7B-Instruct target) began 8 days later and is the
   only track anything downstream — mechanistic work included — ever reads
   (`thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md`). This pivot is not mentioned at all
   in the prompt's summary and is one of the more important "messy, not clean" facts a
   defense committee could reasonably ask about. **The user has confirmed, this revision, that
   the reason for the switch is not remembered** — treat this as an open, unresolved provenance
   fact (§4A, §14), not as something this map has explained (§H of this revision explicitly
   revises an earlier draft of this map that had over-stated an inferred reason as fact).
4. **The privacy hypothesis was not reconstructed after the fact.** [USER-CONFIRMED /
   EXPOSE-DOCUMENTED] The original thesis Exposé already argued, before any MUSE/PrivacyLens/
   PersistBench experiment existed, that (a) standard unlearning evaluation focuses on
   forgetting/memorization, (b) privacy also requires contextual reasoning, (c) model
   modifications can have non-local behavioral effects, and therefore (d) unlearning may alter
   privacy reasoning outside the specifically forgotten data — with a working hypothesis that
   unlearning may distort internal representations and thereby degrade the application of
   contextual privacy norms. This map's earlier draft under-stated this: it correctly found no
   *written-down* hypothesis inside the git repository itself, but incorrectly left the
   impression that the privacy question was purely a retrospective framing applied after the
   benchmark-paradox scan. §0.1 below traces the RQ evolution from Exposé → Midterm → Final
   thesis in detail.

Everything below is built from repository evidence, the user's own confirmed recollection, and
(where stated) the two historical planning documents — where sources agree, it is because the
evidence happens to agree, not because any one source was assumed correct over another.

---

## 0.1 Research question evolution: Exposé → Midterm → Final thesis

**Provenance for this section**: Exposé/Midterm content is tagged **EXPOSE-DOCUMENTED** /
**MIDTERM-DOCUMENTED** per the source-access note above (user-reported document content, PDF/
PPTX not directly opened by this session). The Final-thesis RQs are **REPO-VERIFIED** where
they match `THESIS_WRITING_PLAN.md` §2 verbatim, and are noted as such.

### Exposé (original plan) — [EXPOSE-DOCUMENTED]

- RQ1 — does machine unlearning impact contextual privacy reasoning beyond the specific data
  being forgotten?
- RQ2 — does unlearning uniquely affect contextual privacy reasoning while general
  capabilities and safety evaluations show no degradation?
- RQ3 — how do internal representations of contextual privacy change due to unlearning?

↓

### Midterm (2026-07-29) — [MIDTERM-DOCUMENTED]

- RQ1 — does unlearning affect contextual privacy beyond forgotten data? (unchanged in
  substance from the Exposé)
- RQ2 — can privacy degrade while standard metrics still look fine? (a sharpened restatement
  of the Exposé's RQ2 — "standard metrics"/"general capabilities and safety evaluations" is
  now specifically operationalized as PrivacyLens-vs-PersistBench-style behavioral metrics)
- RQ3 — how do internal representations change after unlearning? **Explicitly marked FUTURE
  WORK at the midterm** — no mechanistic experiment existed yet.
- The midterm's own stated open question, carried forward unresolved: *"PrivacyLens can remain
  stable while PersistBench generation degrades — why?"* This is the exact question the final
  mechanistic chapter (§8 of this map) answers.

↓

### Final thesis — [REPO-VERIFIED, matches `THESIS_WRITING_PLAN.md` §2 verbatim]

- **RQ1**: How does machine unlearning affect contextual privacy behavior beyond the targeted
  forgotten data?
- **RQ2**: Can contextual privacy behavior degrade while explicit privacy/norm recognition
  remains intact?
- **RQ3**: Do BASE-vs-unlearned internal-state differences causally influence
  safe-vs-sycophantic behavior, and what role does stored user context play?

**These are refinements, not replacements.** RQ1 is essentially unchanged across all three
stages. RQ2 sharpens from a general "does unlearning uniquely affect privacy while other
metrics look fine" into the thesis's most concrete, testable claim (recognition-vs-behavior
dissociation on a specific, manually-audited case set — Experiment A, §8 item 6). RQ3 is the
direct fulfillment of the midterm's own explicitly-flagged future work, now split into two
causally-testable sub-questions (BASE-vs-unlearned weight-space differences, §8 item 3; stored
user context, §8 item 7) that did not yet exist as a design at the midterm stage. **Section 0's
earlier framing — that no rationale document exists for the privacy hypothesis — remains true
only in a narrower sense**: no such document exists *inside the git repository itself* (no
`.md`/`.py` file states it), but the Exposé and midterm slides, external to the repository,
already carried this hypothesis forward from the very start of the thesis.

---

## 1. Chronological reconstruction of the whole project

```
Phase 1 — TOFU baseline sweep (2026-05-22 → 05-25)
  Q: does open-unlearning's framework run correctly end-to-end, for every stock method,
     at small model scale?
  10 methods × {Llama-3.2-1B (all 10), Qwen2.5-1.5B (all 10), Qwen2.5-3B (subset then all)}
  TOFU "f10" (10%-forget) split. No checkpoint-selection metric exists yet.
  ↓ Result: all 10 methods run correctly; CEU/GradAscent collapse model_utility to 0.0 on
     Llama-3.2-1B; GradDiff collapses to 0.22 utility with near-zero forget-ROUGE; NPO/PDU/
     UNDIAL are intermediate; SatImp/SimNPO/WGA/RMU cluster at the best utility (~0.28–0.39)
     while still forgetting meaningfully (§2 table, real numbers).
  ↓ Decision: scale up model size and narrow the method set (no written rationale found,
     but the TOFU numbers above are consistent with dropping the utility-collapsing methods).

Phase 2 — Model/method scaling (2026-05-31 → 06-23)
  Q: do the surviving methods hold up at up to 14B parameters, on the FULL TOFU forget set,
     and does PrivacyLens change the picture as a second axis?
  Narrows to an inferred "top 3" (2026-05-31), then explicitly SatImp/SimNPO/RMU/WGA
  (2026-06-14 onward, 4 models × 4 methods). PrivacyLens introduced 2026-06-17. Moves from
  f10 to tofufull. Scales to Llama-3.1-8B and Qwen2.5-14B-Instruct.
  ↓ Result: the 4-method subset scales cleanly to 14B; checkpoint-selection proxy metrics
     (Selection_proxy → Agg_proxy) are invented and iterated within days.
  ↓ Decision: TOFU is synthetic — move the thesis's central claims to a realistic benchmark
     (MUSE). Last TOFU checkpoint: 2026-06-23.

Phase 3 — Checkpoint-selection methodology (developed inside Phase 2, 2026-06-14 → 07-06)
  Q: how should HF Trainer's load_best_model_at_end pick "the best" unlearning checkpoint,
     when unlearning trades off utility against forgetting?
  ↓ Result: Agg_proxy/Selection_proxy (TOFU, harmonic mean incl. an MIA privacy term or not)
     → adapted 3 weeks later into best_agg (MUSE-specific, harmonic mean of a utility-ROUGE
     proxy and a forgetting-ROUGE/extraction-strength proxy). best_agg is the literal
     mechanism, proven checkpoint-by-checkpoint, that selected every canonical MUSE-News and
     MUSE-Books checkpoint (§4).

Phase 4 — MUSE-News, Track A (official target, 2026-07-01 → 07-04) — SUPERSEDED, not junk
  Q: does unlearning directly from the official muse-bench/MUSE-News_target (Llama-2-7b, no
     local finetune) produce a complete, working result?
  RMU/WGA/SimNPO/SatImp; post-hoc checkpoint selection (no best_agg — best_agg didn't exist
  yet); a complete combined MUSE+PrivacyLens table was produced.
  ↓ Result: it worked. FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv is real and complete.
  ↓ Decision: abandoned in favor of a locally-finetuned Qwen2.5-7B-Instruct target instead.
     **[USER-CONFIRMED: the reason for this switch is not remembered.]** What is known: Track A
     was never shown to the supervisor (grep-confirmed zero hits in
     `supervisor_update/`/`meeting_updates/`); Track B began 8 days later and is the only track
     anything downstream ever reads. **No verified contemporaneous rationale for the switch is
     available** — a prior draft of this map speculated a reason ("methodological consistency
     with MUSE-Books," "built for the mechanistic phase's model family"); that speculation is
     withdrawn here, not restated. This is a real pivot, not a natural continuation, and its
     motivation is genuinely unknown — see §4A/§14. Classification for the defense: THESIS
     PROVENANCE / BACKUP, not MAIN TALK (§11/§12).

Phase 4′ — MUSE-News, Track B (locally-finetuned target, CANONICAL, 2026-07-06 → 07-08)
  Finetune Qwen2.5-7B-Instruct on MUSE-News (2026-07-06, same day best_agg was written)
  → unlearn 4 methods with metric_for_best_model=best_agg (3 of 4 OOM'd, retried)
  → checkpoint selection frozen (BASE / SatImp-459 / SimNPO-459 / RMU-459 / WGA-306)
  → PrivacyLens (493-case MCQ) + PersistBench (cross-domain/sycophancy/beneficial-memory,
     local-Qwen judge, NOT the canonical Kimi-K2 judge) evaluated, 2026-07-08.
  ↓ Result: standard MUSE forgetting/utility metrics + a full PrivacyLens/PersistBench
     behavioral profile, for BASE/RMU/WGA/SatImp/SimNPO.
  ↓ Decision: replicate the same pipeline on MUSE-Books (both an official Llama-2-7b target
     AND a second locally-finetuned Qwen2.5-7B-Instruct target).

Phase 6 — MUSE-Books replication (behavioral: 2026-07-09 → 07-12; mechanistic: 2026-09-06)
  Same methods, same best_agg selection mechanism, both a Llama-2-7b and a Qwen2.5-7B-
  Instruct track, both canonical (unlike MUSE-News, there is no superseded/dead track here).
  ↓ Result (behavioral): a full PrivacyLens/PersistBench profile for both tracks.
  ↓ Result (mechanistic replication, 6 weeks after the MUSE-News mechanistic phase): a
     genuine NEGATIVE replication — "the full MUSE-News story does not replicate on
     MUSE-Books... the central PersistBench behavioral split reverses or becomes mixed"
     (`mechanistic/outputs/muse_books_weekly_update_analysis/DISCOVERY_REPORT.md`, quoted
     verbatim). This is a real, reported finding, not a discarded draft.

WMDP side investigation (2026-07-13 → 08-12, parallel/interleaving with the above)
  Q: does the thesis's unlearning methodology (esp. RMU) generalize as a WMDP-cyber/bio
     safety intervention?
  ↓ Result: real validity/collapse issues found and fixed (smoke → fixed → sweep → real
     iteration); an MMLU utility follow-up.
  ↓ Decision (explicit, in a supervisor meeting note): "Last week we agreed to revisit WMDP
     before moving to interpretability" — WMDP is NOT part of the final thesis scope, but it
     is the documented reason the thesis pivoted to mechanistic interpretability next. The
     mechanistic phase begins within days of the final WMDP meeting update (2026-08-12 → 
     mechanistic phase starts 2026-08-15).

Phase 5 — Mechanistic analysis, MUSE-News (2026-08-15 → 08-28, ~2-week campaign)
  Built entirely on the Track B MUSE-News BASE/SatImp/SimNPO checkpoints.
  1. PrivacyLens hidden-state/logit-lens tooling (08-15)
  2. privacy_collapse pilot study (08-23/24) — validates the methodology at small scale
  3. Single-case + generalized PersistBench stress-test tooling (08-24/25)
  4. Controlled MCQ privacy-judgment probe (08-27)
  5. Native prompt-end hidden-state extraction + sycophancy-transition analysis (08-27/28)
  6. Controlled MCQ sycophancy probe + A/B label-swap robustness (08-28)
  ↓ Result: the "benchmark paradox" — PrivacyLens (explicit recognition) and PersistBench
     (contextual generation behavior) move in different directions in several conditions,
     most consistently for RMU, across TOFU/MUSE-News/MUSE-Books (mechanistic/outputs/
     benchmark_paradox/FINAL_REPORT.md — a systematic 24-condition scan).
  ↓ Decision: narrow to ONE dataset/category/method combination for deep causal follow-up:
     MUSE-News × PersistBench-sycophancy × SatImp/SimNPO (§7 explains exactly why this one).

Phase 5′ — Frozen final mechanism (2026-09-06 → 09-23) — see §8, integrated by reference
  Manual audit (27 candidates → 10 HIGH_CONFIDENCE_FAILURE) → clean teacher-forced
  BASE↔unlearned activation patching → free-generation Experiment 1 → reproducibility
  diagnostic → Experiment A (recognition-vs-behavior) → Experiment B (memory/context
  patching) → FOCUSED_THESIS_SYNTHESIS.md (H1 partial / H2 supported / H3 partial).

Repository cleanup / provenance audit (2026-09-09 → 09-14, then this map, 2026-09-24)
  Read-only forensic work producing thesis_cleanup_audit/*, then thesis/ + research_history/
  as the promoted, citable structure, then this MASTER_THESIS_MAP.md.
```

---

## 2. TOFU starting-phase audit

**All 10 methods, exact names, confirmed by grep of the actual launcher scripts**
(`research_history/01_tofu_baselines/README.md`, `thesis_cleanup_audit/experiment_history.csv`
row 1): **CEU, GradAscent, GradDiff, NPO, PDU, RMU, SatImp, SimNPO, UNDIAL, WGA**.

**Model/checkpoint**: Llama-3.2-1B (all 10 methods), Qwen2.5-1.5B (all 10), Qwen2.5-3B
(a "selected" subset first, then all methods) — `run_qwen15_methods_a180.sh` (2026-05-22, the
oldest thesis script in the repo by mtime), `run_llama1b_paper_methods_a180.sh` +
`run_llama1b_other_methods_fullmetrics_a180.sh` (05-23/24), `run_qwen3b_selected_methods_a100.sh`
+ `run_qwen3b_all_methods_fullmetrics_a180.sh` (05-23–25).

**TOFU split/config**: `f10` (10%-forget split), internal batch label `a180` (undecoded —
NEEDS USER CONFIRMATION whether this stood for a specific SLURM partition/allocation or
something else; not explained in any file found).

**Forget/retain set**: standard TOFU forget10/retain90 split as shipped by open-unlearning;
no thesis-specific modification at this stage (`configs/eval/tofu.yaml` had not yet received
its later thesis edit — see §14).

**Evaluation metrics**: ROUGE-based knowledge/verbatim memorization, `extraction_strength`,
`exact_memorization`, `forget_Q_A_Prob`, `forget_truth_ratio`, 4 MIA scores (`mia_loss`,
`mia_zlib`, `mia_min_k`, `mia_min_k_plus_plus`), `model_utility`, `privleak`,
`forget_Q_A_gibberish` — the stock open-unlearning TOFU evaluator's full metric set.

**Hyperparameter sweeps**: none found beyond model-size/method combinations — no learning-rate
or forget-strength sweep evidence in Phase 1's scripts.

**Invalid/failed runs at this stage**: none flagged as failed in Phase 1 itself (the OOM/retry
failures appear later, at the MUSE-News stage — §4). However, the raw numbers below show that
**CEU and GradAscent are functionally failed runs in substance** even though they completed
without error (catastrophic utility collapse).

**Checkpoint-selection approach**: **none** — confirmed directly by reading a Phase-1
`trainer_state.json`: `best_global_step: None`, `best_metric: None`, `global_step == max_steps`
(120) for every run. Checkpoints were saved on a fixed schedule and never automatically
selected; whatever decision followed was made by manually inspecting these numbers (no
selection script/log for this specific comparison was found — **NEEDS USER CONFIRMATION**
whether this comparison was actually made by hand at the time, or whether the Phase-2 method
narrowing was decided on some other basis entirely).

### Real numbers: Llama-3.2-1B, TOFU-f10, final checkpoint (step 120), all 10 methods

Extracted directly from the frozen `trainer_state.json` snapshots in
`research_history/01_tofu_baselines/manifests/` (the `fullmetrics` variant of each method,
where available, adds MIA/exact-memorization columns; the plain variant is otherwise
identical). This exact table does not exist pre-assembled anywhere in the repository — it was
built for this map directly from the raw JSON, not copied from a prior document.

| Method | `model_utility`† | `forget_truth_ratio`‡ | `forget_Q_A_Prob`‡ | `forget_Q_A_ROUGE`‡ | `extraction_strength`‡ | `privleak` | Status | Likely reason (inferred, not documented) |
|---|---:|---:|---:|---:|---:|---:|---|---|
| CEU | **0.0000** | 0.928 | 0.0000 | 0.0000 | 0.0325 | 27.4 | **Utility collapse** | Model retains nothing; not a usable checkpoint |
| GradAscent | **0.0000** | 0.000 | 0.0000 | 0.0000 | 0.0325 | -6.4 | **Utility collapse** | Same — classic pure-ascent failure mode |
| GradDiff | 0.222 | 0.005 | 0.0005 | 0.0014 | 0.0325 | 98.9 | Near-collapse, aggressive forgetting | Forgets almost completely but retains little else |
| NPO | 0.333 | 0.694 | 0.0132 | 0.185 | 0.046 | 99.6 | Intermediate | Reasonable balance, but below the top cluster |
| PDU | 0.296 (fullmetrics only) | 0.784 | 0.115 | 0.293 | 0.056 | 36.3 | Intermediate | — |
| UNDIAL | 0.274 | 0.740 | 0.062 | 0.313 | 0.044 | 46.5 | Intermediate | — |
| RMU | 0.282 | 0.711 | 0.044 | 0.216 | 0.046 | 80.0 | **Top cluster** | Carried forward to Phase 2/MUSE |
| WGA | 0.388 | 0.745 | 0.177 | 0.356 | 0.058 | 35.5 | **Top cluster** | Carried forward to Phase 2/MUSE |
| SatImp | 0.389 | 0.738 | 0.201 | 0.387 | 0.061 | 29.5 | **Top cluster, highest utility** | Carried forward; final mechanistic core |
| SimNPO | 0.389 | 0.738 | 0.200 | 0.386 | 0.061 | 29.4 | **Top cluster, near-identical to SatImp** | Carried forward; final mechanistic core |

† Higher = more retained general capability. ‡ TOFU-standard metrics; interpretation direction
varies by metric (see open-unlearning's own metric docs) — reported as-is, not re-derived.

**How methods were compared**: no committed scoring/ranking script or document was found for
this specific step — the pattern above (CEU/GradAscent/GradDiff collapse; SatImp/SimNPO/WGA/RMU
cluster at the best utility while still forgetting substantially) is **this map's own
reconstruction from the raw numbers**, offered as the most defensible account available, not
a quoted decision. **NEEDS USER CONFIRMATION**: was this in fact the basis for narrowing to
the "top 3"/"top 4," or was there a different (e.g. supervisor-directed, or PrivacyLens-based)
reason not captured in any committed file?

**Which methods were "eventually selected"**: SatImp, SimNPO, RMU, WGA (Phase 2 onward,
explicit in `run_4models_4methods_save_bestagg.sh`); narrowed again to SatImp/SimNPO only for
the mechanistic core (Phase 5 onward). CEU, GradAscent, GradDiff, NPO, PDU, UNDIAL do not
appear in any script after Phase 2 — confirmed by grep across `research_history/02.../scripts/`
onward.

---

## 3. Method-selection logic — how messy was it, really

Answering the prompt's explicit sub-questions directly:

- **Was it literally "best four"?** Exactly four methods (SatImp, SimNPO, RMU, WGA) are the
  ones carried from TOFU-full scaling into MUSE-News/MUSE-Books, but **there is no formal,
  globally-ranked "top 4" table anywhere in the repository** — this map does not claim one
  exists. [USER-CONFIRMED] The defensible narrative, confirmed by the user: broad TOFU
  exploration of all 10 methods → methods with severe utility collapse or a poor
  forgetting/utility trade-off (CEU, GradAscent, GradDiff — §2) were not pursued further →
  RMU, WGA, SatImp, and SimNPO were retained as four usable, comparable methods for broader
  experiments. This happened in at least two visible steps in the scripts (an inferred "top 3"
  on 2026-05-31, then an explicit 4-method grid from 2026-06-14) — the exact historical ranking
  rule that produced "top 3" specifically cannot be reconstructed from any file, and this map
  says so rather than inventing one.
- **Best according to which metric?** Model-utility retention appears to be the dominant
  factor from the raw numbers (§2) — the three methods that collapse utility to near-zero
  (CEU, GradAscent, GradDiff) are exactly the ones dropped. But `forget_truth_ratio`/
  `forget_Q_A_Prob` (forgetting strength) is not obviously traded off against utility in a
  documented formula at this stage — the actual multi-objective harmonic-mean formalization
  (`Agg_proxy`/`Selection_proxy`, later `best_agg`) is invented **three weeks later**
  (2026-06-14), i.e. **after** the method-narrowing had already happened once, not before it.
  This is a genuinely messy, non-linear order of operations: informal utility-based triage
  first, principled multi-objective metric second.
- **Was selection multi-objective?** Only formally from 2026-06-14 onward (`Agg_proxy` =
  harmonic mean of memorization/privacy/utility proxies; `Selection_proxy` = harmonic mean of
  memorization/utility only, dropping the MIA-privacy term — itself a documented, deliberate
  same-day methodological refinement, see `research_history/02_model_method_scaling/README.md`
  §"What was learned").
- **Terminology correction — "Priv" in the aggregation formula is not contextual privacy.**
  [MIDTERM-DOCUMENTED + REPO-VERIFIED] The July midterm documents the formula as
  `Agg = HM(Mem, Priv, Util)` — Mem = forgetting/memorization score, Priv = the OpenUnlearning
  leakage/privacy proxy (an MIA-based score), Util = retained utility/fluency. This maps
  directly onto the code as-implemented (`Mem_proxy`, `Privacy_proxy`, `Utility_proxy` →
  `Agg_proxy`, confirmed via `git diff` on `src/trainer/base.py` and
  `thesis_cleanup_audit/CHECKPOINT_SELECTION_PATCH.md` §1). **This `Priv`/`Privacy_proxy` term
  is an MIA-based membership-inference/leakage score — it is not PrivacyLens or PersistBench
  contextual privacy, and the two must not be conflated anywhere in the thesis text.** The
  formula also did not stay fixed for the whole thesis — do not describe one unchanged
  aggregation formula as used throughout: `Agg_proxy` (TOFU, includes the `Priv` term) →
  `Selection_proxy` (TOFU, same-day variant, `Priv` term dropped) → MUSE's `best_agg` (a
  different, MUSE-specific formula: harmonic mean of a retain-ROUGE utility proxy and a
  forget-ROUGE/extraction-strength memory proxy — **no leakage/privacy term at all**, since
  MUSE evaluation does not produce MIA scores). Chronologically: early TOFU checkpoint
  selection included Mem + leakage-proxy + utility; the privacy term was then dropped for some
  TOFU-full runs (`Selection_proxy`); MUSE selection (`best_agg`) balances only the
  MUSE-relevant forgetting/utility proxies, with no analogue of the leakage term at all
  (`thesis/docs/trainer_patch.md`).
- **Trade-off forgetting vs. utility?** Yes, this is the entire point of the harmonic-mean
  metrics — a harmonic mean collapses toward zero if either term is bad, which is exactly why
  CEU/GradAscent/GradDiff (good forgetting, zero utility) would score poorly under it even
  though they "forget well" by a naive read of `forget_truth_ratio` alone.
- **Excluded for collapsed generations / engineering problems?** Not documented as the reason
  for the TOFU-stage exclusions (CEU/GradAscent look like genuine utility collapse, not a
  parsing/generation bug), **but** generation collapse is explicitly documented as a real,
  encountered failure mode later in the project: MUSE-Books/Llama2/WGA produced 0% valid
  PersistBench output (`mechanistic/outputs/benchmark_paradox/FINAL_REPORT.md` §D–F, §I) —
  a real engineering/collapse exclusion, just at a different phase (privacy evaluation, not
  TOFU method selection).
- **Did the selected methods remain the same throughout MUSE-News/MUSE-Books?** The
  behavioral-layer set (BASE, RMU, WGA, SatImp, SimNPO) is consistent across both datasets and
  both MUSE-Books tracks. The **mechanistic** set narrows further and is **not** the same:
  only BASE/SatImp/SimNPO ever appear in a `gpu_extraction_provenance.json` — RMU and WGA are
  evaluated behaviorally on MUSE-News/Books but never mechanistically (`thesis/README.md` §4,
  confirmed repeatedly).
- **Why SatImp/SimNPO specifically (not RMU/WGA) for the mechanistic core?**
  **[USER-CONFIRMED]** — this replaces an earlier draft's speculative "matched pair" rationale.
  SatImp and SimNPO were chosen for the deep MUSE-News mechanistic case study because they
  showed the clearest, most direct pattern of PrivacyLens remaining approximately stable while
  PersistBench sycophancy degraded — the recognition/behavior mismatch itself, not a
  utility/forgetting-profile similarity, is what motivated the mechanistic investigation. This
  connects directly to the final verified results (§6/§7): on MUSE-News sycophancy, both
  SatImp and SimNPO worsen at every FR@K while PrivacyLens changes remain small (−0.40/−0.61
  pp), and this exact pair (dataset × category × these two methods) is what the subsequent
  manual audit → Experiment A → activation patching → Experiment B chain investigates. **Do
  not attribute RMU/WGA's exclusion from the mechanistic core to architectural differences as
  the primary reason** — RMU being a representation-editing method (vs. SatImp/SimNPO/WGA's
  preference-optimization family) and WGA's generation-collapse failure on one MUSE-Books
  track are real, repo-verified facts, but they are **secondary observations**, not the
  documented selection reason; the primary, user-confirmed reason is the recognition-vs-behavior
  pattern above.
- **Bottom line, stated plainly**: the final method set was reached "partly pragmatically," as
  the prompt anticipated — but the pragmatism shows up as *silence* in the documentation
  record (no rationale document at either narrowing point), not as an explicit ad hoc decision
  that was written down and can be quoted.

---

## 4. MUSE phase reconstruction

### A. MUSE-News

**Two tracks existed; only one is canonical** (full evidence:
`thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md`).

| | Track A (superseded) | Track B (canonical) |
|---|---|---|
| Base target | Official `muse-bench/MUSE-News_target` (Llama-2-7b), no local finetune | Locally finetuned Qwen2.5-7B-Instruct (`saves/finetune/muse_news_qwen25_7b_instruct_target`) |
| Methods | RMU, WGA, SimNPO, SatImp | BASE, RMU, WGA, SimNPO, SatImp |
| Checkpoint selection | Post-hoc, reading `MUSE_SUMMARY.json` across all saved checkpoints — **no `best_agg`, no in-training selection at all** | In-training `best_agg` (`metric_for_best_model=best_agg`), proven exact via `trainer_state.json` (§ below) |
| Selected checkpoints | (Track-A-specific paths, `*_ckpts_bs1_gc_sbatch`) | SatImp/SimNPO checkpoint-459, WGA checkpoint-306, RMU checkpoint-459 |
| Dates | 2026-07-01 → 07-04 | 2026-07-06 → 07-08 |
| Completeness | Complete: a real combined `FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv` exists | Complete through PrivacyLens + PersistBench + the entire mechanistic suite |
| Ever shown to supervisor? | **No** — grep-confirmed zero hits in `supervisor_update/`/`meeting_updates/` | Implicitly yes (feeds every later mechanistic report) |
| Read by anything downstream? | **No** — confirmed by `MUSE_NEWS_TRACK_RESOLUTION.md` §2/§4, no script or plot mixes the two tracks | Yes — every mechanistic artifact |
| Status | Real, complete, historical — preserved at `research_history/04_muse_track_a/` | **The canonical MUSE-News result cited throughout the thesis** |

**Question this phase answers**: closer to *"can the selected TOFU-narrowed methods produce a
complete, workable pipeline on a realistic benchmark at all"* than the prompt's framed
*"do methods generalize from TOFU to realistic knowledge"* — the actual sequence shows the
thesis solving an engineering/target-choice problem first (which base model, which target,
which selection mechanism) before any forgetting/utility generalization question is even
answered on this dataset.

**Why Track A was abandoned for Track B — state only what is known.** [USER-CONFIRMED: the
user does not remember the historical reason.] What is verifiable: Track A existed and was
completed (a real, working, end-to-end result); Track B became canonical; every downstream
mechanistic analysis uses Track B exclusively; **no verified contemporaneous rationale for the
switch is available**, in the repository or in the user's own recollection. An earlier draft of
this map speculated a reason ("methodological consistency with MUSE-Books," "built for the
mechanistic phase's model family") — that speculation is withdrawn, not restated, per explicit
user instruction. **Classification for the defense: THESIS PROVENANCE / BACKUP, not MAIN
TALK** (§11/§12) — it is honest, disclosable provenance, not a decision to present as reasoned.

**Standard MUSE evaluation**: ROUGE-based knowledge/verbatim memorization, `extraction_strength`,
`model_utility` (retain-side), computed in-line by open-unlearning's own evaluator during
training; `best_agg = harmonic_mean(clamp(retain_knowmem_ROUGE), 1 - mean(forget_knowmem_ROUGE,
forget_verbmem_ROUGE, extraction_strength))` selects the checkpoint (`thesis/docs/trainer_patch.md`).

**Checkpoint-selection proof, not assumption**: `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/
checkpoint-459/trainer_state.json` records `best_metric=0.19242792501682263`,
`best_global_step=459` — an exact match, to 17 significant figures, against the value
independently recorded in `SELECTED_MODEL_PATHS.tsv` (`thesis_cleanup_audit/
CHECKPOINT_SELECTION_PATCH.md` §4). Checkpoint-500 also exists on disk for both SatImp and
SimNPO — 459 was a metric-driven choice, not "the only checkpoint available."

### B. MUSE-Books

Two tracks, **both canonical** (no track-resolution ambiguity here, unlike MUSE-News):

| | Llama-2-7b track | Qwen2.5-7B-Instruct track (locally finetuned) |
|---|---|---|
| BASE | `muse-bench/MUSE-Books_target` (official HF) | `saves/finetune/muse_books_qwen25_7b_instruct_target` |
| SatImp | `saves/unlearn/muse_books_llama2_7b_satimp/checkpoint-153` | `saves/unlearn/muse_books_qwen25_7b_instruct_satimp/checkpoint-51` |
| SimNPO | `saves/unlearn/muse_books_llama2_7b_simnpo/checkpoint-408` | `saves/unlearn/muse_books_qwen25_7b_instruct_simnpo/checkpoint-51` |
| Selection | `best_agg`, same mechanism as MUSE-News Track B | `best_agg`, confirmed via `trainer_state.json`'s own `best_global_step=51` matching the replication document's independent statement (`thesis_cleanup_audit/EXPERIMENT_HISTORY.md` §6: "not an unresolved choice between steps 51 and 500") |
| Dates (behavioral) | 2026-07-09 → 07-11 | ~2026-07-12 |
| Mechanistic replication | 2026-09-06, reusing the exact frozen MUSE-News methodology | same |

**Question this phase answers**: does the MUSE-News mechanistic finding (recognition-behavior
dissociation on sycophancy) generalize to a second dataset? **Answer: no** — the replication's
own stated bottom line, quoted verbatim from `mechanistic/outputs/muse_books_weekly_update_analysis/
DISCOVERY_REPORT.md`: *"The full MUSE-News story does not replicate on MUSE-Books.
PrivacyLens again shows no Privacy-Collapse-style collapse, and the controlled A/B direction
is again lexically confounded. However, the central PersistBench behavioral split reverses or
becomes mixed: cross-domain FR@K is essentially unchanged/mixed, and sycophancy FR@K improves,
not worsens."* This is a genuine, reported negative-replication finding — important for both
thesis honesty and for the "why MUSE-News, why not MUSE-Books" defense narrative (§7).

---

## 4.5 Midterm state of the thesis

**Provenance: [MIDTERM-DOCUMENTED]** — per the source-access note at the top of this document,
the July 29 midterm presentation itself was not opened by this session; the following is the
user's own reported summary of what that milestone had already established, not an
independently re-derived reading of the `.pptx`. This section exists because the final
mechanistic experiments (§8) directly answer the one question this milestone left explicitly
open — the midterm is a real, dated checkpoint in the thesis's evolution, not a retrospective
framing device.

By 2026-07-29, the thesis had already established:

1. TOFU checkpoint selection had been completed.
2. Four methods were fixed: RMU, WGA, SimNPO, SatImp.
3. PrivacyLens was used as direct privacy-norm judgment.
4. PersistBench was introduced for open-ended contextual behavior.
5. A validity gate separated generation collapse from interpretable privacy failures.
6. PrivacyLens was often stable or improved.
7. PersistBench showed stronger degradation signals.
8. Effects were explicitly already described as non-universal — i.e. **the "heterogeneous, not
   general" framing in §6/§7/§I of this map is not a late addition**; it was already the
   midterm's own characterization of the results, months before the benchmark-paradox
   24-condition scan or the MUSE-News-sycophancy case study existed.
9. Mechanistic explanation was still missing.
10. The stated next step was to explain why PrivacyLens could remain stable while PersistBench
    degraded.

**Why this matters for the thesis narrative**: the final mechanistic chapters (§8, manual audit
→ Experiment A → activation patching → Experiment B) are the direct, evidenced answer to
exactly the question left open at item 10 above — this is a continuous research arc with a
documented midpoint, not two disconnected projects joined after the fact. Cross-reference:
§0.1 (Research question evolution), §9.5 (Final defense story).

---

## 5. Privacy-evaluation phase reconstruction

**When it entered the workflow**: PrivacyLens first appears at TOFU-scaling scale
(`run_privacylens_full_before_after.sh`, 2026-06-17) — i.e. **before** MUSE existed in the
thesis at all. PersistBench enters later, at the MUSE-News Track-A/B behavioral-evaluation
stage (first generation job 2026-07-05/08). There is **no proposal or design document stating
the original hypothesis in prose** — `thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md` and
`EXPERIMENT_HISTORY.md` both confirm no rationale document exists for *why* PrivacyLens/
PersistBench specifically were chosen as the privacy axis. The closest thing to a stated
hypothesis is the **benchmark_paradox** report's own framing (see below), which is dated to
the mechanistic phase (2026-09), i.e. it documents what was *found*, not a *prior* hypothesis
written down beforehand. **NEEDS USER CONFIRMATION**: was "better forgetting may harm
contextual privacy" the actual working hypothesis at the time PrivacyLens/PersistBench were
first adopted (mid-2026), or is that framing a retrospective one applied only once the
paradox was found?

### PrivacyLens

- **What it measures**: explicit MCQ-style recognition of privacy norms (493-case eval).
- **How run**: `thesis/scripts/privacylens/eval_privacylens_mcq_local.py` (+ `_local_strict`,
  `_forced_choice` variants) against the frozen `external/privacy-collapse/benchmarks/
  privacylens/data/main_data.json`.
- **Models/methods/datasets**: BASE/RMU/WGA/SatImp/SimNPO on MUSE-News (Qwen), MUSE-Books
  (both Llama-2 and Qwen tracks); also every TOFU-scaling model size in Phase 2.
- **Scalar accuracy**: MUSE-News: 92.29% (BASE) → 91.89% (SatImp) / 91.68% (SimNPO); MUSE-Books:
  even more stable (cosine 0.991 on the representation side — see below).
- **Representation analysis**: hidden-state direction cosine between BASE and each unlearned
  model's "privacy-aware vs. not" decision direction — 0.937 (SatImp) / 0.938 (SimNPO) on
  MUSE-News; 0.991 on MUSE-Books (highly aligned, i.e. explicit judgment representation barely
  moves).
- **Canonical outputs**: `outputs/privacylens_muse_{news_qwen25,books_llama2,books_qwen25}_selected/`.

### PersistBench

- **Categories evaluated**: cross-domain, sycophancy, beneficial-memory-usage.
- **Generation setup** (confirmed via actual vLLM server logs, not assumed —
  `thesis/docs/generation_provenance.md`): `temperature=0.0` (greedy/deterministic),
  `max_tokens=96`, prompt truncated to the last 1800 tokens, `max_model_len=2048`, 3
  generations/item for cross-domain and sycophancy, 1/item for beneficial-memory. For
  Qwen-family runs, effective `repetition_penalty=1.05` (the checkpoint's own
  `generation_config.json` default, confirmed via vLLM startup log) — **not** 1.08, see §14.
  Llama-2-7b MUSE-Books track: repetition penalty/top_p/top_k **unresolved, honestly
  flagged UNKNOWN** (no matching override-log line found).
- **Judge setup**: a locally-served `Qwen/Qwen2.5-7B-Instruct`, **not** the canonical
  PersistBench judge (`moonshotai/kimi-k2-thinking`) — true for **100% of PersistBench
  results in this repository**, both datasets, all tracks (`thesis/README.md` §9/§15,
  `PERSISTBENCH_MODIFICATIONS.md` §6). This requires a caveat wherever PersistBench numbers
  are stated in the thesis text.
- **FR@K / metrics**: official `external/PersistBench/analysis/failure_rates.py` (confirmed
  unmodified upstream code — `PERSISTBENCH_MODIFICATIONS.md` §0). FR@1/2/3 reported per
  category.
- **Valid-generation checks**: a thesis-authored downstream classifier
  (`tmp_paths/create_persistbench_validity_summary_with_muse.py`) flags empty/gibberish/
  web-contaminated/tool-schema/collapsed outputs as invalid, not privacy failures. This
  classifier's own "custom privacy-context %" number is **explicitly marked non-comparable**
  to the official FR@K numbers by the thesis's own reconciliation document — do not conflate
  the two (§14).
- **Canonical outputs**: `external/PersistBench/outputs/muse_{news_qwen25,books_llama2,
  books_qwen25}_selected_full/`.

**Logical purpose / hypothesis — corrected in this revision.** An earlier draft of this map
stated that no prior design document contained the privacy hypothesis, and that the "privacy
paradox" framing was purely retrospective. **This is corrected**: [EXPOSE-DOCUMENTED] the
Exposé already carried the working hypothesis that unlearning may distort internal
representations and thereby degrade the application of contextual privacy norms, well before
PrivacyLens or PersistBench were adopted as the specific instruments (§0.1). What remains true
of the *repository itself* is narrower: no committed `.md`/`.py` file inside this git history
states that hypothesis in prose — the benchmark-paradox report's own framing (§B of
`mechanistic/outputs/benchmark_paradox/FINAL_REPORT.md`: does explicit privacy-norm judgment
move together with, or independently of, contextual/generative privacy behavior after
unlearning?) is the closest *repository-internal* statement, and its "privacy paradox" finding
(PrivacyLens improves/stable while strict-valid PersistBench failures *increase*, in 7 of 16
clean dual-benchmark conditions, most consistently for RMU) is real evidence *for* the
originally-hypothesized effect, not the origin of the hypothesis itself.

**Benchmark evolution — [EXPOSE-DOCUMENTED / REPO-VERIFIED].** The original Exposé planned
independent contextual-privacy benchmarks including **PrivacyLens** and **CIMemories**. The
actual final implementation evolved to **PrivacyLens** and **PersistBench** — PersistBench
became the generation-side (contextual/free-generation behavior) benchmark actually used in
the empirical pipeline, in place of CIMemories. This is stated here as normal research
development, not hidden: the planned contextual-privacy evaluation axis was retained in spirit
(an explicit-judgment benchmark paired with a generation-behavior benchmark), while the
specific generation-side tool changed. No file in the repository documents *why* CIMemories
was not used instead of/alongside PersistBench — **NEEDS USER CONFIRMATION** if this detail
matters for the thesis's methods section.

---

## 6. Full behavioral results matrix

Only results that materially feed a thesis conclusion — not every debugging number. Judge
caveat (local Qwen, not canonical Kimi-K2) applies to every PersistBench column; not repeated
per cell.

| Dataset / category | Method | Forgetting outcome (MUSE ROUGE / TOFU truth-ratio, where applicable) | Utility outcome | PrivacyLens (Δ) | PersistBench FR@1 (before→after) | Interpretation |
|---|---|---|---|---|---|---|
| MUSE-News, sycophancy | SatImp | (standard MUSE metrics; `best_agg`-selected checkpoint-459) | Retained per `best_agg` selection | 92.29%→91.89% (−0.40 pp, ~stable) | 9.5%→12.0% (worsens at every K: 9.5/12.5/12.5→12.0/17.0/17.0) | **Selected mechanistic case study** — degrades |
| MUSE-News, sycophancy | SimNPO | same | same | 92.29%→91.68% (−0.61 pp, ~stable) | 9.5%→11.5% (9.5/12.5/12.5→11.5/15.0/15.0) | **Selected mechanistic case study** — degrades |
| MUSE-News, cross-domain | SatImp | same checkpoint | same | (not separately tracked here) | 3.5%→2.0% | *Improves* — considered, explicitly not pursued mechanistically |
| MUSE-News, cross-domain | SimNPO | same checkpoint | same | — | 3.5%→1.5% | *Improves* — same |
| MUSE-Books, sycophancy | SatImp/SimNPO | (checkpoint-51, Qwen track) | — | cosine 0.991 (even more stable) | **improves**, does not replicate MUSE-News | Negative replication (real finding, §4B) |
| MUSE-Books, cross-domain | SatImp/SimNPO | same | — | — | essentially unchanged/mixed | Negative replication |
| TOFU, Qwen2.5-7B | RMU | forget_truth_ratio moves toward reference | model_utility retained | 77.49%→82.96% (**improves**, +5.48 pp) | strict 5.51%→6.96% (**worsens**, +1.45 pp) | **Privacy paradox** (strongest controlled example — bootstrap CI [2.637,8.316] for ΔPL, McNemar p=0.0002 on PL transitions) |
| TOFU, Qwen2.5-7B | WGA | — | — | 77.49%→80.93% (improves) | 5.51%→5.11% (**improves**) | Both improve — control/counterexample |
| TOFU, Llama3.1-8B | RMU | — | — | 34.48%→52.54% (improves) | 2.63%→3.32% (worsens) | Privacy paradox |
| MUSE-Books, Qwen2.5-7B | RMU | — | — | 85.40%→52.97% (**collapses**, −32.4 pp) | 3.23%→6.57% (worsens) | Both worsen (not a paradox — real, larger degradation) |
| MUSE-Books, Llama2-7B | WGA | — | — | 29.69%→0% | 0% valid generations | **Generation collapse** — excluded from all strong claims |

**Metric-comparability caveat, stated explicitly per the prompt's instruction**: TOFU's
`forget_truth_ratio`/MIA scores, MUSE's ROUGE/`extraction_strength`-based forgetting metrics,
and PersistBench's category-specific FR@K are **not directly comparable across datasets** —
they are different measurement constructs (synthetic QA-pair memorization vs. real-document
knowledge retention vs. contextual behavioral failure rate). Nothing in this table implies a
common scale; each row's forgetting/PrivacyLens/PersistBench numbers are only comparable
within their own dataset row.

---

## 7. Why MUSE-News sycophancy became the mechanistic case study

**Primary, user-confirmed reason** [USER-CONFIRMED]: SatImp and SimNPO were chosen for the
deep MUSE-News mechanistic case study because they showed the clearest direct pattern of
PrivacyLens remaining approximately stable **while** PersistBench sycophancy degraded — this
recognition/behavior mismatch is what motivated the mechanistic investigation, not a
population-representativeness argument. The rest of this section (repository evidence) is
fully consistent with, and adds supporting detail to, that primary reason — reconstructed
directly from `mechanistic/outputs/benchmark_paradox/FINAL_REPORT.md` (the 24-condition scan)
and `mechanistic/experiments/muse_news_sycophancy_paradox/report/FINAL_REPORT.md` (the
case-specific behavioral re-derivation):

- **What happened on MUSE-News sycophancy**: worsens at every FR@K for both methods (SatImp
  9.5%→12.0%/12.5%→17.0%; SimNPO 9.5%→11.5%/12.5%→15.0%), on a **100%-valid, non-collapsed**
  200-row population (zero excluded generations) — this validity property is exactly why this
  specific setting, rather than a noisier one, was chosen for deep mechanistic follow-up.
- **What happened on MUSE-News cross-domain**: *improves* for both methods (3.5%→2.0%/1.5%) —
  considered and explicitly not pursued mechanistically, reported as a negative/contrast result.
- **What happened on MUSE-Books sycophancy**: *improves*, does not replicate the MUSE-News
  degradation at all (§4B, §6).
- **Why MUSE-News sycophancy was interesting**: it is the one setting in the whole
  cross-dataset/cross-method scan that combines (a) a clean, 100%-valid population, (b) a
  worsening effect at *every* K for *both* mechanistic-core methods, and (c) survives an
  intersection-valid robustness check. The broader 24-condition scan classifies MUSE-News
  Qwen SatImp/SimNPO as "**Both worsen**" (not technically a "paradox," since PrivacyLens also
  moves slightly negative, −0.41/−0.61 pp) under a strict sign-based rule, while the dedicated
  case-study report treats the same PrivacyLens delta as "~stable" using an explicit ±0.5–1.0pp
  tolerance band that the paradox report itself defines and reports as still qualifying 8–9 of
  16 conditions. **This is a real internal framing difference across two documents that both
  survive as canonical — flagged in §14, not smoothed over here.**
- **Why it was not representative of every result**: cross-domain (same dataset, same
  checkpoints) improves; MUSE-Books (different dataset, same methods) does not replicate at
  all. The thesis's own selection logic is explicit about this — see
  `THESIS_WRITING_PLAN.md` §1: *"Focusing on the one setting where a genuine degradation was
  found and manually verified."*
- **Why it was still scientifically useful as a case study**: it is a real, validated,
  causally-tractable instance of a broader, heterogeneous phenomenon (the "privacy paradox"),
  not a representative average — exactly the right object for deep mechanistic work, which
  needs a *clean, reproducible instance*, not a *population-average effect size*.

```
BROAD EXPERIMENTS (24-condition benchmark-paradox scan, TOFU + MUSE-News + MUSE-Books,
                    4 methods × 2 model families)
  ↓
interesting, anomalous, but not universal case:
  MUSE-News × PersistBench-sycophancy × SatImp/SimNPO
  (100%-valid population, worsens at every K, both methods; cross-domain and MUSE-Books
   do NOT show the same effect)
  ↓
DEEP MECHANISTIC ANALYSIS (manual audit → clean patching → free-generation test →
                            reproducibility check → recognition probe → memory probe)
```

---

## 8. Integration of the frozen mechanistic lineage

**This section reuses, and does not reinterpret or rerun, the canonical documentation already
frozen under `mechanistic/experiments/muse_news_sycophancy_final_mechanism/`.** Every number
below is quoted, not recomputed.

1. **Behavioral discovery** — §6/§7 above; canonical source `mechanistic/experiments/
   muse_news_sycophancy_paradox/report/FINAL_REPORT.md`.
2. **Manual audit** — **27 candidates** manually reviewed → **10 HIGH_CONFIDENCE_FAILURE**, 9
   LIKELY_JUDGE_NOISE, 8 AMBIGUOUS. The dominant exclusion reason: a "task-compliance
   confound" (model substantively answers while also validating the user's belief — judge-
   noisy, not a clean failure). 10 (model, case) treatment instances = **8 unique
   PersistBench IDs** (SatImp 6, SimNPO 4, 2 shared: `aa71a70f…`, `7079a34e…`). Canonical:
   `.../muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit/clean_selection.json`.
3. **Clean teacher-forced BASE↔unlearned activation patching.** **Canonical direction
   convention, reproduced verbatim, not to be re-flipped:**
   - **Forward** = donor **BASE** → recipient **unlearned**. At L21–27: SatImp **+0.138**
     CI[0.119,0.158] 6/6; SimNPO **+0.111** CI[0.077,0.143] 4/4. Shifts the unlearned
     recipient toward the BASE/safe continuation.
   - **Reverse** = donor **unlearned** → recipient **BASE**. At L21–27: SatImp **−0.141**
     CI[−0.161,−0.123] 6/6; SimNPO **−0.113** CI[−0.144,−0.078] 4/4. Shifts BASE toward the
     sycophantic continuation.
   - L14–20 comparable magnitude to L21–27, both directions. Canonical:
     `.../activation_patching_clean_audit/CLEAN_RERUN_REPORT.md`.
4. **Free-generation Experiment 1** — only 3/6 SatImp and 0/4 SimNPO treatment cases reproduce
   as a fresh-generation FAILURE at all; one confident, both-judges-agreed, bidirectional
   repair for SatImp at L14-20 (`aa71a70f`); SimNPO untestable. Judge agreement (Qwen vs.
   Gemma-3) only 59%. Canonical: `EXPERIMENT_1_RESULTS.md`.
5. **Reproducibility diagnostic** — a fresh rerun of the literal original vLLM pipeline
   matches its own July results only 55% of the time; Experiment 1's HF approximation matches
   70% — the non-reproduction problem is predominantly generation-environment/behavioral
   instability, not an Experiment-1-specific bug. Canonical: `repro_check/REPRO_CHECK_RESULTS.md`.
6. **Experiment A — recognition vs. behavior**: **10/10 (100%)** genuine failure instances
   robustly (both MCQ orderings) answer the anti-sycophancy question correctly. Canonical:
   `EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md`.
7. **Experiment B — memory/context patching**: injecting a WITH_MEMORY state into a NO_MEMORY
   context shifts preference toward sycophantic, strongest at **L14-20** (BASE 10/10, SatImp
   5/6, SimNPO 2/4 — small n) — **but BASE shows the effect at least as strongly as the
   unlearned models**, so this experiment does **not** establish unlearning-specificity.
   Canonical: `EXPERIMENT_B_MEMORY_INTEGRATION.md`. (This has its **own**, separate
   forward/reverse terminology from item 3 above — do not merge the two conventions.)
8. **Final synthesis** — `FOCUSED_THESIS_SYNTHESIS.md` (canonical, frozen) reports H1
   **PARTIALLY SUPPORTED**, H2 **SUPPORTED**, H3 **PARTIALLY SUPPORTED**. **This map records a
   resolved, authoritative final wording below (§ "Final hypothesis wording"), which
   preserves the frozen document's own wording as historical context but supersedes it as the
   preferred phrasing for the thesis text and defense**, per explicit instruction: do not
   silently pick one wording as if the other did not exist.

### Final hypothesis wording (authoritative for the thesis text and defense)

| | Frozen-document wording (`FOCUSED_THESIS_SYNTHESIS.md`, historical) | **Authoritative final wording (this revision)** |
|---|---|---|
| **H1** — "Machine unlearning generally degrades contextual privacy." | PARTIALLY SUPPORTED | **NOT SUPPORTED AS A GENERAL CLAIM.** Reason: effects are heterogeneous across dataset/category/method (§6/§7). Important follow-up, not a retraction: specific, real, causally-verified harmful privacy-context effects **do occur** in particular settings (MUSE-News sycophancy, SatImp/SimNPO) — "not general" must not be read as "no effect exists." |
| **H2** — "Unlearning can preserve explicit privacy/norm recognition while changing contextual privacy behavior." | SUPPORTED | **SUPPORTED.** Unchanged — 10/10 genuine failure instances robustly answer the explicit anti-sycophancy MCQ correctly (§8 item 6). |
| **H3** — "Unlearning specifically altered/strengthened the tested memory-integration pathway." | PARTIALLY SUPPORTED | **NOT ESTABLISHED.** Experiment B establishes that memory/context is causally involved in the safe-vs-sycophantic preference — it does **not** establish that the specific tested pathway is uniquely strengthened by unlearning (BASE shows the same channel at least as strongly as SatImp and more consistently than SimNPO, §8 item 7). |

**Both wordings describe the identical underlying evidence** — the difference is phrasing
precision (e.g. "partially supported" is ambiguous between "the effect is real but narrower
than claimed" and "the effect is real but unlearning-specificity is unestablished"; the
authoritative wording disambiguates this for H1 and H3 specifically). Use the authoritative
column in new thesis/slide text; cite the frozen document's wording only when directly quoting
it as a source.

---

## 9. End-to-end thesis story

```
"How well do current unlearning methods forget, at all, on a standard benchmark?"
  ↓ finding: 10 methods run correctly; 3 (CEU, GradAscent, GradDiff) effectively destroy
    general utility rather than forgetting selectively.
"Which methods are strong enough (utility + forgetting balance) to study further?"
  ↓ selection (undocumented rationale, evidence-consistent reconstruction): SatImp, SimNPO,
    RMU, WGA — carried through TOFU-full scaling up to 14B.
"Do these methods produce a complete, workable pipeline on a realistic benchmark (MUSE-News)?"
  ↓ finding: yes, but only after abandoning a first, complete attempt (official-target
    Track A) in favor of a locally-finetuned target (Track B) — a real pivot, not a
    continuation.
"Do these methods behave similarly across a second, related dataset (MUSE-Books)?"
  ↓ finding: broadly yes at the behavioral-forgetting/utility level (both use best_agg,
    both produce complete evaluations).
"What happens to privacy/contextual behavior after unlearning, and is the effect uniform?"
  ↓ finding: heterogeneous — a 24-condition scan across TOFU/MUSE-News/MUSE-Books finds a
    "privacy paradox" (explicit recognition stable/improves, contextual behavior worsens) in
    7/16 clean conditions, most consistently for RMU; other conditions show both-improve,
    both-worsen, or reverse patterns.
"Is the privacy effect general, or does it depend on dataset and category?"
  ↓ finding: depends on both — MUSE-News sycophancy worsens at every K for SatImp/SimNPO;
    the same dataset's cross-domain category improves; MUSE-Books does not replicate the
    sycophancy degradation at all.
"Why does MUSE-News sycophancy specifically worsen, mechanistically?"
  ↓ mechanistic investigation begins, narrowed to this one clean, validated, worst-case
    instance (§7).
"Did the model forget the anti-sycophancy rule itself?"
  ↓ no — 10/10 manually-verified genuine failures still correctly answer an explicit MCQ
    probe of the rule, in both answer orderings (Experiment A).
"Do internal BASE-vs-unlearned representation differences causally matter?"
  ↓ yes, strongly, at the teacher-forced level (clean activation patching, both directions,
    both methods); only partially (1 clean example, SatImp only) transfers to actual free
    generation, and free generation itself is shown to be only 55-70% self-reproducible even
    under the literal original pipeline (reproducibility diagnostic).
"Is stored user memory/context causally involved in the preference shift?"
  ↓ yes — injecting a memory-conditioned state into a memory-free prompt shifts preference
    toward sycophantic, most consistently at L14-20 (Experiment B).
"Did unlearning specifically create or amplify that memory-integration channel?"
  ↓ not established — BASE shows the same tested channel at least as strongly as SatImp and
    more consistently than SimNPO (Experiment B's central negative/non-confirmatory finding).
Final thesis interpretation:
  unlearning, in this specific, well-evidenced case, changed how existing knowledge and
  contextual signals get translated into downstream generated behavior — not that it erased
  privacy-relevant knowledge (recognition is intact), and not that it broke a specific,
  newly-identified memory mechanism (the tested channel pre-exists in BASE).
```

---

## 9.5 Final defense story

A shorter, defense-ready version of §9 above, anchored explicitly to the RQ evolution in §0.1.
Same evidence, tighter narrative arc for the talk itself:

1. Machine unlearning is evaluated mainly by whether data is forgotten.
2. Original thesis question [EXPOSE-DOCUMENTED, §0.1]: can unlearning create contextual-privacy
   side effects elsewhere, beyond the forgotten data itself?
3. Broad TOFU exploration of 10 methods (§2).
4. Narrow to four usable methods using the forgetting/utility trade-off — no severe utility
   collapse, no formal ranked table (§3).
5. Scale and evaluate on TOFU/MUSE (§2, §4).
6. Evaluate contextual privacy with PrivacyLens and PersistBench — the final-implementation
   evolution of the Exposé's planned PrivacyLens/CIMemories pairing (§5 "Benchmark evolution").
7. Find heterogeneous privacy effects (§6, benchmark-paradox 24-condition scan) — this is
   exactly the midterm's own open finding, not a new discovery (§4.5).
8. Identify a clean case, for the user-confirmed reason (§7): MUSE-News sycophancy ×
   SatImp/SimNPO — PrivacyLens approximately stable, PersistBench worsens.
9. Manually verify failures (27 → 10 HIGH_CONFIDENCE_FAILURE, §8 item 2).
10. Ask whether models forgot the rule: **No** — Experiment A, 10/10 (§8 item 6).
11. Ask whether BASE-vs-unlearned internal state differences causally matter: **Yes** —
    teacher-forced activation patching (§8 item 3).
12. Ask whether stored user context causally matters: **Yes** — Experiment B (§8 item 7).
13. Ask whether unlearning simply created/strengthened that memory pathway: **Not
    established** — BASE shows it strongly too (§8 item 7, §"Final hypothesis wording").
14. Final conclusion: unlearning can leave explicit privacy recognition intact while changing
    how contextual signals and existing knowledge are translated into behavior — the direct,
    evidenced answer to the question the midterm left explicitly open (§4.5).

---

## 10. Code ↔ thesis mapping

| Thesis phase | Main question | Code/scripts | Inputs/config | Canonical outputs | Presentation counterpart |
|---|---|---|---|---|---|
| TOFU baseline sweep | Do all 10 methods run correctly at small scale? | `research_history/01_tofu_baselines/scripts/run_{qwen15,llama1b,qwen3b}_*_a180.sh` | `configs/eval/tofu.yaml` (pre-thesis-edit), stock method configs | `research_history/01_tofu_baselines/manifests/*trainer_state.json` | Slide: "TOFU broad method comparison" |
| Model/method scaling + checkpoint-selection dev | Do methods hold at 14B/full-forget; how to pick "best" checkpoint? | `research_history/02_model_method_scaling/scripts/*`, `research_history/03_checkpoint_selection_development/scripts/*`, `src/trainer/base.py` (`Agg_proxy`/`Selection_proxy`, then `best_agg`) | `configs/model/Qwen2.5-14B-Instruct.yaml` | `research_history/02.../manifests/`, `03.../trainer_snapshots/*.bak_*` | Slide: "Selecting methods for deeper study" |
| MUSE-News Track A (superseded) | Does the official-target pipeline work end-to-end? | `research_history/04_muse_track_a/scripts/*` | official `muse-bench/MUSE-News_target` | `research_history/04.../manifests/openunlearning_selection/FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv` | Backup slide only ("a pivot we made") |
| MUSE-News Track B (canonical) + MUSE-Books | Complete forgetting/utility/privacy pipeline on realistic data | `thesis/scripts/muse_news/*`, `thesis/scripts/muse_books/*` | `best_agg` via `src/trainer/base.py` | `saves/final_muse_{news_qwen25_7b_instruct,books_llama2_7b,books_qwen25_7b_instruct}_selection/SELECTED_MODEL_PATHS.tsv` | Slides: "MUSE-News/Books setup", "Forgetting/utility results" |
| PrivacyLens evaluation | Does explicit privacy-norm recognition survive unlearning? | `thesis/scripts/privacylens/eval_privacylens_mcq_local.py` (+ variants) | `external/privacy-collapse/benchmarks/privacylens/data/main_data.json` | `outputs/privacylens_muse_*_selected/` | Slide: "Privacy evaluation setup" |
| PersistBench evaluation | Does contextual/generative privacy behavior change? | `thesis/scripts/persistbench/run_persistbench_muse_*_selected.sh` + local-judge scripts | `external/PersistBench` (4 patched files, `thesis/docs/persistbench_patch.md`) | `external/PersistBench/outputs/muse_*_selected_full/*.json` | Slide: "Privacy evaluation setup" |
| Benchmark-paradox discovery | Is the privacy effect uniform across datasets/methods? | `mechanistic/analyze_benchmark_paradox.py`, `prepare_paradox_mechanistic_candidates.py` | frozen generation/judgment JSON across all datasets | `mechanistic/outputs/benchmark_paradox/FINAL_REPORT.md` + 6 plots | Slide: "Privacy results: heterogeneous effects" |
| MUSE-News sycophancy case selection | Why this one setting? | `mechanistic/experiments/muse_news_sycophancy_paradox/report/*` | Track B PersistBench/PrivacyLens outputs | `.../report/FINAL_REPORT.md` | Slide: "Why MUSE-News sycophancy?" |
| Manual failure audit | Which behavioral transitions are genuine failures? | `.../paradox/audit/manual_transition_audit.csv` + build scripts | 27 candidate transitions | `.../activation_patching_clean_audit/clean_selection.json` | Slide: "Manual failure validation" |
| Clean teacher-forced patching | Do BASE↔unlearned representations causally matter? | `run_activation_patching_clean.py` | `clean_selection.json` | `.../CLEAN_RERUN_REPORT.md` + `plots/clean_per_example_shifts.png` | Slide: "Activation patching" |
| Free-generation Exp. 1 + repro check | Does patching change actual generation? Is non-reproduction a bug? | `mechanistic/muse_news_activation_patching.py`, `repro_check/*` | clean 10-case set | `EXPERIMENT_1_RESULTS.md`, `repro_check/REPRO_CHECK_RESULTS.md` | Slide: "Free-generation / reproducibility qualifier" |
| Experiment A | Does explicit recognition survive genuine failures? | `expA_mcq/extract_missing_5.py` + reused `persistbench_sycophancy_mcq` | `clean_selection.json` memories/queries | `EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md` | Slide: "Recognition–behavior gap" |
| Experiment B | Is memory/context causally involved, and unlearning-specific? | `expB_memory/run_expB_memory_patch.py` | WITH_MEMORY/NO_MEMORY manifests + representations | `EXPERIMENT_B_MEMORY_INTEGRATION.md` | Slide: "Memory/context experiment" |
| Final synthesis | What does it all mean? | — | all of the above | `FOCUSED_THESIS_SYNTHESIS.md`, `THESIS_RESULTS_CHEATSHEET.md` | Slides: "What mechanism is/isn't supported", "Final conclusions" |
| MUSE-Books mechanistic replication | Does the story generalize? | `mechanistic/outputs/muse_books_weekly_update_analysis/*` | reused News methodology | `DISCOVERY_REPORT.md` | Backup/footnote on "Why MUSE-News" slide |
| Repository provenance audit | Is every claim traceable and correctly labeled? | `thesis_cleanup_audit/build_inventory.py` + this session | entire repo | `thesis_cleanup_audit/*.md`, `MASTER_THESIS_MAP.md` (this file) | Not presented — methodology backing only |

---

## 11. Proposed presentation slide sequence

**Revised this pass to match the task's explicit 19-slide skeleton (item K)**, which folds
"MUSE-News/Books setup" and "forgetting/utility results" into one slide, splits "privacy
evaluation setup" into its own PrivacyLens-vs-PersistBench slide ahead of the heterogeneity
result, splits "activation patching" into a concept slide and a result slide, and adds an
explicit "final answers to RQs" slide (tied to §0.1's RQ evolution) immediately before
conclusions. Checked against the repository's actual evidence weight, not assumed. Total
main-deck: **19 slides**, ≈ 25–28 minutes at the given per-slide estimates — trim per your
actual time budget (this errs toward completeness, cut per §12's OMIT/BACKUP guidance if you
need fewer).

| # | Title | Message | Evidence shown | Figure/table needed | Source | Exists? | Time | Main/Backup |
|---|---|---|---|---|---|---|---|---|
| 1 | Title | — | — | — | — | — | 0.5m | MAIN |
| 2 | Motivation / gap | Standard unlearning eval focuses on forgetting; privacy needs contextual reasoning; model edits can have non-local effects [EXPOSE-DOCUMENTED, §0.1] | — | none | Exposé (per user report) | — | 1m | MAIN |
| 3 | Research questions | RQ1–RQ3, shown as an Exposé→Midterm→Final evolution, not presented as invented after the results | §0.1 table | text slide | `THESIS_WRITING_PLAN.md` §2 + §0.1 this map | exists as text | 1.5m | MAIN |
| 4 | End-to-end thesis pipeline | TOFU → method selection → MUSE → PrivacyLens/PersistBench → heterogeneous effects → mechanistic case study | full pipeline diagram | 1 new diagram | this map §1/§9/§9.5 | **MISSING — must be generated** | 1.5m | MAIN |
| 5 | TOFU broad method exploration | 10 methods; CEU/GradAscent/GradDiff collapse utility | §2 table (this map) | 1 new bar chart (utility vs. forget-quality per method) | raw `trainer_state.json` (§2) | **MISSING — data exists, no plot** | 1.5m | MAIN |
| 6 | Method/checkpoint selection | Forgetting/utility trade-off narrows 10→4 (RMU/WGA/SatImp/SimNPO), no formal ranked table; `Agg`(Mem,Priv,Util)→`Agg_proxy`/`Selection_proxy`→`best_agg` metric evolution | §3 narrative + formula | table/formula slide | this map §3, `thesis/docs/trainer_patch.md` | exists as text | 2m | MAIN |
| 7 | Move to MUSE | MUSE-News/Books setup + forgetting/utility results, both datasets, `best_agg` selection | checkpoint table + bar chart | table + 1 new chart | `thesis/README.md` §6, `MUSE_SUMMARY.json` | table exists; chart **MISSING** | 2m | MAIN |
| 8 | PrivacyLens vs. PersistBench | Explicit-recognition benchmark + contextual-generation benchmark; judge caveat; benchmark evolution (Exposé's PrivacyLens+CIMemories → final PrivacyLens+PersistBench) [EXPOSE-DOCUMENTED for the planned pairing] | settings table | table | `thesis/docs/generation_provenance.md`, §5 this map | exists as text | 1.5m | MAIN |
| 9 | Behavioral result: heterogeneous privacy effects | Paradox in 7/16 clean conditions; not uniform — already the midterm's own framing, not a late addition [MIDTERM-DOCUMENTED, §4.5] | benchmark-paradox quadrant plots | `overall_quadrant.png`, `dataset_level_summary.png` | `mechanistic/outputs/benchmark_paradox/` | **EXISTS AND USABLE** | 2m | MAIN |
| 10 | Why MUSE-News sycophancy? | User-confirmed reason: the clearest case of PrivacyLens stable + PersistBench worse, for SatImp/SimNPO specifically [USER-CONFIRMED, §7] | FR@K table/bar | 1 new bar chart | `.../muse_news_sycophancy_paradox/report/FINAL_REPORT.md` | **MISSING — must be generated** (data in report table) | 1.5m | MAIN |
| 11 | Manual failure validation | 27 candidates → 10 genuine failures, why the rest were excluded | audit summary | table (exists in `manual_transition_audit.csv`) | `clean_selection.json` | exists, needs slide formatting | 1.5m | MAIN |
| 12 | Recognition–behavior gap | 10/10 still know the rule when asked directly — this is the midterm's open question, answered [MIDTERM-DOCUMENTED, §4.5] | 10-row table + 1 worked example | `EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md` table | exists, needs reformatting | 2m | MAIN |
| 13 | Activation patching — concept | What teacher-forced donor→recipient patching means, and the canonical forward/reverse convention (§8 item 3) | donor/recipient diagram | 1 new diagram | this map §8 item 3 | **MISSING — must be generated** | 1m | MAIN |
| 14 | Activation patching — result | BASE↔unlearned representations causally shift the preference | layer-range plot | `clean_per_example_shifts.png` | `activation_patching_clean_audit/plots/` | **EXISTS AND USABLE** | 2m | MAIN |
| 15 | Free-generation qualifier | Patching's effect on real generation is weaker and generation itself is only 55–70% self-reproducible | 1–2 sentences + numbers | — | `EXPERIMENT_1_RESULTS.md`, `repro_check/` | n/a (text) | 1.5m | MAIN |
| 16 | Memory/context causal experiment | Context is causally involved, but not shown unlearning-specific (BASE ≥ unlearned) | forward/reverse shift table | Table 3 (exists as markdown in `EXPERIMENT_B_MEMORY_INTEGRATION.md`) | exists, needs porting | 2m | MAIN |
| 17 | Mechanistic synthesis | Two causal axes (weights vs. context) both point the same way; layer-range tension explicitly flagged, not smoothed over | 1 new synthesis diagram | — | `FOCUSED_THESIS_SYNTHESIS.md` | **MISSING — must be generated** | 2m | MAIN |
| 18 | Final answers to RQs | RQ1: not supported as general claim (heterogeneous, but real effects occur); RQ2: supported; RQ3: causal-yes for both axes, unlearning-specificity of the memory channel not established | RQ1–RQ3 verdict table | table | §"Final hypothesis wording" this map, §0.1 | exists as text | 1.5m | MAIN |
| 19 | Contributions / conclusion | 5 contributions; answers the question the midterm left open | — | — | `THESIS_WRITING_PLAN.md` §10 | n/a | 1.5m | MAIN |
| B1 | MUSE-News Track A/B pivot | Track A existed and was completed; Track B is canonical; no known reason for the switch [USER-CONFIRMED: unknown] | provenance table | `MUSE_NEWS_TRACK_RESOLUTION.md` §2 | exists | 1.5m | BACKUP |
| B2 | Checkpoint-selection metric mechanics | `Agg`(Mem,Priv,Util)/`Agg_proxy`/`Selection_proxy`/`best_agg` exact formulas, and why `Priv` ≠ PrivacyLens | formula slide | `thesis/docs/trainer_patch.md`, §3 this map | exists as text | 1.5m | BACKUP |
| B3 | Full reproducibility per-case table | Every case's repro rate | table | `repro_check/repro_check_judged.json` | exists | 1.5m | BACKUP |
| B4 | MUSE-Books mechanistic replication detail | Full negative-replication numbers | table + quotes | `muse_books_weekly_update_analysis/DISCOVERY_REPORT.md` | exists | 2m | BACKUP |
| B5 | Generation-provenance correction | The 1.05-vs-1.08 repetition-penalty documentation error | text | `thesis/docs/generation_provenance.md` §3 | exists | 1m | BACKUP |
| B6 | PersistBench judge/patch engineering detail | 4 patched files, local-judge rewrite | table | `thesis_cleanup_audit/PERSISTBENCH_MODIFICATIONS.md` | exists | 1.5m | BACKUP |
| B7 | Negative/non-confirmatory findings (full list) | Cross-domain improves; MUSE-Books doesn't replicate; Experiment B is BASE-comparable — the headline items already appear in slide 18's text, this is the expanded backup version | text/bullets | — | `THESIS_WRITING_PLAN.md` §8 | n/a | 1.5m | BACKUP |

**How this differs from the task's own 19-item skeleton (item K)**: it is followed structurally
almost exactly — the only substantive change is demoting the prompt's implicit "negative/
non-confirmatory findings" content (previously its own main slide in an earlier draft of this
map) into the "final answers to RQs" slide's text plus a full backup slide (B7), since the
task's 19-slide list does not itself allocate a separate main slide to it and slide 18 already
carries the substance ("not supported as general claim... but real effects occur in particular
settings").

---

## 12. Thesis content vs. presentation content classification

| Item | Classification | Why |
|---|---|---|
| TOFU 10-method utility-collapse pattern (§2) | **MAIN TALK** | Explains why later methods were chosen — directly answers "why only 4/2 methods" if asked |
| TOFU per-method exact numbers beyond the collapse pattern | **THESIS ONLY** | Needed for a written methods table, not needed slide-by-slide in a talk |
| `Agg_proxy`/`Selection_proxy`/`best_agg` exact formulas | **BACKUP** (concise 1-line summary MAIN) | Reviewers may ask "how was best checkpoint chosen" — have the formula ready, don't lead with it |
| MUSE-News Track A/B pivot | **BACKUP** | Important honesty/provenance point, not central to the scientific argument |
| Failed OOM training attempts, failed SLURM jobs | **OMIT** | Zero scientific content, pure engineering noise |
| Full reproducibility per-case table (20 rows) | **BACKUP** | The 55%/70% headline numbers are MAIN; the row-by-row detail is BACKUP |
| Exact teacher-forcing implementation details (no-KV-cache donor recompute, etc.) | **BACKUP**, one-line summary MAIN | Needed if asked "how does patching work technically" |
| Benchmark-paradox 24-condition full scan | **MAIN TALK** (summarized), **THESIS ONLY** (full table) | The heterogeneity finding is central; the full 24-row table belongs in a thesis appendix |
| Recognition-vs-behavior result (Experiment A) | **MAIN TALK** | The thesis's cleanest, most defensible result |
| Experiment B's negative/non-confirmatory finding (BASE ≥ unlearned) | **MAIN TALK** | This is scientifically the most important caution in the whole mechanistic chapter — must not be cut for time |
| Generation-provenance repetition-penalty correction (1.05 vs. 1.08) | **THESIS ONLY** (footnote), **BACKUP** slide if asked | A documentation-accuracy fix, not a scientific finding, but must appear in the thesis text for correctness |
| PersistBench local-judge-vs-canonical-judge caveat | **MAIN TALK** (one-line caveat, stated once) | Affects every PersistBench number shown — must be stated, but only once, not per-slide |
| WMDP side investigation | **THESIS ONLY** (brief mention as motivation for the pivot to interpretability), **OMIT** from main results | Real work, but out of final scope; only its role as "why we pivoted" belongs anywhere in the talk |
| Repository cleanup/provenance-audit process itself | **OMIT** | Methodology-of-methodology; not defensible thesis content, purely an internal-consistency exercise |
| MUSE-Books negative replication | **MAIN TALK** | Directly supports the "not general, heterogeneous" thesis claim — omitting it would be cherry-picking |
| `configs/eval/tofu.yaml` / `src/trainer/base.py` upstream-diff mechanics | **BACKUP** | Relevant to "what did you personally build vs. use off the shelf," not to the scientific narrative |

---

## 13. Missing/existing figures audit

| Planned figure | Status | Source data | Notes |
|---|---|---|---|
| Overview pipeline diagram (whole thesis) | **MISSING — must be generated** | this map §1/§9 | Pure conceptual diagram, no plotting needed |
| TOFU method-comparison figure | **MISSING — must be generated** | raw `trainer_state.json` files (§2); no prior plot found anywhere in `research_history/01.../` or `02.../` | Data fully exists (JSON), plotting code does not |
| Method-selection figure/table | **MISSING — must be generated** (or reuse #TOFU figure with an annotation) | same as above | |
| MUSE forgetting/utility figure | **MISSING — must be generated** | `MUSE_SUMMARY.json` per checkpoint, `SELECTED_MODEL_PATHS.tsv` (`best_metric` column) | No bar chart of this shape found anywhere |
| Privacy heterogeneity figure | **EXISTS AND USABLE** | `mechanistic/outputs/benchmark_paradox/{overall_quadrant,strict_quadrant,broad_quadrant,dataset_level_summary,method_level_summary,validity_plot}.png` | 6 plots already cover this; may need relabeling/redesign for thesis polish, not regeneration |
| MUSE-News-sycophancy-specific FR@K bar chart | **MISSING — must be generated** | numbers exist in `.../paradox/report/FINAL_REPORT.md` §1 | Simple grouped bar chart, data fully in hand |
| Recognition-vs-behavior conceptual diagram (shared input → 2 divergent paths) | **MISSING — must be generated** | worked example already written up (`EXPERIMENT_A_RECOGNITION_BEHAVIOR_GAP.md`) | Pure diagram, not a data plot |
| Recognition-vs-behavior representational plots (cosine/logit) | **EXISTS, may need redesign** | `mechanistic/privacy_collapse/persistbench_sycophancy_mcq/plots/{recognition_vs_native_behavior,controlled_probe_direction_comparison,sycophancy_mcq_direction_cosine,sycophancy_mcq_safe_minus_syc_logit}.png` | These are a *different*, related representational analysis, not the "same input, two paths" conceptual diagram above — don't conflate the two |
| Activation-patching-by-layer-range figure | **EXISTS AND USABLE** | `mechanistic/experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit/plots/clean_per_example_shifts.png` | `THESIS_WRITING_PLAN.md` itself already flags this as "likely exists, check shape" — confirmed present |
| Memory-patching (Experiment B) figure | **MISSING — must be generated** | `expB_memory/expB_scores.csv` (THESIS_WRITING_PLAN.md's own Table 3 says "exists as markdown tables... needs reformatting," no plot found) | The *related but distinct* Phase-7 "memory_influence_by_layer" plots (`muse_news_sycophancy_paradox/plots/memory_influence_*.png`) exist for an **earlier, different** analysis (pre-manual-audit) — do not present these as Experiment B's own figure without relabeling |
| Final conceptual synthesis diagram | **MISSING — must be generated** | Synthesizes existing results, no new data | Pure diagram |
| Old (superseded) plots that must NOT be reused | — | `mechanistic/outputs/muse_news_sycophancy_mechanistic/{continuation_preference_by_layer,memory_influence_by_layer_*}.png` | These are from the SUPERSEDED pre-audit case selection (`continuation_cases_v1.json`) — `RESULTS_REGISTRY.csv` explicitly forbids citing this directory's patching data for any reported number |

---

## 14. Historical artifacts / claims that must not appear in final thesis or slides

- **`repetition_penalty=1.08`** — appears in `mechanistic/outputs/muse_books_weekly_update_analysis/README.md`'s provenance section and is hardcoded into `mechanistic/privacy_collapse/persistbench_native/{prepare_native_200,prepare_native_sycophancy_200}.py`. **Confirmed incorrect** for every canonical MUSE-News/MUSE-Books generation (`thesis/docs/generation_provenance.md` §3): the actual vLLM server logs from the generation jobs themselves show **1.05**. The `1.08` figure is a real, legitimate setting from the later, out-of-scope **WMDP** side-investigation (`research_history/05_wmdp_side_investigation/`), incorrectly backfilled onto the description of the earlier, unrelated MUSE generation runs by a script written two months after the fact. **Do not state 1.08 anywhere in the thesis; state 1.05 for Qwen-family runs, and UNKNOWN for the Llama-2-7b MUSE-Books track.**
- **The custom "3.85%→4.92%" privacy-context classifier percentage** (`tmp_paths/create_persistbench_validity_summary_with_muse.py`) — a plain substring-match classifier (not word-boundary-safe: e.g. `"age"` matches inside "average," "manage," "damage") whose own reconciliation document already marks it "not comparable" to the official FR@K numbers. **Do not cite this number as "the" PersistBench result** — cite the official `failure_rates.py`-derived FR@K instead.
- **Old, pre-audit case selection (`continuation_cases_v1.json`, 9 cases, judge-score-jump selected, includes cross_domain)** — `RESULTS_REGISTRY.csv` explicitly forbids using this for any reported treatment-set number; use `clean_selection.json` (10 cases, 8 unique IDs, manually audited) instead. The patching outputs computed on this old set (`mechanistic/outputs/muse_news_sycophancy_mechanistic/patching/`) must likewise not be cited.
- **MUSE-News Track A's combined table** (`saves/final_muse_news_openunlearning_selection/FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv`) — a real, complete result for a **different checkpoint family** (official Llama-2-7b target, no local finetune, no `best_agg` selection). Confirmed never shown to the supervisor and never read by anything downstream. If discussed at all (backup slide only, per §11/§12), it must be explicitly labeled "Track A, superseded, historical" — never presented as interchangeable with the canonical Track B numbers.
- **The "privacy paradox" quadrant classification for MUSE-News/Qwen SatImp and SimNPO** — the 24-condition `benchmark_paradox` scan classifies these as "**Both worsen**" (strict sign-based rule: PrivacyLens moved slightly negative, −0.41/−0.61 pp), while the dedicated case-study report (`muse_news_sycophancy_paradox/report/FINAL_REPORT.md`) describes the same PrivacyLens delta as "**~stable**" using an explicit tolerance-band framing. **Both documents are internally correct on their own terms** (they use different, both-documented thresholds), but a reader moving between the two could reasonably think they contradict. State explicitly in the thesis which framing is being used, and why (the tolerance-band framing is more appropriate for the mechanistic case study, since the ±0.5–1.0pp band is explicitly pre-registered in the paradox report itself as a robustness check, not an ad hoc adjustment).
- **Two "final report" documents describing the identical MUSE-News sycophancy behavioral starting point**: `mechanistic/outputs/muse_news_sycophancy_mechanistic/FINAL_REPORT.md` (earlier; its *case-selection and patching data* are SUPERSEDED) vs. `mechanistic/experiments/muse_news_sycophancy_paradox/report/FINAL_REPORT.md` (canonical). The behavioral percentages themselves match exactly between the two (independently re-derived) — **only the earlier document's downstream case-selection/patching artifacts are superseded, not its behavioral numbers.** Cite only the paradox-directory version going forward; do not describe the earlier one as "wrong."
- **The layer-range non-triangulation across three separate causal-patching results** (clean BASE↔unlearned patching strongest at L21-27; free-generation Experiment 1's one confident repair at L14-20 with L21-27 flagged as possible donor-copying; Experiment B's memory patching strongest at L14-20) — `THESIS_WRITING_PLAN.md` §12 explicitly instructs this be flagged in Discussion, not silently resolved. Repeated here because it is exactly the kind of inconsistency a rushed slide deck could accidentally smooth over.
- **`configs/eval/tofu.yaml` and `src/trainer/base.py`** — both are tracked upstream files modified in place (7 lines changed / 147 lines added respectively, confirmed via `git diff --stat HEAD`). Do not present these as the thesis author's own framework — they are documented, additive patches to `locuslab/open-unlearning`, not new frameworks (`thesis/README.md` §2, `thesis/docs/trainer_patch.md`).
- **`Agg_proxy`/`Selection_proxy` code in `src/trainer/base.py`** — confirmed dead weight for every MUSE-News/MUSE-Books experiment (the required TOFU-specific metric keys are never present in a MUSE eval call, so the code silently no-ops). Do not describe `best_agg` and `Agg_proxy` as "the same mechanism" — they are two independent, non-interacting metrics that happen to live in the same function.

---

## 15. Final proposed thesis structure (whole thesis, not just the mechanistic ending)

`THESIS_WRITING_PLAN.md` proposes a 9-chapter structure (Introduction → Background → RQ/Design
→ Behavioral Effects → Recognition-Behavior Gap → Mechanistic Analysis → Discussion →
Limitations → Conclusion) that is **entirely and deliberately scoped to the MUSE-News
sycophancy mechanistic ending** — it explicitly treats the TOFU/MUSE-News-Track-A/MUSE-Books
work as pre-existing context to cite, not to narrate. Given the amount of genuine, real,
completed research in Phases 1–4 (§1–§4 above), this map recommends **expanding, not
replacing**, that structure — the mechanistic chapters (4–9 below) are `THESIS_WRITING_PLAN.md`
verbatim; chapters 1–3 are new, sitting in front of it.

| Ch. | Title | Question | Experiment | Result | Canonical code/output | Presentation counterpart |
|---|---|---|---|---|---|---|
| 1 | Introduction | Motivate the whole arc: unlearning method proliferation → need to pick methods → need a realistic benchmark → does it have side effects? | — | — | — | Slides 1–3 |
| 2 | Background | Unlearning methods (10, then 4, then 2), TOFU, MUSE, PrivacyLens/PersistBench, activation patching (lit review) | — | — | — | Slide 4 |
| 3 | **NEW — Method development: from TOFU to a final method/dataset/checkpoint-selection design** | Which methods forget adequately without destroying utility, at what scale, and how should "best checkpoint" be defined? | Phases 1–3 (§1–§3 this map) | 10→4 methods (utility-collapse pattern), `Agg_proxy`→`best_agg` metric development | `research_history/01–03/`, `src/trainer/base.py`, `thesis/docs/trainer_patch.md` | Slides 5–6 |
| 4 | **NEW — MUSE-News/MUSE-Books: forgetting and utility results** | Do the selected methods produce complete, usable forgetting/utility results on realistic data? | Phase 4/4′/6 (§4 this map) | Track A→B pivot (MUSE-News), both tracks canonical (MUSE-Books) | `thesis/README.md` §6–7, `SELECTED_MODEL_PATHS.tsv` | Slides 7–8 |
| 5 | Behavioral Effects of Machine Unlearning on Contextual Privacy | RQ1 (`THESIS_WRITING_PLAN.md` unchanged) | Benchmark-paradox scan, PrivacyLens stability, PersistBench sycophancy/cross-domain | Heterogeneous, not uniform | §6/§7 this map, `benchmark_paradox/FINAL_REPORT.md` | Slides 9–11 |
| 6 | Recognition–Behavior Gap | RQ2 | Manual audit, Experiment A | 10/10 recognition intact | §8 item 2/6 this map | Slides 12–13 |
| 7 | Mechanistic Analysis | RQ3/RQ4 | Clean patching, Exp. 1, repro check, Exp. B | H1/H3 partial support | §8 items 3–7 this map | Slides 14–16 |
| 8 | Discussion | Synthesize, resolve/flag the layer-range tension | — | H1 partial / H2 supported / H3 partial | `FOCUSED_THESIS_SYNTHESIS.md` | Slide 17 |
| 9 | Limitations | Per-claim limitation table (`THESIS_WRITING_PLAN.md` §9, unchanged) plus: undocumented method-selection rationale (Ch. 3), local-judge-not-canonical caveat (Ch. 4/5), MUSE-Books non-replication (Ch. 5) | — | — | — | Folded into slide 18 |
| 10 | Conclusion | Contributions (add: "documented the full method/dataset selection pipeline, not only the final mechanistic case study") | — | — | — | Slide 19 |

**Does the earlier TOFU/MUSE work require changes to `THESIS_WRITING_PLAN.md`'s existing
chapters?** No — Chapters 4–9 above are that plan's Chapters 3–9 essentially unchanged (only
renumbered to make room for the new Chapters 3–4). The plan's own Ch. 3 ("Research Questions
and Experimental Design") already correctly treats case-selection as methodology, and nothing
in the newly-surfaced TOFU/MUSE evidence contradicts anything already written there — it only
adds two chapters of *earlier* context that the mechanistic-only plan had assumed would be
handled elsewhere (e.g., in a methods appendix) rather than as full chapters.

---

## USER CONFIRMATION REQUIRED

- [x] **Stage 0 (new) — Research-question evolution**: [EXPOSE-DOCUMENTED/MIDTERM-DOCUMENTED,
  §0.1] Exposé RQ1–3 → Midterm RQ1–3 (RQ3 explicitly future work) → Final RQ1–3. **Resolved by
  the user this pass** — the privacy hypothesis was not retrospective. Residual open item:
  the exact PDF/PPTX wording could not be independently verified by this session (files not
  accessible) — if a direct quote is needed for the thesis's own citation of its Exposé, pull
  it from the original document yourself, since this map necessarily paraphrases the user's
  report of it.
- [x] **Stage 1 — TOFU broad method evaluation**: 10 methods, Llama-3.2-1B/Qwen2.5-1.5B/3B, f10
  split; CEU/GradAscent/GradDiff collapse utility; RMU/WGA/SatImp/SimNPO retained. **Resolved
  by the user this pass** [USER-CONFIRMED, §3D]: narrowing was based on the forgetting/utility
  aggregate/trade-off; there is no formal globally-ranked "top 4" table, and this map does not
  claim one — the exact historical ranking *rule* (as opposed to the qualitative trade-off
  criterion) remains unreconstructable from any file, which is stated as a fact, not left open
  as a question needing your input.
- [ ] **Stage 2 — Method-selection metric development**: `Agg`(Mem,Priv,Util) [MIDTERM-DOCUMENTED]
  → `Agg_proxy`/`Selection_proxy` → `best_agg` (MUSE), harmonic-mean checkpoint selection, with
  `Priv` = the OpenUnlearning MIA/leakage proxy, not PrivacyLens/PersistBench contextual
  privacy (§3C). Confirmed load-bearing, mechanically proven for `best_agg`/`Agg_proxy`/
  `Selection_proxy` via `trainer_state.json`. No confirmation needed on the mechanics; the
  midterm-documented `Agg` formula naming is taken from your report and not independently
  verified against the `.pptx` by this session.
- [x] **Stage 3 — MUSE-News Track A → Track B pivot**: a complete Track-A result was produced
  and then abandoned in favor of a locally-finetuned Qwen2.5-7B-Instruct target. **Resolved by
  the user this pass**: the reason is confirmed **not remembered** — this map no longer
  presents an inferred motivation as fact (§1 Phase 4, §4A, §H of the task). Classification:
  THESIS PROVENANCE / BACKUP only.
- [ ] **Stage 4 — MUSE-News/MUSE-Books behavioral evaluation**: standard MUSE metrics +
  PrivacyLens + PersistBench (local-Qwen judge, not canonical Kimi-K2) for BASE/RMU/WGA/
  SatImp/SimNPO, both datasets. No confirmation needed for the mechanics; confirmation still
  needed on whether the **judge caveat** has been communicated to your supervisor/committee
  previously, since it affects every PersistBench number in the thesis.
- [x] **Stage 5 — Privacy-evaluation heterogeneity discovery**: 24-condition benchmark-paradox
  scan; 7/16 clean conditions show a "privacy paradox," most consistently for RMU. **Resolved
  by the user this pass** [EXPOSE-DOCUMENTED, §0.1]: "better forgetting may harm contextual
  privacy" was the thesis's original working hypothesis from the Exposé, not a retrospective
  framing applied after this scan was run — the scan is evidence *for* a pre-existing
  hypothesis, not the hypothesis's origin.
- [x] **Stage 6 — Mechanistic case selection**: MUSE-News × PersistBench-sycophancy ×
  SatImp/SimNPO chosen as the one clean, both-methods, every-K degradation on a 100%-valid
  population. **Resolved by the user this pass** [USER-CONFIRMED, §3E/§7]: chosen because
  these two methods showed the clearest direct PrivacyLens-stable/PersistBench-worse pattern —
  this supersedes an earlier draft's speculative "matched utility/forgetting profile" and
  "architectural difference" framing, which is now presented only as a secondary observation.
- [ ] **Stage 7 — Recognition/mechanistic analysis (frozen)**: manual audit (27→10), clean
  teacher-forced patching, free-generation Exp. 1, reproducibility diagnostic, Experiment A
  (10/10 recognition intact), Experiment B (memory-context causal but not unlearning-specific).
  This entire stage is treated as frozen and reused verbatim, per your instruction — no
  confirmation needed on the numbers themselves. **New this pass**: the authoritative final
  hypothesis wording (H1 NOT SUPPORTED AS GENERAL CLAIM / H2 SUPPORTED / H3 NOT ESTABLISHED,
  §8 "Final hypothesis wording") is this map's resolution of a phrasing conflict between two
  already-frozen documents, not a new finding — confirm this phrasing is what you want to carry
  into the thesis text and slides, since the frozen documents' own "partially supported"
  wording for H1/H3 is preserved only as historical citation, not as the primary phrasing.
- [ ] **Stage 8 — MUSE-Books mechanistic replication**: genuine negative replication (the
  MUSE-News story does not hold on MUSE-Books). No confirmation needed — directly quoted from
  the frozen report.
- [ ] **Stage 9 — Final thesis structure**: this map proposes prepending 2 new chapters (method
  development, MUSE forgetting/utility) to `THESIS_WRITING_PLAN.md`'s existing 9-chapter
  mechanistic-ending structure, renumbering the rest. **NEEDS USER CONFIRMATION**: does this
  match your intended thesis scope, or do you want the earlier TOFU/MUSE work handled more
  briefly (e.g., as a single "Methods" chapter rather than two full result chapters)?
- [ ] **Slide count / structure**: this map proposes 19 main slides + 7 backup, revised this
  pass to the task's own 19-item skeleton (§11/§K). **NEEDS USER CONFIRMATION**: does this
  match your available defense time, or should some MAIN slides (§12) be demoted to BACKUP?

Additional standalone items already explicitly flagged **NEEDS USER CONFIRMATION** inline
above (not repeated here): the meaning of the `a180` batch label (§2); whether Exposé/Midterm
wording quoted or paraphrased in §0.1/§4.5 exactly matches the source PDF/PPTX, which this
session could not open directly (source-access note, top of document); whether the planned
CIMemories benchmark was dropped for a documented reason not captured anywhere (§5 "Benchmark
evolution"); whether the "judge caveat has been communicated to your supervisor" question in
Stage 4 above has in fact already been addressed elsewhere.

---

*This document was originally generated by inspecting the repository's own files (scripts,
configs, `trainer_state.json` snapshots, frozen reports, manifests) on 2026-09-24, then revised
the same day to integrate the Exposé, the July midterm, and the user's own confirmed
recollection (see changelog below). Nothing was moved, renamed, rerun, restructured, or
altered to produce either pass. If any statement above conflicts with your own memory of the
project, the resolution should come from you (via the checklist above), not from re-trusting
this document, the original prompt's summary, or the Exposé/midterm paraphrase over one
another without checking the underlying source.*

---

## Changelog (this revision)

- Added a source-access note: the Exposé PDF and midterm PPTX were not found or opened by this
  session; their content is incorporated as the user's reported historical context, tagged
  EXPOSE-DOCUMENTED/MIDTERM-DOCUMENTED accordingly rather than as independently verified primary
  sources.
- Added §0.1 "Research question evolution" (Exposé RQ1–3 → Midterm RQ1–3, with RQ3 flagged as
  future work at the midterm → Final RQ1–3), correcting §0's earlier over-statement that the
  privacy hypothesis was purely retrospective.
- Added §4.5 "Midterm state of the thesis" (the 10-point 2026-07-29 checkpoint, including the
  midterm's own explicitly-open question that the final mechanistic chapters answer).
- Added §9.5 "Final defense story" (concise 14-step narrative arc, cross-referenced to §0.1/§9).
- §3: corrected the TOFU aggregation-metric description — clarified `Agg = HM(Mem, Priv, Util)`
  (midterm terminology), that `Priv` is the OpenUnlearning MIA/leakage proxy and **not**
  PrivacyLens/PersistBench contextual privacy, and that the formula evolved
  (`Agg_proxy` → `Selection_proxy` → MUSE's `best_agg`) rather than staying fixed.
- §3: reworded the "best four" method-narrowing bullet to state plainly there is no formal
  globally-ranked table, only a forgetting/utility trade-off criterion (user-confirmed).
- §3/§7: replaced the earlier speculative "SatImp/SimNPO as a matched pair, RMU/WGA excluded
  for architectural reasons" rationale with the user-confirmed reason (clearest
  PrivacyLens-stable/PersistBench-worse pattern); architecture/collapse notes downgraded to
  secondary observations only.
- §1/§4A: removed the earlier draft's inferred rationale for the MUSE-News Track A→Track B
  switch ("methodological consistency," "built for the mechanistic phase's model family");
  replaced with an explicit "reason not remembered, not established" statement and a
  THESIS-PROVENANCE/BACKUP-only classification.
- §5: added the "Benchmark evolution" note (Exposé's planned PrivacyLens+CIMemories → final
  PrivacyLens+PersistBench) and corrected the "Logical purpose/hypothesis" paragraph to remove
  the claim that no prior design document contained the privacy hypothesis.
- §8/new "Final hypothesis wording" subsection: added the authoritative final H1/H2/H3 wording
  (H1 NOT SUPPORTED AS A GENERAL CLAIM, H2 SUPPORTED, H3 NOT ESTABLISHED), explicitly preserving
  the frozen `FOCUSED_THESIS_SYNTHESIS.md`'s "partially supported" wording as historical, not
  authoritative, phrasing.
- §11: rewrote the proposed slide sequence to the task's 19-slide skeleton (combined MUSE
  setup+results slide, PrivacyLens-vs-PersistBench slide, activation-patching concept/result
  split, explicit "final answers to RQs" slide); added backup slide B7 for the full
  negative-findings list.
- USER CONFIRMATION REQUIRED checklist: marked Stages 0, 1, 3, 5, 6 resolved this pass (with
  brief resolution notes); left Stages 2, 4, 7 (partially), 8, 9 and the slide-count question
  open, since those remain genuinely unconfirmed.
- No files were moved, no experiments were run, no scientific outputs were modified, and the
  repository was not restructured, per this task's explicit constraints.
