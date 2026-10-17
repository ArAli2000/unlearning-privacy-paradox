#!/usr/bin/env python3
"""Coarse layer-range activation patching for MUSE-News native PersistBench sycophancy
(plus a few cross-domain) SAFE_TO_FAILURE cases.

Primary intervention: run the unlearned model's own autoregressive decoding, but at every step
replace its residual-stream output at a contiguous band of decoder layers (at the position about to
be predicted) with the activation BASE produces for the same running sequence. The loop is
step-by-step without a KV cache, as in the other extraction scripts, so BASE always sees exactly
what the unlearned model has generated so far.

--reverse: BASE decodes and the unlearned method supplies the donor activations.

Layer indexing: 1..28 refers to the output of model.model.layers[index-1] (hidden_states[0] is the
embedding output).

Decoding: greedy (temperature 0) with a repetition penalty of 1.05 over the full running sequence
(HF-style), approximating the original PersistBench settings (temperature 0, repetition_penalty 1.05,
max_tokens 96) without vLLM.

Cases: the SAFE_TO_FAILURE rows with the largest judge-score jump from continuation_cases_v1.json,
capped per method/category. Selection was fixed before any patched generation was inspected.

Rescoring: a simplified local judge pass (same JUDGE_SYSTEM_PROMPT_SINGLE_* rubric and
build_judge_prompt as the original benchmark, run with transformers.generate on the cached
Qwen/Qwen2.5-7B-Instruct, with a JSON-repair retry) is applied to every generated continuation.
It approximates the original vLLM guided_json judge.

Output: mechanistic/outputs/muse_news_sycophancy_mechanistic/patching/
  patched_generations.json
  patched_generations_judged.json
  patching_metadata.json
"""

from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import re
import sys
import time
import types
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "mechanistic/outputs/muse_news_sycophancy_mechanistic"
PATCH_OUT = OUT_ROOT / "patching"
CONTINUATION_MANIFEST = OUT_ROOT / "manifests/continuation_cases_v1.json"

MODEL_PATHS = {
    "BASE": ROOT / "saves/finetune/muse_news_qwen25_7b_instruct_target",
    "SatImp": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459",
    "SimNPO": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459",
}
JUDGE_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

LAYER_RANGES = {
    "early": list(range(1, 8)),
    "early_middle": list(range(8, 15)),
    "middle_late": list(range(15, 22)),
    "late": list(range(22, 29)),
}
NUM_LAYERS = 28
MAX_NEW_TOKENS = 96
REPETITION_PENALTY = 1.05


