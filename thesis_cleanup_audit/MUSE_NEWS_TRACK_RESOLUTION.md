# MUSE-News track resolution

Read-only provenance investigation. No files were moved, renamed, deleted, refactored, or modified; no model inference or GPU jobs were run; no git history was changed. All evidence below is either a direct file/metadata read or a `git`/`find`/`grep`/`stat` command against the existing repository. Every claim below is backed by an exact path quoted inline; nothing is asserted from memory of the prior audit alone.

## Bottom line (read this first)

**Track B — the locally-finetuned Qwen2.5-7B-Instruct target — is unambiguously the track in current, active use.** The exact checkpoint paths you gave are confirmed correct, not merely plausible:

- BASE: `saves/finetune/muse_news_qwen25_7b_instruct_target`
- SatImp: `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459`
- SimNPO: `saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459`

These exact three strings are embedded as machine-recorded metadata inside every generation file, every GPU-extraction provenance record, and every PrivacyLens output file produced by the mechanistic interpretability pipeline (evidence in §1 and §3). Track A (the official-HF-target Llama-2-7b track) produced one early combined table on 2026-07-04 and is not read by anything downstream of that date — it is a self-contained, dead-end artifact, not a competing "current" source of truth. No mixed-provenance contamination was found: every place Track A is mentioned in the mechanistic/thesis-analysis code, it is explicitly labeled as a different, non-comparable, earlier result — the thesis author had already done this reconciliation once, on 2026-08-28, in `mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_persistbench_metric_reconciliation.md` (§4).

The one real issue found is not a track-mixing problem: **no MUSE-News PersistBench result (either track) was ever judged by the canonical PersistBench judge** (`moonshotai/kimi-k2-thinking`); all of them used a legacy local `Qwen/Qwen2.5-7B-Instruct` judge. This must be labeled correctly in the thesis text (see §5, point 5).

---

## 1. Provenance trace of current MUSE-News results (Track B)

