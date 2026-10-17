# Gemma vLLM engine-core startup failure — diagnosis (job 438615)

## 1. Exact root cause

```
PermissionError: [Errno 13] Permission denied: '/home/elshashay'
```

Raised from `flashinfer/jit/core.py:18`:
```python
os.makedirs(jit_env.FLASHINFER_WORKSPACE_DIR, exist_ok=True)
```

Confirmed directly (interpreter check, no model loaded):
```
>>> from flashinfer.jit import env as jit_env
>>> jit_env.FLASHINFER_WORKSPACE_DIR
'/home/elshashay/.cache/flashinfer/0.6.12'
```

`$HOME` for this job was the default `/home/elshashay` (never overridden by the
smoke-test script). That directory is `drwx------`, owned by `elshashay`, and
looks normal from the login node — but is **not writable when the job runs on
a compute node** (rubeus). This is a cluster home-directory-mount
characteristic, not anything about Gemma, vLLM, CUDA, or the GPU.

This is exactly the same failure class every historically-successful
vLLM-serving script in this repo already works around. For example
`thesis/scripts/persistbench/run_persistbench_muse_books_qwen25_localjudge.sh`
explicitly does:
```bash
export HOME=/storage/ukp/work/elshashay
export FLASHINFER_WORKSPACE_DIR=$HOME/.cache/flashinfer
export VLLM_USE_FLASHINFER_SAMPLER=0
mkdir -p ... "$FLASHINFER_WORKSPACE_DIR" ...
```
The Gemma smoke-test script simply never carried this environment setup over
from those scripts — it is a missing-configuration gap in the new script, not
a new problem with Gemma.

## 2. Failure stage

Startup got **all the way to GPU engine-core initialization**, well past every
earlier stage:

