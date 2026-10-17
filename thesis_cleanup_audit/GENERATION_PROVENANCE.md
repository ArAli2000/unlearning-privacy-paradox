# Generation provenance: MUSE-News / MUSE-Books PersistBench settings

Read-only forensic investigation. Nothing was moved, renamed, deleted, modified, or rerun. Every value below is sourced from one of: (1) metadata embedded directly in the frozen PersistBench output JSON files, (2) the exact `vLLM` server stdout logs from the actual generation jobs, (3) the exact launcher script used for that job, or (4) `stat` mtimes establishing what code existed at run time. Current code is used as evidence only where its presence at the run date is independently proven (never as a default assumption) — this is stated explicitly wherever it applies.

## 0. Scope and job identification

| Run | Launcher | SLURM array job | Generation date (from log/file mtime) |
|---|---|---|---|
| MUSE-News, Qwen2.5-7B-Instruct (canonical Track B): BASE/RMU/WGA/SimNPO/SatImp | `run_persistbench_muse_news_qwen25_selected.sh` | 408558 (tasks 0–4) | 2026-07-08 |
| MUSE-Books, Llama-2-7b (official target): BASE/RMU/WGA/SatImp/SimNPO | `run_persistbench_muse_books_llama2_selected.sh` | 408885 | 2026-07-10 |
| MUSE-Books, Qwen2.5-7B-Instruct (locally finetuned): BASE/RMU/WGA/SatImp/SimNPO | `run_persistbench_muse_books_qwen25_selected.sh` | 409517 | 2026-07-12 |

Per `MUSE_NEWS_TRACK_RESOLUTION.md`, Track A (MUSE-News official-Llama-2-target) is superseded and not the canonical result; it is not investigated in depth here, but nothing below changes if it were — its generation predates all patches to `utils.py` even more completely than Track B's.

## 1. Confirmed / strongly-supported settings, per run

Evidence for every row below comes from `d["config"]["models"][0]["api_params"]` inside the frozen output files themselves (e.g. `external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_before.json`) and the exact `vllm serve` invocation lines in each launcher script — **identical across all three runs above**, confirmed by direct comparison, not assumption:

| Setting | Value | Evidence tier | Source |
|---|---|---|---|
| `temperature` | `0.0` | **CONFIRMED** | `config.models[0].api_params.temperature` in every one of the 3 primary output files (News-Qwen, Books-Llama2, Books-Qwen `before.json`, each spot-checked) |
| `max_tokens` (generated response length cap) | `96` | **CONFIRMED** | same `api_params` field, all 3 runs |
| `truncate_prompt_tokens` | `1800` | **CONFIRMED** | `api_params.extra_body.truncate_prompt_tokens`, all 3 runs |
| Truncation side | left (drops earliest tokens, keeps the prompt tail before the final user turn) | **STRONGLY SUPPORTED** | not itself a separate request field; this is vLLM's documented behavior for the `truncate_prompt_tokens` extra-body parameter, which was confirmed present (row above) |
| Number of generations per benchmark item | `3` for `cross_domain` (200 items), `3` for `sycophancy` (200 items), `1` for `beneficial_memory_usage` (100 items) — 1,300 generations total per model | **CONFIRMED** | directly counted from `entries[*]["results"][model]["generations"]` list lengths in all 3 primary output files; identical distribution in all 3 |
| Chat template | `templates/simple_llama_chat_template.jinja` | **STRONGLY SUPPORTED** | exact `--chat-template` flag in both the News-Qwen and Books-Llama2 launcher scripts, byte-identical text, confirmed by direct read; applied uniformly regardless of model family (a Llama-oriented template name used for the Qwen runs too — this is an accurate reading of the script, not a copy-paste error on this audit's part) |
| Serving stack / dtype | vLLM OpenAI-compatible server, `--dtype bfloat16`, `--gpu-memory-utilization 0.90`, `--max-model-len 2048` | **STRONGLY SUPPORTED** | exact `vllm serve` command line, identical across launchers |
| Provider (PersistBench-side) | `"openai_compatible"` | **CONFIRMED** | `config.models[0].provider` in output metadata |
| System prompt (thesis-added override) | **none active** | **CONFIRMED (by exclusion)** | the `STRICT_GENERATION_CONTROL` block that later injects a "do not output JSON/code" system prompt was added to `utils.py` on 2026-07-21 22:19 — after all 3 generation dates above (07-08, 07-10, 07-12); confirmed via `stat` mtime and the incremental `.bak_*` diff chain already established in `PERSISTBENCH_MODIFICATIONS.md` §4. Whatever system prompt was actually used came from PersistBench's own unmodified `prompts.py` (confirmed not among the 4 files this thesis modified — see `PERSISTBENCH_MODIFICATIONS.md` §0), not from any thesis patch. |
| `seed` | not set anywhere | **UNKNOWN**, practically inconsequential | no `--seed` flag on any `vllm serve` invocation, no `seed` field in any `api_params`; since `temperature=0.0` forces greedy/argmax decoding (no sampling occurs), a seed would not have affected which tokens were chosen even if one had been set |
| `do_sample` | not applicable | **N/A** | this is a HF-`transformers`-`generate()` concept; generation here goes through vLLM's OpenAI-compatible chat-completions API, which has no such field — `temperature=0.0` is the operative equivalent (forces deterministic/greedy output) |

## 2. Repetition penalty, top_p, top_k — model-family-dependent, recovered from vLLM's own startup log

None of the three launcher scripts' `api_params` set `repetition_penalty`, `top_p`, or `top_k` explicitly. **The strongest possible evidence — the vLLM API server's own startup log for the exact job in question — resolves what applied instead.**

### Qwen2.5-7B-Instruct-based runs (MUSE-News Track B, MUSE-Books Qwen track)

Every one of the 7 vLLM logs checked (5 MUSE-News jobs, 2 MUSE-Books-Qwen jobs — `logs/vllm_muse_news_qwen25_{before,rmu,wga,simnpo,satimp}_408558_*.log`, `logs/vllm_muse_books_qwen25_{before,satimp,simnpo}_409517_*.log`) contains the **identical** line, timestamped at the actual generation date:

```
WARNING 07-08 12:40:57 [model.py:1502] Default vLLM sampling parameters have been overridden by the model's
`generation_config.json`: `{'repetition_penalty': 1.05, 'temperature': 0.7, 'top_k': 20, 'top_p': 0.8}`.
If this is not intended, please relaunch vLLM instance with `--generation-config vllm`.
```

(shown for job 408558 task 0; the 07-12 MUSE-Books-Qwen logs show the identical dict at their own timestamps). This is vLLM auto-adopting the checkpoint's own `generation_config.json` (independently confirmed by reading `saves/finetune/muse_news_qwen25_7b_instruct_target/generation_config.json` and `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459/generation_config.json`, both containing exactly `repetition_penalty: 1.05, temperature: 0.7, top_k: 20, top_p: 0.8`) as its **base sampling defaults**, overridden per-field by whatever the request explicitly specifies.

Since the request explicitly specified only `temperature=0.0` (overriding the 0.7 default) and nothing for `repetition_penalty`/`top_p`/`top_k`:

| Setting | Effective value | Evidence tier |
|---|---|---|
| `repetition_penalty` | **1.05** | **CONFIRMED** — vLLM startup log, all 7 Qwen jobs checked (5 News + 2 Books), dated exactly at generation time |
| `top_p` | 0.8 (as logged), but **had no effect on the output** since `temperature=0.0` forces greedy/argmax token selection, which does not draw from a top-p/top-k-restricted distribution | **CONFIRMED** value logged; **practically moot** given confirmed `temperature=0.0` |
| `top_k` | 20 (as logged), same "moot under greedy decoding" caveat as `top_p` | **CONFIRMED** value logged; practically moot |

### Llama-2-7b-based run (MUSE-Books official target)

The equivalent log (`logs/vllm_muse_books_llama2_before_408885_0.log`) was checked for the same warning and **does not contain it** — no "Default vLLM sampling parameters have been overridden" line appears anywhere in that log. This means either the Llama-2 checkpoint's own `generation_config.json` does not set these fields, or no override applied for another reason not captured in the log; this audit did not locate a `generation_config.json` for the Llama-2-7b MUSE-Books target on disk (it uses the official HF-cached `muse-bench/MUSE-Books_target`/`NousResearch/Llama-2-7b-hf` tokenizer rather than a locally-saved finetune directory, so no local copy of that file was found to inspect directly).

| Setting | Effective value | Evidence tier |
|---|---|---|
| `repetition_penalty` | not established | **UNCERTAIN** — no override warning observed, no explicit request value; most plausibly vLLM's own neutral default (no penalty), but this cannot be confirmed from available repository evidence |
| `top_p` / `top_k` | not established | **UNCERTAIN**, same reasoning; also practically moot given `temperature=0.0` |

## 3. The `repetition_penalty = 1.08` claim: status = **INCORRECT**

`mechanistic/outputs/muse_books_weekly_update_analysis/README.md`, section "Provenance and artifact map," states: *"Generation source: `external/PersistBench/outputs/muse_books_qwen25_selected_full/*.json`; temperature 0, max 96 tokens, **repetition penalty 1.08**, left truncation to 1,800 tokens, vLLM seed 0."*

**This is incorrect for the Qwen-based generation it describes.** The chain of evidence:

1. The actual PersistBench request `api_params` for this exact run (`muse_books_qwen25_selected_full`) contain no `repetition_penalty` field at all (§1).
2. The vLLM server that actually ran this generation (`logs/vllm_muse_books_qwen25_before_409517_0.log`, 2026-07-12) logged the effective value as **1.05**, not 1.08 (§2).
3. **The exact source of the "1.08" figure is found and is not a runtime measurement of anything**: it is a literal hardcoded value in two Python scripts —
   ```
   mechanistic/privacy_collapse/persistbench_native/prepare_native_200.py:208:      "repetition_penalty": 1.08,
   mechanistic/privacy_collapse/persistbench_native/prepare_native_sycophancy_200.py:243:  "repetition_penalty": 1.08,
   ```
   Both scripts **repackage already-generated PersistBench responses** (they read `generated_response`/`memory_response` text that already exists in `external/PersistBench/outputs/.../*.json` and copy it into a new JSONL shape for hidden-state extraction) — they do not call any generation API themselves and therefore cannot have measured this value at run time. The `1.08` is a hardcoded literal written into a `generation_settings` metadata dict for documentation purposes, alongside `"top_p": 1.0` (also unconfirmed/incorrect — the actual effective value was 0.8 per §2) and `"vllm_seed": 0` (also unconfirmed — no seed was ever set, §1).
4. `1.08` is not an arbitrary wrong number — it exactly matches the `PB_REPETITION_PENALTY` environment-variable **default** introduced into `external/PersistBench/src/benchmark/utils.py`'s `STRICT_GENERATION_CONTROL` block on **2026-07-21** (`params["extra_body"]["repetition_penalty"] = float(os.environ.get("PB_REPETITION_PENALTY", "1.08"))`), and it is the exact value two later, out-of-scope WMDP-cyber scripts explicitly export (`run_persistbench_wmdp_cyber_qwen_strict_generate.sh:18` and `_limit50.sh:19`, both 2026-07-21/22). **The most likely explanation, fully consistent with all dated evidence: whoever wrote `prepare_native_200.py` (mtime 2026-09-06, i.e. written roughly two months after the actual MUSE generation) looked at the then-current `utils.py` to describe what generation settings were probably used, and that file's `STRICT_GENERATION_CONTROL` default was 1.08 by then — this is exactly the trap of treating current code as historical evidence, and it produced a documented, propagated, incorrect number.**

**Classification: INCORRECT**, not merely unsupported — this audit has affirmative, dated, run-specific evidence (the vLLM server's own log) that directly contradicts the 1.08 figure with a different concrete number (1.05).

### Where this claim (or its source) appears

| File | What it contains | Needs correction? |
|---|---|---|
| `mechanistic/outputs/muse_books_weekly_update_analysis/README.md` | States "repetition penalty 1.08" in prose, in the provenance section | **Yes** |
| `mechanistic/outputs/muse_books_weekly_update_analysis/DISCOVERY_REPORT.md` | Does **not** repeat the specific number (checked directly; no `repetition_penalty` match) | No |
| `mechanistic/privacy_collapse/persistbench_native/prepare_native_200.py:208` | Hardcoded source of the number | Yes, at a later code-fix stage (not this read-only pass) |
| `mechanistic/privacy_collapse/persistbench_native/prepare_native_sycophancy_200.py:243` | Same hardcoded number | Yes, same as above |
| 9 generated JSONL files carrying the propagated metadata: `mechanistic/privacy_collapse/persistbench_native/generations/{base,satimp,simnpo,sycophancy_base,sycophancy_satimp,sycophancy_simnpo}_generation0.jsonl` and their 3 Books-side copies under `mechanistic/outputs/muse_books_weekly_update_analysis/native_sycophancy/generations/` | Each record's `generation_settings.repetition_penalty` field | Data files — flag with an errata note rather than edit in place; the `generated_response` text itself in these files remains a valid frozen artifact, only the metadata *describing* it is wrong |
| `thesis_cleanup_audit/PERSISTBENCH_MODIFICATIONS.md`, `CODE_QUALITY_REVIEW.md`, `METHODOLOGY_PRESERVATION_PLAN.md` (this audit's own prior output) | Already flagged this exact figure as needing verification, without yet confirming/refuting it | This document (`GENERATION_PROVENANCE.md`) supersedes those with a definitive answer; no edit needed to the prior files, but any future reader should be pointed here |

No other document (searched: every `.md`, `.py`, `.json`, `.jsonl`, `.sh`, `.csv` outside `.venv`) repeats the specific figure "1.08" in a MUSE-News/MUSE-Books generation-settings context.

## 4. MUSE-News vs. MUSE-Books: same or different settings?

**Mostly identical, with one confirmed model-family-driven difference and one unresolved model-family gap:**

| Setting | MUSE-News (Qwen, Track B) | MUSE-Books (Qwen) | MUSE-Books (Llama-2) | Same across all three? |
|---|---|---|---|---|
| `temperature` (requested) | 0.0 | 0.0 | 0.0 | ✅ identical |
| `max_tokens` | 96 | 96 | 96 | ✅ identical |
| `truncate_prompt_tokens` | 1800 | 1800 | 1800 | ✅ identical |
| generations/item (cross-domain / sycophancy / beneficial) | 3 / 3 / 1 | 3 / 3 / 1 | 3 / 3 / 1 | ✅ identical |
| chat template | `simple_llama_chat_template.jinja` | (Books-Qwen script not independently re-checked line-by-line, but shares the same script template as Books-Llama2, confirmed byte-identical to News script in the sections read) | `simple_llama_chat_template.jinja` | ✅ identical, confirmed for News and Books-Llama2 directly |
| `max_model_len` | 2048 | (not re-verified for Books-Qwen script specifically) | 2048 | Confirmed identical for News and Books-Llama2; Books-Qwen presumed same launcher template but not independently re-opened in this pass |
| effective `repetition_penalty` | **1.05** (model default, vLLM log) | **1.05** (model default, vLLM log) | **UNCERTAIN** (no log evidence either way) | Same for both Qwen runs; **different model family, unresolved for Llama-2** |
| effective `top_p`/`top_k` | 0.8 / 20 (moot, greedy decoding) | 0.8 / 20 (moot, greedy decoding) | UNCERTAIN (moot regardless, greedy decoding) | Same for both Qwen runs |

**Conclusion: the explicit, thesis-controlled generation parameters (temperature, max_tokens, prompt truncation, generation counts, chat template, model precision) are identical across MUSE-News and MUSE-Books.** The one confirmed difference is not a thesis choice but an artifact of which base model was used: Qwen2.5-7B-Instruct's own `generation_config.json` causes vLLM to apply `repetition_penalty=1.05` by default, while the Llama-2-7b track shows no evidence of an equivalent override. Whether the Llama-2 track's effective repetition penalty differed from 1.05 or from 1.0 cannot be established from repository evidence and should be marked **UNKNOWN**, not assumed either way.

## 5. Reproducibility consequences

1. **Can the original generations be reproduced exactly from current code?** **No.** `external/PersistBench/src/benchmark/utils.py` as it stands today would inject `STRICT_GENERATION_CONTROL` (forcing `repetition_penalty=1.08` via env-var default instead of letting the model's own 1.05 apply, injecting a "no JSON/code" system prompt that was never part of the original run, and re-deriving `max_tokens` through a different code path) — none of this existed on 2026-07-08/10/12. Running any `run_persistbench_muse_{news,books}_*.sh` script today, unmodified, would **not** reproduce the original text outputs.
2. **Can they be reproduced from historical scripts/configs?** **Partially, and only with additional reconstruction.** The launcher scripts themselves are unchanged and their `api_params` are confirmed accurate; the model checkpoints are frozen on disk. But no single preserved file captures `utils.py`'s exact state as of 2026-07-08 — it must be reconstructed by reverting the `STRICT_GENERATION_CONTROL` and `FORCE_VLLM_TRUNCATE_PROMPT_PATCH` blocks added on 2026-07-21 (both fully diffed and dated in `PERSISTBENCH_MODIFICATIONS.md` §4), which this and the prior audit have now done. Exact vLLM version at run time was not independently verified in this pass (would require checking `external/PersistBench/uv.lock`'s pinned version against whatever `pip freeze`/environment snapshot exists, if any, from that date — not attempted here as it is outside the requested scope).
3. **Which existing generation JSON files must be treated as canonical frozen artifacts?** `external/PersistBench/outputs/muse_news_qwen25_selected_full/*.json`, `external/PersistBench/outputs/muse_books_llama2_selected_full/*.json`, `external/PersistBench/outputs/muse_books_qwen25_selected_full/*.json`, and their PrivacyLens counterparts (`outputs/privacylens_muse_news_qwen25_selected/`, `outputs/privacylens_muse_books_{llama2,qwen25}_selected/`) — these contain the actual generated text and are valid regardless of the metadata-documentation error found in §3; nothing about the generated content itself is called into question here, only the *description* of how it was produced.
4. **Which generation parameters should be stated in the thesis Experimental Setup?** `temperature=0.0` (greedy/deterministic decoding), `max_tokens=96`, prompt truncated to the last 1800 tokens, `max_model_len=2048`, 3 generations per cross-domain/sycophancy item and 1 per beneficial-memory item, `bfloat16` precision, a shared plain-text chat template (`templates/simple_llama_chat_template.jinja`) applied uniformly across model families, served via vLLM's OpenAI-compatible API. For the Qwen-family runs specifically, it is accurate and confirmed to additionally state that the model's own default `repetition_penalty=1.05` (from its `generation_config.json`) was in effect, since it was neither overridden by the request nor by any code active at the time.
5. **Which parameters should NOT be claimed?** `repetition_penalty=1.08` (confirmed incorrect, §3); any specific `top_p`/`top_k` value for the Llama-2 MUSE-Books track (unconfirmed); any specific `seed` value (never set); any claim that a custom/strict system prompt was used during generation (it was not active at the time — §1).
6. **Which existing documentation files require correction?** `mechanistic/outputs/muse_books_weekly_update_analysis/README.md`'s repetition-penalty line, and — at a later, deliberate code-editing stage, not in this read-only pass — the hardcoded `"repetition_penalty": 1.08` / `"top_p": 1.0` / `"vllm_seed": 0` literals in `prepare_native_200.py` and `prepare_native_sycophancy_200.py`, ideally replaced with either the correct confirmed values (1.05 / 0.8 / "unset — greedy decoding, seed inconsequential") or removed/marked as non-authoritative documentation rather than measured provenance.

## 6. Does anything here block the repository migration?

**No.** This is a documentation-accuracy finding, not a discovery that any canonical result is invalid or was produced by materially different sampling behavior than believed for the parameters that matter (temperature, truncation, generation counts are all confirmed correct and identical to what was already assumed). The one wrong number (`repetition_penalty`) does not change which files are canonical, does not implicate a different track, and does not require regenerating anything — it requires a text correction to one README (and, later, to two source scripts), which can happen independently of and either before or after the planned file migration.
