# Generation provenance: PersistBench settings for MUSE-News and MUSE-Books

Values below come from (1) metadata in the frozen PersistBench output JSON files, (2) the vLLM server logs of the generation jobs, (3) the launcher scripts, and (4) file modification times showing which code existed at run time.

## 1. Runs

| Run | Launcher | SLURM array job | Date |
|---|---|---|---|
| MUSE-News, Qwen2.5-7B-Instruct: BASE, RMU, WGA, SimNPO, SatImp | `thesis/scripts/persistbench/run_persistbench_muse_news_qwen25_selected.sh` | 408558 (tasks 0-4) | 2026-07-08 |
| MUSE-Books, Llama-2-7b (official target): same five conditions | `thesis/scripts/persistbench/run_persistbench_muse_books_llama2_selected.sh` | 408885 | 2026-07-10 |
| MUSE-Books, Qwen2.5-7B-Instruct (locally fine-tuned): same five conditions | `thesis/scripts/persistbench/run_persistbench_muse_books_qwen25_selected.sh` | 409517 | 2026-07-12 |

The earlier MUSE-News run on the official Llama-2 target is not used in the thesis.

## 2. Settings common to all three runs

Source: `config.models[0].api_params` in the output files (for example `external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_before.json`) and the `vllm serve` lines of the launchers.

| Setting | Value | Source |
|---|---|---|
| `temperature` | 0.0 | `api_params`, all three runs |
| `max_tokens` | 96 | `api_params` |
| `truncate_prompt_tokens` | 1800 | `api_params.extra_body` |
| Truncation side | left (earliest tokens dropped) | vLLM behavior for this parameter |
| Generations per item | 3 for `cross_domain` (200 items), 3 for `sycophancy` (200 items), 1 for `beneficial_memory_usage` (100 items); 1,300 per model | counted from the output files |
| Chat template | `templates/simple_llama_chat_template.jinja`, also for the Qwen runs | `--chat-template` flag in the launchers |
| Serving | vLLM OpenAI-compatible server, `--dtype bfloat16`, `--gpu-memory-utilization 0.90`, `--max-model-len 2048` | `vllm serve` line |
| Provider | `openai_compatible` | output metadata |
| Thesis-added system prompt | none | The `STRICT_GENERATION_CONTROL` block that injects one was added on 2026-07-21, after these runs. The system prompt used was PersistBench's own `prompts.py`, which the thesis did not modify. |
| `seed` | not set | No `--seed` flag and no `seed` request field. Irrelevant at temperature 0. |
| `do_sample` | not applicable | Generation goes through the chat-completions API; `temperature=0.0` gives greedy decoding. |

## 3. Repetition penalty, top_p, top_k

None of the requests set these. The effective values come from the vLLM startup log of each job.

### Qwen2.5-7B-Instruct runs (MUSE-News, MUSE-Books Qwen)

All seven logs checked (`logs/vllm_muse_news_qwen25_{before,rmu,wga,simnpo,satimp}_408558_*.log`, `logs/vllm_muse_books_qwen25_{before,satimp,simnpo}_409517_*.log`) contain the same line at the generation date:

```
WARNING 07-08 12:40:57 [model.py:1502] Default vLLM sampling parameters have been overridden by the model's
`generation_config.json`: `{'repetition_penalty': 1.05, 'temperature': 0.7, 'top_k': 20, 'top_p': 0.8}`.
If this is not intended, please relaunch vLLM instance with `--generation-config vllm`.
```

(job 408558 task 0 shown). vLLM adopted the checkpoint's `generation_config.json`; the same values are in `saves/finetune/muse_news_qwen25_7b_instruct_target/generation_config.json` and `saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459/generation_config.json`. The request overrode only `temperature`, so:

| Setting | Effective value |
|---|---|
| `repetition_penalty` | 1.05 |
| `top_p`, `top_k` | 0.8 and 20 as logged; no effect, because temperature 0 selects the argmax token |

### Llama-2-7b run (MUSE-Books official target)

`logs/vllm_muse_books_llama2_before_408885_0.log` does not contain the override warning. No local `generation_config.json` exists for the official target, so it could not be inspected. `repetition_penalty`, `top_p` and `top_k` are therefore not established for this run; the most likely case is vLLM's defaults (no penalty). `top_p` and `top_k` have no effect at temperature 0.

## 4. Repetition penalty 1.08 is incorrect

`mechanistic/outputs/muse_books_weekly_update_analysis/README.md` states "repetition penalty 1.08" for the MUSE-Books Qwen generations. This is wrong. The request `api_params` contain no `repetition_penalty`, and the vLLM log of the job (`logs/vllm_muse_books_qwen25_before_409517_0.log`, 2026-07-12) shows 1.05.

