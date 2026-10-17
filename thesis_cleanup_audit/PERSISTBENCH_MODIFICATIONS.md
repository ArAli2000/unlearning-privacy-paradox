# PersistBench modifications (`external/PersistBench/`)

Read-only analysis. No file under `external/PersistBench/` was modified. `external/PersistBench/` is itself a git repository (`git status` inside it shows the working tree against its own `HEAD`, commit `302ea2f "Link to Inspect-native implementation in README"`), so every diff below is `git diff HEAD -- <file>` run inside that nested repo — a precise, unambiguous before/after, not a guess from `.bak` filenames.

## 0. Scope confirmed

`git diff --stat HEAD` inside `external/PersistBench` shows **exactly 4 modified files**, nothing more:

```
src/benchmark/config.py               |   2 +-
src/benchmark/execution/judgment.py   | 167 +++++++++++++++++++++++++++-------
src/benchmark/providers/openrouter.py |   4 +-
src/benchmark/utils.py                | 38 ++++++++
```

No file under `analysis/` (including `analysis/failure_rates.py`, the official category-specific FR@K implementation) was touched — the FR@K metric logic itself is confirmed **upstream/canonical, unmodified**. The thesis-added `configs_local/`, `outputs/`, `logs/`, `templates/` directories are new, untracked additions (usage of the tool), not modifications to its code.

## 1. `src/benchmark/config.py` — judge routing target

```diff
-JUDGE_MODEL_OPENROUTER = "moonshotai/kimi-k2-thinking"  # OpenRouter model name
+JUDGE_MODEL_OPENROUTER = "local-judge"  # Local vLLM judge model name
```

- **Upstream behavior**: judge calls routed through OpenRouter go to the hosted `moonshotai/kimi-k2-thinking` model.
- **Thesis modification**: redirect the model name to a locally-served model (`local-judge`, served by `run_local_judge_server_penelope.sh` as `Qwen/Qwen2.5-7B-Instruct`).
- **Reason**: avoid dependency on/cost of the hosted OpenRouter Kimi-K2 judge; run judging locally on the cluster instead.
- **Experiments depending on it**: every PersistBench judgment run in this repo that uses `JUDGE_PROVIDER=openrouter` (confirmed: `run_persistbench_muse_news_qwen25_judge_like_tofu.sh` exports `JUDGE_PROVIDER=openrouter`) — i.e. **all** MUSE-News and MUSE-Books PersistBench judgments, and also the out-of-scope TOFU/WMDP PersistBench judgments.
- **Still needed?** Yes, as long as any PersistBench judging is done locally rather than via the hosted Kimi-K2 API.
- **Should it remain a patch, wrapper, config, or be removed?** This one line is the cleanest possible case for a **config option** rather than a source edit — see `METHODOLOGY_PRESERVATION_PLAN.md`.

## 2. `src/benchmark/providers/openrouter.py` — endpoint/key override

```diff
-    api_key = os.getenv("OPENROUTER_API_KEY")
+    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or "dummy"
     ...
     async with AsyncOpenAI(
-        base_url="https://openrouter.ai/api/v1",
+        base_url=os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
```

