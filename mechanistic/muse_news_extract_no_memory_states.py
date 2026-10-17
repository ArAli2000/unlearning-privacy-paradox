#!/usr/bin/env python3
"""GPU extraction of prompt-end hidden states for the memory-ablated
('no_memory') MUSE-News native PersistBench prompts (Phase 7).

For each of the 200 rows in
mechanistic/outputs/muse_news_sycophancy_mechanistic/manifests/native_{category}_200_no_memory_v1.json
this extracts the hidden state at the final prompt token (embedding + L1-L28,
29 states, width 3584) for BASE/SatImp/SimNPO, using the no_memory_prompt
token IDs. The with_memory prompt-end states already exist
(mechanistic/privacy_collapse/persistbench_native/representations/{,sycophancy/}*_prompt_end.pt)
and are not re-extracted here.

Output: mechanistic/outputs/muse_news_sycophancy_mechanistic/representations/<category>/
  {base,satimp,simnpo}_prompt_end_no_memory.pt   ([200, 29, 3584] float32, CPU)
  extraction_metadata.json
"""

from __future__ import annotations

import argparse
import gc
import json
import platform
import socket
import time
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "mechanistic/outputs/muse_news_sycophancy_mechanistic"
EXPECTED_SHAPE = (200, 29, 3584)
MODEL_PATHS = {
    "BASE": ROOT / "saves/finetune/muse_news_qwen25_7b_instruct_target",
    "SatImp": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459",
    "SimNPO": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", required=True, choices=["sycophancy", "cross_domain"])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; submit via SLURM")

    manifest_path = OUT_ROOT / "manifests" / f"native_{args.category}_200_no_memory_v1.json"
    output_dir = OUT_ROOT / "representations" / args.category
    output_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = data["records"]
    if len(records) != 200:
        raise RuntimeError(f"Expected 200 records, found {len(records)}")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )
    canonical_ids = [record["no_memory_prompt"]["effective_prompt_token_ids"] for record in records]
    base_vocab = tokenizer.get_vocab()

    metadata = {
        "manifest": str(manifest_path.relative_to(ROOT)),
        "category": args.category,
        "record_count": 200,
        "expected_shape": list(EXPECTED_SHAPE),
        "semantic_position": "last token of the no-memory (ablated) effective chat-formatted prompt, immediately before generation",
        "generated_response_tokens_included": False,
        "prompt_token_ids_identical_across_models": True,
        "persistbench_ids": [record["persistbench_id"] for record in records],
        "execution": {
            "hostname": socket.gethostname(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "cuda_device": torch.cuda.get_device_name(0),
            "dtype_model": "bfloat16",
            "dtype_saved": "float32",
            "attention": "sdpa",
            "use_cache": False,
        },
        "models": {},
    }

    for label, model_path in MODEL_PATHS.items():
        output_path = output_dir / f"{label.lower()}_prompt_end_no_memory.pt"
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
        }
        del tensor, rows, model, model_tokenizer
        gc.collect()
        torch.cuda.empty_cache()

    metadata_path = output_dir / "extraction_metadata.json"
    if metadata_path.exists():
        existing_meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        existing_meta.setdefault("models", {}).update(metadata["models"])
        metadata_path.write_text(json.dumps(existing_meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Extraction validated: {metadata_path}", flush=True)


if __name__ == "__main__":
    main()
