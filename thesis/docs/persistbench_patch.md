# PersistBench patches (vendored tool, modified in place)

`external/PersistBench/` is a vendored external tool (its own git repository, `KEEP IN PLACE` — not reorganized by this migration). Four of its files are hand-patched relative to that repo's own tracked HEAD (`302ea2f`). Full diff analysis: `thesis_cleanup_audit/PERSISTBENCH_MODIFICATIONS.md`. Reference copies of the 6 `.bak_*`/`.before_*` pre-patch snapshots are kept at `thesis/docs/persistbench_patch_history/` for convenience; the originals remain, untouched, next to the live files inside `external/PersistBench/` (nothing under `external/PersistBench/` was moved).

## What changed, and why

| File | Change | Why | Still needed? |
|---|---|---|---|
| `src/benchmark/config.py` | `JUDGE_MODEL_OPENROUTER` → `"local-judge"` | Route judging to a locally-served model instead of the hosted OpenRouter Kimi-K2 endpoint | Yes — every PersistBench judgment in this repo uses it |
| `src/benchmark/providers/openrouter.py` | API key falls back to `OPENAI_API_KEY`/`"dummy"`; base URL overridable via `OPENAI_BASE_URL` | Plumbing that lets the local judge server be reached through the same code path | Not currently exercised by the MUSE-News/MUSE-Books pipeline (superseded by the `judgment.py` rewrite below); verify before removing in case another provider path still uses it |
| `src/benchmark/execution/judgment.py` | `_judge_via_openrouter` fully rewritten: direct client to the local server, vLLM `guided_json` schema enforcement, a self-repair LLM call if the local judge omits the `score` field | A local Qwen2.5-7B-Instruct judge is not reliable at emitting clean JSON via free-text parsing; this rewrite is a robustness fix | Yes — this is the only reason local-Qwen judging produces parseable scores at all |
| `src/benchmark/utils.py` | 3 incremental additions to `openai_compat_generate` (see below) | Generation-determinism controls | Partially — see caveat below |

## `utils.py`'s three layers (chronological)

1. **Local-judge max-tokens cap + json-force-on-localhost** (~2026-06-29). **Confirmed dead code**: `judgment.py`'s rewrite bypasses this function entirely for judging, and no generation script ever sets the `OPENAI_BASE_URL` env var this block checks for.
2. **`FORCE_VLLM_TRUNCATE_PROMPT_PATCH`** (~2026-07-05). **Confirmed dead/redundant**: immediately overwritten by layer 3's own `truncate_prompt_tokens` assignment.
3. **`STRICT_GENERATION_CONTROL`** (2026-07-21 22:19) — forces `temperature`/`top_p`/`max_tokens`/`truncate_prompt_tokens`/`repetition_penalty`, injects a "no JSON/code" system prompt. **This is genuinely active for any generation run today, but it postdates every canonical MUSE-News/MUSE-Books generation (2026-07-08/10/12) by 9–13 days** — see `thesis/docs/generation_provenance.md` for the confirmed actual settings used at generation time, and the correction to a documentation claim this discrepancy exposed.

## Reproducibility note

Because layers 1–2 are dead code and layer 3 postdates the canonical generations, **re-running any `thesis/scripts/persistbench/*.sh` launcher today would not reproduce the original generation parameters exactly** (it would pick up layer 3's `repetition_penalty=1.08` default instead of the historically-confirmed effective `1.05`, and would inject a system prompt that wasn't present originally). The existing frozen generation JSON/JSONL files remain the authoritative record; see `thesis/manifests/provenance/persistbench_generation_corrections.json`.

## Status of these files

None of `external/PersistBench/`'s files were touched by this migration — this document only explains what was already there. Extracting the `judgment.py` rewrite into a separately-named `local_judge.py` module, and removing the two confirmed-dead `utils.py` blocks, are recommended future steps (see `thesis_cleanup_audit/METHODOLOGY_PRESERVATION_PLAN.md`), not performed in this pass.
