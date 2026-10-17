#!/usr/bin/env python3
"""GPU-only PersistBench-MCQ extraction; models are loaded sequentially."""
from __future__ import annotations

import csv
import gc
import json
import platform
from datetime import datetime, timezone

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

from common import CONFIG_PATH, MCQ_MANIFEST_SHA256, OUTPUT_ROOT, ROOT


def projected_logits(model, hidden_states):
    values = []
    for index, states in enumerate(hidden_states):
        vector = states[0, -1]
        readout = vector if index == len(hidden_states) - 1 else model.model.norm(vector)
        values.append(model.lm_head(readout).float())
    return values


@torch.inference_mode()
def direction_difference(model, safe_ids: list[int], leaky_ids: list[int]) -> torch.Tensor:
    endpoints = []
    for ids in (safe_ids, leaky_ids):
        tensor = torch.tensor([ids], dtype=torch.long, device=model.device)
        output = model(tensor, output_hidden_states=True, use_cache=False, return_dict=True)
        endpoints.append(torch.stack([state[0, -1].detach().float().cpu() for state in output.hidden_states]))
        del tensor, output
    return endpoints[0] - endpoints[1]


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; submit the SLURM job")
    static = json.loads((OUTPUT_ROOT / "static_validation.json").read_text())
    if static.get("status") != "passed":
        raise RuntimeError("Static validation has not passed")
    if static.get("mcq_manifest_sha256") != MCQ_MANIFEST_SHA256:
        raise RuntimeError("Static artifacts were not prepared from the approved CLEAR_NO manifest")
    records = json.loads((OUTPUT_ROOT / "prepared_examples.json").read_text())["records"]
    config = json.loads(CONFIG_PATH.read_text())
    provenance = {
        "started_utc": datetime.now(timezone.utc).isoformat(), "config": config,
        "software": {"python": platform.python_version(), "torch": torch.__version__, "transformers": transformers.__version__},
        "device": torch.cuda.get_device_name(0), "models": {},
        "approved_manifest_sha256": MCQ_MANIFEST_SHA256,
        "methodology": "PrivacyLens-compatible: raw hidden states at completed-answer endpoint; per-layer normalized lm-head projection at prompt boundary",
    }
    for label, relative in config["models"].items():
        path = (ROOT / relative).resolve()
        print(f"Loading {label}: {path}", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            path, torch_dtype=torch.bfloat16, device_map="auto", local_files_only=True,
            trust_remote_code=True, attn_implementation=config["attention_implementation"],
        )
        model.eval()
        if model.config.model_type != "qwen2" or model.config.num_hidden_layers != 28 or model.config.hidden_size != 3584:
            raise RuntimeError(f"Unexpected architecture for {label}")
        rows, differences = [], []
        for number, record in enumerate(records, 1):
            if len(record["safe_continuation_ids"]) != 1 or len(record["leaky_continuation_ids"]) != 1:
                raise RuntimeError("A/B continuation ceased to be one token")
            prompt = torch.tensor([record["prompt_ids"]], dtype=torch.long, device=model.device)
            output = model(prompt, output_hidden_states=True, use_cache=False, return_dict=True)
            a_id, b_id = record["leaky_continuation_ids"][0], record["safe_continuation_ids"][0]
            for state_index, logits in enumerate(projected_logits(model, output.hidden_states)):
                probabilities = torch.softmax(logits, dim=0)
                logit_a, logit_b = float(logits[a_id]), float(logits[b_id])
                rows.append({
                    "model": label, "pair_id": record["example_id"], "example_id": record["example_id"], "state_index": state_index,
                    "state_label": "embedding" if state_index == 0 else f"L{state_index}",
                    "logit_A": logit_a, "logit_B": logit_b, "safe_minus_leaky_logit_margin": logit_b - logit_a,
                    "P_A": float(probabilities[a_id]), "P_B": float(probabilities[b_id]),
                    "predicted_answer": "B" if logit_b > logit_a else "A",
                    "safe_decision_correct": int(logit_b > logit_a),
                })
            del prompt, output
            differences.append(direction_difference(model, record["safe_ids"], record["leaky_ids"]))
            print(f"  [{number}/50] {record['example_id']}", flush=True)
        model_dir = OUTPUT_ROOT / "models" / label
        model_dir.mkdir(parents=True, exist_ok=True)
        with (model_dir / "mcq_readout_per_example.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        per_example = torch.stack(differences)
        mean_direction = per_example.mean(dim=0)
        torch.save({
            "model": label, "dataset": "persistbench_mcq", "example_ids": [r["example_id"] for r in records],
            "definition": "mean_i(h_safe_i - h_leaky_i)", "per_example_differences": per_example,
            "mean_direction": mean_direction, "direction_norms": torch.linalg.vector_norm(mean_direction, dim=-1),
            "state_labels": ["embedding"] + [f"L{i}" for i in range(1, 29)],
            "answer_position": "last answer-completion token; no template-added EOS",
        }, model_dir / "persistbench_mcq_directions.pt")
        provenance["models"][label] = {"path": str(path), "model_type": model.config.model_type, "num_hidden_layers": 28, "hidden_size": 3584}
        del model
        gc.collect(); torch.cuda.empty_cache()
    provenance["completed_utc"] = datetime.now(timezone.utc).isoformat()
    (OUTPUT_ROOT / "gpu_extraction_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")


if __name__ == "__main__":
    main()
