# Gemma-3 judge prompt-length check (category-aware, corrected)

Corrects the earlier Gemma-2 scans (`/tmp/measure_prompt_lens.py`, `/tmp/measure_prompt_lens_gemma3_v2.py`), which paired every generation with all three judge rubrics. This measurement instead pairs each real generation with only its own actual PersistBench category's rubric -- exactly what `gemma_judge.py` sends.

Model: `google/gemma-3-12b-it` at `/storage/ukp/shared/shared_model_weights/models--google--gemma-3-12b-it`
Model native context length: 131072
Configured judge max output tokens: 256
Planned Gemma-3 `--max-model-len`: 16384

## Per-category statistics

| Category | Requests | Min | Median | P95 | P99 | Max | Required ctx (max+output) | >8192 tok | >planned-output |
|---|---|---|---|---|---|---|---|---|---|
| cross_domain | 9000 | 8866 | 9054.0 | 9168.0 | 9240.0 | 9249 | 9505 | 9000 (100.00%) | 0 (0.00%) |
| sycophancy | 9000 | 8776 | 8903.0 | 9028.0 | 9063.0 | 9104 | 9360 | 9000 (100.00%) | 0 (0.00%) |
| beneficial_memory_usage | 1500 | 2285 | 2412.0 | 2526.0 | 2562.4 | 2627 | 2883 | 0 (0.00%) | 0 (0.00%) |

## Maximum example per category

- **cross_domain**: 9249 tokens -- `external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_satimp.json`, entry `007bed460ddc8586ddb88c33c3ca0c8d`, model `muse_news_qwen25_satimp`, generation index 0
- **sycophancy**: 9104 tokens -- `external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_wga.json`, entry `8789f945d3fe37bde47041f00005ff22`, model `muse_books_qwen25_wga`, generation index 0
- **beneficial_memory_usage**: 2627 tokens -- `external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_rmu.json`, entry `09e2279cac99a727096b0290e7f203bf`, model `muse_news_qwen25_rmu`, generation index 0

## Overall

- Total real judgment requests (all categories): 19500
- Overall max input tokens: 9249
  - Producing example: category `cross_domain`, `external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_satimp.json`, entry `007bed460ddc8586ddb88c33c3ca0c8d`, model `muse_news_qwen25_satimp`, generation index 0
- Required total context for overall max (input + 256 output): 9505
- Count/percentage exceeding 8192 input tokens (Gemma-2's ceiling, for reference): 18000 (92.31%)
- Fits without truncation at planned `--max-model-len` (16384), with output headroom: **True**

## Chat-template check (system-role support)

Inspected directly (not assumed from the Gemma-2 precedent):
`/storage/ukp/shared/shared_model_weights/models--google--gemma-3-12b-it/chat_template.json`'s
Jinja template.

Finding: the template explicitly checks `messages[0]['role'] == 'system'`, and
when true, folds that message's content into a `first_user_prefix` variable
(`content + '\n\n'`) that is prepended to the first `user` turn's own content
inside a single `<start_of_turn>user ... <end_of_turn>` block. There is no
separate `<start_of_turn>system` block anywhere in the template output --
unlike Gemma-2 (which rejected a `system`-role message outright with HTTP 400
"System role not supported"), Gemma-3's template *accepts* a leading
system-role message, but still renders it as part of the first user turn's
text, not as a structurally distinct turn.

Consequence: sending `{"role": "system", ...}` + `{"role": "user", ...}` and
manually concatenating the same text into one `{"role": "user", ...}` message
(the approach `gemma_judge.py` already uses, carried over from the Gemma-2
implementation) produce token-for-token equivalent rendered output -- the
native path prepends `system_content + "\n\n"` before the (whitespace-trimmed)
user content; the manual-concatenation path joins the same two strings with
`"\n\n"` directly. Since the outcome is identical and the manual-concatenation
approach was already validated end-to-end for Gemma-2, `gemma_judge.py` was
NOT changed to use a native system-role message -- this is confirmed to be a
no-op choice, not an untested assumption. This token-count script reproduces
`gemma_judge.py`'s exact manual-concatenation construction, so the measured
token counts above are what the real judging code actually sends.
