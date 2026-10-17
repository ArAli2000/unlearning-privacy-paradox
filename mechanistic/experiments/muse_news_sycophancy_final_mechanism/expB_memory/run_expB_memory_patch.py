#!/usr/bin/env python3
"""Experiment B: does the SAME unlearned model's WITH_MEMORY vs NO_MEMORY
internal state at the prompt-end position causally shift the model's
teacher-forced preference between the safe (BASE-authored) and sycophantic
(manually verified unlearned failure) continuations?

This is a WITHIN-MODEL comparison (unlike Experiment 1/Phase-9, which
compared BASE vs unlearned). Recipient and donor are the SAME model weights;
only the PROMPT differs (memory present vs removed).

Primary readout: the same teacher-forced mean-logprob safe-vs-sycophantic
contrast already established in `run_activation_patching_clean.py`
(`analysis/activation_patching_clean_audit/`), reused unmodified
(`mean_logprob`). Free generation is NOT used here (per task instruction --
free generation is unstable/run-sensitive, established separately).

Alignment: WITH_MEMORY and NO_MEMORY prompts have different lengths (the
memory block changes prompt length), so raw full-sequence position-wise
patching (as used for BASE-vs-unlearned, where both sequences are identical)
is invalid here. Instead this patches ONLY the single prompt-end position
(the last token of each condition's own effective prompt, immediately before
generation/continuation) -- reusing the exact same semantic position already
extracted by the repo's own no-memory alignment infrastructure
(`extract_no_memory_prompt_end.py`: "last token of the memory-ablated
(no-memory) effective prompt"). Donor values are the ALREADY-EXTRACTED
prompt-end hidden states (no live donor forward pass needed):
  WITH_MEMORY: mechanistic/privacy_collapse/persistbench_native/representations/
               sycophancy/{base,satimp,simnpo}_prompt_end.pt  (200, 29, 3584)
  NO_MEMORY:   mechanistic/experiments/muse_news_sycophancy_paradox/representations/
               {base,satimp,simnpo}_prompt_end_no_memory.pt   (200, 29, 3584)
Row order verified identical (same 200 persistbench_ids, same order) between
both manifests before this script was written.

Conditions per (persistbench_id, model):
  A. WITH_MEMORY unpatched
  B. WITH_MEMORY patched with NO_MEMORY donor state (forward direction --
     "does removing memory's internal effect shift toward the safe
     continuation?")
  C. NO_MEMORY unpatched
  D. NO_MEMORY patched with WITH_MEMORY donor state (reverse direction --
     "does injecting the memory-conditioned state shift toward the
     sycophantic continuation?")
Layer ranges: L14-20, L21-27 (0-indexed), per task instruction (no L0-6/L7-13
here, no head/neuron/SAE analysis).

Models: SatImp, SimNPO (primary) + BASE (optional control, included here
since it reuses the same already-extracted tensors at negligible extra
cost). Clean HIGH_CONFIDENCE_FAILURE examples only (10 treatment cases from
clean_selection.json) -- no controls, no new example selection.

Output: expB_memory/expB_scores.csv (per example/model/direction/range),
        expB_memory/expB_provenance.json
"""
from __future__ import annotations

import gc
import json
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[4]
EXP_DIR = Path(__file__).resolve().parent

CLEAN_SELECTION = (
    ROOT / "mechanistic/experiments/muse_news_sycophancy_paradox/analysis/"
    "activation_patching_clean_audit/clean_selection.json"
)
WITH_MEMORY_MANIFEST = ROOT / "mechanistic/privacy_collapse/persistbench_native/manifests/native_sycophancy_200_v1.json"
NO_MEMORY_MANIFEST = ROOT / "mechanistic/experiments/muse_news_sycophancy_paradox/manifests/native_sycophancy_200_no_memory_v1.json"

WITH_MEMORY_TENSOR_DIR = ROOT / "mechanistic/privacy_collapse/persistbench_native/representations/sycophancy"
NO_MEMORY_TENSOR_DIR = ROOT / "mechanistic/experiments/muse_news_sycophancy_paradox/representations"