def load_prompt_and_judge_builders():
    pkg = types.ModuleType("benchmark")
    pkg.__path__ = [str(ROOT / "external/PersistBench/src/benchmark")]
    sys.modules["benchmark"] = pkg
    for module_name in ("config", "prompts"):
        spec = importlib.util.spec_from_file_location(
            f"benchmark.{module_name}", ROOT / f"external/PersistBench/src/benchmark/{module_name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"benchmark.{module_name}"] = module
        spec.loader.exec_module(module)
    prompts = sys.modules["benchmark.prompts"]
    return prompts.build_judge_prompt, {
        "sycophancy": prompts.JUDGE_SYSTEM_PROMPT_SINGLE_SYCOPHANCY,
        "cross_domain": prompts.JUDGE_SYSTEM_PROMPT_SINGLE_CROSS_DOMAIN,
    }


def select_cases(max_per_method: int, max_cross_domain: int) -> list[dict[str, Any]]:
    manifest = json.loads(CONTINUATION_MANIFEST.read_text(encoding="utf-8"))
    failures = [c for c in manifest["cases"] if c["group"] == "FAILURE"]
    selected: list[dict[str, Any]] = []
    for category, method in (("sycophancy", "SatImp"), ("sycophancy", "SimNPO")):
        pool = [c for c in failures if c["category"] == category and c["method"] == method]
        pool.sort(key=lambda c: c["unlearned_score"] - c["base_score"], reverse=True)
        selected.extend(pool[:max_per_method])
    cross = [c for c in failures if c["category"] == "cross_domain"]
    cross.sort(key=lambda c: c["unlearned_score"] - c["base_score"], reverse=True)
    selected.extend(cross[:max_cross_domain])
    return selected


class ActivationDonor:
    """Captures, and can later replay, the last-position residual-stream output of
    a set of decoder layers for the model it is attached to."""

    def __init__(self, model):
        self.model = model
        self.captured: dict[int, torch.Tensor] = {}
        self._hooks = []

    def capture(self, layers: list[int], sequence: list[int]) -> None:
        self.captured = {}
        handles = []

        def make_capture_hook(layer_index: int):
            def hook(module, inputs, output):
                self.captured[layer_index] = output[0][0, -1, :].detach().clone()
                return output

            return hook

        for layer_index in layers:
            handles.append(self.model.model.layers[layer_index - 1].register_forward_hook(make_capture_hook(layer_index)))
        device = self.model.get_input_embeddings().weight.device
        ids = torch.tensor([sequence], dtype=torch.long, device=device)
        attention_mask = torch.ones_like(ids)
        with torch.inference_mode():
            self.model(input_ids=ids, attention_mask=attention_mask, use_cache=False, return_dict=True)
        for handle in handles:
            handle.remove()
        del ids, attention_mask


def apply_repetition_penalty(logits: torch.Tensor, sequence: list[int], penalty: float) -> torch.Tensor:
    if penalty == 1.0:
        return logits
    unique_ids = torch.tensor(sorted(set(sequence)), device=logits.device, dtype=torch.long)
    scores = logits[unique_ids]
    scores = torch.where(scores < 0, scores * penalty, scores / penalty)
    logits = logits.clone()
    logits[unique_ids] = scores
    return logits


def generate(
    primary_model,
    donor_model,
    tokenizer,
    prompt_ids: list[int],
    patch_layers: list[int] | None,
    max_new_tokens: int = MAX_NEW_TOKENS,
) -> dict[str, Any]:
    device = primary_model.get_input_embeddings().weight.device
    sequence = list(prompt_ids)
    generated: list[int] = []
    donor = ActivationDonor(donor_model) if patch_layers else None

    for _ in range(max_new_tokens):
        patch_handles = []
        if patch_layers:
            donor.capture(patch_layers, sequence)

            def make_patch_hook(layer_index: int):
                def hook(module, inputs, output):
                    hs = output[0].clone()
                    hs[:, -1, :] = donor.captured[layer_index].to(hs.dtype)
                    return (hs,) + tuple(output[1:])

                return hook

            for layer_index in patch_layers:
                patch_handles.append(
                    primary_model.model.layers[layer_index - 1].register_forward_hook(make_patch_hook(layer_index))
                )

        ids = torch.tensor([sequence], dtype=torch.long, device=device)
        attention_mask = torch.ones_like(ids)
        with torch.inference_mode():
            outputs = primary_model(input_ids=ids, attention_mask=attention_mask, use_cache=False, return_dict=True)
        logits = outputs.logits[0, -1, :].float()
        for handle in patch_handles:
            handle.remove()
        logits = apply_repetition_penalty(logits, sequence, REPETITION_PENALTY)
        next_token = int(torch.argmax(logits).item())
        del ids, attention_mask, outputs, logits
        if next_token == tokenizer.eos_token_id:
            break
        generated.append(next_token)
        sequence.append(next_token)

    text = tokenizer.decode(generated, skip_special_tokens=True)
    return {"token_ids": generated, "text": text, "token_count": len(generated)}


def run_generations(cases: list[dict[str, Any]], reverse: bool) -> list[dict[str, Any]]:
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )
    results: list[dict[str, Any]] = []

    for method in ("SatImp", "SimNPO"):
        method_cases = [c for c in cases if c["method"] == method]
        if not method_cases:
            continue
        print(f"Loading BASE and {method} for patching...", flush=True)
        base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATHS["BASE"], torch_dtype=torch.bfloat16, device_map="auto",
            trust_remote_code=True, local_files_only=True, attn_implementation="sdpa",
        ).eval()
        base_model.requires_grad_(False)
        method_model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATHS[method], torch_dtype=torch.bfloat16, device_map="auto",
            trust_remote_code=True, local_files_only=True, attn_implementation="sdpa",
        ).eval()
        method_model.requires_grad_(False)

        primary, donor, primary_label, donor_label = (
            (base_model, method_model, "BASE", method) if reverse else (method_model, base_model, method, "BASE")
        )

        for case in method_cases:
            started = time.time()
            unpatched = generate(primary, primary, tokenizer, case["prompt_token_ids"], patch_layers=None)
            unpatched["runtime_seconds"] = time.time() - started
            record = {
                "persistbench_id": case["persistbench_id"],
                "category": case["category"],
                "method": method,
                "transition": case["transition"],
                "base_score": case["base_score"],
                "unlearned_score": case["unlearned_score"],
                "reverse_patch": reverse,
                "primary_model": primary_label,
                "donor_model": donor_label,
                "unpatched_generation": unpatched,
                "patched_generations": {},
            }
            for range_name, layers in LAYER_RANGES.items():
                started = time.time()
                patched = generate(primary, donor, tokenizer, case["prompt_token_ids"], patch_layers=layers)
                patched["runtime_seconds"] = time.time() - started
                patched["layer_range"] = layers
                record["patched_generations"][range_name] = patched
                print(
                    f"  {case['persistbench_id'][:8]} [{method}] range={range_name}: "
                    f"{patched['token_count']} tokens in {patched['runtime_seconds']:.1f}s",
                    flush=True,
                )
            results.append(record)
            print(f"Case {case['persistbench_id'][:8]} [{method}] done in {time.time()-started:.1f}s (last range)", flush=True)

        del base_model, method_model
        gc.collect()
        torch.cuda.empty_cache()

    return results


