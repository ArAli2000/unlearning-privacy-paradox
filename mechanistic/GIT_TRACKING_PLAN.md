# Git Tracking Plan for `mechanistic/`

**Status: PROPOSAL ONLY.** Nothing has been staged, committed, or deleted, and
`.gitignore` has not been modified. This document is read-only analysis for
review. All commands below are suggestions to run manually after you approve
the plan.

---

## 1. Audit

**Total:** 1,074 files, 22 GB, currently entirely untracked (`git status` shows
`?? mechanistic/`).

### Largest directories

| Size | Path | What it is |
|---|---|---|
| 14 GB | `privacy_collapse/persistbench/model_cache/` | HF hub cache (Mistral-7B-Instruct-v0.3 weights) |
| 3.9 GB | `outputs/single_persistbench_case_{rmu_case1,rmu_case2,wga_case1}/` | full per-token activation dumps (`.pt`) for 3 single-case deep-dives |
| 1.9 GB | 7 directories literally named `representations/` (paradox, persistbench_native, persistbench_sycophancy_mcq, muse_news_sycophancy_mechanistic, muse_books_weekly_update_analysis ×2) | pre-extracted hidden-state tensors |
| 1.6 GB | `outputs/privacy_position_analysis/activations/` | per-sample position-level activation tensors (72 `.pt` files) |
| 718 MB | `outputs/muse_books_weekly_update_analysis/` | MUSE-Books comparison analysis (mostly its own `representations/`) |
| ~230 MB | 3 directories named `models/` (privacy_collapse_muse_news_qwen25_7b, privacy_collapse_persistbench_mcq_muse_news_qwen25_7b, privacylens_representation) | mixed: small canonical CSVs **plus** large direction-vector `.pt` files in the same folders |

### Largest individual files

Top 3: three Mistral-7B blob files in `model_cache/`, 4.3–4.8 GB each. After
those, everything over 300 MB is a `.pt` tensor dump (per-case
`base/rmu/wga_representations.pt` in the three `single_persistbench_case_*`
directories, ~320–508 MB each). Nothing outside `model_cache/` and `.pt` files
exceeds 15 MB.

### File extensions (count / total size)

