#!/usr/bin/env python3
"""Clean rerun of the activation patching experiment.

Differs from run_activation_patching.py only in example selection: examples come from
clean_selection.json (HIGH_CONFIDENCE_FAILURE treatment + matched SAFE_TO_SAFE controls)
instead of a judge-score-jump ranking. Layer ranges, patching mechanism and teacher-forced
mean-logprob scoring are unchanged. Writes only to this directory.
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
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[5]
EXP = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SELECTION = HERE / "clean_selection.json"
NATIVE_MANIFEST = (
    ROOT / "mechanistic/privacy_collapse/persistbench_native/manifests/native_sycophancy_200_v1.json"
)
OUT_DIR = HERE
MODEL_PATHS = {
    "BASE": ROOT / "saves/finetune/muse_news_qwen25_7b_instruct_target",
    "SatImp": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459",
    "SimNPO": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459",
}
LAYER_RANGES = {
    "early_L0-6": (0, 6),
    "early_mid_L7-13": (7, 13),
    "mid_late_L14-20": (14, 20),
    "late_L21-27": (21, 27),
}


def load_prompts() -> dict[str, list[int]]:
    native = json.loads(NATIVE_MANIFEST.read_text(encoding="utf-8"))
    return {rec["persistbench_id"]: rec["prompt"]["effective_prompt_token_ids"] for rec in native["records"]}


def select_examples(selection: dict, method: str) -> list[dict]:
    m = selection["methods"][method]
    items = []
    for t in m["treatment"]:
        it = dict(t)
        it["group"] = "HIGH_CONFIDENCE_FAILURE"
        items.append(it)
    for c in m["control"]:
        it = dict(c)
        it["group"] = "SAFE_TO_SAFE_MATCHED_CONTROL"
        items.append(it)
    return items


class LayerCapture:
    def __init__(self, model, layer_indices: list[int]):
        self.model = model
        self.layer_indices = layer_indices
        self.captured: dict[int, torch.Tensor] = {}
        self.handles = []

    def _make_capture_hook(self, layer_index: int):
        def hook(module, inputs, output):
            tensor = output[0] if isinstance(output, tuple) else output
            self.captured[layer_index] = tensor.detach().clone()
            return output

        return hook

    def register_capture(self):
        for j in self.layer_indices:
            handle = self.model.model.layers[j].register_forward_hook(self._make_capture_hook(j))
            self.handles.append(handle)

    def remove(self):
        for h in self.handles:
            h.remove()
        self.handles = []


class LayerPatch:
    def __init__(self, model, donor_activations: dict[int, torch.Tensor]):
        self.model = model
        self.donor_activations = donor_activations
        self.handles = []

    def _make_patch_hook(self, layer_index: int):
        def hook(module, inputs, output):
            donor = self.donor_activations[layer_index].to(
                device=output[0].device if isinstance(output, tuple) else output.device,
                dtype=output[0].dtype if isinstance(output, tuple) else output.dtype,
            )
            if isinstance(output, tuple):
                if donor.shape != output[0].shape:
                    raise RuntimeError(f"Shape mismatch at layer {layer_index}: {donor.shape} vs {output[0].shape}")
                return (donor,) + output[1:]
            if donor.shape != output.shape:
                raise RuntimeError(f"Shape mismatch at layer {layer_index}: {donor.shape} vs {output.shape}")
            return donor

        return hook

    def register(self, layer_indices: list[int]):
        for j in layer_indices:
            handle = self.model.model.layers[j].register_forward_hook(self._make_patch_hook(j))
            self.handles.append(handle)

    def remove(self):
        for h in self.handles:
            h.remove()
        self.handles = []


def mean_logprob(model, prompt_ids: list[int], response_ids: list[int], device) -> float:
    full_ids = prompt_ids + response_ids
    input_ids = torch.tensor([full_ids], dtype=torch.long, device=device)
    attention_mask = torch.ones_like(input_ids)
    with torch.inference_mode():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False, return_dict=True)
    logits = outputs.logits[0].float()
    p0 = len(prompt_ids)
    source = logits[p0 - 1 : p0 - 1 + len(response_ids)]
    log_probs = torch.log_softmax(source, dim=-1)
    target = torch.tensor(response_ids, dtype=torch.long, device=device)
    target_logprobs = log_probs.gather(1, target.unsqueeze(1)).squeeze(1)
    result = float(target_logprobs.mean().item())
    del outputs, logits, source, log_probs, target_logprobs, input_ids, attention_mask
    return result


def capture_donor_layers(donor_model, prompt_ids: list[int], response_ids: list[int], device, layer_indices: list[int]) -> dict[int, torch.Tensor]:
    capture = LayerCapture(donor_model, layer_indices)
    capture.register_capture()
    full_ids = prompt_ids + response_ids
    input_ids = torch.tensor([full_ids], dtype=torch.long, device=device)
    attention_mask = torch.ones_like(input_ids)
    with torch.inference_mode():
        donor_model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False, return_dict=True)
    capture.remove()
    return capture.captured


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--direction", choices=["unlearned_recipient", "base_recipient"], required=True)
    parser.add_argument("--methods", nargs="+", default=["SatImp", "SimNPO"])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required")

    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    prompts_by_id = load_prompts()
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )

    rows = []
    for method in args.methods:
        if args.direction == "unlearned_recipient":
            donor_label, recipient_label = "BASE", method
        else:
            donor_label, recipient_label = method, "BASE"

        examples = select_examples(selection, method)
        print(f"[{method}/{args.direction}] {len(examples)} examples selected: "
              f"{[e['persistbench_id'][:10] for e in examples]}", flush=True)

        donor = AutoModelForCausalLM.from_pretrained(
            MODEL_PATHS[donor_label], torch_dtype=torch.bfloat16, device_map="auto",
            trust_remote_code=True, local_files_only=True, attn_implementation="sdpa",
        ).eval()
        donor.requires_grad_(False)
        donor_device = donor.get_input_embeddings().weight.device

        recipient = AutoModelForCausalLM.from_pretrained(
            MODEL_PATHS[recipient_label], torch_dtype=torch.bfloat16, device_map="auto",
            trust_remote_code=True, local_files_only=True, attn_implementation="sdpa",
        ).eval()
        recipient.requires_grad_(False)
        recipient_device = recipient.get_input_embeddings().weight.device

        all_layer_indices = sorted({j for rng in LAYER_RANGES.values() for j in range(rng[0], rng[1] + 1)})

        for item in examples:
            prompt_ids = prompts_by_id[item["persistbench_id"]]
            texts = {"safe": item["base_response"], "alt": item["unlearned_response"]}
            response_ids = {role: tokenizer.encode(text, add_special_tokens=False) for role, text in texts.items()}

            baseline_logprob = {
                role: mean_logprob(recipient, prompt_ids, ids, recipient_device) for role, ids in response_ids.items()
            }
            baseline_score = baseline_logprob["safe"] - baseline_logprob["alt"]
            rows.append(
                {"method": method, "direction": args.direction, "persistbench_id": item["persistbench_id"],
                 "group": item["group"], "condition": "unpatched", "score": baseline_score,
                 "logprob_safe": baseline_logprob["safe"], "logprob_alt": baseline_logprob["alt"],
                 "base_score": item["base_score"], "unlearned_score": item.get("unlearned_score")}
            )

            for role, ids in response_ids.items():
                donor_activations = capture_donor_layers(donor, prompt_ids, ids, donor_device, all_layer_indices)
                for range_name, (lo, hi) in LAYER_RANGES.items():
                    layer_indices = list(range(lo, hi + 1))
                    patch = LayerPatch(recipient, {j: donor_activations[j] for j in layer_indices})
                    patch.register(layer_indices)
                    try:
                        lp = mean_logprob(recipient, prompt_ids, ids, recipient_device)
                    finally:
                        patch.remove()
                    rows.append(
                        {"method": method, "direction": args.direction, "persistbench_id": item["persistbench_id"],
                         "group": item["group"], "condition": f"patched_{range_name}", "text_role": role,
                         "logprob": lp}
                    )
                del donor_activations
                gc.collect()
                torch.cuda.empty_cache()

        del donor, recipient
        gc.collect()
        torch.cuda.empty_cache()

    df = pd.DataFrame(rows)
    patched = df[df["condition"] != "unpatched"]
    patched_wide = patched.pivot_table(
        index=["method", "direction", "persistbench_id", "group", "condition"], columns="text_role", values="logprob"
    ).reset_index()
    patched_wide["score"] = patched_wide["safe"] - patched_wide["alt"]
    unpatched = df[df["condition"] == "unpatched"][
        ["method", "direction", "persistbench_id", "group", "condition", "score", "base_score", "unlearned_score"]
    ]
    final = pd.concat(
        [unpatched, patched_wide[["method", "direction", "persistbench_id", "group", "condition", "score"]]],
        ignore_index=True,
    )

    out_path = args.out or (OUT_DIR / f"activation_patching_clean_{args.direction}.csv")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    final.to_csv(out_path, index=False)
    provenance = {
        "direction": args.direction, "layer_ranges": LAYER_RANGES,
        "selection_source": "manual_transition_audit.csv (HIGH_CONFIDENCE_FAILURE only) + matched SAFE_TO_SAFE controls",
        "hostname": socket.gethostname(), "python": platform.python_version(), "torch": torch.__version__,
        "cuda_device": torch.cuda.get_device_name(0), "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (OUT_DIR / f"activation_patching_clean_{args.direction}_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {out_path} ({len(final)} rows)")
    print(final.pivot_table(index=["method", "group", "condition"], values="score").round(3))


if __name__ == "__main__":
    main()