| Result | Generating script | Input generation file | Judgment file | Model/checkpoint | Output file | Track |
|---|---|---|---|---|---|---|
| PrivacyLens (behavioral, 493-case) | `run_privacylens_muse_news_qwen25_selected.sh` → `scripts/eval_privacylens_mcq_local.py` | `external/privacy-collapse/benchmarks/privacylens/data/main_data.json` | n/a (direct MCQ scoring) | `model_path` field in output = `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459` (SatImp; verified by reading the file, see below) | `outputs/privacylens_muse_news_qwen25_selected/muse_news_qwen25_{before,rmu,wga,satimp,simnpo}/privacy_mcq_all493.json` | **B** |
| PersistBench generation (cross-domain + sycophancy + beneficial-memory, 500 rows) | `run_persistbench_muse_news_qwen25_selected.sh` | frozen PersistBench benchmark rows | — | (checkpoints as above, via `tmp_paths/muse_news_qwen25_persistbench_models.tsv`) | `external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_{before,rmu,wga,satimp,simnpo}.json` | **B** |
| PersistBench judgment | `run_persistbench_muse_news_qwen25_judge_like_tofu.sh` → routed to `run_local_judge_server_penelope.sh` (`Qwen/Qwen2.5-7B-Instruct` served as `local-judge`) | the 5 generation files above | same files (judgment written in place, `metadata.judge_model="local-judge"`) | n/a (judge, not evaluated model) | same files | **B** |
| Generation validation | `tmp_paths/create_persistbench_validity_summary_with_muse.py` | the 5 generation/judgment files above | — | — | `external/PersistBench/outputs/PERSISTBENCH_ALL_DATASETS_VALIDITY_SUMMARY_WITH_MUSE.tsv` | **B** (News rows) |
| Native prompt-end hidden-state extraction (cross-domain) | `mechanistic/privacy_collapse/persistbench_native/{prepare_native_200.py, extract_prompt_end_hidden_states.py}` | `external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_{before,satimp,simnpo}.json` (confirmed via embedded `source_output` field, see §3) | — | embedded `checkpoint` field per generation record (verified, §3) | `mechanistic/privacy_collapse/persistbench_native/generations/{base,satimp,simnpo}_generation0.jsonl`, `representations/{base,satimp,simnpo}_prompt_end.pt`, `representations/extraction_metadata.json` | **B** |
| Sycophancy transition analysis | `mechanistic/privacy_collapse/persistbench_native/{prepare_native_sycophancy_200.py, analyze_sycophancy.py}` | `muse_news_qwen25_selected_full/muse_news_qwen25_{before,satimp,simnpo}.json` | — | same as above | `generations/sycophancy_{base,satimp,simnpo}_generation0.jsonl`, `representations/sycophancy/*_prompt_end.pt`, `analysis/sycophancy/*.{json,csv,png}` | **B** |
| Controlled MCQ probes (privacy-judgment) | `mechanistic/privacy_collapse/persistbench_mcq/{build_manifest,extract,analyze}.py` | frozen 50-case manifest | — | `mechanistic/outputs/privacy_collapse_persistbench_mcq_muse_news_qwen25_7b/gpu_extraction_provenance.json` records exact absolute paths (see §3) | `mechanistic/outputs/privacy_collapse_persistbench_mcq_muse_news_qwen25_7b/*` | **B** |
| A/B label-swap robustness | `mechanistic/privacy_collapse/persistbench_sycophancy_mcq/{build_manifest,extract,analyze,finalize,plot_recognition}.py` | frozen 50-case clear-no manifest | — | `mechanistic/privacy_collapse/persistbench_sycophancy_mcq/analysis/gpu_extraction_provenance.json` records exact absolute paths (see §3) | `mechanistic/privacy_collapse/persistbench_sycophancy_mcq/{representations,analysis,plots}/*` | **B** |
| News-vs-Books comparison | `mechanistic/outputs/muse_books_weekly_update_analysis/{DISCOVERY_REPORT.md, README.md}` | Books: `external/PersistBench/outputs/muse_books_qwen25_selected_full/*.json`; News: `muse_news_qwen25_selected_full/*.json` | both legacy-local-Qwen judged | Books BASE/SatImp/SimNPO = `saves/finetune/muse_books_qwen25_7b_instruct_target`, `.../muse_books_qwen25_7b_instruct_{satimp,simnpo}/checkpoint-51`; News = Track B paths above | `mechanistic/outputs/muse_books_weekly_update_analysis/README.md` (the comparison document itself) | **B** for News side; Books side is its own single track (no ambiguity there) |
| "Weekly update" plots/tables | No single `muse_news_weekly_update_analysis/` directory exists (the Books doc explicitly frames itself as replicating "the latest MUSE-News weekly-update analyses" — see `mechanistic/outputs/muse_books_weekly_update_analysis/DISCOVERY_REPORT.md` line 1). The News-side equivalent is the collection of dated outputs under `mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/`, `privacy_collapse_persistbench_mcq_muse_news_qwen25_7b/`, and `privacy_collapse/persistbench_native/analysis/` (all dated 2026-08-23 to 2026-08-28) | — | — | — | (as above) | **B** |
| Metric reconciliation / FINAL_*-equivalent for the mechanistic study | `mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_persistbench_metric_reconciliation.{json,md}` | reads the Track B generation/judgment files above **and explicitly the Track A files, labeled as non-comparable** (see §4) | — | Track B checkpoints (table reproduced verbatim in §4) | the reconciliation file itself | **B is primary; A is cited only as clearly-labeled historical context** |
| Only existing combined `FINAL_*.csv` | `make_final_muse_news_combined_table.py` | `outputs/privacylens_muse_news_selected/*/privacy_mcq_all493.json` + `saves/final_muse_news_openunlearning_selection/*` | — | Track A checkpoints (`muse_news_{method}_ckpts_bs1_gc_sbatch`, official `muse-bench/MUSE-News_target`) | `saves/final_muse_news_openunlearning_selection/FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv` (dated 2026-07-04) | **A — and A only; this file has no Track-B counterpart and is not read by anything else in the repo (verified, §2)** |

---

## 2. Track comparison table

