#!/usr/bin/env python3
"""Phase 8 (GPU): layer-wise teacher-forced preference between the actual BASE-safe
response and the actual unlearned-model response, for the MUSE-News sycophancy
SAFE_TO_FAILURE group (primary) and the full SAFE_TO_SAFE group (control).

For each example and each evaluating model M in {BASE, method}, and each candidate
continuation C in {text_safe := BASE's own generation-0 response, text_alt := the
method's own generation-0 response for the same row}, this computes a per-layer
logit-lens estimate of mean log P_M(C's tokens | prompt, previous C tokens) by teacher
forcing prompt_tokens + C_tokens through model M once, taking hidden_states at every
layer, applying M's own final norm (except the already-normed last hidden-state entry,
per this repo's established logit-lens convention -- see
mechanistic/privacy_collapse/persistbench_sycophancy_mcq/extract.py) and M's own
lm_head, then log_softmax and gathering the actual next-token log-probability at each
response position.

score_M(layer) = mean_logprob_M(text_safe, layer) - mean_logprob_M(text_alt, layer)

This is the sound multi-token alternative to a single "safe vs failing continuation"
log-prob ratio requested for Phase 8: it does not require the two continuations to have
equal length or shared tokens, and it uses each model's own weights throughout (no
cross-model tying).
"""
from __future__ import annotations

import argparse
import gc
import json
import platform
import socket
import time
from pathlib import Path

import pandas as pd
import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TRANSITIONS = HERE / "manifests" / "sycophancy_transition_groups.json"
NATIVE_MANIFEST = (
    ROOT / "mechanistic/privacy_collapse/persistbench_native/manifests/native_sycophancy_200_v1.json"
)
OUT_DIR = HERE / "representations"
NUM_STATES = 29  # embedding + 28 transformer layers

MODEL_PATHS = {
    "BASE": ROOT / "saves/finetune/muse_news_qwen25_7b_instruct_target",
    "SatImp": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459",
    "SimNPO": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459",
}
METHODS = ["SatImp", "SimNPO"]


def load_native_prompts() -> dict[str, list[int]]:
    native = json.loads(NATIVE_MANIFEST.read_text(encoding="utf-8"))
    return {rec["persistbench_id"]: rec["prompt"]["effective_prompt_token_ids"] for rec in native["records"]}


def build_population(method: str, transitions: dict) -> list[dict]:
    groups = transitions["methods"][method]["groups"]
    pop = []
    for item in groups["SAFE_TO_FAILURE"]:
        pop.append({**item, "group": "SAFE_TO_FAILURE"})
    for item in groups["SAFE_TO_SAFE"]:
        pop.append({**item, "group": "SAFE_TO_SAFE"})
    return pop


def layerwise_mean_logprob(model, prompt_ids: list[int], response_ids: list[int], device) -> list[float]:
    """Return a length-NUM_STATES list: mean teacher-forced log-prob per response token, per layer."""
    if len(response_ids) == 0:
        raise RuntimeError("Empty response token sequence")
    full_ids = prompt_ids + response_ids
    input_ids = torch.tensor([full_ids], dtype=torch.long, device=device)
    attention_mask = torch.ones_like(input_ids)
    with torch.inference_mode():
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            output_hidden_states=True,
            use_cache=False,
            return_dict=True,
        )
    hidden_states = outputs.hidden_states
    if hidden_states is None or len(hidden_states) != NUM_STATES:
        raise RuntimeError(f"Expected {NUM_STATES} hidden states, got {0 if hidden_states is None else len(hidden_states)}")
    p0 = len(prompt_ids)
    target_ids = torch.tensor(response_ids, dtype=torch.long, device=device)  # tokens at positions p0..p0+L-1
    source_slice = slice(p0 - 1, p0 - 1 + len(response_ids))  # positions predicting each target
    per_layer_mean: list[float] = []
    for layer_index, state in enumerate(hidden_states):
        h = state[0, source_slice]  # (L, hidden)
        if layer_index != NUM_STATES - 1:
            h = model.model.norm(h)
        logits = model.lm_head(h).float()  # (L, vocab)
        log_probs = torch.log_softmax(logits, dim=-1)
        target_logprobs = log_probs.gather(1, target_ids.unsqueeze(1)).squeeze(1)  # (L,)
        per_layer_mean.append(float(target_logprobs.mean().item()))
        del h, logits, log_probs, target_logprobs
    del outputs, hidden_states, input_ids, attention_mask
    return per_layer_mean


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="cap examples per method (smoke test)")
    parser.add_argument("--out", type=Path, default=OUT_DIR / "teacher_forced_layer_logprobs.csv")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required")

    transitions = json.loads(TRANSITIONS.read_text(encoding="utf-8"))
    prompts_by_id = load_native_prompts()

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )

    populations = {method: build_population(method, transitions) for method in METHODS}
    if args.limit is not None:
        for method in METHODS:
            populations[method] = populations[method][: args.limit]

    rows: list[dict] = []
    provenance = {
        "hostname": socket.gethostname(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda_device": torch.cuda.get_device_name(0),
        "num_states": NUM_STATES,
        "logit_lens_convention": "model.model.norm() applied to every hidden_states entry except "
        "the last (already normed by the model's forward pass), then model.lm_head(); matches "
        "mechanistic/privacy_collapse/persistbench_sycophancy_mcq/extract.py",
        "population_sizes": {m: len(populations[m]) for m in METHODS},
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    def run_model_over(label: str, model_path: Path, method: str, population: list[dict]) -> None:
        print(f"Loading {label} for method={method} ({len(population)} rows)", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
            local_files_only=True,
            attn_implementation="sdpa",
        ).eval()
        model.requires_grad_(False)
        device = model.get_input_embeddings().weight.device
        for index, item in enumerate(population, 1):
            prompt_ids = prompts_by_id[item["persistbench_id"]]
            for text_role, text in (("safe", item["base_response"]), ("alt", item["unlearned_response"])):
                response_ids = tokenizer.encode(text, add_special_tokens=False)
                if len(response_ids) == 0:
                    raise RuntimeError(f"Empty tokenization for {item['persistbench_id']}/{text_role}")
                per_layer = layerwise_mean_logprob(model, prompt_ids, response_ids, device)
                for layer_index, mean_logprob in enumerate(per_layer):
                    rows.append(
                        {
                            "method": method,
                            "evaluating_model": label,
                            "persistbench_id": item["persistbench_id"],
                            "group": item["group"],
                            "text_role": text_role,
                            "response_token_count": len(response_ids),
                            "layer": layer_index,
                            "mean_logprob": mean_logprob,
                        }
                    )
            if index == 1 or index % 20 == 0:
                print(f"  {label}/{method}: {index}/{len(population)}", flush=True)
        del model
        gc.collect()
        torch.cuda.empty_cache()

    # BASE is evaluated against both methods' populations (union of rows differs per method
    # because SAFE_TO_SAFE/SAFE_TO_FAILURE membership is method-specific).
    for method in METHODS:
        run_model_over("BASE", MODEL_PATHS["BASE"], method, populations[method])
    for method in METHODS:
        run_model_over(method, MODEL_PATHS[method], method, populations[method])

    df = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    provenance["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    provenance["row_count"] = len(df)
    (args.out.parent / "teacher_forced_extraction_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {args.out} ({len(df)} rows)")


if __name__ == "__main__":
    main()
