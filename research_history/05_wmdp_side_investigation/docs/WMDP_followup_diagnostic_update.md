# WMDP Follow-up Diagnostic Update

## 1. Goal

Last week we agreed to revisit WMDP before moving to interpretability.

The goal is to understand whether WMDP gives a clean safety-side result, or whether the results are dominated by generation collapse / invalid outputs.

## 2. Artifact recovery

I recovered the previous WMDP artifacts inside:

`/storage/ukp/work/elshashay/open-unlearning`

Important folders/files found:

- `saves/final_wmdp_cyber_all4_selection`
- `outputs/wmdp_cyber_all4_summary`
- `outputs/wmdp_cyber_all4_summary/wmdp_cyber_all4_sweep300_scores.tsv`

This means WMDP was not missing. It had already been run before the midterm, but it was not included because the results had validity/collapse issues.

## 3. WMDP-Cyber safety sweep summary

I recovered and summarized the WMDP-Cyber sweep results.

The sweep contains:

- 2 models: Llama2-7B and Qwen2.5-7B
- 4 methods: RMU, WGA, SimNPO, SatImp
- checkpoints from step 0 to 300

| Model | Method | Step-0 Acc. | Lowest Acc. | Best Checkpoint | Δ vs Step 0 | Final Acc. | Final Δ |
|---|---|---:|---:|---|---:|---:|---:|
| Llama2-7B | RMU | 34.17 | 26.47 | checkpoint-280 | -7.70 pp | 26.72 | -7.45 pp |
| Llama2-7B | SatImp | 34.17 | 25.31 | checkpoint-280 | -8.86 pp | 25.31 | -8.86 pp |
| Llama2-7B | SimNPO | 34.17 | 29.54 | checkpoint-260 | -4.63 pp | 32.81 | -1.36 pp |
| Llama2-7B | WGA | 34.17 | 24.51 | checkpoint-260 | -9.66 pp | 24.71 | -9.46 pp |
| Qwen2.5-7B | RMU | 54.45 | 33.92 | checkpoint-260 | -20.53 pp | 36.74 | -17.72 pp |
| Qwen2.5-7B | SatImp | 54.45 | 42.02 | checkpoint-280 | -12.43 pp | 45.34 | -9.11 pp |
| Qwen2.5-7B | SimNPO | 54.45 | 47.36 | checkpoint-240 | -7.10 pp | 49.97 | -4.48 pp |
| Qwen2.5-7B | WGA | 54.45 | 24.46 | checkpoint-300 | -30.00 pp | 24.46 | -30.00 pp |

## 4. Current interpretation

WMDP-Cyber accuracy measures cyber benchmark performance. Lower accuracy after unlearning suggests reduced cyber capability.

However, this alone is not enough to claim clean safety unlearning, because the model may also be damaged or collapsed.

So the WMDP question should be separated into:

1. Safety accuracy:
   Did the unlearning method reduce WMDP-Cyber capability?

2. Generation validity:
   Are the resulting model generations still interpretable, or did they collapse / become contaminated?

The main risk is that lower WMDP accuracy may reflect model damage rather than a clean safety-side unlearning effect.

## 5. Next diagnostic step

Next I need to connect the WMDP safety table with validity/collapse diagnostics:

- check selected checkpoints,
- inspect PrivacyLens / generation outputs for WMDP,
- identify which methods collapse,
- collect 2–3 examples of invalid outputs,
- decide whether WMDP should be a main result or only a backup diagnostic.

## 6. Proposed plan before interpretability

1. Verify existing WMDP safety results.
2. Collect validity and collapse diagnostics.
3. Rerun only problematic settings if needed.
4. Then move to RQ3 interpretability on the clearest behavioural setting.