| Result / Experiment | Official-target (Track A) output | Locally-finetuned-target (Track B) output | Which is used currently? | Evidence |
|---|---|---|---|---|
| Checkpoint selection manifest | `saves/final_muse_news_openunlearning_selection/SELECTED_MODEL_PATHS.tsv` (2026-07-01) | `saves/final_muse_news_qwen25_7b_instruct_selection/SELECTED_MODEL_PATHS.tsv` (2026-07-08) | **B** | Both files read directly; B's rows exactly match the paths you gave: `SATIMP saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459`, `SIMNPO ... checkpoint-459`, `before saves/finetune/muse_news_qwen25_7b_instruct_target` |
| PrivacyLens 493-case eval | `outputs/privacylens_muse_news_selected/` | `outputs/privacylens_muse_news_qwen25_selected/` | **B** (only B is read by the mechanistic reconciliation; A is read only by the one 2026-07-04 combiner) | `grep -rl "privacylens_muse_news_qwen25_selected"` → only `run_privacylens_muse_news_qwen25_selected.sh` and `mechanistic/analyze_benchmark_paradox.py`; `grep -rl "FINAL_MUSE_News_MUSE_plus_PrivacyLens\|final_muse_news_openunlearning_selection"` → only the 3 Track-A-generating scripts themselves and this audit's own docs |
| PersistBench cross-domain/sycophancy/beneficial-memory generations | `external/PersistBench/outputs/muse_news_selected_full/*.json` (2026-07-05) | `external/PersistBench/outputs/muse_news_qwen25_selected_full/*.json` (2026-07-08) | **B** | Every `mechanistic/privacy_collapse/persistbench_native/generations/*.jsonl` record's `source_output` field points at `muse_news_qwen25_selected_full/...json`, never at `muse_news_selected_full/...json` (verified by reading the raw JSONL, §3) |
| Combined MUSE+PrivacyLens final table | ✅ exists: `FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv` | ❌ does not exist — `saves/final_muse_news_qwen25_7b_instruct_selection/` contains only `SELECTED_MODEL_PATHS.tsv`, no combined csv, confirmed by directory listing | Neither track has a "current" combined csv that the mechanistic work reads; Track A's csv is an orphaned early artifact | `ls -la saves/final_muse_news_qwen25_7b_instruct_selection/` shows exactly one file |
| Mechanistic hidden-state / MCQ / A-B-swap analysis | none — Track A was never carried into the mechanistic pipeline | ✅ all of it (§1) | **B exclusively** | Every `gpu_extraction_provenance.json` under `mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/`, `.../privacy_collapse_persistbench_mcq_muse_news_qwen25_7b/`, and `persistbench_sycophancy_mcq/analysis/` records Track B's exact absolute paths (§3) |
| Supervisor-bundle results (`supervisor_update/code_settings/results/`) | not present | not present | **neither** — this bundle contains zero MUSE-News files at all | `ls supervisor_update/code_settings/results/ \| grep -i muse_news` → empty. The 40 files in that bundle are all TOFU-model PrivacyLens snapshots, unrelated to MUSE-News |
| Completeness | Complete for the 4 unlearning methods it covers (RMU/WGA/SimNPO/SatImp) + one combined table, but **stops there** — no PersistBench-native/MCQ/probe work was ever built on it | Complete through PrivacyLens + PersistBench (5 methods incl. RMU/WGA) + the full mechanistic interpretability suite (native hidden states, sycophancy transitions, controlled MCQ, A/B swap) | Track B is the only track with a complete, continuously-extended result chain | Directory listings in §1/§3 |

**Was Track A ever shown to the supervisor?** No evidence found. `grep`-ing `supervisor_update/`, `meeting_updates/`, and `meeting_updates_wmdp_safety_summary.csv` for `ckpts_bs1_gc_sbatch`, `muse-bench/MUSE-News_target`, and `openunlearning_selection` returns **zero hits**. Track A appears to be purely a private/exploratory intermediate result that was never bundled for supervisor reporting.

**Do any final plots/tables mix data from the two tracks?** No. The only document that discusses both tracks together, `muse_news_persistbench_metric_reconciliation.md`, does so by explicitly labeling Track A's numbers as "a different model/checkpoint family... not comparable" (verbatim, §4) — it is a deliberate side-by-side citation for methodological transparency, not an accidental average or merge of the two.

---

## 3. Checkpoint verification (not assumed — proven from embedded metadata)

All three of your stated paths were independently confirmed to exist on disk and to be the exact paths recorded by the pipeline's own machine-generated provenance files (not just referenced by a script that could itself be stale):