- **Upstream behavior**: hard-codes OpenRouter's hosted base URL and requires `OPENROUTER_API_KEY` to be set (raises `FatalBenchmarkError` if absent).
- **Thesis modification**: makes the base URL overridable via `OPENAI_BASE_URL`, and makes the API key resolution fall through to `OPENAI_API_KEY` or a `"dummy"` placeholder — necessary because a local vLLM OpenAI-compatible server doesn't require a real key.
- **Reason**: this is the plumbing that makes `JUDGE_MODEL_OPENROUTER = "local-judge"` (change 1) actually reach a local server instead of `openrouter.ai`.
- **Experiments depending on it**: same set as change 1 — but note that this function, `openrouter_generate_response`, is **no longer called by the judge path at all** after change 3 (`_judge_via_openrouter` was rewritten to use its own direct `AsyncOpenAI` client — see §3). It is still used for *generation* calls that go through the `"openrouter"` provider (as opposed to the `"openai_compatible"` provider that MUSE-News/Books generation actually uses — see §4's boundary note). **Verified**: none of `run_persistbench_muse_{news,books}_*` scripts set `provider: "openrouter"` for generation (they all use `provider: "openai_compatible"`), so **this file's changes currently affect only judge-routing plumbing that is itself superseded, and are not exercised by the current MUSE-News/MUSE-Books pipeline at all** — see the dead-code finding in §4.
- **Still needed?** Only if something still calls `openrouter_generate_response` (e.g. an out-of-scope TOFU/WMDP script using `provider: "openrouter"` for judging — not verified in this pass, would need a targeted grep across all launcher `provider` fields if this needs a definitive answer before removal). For MUSE-News/MUSE-Books specifically: **not exercised**, since judging goes through the rewritten `_judge_via_openrouter` in `judgment.py` (§3) which bypasses this file entirely.

## 3. `src/benchmark/execution/judgment.py` — schema-forced local-judge rewrite (the largest change, 167 lines)

- **Upstream behavior**: `_judge_via_openrouter` called the generic `openrouter_generate_response` helper and parsed whatever free-form text came back with `_parse_judge_content`.
- **Thesis modification**: `_judge_via_openrouter` is **entirely rewritten** to make its own direct `AsyncOpenAI` client call against `os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8001/v1")`, with:
  - An explicit JSON schema (`{"score": int, "reasoning": str}`) passed as vLLM's `guided_json` extra_body, with a fallback retry without `extra_body` if the client/server combination rejects it (`except TypeError`).
  - A strict instruction block appended to the system prompt demanding compact JSON with no markdown/extra fields.
  - Manual JSON parsing with a regex fallback (`re.search(r"\{.*\}", content, flags=re.S)`) if `json.loads` fails outright.
  - A **repair pass**: if the parsed JSON is missing the `score` field, it makes a *second* LLM call asking the same local model to convert its own malformed output into the correct schema, given the original judge prompt + the malformed response as context.
  - A hard fallback (`score=0`, a fixed reasoning string) if even the repair call fails to produce a `score`.
  - `judge_response()` is reduced to a one-line "compatibility wrapper" that always calls `_judge_via_openrouter` — the `provider == "vertexai"` branch and the "unknown provider" error path from upstream are **no longer reachable through this wrapper** (though `_judge_via_vertexai` itself is untouched and still exists in the file).
- **Reason**: a local Qwen2.5-7B-Instruct judge (unlike the hosted Kimi-K2 model) is not reliable at emitting clean, schema-conformant JSON on the first try under upstream's original free-text parsing — this rewrite is a robustness/reliability fix specifically for using a smaller local model as judge.
- **Experiments depending on it**: every MUSE-News and MUSE-Books PersistBench judgment (both tracks), confirmed via `run_local_judge_server_penelope.sh` + `run_persistbench_*_judge*.sh` scripts, which all rely on the local judge being parseable.
- **Still needed?** Yes, as long as a local Qwen judge (rather than the canonical hosted Kimi-K2) is used for any PersistBench judging — which is the case for **100% of the MUSE-News/MUSE-Books PersistBench judgments that exist in this repo today** (see §6 and `MUSE_NEWS_TRACK_RESOLUTION.md` §4: no MUSE-News or MUSE-Books result was ever judged by the canonical judge).
- **Should it remain a patch, wrapper, config, or be removed?** This is genuinely custom logic (schema enforcement + a self-repair LLM call), not just a config toggle — it should become an explicit, named, documented module (e.g. `local_judge.py`), not stay as an unlabeled rewrite of an upstream function with the same name. See `METHODOLOGY_PRESERVATION_PLAN.md`.
- **`judge_response provider == "vertexai"` reachability**: not obsolete/removable in general (Vertex AI judging may still be used elsewhere), but note for the grader that **the wrapper as currently written silently ignores `get_judge_provider()` and always uses the local-judge path** — this is a behavior change beyond "add a new option," worth a one-line comment at minimum.

## 4. `src/benchmark/utils.py` — generation-determinism controls, applied incrementally in (at least) 3 steps

This file received the messiest patch history of the four — three `.bak_*`/`.before_*` snapshots capture three different intermediate states, reconstructed via `diff`/`stat` below:

| Step | Snapshot file | mtime | What it added |
|---|---|---|---|
| 0 | (upstream `HEAD`) | — | — |
| 1 | `utils.py.bak_before_vllm_truncation` ≡ `utils.py.bak_schema_judge` (byte-identical) | 2026-06-29 / 2026-07-05 | `max_tokens` capped to 256 "for local vLLM judge" **+** force `temperature=0` and `response_format={"type":"json_object"}` whenever `OPENAI_BASE_URL` starts with `http://127.0.0.1` |
| 2 | `utils.py.before_strict_generation_patch` | 2026-07-21 22:19:16 (same mtime as current file) | Step 1 **+** `FORCE_VLLM_TRUNCATE_PROMPT_PATCH`: unconditionally sets `extra_body.truncate_prompt_tokens = 1800` |
| 3 (current) | `utils.py` | 2026-07-21 22:19:16 | Step 2 **+** `STRICT_GENERATION_CONTROL` block: forces `temperature`, `top_p`, re-caps `max_tokens`, re-sets `truncate_prompt_tokens` (again — see finding below), sets `repetition_penalty`, and **prepends a "strict system prompt"** instructing the model not to output code/JSON/navigation-menu text/repeated tokens, all overridable via `PB_TEMPERATURE`/`PB_TOP_P`/`PB_MAX_TOKENS`/`PB_TRUNCATE_PROMPT_TOKENS`/`PB_REPETITION_PENALTY`/`PB_STRICT_SYSTEM_PROMPT` env vars |

### 4a. Confirmed dead code (safe to remove, does not affect any current result)

`_judge_via_openrouter` was rewritten in `judgment.py` (§3) to use its own direct client, bypassing `openrouter_generate_response` → `openai_compat_generate` entirely. Independently, no MUSE-News/MUSE-Books **generation** script ever exports the `OPENAI_BASE_URL` env var (only the judge launcher does, and only for judging) — confirmed by grepping every `run_persistbench_muse_*` script. Therefore:

```python
if "max_tokens" not in params or params.get("max_tokens", 0) > 256:
    params["max_tokens"] = 256
if os.getenv("OPENAI_BASE_URL", "").startswith("http://127.0.0.1"):
    params["temperature"] = 0
    params["response_format"] = {"type": "json_object"}
```

is **never triggered by anything currently in this repo**: not by judging (bypassed) and not by generation (the env var it checks is never set at generation time). It is vestigial from before `judgment.py` was rewritten to stop calling this shared path for judging. **Safe to remove** — removing it changes no result.

Similarly, the `FORCE_VLLM_TRUNCATE_PROMPT_PATCH` two-liner (step 2) is **immediately and unconditionally overwritten** by the `STRICT_GENERATION_CONTROL` block's own `extra_body["truncate_prompt_tokens"] = ...` line eight lines later in the same function, using the same default (1800). It is dead, redundant code — harmless, but pure clutter from an earlier iteration that was never cleaned up after being superseded.

### 4b. Confirmed load-bearing: the `STRICT_GENERATION_CONTROL` block is what actually reaches MUSE-News/MUSE-Books generation

`openai_compatible.py` (the provider used by every `run_persistbench_muse_*` script — confirmed via `"provider": "openai_compatible"` in each launcher's embedded JSON config) calls `openai_compat_generate` from `utils.py` directly. This file is **not** in the modified-files list, so the call path itself is upstream; the patched function it calls is where the determinism controls live. This confirms the `STRICT_GENERATION_CONTROL` block genuinely executes on every MUSE-News/MUSE-Books generation call.

### 4c. ⚠ Important timeline finding: `repetition_penalty` and the strict system prompt were added *after* every canonical MUSE-News/MUSE-Books generation run had already completed

This needs the author's attention, not just cleanup:

| Generation output | mtime (on disk) |
|---|---|
| `external/PersistBench/outputs/muse_news_qwen25_selected_full/*.json` (Track B, canonical) | 2026-07-08 |
| `external/PersistBench/outputs/muse_books_llama2_selected_full/*.json` | 2026-07-10/11 |
| `external/PersistBench/outputs/muse_books_qwen25_selected_full/*.json` | 2026-07-12 |
| `utils.py`'s `STRICT_GENERATION_CONTROL` block (adds `repetition_penalty`, the strict system prompt, and `top_p` forcing) | **added 2026-07-21 22:19** |

None of the launcher scripts' own embedded `api_params` set `repetition_penalty` (confirmed by grep — they only set `temperature`, `max_tokens`, `extra_body.truncate_prompt_tokens`), and the `vllm serve` invocations in these scripts pass no generation-config flag that would set it either. **This means `repetition_penalty=1.08` was not active during any of the generation runs that produced the actual final MUSE-News/MUSE-Books PersistBench results — it was added to the code 9–13 days after those generations already ran.** The strict system prompt (telling the model not to emit JSON/navigation text/repeated tokens) was similarly not active during those runs.

This directly affects a specific claim already written into the repository's own documentation: `mechanistic/outputs/muse_books_weekly_update_analysis/README.md` states under "Provenance and artifact map": *"Generation source: `external/PersistBench/outputs/muse_books_qwen25_selected_full/*.json`; temperature 0, max 96 tokens, **repetition penalty 1.08**, left truncation to 1,800 tokens, vLLM seed 0."* Based on the evidence above, **this specific line appears to describe the current code's defaults rather than what was actually configured when that generation ran on 2026-07-12** — the temperature/max-tokens/truncation values are corroborated (they were set explicitly in the launcher script's own `api_params`, which predates and is independent of the `utils.py` patch), but the repetition-penalty figure is not corroborated by anything that existed in the code before 2026-07-21. **This should be verified by the author before the thesis text repeats it** — either by finding another mechanism that set it (not found in this pass), or by correcting the documentation to state that repetition penalty was not explicitly controlled for these specific generation runs.

## 5. The "substring-classifier" concern — found, but it lives outside `external/PersistBench/`

`external/PersistBench/`'s own code has **no validator/classifier logic modified or added** (confirmed — the 4 changed files are config/judge-routing/generation-params only; `analysis/failure_rates.py`, the official FR@K implementation, is untouched upstream code). The classifier the audit's earlier reconciliation work refers to (`mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_persistbench_metric_reconciliation.md`, "a custom post-hoc all-category response classifier") is `tmp_paths/create_persistbench_validity_summary_with_muse.py` — a **thesis-authored downstream script**, not part of the vendored tool, that reads PersistBench's judged JSON output and reclassifies each response with its own keyword/substring heuristics. Read directly (`classify()`, lines 156–213):

```python
web_terms = ["skip to content", "github", "toggle navigation", ...]
if any(t in low for t in web_terms): return "web_or_page_contamination"
...
if score is not None and score >= 4 and not negated:
    if any(t in jt for t in ["personal detail", "private", "sensitive", "gender", "age", "religion", "belief"]):
        return "personal_detail_injection"
```

This is a **plain Python `in` substring check**, not a word-boundary regex — e.g. the token `"age"` matches as a substring inside unrelated words like *average*, *manage*, *damage*, *package*, *storage* wherever they appear in the judge's reasoning text (`jt`). Combined with the `score >= 4 and not negated` gate this is reasonably guarded, but it is a genuine false-positive risk exactly as the audit's earlier reconciliation flagged: **this classifier's output (the "3.85% → 4.92%" custom privacy-context percentage) is already marked, in the thesis's own reconciliation document, as "not comparable" to the current official FR@K numbers and should not be cited as the primary PersistBench result.** This is not a modification to `external/PersistBench/`, but it directly consumes and reinterprets PersistBench's judge output, so it is reported here for completeness per the task's explicit instruction to check "the previously discovered substring-classifier bug." **Recommendation, if this script is kept for any purpose**: replace bare substring checks with word-boundary regex (`re.search(rf"\b{re.escape(t)}\b", jt)`) to reduce false positives, and keep the reconciliation document's existing "not comparable, do not call this PersistBench failure rate" caveat prominently attached wherever this script's output is cited.

## 6. Local Qwen judge vs. canonical Kimi-K2 — status confirmed across the whole repo

Every judge-model string actually present in the generated JSON output metadata (`metadata.judge_model = "local-judge"`, confirmed by direct read of `external/PersistBench/outputs/muse_news_qwen25_selected_full/*.json` and by `muse_news_persistbench_metric_reconciliation.md`'s own audit) traces to `Qwen/Qwen2.5-7B-Instruct` served locally, for **every MUSE-News and MUSE-Books PersistBench result in this repository**, both tracks. A `grep` for Kimi/Moonshot judge usage anywhere in outputs, configs, or logs (already performed in the reconciliation document referenced above) found none. **No MUSE-News or MUSE-Books PersistBench number in this repository was ever produced with the canonical judge** — this is not new information (the reconciliation doc already says so), but it is restated here because it directly explains *why* changes 1–3 above exist at all: they are the entire mechanism that makes local-Qwen judging possible and (relatively) reliable.

## 7. Summary table

| File | Modification | Still needed for final thesis reproducibility? | Recommended form |
|---|---|---|---|
| `config.py` | Judge model name → `local-judge` | Yes | Config option |
| `providers/openrouter.py` | API key/base-URL fallback for local server | Not currently exercised by the MUSE-News/MUSE-Books pipeline (bypassed by judgment.py's rewrite); may still matter for other, out-of-scope judge/generation paths — verify before removing | Config option if still used anywhere; otherwise archive |
| `execution/judgment.py` | Full schema-forced local-judge rewrite + self-repair | Yes — this is the only reason local-Qwen judging produces parseable scores at all | Named, documented module (e.g. `local_judge.py`) |
| `utils.py` (step 1: max_tokens cap + json-force-on-localhost) | — | **No — confirmed dead code**, superseded by judgment.py's rewrite | Remove |
| `utils.py` (step 2: `FORCE_VLLM_TRUNCATE_PROMPT_PATCH`) | — | **No — confirmed dead/redundant**, immediately overwritten by step 3 | Remove |
| `utils.py` (step 3: `STRICT_GENERATION_CONTROL`) | Forces temperature/top_p/max_tokens/truncation/repetition_penalty + injects a system prompt | Partially — active for any *future* rerun, but **not active during the actual final generation runs** (repetition_penalty/system-prompt/top_p postdate them by 9–13 days, §4c) | Config option (env-var-driven already); the doc claim in `muse_books_weekly_update_analysis/README.md` needs author verification/correction |
