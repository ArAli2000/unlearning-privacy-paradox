#!/usr/bin/env python3
"""GPU-only sequential extraction for the MUSE-News Qwen Privacy Collapse pilot."""
from __future__ import annotations

import csv
import gc
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

from common import CONFIG_PATH, OUTPUT_ROOT, ROOT


def rank_of(logits: torch.Tensor, token_id: int) -> int:
    target = logits[token_id]
    return int((logits > target).sum().item() + 1)


def projected_logits(model, hidden_states: tuple[torch.Tensor, ...], position: int) -> list[torch.Tensor]:
    result = []
    for state_index, states in enumerate(hidden_states):
        vector = states[0, position]
        # Qwen2Model.forward stores states 0..L-1 before blocks and applies the
        # final RMSNorm before storing state L.  Normalize only intermediate states.
        readout = vector if state_index == len(hidden_states) - 1 else model.model.norm(vector)
        result.append(model.lm_head(readout).float())
    return result


@torch.inference_mode()
def score_pair(model, prompt_ids: list[int], continuations: tuple[list[int], list[int]]) -> tuple[list[dict], list[dict]]:
    # The statically validated pilot alternatives are each exactly one token, so
    # one prompt forward pass supplies the identical scoring boundary for both.
    # Refuse to silently take a first subtoken if future prompt formatting changes.
    if any(len(value) != 1 for value in continuations):
        raise RuntimeError("Pilot A/B alternatives are no longer single-token; extend teacher-forced sequence scoring")
    ids = torch.tensor([prompt_ids], dtype=torch.long, device=model.device)
    with torch.inference_mode():
        output = model(ids, output_hidden_states=True, use_cache=False, return_dict=True)
    all_scores = []
    logits_by_layer = projected_logits(model, output.hidden_states, len(prompt_ids) - 1)
    for continuation in continuations:
        target_id = continuation[0]
        layer_scores = []
        for logits in logits_by_layer:
            logprob = torch.log_softmax(logits, dim=-1)[target_id]
            layer_scores.append({
                "token_logits": [float(logits[target_id])], "token_logprobs": [float(logprob)],
                "token_probs": [float(logprob.exp())], "token_ranks": [rank_of(logits, target_id)]
            })
        all_scores.append(layer_scores)
    del output, ids
    return all_scores[0], all_scores[1]