1. SLURM job start — OK (confirmed: job ran 10m14s on `rubeus`)
2. Environment activation (`activate_unlearning_env base`) — OK
3. GPU visibility — OK (job scheduled with `gres/gpu:a180=1`, no GPU-visibility errors logged)
4. vLLM API server start — OK (banner + `non-default args` printed correctly, showing the right model path/dtype/max_model_len)
5. Model config read — OK (`Resolved architecture: Gemma2ForCausalLM` at 15:44:53 — vLLM correctly parsed `config.json` and identified Gemma-2)
6. Tokenizer load — not separately logged, but no error occurred before or during config init tied to the tokenizer
7. CUDA initialization / distributed init — OK (`parallel_state.py:1568 world_size=1 rank=0 ... backend=nccl` at 15:46:22 — NCCL/CUDA context created successfully)
8. **Engine-core GPU worker init → `Sampler.__init__` → `TopKTopPSampler.__init__` → `flashinfer_sampler_supported()` → `import flashinfer` → `flashinfer/jit/core.py` module-level `os.makedirs(...)` → CRASH** at 15:46:25 (only 3 seconds after distributed init began)
9. Weight loading — **never reached** (the crash happens during sampler construction, before `load_weights` is called)
10. KV-cache allocation — never reached
11. Server-ready health check — never reached (this is why the smoke-test script's own wait-loop reported "did not become ready in time" — a secondary, correct-but-uninformative symptom of the real crash)

**First failing stage: engine-core GPU-worker initialization, specifically FlashInfer JIT module import (triggered by an optional sampler-backend capability probe), which failed because the default FlashInfer workspace-cache directory computation used an unwritable `$HOME`.**

## 3. GPU / resource fit

- Node: `rubeus`, GPU: `NVIDIA A100-SXM4-80GB`, 81920 MiB VRAM (confirmed directly via a prior trivial `nvidia-smi` diagnostic job, 438611, on this same node).
- Gemma-2-9B-IT in bfloat16 needs ~18.5 GB for weights (`model.safetensors.index.json`'s `total_size: 18483411968`) plus a modest KV cache at `max_model_len=2048`. This comfortably fits in 80 GB even at `gpu_memory_utilization=0.90` (~72 GB budget). **No evidence anywhere in the logs of an OOM condition** — the crash occurs before any weight loading or KV-cache allocation is attempted, so VRAM sizing is irrelevant to this failure.
- `tensor_parallel_size=1` (single GPU, matches the 1-GPU allocation) — appropriate, not a cause.
- `dtype=bfloat16`, `max_model_len=2048`, `gpu_memory_utilization=0.9` — all as configured; none of these appear anywhere in the traceback.

**Conclusion: this is not a resource-fit / OOM / dtype issue.**

## 4. vLLM command used

```bash
vllm serve "${GEMMA_LOCAL_PATH}" \
  --served-model-name gemma-judge \
  --host 127.0.0.1 \
  --port "$PORT" \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 2048
```

No `--trust-remote-code` (not needed — `Gemma2ForCausalLM` is natively supported by vLLM 0.23.0, confirmed by the successful architecture resolution), no `--enforce-eager`, no explicit `--tensor-parallel-size` (defaults to 1, correct for a 1-GPU job).

Compared with the historically-successful Qwen local-judge command
(`run_local_judge_server_penelope.sh`, same vLLM version, same cluster):
structurally identical (`--host`/`--port`/`--dtype bfloat16`/`--gpu-memory-utilization`/`--max-model-len`) — the **only meaningful difference between the two scripts is that the Qwen script sets the `HOME`/cache/`VLLM_USE_FLASHINFER_SAMPLER` environment block before calling `vllm serve`, and the Gemma smoke-test script did not.** No vLLM flag itself is implicated.

## 5. Model files / config consistency

Already verified in `smoke_test/gemma_availability_check.md` and reconfirmed by this run's own log line `Resolved architecture: Gemma2ForCausalLM` — vLLM read `config.json` successfully and correctly identified the architecture, `max_model_len` was accepted at 2048 (well under the model's native context), and all 4 safetensors shards were loadable (loading was never reached, but the earlier index/shard-presence check in `gemma_availability_check.md` already confirmed completeness). **No config/tokenizer/shard inconsistency found; none is implicated by the traceback.**

## 6. Software compatibility

- Python 3.13, `torch==2.11.0+cu130` (CUDA 13.0), `vllm==0.23.0`, `transformers==5.12.1`, `safetensors==0.8.0`, `flashinfer-python==0.6.12`.
- The failure is **not a version-incompatibility crash** (no `ImportError`/`AttributeError`/CUDA-arch-mismatch anywhere in the trace). It is a plain filesystem `PermissionError` raised at FlashInfer's module-import time, from a directory-creation call unrelated to model compatibility.
- Confirmed directly in the installed source (`vllm/v1/sample/ops/topk_topp_sampler.py`, lines 20–65): `flashinfer_sampler_supported()` checks `envs.VLLM_USE_FLASHINFER_SAMPLER` and returns `False` **before** the line that imports `vllm.v1.attention.backends.flashinfer` (which is what pulls in the crashing `flashinfer` package). So `VLLM_USE_FLASHINFER_SAMPLER=0` is confirmed sufficient to prevent this exact code path from ever importing FlashInfer, not merely a guess by analogy to the historical scripts.

## 7. Minimal fix proposed and applied

Added one environment-setup block to `run_gemma_judge_smoketest.sbatch`, copied verbatim from the pattern already proven across many historically-successful jobs in this repo (`run_persistbench_muse_books_qwen25_localjudge.sh` and others):

```bash
export HOME=/storage/ukp/work/elshashay
export XDG_CACHE_HOME="$HOME/.cache"
export HF_HOME="$XDG_CACHE_HOME/huggingface"
export TRANSFORMERS_CACHE="$HF_HOME"
export HF_DATASETS_CACHE="$HF_HOME/datasets"
export TRITON_CACHE_DIR="$HOME/.triton/autotune"
export FLASHINFER_WORKSPACE_DIR="$XDG_CACHE_HOME/flashinfer"
export VLLM_USAGE_STATS_DIR="$HOME/.cache/vllm/usage"
export VLLM_USE_FLASHINFER_SAMPLER=0
mkdir -p "$XDG_CACHE_HOME" "$HF_HOME" "$HF_DATASETS_CACHE" "$TRITON_CACHE_DIR" "$FLASHINFER_WORKSPACE_DIR" "$VLLM_USAGE_STATS_DIR"
```

No vLLM flag, model choice, GPU request, or judging code was changed. This
does not touch `gemma_judge.py`, the model identity, or any Qwen/frozen file.

## 8. Discrepancy noted, not resolved

The smoke-test wrapper's own readiness check reported the generic
`"Gemma judge server did not become ready in time"` message, and the
`APIServer` process separately raised `RuntimeError: Engine core
initialization failed. See root cause above.` — both are downstream/wrapper
symptoms of the same single root cause identified in §1, not independent
problems.
