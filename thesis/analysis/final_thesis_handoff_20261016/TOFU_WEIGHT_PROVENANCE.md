# TOFU weight provenance: were the selected checkpoints evaluated?

**Question.** The earlier handoff noted that the TOFU behavioural evaluations loaded each run directory's *top-level* weights rather than the selected `checkpoint-N` folder, and that the two had not been byte-compared. Is the thesis statement "the selected TOFU checkpoints were used for behavioural evaluation" factually correct?

**Answer: yes for the weights, with one wording caveat for the paths.** For all 8 TOFU unlearned conditions in the thesis (Qwen2.5-7B-Instruct and Llama-3.1-8B-Instruct, each with RMU, WGA, SatImp, SimNPO), every weight shard of the top-level run directory is **byte-identical (SHA-256)** to the corresponding shard of the selected checkpoint, and all config and tokenizer files are identical too. The evaluated weights therefore *are* the selected checkpoint. The statement is **not** accurate if it is read as "the evaluation loaded the `checkpoint-N` directory": most evaluations loaded the run directory (details below).

Table: `tofu_weight_provenance.tsv` (20 rows: 8 unlearned conditions × 2 benchmarks, plus the 2 Targets × 2 benchmarks). No directory was modified; hashing was read-only (`scripts/tofu_hash_dirs.py`, raw hashes in `scripts/_tofu_hashes.json`).

## What each evaluation loaded (from logs / output metadata)

| Evaluation | Qwen2.5-7B-Instruct (TOFU) | Llama-3.1-8B-Instruct (TOFU) |
|---|---|---|
| PersistBench | top-level run directory (vLLM server log `model=`) | top-level run directory (vLLM server log `model=`) |
| PrivacyLens | **`checkpoint-104` directly** (`meta.model_path` in the output JSON) | top-level run directory (`meta.model_path`) |
| Targets | start model directory (`saves/finetune/tofu_Qwen2.5-7B-Instruct_full`), no selection | Hugging Face snapshot `…/snapshots/1a5c5b1a…`, no selection |

## Selected checkpoint vs top-level weights

| Model | Condition | Selected step | Top-level vs selected checkpoint: weight shards | Config + tokenizer files | Other evidence |
|---|---|---|---|---|---|
| Qwen2.5-7B | RMU | 104 | 4/4 identical | identical | trainer state: final step 120, `best_model_checkpoint` = checkpoint-104; `BEST_CHECKPOINT.txt` → checkpoint-104 |
| Qwen2.5-7B | WGA | 104 | 4/4 identical | identical | same pattern |
| Qwen2.5-7B | SatImp | 104 | 4/4 identical | identical | same pattern |
| Qwen2.5-7B | SimNPO | 104 | 4/4 identical | identical | same pattern |
| Llama-3.1-8B | RMU | 65 | 4/4 identical | identical | final step 120, best 65; `checkpoint-120` holds no weights (pruned) |
| Llama-3.1-8B | WGA | 117 | 4/4 identical | identical | final step 120, best 117; `checkpoint-120` pruned |
| Llama-3.1-8B | SatImp | 52 | 4/4 identical | identical | final step 120, best 52; `checkpoint-120` pruned |
| Llama-3.1-8B | SimNPO | 120 | 4/4 identical | identical | best step = last step = 120 |

- The top-level shards are **separate physical files** (distinct inodes, not symlinks or hardlinks), so the match is a real content match, not one file compared to itself. The only file that differs between each top-level directory and its checkpoint is `trainer_state.json`, which is expected (the top-level one records the final step and best-checkpoint pointer).
- The top-level weights were written after the last training step (for example Qwen RMU: top-level shard at 01:06 versus `checkpoint-104` at 00:55) and match the *best* checkpoint, not the final one. For seven of the eight runs the selected step is earlier than the final step 120, so the top-level weights are the selected checkpoint's weights and not the step-120 weights. This is consistent with the trainer reloading the best model before its final save, but I did not verify the training code path, only the byte identity.
- **Negative control (Qwen RMU):** the top-level weights were also compared with `checkpoint-78` and `checkpoint-120`. Shard 1 differs from both (and matches only `checkpoint-104`). Shards 2–4 are identical across all three checkpoints, which is expected for RMU because it edits only some layers. So the comparison can distinguish steps, and for RMU shard 1 is the deciding file. For the other seven runs all shards of the selected checkpoint matched, and no further checkpoint was hashed because it was not needed to answer the question.
- **Timeline:** all weight files were last written on 18–20 June 2026, before the earliest evaluation outputs (PrivacyLens 19–20 June, PersistBench 29 June), so the hashes taken today describe the files that were loaded (file times are supporting evidence, not proof of immutability).
- **Selection record:** the selected step in each case equals the trainer state's `best_global_step` of the run (Qwen 104; Llama 65 / 117 / 52 / 120) and the step listed in `thesis/docs/experimental_setup_audit/selected_checkpoints.tsv`.

## Wording for the thesis

- Safe: "The evaluated TOFU unlearned models are the selected checkpoints; the run directories used for evaluation contain weights that are byte-identical to the selected checkpoint (SHA-256)."
- Not accurate as a blanket statement: "evaluations loaded `checkpoint-N`". Only PrivacyLens on TOFU Qwen2.5-7B did; PersistBench (both models) and PrivacyLens on Llama-3.1 loaded the run directory.
- Targets have no checkpoint selection; they are the TOFU-finetuned start models.

## Remaining quirks (do not change the conclusion)

- Llama-3.1 SimNPO: the directory on disk is named `…simnpo_from_tofufull_aggproxy_savebest`, but its trainer state records `best_model_checkpoint` as `…simnpo_from_tofufull_selectionproxy_savebest/checkpoint-120` (a name mismatch, same step 120). The weights in the evaluated directory are byte-identical to its own `checkpoint-120`.
- Scope: this covers the TOFU 7B/8B models in the thesis configuration tables. The PrivacyLens output folders also contain smaller TOFU scaling models (Qwen2.5-3B/14B, Llama-3.2-3B); those were not compared.