def simplified_local_judge_score(
    judge_model, judge_tokenizer, build_judge_prompt, judge_system_prompts, category: str,
    memories: list[str], query: str, response: str,
) -> dict[str, Any]:
    system_prompt = judge_system_prompts[category]
    user_message = build_judge_prompt(memories, query, response)
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]

    def ask(extra_instruction: str | None = None) -> str:
        msgs = list(messages)
        if extra_instruction:
            msgs.append({"role": "user", "content": extra_instruction})
        ids = judge_tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_tensors="pt").to(
            judge_model.get_input_embeddings().weight.device
        )
        with torch.inference_mode():
            out = judge_model.generate(ids, max_new_tokens=300, do_sample=False)
        return judge_tokenizer.decode(out[0, ids.shape[1]:], skip_special_tokens=True)

    raw = ask()
    match = re.search(r'"score"\s*:\s*(-?\d+)', raw)
    if not match:
        match = re.search(r"\bscore\D{0,10}?(\d)\b", raw, re.IGNORECASE)
    if match:
        return {"score": int(match.group(1)), "raw_judge_response": raw, "repair_used": False}

    repaired = ask('Reply with ONLY a JSON object: {"score": integer, "reasoning": "short reason"}')
    match = re.search(r'"score"\s*:\s*(-?\d+)', repaired)
    if match:
        return {"score": int(match.group(1)), "raw_judge_response": repaired, "repair_used": True}
    return {"score": None, "raw_judge_response": raw, "repair_used": True, "repair_response": repaired}


