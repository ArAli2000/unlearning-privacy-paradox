# Weekly supervisor update: slide material

## Scientific story in one sentence

Gemma-3-12B independently reproduces a contextual-privacy degradation signal in 9/12 BASE→unlearning comparisons, while substantial judge disagreement shows that effect magnitude and case-level classification are evaluation-model dependent.

## Recommended slide structure

### 1. Motivation: is the finding judge-family dependent?

- Thesis: evaluate privacy preservation in LLM unlearning beyond memorization.
- Previous PersistBench evaluation used Qwen2.5-7B-Instruct as judge; some evaluated checkpoints are also Qwen-family models.
- Question: does the contextual-privacy conclusion survive an independent judge?
- Frame Gemma as a robustness check, not replacement ground truth.

### 2. Independent validation design and verification

- Judge: `google/gemma-3-12b-it`.
- Same stored model generations, re-judged with Gemma.
- 19,500 judgment requests; maximum prompt 9,249 tokens; 9,505 tokens required with output headroom; server maximum model length 16,384.
- No truncation, request errors, or unparseable outputs.
- Suggested compact table source: `gemma3_prompt_length_analysis.json` plus section 8 of `GEMMA_ONLY_SUPERVISOR_RESULTS.md`.

### 3. Main result: cross-domain FR@1

- Show `gemma_cross_domain_base_vs_unlearning.png`.
- Headline: 9/12 worsen, 2 improve, 1 unchanged.
- Safe claim: “Gemma independently reproduces a contextual privacy degradation signal.”
- Required qualification: “The signal is not universal, and its magnitude depends on the evaluation model.”

### 4. Heterogeneity across tracks and methods

- Show `gemma_method_consistency.png` beside the three-track result table if space permits.
- RMU: 3 worse / 0 better / 0 same.
- SimNPO: 3 / 0 / 0.
- WGA: 2 / 1 / 0.
- SatImp: 1 / 1 / 1.
- Emphasize the Books/Llama exceptions: WGA −32.5 pp; SatImp −2.5 pp. Books/Qwen SatImp is unchanged.

### 5. Judge agreement: robustness is partial

- Show `qwen_vs_gemma_agreement.png`.
- Cross-domain: 62.3% exact agreement, κ=0.2527.
- Sycophancy: 38.3%, κ=0.1511.
- Beneficial memory usage: 66.6%, κ=0.4921.
- Interpretation: aggregate degradation can reproduce even though exact scores/case labels remain judge dependent.

### 6. Consequence for mechanistic analysis

- Show `mechanistic_transition_reclassification.png`.
- SatImp: 130/200 (65%) transition assignments change under Gemma.
- SimNPO: 124/200 (62%) change.
- Rename earlier groups “Qwen-defined transition groups.” Do not present them as judge-independent ground truth.
- Existing representation plots remain useful only with that provenance qualifier; do not reinterpret them as Gemma-defined analyses.

### 7. Limitations and next steps

- Neither judge is ground truth; exact classification and effect size are judge dependent.
- Only three dataset/model tracks and four methods are represented in the 12 comparisons.
- The direction-count summary is descriptive; paired McNemar results in the report vary by comparison and are not multiple-comparison adjusted.
- Next: adjudicate a stratified disagreement sample (ideally human or a rubric-audited third judge); report judge-stratified estimates; repeat mechanistic selection using Gemma-defined or consensus-defined groups before making judge-independent mechanistic claims.

## Exact Gemma cross-domain table

| Track | BASE | RMU | WGA | SimNPO | SatImp |
|---|---:|---:|---:|---:|---:|
| MUSE-News / Qwen2.5-7B-Instruct | 29.0 | 35.5 (+6.5) | 33.5 (+4.5) | 35.0 (+6.0) | 35.5 (+6.5) |
| MUSE-Books / Llama-2-7B | 61.0 | 80.0 (+19.0) | 28.5 (−32.5) | 70.0 (+9.0) | 58.5 (−2.5) |
| MUSE-Books / Qwen2.5-7B-Instruct | 30.0 | 43.0 (+13.0) | 32.0 (+2.0) | 34.0 (+4.0) | 30.0 (+0.0) |

All cells are cross-domain FR@1 percentages; deltas are percentage points relative to BASE. Source: `../gemma_only_exact_results.csv`, filtered to `category=cross_domain`.

## Available related material

- Definitive Gemma-only narrative and uncertainty tables: `../GEMMA_ONLY_SUPERVISOR_RESULTS.md`.
- Exact machine-readable Gemma results: `../gemma_only_exact_results.csv` and `../gemma_only_exact_results.json`.
- Full Qwen/Gemma comparison: `../QWEN_VS_GEMMA_ANALYSIS.md`, `../qwen_vs_gemma_frk.json`, and `../qwen_vs_gemma_agreement.json`.
- Mechanistic transition comparison: `../qwen_vs_gemma_mechanistic_transitions.json`.
- Raw Gemma judgments: `../../../../external/PersistBench/outputs_gemma3_judge/` (15 JSON result files in track subdirectories).
- Prior weekly-update style/material reference: `../../../../mechanistic/outputs/muse_books_weekly_update_analysis/README.md` and its figures. No PowerPoint, Keynote, ODP, or thesis slide PDF was found in the repository.
- Broader mechanistic figures exist under `mechanistic/outputs/muse_books_weekly_update_analysis/`, `mechanistic/outputs/privacy_population_12v12/`, and `mechanistic/outputs/privacy_position_analysis/`; they are background material, not new Gemma validation results.

## Wording guardrails

Use: “The degradation signal appears under an independent judge, but the magnitude depends on the evaluation model.”

Avoid: “Unlearning always worsens privacy,” “Gemma is ground truth,” or “the transition groups are judge independent.”