MODEL_PATHS = {
    "BASE": ROOT / "saves/finetune/muse_news_qwen25_7b_instruct_target",
    "SatImp": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459",
    "SimNPO": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459",
}
LAYER_RANGES = {
    "mid_late_L14-20": (14, 20),
    "late_L21-27": (21, 27),
}
EXPECTED_TENSOR_SHAPE = (200, 29, 3584)


def load_prompts(manifest_path: Path) -> dict[str, list[int]]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {r["persistbench_id"]: r["prompt"]["effective_prompt_token_ids"] for r in data["records"]}


def load_id_order(manifest_path: Path) -> list[str]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [r["persistbench_id"] for r in data["records"]]


def load_treatment_cases() -> list[dict]:
    selection = json.loads(CLEAN_SELECTION.read_text(encoding="utf-8"))
    cases = []
    for method, mv in selection["methods"].items():
        for rec in mv["treatment"]:
            cases.append({
                "persistbench_id": rec["persistbench_id"],
                "method": method,
                "base_response": rec["base_response"],
                "unlearned_response": rec["unlearned_response"],
            })
    return cases


class SinglePositionPatch:
    """Replaces the hidden state at ONE sequence position (not the whole
    tensor) at each of the given decoder layers, leaving every other
    position untouched. Required because donor (different-length prompt) and
    recipient sequences are not the same length here, unlike the
    BASE-vs-unlearned full-sequence patch used elsewhere in this repo."""

    def __init__(self, model, position: int, donor_vectors: dict[int, torch.Tensor]):
        self.model = model
        self.position = position
        self.donor_vectors = donor_vectors
        self.handles = []

    def _make_hook(self, layer_index: int):
        def hook(module, inputs, output):
            is_tuple = isinstance(output, tuple)
            tensor = output[0] if is_tuple else output
            donor = self.donor_vectors[layer_index].to(device=tensor.device, dtype=tensor.dtype)
            tensor = tensor.clone()
            tensor[:, self.position, :] = donor
            return (tensor,) + output[1:] if is_tuple else tensor

        return hook

    def register(self, layer_indices: list[int]):
        for j in layer_indices:
            self.handles.append(self.model.model.layers[j].register_forward_hook(self._make_hook(j)))

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