def score_generations(results: list[dict[str, Any]]) -> None:
    build_judge_prompt, judge_system_prompts = load_prompt_and_judge_builders()
    native_manifests = {
        "sycophancy": json.loads((ROOT / "mechanistic/privacy_collapse/persistbench_native/manifests/native_sycophancy_200_v1.json").read_text()),
        "cross_domain": json.loads((ROOT / "mechanistic/privacy_collapse/persistbench_native/manifests/native_cross_domain_200_v1.json").read_text()),
    }
    records_by_id = {
        category: {r["persistbench_id"]: r for r in data["records"]} for category, data in native_manifests.items()
    }

    print(f"Loading local judge: {JUDGE_MODEL_ID}", flush=True)
    judge_tokenizer = AutoTokenizer.from_pretrained(JUDGE_MODEL_ID, use_fast=True, local_files_only=True)
    judge_model = AutoModelForCausalLM.from_pretrained(
        JUDGE_MODEL_ID, torch_dtype=torch.bfloat16, device_map="auto", local_files_only=True, attn_implementation="sdpa",
    ).eval()
    judge_model.requires_grad_(False)

    for record in results:
        native_record = records_by_id[record["category"]][record["persistbench_id"]]
        memories = native_record["memories"]
        query = native_record["query"]
        for gen_key in ("unpatched_generation", *[f"patched:{r}" for r in record["patched_generations"]]):
            if gen_key == "unpatched_generation":
                gen = record["unpatched_generation"]
            else:
                gen = record["patched_generations"][gen_key.split(":", 1)[1]]
            gen["judge"] = simplified_local_judge_score(
                judge_model, judge_tokenizer, build_judge_prompt, judge_system_prompts,
                record["category"], memories, query, gen["text"],
            )
            print(f"  judged {record['persistbench_id'][:8]} {gen_key}: score={gen['judge']['score']}", flush=True)

    del judge_model, judge_tokenizer
    gc.collect()
    torch.cuda.empty_cache()


def main() -> None:
    global MAX_NEW_TOKENS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-per-method", type=int, default=3)
    parser.add_argument("--max-cross-domain", type=int, default=3)
    parser.add_argument("--reverse", action="store_true", help="Patch BASE using unlearned-method donor activations instead.")
    parser.add_argument("--skip-judge", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=MAX_NEW_TOKENS)
    parser.add_argument("--tag", default="")
    parser.add_argument("--methods", nargs="+", default=["SatImp", "SimNPO"], choices=["SatImp", "SimNPO"])
    args = parser.parse_args()
    MAX_NEW_TOKENS = args.max_new_tokens

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; submit via SLURM")

    PATCH_OUT.mkdir(parents=True, exist_ok=True)
    cases = select_cases(args.max_per_method, args.max_cross_domain)
    cases = [c for c in cases if c["method"] in args.methods]
    print(f"Selected {len(cases)} cases: {[(c['category'], c['method'], c['persistbench_id'][:8]) for c in cases]}", flush=True)

    results = run_generations(cases, reverse=args.reverse)

    suffix = ("_reverse" if args.reverse else "") + (f"_{args.tag}" if args.tag else "")
    out_path = PATCH_OUT / f"patched_generations{suffix}.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)}", flush=True)

    if not args.skip_judge:
        score_generations(results)
        judged_path = PATCH_OUT / f"patched_generations_judged{suffix}.json"
        judged_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {judged_path.relative_to(ROOT)}", flush=True)

    metadata = {
        "cases": [{"persistbench_id": c["persistbench_id"], "category": c["category"], "method": c["method"]} for c in cases],
        "layer_ranges": LAYER_RANGES,
        "reverse_patch": args.reverse,
        "max_new_tokens": MAX_NEW_TOKENS,
        "repetition_penalty": REPETITION_PENALTY,
        "decoding": "greedy (temperature 0) with HF-style repetition penalty; no KV cache (full recompute per step)",
        "judge": "simplified local-judge rescoring via transformers.generate + JSON-repair retry, NOT the original vLLM guided_json pipeline" if not args.skip_judge else "skipped",
    }
    (PATCH_OUT / f"patching_metadata{suffix}.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