| Ext | Count | Total size | Category |
|---|---|---|---|
| `.pt` | 203 | **7,655 MB** | large binary tensors — dominant risk |
| `.json` | 226 | 93 MB | mixed: manifests, provenance, small results, a few large superseded manifests |
| `.png` | 184 | 25 MB | small plots, safe |
| `.csv` | 152 | 31 MB | small result tables, safe (one 7.8 MB exception) |
| `.py` | 98 | 0.8 MB | source, safe |
| `.pyc` | 76 | 0.8 MB | bytecode cache — already ignored globally (`__pycache__/`, `*.py[cod]`) |
| `.md` | 49 | 0.9 MB | reports, safe |
| `.sbatch` | 40 | <0.1 MB | job scripts, safe |
| `.jsonl` | 13 | 8.2 MB | raw generation corpora — small, safe |
| `.out`/`.err` | 18 | <0.1 MB | stray SLURM logs inside `mechanistic/` (not the repo's shared `logs/`) — tiny but should stay untracked by convention |
| `.txt`, `.TAG` | 4 | <0.1 MB | negligible |
| (no ext) | 11 | (part of the 14 GB) | HF cache blobs inside `model_cache/` |

**Key finding:** of the 7,655 MB in `.pt` files, only 1,908 MB (25%) sits
inside a directory literally named `representations/`, which is the only
pattern the current `.gitignore` covers (`mechanistic/**/representations/`).
The other **5,747 MB (75%) is currently NOT covered by any existing ignore
rule** — it lives in directories named `activations/`, `models/`,
`single_persistbench_case_*/`, and one named `privacylens_representation`
(singular, doesn't match the plural `representations/` pattern), plus ~90
scattered small `.pt` files directly in `outputs/main*/`. This is the main gap
this plan closes.

### Source code / manifests / reports vs. large generated artifacts

- **Source code:** 98 `.py` + 40 `.sbatch` files, 1.6 MB total across all of
  `mechanistic/` — every script that produced every result in this tree.
- **Reports:** 49 `.md` files, 0.9 MB.
- **Manifests/configs/small results:** the `.json`/`.csv`/`.jsonl`/`.png`
  files, ~159 MB combined *before* excluding anything superseded (see §3.2).
- **Large generated artifacts:** the 14 GB model cache + 7.6 GB of `.pt`
  tensor dumps — 21.6 GB, ~98% of the directory's size, and reproducible from
  checkpoints + scripts (none of it is a unique, hand-audited, or manually
  curated artifact — it is all a deterministic function of frozen model
  weights and existing extraction scripts).

---

## 2. TRACK

Everything below is small, reproducibility-critical, and not mechanically
regenerable-and-disposable the way a hidden-state dump is (either because it's
source code, or because it encodes a human decision — a manual audit, a
curated selection, a written result).

- **All Python source:** every `*.py` under `mechanistic/` (98 files, 0.8 MB).
- **All SLURM submission scripts:** every `*.sbatch` under `mechanistic/` (40
  files, <0.1 MB).
- **All Markdown:** every `README.md`, `*_RESULTS.md`, `*_REPORT.md`,
  `EXPERIMENT_INDEX.md`, `RESULTS_REGISTRY.csv` (see next bullet),
  `THESIS_RESULTS_CHEATSHEET.md`, `GIT_TRACKING_PLAN.md` itself, etc. (49
  files, 0.9 MB).
- **Small canonical result CSVs/JSONs** — the actual numbers the thesis cites:
  e.g. `clean_selection.json`, `manual_transition_audit.csv`,
  `clean_per_example_shifts.csv`, `expA_mcq/missing5_readout.csv`,
  `expB_memory/expB_scores.csv`, `mcq_readout_per_example.csv`, all
  `analysis/*.csv` and `analysis/*.json` result files under the final-mechanism
  and paradox directories that are marked CANONICAL/SUPPORTING in
  `mechanistic/experiments/muse_news_sycophancy_final_mechanism/RESULTS_REGISTRY.csv`.
- **Experiment manifests that are inputs, not dumps** — e.g.
  `persistbench_sycophancy_mcq_clear_no_50_v1.json` (0.35 MB),
  `native_sycophancy_200_v1.json` / `native_cross_domain_200_v1.json` under
  `privacy_collapse/persistbench_native/manifests/` (8.5–8.75 MB each — these
  define the actual prompt/token sets every canonical result traces back to).
- **Raw generation corpora, `.jsonl`, under `persistbench_native/generations/`**
  (6 files, ~4.3 MB) — small enough, and these are the literal generations
  behind the canonical sycophancy/cross-domain numbers.
- **All `.png` plots** referenced by a canonical report (25 MB total; none are
  individually large).
- **Provenance JSON** (`*_provenance.json`, `*_metadata.json`) wherever it sits
  next to canonical results — small and needed to interpret the CSVs.

**Approx. size if all of the above is tracked as-is: ~130–160 MB**, before
applying the exclusions in §3.2 for specific large/superseded manifests
(which would bring it down further, to roughly **~100–130 MB**).

---

## 3. DO NOT TRACK

### 3.1 Already covered by existing `.gitignore` (no change needed)

- `mechanistic/**/model_cache/` — the 14 GB HF hub cache. Confirmed fully
  excluded (directory-level match).
- `mechanistic/**/representations/` — 1.9 GB of the 7.6 GB of `.pt` files.
  Confirmed fully excluded.
- `__pycache__/`, `*.py[cod]` — the 76 `.pyc` files (generic rule, already
  applies inside `mechanistic/`).

### 3.2 Needs a new rule (see §4)

- **All remaining `.pt` files outside a `representations/` directory** — 5.75 GB:
  `outputs/single_persistbench_case_*/{base,rmu,wga}_representations.pt`,
  `outputs/privacy_position_analysis/activations/**/*.pt`,
  `outputs/*/models/**/*.pt`, `outputs/muse_books_weekly_update_analysis/privacylens_representation/models/**/*.pt`,
  ~75 small `outputs/main*/*_last_prompt_token.pt` files, and a few misc
  top-level `.pt` files. All of these are activation/direction-vector tensors,
  mechanically regenerable from checkpoints + the scripts that are being
  tracked.
- **Stray SLURM `.out`/`.err` logs living inside `mechanistic/` subdirectories**
  (18 files, negligible size but inconsistent with the rest of the repo, where
  all logs go to the gitignored top-level `logs/`): e.g.
  `outputs/privacy_branch_counterfactuals/slurm-*.{out,err}`,
  `outputs/muse_books_weekly_update_analysis/slurm/logs/*.{out,err}`,
  `experiments/muse_news_sycophancy_final_mechanism/archive/failed_or_superseded/expA_failed_slurm_attempts/*.{out,err}`
  (the last of these was deliberately archived for provenance in the prior
  cleanup pass — its `README.md` explanation should stay tracked, but the raw
  log bytes themselves don't need to be in git; they're already preserved on
  disk).
- **Explicitly superseded, large, do-not-cite outputs** — the old
  pre-manual-audit MUSE-News patching directory,
  `mechanistic/outputs/muse_news_sycophancy_mechanistic/`:
  - `manifests/native_sycophancy_200_no_memory_v1.json` +
    `manifests/native_cross_domain_200_no_memory_v1.json` — 28.3 MB combined,
    superseded duplicates of manifests canonically tracked elsewhere
    (`persistbench_native/manifests/`, `paradox/manifests/`).
  - `manifests/continuation_cases_v1.json` — 1.66 MB, the old noisy 9-case
    selection explicitly forbidden for thesis numbers
    (`EXPERIMENT_PLAN.md` §8).
  - `patching/*.json` — 472 KB, patching outputs computed on the forbidden
    old selection above.
  
  (The three small `.md` reports in that same directory —
  `FINAL_REPORT.md`, `README.md`, `QUALITATIVE_REPORT.md`, ~90 KB total — are
  handled separately in §5, since their *behavioral* numbers were
  independently reproduced and are not disqualified the way the
  selection/patching data is.)

### 3.3 Duplicated large outputs (same content as a canonical location, different dataset arm — not "superseded" so much as "not the primary thesis result")

- `mechanistic/outputs/muse_books_weekly_update_analysis/{native_sycophancy,native_cross_domain}/manifests/*.json`
  — 17.25 MB combined. These are the MUSE-Books analogue of the canonical
  MUSE-News manifests. MUSE-Books does not replicate the sycophancy effect
  (documented in the paradox report) and is not the primary thesis case — see
  §5 for the manual-review recommendation rather than a hard exclusion.

---

## 4. Proposed `.gitignore` additions (minimal)

Deliberately **not** a broad `outputs/` or `mechanistic/**/*.json` rule — both
would catch small canonical results this plan wants tracked. Every line below
is scoped to `mechanistic/` and targets exactly the gap identified in §3.2.

```gitignore
# --- mechanistic/ git-tracking-plan additions (proposed, NOT yet applied) ---
# Closes the gap the existing `mechanistic/**/representations/` rule misses:
# large torch tensor dumps (activations, direction vectors, per-case
# representations) that live outside a directory literally named
# "representations/". ~5.75 GB across outputs/single_persistbench_case_*/,
# outputs/privacy_position_analysis/activations/, outputs/*/models/, and
# outputs/muse_books_weekly_update_analysis/privacylens_representation/models/.
mechanistic/**/*.pt

# Stray SLURM stdout/stderr logs saved inside mechanistic/ subdirectories
# instead of the repo's shared (already-gitignored) logs/ directory.
mechanistic/**/*.out
mechanistic/**/*.err

# Explicitly superseded MUSE-News patching data (old, pre-manual-audit case
# selection; see mechanistic/experiments/muse_news_sycophancy_final_mechanism/
# RESULTS_REGISTRY.csv and EXPERIMENT_PLAN.md section 8 - must not be cited
# for thesis numbers). Only the large manifests/patching data are excluded
# here; the directory's small .md reports are kept trackable.
mechanistic/outputs/muse_news_sycophancy_mechanistic/manifests/native_sycophancy_200_no_memory_v1.json
mechanistic/outputs/muse_news_sycophancy_mechanistic/manifests/native_cross_domain_200_no_memory_v1.json
mechanistic/outputs/muse_news_sycophancy_mechanistic/manifests/continuation_cases_v1.json
mechanistic/outputs/muse_news_sycophancy_mechanistic/patching/
```

Note: `mechanistic/**/*.pt` makes the existing
`mechanistic/**/representations/` line redundant (every `.pt` inside a
`representations/` dir is now also matched by the extension rule), but I'd
recommend **keeping both** — the directory rule is self-documenting about
*why* those directories exist, and costs nothing to keep.

---

## 5. REVIEW MANUALLY

These don't have an obvious, low-risk automatic answer — flagging them
instead of deciding for you.

| Path | Size | Why it's ambiguous |
|---|---|---|
| `outputs/muse_books_weekly_update_analysis/{native_sycophancy,native_cross_domain}/manifests/native_*_200_v1.json` | 17.25 MB | Legitimate manifest (not superseded/forbidden like §3.2's), but for a secondary dataset arm (MUSE-Books) that does not replicate the primary thesis effect. Tracking costs 17 MB for a manifest that's mostly reference/negative-result material. |
| `outputs/benchmark_paradox/next_mechanistic_sample_candidates.csv` | 7.78 MB | Intermediate candidate-sampling output from the upstream discovery pass, not itself a cited thesis number. Its sibling `FINAL_REPORT.md` in the same directory is clearly canonical-context and should be tracked regardless. |
| `outputs/muse_news_sycophancy_mechanistic/{FINAL_REPORT.md,README.md,QUALITATIVE_REPORT.md}` | ~90 KB | Small, so no size reason to exclude — but the directory's selection/patching data is disqualified (§3.2) while these reports' *behavioral* numbers were independently reproduced and treated as historical-context canonical elsewhere. Recommend: **track** (tiny, and useful provenance for how the case was originally found), but this is a judgment call, not a size call. |
| `outputs/privacy_collapse_muse_news_qwen25_7b/prepared_examples.json`, `outputs/muse_books_weekly_update_analysis/privacylens_representation/prepared_examples.json`, `.../sycophancy_mcq/analysis/prepared_examples.json` | 2.0–2.2 MB each (~6.4 MB total) | "Prepared examples" dumps — likely reconstructable from the manifest + extraction script, but also plausibly the exact frozen input to a canonical analysis. Small enough either way; flagging rather than assuming. |
| `outputs/main1` … `outputs/main491` (26 directories) | small individually, ~few MB combined once `.pt` is excluded | These appear to belong to a different/earlier thesis chapter (not the MUSE-News sycophancy mechanism), never audited in the prior cleanup pass. Recommend treating as out-of-scope for *this* plan — flag for a separate pass rather than deciding now. |

---

## 6. Estimated size of the resulting tracked subset

- If every REVIEW MANUALLY item is **included**: ≈ 130–150 MB.
- If every REVIEW MANUALLY item is **excluded**: ≈ 100–110 MB.
- Either way, this is a **~99.3–99.5% reduction** from the current 22 GB
  untracked footprint, and comfortably within normal git repository size norms.

---

## 7. Exact suggested commands (not run)

**Step 1 — apply the `.gitignore` additions from §4** (manual edit, your
review first).

**Step 2 — dry-run to verify scope before staging anything:**

```bash
git add --dry-run mechanistic/ | wc -l          # file count that would be staged
git add --dry-run mechanistic/ | grep '\.pt$'   # MUST be empty — sanity check the .pt rule worked
git add --dry-run mechanistic/ | grep -E '\.(out|err)$'   # MUST be empty
```

**Step 3 — stage (only after the dry run looks right):**

```bash
git add mechanistic/
```

Because `.gitignore` now excludes `model_cache/`, all `.pt` files, stray
`.out`/`.err`, and the specific superseded MUSE-News patching artifacts, a
single `git add mechanistic/` becomes safe and complete — git automatically
skips everything matched by the new ignore rules, so this is no longer a
"blind add."

**Step 4 — verify what actually got staged before committing:**

```bash
git diff --cached --stat mechanistic/ | tail -5     # total insertion count / file count summary
git diff --cached --stat mechanistic/ | grep '\.pt$'  # MUST be empty
du -csh $(git diff --cached --name-only mechanistic/) 2>/dev/null | tail -1   # total staged size
```

**If you want to resolve the §5 REVIEW MANUALLY items as "exclude" before
staging**, add these lines to `.gitignore` first (optional, your call):

```gitignore
mechanistic/outputs/muse_books_weekly_update_analysis/native_sycophancy/manifests/native_sycophancy_200_v1.json
mechanistic/outputs/muse_books_weekly_update_analysis/native_cross_domain/manifests/native_cross_domain_200_v1.json
mechanistic/outputs/benchmark_paradox/next_mechanistic_sample_candidates.csv
mechanistic/outputs/main*/
```

**Do not run `git commit` as part of this plan** — that is a separate,
explicit decision for you to make after reviewing what `git diff --cached
--stat` shows.
