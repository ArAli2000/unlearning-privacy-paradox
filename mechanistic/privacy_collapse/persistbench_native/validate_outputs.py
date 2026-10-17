#!/usr/bin/env python3
"""Validate frozen native PersistBench prompt-end extraction outputs."""

import json
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE / "manifests/native_cross_domain_200_v1.json").read_text())
metadata = json.loads((HERE / "representations/extraction_metadata.json").read_text())
ids = [record["persistbench_id"] for record in manifest["records"]]
assert len(ids) == len(set(ids)) == 200
assert metadata["persistbench_ids"] == ids
assert metadata["prompt_token_ids_identical_across_models"] is True
assert metadata["generated_response_tokens_included"] is False
assert metadata["eos_endpoint"] is False
for record in manifest["records"]:
    prompt = record["prompt"]
    assert prompt["effective_prompt_identical_across_models"] is True
    assert prompt["contains_generated_response_tokens"] is False
    assert prompt["template_added_eos_at_endpoint"] is False
    assert prompt["extraction_index"] == len(prompt["effective_prompt_token_ids"]) - 1
for label in ("base", "satimp", "simnpo"):
    path = HERE / f"representations/{label}_prompt_end.pt"
    tensor = torch.load(path, map_location="cpu", weights_only=True)
    assert tuple(tensor.shape) == (200, 29, 3584)
    assert tensor.dtype == torch.float32
    assert torch.isfinite(tensor).all()
print("Validated 200 IDs/model, identical prompt tokens, prompt-only endpoints, and [200,29,3584] float32 tensors")
