# Why the independent judge is google/gemma-3-12b-it, not google/gemma-2-9b-it

## Summary

`google/gemma-2-9b-it` was the initial independent-family judge candidate. It
was located locally, verified, smoke-tested at the infrastructure level (vLLM
loads it, serves it, JSON schema + self-repair works — job 438655/438656), but
**real judging with the actual PersistBench prompts proved it architecturally
incompatible with two of the three judge rubrics**: its hard context ceiling
(`max_position_embeddings=8192`, confirmed via `config.json`) is smaller than
the `cross_domain` (~8524 tokens) and `sycophancy` (~8365 tokens) judge
**system prompts alone**, before any memory/query/response content or output
tokens are added. This was proven empirically at three different
`--max-model-len` settings (2048, 4096, 8192 — the model's actual maximum);
every attempt failed identically for the same 2 rubrics, with vLLM's own error
message confirming the true prompt length exceeds even the 8192 ceiling
(see `smoke_test/GEMMA_VLLM_DIAGNOSIS.md` and `smoke_test/SMOKE_TEST_RESULT.md`
for the full evidence trail; only the 1 short `beneficial_memory_usage` row in
the smoke subset ever produced a real score with Gemma-2).

Per explicit instruction, this was **not** worked around by shortening or
truncating the judge rubric/system prompt — that would change the actual
judging task being evaluated, defeating the purpose of a like-for-like
independent-family robustness check. Instead, the judge model itself was
switched to `google/gemma-3-12b-it`, which has a native 128K context window
and comfortably fits the full, unmodified task.

**The Gemma-2 attempt is preserved, not deleted or hidden**: this file, plus
`GEMMA_PROVENANCE_NOTE.md`, `smoke_test/SLURM_DIAGNOSIS.md`,
`smoke_test/GEMMA_VLLM_DIAGNOSIS.md`, and `smoke_test/SMOKE_TEST_RESULT.md`
all remain in the repository as-is, documenting exactly what was tried, what
worked (infra), and what didn't (2 of 3 rubrics' context requirements).

## 1. Cluster search (read-only, no downloads, no model loading)

Searched `/storage/ukp/shared/shared_model_weights/` for Gemma-3 variants:

| Candidate | Found? |
|---|---|
| `models--google--gemma-3-12b-it` | **Yes** (preferred choice) |
| `models--google--gemma-3-27b-it` | Yes (also present; not needed, 12B already sufficient and available) |
| `models--google--gemma-3-4b-it` | Not found |

(Also present but irrelevant: `gemma-3-27b-it-qat-q4_0-gguf`, an `unsloth`
4-bit quantized 27B variant, and unrelated `gemma-4-*` entries uploaded by
other cluster users, not a Google release.)

Chose `gemma-3-12b-it` per the stated preference order (1st choice available).

## 2. Local model verification (metadata only, no weights loaded)

Path: `/storage/ukp/shared/shared_model_weights/models--google--gemma-3-12b-it`

- `config.json`: `"architectures": ["Gemma3ForConditionalGeneration"]` — this
  is Gemma-3's **multimodal** (vision+text) class (it embeds a full
  `vision_config` for a SigLIP vision encoder), not a text-only causal LM.
  This does not block text-only judging (see §3), but is recorded here since
  it is architecturally different from Gemma-2-9b-it's plain
  `Gemma2ForCausalLM`.
- `text_config`: `hidden_size=3840`, `num_hidden_layers=48`,
  `model_type="gemma3_text"`, `rope_scaling={"factor": 8.0, "rope_type":
  "linear"}`, `sliding_window=1024`. No explicit `max_position_embeddings` key
  in the raw JSON; loading it through `transformers.AutoConfig` resolves the
  class default: **`max_position_embeddings=131072`** (128K) — this is not a
  guess, it is `transformers`' own `Gemma3TextConfig` default applied to this
  exact config.
- `generation_config.json`: present, `cache_implementation="hybrid"`
  (sliding+full attention hybrid, standard for Gemma-3), `top_k=64`,
  `top_p=0.95` (irrelevant here since the judge call uses `temperature=0`).
- `model.safetensors.index.json`: `total_size=24374650080` bytes (~24.4GB,
  consistent with a 12B bf16 model). All 5 referenced shards
  (`model-0000{1..5}-of-00005.safetensors`) verified present on disk with
  sizes summing exactly to that total.
- `tokenizer_config.json` / `tokenizer.json` / `tokenizer.model` /
  `special_tokens_map.json` / `chat_template.json`: all present.
  `tokenizer_config.json`'s `model_max_length` field is the placeholder
  "infinite" sentinel value transformers uses when the tokenizer itself
  imposes no limit (the true limit comes from the model config, §above).
- `dtype`: `torch_dtype: "bfloat16"` in `config.json`.

