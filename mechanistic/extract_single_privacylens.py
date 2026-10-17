#!/usr/bin/env python3
"""Extract last-prompt-token hidden states for one PrivacyLens sample."""

import argparse
import gc
import hashlib
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.eval_privacylens_mcq_local import construct_prompt, format_chat_prompt


DATA_PATH = REPO_ROOT / "external/privacy-collapse/benchmarks/privacylens/data/main_data.json"
MODEL_PATHS = {
    "BASE": Path("/storage/ukp/work/elshashay/open-unlearning/saves/finetune/tofu_Qwen2.5-7B-Instruct_full"),
    "RMU": Path("/storage/ukp/work/elshashay/open-unlearning/saves/unlearn/proper_qwen25_7b_rmu_from_tofufull_selectionproxy_savebest/checkpoint-104"),
    "WGA": Path("/storage/ukp/work/elshashay/open-unlearning/saves/unlearn/proper_qwen25_7b_wga_from_tofufull_selectionproxy_savebest/checkpoint-104"),
}


def load_sample(sample_id: str) -> dict:
    with DATA_PATH.open(encoding="utf-8") as handle:
        matches = [item for item in json.load(handle) if item.get("name") == sample_id]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {sample_id!r} sample, found {len(matches)}")
    return matches[0]


def build_prompt(item: dict, tokenizer) -> str:
    return format_chat_prompt(tokenizer, build_prompt_text(item))


def build_prompt_text(item: dict) -> str:
    seed = item["seed"]
    trajectory = item["trajectory"]
    return construct_prompt(
        prompt_type="naive",
        user_name=trajectory["user_name"],
        user_email=trajectory["user_email"],
        user_instruction=trajectory["user_instruction"],
        toolkits=trajectory["toolkits"],
        trajectory=trajectory["executable_trajectory"],
        data_type=seed["data_type"],
        data_subject=seed["data_subject"],
        transmission_principle=seed["transmission_principle"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-id", default="main1")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Defaults to mechanistic/outputs/<sample-id>/ under the repository root.",
    )
    args = parser.parse_args()

    if not args.sample_id or Path(args.sample_id).name != args.sample_id:
        raise ValueError("--sample-id must be a non-empty dataset ID, not a path")
    output_dir = args.output_dir or REPO_ROOT / "mechanistic/outputs" / args.sample_id

    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA GPU is required; run this script through the SLURM job.")
    for label, path in MODEL_PATHS.items():
        if not path.is_dir():
            raise FileNotFoundError(f"{label} model directory does not exist: {path}")

    # BASE supplies the one canonical tokenizer and tokenization used by every model.
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    sample = load_sample(args.sample_id)
    exact_prompt = build_prompt(sample, tokenizer)
    encoded = tokenizer(exact_prompt, return_tensors="pt")
    canonical_input_ids = encoded["input_ids"].contiguous()
    canonical_attention_mask = encoded["attention_mask"].contiguous()
    canonical_ids_list = canonical_input_ids[0].tolist()
    token_ids_sha256 = hashlib.sha256(
        canonical_input_ids.numpy().tobytes()
    ).hexdigest()

    output_dir.mkdir(parents=True, exist_ok=True)
    model_metadata = {}

    for label, model_path in MODEL_PATHS.items():
        print(f"Loading {label}: {model_path}", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
            local_files_only=True,
            attn_implementation="sdpa",
        )
        model.eval()

        device = model.get_input_embeddings().weight.device
        input_ids = canonical_input_ids.to(device)
        attention_mask = canonical_attention_mask.to(device)

        # Check the actual tensors supplied to each model against the canonical tokenization.
        if not torch.equal(input_ids.cpu(), canonical_input_ids):
            raise RuntimeError(f"{label} input IDs differ from the canonical BASE token IDs")
        if not torch.equal(attention_mask.cpu(), canonical_attention_mask):
            raise RuntimeError(f"{label} attention mask differs from the canonical mask")

        with torch.inference_mode():
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                output_hidden_states=True,
                use_cache=False,
                return_dict=True,
            )

        if outputs.hidden_states is None:
            raise RuntimeError(f"{label} did not return hidden states")
        activations = torch.stack(
            [hidden_state[0, -1].detach().to(device="cpu", dtype=torch.float32)
             for hidden_state in outputs.hidden_states]
        )
        expected_shape = (model.config.num_hidden_layers + 1, model.config.hidden_size)
        if tuple(activations.shape) != expected_shape:
            raise RuntimeError(
                f"{label} shape {tuple(activations.shape)} != expected {expected_shape}"
            )
        if not torch.isfinite(activations).all().item():
            raise RuntimeError(f"{label} activations contain NaN or Inf values")

        output_path = output_dir / f"{label.lower()}_last_prompt_token.pt"
        torch.save(activations, output_path)
        model_metadata[label] = {
            "model_path": str(model_path),
            "activation_path": str(output_path),
            "activation_shape": list(activations.shape),
            "activation_dtype": str(activations.dtype),
            "sequence_length": canonical_input_ids.shape[1],
            "hidden_size": model.config.hidden_size,
            "layer_count": model.config.num_hidden_layers,
            "saved_state_count": len(outputs.hidden_states),
            "token_ids_sha256": token_ids_sha256,
            "token_ids_identical_to_canonical": True,
        }
        print(f"Saved {label} activations {tuple(activations.shape)} to {output_path}", flush=True)

        del outputs, activations, input_ids, attention_mask, model
        gc.collect()
        torch.cuda.empty_cache()

    if len({entry["token_ids_sha256"] for entry in model_metadata.values()}) != 1:
        raise RuntimeError("Token ID verification failed across models")

    metadata = {
        "sample_id": args.sample_id,
        "dataset_path": str(DATA_PATH),
        "prompt_type": "naive",
        "exact_prompt": exact_prompt,
        "token_ids": canonical_ids_list,
        "decoded_tokens": tokenizer.convert_ids_to_tokens(canonical_ids_list),
        "sequence_length": canonical_input_ids.shape[1],
        "token_ids_sha256": token_ids_sha256,
        "models": model_metadata,
    }
    metadata_path = output_dir / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"Saved metadata to {metadata_path}", flush=True)


if __name__ == "__main__":
    main()