The 1.08 comes from hardcoded literals written into a `generation_settings` metadata dict:

```
mechanistic/privacy_collapse/persistbench_native/prepare_native_200.py:208:           "repetition_penalty": 1.08,
mechanistic/privacy_collapse/persistbench_native/prepare_native_sycophancy_200.py:243: "repetition_penalty": 1.08,
```

These scripts only repackage already generated PersistBench responses into JSONL for hidden-state extraction; they do not generate and could not have measured the value. The same dict has `"top_p": 1.0` (actual effective value 0.8) and `"vllm_seed": 0` (no seed was set). The value 1.08 matches the `PB_REPETITION_PENALTY` default in the `STRICT_GENERATION_CONTROL` block added to `utils.py` on 2026-07-21, and two later WMDP-Cyber scripts export the same value. The scripts were written about two months after the MUSE generations, and the value was most likely taken from the then-current `utils.py`.

Where it appears:

| Location | Status |
|---|---|
| `mechanistic/outputs/muse_books_weekly_update_analysis/README.md` | states 1.08 in prose; incorrect |
| `prepare_native_200.py:208`, `prepare_native_sycophancy_200.py:243` | hardcoded source |
| Nine JSONL files: `mechanistic/privacy_collapse/persistbench_native/generations/{base,satimp,simnpo,sycophancy_base,sycophancy_satimp,sycophancy_simnpo}_generation0.jsonl` and three copies under `mechanistic/outputs/muse_books_weekly_update_analysis/native_sycophancy/generations/` | `generation_settings.repetition_penalty` is wrong; the generated text is valid and was not edited |

The correction is recorded in `thesis/manifests/provenance/persistbench_generation_corrections.json`. `DISCOVERY_REPORT.md` in the same directory does not repeat the number.

## 5. Comparison across runs

| Setting | MUSE-News (Qwen) | MUSE-Books (Qwen) | MUSE-Books (Llama-2) |
|---|---|---|---|
| `temperature` | 0.0 | 0.0 | 0.0 |
| `max_tokens` | 96 | 96 | 96 |
| `truncate_prompt_tokens` | 1800 | 1800 | 1800 |
| Generations per item (cross-domain / sycophancy / beneficial) | 3 / 3 / 1 | 3 / 3 / 1 | 3 / 3 / 1 |
| Chat template | `simple_llama_chat_template.jinja` | same (shares the launcher template) | `simple_llama_chat_template.jinja` |
| `max_model_len` | 2048 | 2048 (launcher template shared with the other two; not checked line by line) | 2048 |
| Effective `repetition_penalty` | 1.05 | 1.05 | not established |
| Effective `top_p` / `top_k` | 0.8 / 20 (no effect) | 0.8 / 20 (no effect) | not established (no effect) |

The settings chosen by the thesis are identical across the runs. The only difference is the model-dependent default from `generation_config.json`.

## 6. Reproducibility

1. The original generations cannot be reproduced exactly with the current code. The patched `external/PersistBench/src/benchmark/utils.py` applies `STRICT_GENERATION_CONTROL` (`repetition_penalty=1.08`, an injected "no JSON/code" system prompt, a different `max_tokens` path), none of which existed on 2026-07-08, 07-10 or 07-12.
2. The launcher `api_params` are unchanged and the checkpoints are frozen. The earlier `utils.py` can be reconstructed by reverting the blocks added on 2026-07-21 (`docs/persistbench_patch.md`). The vLLM version used at the time was not checked against `external/PersistBench/uv.lock`.
3. Canonical frozen outputs: `external/PersistBench/outputs/{muse_news_qwen25,muse_books_llama2,muse_books_qwen25}_selected_full/*.json` and the PrivacyLens outputs in `outputs/privacylens_muse_news_qwen25_selected/` and `outputs/privacylens_muse_books_{llama2,qwen25}_selected/`.
4. To state in the experimental setup: temperature 0.0 (greedy), `max_tokens` 96, prompt truncated to the last 1800 tokens, `max_model_len` 2048, 3 generations per cross-domain and sycophancy item and 1 per beneficial-memory item, bfloat16, the shared chat template, vLLM OpenAI-compatible serving. For the Qwen runs, also the model default `repetition_penalty=1.05`.
5. Not to be claimed: `repetition_penalty=1.08`; specific `top_p`/`top_k` for the Llama-2 run; any seed; any custom system prompt at generation time.