def extract_direction_difference(model, safe_ids: list[int], leaky_ids: list[int]) -> torch.Tensor:
    vectors = []
    for ids in (safe_ids, leaky_ids):
        tensor = torch.tensor([ids], dtype=torch.long, device=model.device)
        with torch.inference_mode():
            output = model(tensor, output_hidden_states=True, use_cache=False, return_dict=True)
        # Same semantic answer-side endpoint: last continuation token in both sequences.
        vectors.append(torch.stack([state[0, -1].detach().float().cpu() for state in output.hidden_states]))
        del output, tensor
    return vectors[0] - vectors[1]


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; submit the SLURM job. Never run this 7B extraction on a login CPU.")
    config = json.loads(CONFIG_PATH.read_text())
    prepared = json.loads((OUTPUT_ROOT / "prepared_examples.json").read_text())
    static = json.loads((OUTPUT_ROOT / "static_validation.json").read_text())
    if static.get("status") != "passed":
        raise RuntimeError("Static validation has not passed")

    tokenizer_path = (ROOT / config["models"]["BASE"]).resolve()
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True, use_fast=True)
    provenance = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "software": {"python": platform.python_version(), "torch": torch.__version__, "transformers": transformers.__version__},
        "device": torch.cuda.get_device_name(0),
        "normalization": {
            "installed_qwen_behavior": "hidden_states[-1] is post-final-RMSNorm; preceding states are pre-final-RMSNorm",
            "logit_lens": "apply each model's model.model.norm to states 0..L-1; use state L directly; then own lm_head",
            "double_normalize_final_state": False,
        },
        "models": {},
    }

    for model_label, relative_path in config["models"].items():
        model_path = (ROOT / relative_path).resolve()
        print(f"Loading {model_label}: {model_path}", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype=torch.bfloat16, device_map="auto", local_files_only=True,
            trust_remote_code=True, attn_implementation=config["attention_implementation"]
        )
        model.eval()
        if model.config.model_type != "qwen2" or model.config.num_hidden_layers != 28:
            raise RuntimeError(f"Unexpected architecture for {model_label}")
        model_dir = OUTPUT_ROOT / "models" / model_label
        model_dir.mkdir(parents=True, exist_ok=True)
        logit_rows = []

        for dataset_name in ("privacy", "control"):
            differences = []
            example_ids = []
            for index, record in enumerate(prepared[dataset_name], 1):
                safe_scores, leaky_scores = score_pair(
                    model, record["prompt_ids"],
                    (record["safe_continuation_ids"], record["leaky_continuation_ids"])
                )
                for layer, (safe, leaky) in enumerate(zip(safe_scores, leaky_scores)):
                    safe_logprob, leaky_logprob = sum(safe["token_logprobs"]), sum(leaky["token_logprobs"])
                    single = len(safe["token_logits"]) == len(leaky["token_logits"]) == 1
                    logit_difference = safe["token_logits"][0] - leaky["token_logits"][0] if single else math.nan
                    logit_rows.append({
                        "model": model_label, "dataset": dataset_name, "example_id": record["example_id"],
                        "state_index": layer, "state_label": "embedding" if layer == 0 else f"L{layer}",
                        "safe_semantic_label": record["safe"]["semantic_label"], "leaky_semantic_label": record["leaky"]["semantic_label"],
                        "safe_continuation_ids": json.dumps(record["safe_continuation_ids"]),
                        "leaky_continuation_ids": json.dumps(record["leaky_continuation_ids"]),
                        "safe_probability": math.exp(safe_logprob), "leaky_probability": math.exp(leaky_logprob),
                        "probability_difference": math.exp(safe_logprob) - math.exp(leaky_logprob),
                        "safe_logprob": safe_logprob, "leaky_logprob": leaky_logprob,
                        "continuation_logprob_difference": safe_logprob - leaky_logprob,
                        "single_token_logit_difference": logit_difference,
                        "safe_token_logits": json.dumps(safe["token_logits"]), "leaky_token_logits": json.dumps(leaky["token_logits"]),
                        "safe_token_ranks": json.dumps(safe["token_ranks"]), "leaky_token_ranks": json.dumps(leaky["token_ranks"]),
                    })
                differences.append(extract_direction_difference(model, record["safe_ids"], record["leaky_ids"]))
                example_ids.append(record["example_id"])
                print(f"  {dataset_name} [{index}/{len(prepared[dataset_name])}] {record['example_id']}", flush=True)
            per_example = torch.stack(differences)
            mean_direction = per_example.mean(dim=0)
            torch.save({
                "model": model_label, "dataset": dataset_name, "example_ids": example_ids,
                "definition": "mean(h_safe) - mean(h_leaky)",
                "per_example_differences": per_example, "mean_direction": mean_direction,
                "direction_norms": torch.linalg.vector_norm(mean_direction, dim=-1),
                "state_labels": ["embedding"] + [f"L{i}" for i in range(1, 29)],
                "answer_position": "last answer-continuation token",
            }, model_dir / f"{dataset_name}_directions.pt")

        with (model_dir / "logit_lens_per_example.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(logit_rows[0])); writer.writeheader(); writer.writerows(logit_rows)
        provenance["models"][model_label] = {
            "path": str(model_path), "model_type": model.config.model_type,
            "num_hidden_layers": model.config.num_hidden_layers, "hidden_size": model.config.hidden_size,
            "vocab_size": model.config.vocab_size, "lm_head_tied": bool(model.config.tie_word_embeddings),
        }
        del model
        gc.collect()
        torch.cuda.empty_cache()

    provenance["completed_utc"] = datetime.now(timezone.utc).isoformat()
    (OUTPUT_ROOT / "gpu_extraction_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print("Sequential extraction complete", flush=True)


if __name__ == "__main__":
    main()
