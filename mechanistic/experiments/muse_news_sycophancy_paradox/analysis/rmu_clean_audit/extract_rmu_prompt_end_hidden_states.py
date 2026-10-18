#!/usr/bin/env python3
"""Extract prompt-end hidden states for RMU, with the same protocol as
privacy_collapse/persistbench_native/extract_prompt_end_hidden_states.py (same manifest, last
prompt token, all 29 hidden states, same dtype/attention/validation). Kept as a separate
script with its own output directory so the SatImp/SimNPO outputs are not touched.
"""
from __future__ import annotations

import gc
import hashlib
import json
import platform
import socket
import time
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

import os as _os; _ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), *['..']*5))
ROOT = Path(_ROOT)
NATIVE = ROOT / "mechanistic/privacy_collapse/persistbench_native"
MANIFEST = NATIVE / "manifests/native_sycophancy_200_v1.json"
HERE = Path(__file__).resolve().parent
OUTPUT_DIR = HERE / "representations"
EXPECTED_SHAPE = (200, 29, 3584)
MODEL_PATH = ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_rmu/checkpoint-459"
BASE_TOKENIZER_PATH = ROOT / "saves/finetune/muse_news_qwen25_7b_instruct_target"


def ids_sha(ids: list[int]) -> str:
    return hashlib.sha256(torch.tensor(ids, dtype=torch.int64).numpy().tobytes()).hexdigest()


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; submit via sbatch")

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = data["records"]
    if len(records) != 200:
        raise RuntimeError("Frozen native manifest does not contain 200 records")

    tokenizer = AutoTokenizer.from_pretrained(
        BASE_TOKENIZER_PATH, use_fast=True, trust_remote_code=True, local_files_only=True
    )
    canonical_ids = [record["prompt"]["effective_prompt_token_ids"] for record in records]
    for record, token_ids in zip(records, canonical_ids, strict=True):
        if ids_sha(token_ids) != record["prompt"]["effective_prompt_token_ids_sha256"]:
            raise RuntimeError(f"Prompt token SHA mismatch: {record['persistbench_id']}")
        if record["prompt"]["extraction_index"] != len(token_ids) - 1:
            raise RuntimeError(f"Extraction index mismatch: {record['persistbench_id']}")
        if token_ids[-1] == tokenizer.eos_token_id:
            raise RuntimeError(f"EOS prompt endpoint: {record['persistbench_id']}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "rmu_prompt_end.pt"

    base_vocab = tokenizer.get_vocab()
    model_tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH, use_fast=True, trust_remote_code=True, local_files_only=True
    )
    if model_tokenizer.get_vocab() != base_vocab:
        raise RuntimeError("Tokenizer vocabulary differs for RMU")

    print(f"Loading RMU: {MODEL_PATH}", flush=True)
    started = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        local_files_only=True,
        attn_implementation="sdpa",
    ).eval()
    model.requires_grad_(False)
    if model.config.num_hidden_layers != 28 or model.config.hidden_size != 3584:
        raise RuntimeError("Unexpected architecture for RMU")
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
            raise RuntimeError(f"Missing hidden states for RMU/{record['persistbench_id']}")
        activation = torch.stack(
            [state[0, -1].detach().to(device="cpu", dtype=torch.float32) for state in outputs.hidden_states]
        )
        if tuple(activation.shape) != (29, 3584) or not torch.isfinite(activation).all():
            raise RuntimeError(f"Invalid activation for RMU/{record['persistbench_id']}")
        rows.append(activation)
        if index == 1 or index % 20 == 0:
            print(f"RMU: {index}/200", flush=True)
        del outputs, activation, input_ids, attention_mask
    tensor = torch.stack(rows)
    if tuple(tensor.shape) != EXPECTED_SHAPE or tensor.dtype != torch.float32 or not torch.isfinite(tensor).all():
        raise RuntimeError(f"Invalid final tensor for RMU: {tuple(tensor.shape)}")
    torch.save(tensor, output_path)

    metadata = {
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "record_count": 200,
        "expected_shape": list(EXPECTED_SHAPE),
        "semantic_position": "last token of original effective chat-formatted prompt immediately before generation",
        "checkpoint": str(MODEL_PATH.relative_to(ROOT)),
        "tensor": str(output_path.relative_to(ROOT)),
        "shape": list(tensor.shape),
        "dtype": str(tensor.dtype),
        "runtime_seconds": time.time() - started,
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
    }
    (OUTPUT_DIR / "extraction_metadata_rmu.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Extraction validated: {output_path}", flush=True)
    del tensor, rows, model, model_tokenizer
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
