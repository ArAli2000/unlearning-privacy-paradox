#!/usr/bin/env python3
"""Reproducibility check: regenerate the unpatched BASE/unlearned responses for the 10
HIGH_CONFIDENCE_FAILURE cases with vLLM, using the settings of the original PersistBench
generation run (job 408558, thesis/scripts/persistbench/run_persistbench_muse_news_qwen25_selected.sh).

Each (model, prompt) gets 3 separate sequential calls, as in the original run, rather than
one batched n=3 call, so call-to-call engine variance is exercised.

Settings are taken from the vLLM server log (logs/vllm_muse_news_qwen25_before_408558_0.log),
not from the native manifest's `generation_settings` field, which wrongly says
repetition_penalty=1.08 / top_p=1.0. The log shows the checkpoint's generation_config.json
defaults were applied (repetition_penalty=1.05, top_k=20, top_p=0.8); the client only
overrode temperature (0.0) and max_tokens (96). So only those two are passed to SamplingParams.
Server flags: dtype=bfloat16, max_model_len=2048.

To isolate engine/decoding differences, the exact `effective_prompt_token_ids` from
native_sycophancy_200_v1.json (the ids Experiment 1 used) are passed as prompt_token_ids,
bypassing the chat template.

Output: repro_check/repro_check_raw.json
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from vllm import LLM, SamplingParams

try:
    from vllm.inputs import TokensPrompt
    def make_prompt(ids):
        return TokensPrompt(prompt_token_ids=ids)
except ImportError:
    def make_prompt(ids):
        return {"prompt_token_ids": ids}

ROOT = Path(__file__).resolve().parents[4]
EXP_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent

CLEAN_SELECTION = (
    ROOT / "mechanistic/experiments/muse_news_sycophancy_paradox/analysis/"
    "activation_patching_clean_audit/clean_selection.json"
)
NATIVE_MANIFEST = ROOT / "mechanistic/privacy_collapse/persistbench_native/manifests/native_sycophancy_200_v1.json"

MODEL_PATHS = {
    "BASE": ROOT / "saves/finetune/muse_news_qwen25_7b_instruct_target",
    "SatImp": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459",
    "SimNPO": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459",
}
N_REPS = 3
MAX_TOKENS = 96


def load_needed_prompts() -> dict[str, list[int]]:
    native = json.loads(NATIVE_MANIFEST.read_text(encoding="utf-8"))
    return {r["persistbench_id"]: r["prompt"]["effective_prompt_token_ids"] for r in native["records"]}


def load_treatment_cases() -> list[dict]:
    selection = json.loads(CLEAN_SELECTION.read_text(encoding="utf-8"))
    cases = []
    for method, mv in selection["methods"].items():
        for rec in mv["treatment"]:
            cases.append({"persistbench_id": rec["persistbench_id"], "method": method})
    return cases


def main() -> None:
    prompt_ids_by_pid = load_needed_prompts()
    cases = load_treatment_cases()

    # BASE is needed once per unique persistbench_id across all cases.
    unique_pids = sorted({c["persistbench_id"] for c in cases})
    needed_by_model: dict[str, list[str]] = {"BASE": unique_pids}
    for method in ("SatImp", "SimNPO"):
        needed_by_model[method] = [c["persistbench_id"] for c in cases if c["method"] == method]

    results: dict[str, dict[str, list[str]]] = {}  # pid -> model -> [rep0, rep1, rep2]

    for model_label, pids in needed_by_model.items():
        if not pids:
            continue
        print(f"Loading vLLM engine for {model_label} ({MODEL_PATHS[model_label]})...", flush=True)
        llm = LLM(
            model=str(MODEL_PATHS[model_label]),
            tokenizer=str(MODEL_PATHS["BASE"]),  # shared tokenizer, matches native manifest's software.tokenizer_checkpoint
            dtype="bfloat16",
            max_model_len=2048,
            gpu_memory_utilization=0.90,
        )
        sampling_params = SamplingParams(temperature=0.0, max_tokens=MAX_TOKENS)
        # repetition_penalty/top_k/top_p are left unset so vLLM inherits them from
        # the checkpoint's generation_config.json, as in the original run.

        for rep in range(N_REPS):
            t0 = time.time()
            prompts = [make_prompt(prompt_ids_by_pid[pid]) for pid in pids]
            outputs = llm.generate(prompts, sampling_params)
            for pid, out in zip(pids, outputs):
                text = out.outputs[0].text
                results.setdefault(pid, {}).setdefault(model_label, []).append(text)
            print(f"  {model_label} rep {rep}: {len(pids)} prompts in {time.time()-t0:.1f}s", flush=True)

        del llm
        import gc, torch
        gc.collect()
        torch.cuda.empty_cache()

    out_path = OUT_DIR / "repro_check_raw.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
