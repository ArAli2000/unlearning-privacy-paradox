#!/usr/bin/env python3
"""Efficiently extract selected PrivacyLens samples with one load per model."""

import argparse
import csv
import gc
import hashlib
import json
import platform
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

from extract_single_privacylens import (
    DATA_PATH, MODEL_PATHS, REPO_ROOT, build_prompt, build_prompt_text,
)


EXPECTED_SHAPE = (29, 3584)


def valid_complete_output(sample_id: str) -> bool:
    output_dir = REPO_ROOT / "mechanistic/outputs" / sample_id
    metadata_path = output_dir / "metadata.json"
    if not metadata_path.exists():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("sample_id") != sample_id:
            return False
        for label in ("base", "rmu", "wga"):
            tensor = torch.load(
                output_dir / f"{label}_last_prompt_token.pt", map_location="cpu", weights_only=True
            )
            if tuple(tensor.shape) != EXPECTED_SHAPE or tensor.dtype != torch.float32:
                return False
            if not torch.isfinite(tensor).all().item():
                return False
        return True
    except (OSError, ValueError, KeyError, RuntimeError, TypeError, json.JSONDecodeError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPO_ROOT / "mechanistic/outputs/privacy_population_12v12/sample_manifest.csv",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; run through the mechanistic SLURM job")

    with args.manifest.open(newline="", encoding="utf-8") as handle:
        sample_ids = list(dict.fromkeys(row["sample_id"] for row in csv.DictReader(handle)))
    dataset = {item["name"]: item for item in json.loads(DATA_PATH.read_text(encoding="utf-8"))}
    missing_ids = [sid for sid in sample_ids if sid not in dataset]
    if missing_ids:
        raise RuntimeError(f"Manifest IDs missing from dataset: {missing_ids}")
    selected = [sid for sid in sample_ids if args.overwrite or not valid_complete_output(sid)]
    skipped = [sid for sid in sample_ids if sid not in selected]
    print(f"Selected {len(selected)} samples; skipping valid existing samples: {skipped}", flush=True)
    if not selected:
        return

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    canonical = {}
    metadata = {}
    for sid in selected:
        raw_prompt = build_prompt_text(dataset[sid])
        final_prompt = build_prompt(dataset[sid], tokenizer)
        encoded = tokenizer(final_prompt, return_tensors="pt")
        input_ids = encoded["input_ids"].contiguous()
        attention_mask = encoded["attention_mask"].contiguous()
        ids_list = input_ids[0].tolist()
        digest = hashlib.sha256(input_ids.numpy().tobytes()).hexdigest()
        canonical[sid] = {"input_ids": input_ids, "attention_mask": attention_mask}
        metadata[sid] = {
            "sample_id": sid,
            "dataset_path": str(DATA_PATH),
            "prompt_type": "naive",
            "raw_constructed_prompt": raw_prompt,
            "exact_prompt": final_prompt,
            "token_ids": ids_list,
            "decoded_tokens": tokenizer.convert_ids_to_tokens(ids_list),
            "token_ids_sha256": digest,
            "sequence_length": input_ids.shape[1],
            "tokenizer_path": str(MODEL_PATHS["BASE"]),
            "software": {
                "python": platform.python_version(), "torch": torch.__version__,
                "transformers": transformers.__version__, "cuda_runtime": torch.version.cuda,
            },
            "device": {"name": torch.cuda.get_device_name(0), "index": 0},
            "models": {},
        }

    for label, model_path in MODEL_PATHS.items():
        print(f"Loading {label} once: {model_path}", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=True,
            local_files_only=True, attn_implementation="sdpa",
        )
        model.eval()
        device = model.get_input_embeddings().weight.device
        expected_shape = (model.config.num_hidden_layers + 1, model.config.hidden_size)
        if expected_shape != EXPECTED_SHAPE:
            raise RuntimeError(f"{label} config implies {expected_shape}, expected {EXPECTED_SHAPE}")
        for index, sid in enumerate(selected, 1):
            cpu_ids = canonical[sid]["input_ids"]
            cpu_mask = canonical[sid]["attention_mask"]
            input_ids, attention_mask = cpu_ids.to(device), cpu_mask.to(device)
            if not torch.equal(input_ids.cpu(), cpu_ids) or not torch.equal(attention_mask.cpu(), cpu_mask):
                raise RuntimeError(f"Canonical token tensor verification failed for {label}/{sid}")
            with torch.inference_mode():
                outputs = model(
                    input_ids=input_ids, attention_mask=attention_mask,
                    output_hidden_states=True, use_cache=False, return_dict=True,
                )
            if outputs.hidden_states is None:
                raise RuntimeError(f"No hidden states returned for {label}/{sid}")
            activations = torch.stack([
                state[0, -1].detach().to(device="cpu", dtype=torch.float32)
                for state in outputs.hidden_states
            ])
            if tuple(activations.shape) != EXPECTED_SHAPE:
                raise RuntimeError(f"Bad shape for {label}/{sid}: {tuple(activations.shape)}")
            if not torch.isfinite(activations).all().item():
                raise RuntimeError(f"Non-finite activation for {label}/{sid}")
            output_dir = REPO_ROOT / "mechanistic/outputs" / sid
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{label.lower()}_last_prompt_token.pt"
            torch.save(activations, output_path)
            metadata[sid]["models"][label] = {
                "model_path": str(model_path), "activation_path": str(output_path),
                "activation_shape": list(activations.shape), "activation_dtype": str(activations.dtype),
                "model_type": model.config.model_type, "hidden_size": model.config.hidden_size,
                "layer_count": model.config.num_hidden_layers,
                "saved_state_count": len(outputs.hidden_states),
                "attention_backend": model.config._attn_implementation,
                "token_ids_sha256": metadata[sid]["token_ids_sha256"],
                "token_ids_identical_to_canonical": True,
            }
            print(f"[{index}/{len(selected)}] {label}/{sid}: {tuple(activations.shape)}", flush=True)
            del outputs, activations, input_ids, attention_mask
        del model
        gc.collect()
        torch.cuda.empty_cache()

    for sid in selected:
        hashes = {entry["token_ids_sha256"] for entry in metadata[sid]["models"].values()}
        if len(hashes) != 1 or len(metadata[sid]["models"]) != len(MODEL_PATHS):
            raise RuntimeError(f"Cross-model token verification failed for {sid}")
        output_dir = REPO_ROOT / "mechanistic/outputs" / sid
        (output_dir / "metadata.json").write_text(
            json.dumps(metadata[sid], indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(f"Completed {len(selected)} samples", flush=True)


if __name__ == "__main__":
    main()
