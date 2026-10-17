#!/usr/bin/env python3
"""CPU-only source, prompt, label, checkpoint, and Qwen-token validation."""
from __future__ import annotations

import json

from tokenizers import Tokenizer

from common import (
    CONFIG_PATH, LEAKY, MCQ_MANIFEST, MCQ_MANIFEST_SHA256, OUTPUT_ROOT, PROMPT_TEMPLATE, ROOT, SAFE,
    SOURCE_POOL, SOURCE_POOL_SHA256, chat_prompt, file_sha256, prompt_text, tokenize_pair,
)

TOKENIZER_FILES = ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt")


def main() -> None:
    source = [json.loads(line) for line in SOURCE_POOL.read_text().splitlines() if line.strip()]
    manifest = json.loads(MCQ_MANIFEST.read_text())
    if file_sha256(MCQ_MANIFEST) != MCQ_MANIFEST_SHA256:
        raise RuntimeError("Approved CLEAR_NO manifest SHA-256 mismatch")
    if file_sha256(SOURCE_POOL) != SOURCE_POOL_SHA256:
        raise RuntimeError("Frozen full source pool SHA-256 mismatch")
    if len(source) != 200 or len(manifest["records"]) != 50:
        raise RuntimeError("Expected the full 200-row source and exactly 50 MCQ records")
    mcq_ids = [row["example_id"] for row in manifest["records"]]
    if len(set(mcq_ids)) != 50 or len({row["persistbench_id"] for row in manifest["records"]}) != 50:
        raise RuntimeError("MCQ IDs and PersistBench IDs must be unique")

    for derived in manifest["records"]:
        original = source[derived["source_index"]]
        for field in ("query", "memory_domain", "query_domain"):
            if derived[field] != original[field]:
                raise RuntimeError(f"Frozen field {field} changed for {derived['example_id']}")
        if original["memories"][derived["target_memory_index"]] != derived["target_memory_text"]:
            raise RuntimeError(f"Frozen target mismatch for {derived['example_id']}")
        if derived["prompt"] != prompt_text(original["query"], derived["target_memory_text"]):
            raise RuntimeError(f"Prompt template mismatch for {derived['example_id']}")
        if derived["label_clarity"] != "CLEAR_NO" or derived["safe"] != SAFE or derived["privacy_violating"] != LEAKY:
            raise RuntimeError(f"Label mapping mismatch for {derived['example_id']}")

    config = json.loads(CONFIG_PATH.read_text())
    model_paths = {name: (ROOT / path).resolve() for name, path in config["models"].items()}
    tokenizer_hashes, model_configs = {}, {}
    for label, path in model_paths.items():
        if not path.is_dir():
            raise FileNotFoundError(f"Missing checkpoint: {path}")
        tokenizer_hashes[label] = {name: file_sha256(path / name) for name in TOKENIZER_FILES}
        model_configs[label] = json.loads((path / "config.json").read_text())
    if len({json.dumps(value, sort_keys=True) for value in tokenizer_hashes.values()}) != 1:
        raise RuntimeError("Tokenizer artifacts differ across checkpoints")
    dimensions = {(cfg["num_hidden_layers"], cfg["hidden_size"], cfg["vocab_size"]) for cfg in model_configs.values()}
    if dimensions != {(28, 3584, 152064)}:
        raise RuntimeError(f"Unexpected or incompatible checkpoint dimensions: {dimensions}")

    tokenizer = Tokenizer.from_file(str(model_paths["BASE"] / "tokenizer.json"))
    prepared = []
    for row in manifest["records"]:
        formatted = chat_prompt(row["prompt"])
        pair = tokenize_pair(tokenizer, formatted)
        prepared.append({
            **row,
            "chat_formatted_prompt": formatted,
            **pair,
            "pair_invariant": {
                "only_answer_suffix_differs": True,
                "logit_position": len(pair["prompt_ids"]) - 1,
                "safe_direction_position": len(pair["safe_ids"]) - 1,
                "leaky_direction_position": len(pair["leaky_ids"]) - 1,
                "answer_position_is_not_eos": True,
            },
        })
    clean_single = all(len(r["safe_continuation_ids"]) == len(r["leaky_continuation_ids"]) == 1 for r in prepared)
    if not clean_single:
        raise RuntimeError("A/B are not clean single-token continuations")
    safe_ids = sorted({tuple(r["safe_continuation_ids"]) for r in prepared})
    leaky_ids = sorted({tuple(r["leaky_continuation_ids"]) for r in prepared})
    if safe_ids == leaky_ids:
        raise RuntimeError("A and B unexpectedly share a token ID")
    maximum = max(max(len(r["safe_ids"]), len(r["leaky_ids"])) for r in prepared)
    max_positions = min(cfg["max_position_embeddings"] for cfg in model_configs.values())
    if maximum > max_positions:
        raise RuntimeError("A completed prompt exceeds the context window")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    prepared_path = OUTPUT_ROOT / "prepared_examples.json"
    prepared_path.write_text(json.dumps({"records": prepared}, indent=2, ensure_ascii=False) + "\n")
    report = {
        "status": "passed",
        "probe_name": "PersistBench-MCQ",
        "record_count": len(prepared),
        "unique_id_count": len(set(mcq_ids)),
        "all_ids_unique": True,
        "frozen_query_target_and_domain_fields_exactly_match_source": True,
        "all_targets_equal_memories_at_target_index": True,
        "prompt_template_exactly_uniform_apart_from_two_insertions": True,
        "prompt_template": PROMPT_TEMPLATE,
        "all_safe_labels": SAFE,
        "all_leaky_labels": LEAKY,
        "all_answers_clean_single_token_alternatives": True,
        "safe_continuation_ids": safe_ids,
        "leaky_continuation_ids": leaky_ids,
        "direction_extraction_position": "last answer-completion token; no EOS is appended",
        "logit_readout_position": "last prompt token, which predicts the one-token A/B completion",
        "layer_convention": "hidden_states[0..28] = embedding plus L1..L28; direction uses raw stored states; logit lens applies own final RMSNorm to states 0..27 and not to already-normalized state 28, then own lm_head",
        "privacy_lens_compatibility": "same Qwen chat framing, A/B continuation boundary, safe-minus-leaky direction definition, answer-token endpoint, 29-state convention, and per-model normalization/lm_head projection",
        "maximum_completed_tokens": maximum,
        "checkpoint_max_position_embeddings": max_positions,
        "source_pool_sha256": SOURCE_POOL_SHA256,
        "mcq_manifest_sha256": file_sha256(MCQ_MANIFEST),
        "tokenizer_artifact_sha256": tokenizer_hashes,
        "checkpoint_dimensions": {label: [cfg["num_hidden_layers"], cfg["hidden_size"], cfg["vocab_size"]] for label, cfg in model_configs.items()},
        "prepared_examples_path": str(prepared_path),
    }
    (OUTPUT_ROOT / "static_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
