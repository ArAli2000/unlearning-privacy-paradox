#!/usr/bin/env python3
"""CPU-only validation and prompt/token provenance generation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tokenizers import Tokenizer

from common import (
    COMMONSENSE,
    CONFIG_PATH,
    DATA_PATH,
    LEAKY,
    MANIFEST_PATH,
    OUTPUT_ROOT,
    ROOT,
    SAFE,
    chat_prompt,
    control_prompt_text,
    privacy_prompt_text,
    tokenize_pair,
)


TOKENIZER_FILES = ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepared_record(tokenizer, example_id: str, dataset: str, raw_prompt: str) -> dict:
    formatted = chat_prompt(tokenizer, raw_prompt)
    pair = tokenize_pair(tokenizer, formatted, SAFE["choice"], LEAKY["choice"])
    return {
        "example_id": example_id,
        "dataset": dataset,
        "raw_prompt": raw_prompt,
        "chat_formatted_prompt": formatted,
        "safe": {**SAFE, "continuation_text": SAFE["choice"], "continuation_ids": pair["safe_continuation_ids"]},
        "leaky": {**LEAKY, "continuation_text": LEAKY["choice"], "continuation_ids": pair["leaky_continuation_ids"]},
        **pair,
        "pair_invariant": {
            "shared_prefix_length": len(pair["prompt_ids"]),
            "safe_suffix_length": len(pair["safe_continuation_ids"]),
            "leaky_suffix_length": len(pair["leaky_continuation_ids"]),
            "only_answer_suffix_differs": True,
            "direction_position_safe": len(pair["safe_ids"]) - 1,
            "direction_position_leaky": len(pair["leaky_ids"]) - 1,
            "logit_lens_initial_position": len(pair["prompt_ids"]) - 1,
        },
        "label_swap_ready": {
            "semantic_labels_stored_separately_from_literal_choices": True,
            "shared_prompt_ids_stored": True,
            "both_continuation_ids_stored": True,
        },
    }


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    manifest = json.loads(MANIFEST_PATH.read_text())
    ids = manifest["case_ids"]
    if len(ids) != 50 or len(set(ids)) != 50:
        raise RuntimeError("Frozen manifest must contain exactly 50 unique IDs")

    model_paths = {name: (ROOT / path).resolve() for name, path in config["models"].items()}
    hashes = {}
    model_configs = {}
    for label, path in model_paths.items():
        if not path.is_dir():
            raise FileNotFoundError(f"Missing checkpoint: {path}")
        hashes[label] = {name: file_hash(path / name) for name in TOKENIZER_FILES}
        model_configs[label] = json.loads((path / "config.json").read_text())
    if len({json.dumps(value, sort_keys=True) for value in hashes.values()}) != 1:
        raise RuntimeError("Tokenizer artifacts differ across checkpoints")
    vocab_sizes = {value["vocab_size"] for value in model_configs.values()}
    architectures = {tuple(value["architectures"]) for value in model_configs.values()}
    dimensions = {(value["num_hidden_layers"], value["hidden_size"]) for value in model_configs.values()}
    if len(vocab_sizes) != 1 or len(architectures) != 1 or len(dimensions) != 1:
        raise RuntimeError("Checkpoint architecture/vocabulary incompatibility")

    tokenizer = Tokenizer.from_file(str(model_paths["BASE"] / "tokenizer.json"))
    source = json.loads(DATA_PATH.read_text())
    by_id = {item["name"]: item for item in source}
    if any(case_id not in by_id for case_id in ids):
        raise RuntimeError("Manifest contains an unknown PrivacyLens ID")

    privacy = [prepared_record(tokenizer, case_id, "privacy_lens", privacy_prompt_text(by_id[case_id])) for case_id in ids]
    control = [
        prepared_record(tokenizer, f"commonsense_{index:02d}", "binary_commonsense_answer_selection", control_prompt_text(question))
        for index, (question, correct) in enumerate(COMMONSENSE, 1)
    ]
    if any(correct != "B" for _, correct in COMMONSENSE):
        raise RuntimeError("Released control semantics changed: expected B to be the correct alternative")
    all_records = privacy + control
    clean_single = all(len(r["safe_continuation_ids"]) == len(r["leaky_continuation_ids"]) == 1 for r in all_records)
    maximum_prompt_tokens = max(len(r["prompt_ids"]) for r in all_records)
    maximum_completed_tokens = max(max(len(r["safe_ids"]), len(r["leaky_ids"])) for r in all_records)
    max_positions = min(value["max_position_embeddings"] for value in model_configs.values())
    if maximum_completed_tokens > max_positions:
        raise RuntimeError("A prepared example exceeds the checkpoint context window")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    prepared_path = OUTPUT_ROOT / "prepared_examples.json"
    prepared_path.write_text(json.dumps({"privacy": privacy, "control": control}, indent=2) + "\n")
    report = {
        "status": "passed",
        "privacy_count": len(privacy),
        "privacy_unique_ids": len(set(ids)),
        "control_count": len(control),
        "safe_mapping": SAFE,
        "leaky_mapping": LEAKY,
        "all_pairs_preserve_exact_prompt_prefix": True,
        "all_answers_clean_single_token_alternatives": clean_single,
        "maximum_prompt_tokens": maximum_prompt_tokens,
        "maximum_completed_tokens": maximum_completed_tokens,
        "checkpoint_max_position_embeddings": max_positions,
        "safe_continuation_ids": sorted({tuple(r["safe_continuation_ids"]) for r in all_records}),
        "leaky_continuation_ids": sorted({tuple(r["leaky_continuation_ids"]) for r in all_records}),
        "tokenizer_artifact_sha256": hashes,
        "checkpoint_vocab_sizes": {k: v["vocab_size"] for k, v in model_configs.items()},
        "checkpoint_dimensions": {k: [v["num_hidden_layers"], v["hidden_size"]] for k, v in model_configs.items()},
        "prepared_examples_path": str(prepared_path),
        "qwen_source_normalization_note": (
            "Installed transformers Qwen2Model.forward appends pre-block residual states, then applies self.norm "
            "and appends the final normalized state. Extraction applies model.model.norm to hidden_states[:-1] "
            "for logit lens and uses hidden_states[-1] directly, preventing double normalization."
        ),
        "control_source_note": (
            "20 intended binary commonsense questions from upstream steering_task_vector.py; restored the "
            "missing comma between released items 5 and 6, which otherwise concatenates them into 19 strings."
        ),
    }
    (OUTPUT_ROOT / "static_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    schema = {
        "logit_lens_per_example.csv": [
            "model", "dataset", "example_id", "state_index", "state_label",
            "safe_semantic_label", "leaky_semantic_label", "safe_continuation_ids", "leaky_continuation_ids",
            "safe_probability", "leaky_probability", "probability_difference", "safe_logprob", "leaky_logprob",
            "continuation_logprob_difference", "single_token_logit_difference", "safe_token_logits",
            "leaky_token_logits", "safe_token_ranks", "leaky_token_ranks"
        ],
        "directions.pt": {
            "keys": ["model", "dataset", "example_ids", "definition", "per_example_differences", "mean_direction", "direction_norms", "state_labels", "answer_position"],
            "per_example_differences": {"privacy": [50, 29, 3584], "control": [20, 29, 3584]},
            "mean_direction": [29, 3584], "direction_norms": [29]
        },
        "logit_lens_summary.csv": {
            "group_by": ["model", "dataset", "state_index", "state_label"],
            "statistics": ["mean", "median", "std", "count"]
        },
        "direction_norms_and_cosines.csv": [
            "dataset", "model", "state_index", "state_label", "direction_norm", "base_direction_norm", "cosine_to_base"
        ]
    }
    (OUTPUT_ROOT / "output_schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
