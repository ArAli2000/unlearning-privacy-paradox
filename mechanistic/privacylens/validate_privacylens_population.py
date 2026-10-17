#!/usr/bin/env python3
"""CPU-only validation and provenance normalization for population activations."""

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import torch
import transformers
from transformers import AutoTokenizer

from extract_single_privacylens import DATA_PATH, MODEL_PATHS, REPO_ROOT, build_prompt, build_prompt_text


EXPECTED_SHAPE = (29, 3584)
JOB_BY_SAMPLE = {"main1": "421534", "main415": "421550"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path,
        default=REPO_ROOT / "mechanistic/outputs/privacy_population_12v12/sample_manifest.csv",
    )
    args = parser.parse_args()
    with args.manifest.open(newline="", encoding="utf-8") as handle:
        sample_ids = list(dict.fromkeys(row["sample_id"] for row in csv.DictReader(handle)))
    dataset = {item["name"]: item for item in json.loads(DATA_PATH.read_text(encoding="utf-8"))}
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    validated = []
    for sid in sample_ids:
        output_dir = REPO_ROOT / "mechanistic/outputs" / sid
        metadata_path = output_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        raw_prompt = build_prompt_text(dataset[sid])
        final_prompt = build_prompt(dataset[sid], tokenizer)
        encoded = tokenizer(final_prompt, return_tensors="pt")
        input_ids, attention_mask = encoded["input_ids"], encoded["attention_mask"]
        digest = hashlib.sha256(input_ids.contiguous().numpy().tobytes()).hexdigest()
        if metadata["sample_id"] != sid or metadata["exact_prompt"] != final_prompt:
            raise RuntimeError(f"Prompt metadata mismatch for {sid}")
        if metadata["token_ids"] != input_ids[0].tolist() or metadata["token_ids_sha256"] != digest:
            raise RuntimeError(f"Canonical token mismatch for {sid}")
        if metadata["sequence_length"] != input_ids.shape[1] or not attention_mask.all().item():
            raise RuntimeError(f"Sequence length or attention-mask mismatch for {sid}")

        for label, model_path in MODEL_PATHS.items():
            tensor_path = output_dir / f"{label.lower()}_last_prompt_token.pt"
            tensor = torch.load(tensor_path, map_location="cpu", weights_only=True)
            if tuple(tensor.shape) != EXPECTED_SHAPE or tensor.dtype != torch.float32:
                raise RuntimeError(f"Shape/dtype mismatch for {label}/{sid}")
            if tensor.device.type != "cpu" or not torch.isfinite(tensor).all().item():
                raise RuntimeError(f"Device/finiteness mismatch for {label}/{sid}")
            config = json.loads((model_path / "config.json").read_text(encoding="utf-8"))
            model_meta = metadata["models"][label]
            if Path(model_meta["model_path"]).resolve() != model_path.resolve():
                raise RuntimeError(f"Model path mismatch for {label}/{sid}")
            if model_meta["token_ids_sha256"] != digest or not model_meta["token_ids_identical_to_canonical"]:
                raise RuntimeError(f"Per-model token verification mismatch for {label}/{sid}")
            model_meta.update({
                "model_type": config["model_type"], "hidden_size": config["hidden_size"],
                "layer_count": config["num_hidden_layers"], "attention_backend": "sdpa",
            })

        metadata.update({
            "raw_constructed_prompt": raw_prompt,
            "tokenizer_path": str(MODEL_PATHS["BASE"]),
            "canonical_attention_mask": attention_mask[0].tolist(),
            "software": {
                "python": platform.python_version(), "torch": torch.__version__,
                "transformers": transformers.__version__, "cuda_runtime": torch.version.cuda,
            },
            "device": {"name": "NVIDIA A100-SXM4-80GB", "extraction_node": "rubeus", "index": 0},
            "extraction_job_id": JOB_BY_SAMPLE.get(sid, "421573"),
        })
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        validated.append({
            "sample_id": sid, "sequence_length": input_ids.shape[1], "models": 3,
            "shape": "29x3584", "dtype": "torch.float32", "device": "cpu",
            "finite": True, "canonical_tokens_verified": True,
            "cross_model_token_hash_verified": len({metadata["models"][x]["token_ids_sha256"] for x in MODEL_PATHS}) == 1,
            "extraction_job_id": metadata["extraction_job_id"],
        })
    validation_path = args.manifest.parent / "extraction_validation.csv"
    with validation_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(validated[0]))
        writer.writeheader(); writer.writerows(validated)
    print(f"Validated {len(validated)} samples / {len(validated) * 3} tensors; wrote {validation_path}")


if __name__ == "__main__":
    main()
