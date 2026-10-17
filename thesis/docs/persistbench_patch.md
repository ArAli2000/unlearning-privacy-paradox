# PersistBench patch

`external/PersistBench` is an external repository (submodule, pinned to commit `302ea2f`). Four of its files were modified for the thesis. The modifications are in `thesis/patches/persistbench.patch`; apply them with

```bash
git -C external/PersistBench apply ../../thesis/patches/persistbench.patch
```

(or let `thesis/scripts/setup_external_dependencies.sh` do it). Pre-patch snapshots of the modified files are in `thesis_archive.zip` under `thesis/docs/persistbench_patch_history/`.

## Modified files

| File | Change | Reason | Current use |
|---|---|---|---|
| `src/benchmark/config.py` | `JUDGE_MODEL_OPENROUTER` set to `"local-judge"` | Route judging to a locally served model instead of the hosted Kimi-K2 endpoint | Used by every PersistBench judgment in the thesis |
| `src/benchmark/providers/openrouter.py` | API key falls back to `OPENAI_API_KEY` or `"dummy"`; base URL overridable with `OPENAI_BASE_URL` | Lets the local judge server be reached through the same code path | Not exercised by the MUSE pipeline, since the `judgment.py` rewrite below bypasses it |
| `src/benchmark/execution/judgment.py` | `_judge_via_openrouter` rewritten: direct client to the local server, vLLM `guided_json` schema enforcement, a repair call if the judge omits `score` | The local Qwen2.5-7B-Instruct judge does not reliably emit clean JSON through free-text parsing | Required for local judging to produce parseable scores |
| `src/benchmark/utils.py` | Three additions to `openai_compat_generate` (below) | Generation controls | Only the third is active |

## The three changes in `utils.py`

1. Local-judge max-tokens cap and forced JSON on localhost (about 2026-06-29). Dead code: the rewritten `judgment.py` does not call this function for judging, and no generation script sets the `OPENAI_BASE_URL` variable the block checks.
2. `FORCE_VLLM_TRUNCATE_PROMPT_PATCH` (about 2026-07-05). Redundant: it is overwritten by the next block's own `truncate_prompt_tokens` assignment.
3. `STRICT_GENERATION_CONTROL` (2026-07-21). Forces `temperature`, `top_p`, `max_tokens`, `truncate_prompt_tokens` and `repetition_penalty`, and injects a "no JSON/code" system prompt. It is active for any generation run with the patched code, but it was added 9 to 13 days after all canonical MUSE generations (2026-07-08, 07-10, 07-12).

## Consequence for reproduction

Running a `thesis/scripts/persistbench/*.sh` generation launcher with the patched code applies block 3 and therefore does not reproduce the original generation parameters: `repetition_penalty` defaults to 1.08 instead of the effective 1.05, and a system prompt is injected that was not present originally. The frozen generation files are the reference. The settings actually used are in `generation_provenance.md`, and the metadata corrections are in `thesis/manifests/provenance/persistbench_generation_corrections.json`.
