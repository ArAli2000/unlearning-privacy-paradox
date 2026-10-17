#!/usr/bin/env python3
"""CPU-only deterministic validation for PersistBench-MCQ CLEAR_NO 50 v1."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tokenizers import Tokenizer


ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "external/PersistBench/benchmark_samples/cross_domain.jsonl"
MANIFEST = ROOT / "mechanistic/privacy_collapse/persistbench_mcq/manifests/persistbench_mcq_clear_no_50_v1.json"
CONFIG = ROOT / "mechanistic/privacy_collapse/configs/muse_news_qwen25_7b.json"
REPORT = ROOT / "mechanistic/privacy_collapse/persistbench_mcq/analysis/mcq_clear_no_50_v1_static_validation.json"
TOKENIZER_FILES = ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def persistbench_id(memories: list[str], query: str) -> str:
    content = json.dumps({"memories": sorted(memories), "query": query}, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()


def encode(tokenizer, text: str) -> list[int]:
    value = tokenizer.encode(text, add_special_tokens=False)
    return value.ids if hasattr(value, "ids") else value


def main() -> None:
    source = [json.loads(line) for line in SOURCE.read_text().splitlines() if line.strip()]
    manifest = json.loads(MANIFEST.read_text())
    records = manifest["records"]
    if len(source) != 200 or len(records) != 50 or manifest["record_count"] != 50:
        raise RuntimeError("Expected full 200-row source and exactly 50 selected records")
    if len({r["example_id"] for r in records}) != 50 or len({r["persistbench_id"] for r in records}) != 50:
        raise RuntimeError("Example and PersistBench IDs must be unique")
    if len({(r["persistbench_id"], r["target_memory_index"]) for r in records}) != 50:
        raise RuntimeError("Memory/query pairs must be unique")
    if any(r["label_clarity"] != "CLEAR_NO" for r in records):
        raise RuntimeError("Every label_clarity must be CLEAR_NO")
    if any(r["safe"] != manifest["safe_mapping"] or r["safe"]["choice"] != "B" for r in records):
        raise RuntimeError("Every privacy-safe answer must be B / No")
    if any(r["privacy_violating"] != manifest["privacy_violating_mapping"] or r["privacy_violating"]["choice"] != "A" for r in records):
        raise RuntimeError("Every privacy-violating answer must be A / Yes")
    for expected_order, record in enumerate(records):
        if record["final_order"] != expected_order:
            raise RuntimeError("Final ordering is not contiguous")
        row = source[record["source_index"]]
        if record["persistbench_id"] != persistbench_id(row["memories"], row["query"]):
            raise RuntimeError(f"PersistBench ID mismatch: {record['example_id']}")
        for field in ("query", "memory_domain", "query_domain"):
            if record[field] != row[field]:
                raise RuntimeError(f"Source field {field} mismatch: {record['example_id']}")
        index = record["target_memory_index"]
        if not 0 <= index < len(row["memories"]) or record["target_memory_text"] != row["memories"][index]:
            raise RuntimeError(f"Target index/text mismatch: {record['example_id']}")
        expected_prompt = manifest["prompt_template"].format(target_memory_text=record["target_memory_text"], query=record["query"])
        if record["prompt"] != expected_prompt:
            raise RuntimeError(f"Prompt template mismatch: {record['example_id']}")
        if not record["selection_rationale"].strip():
            raise RuntimeError(f"Missing selection rationale: {record['example_id']}")

    config = json.loads(CONFIG.read_text())
    paths = {label: (ROOT / relative).resolve() for label, relative in config["models"].items()}
    hashes = {label: {name: sha256(path / name) for name in TOKENIZER_FILES} for label, path in paths.items()}
    if len({json.dumps(value, sort_keys=True) for value in hashes.values()}) != 1:
        raise RuntimeError("Tokenizer artifacts differ across checkpoints")
    tokenizer = Tokenizer.from_file(str(paths["BASE"] / "tokenizer.json"))
    safe_suffixes, violating_suffixes = set(), set()
    maximum_tokens = 0
    for record in records:
        formatted = f"<|im_start|>user\n{record['prompt']}<|im_end|>\n<|im_start|>assistant\n"
        prompt_ids = encode(tokenizer, formatted)
        safe_ids = encode(tokenizer, formatted + "B")
        violating_ids = encode(tokenizer, formatted + "A")
        if safe_ids[:len(prompt_ids)] != prompt_ids or violating_ids[:len(prompt_ids)] != prompt_ids:
            raise RuntimeError("Answer concatenation changed the prompt token prefix")
        safe_suffixes.add(tuple(safe_ids[len(prompt_ids):]))
        violating_suffixes.add(tuple(violating_ids[len(prompt_ids):]))
        maximum_tokens = max(maximum_tokens, len(safe_ids), len(violating_ids))
    if safe_suffixes != {(33,)} or violating_suffixes != {(32,)}:
        raise RuntimeError(f"A/B tokenization changed: A={violating_suffixes}, B={safe_suffixes}")

    report = {
        "status": "passed", "manifest": str(MANIFEST.relative_to(ROOT)), "manifest_sha256": sha256(MANIFEST),
        "source": str(SOURCE.relative_to(ROOT)), "source_sha256": sha256(SOURCE), "source_count": len(source),
        "record_count": len(records), "unique_example_ids": 50, "unique_persistbench_ids": 50,
        "unique_memory_query_pairs": 50, "all_label_clarity_CLEAR_NO": True,
        "all_target_indices_and_text_match_original_source": True, "all_queries_and_domains_match_original_source": True,
        "all_prompts_exactly_instantiate_one_template": True, "all_safe_answers": "B / No",
        "all_privacy_violating_answers": "A / Yes", "safe_B_continuation_ids": [[33]],
        "privacy_violating_A_continuation_ids": [[32]], "maximum_completed_tokens": maximum_tokens,
        "selection_behavioral_output_exclusion": manifest["model_output_exclusion"],
        "selection_was_design_only": True, "models_or_judges_run": False, "tokenizer_artifact_sha256": hashes,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
