# Phase 1: Gemma judge availability check — STOPPED

All checks below were performed on the login node (`slurm-login`) without loading any model weights or importing `torch`/`vllm` in a way that would touch a GPU or trigger a large download — only filesystem/API metadata checks.

## 1. Is `google/gemma-2-9b-it` already cached?

```
$ find /storage/ukp/work/elshashay/.cache/huggingface/hub -maxdepth 1 -iname "*gemma*"
$ find /mnt/beegfs/work/elshashay/.cache/huggingface/hub -maxdepth 1 -iname "*gemma*"
```
Both empty. **Not cached anywhere findable in this account's HF cache.**

## 2. Is Hugging Face authentication configured?

```
$ python -c "from huggingface_hub import HfApi; HfApi().whoami()"
huggingface_hub.errors.LocalTokenNotFoundError: Token is required (token=True), but no token found.
```
No `HF_TOKEN`/`HUGGINGFACE_TOKEN` in the shell environment; no token file at any of `~/.huggingface/token`, `~/.cache/huggingface/token`, `/storage/ukp/work/elshashay/.huggingface/token`, `/mnt/beegfs/work/elshashay/.cache/huggingface/token`. **No HF authentication is configured in this environment.**

## 3. Does the model actually require authentication/license acceptance?

```
$ curl -s https://huggingface.co/api/models/google/gemma-2-9b-it | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['gated'], d['disabled'], d['private'])"
manual False False
```
**Confirmed: `gated: "manual"`.** `google/gemma-2-9b-it` requires a Hugging Face account to (a) accept Google's usage license for the Gemma model family and (b) be authenticated with a token belonging to that account, before any file in the repository can be downloaded. This is independent of whether the repo's metadata page is publicly viewable (it is — the API call above succeeded without a token — but that only returns model-card metadata, not the weight files).

## 4. Can the existing environment serve it via vLLM at all (setup check, not a load)?

- `unlearning` conda env (used for training/finetuning): **no `vllm` installed.**
- `external/PersistBench/.venv` (the vendored tool's own uv-managed venv): **no `vllm` installed.**
- `base` conda env (`/storage/ukp/work/elshashay/miniconda3`): **`vllm==0.23.0` installed** — this is the environment `thesis/scripts/persistbench/run_local_judge_server_penelope.sh` already activates (`conda activate base`) to serve the existing Qwen judge, confirmed by direct inspection of that script. vLLM 0.23.0 is recent enough to support the Gemma-2 architecture (added to vLLM well before this release); this will be given a final empirical confirmation at actual job-launch time on a GPU node, not on the login node, per the task's constraint.
- `transformers==4.51.3` is installed in the `unlearning` env — recent enough for Gemma-2 (`Gemma2ForCausalLM` was added in transformers 4.42) — checked in case vLLM ends up needing a transformers-based fallback path for chat templating.

## 5. GPU memory / cluster fit (informational, not yet needed)

`sinfo` confirms real GPU partitions on this cluster include `a100` (80GB variants among them), `h100pcie`, `h200nvl`, `a6000`, `v100`. Gemma-2-9b-it in bf16 is ~18GB of weights, comparable in scale to the Qwen2.5-7B-Instruct judge already served successfully on this cluster's existing GPU allocation (`--gres=gpu:a180:1`, `--mem=180G` in the existing judge-server script) — expected to fit the same allocation without a memory concern, to be confirmed at actual launch.

## 6. Conclusion — STOP condition met

`google/gemma-2-9b-it` is **unavailable in this environment right now**, specifically because:
1. It is not cached locally, and
2. Downloading it requires Hugging Face authentication from an account that has been manually granted access to this gated model, and
3. No such authentication is configured anywhere in this environment.

Per the task's explicit instruction — *"If google/gemma-2-9b-it is unavailable or incompatible, STOP and report the specific reason before substituting another model. Do not silently choose a different Gemma model."* — this process stops here. `vllm` itself, the conda environment, and the cluster's GPU resources are all otherwise ready; the only missing piece is credentialed access to the model weights.
