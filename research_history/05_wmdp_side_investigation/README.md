# Phase 05 — WMDP side investigation

**This is real, completed research history, not obsolete clutter.** The smoke-test scripts kept here document a genuine debugging iteration, not discarded junk.

## 1. Question investigated
Does the thesis's unlearning methodology (particularly RMU) generalize as a safety intervention on WMDP-cyber/bio, and can a robust generation/judging pipeline for it be established?

## 2. Dataset / models / methods
WMDP-cyber, WMDP-bio; Qwen2.5-7B (various unlearned checkpoints); RMU and other methods; an MMLU utility follow-up.

## 3. Key scripts / docs
- The full smoke→fixed→sweep→real iteration, kept together deliberately: `scripts/run_wmdp_cyber_all4_smoke_array.sh` → `_nonrmu_smoke_fixed_array.sh` → `_all4_sweep300_array.sh` → `_rmu_real_array.sh`
- `scripts/run_wmdp_cyber_before_eval.sh`, `run_wmdp_cyber_qwen25_7b_rmu_test.sh`, `run_wmdp_bio_test_qwen_books_before.sh`
- `scripts/run_wmdp_mmlu_qwen_{small,missing,wga_sweep}.sh` — utility follow-up
- `scripts/run_persistbench_wmdp_cyber_*.sh` (generate/judge, including the "strict generation" variants — **this is where `PB_REPETITION_PENALTY=1.08` was actually introduced and is correct**, see `../../thesis/docs/generation_provenance.md`)
- `scripts/run_persistbench_qwen25_7b_{full_generate,test}.sh`, `run_persistbench_qwen_wga_ckpt*.sh`, `run_persistbench_{full_generate_from_list,judge_array}.sh`, `run_privacylens_wmdp_cyber_all4_selected.sh`
- `manifests/` — the WMDP-specific model-list `.tsv`/`.txt` files these scripts reference
- `scripts/run_persistbench_qwen25_7b_test.sh.pre_flashinfer_fix_maxlen4096` — moved here 2026-09-14 from the redundant `supervisor_update/` snapshot bundle, since it turned out **not** to be a plain duplicate of `run_persistbench_qwen25_7b_test.sh` above: it predates a fix for a FlashInfer JIT sampler compilation problem (CUDA 12.2 + GCC 14) — the live script exports `VLLM_USE_FLASHINFER_SAMPLER=0` to work around it, this snapshot does not — and it predates a context-length increase (`--max-model-len` 4096 here vs. 8192 in the live script). Kept as a genuine debugging-iteration record, not discarded as redundant.
- `docs/WMDP_followup_diagnostic_update.md`, `qwen_wmdp_mmlu_privacylens_full.csv`, `wmdp_privacylens_structure.csv`, `meeting_updates_wmdp_safety_summary.csv` — the supervisor meeting note that records this phase's findings and the decision to move on

## 4. What was learned
Real validity/collapse issues were found in early WMDP results (documented in the meeting note itself), motivating the smoke→fixed→sweep→real debugging chain. Every step in that chain is kept here together because each documents a real iteration — none is discarded as "just a smoke test."

## 5. Why the thesis moved on
The meeting note explicitly records the decision to revisit WMDP once more, then pivot to interpretability work — the mechanistic-interpretability phase in `../../thesis/` begins within days of the final WMDP meeting update.

## 6. Influence on final methodology
This is where the `PB_REPETITION_PENALTY=1.08` setting (and the other `STRICT_GENERATION_CONTROL` defaults in `external/PersistBench/utils.py`) was actually introduced and used (2026-07-21/22) — directly relevant context for the generation-provenance correction documented in `../../thesis/docs/generation_provenance.md` and `../../thesis/manifests/provenance/persistbench_generation_corrections.json`: `1.08` is a real, legitimate setting for this WMDP work, just incorrectly and later backfilled onto the description of the earlier (and unrelated) MUSE generation runs.