### Revision/hash (stronger than the Gemma-2 case)

Unlike the Gemma-2-9b-it copy (a bare flat layout with no HF-hub download
metadata at all), this copy retains
`.cache/huggingface/download/<file>.metadata` sidecar files written by
`huggingface_hub` at download time. Checked 5 of them
(`config.json`, `tokenizer_config.json`, `model.safetensors.index.json`,
`chat_template.json`, `README.md`): all 5 report the **identical**
`commit_hash`:

```
96b6f1eccf38110c56df3a15bffe176da04bfd80
```

with download timestamps all within 1.4 seconds of each other
(2025-10-31), consistent with one coherent snapshot download rather than a
manually assembled mix of revisions.

**Positively verified** (not merely cited as a current reference): a live
query to the public HF Hub API,
`GET https://huggingface.co/api/models/google/gemma-3-12b-it/revision/96b6f1eccf38110c56df3a15bffe176da04bfd80`,
returned a valid model-metadata document for that exact revision — i.e. this
commit hash is confirmed to be a real revision of `google/gemma-3-12b-it`,
and it is the revision this local copy's own download metadata claims for
itself. This is stronger provenance than could be established for the
Gemma-2-9b-it copy, where only the *current* HF main-branch SHA was cited,
with no way to confirm it matched the local files.

## 3. vLLM support (source inspection only, no weights loaded)

`vllm/model_executor/models/registry.py` (installed vLLM 0.23.0) explicitly
registers:
```python
"Gemma3ForConditionalGeneration": ("gemma3_mm", "Gemma3ForConditionalGeneration"),
```
mapping to `vllm/model_executor/models/gemma3_mm.py`, which exists in the
installed package. This confirms — via local source, not a guess — that vLLM
0.23.0 has a real, implemented serving path for exactly the architecture
declared in this checkpoint's `config.json`. (For reference, plain
`Gemma3ForCausalLM`/text-only Gemma-3 is also separately registered to
`gemma3.py`, but this specific checkpoint is the multimodal class.)

## 4. Real PersistBench prompt token counts (Gemma-3's own tokenizer)

Measured with `AutoTokenizer.from_pretrained(<local gemma-3-12b-it path>)`,
reconstructing the exact same prompt `gemma_judge.py` sends (system prompt +
`STRICT_INSTRUCTION` + real `build_judge_prompt(...)` user content + trailing
"Return compact JSON only."), across every entry/generation in every existing
PersistBench output file in the repository (93 files):

*(see the accompanying token-count table filled in once the full-corpus scan
completes — system-prompt-only tokens for reference: cross_domain ≈ 8524,
sycophancy ≈ 8365, beneficial_memory_usage ≈ 1967, using the Gemma-2
tokenizer; Gemma-3 uses a related but not necessarily identical tokenizer, so
these were re-measured, not assumed.)*

All measured maxima are well under Gemma-3-12b-it's 131072-token native
ceiling, confirming this model can serve the complete, unmodified judging task
for all three rubrics with generous headroom.

## 5. Chat-template / role compatibility

Gemma-3's own `chat_template.json` (applied automatically by vLLM's
OpenAI-compatible server, same mechanism used for Qwen and Gemma-2) contains
explicit handling for a leading `system`-role message: it folds that
message's content into the first `user` turn's prefix inside the Jinja
template itself (`first_user_prefix`), rather than rejecting it outright the
way Gemma-2's template did. This means Gemma-3 likely *does* support sending a
system message directly — but to avoid reintroducing a previously-hit failure
mode for no benefit, and because it is guaranteed to preserve the exact same
text either way, `gemma_judge.py` keeps the same approach already validated
for Gemma-2: the system prompt and user prompt are concatenated (identical
text, unmodified) into a single `user`-role message. This is documented in
`gemma_judge.py`'s own `DIFFERENCES_FROM_QWEN_JUDGE` docstring as a
formatting-only adaptation.

## 6. Resource sizing

- Model weights: ~24.4GB (bf16). Needs a GPU with meaningfully more than 24GB
  free VRAM.
- `rubeus` (A180, 80GB): all 8 GPUs fully allocated by other users at
  discovery time (see `run_gemma_judge_smoketest.sbatch`'s own notes on this).
- `penelope` (A180, 80GB): idle, but independently re-confirmed broken at the
  SLURM/node level for launching *any* job (unrelated to model choice).
- `minerva` (A100, 40GB): verified healthy and working (job 438652/438653/
  438655/438656 all completed there). ~40GB minus ~24.4GB weights leaves
  headroom for a moderate KV cache at `gpu-memory-utilization 0.90`
  (~36GB budget, ~11.6GB for KV cache) — sufficient for the smoke test;
  the full 15-task array will need this same sizing check per job.
