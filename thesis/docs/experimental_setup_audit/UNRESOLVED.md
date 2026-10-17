# Unresolved Questions

Only items that the repository cannot resolve. "Safe to omit" = the thesis can leave the detail out without any false statement; "Needs you" = you must decide or recall.

| # | Question | What is missing / files checked | Safe to omit? |
|---|---|---|---|
| 1 | **Why RMU was kept and PDU dropped** (PDU outranks RMU by derived `Agg` on Qwen2.5-3B: 0.4708 vs 0.4650), and why "top-3" on 2026-05-31 omitted RMU | No script/doc states a rule. Checked all of `research_history/`, `thesis/`, `thesis_cleanup_audit/`, `supervisor_update/` (incl. tarballs), `saves/` selection files, `FINAL_DEFENSE_SLIDE_BLUEPRINT.md`, `MASTER_THESIS_MAP.md`. The post-hoc Phase-1 ranking spreadsheet is not in the repo. | **Needs you** only if you want to give a reason; otherwise state it was a qualitative triage (wording in `CANONICAL_EXPERIMENTAL_SETUP.md` §7). Do not invent a reason. |
| 2 | Why the MUSE-News Track A → Track B switch happened | No contemporaneous note; user previously confirmed not remembered (`MASTER_THESIS_MAP.md` §4A). | Yes. Say only that Track A was completed and superseded. |
| 3 | Whether the `Priv` (MIA-AUC) direction in TOFU `Agg_proxy` was intentional (higher AUC = more leakage but rewarded) | Checked `src/trainer/base.py`, `src/evals/metrics/mia/utils.py:44`, the patch backups in `research_history/03_checkpoint_selection_development/trainer_snapshots/`. No rationale text. | **Needs you** if the TOFU selection metric is described in detail; otherwise describe it as "an MIA-based leakage proxy" without claiming direction. |
| 4 | Which PrivacyLens variant, if any, the thesis intends to report for MUSE-Books/Llama-2 | Free-gen has 0–40% valid parses; forced-choice is degenerate (all "A"). No summary CSV for Books-Llama-2 or decision note. | **Needs you**: either exclude Books-Llama-2 PrivacyLens or report validity-limited numbers with the caveat. |
| 5 | Whether `thesis/scripts/muse_news/run_final_muse_eval_qwen25_7b_instruct_selected.sh` ever ran | No `saves/eval/final_*` output exists. MUSE values used here come from in-training `MUSE_SUMMARY.json`/`trainer_state.json`. | Yes (the in-training evals are sufficient and verified). |
| 6 | Books-Qwen BASE full `MUSE_EVAL.json`/MIA values | Finetune-time evals ran on the News split (config bug); only step-0 scalars exist in unlearn logs (`saves/unlearn/muse_books_qwen25_7b_instruct_*/*.log`). | Yes, unless the thesis needs BASE MIA values for Books-Qwen; then a re-evaluation of the finetuned target on the Books split is required. |
| 7 | Training recipe of the official `muse-bench/*_target` models | Not in the repository. | Yes (cite the MUSE paper/HF card). |
| 8 | Exact GPU model for MUSE training/generation | Only SLURM `gpu:a180:1`; A100-80GB-PCIe is inferred from an OOM trace and Track A `nvidia-smi` (`logs/muse_qwen_ft_407874.err`, `logs/muse_news_406780_0.out`). | Yes: write "one 80 GB-class NVIDIA GPU (SLURM `a180`)" or omit. |
| 9 | Post-run `pip freeze` for the training env and per-run git commit | `thesis/manifests/environment/*` dates from 2026-06-24, before the `best_agg` patch (2026-07-06); versions are consistent with run logs and saved configs. | Yes; state versions as "recorded environment" and mention the uncommitted trainer patch. |
| 10 | Effective repetition penalty for Llama-2 PersistBench runs from the HF-hub `muse-bench/MUSE-Books_target` config | Local checkpoint `generation_config.json` has no sampling fields and no vLLM override line appears; hub copy not opened. Derived: 1.0. | Yes (state "vLLM defaults; no model-specific override logged"). |
| 11 | PersistBench results for TOFU Qwen2.5-3B/14B and Llama-3.2-3B | No such outputs under `external/PersistBench/outputs/`. | Yes: PersistBench on TOFU covers Qwen2.5-7B and Llama-3.1-8B only. |
| 12 | How the ad hoc May 17–20 `tofu_*_fixed` runs were launched; why Llama-3.2-3B B2 uses a 13-step eval grid while Qwen uses 26 | No scripts in repo. | Yes (exploratory stage). |
| 13 | Whether the validity script's pre-migration SHA (`9500396a…`) equals the current copy (`dcc538c8…`; header says only ROOT changed) | Original `tmp_paths` copy not preserved bit-for-bit; I confirmed pooled `valid_pct` reproduce from the current copy. | Yes (cite the current path); mention the path edit only if reproducibility is audited. |
| 14 | Exposé/midterm wording (RQ evolution, midterm "four methods fixed" statement, CIMemories→PersistBench change) | PDF/PPTX not in repo; `MASTER_THESIS_MAP.md` relays user-reported content. | **Needs you** to quote from the originals if cited. |

## Conflicts that are resolved by the repository (listed so they are not re-opened)

- 10-method model set: use Llama-3.2-1B and Qwen2.5-3B (10/10), Qwen2.5-1.5B (8/10) — not "Llama-3.2-3B".
- "tofufull" = TOFU-full-finetuned start with forget10 — not a full forget set.
- `a100`/`a180` = SLURM GPU labels.
- `repetition_penalty` = 1.05 (Qwen runs), not 1.08.
- "Invalid generations excluded" = true only for valid-aware recomputations, not official FR@K.
- `checkpoint-500` was never a candidate in canonical MUSE runs.
- `thesis/docs/persistbench_patch.md:17` dates the truncation patch ~07-05 while `generation_provenance.md` §5 says 07-21; mtimes support 07-05 for truncation and 07-21 for STRICT_GENERATION_CONTROL. Moot for MUSE (truncation is recorded in each output's `api_params`).