```
$ ls -ld saves/finetune/muse_news_qwen25_7b_instruct_target
drwx------ 15 ... Jul  6 06:25 saves/finetune/muse_news_qwen25_7b_instruct_target

$ ls -ld saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459
drwx------  3 ... Jul  7 13:29 saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459

$ ls -ld saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459
drwx------  3 ... Jul  7 09:01 saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459
```

Both `checkpoint-459` and `checkpoint-500` exist side-by-side under both `.../satimp/` and `.../simnpo/` (i.e. there were two candidate steps), so this is not a case of "only one checkpoint exists." The frozen selection manifest resolves the ambiguity:

```
$ cat saves/final_muse_news_qwen25_7b_instruct_selection/SELECTED_MODEL_PATHS.tsv
method  model_path                                                          best_metric
before  saves/finetune/muse_news_qwen25_7b_instruct_target
RMU     saves/unlearn/muse_news_qwen25_7b_instruct_rmu/checkpoint-459        0.228...
WGA     saves/unlearn/muse_news_qwen25_7b_instruct_wga/checkpoint-306        0.202...
SIMNPO  saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459     0.196...
SATIMP  saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459    0.192...
```

This matches your stated paths exactly (checkpoint-459 for both SatImp and SimNPO, `checkpoint-306` for WGA — note WGA is *not* 459, so "459 for everything" is not a blanket rule, it's method-specific selection).

Independently, the actual generation files produced by the mechanistic pipeline embed the checkpoint they used as a literal JSON field per record — this is stronger evidence than a script argument, because it is what the extraction process itself recorded at run time, not what a launcher script merely intended:

```
$ python3 -c "import json; d=json.loads(open('mechanistic/privacy_collapse/persistbench_native/generations/satimp_generation0.jsonl').readline()); print(d['checkpoint'], d['source_output'])"
saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459  external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_satimp.json

$ ... simnpo_generation0.jsonl ...
saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459  external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_simnpo.json

$ ... base_generation0.jsonl ...
checkpoint: saves/finetune/muse_news_qwen25_7b_instruct_target
```

And every GPU-extraction run recorded its own absolute-path provenance:

```
$ cat mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/gpu_extraction_provenance.json   (started 2026-08-24T10:39)
"BASE":   "/mnt/beegfs/work/elshashay/open-unlearning/saves/finetune/muse_news_qwen25_7b_instruct_target"
"SatImp": "/mnt/beegfs/work/elshashay/open-unlearning/saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459"
"SimNPO": "/mnt/beegfs/work/elshashay/open-unlearning/saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459"

$ cat mechanistic/outputs/privacy_collapse_persistbench_mcq_muse_news_qwen25_7b/gpu_extraction_provenance.json   (started 2026-08-27T14:03)
same three paths, config.models.{BASE,SatImp,SimNPO}

$ cat mechanistic/privacy_collapse/persistbench_sycophancy_mcq/analysis/gpu_extraction_provenance.json   (started 2026-08-28T09:47)
same three paths
```

And the PrivacyLens output JSON itself carries the checkpoint as a result field, not just as a directory name:

```
$ python3 -c "import json; print(json.load(open('outputs/privacylens_muse_news_qwen25_selected/muse_news_qwen25_satimp/privacy_mcq_all493.json'))['meta'])"
{
  "model_label": "muse_news_qwen25_satimp",
  "model_path": "saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459",
  "tokenizer_path": "saves/finetune/muse_news_qwen25_7b_instruct_target",
  ...
}
```

**Verdict: your stated paths are correct, and they are corroborated by four independent, machine-generated provenance trails (selection manifest, generation-file metadata, GPU-extraction provenance json ×3, PrivacyLens output metadata), not merely by a script argument that could have drifted.**

---

## 4. Checking for mixed provenance

Explicitly searched for every failure mode you listed:

- **Generations from one track, judgments from another**: not found. PersistBench judgment is written back into the same JSON file as the generation (`metadata.judge_model` field in place), so there is no separate judgment file that could point elsewhere; verified the judge-serving chain (`run_local_judge_server_penelope.sh` → `Qwen/Qwen2.5-7B-Instruct` as `local-judge`, confirmed in `logs/local_judge_408628.out` per the reconciliation doc) is the same for both tracks' judging, so no cross-track judge substitution occurred either.
- **Plots combining both tracks**: not found. No plot file's generating script reads both a `*_ckpts_bs1_gc_sbatch` (Track A) and a `*_qwen25_7b_instruct_*` (Track B) path in the same figure.
- **BASE from one track, SatImp/SimNPO from another**: not found. Every provenance record in §3 lists all three (or five, including RMU/WGA) models from the *same* track together — there is no record anywhere mixing a Track-A BASE with a Track-B method or vice versa.
- **An old result file reused accidentally**: the closest thing to this is `saves/final_muse_news_simnpo_openunlearning_selection/` (2026-07-01, Track A, SimNPO-only, superseded the same day by the fuller 4-method `openunlearning_selection` selection) — but this is a Track-A-internal superseded iteration, not a cross-track mixup, and nothing downstream reads it (confirmed no `grep` hits outside its own directory).
- **Supervisor update citing one track while mechanistic analysis uses another**: cannot be confirmed as a problem because the supervisor bundle (`supervisor_update/code_settings/results/`) contains **no MUSE-News files whatsoever** — so there is nothing in the supervisor bundle to be inconsistent with the mechanistic analysis on this topic. If MUSE-News results were shown to the supervisor by some other means (a slide deck, a live plot, an email) outside this repository, this audit cannot see that — only what is written to disk here.

**The one document that discusses both tracks side-by-side**, `mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_persistbench_metric_reconciliation.md` (dated 2026-08-28), does so *deliberately and clearly*, quoting verbatim:

> "This is a different model/checkpoint family: BASE `muse-bench/MUSE-News_target`, SatImp `saves/unlearn/muse_news_satimp_ckpts_bs1_gc_sbatch/checkpoint-500`, and SimNPO `saves/unlearn/muse_news_simnpo_ckpts_bs1_gc_sbatch/checkpoint-459`. It used the full 500 rows/1,300 responses and the same legacy local Qwen judge. The custom all-category score≥4 privacy-context classifier reported 4.00% → 5.92% / 4.92%. It supports a qualified "MUSE-News became worse" statement for Llama2, but it is **not comparable** to the current Qwen2.5 cross-domain FR@1 result."

This is the thesis author already having done exactly this reconciliation, and getting it right: Track A is cited as historical context, explicitly flagged as a different checkpoint family, and explicitly marked not comparable. **This is the opposite of mixed provenance — it is provenance hygiene already performed.** No correction is needed to this document.

The one genuinely important methodological flag this same document raises, independent of the two-track question: **no MUSE-News PersistBench result under either track was ever judged by the canonical `moonshotai/kimi-k2-thinking` judge** — both tracks used a "legacy local `Qwen/Qwen2.5-7B-Instruct`" judge server. The document itself says: *"Every MUSE-News PersistBench artifact located here uses the legacy local Qwen/Qwen2.5-7B-Instruct judge and must not be described as canonical PersistBench."* This is a labeling requirement for the thesis text, not a provenance-mixing bug, but it belongs in your results/methodology section regardless of which track is canonical.

---

## 5. Final decision

1. **Which MUSE-News track should be treated as canonical for the final thesis?**
   **Track B — the locally-finetuned Qwen2.5-7B-Instruct target track.** It is the track exclusively used by every mechanistic-interpretability result (native hidden-state extraction, sycophancy transition analysis, controlled MCQ probes, A/B label-swap robustness), the track cited in the News-vs-Books comparison, and the track the thesis author's own reconciliation document treats as current. Track A (official Llama-2-7b target) is an early, self-contained, dead-end artifact from 2026-07-01–04 with no downstream consumers.

2. **Exact checkpoint paths belonging to the canonical track** (confirmed on disk and in provenance metadata, §3):
   - BASE: `saves/finetune/muse_news_qwen25_7b_instruct_target`
   - SatImp: `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459`
   - SimNPO: `saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459`
   - (for completeness, also selected but outside your BASE/SatImp/SimNPO question) RMU: `saves/unlearn/muse_news_qwen25_7b_instruct_rmu/checkpoint-459`; WGA: `saves/unlearn/muse_news_qwen25_7b_instruct_wga/checkpoint-306`

3. **Final outputs belonging to the canonical track:**
   - `saves/final_muse_news_qwen25_7b_instruct_selection/SELECTED_MODEL_PATHS.tsv`
   - `outputs/privacylens_muse_news_qwen25_selected/muse_news_qwen25_{before,rmu,wga,satimp,simnpo}/privacy_mcq_all493.json` + `privacylens_muse_news_qwen25_summary.csv`
   - `external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_{before,rmu,wga,satimp,simnpo}.json` + `persistbench_muse_news_qwen25_summary.csv`
   - `mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/*` (native PrivacyLens-style representation/logit-lens study)
   - `mechanistic/privacy_collapse/persistbench_native/{generations,representations,manifests,analysis}/*` (cross-domain + sycophancy native hidden states, sycophancy transitions, category comparison, metric reconciliation)
   - `mechanistic/outputs/privacy_collapse_persistbench_mcq_muse_news_qwen25_7b/*` (controlled MCQ privacy-judgment probe)
   - `mechanistic/privacy_collapse/persistbench_sycophancy_mcq/{representations,analysis,plots}/*` (A/B label-swap robustness)
   - `mechanistic/outputs/muse_books_weekly_update_analysis/README.md` (the News-vs-Books comparison, News side)

4. **Can the alternative track (A) safely be marked historical/archive?**
   **Yes.** Nothing in the current mechanistic/thesis-analysis pipeline reads any Track-A path, and Track A was never shown in the supervisor bundle. Track A's artifacts — `saves/final_muse_news_openunlearning_selection/` (incl. `FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv`), `saves/final_muse_news_simnpo_openunlearning_selection/`, `saves/unlearn/muse_news_{rmu,wga,simnpo,satimp}_ckpts_bs1_gc_sbatch/`, `outputs/privacylens_muse_news_selected/`, `external/PersistBench/outputs/muse_news_selected_full/`, and the generating scripts `run_muse_news_remaining_methods.sbatch`, `run_muse_news_simnpo.sbatch`, `run_privacylens_muse_news_selected.sh`, `run_persistbench_muse_news_judge_like_tofu.sh`/`run_persistbench_muse_news_selected.sh`, `make_final_muse_news_combined_table.py`, `make_muse_news_selected_table.py`, `select_muse_news_best_checkpoints.py` — can all be reclassified from "final chain" to "historical/archive." **This changes the recommendation in `MIGRATION_PLAN.md`, which had provisionally kept both tracks side by side pending this decision; that file should be updated to move these specific paths into the `archive/` tree in a follow-up pass** (not done here, per your instruction to only write this one file).

5. **Does any current thesis result need correction because of mixed provenance?**
   **No result needs correction due to track-mixing** — none was found. **One labeling correction is needed regardless of track**: every MUSE-News PersistBench number in the thesis (cross-domain FR@K, sycophancy FR@K, beneficial-memory failure rate) was produced by a legacy local `Qwen/Qwen2.5-7B-Instruct` judge, not the canonical PersistBench `moonshotai/kimi-k2-thinking` judge. Any thesis text presenting these as "PersistBench results" should explicitly caveat the judge used, per the author's own reconciliation document. Separately, if any thesis draft or earlier supervisor note ever cited the "3.85% → 4.92%" custom privacy-context classifier figure, note that this is a *different metric* than the current official cross-domain FR@1 numbers (3.5% → 2.0%/1.5%) even though it uses the *same* Track-B checkpoints — the two are not directly comparable and should not be conflated in the write-up (this is a metric-definition issue, not a track issue; both use Track B).

6. **Is there anything that prevents proceeding with the repository cleanup?**
   **No.** The ambiguity that blocked the migration plan is now resolved with direct evidence, not inference. The only follow-up action implied (not performed in this read-only investigation) is updating `MIGRATION_PLAN.md`'s MUSE-News rows to move Track A's scripts/outputs into `archive/` rather than keeping both tracks in the proposed `thesis/scripts/muse_news/` structure — a small, mechanical edit once you approve this resolution. Cleanup can proceed without rerunning any experiment: every artifact needed to support Track B as canonical already exists on disk and is fully provenanced.