def scored(model, prompt_ids, response_ids, device, patch: SinglePositionPatch | None, layer_indices=None):
    if patch is not None:
        patch.register(layer_indices)
    try:
        return mean_logprob(model, prompt_ids, response_ids, device)
    finally:
        if patch is not None:
            patch.remove()


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; submit via SLURM")

    cases = load_treatment_cases()
    wm_prompts = load_prompts(WITH_MEMORY_MANIFEST)
    nm_prompts = load_prompts(NO_MEMORY_MANIFEST)
    id_order = load_id_order(WITH_MEMORY_MANIFEST)
    assert id_order == load_id_order(NO_MEMORY_MANIFEST), "with-memory / no-memory row order mismatch"
    row_index = {pid: i for i, pid in enumerate(id_order)}

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )

    # Preload the already-extracted prompt-end tensors for all three models.
    wm_tensors, nm_tensors = {}, {}
    for label in ("BASE", "SatImp", "SimNPO"):
        t_wm = torch.load(WITH_MEMORY_TENSOR_DIR / f"{label.lower()}_prompt_end.pt", map_location="cpu", weights_only=True)
        t_nm = torch.load(NO_MEMORY_TENSOR_DIR / f"{label.lower()}_prompt_end_no_memory.pt", map_location="cpu", weights_only=True)
        assert tuple(t_wm.shape) == EXPECTED_TENSOR_SHAPE, f"{label} with-memory tensor shape {t_wm.shape}"
        assert tuple(t_nm.shape) == EXPECTED_TENSOR_SHAPE, f"{label} no-memory tensor shape {t_nm.shape}"
        wm_tensors[label] = t_wm
        nm_tensors[label] = t_nm

    all_layer_indices = sorted({j for rng in LAYER_RANGES.values() for j in range(rng[0], rng[1] + 1)})

    rows: list[dict[str, Any]] = []
    for model_label in ("SatImp", "SimNPO", "BASE"):
        relevant_cases = [c for c in cases if model_label == "BASE" or c["method"] == model_label]
        if not relevant_cases:
            continue
        print(f"Loading {model_label}...", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATHS[model_label], torch_dtype=torch.bfloat16, device_map="auto",
            trust_remote_code=True, local_files_only=True, attn_implementation="sdpa",
        ).eval()
        model.requires_grad_(False)
        device = model.get_input_embeddings().weight.device

        for case in relevant_cases:
            pid = case["persistbench_id"]
            method_for_tensors = case["method"]  # tensors indexed by pid regardless of BASE/method row content
            wm_ids, nm_ids = wm_prompts[pid], nm_prompts[pid]
            row_i = row_index[pid]

            response_ids = {
                "safe": tokenizer.encode(case["base_response"], add_special_tokens=False),
                "syco": tokenizer.encode(case["unlearned_response"], add_special_tokens=False),
            }

            t0 = time.time()
            # A: WITH_MEMORY unpatched
            wm_unpatched = {r: mean_logprob(model, wm_ids, ids, device) for r, ids in response_ids.items()}
            # C: NO_MEMORY unpatched
            nm_unpatched = {r: mean_logprob(model, nm_ids, ids, device) for r, ids in response_ids.items()}

            base_row = {
                "model": model_label, "method": case["method"], "persistbench_id": pid,
                "unpatched_score_with_memory": wm_unpatched["safe"] - wm_unpatched["syco"],
                "unpatched_score_no_memory": nm_unpatched["safe"] - nm_unpatched["syco"],
            }

            for range_name, (lo, hi) in LAYER_RANGES.items():
                layer_indices = list(range(lo, hi + 1))

                # B: forward -- recipient=WITH_MEMORY, donor=NO_MEMORY (same model)
                donor_nm_vecs = {j: nm_tensors[model_label][row_i, j + 1] for j in layer_indices}  # +1: state 0 is embedding
                patch_fwd = SinglePositionPatch(model, position=len(wm_ids) - 1, donor_vectors=donor_nm_vecs)
                wm_patched = {
                    r: scored(model, wm_ids, ids, device, patch_fwd, layer_indices) for r, ids in response_ids.items()
                }

                # D: reverse -- recipient=NO_MEMORY, donor=WITH_MEMORY (same model)
                donor_wm_vecs = {j: wm_tensors[model_label][row_i, j + 1] for j in layer_indices}
                patch_rev = SinglePositionPatch(model, position=len(nm_ids) - 1, donor_vectors=donor_wm_vecs)
                nm_patched = {
                    r: scored(model, nm_ids, ids, device, patch_rev, layer_indices) for r, ids in response_ids.items()
                }

                rows.append({
                    **base_row, "layer_range": range_name,
                    "patched_score_with_memory_donor_no_memory": wm_patched["safe"] - wm_patched["syco"],
                    "patched_score_no_memory_donor_with_memory": nm_patched["safe"] - nm_patched["syco"],
                    "forward_shift": (wm_patched["safe"] - wm_patched["syco"]) - base_row["unpatched_score_with_memory"],
                    "reverse_shift": (nm_patched["safe"] - nm_patched["syco"]) - base_row["unpatched_score_no_memory"],
                })

            print(f"  {model_label} {pid[:8]} done in {time.time()-t0:.1f}s", flush=True)

        del model
        gc.collect()
        torch.cuda.empty_cache()

    out_path = EXP_DIR / "expB_scores.csv"
    import csv
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out_path} ({len(rows)} rows)", flush=True)

    provenance = {
        "layer_ranges": LAYER_RANGES,
        "continuations": "safe=clean_selection.json base_response; sycophantic=clean_selection.json unlearned_response (same texts as the clean teacher-forced Phase-9 result)",
        "patch_position": "single prompt-end position only (last token of each condition's own effective prompt); NOT full-sequence, because with-memory/no-memory prompts differ in length",
        "donor_source": "already-extracted prompt_end hidden-state tensors (no live donor forward pass needed)",
        "models": ["SatImp", "SimNPO", "BASE (control)"],
        "n_treatment_cases": len(cases),
    }
    (EXP_DIR / "expB_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
