#!/usr/bin/env python3
"""Extract prompt-end hidden states for frozen native PersistBench prompts."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import socket
import time
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifests/native_cross_domain_200_v1.json"
EXPECTED_SHAPE = (200, 29, 3584)
MODEL_PATHS = {
    "BASE": ROOT / "saves/finetune/muse_news_qwen25_7b_instruct_target",
    "SatImp": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459",
    "SimNPO": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459",
}
if os.environ.get("PERSISTBENCH_NATIVE_DATASET") == "muse_books":
    MODEL_PATHS = {
        "BASE": ROOT / "saves/finetune/muse_books_qwen25_7b_instruct_target",
        "SatImp": ROOT / "saves/unlearn/muse_books_qwen25_7b_instruct_satimp/checkpoint-51",
        "SimNPO": ROOT / "saves/unlearn/muse_books_qwen25_7b_instruct_simnpo/checkpoint-51",
    }


def ids_sha(ids: list[int]) -> str:
    return hashlib.sha256(torch.tensor(ids, dtype=torch.int64).numpy().tobytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=HERE / "representations")
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; submit run_prompt_end_extraction.sbatch")
    manifest_path = args.manifest.resolve()
    output_dir = args.output_dir.resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = data["records"]
    if len(records) != 200:
        raise RuntimeError("Frozen native manifest does not contain 200 records")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )
    canonical_ids = [record["prompt"]["effective_prompt_token_ids"] for record in records]
    for record, token_ids in zip(records, canonical_ids, strict=True):
        if ids_sha(token_ids) != record["prompt"]["effective_prompt_token_ids_sha256"]:
            raise RuntimeError(f"Prompt token SHA mismatch: {record['persistbench_id']}")
        if record["prompt"]["extraction_index"] != len(token_ids) - 1:
            raise RuntimeError(f"Extraction index mismatch: {record['persistbench_id']}")
        if token_ids[-1] == tokenizer.eos_token_id:
            raise RuntimeError(f"EOS prompt endpoint: {record['persistbench_id']}")

    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "manifest": str(manifest_path.relative_to(ROOT)),
        "record_count": 200,
        "expected_shape": list(EXPECTED_SHAPE),
        "semantic_position": "last token of original effective chat-formatted prompt immediately before generation",
        "generated_response_tokens_included": False,
        "eos_endpoint": False,
        "prompt_token_ids_identical_across_models": True,
        "persistbench_ids": [record["persistbench_id"] for record in records],
        "prompt_sha256": [record["prompt"]["effective_prompt_token_ids_sha256"] for record in records],
        "final_prompt_token_ids": [ids[-1] for ids in canonical_ids],
        "final_prompt_tokens": [tokenizer.convert_ids_to_tokens(ids[-1]) for ids in canonical_ids],
        "extraction_indices": [len(ids) - 1 for ids in canonical_ids],
        "execution": {
            "hostname": socket.gethostname(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "cuda_runtime": torch.version.cuda,
            "cuda_device": torch.cuda.get_device_name(0),
            "dtype_model": "bfloat16",
            "dtype_saved": "float32",
            "attention": "sdpa",
            "use_cache": False,
        },
        "models": {},
    }

    base_vocab = tokenizer.get_vocab()
    for label, model_path in MODEL_PATHS.items():
        output_path = output_dir / f"{label.lower()}_prompt_end.pt"
        if output_path.exists() and not args.overwrite:
            existing = torch.load(output_path, map_location="cpu", weights_only=True)
            if tuple(existing.shape) == EXPECTED_SHAPE and existing.dtype == torch.float32 and torch.isfinite(existing).all():
                print(f"Skipping valid existing tensor: {output_path}", flush=True)
                continue
            raise RuntimeError(f"Invalid existing tensor; use --overwrite: {output_path}")
        model_tokenizer = AutoTokenizer.from_pretrained(
            model_path, use_fast=True, trust_remote_code=True, local_files_only=True
        )
        if model_tokenizer.get_vocab() != base_vocab:
            raise RuntimeError(f"Tokenizer vocabulary differs for {label}")
        print(f"Loading {label}: {model_path}", flush=True)
        started = time.time()
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
            local_files_only=True,
            attn_implementation="sdpa",
        ).eval()
        model.requires_grad_(False)
        if model.config.num_hidden_layers != 28 or model.config.hidden_size != 3584:
            raise RuntimeError(f"Unexpected architecture for {label}")
        device = model.get_input_embeddings().weight.device
        rows = []
        for index, (record, token_ids) in enumerate(zip(records, canonical_ids, strict=True), 1):
            input_ids = torch.tensor([token_ids], dtype=torch.long, device=device)
            attention_mask = torch.ones_like(input_ids)
            with torch.inference_mode():
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    output_hidden_states=True,
                    use_cache=False,
                    return_dict=True,
                )
            if outputs.hidden_states is None or len(outputs.hidden_states) != 29:
                raise RuntimeError(f"Missing hidden states for {label}/{record['persistbench_id']}")
            activation = torch.stack(
                [state[0, -1].detach().to(device="cpu", dtype=torch.float32) for state in outputs.hidden_states]
            )
            if tuple(activation.shape) != (29, 3584) or not torch.isfinite(activation).all():
                raise RuntimeError(f"Invalid activation for {label}/{record['persistbench_id']}")
            rows.append(activation)
            if index == 1 or index % 20 == 0:
                print(f"{label}: {index}/200", flush=True)
            del outputs, activation, input_ids, attention_mask
        tensor = torch.stack(rows)
        if tuple(tensor.shape) != EXPECTED_SHAPE or tensor.dtype != torch.float32 or not torch.isfinite(tensor).all():
            raise RuntimeError(f"Invalid final tensor for {label}: {tuple(tensor.shape)}")
        torch.save(tensor, output_path)
        metadata["models"][label] = {
            "checkpoint": str(model_path.relative_to(ROOT)),
            "tensor": str(output_path.relative_to(ROOT)),
            "shape": list(tensor.shape),
            "dtype": str(tensor.dtype),
            "runtime_seconds": time.time() - started,
            "tokenizer_vocabulary_identical_to_base": True,
            "prompt_token_ids_identical_to_manifest": True,
        }
        del tensor, rows, model, model_tokenizer
        gc.collect()
        torch.cuda.empty_cache()

    # Fill metadata for valid tensors skipped during a resumed run.
    for label, model_path in MODEL_PATHS.items():
        output_path = output_dir / f"{label.lower()}_prompt_end.pt"
        tensor = torch.load(output_path, map_location="cpu", weights_only=True)
        if tuple(tensor.shape) != EXPECTED_SHAPE or tensor.dtype != torch.float32 or not torch.isfinite(tensor).all():
            raise RuntimeError(f"Post-write validation failed for {label}")
        metadata["models"].setdefault(label, {
            "checkpoint": str(model_path.relative_to(ROOT)),
            "tensor": str(output_path.relative_to(ROOT)),
            "shape": list(tensor.shape),
            "dtype": str(tensor.dtype),
            "runtime_seconds": None,
            "tokenizer_vocabulary_identical_to_base": True,
            "prompt_token_ids_identical_to_manifest": True,
            "resumed_existing_tensor": True,
        })
        del tensor
    metadata_path = output_dir / "extraction_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Extraction validated: {metadata_path}", flush=True)


if __name__ == "__main__":
    main()
