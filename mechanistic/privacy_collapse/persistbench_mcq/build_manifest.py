#!/usr/bin/env python3
"""Build the deterministic frozen 50-example PersistBench-MCQ manifest."""
from __future__ import annotations

import json

from common import LEAKY, MCQ_MANIFEST, PROMPT_TEMPLATE, SAFE, SOURCE_MANIFEST, SOURCE_SHA256, file_sha256, prompt_text


def main() -> None:
    actual_hash = file_sha256(SOURCE_MANIFEST)
    if actual_hash != SOURCE_SHA256:
        raise RuntimeError(f"Frozen source hash mismatch: {actual_hash}")
    source = json.loads(SOURCE_MANIFEST.read_text())
    records = source["records"]
    if len(records) != 50:
        raise RuntimeError(f"Expected exactly 50 source records, found {len(records)}")

    derived = []
    for row in records:
        index = row["target_memory_index"]
        target = row["target_memory_text"]
        if row["memories"][index] != target:
            raise RuntimeError(f"Target index/text mismatch in {row['pair_id']}")
        derived.append({
            "final_order": row["final_order"],
            "example_id": row["pair_id"],
            "persistbench_id": row["persistbench_id"],
            "source_index": row["source_index"],
            "query": row["query"],
            "memories": row["memories"],
            "memory_domain": row["memory_domain"],
            "query_domain": row["query_domain"],
            "target_memory_index": index,
            "target_memory_text": target,
            "prompt": prompt_text(row["query"], target),
            "safe": SAFE,
            "leaky": LEAKY,
        })

    manifest = {
        "schema_version": 1,
        "name": "PersistBench-MCQ",
        "manifest_version": "persistbench-mcq-50-v1",
        "record_count": 50,
        "source_manifest": str(SOURCE_MANIFEST.relative_to(SOURCE_MANIFEST.parents[4])),
        "source_manifest_sha256": SOURCE_SHA256,
        "measurement": "explicit recognition of whether using/revealing a particular stored memory is privacy-appropriate in the current context.",
        "distinct_from_original": "Original PersistBench measures whether the model actually leaks contextual private information during open-ended generation.",
        "prompt_template": PROMPT_TEMPLATE,
        "safe_mapping": SAFE,
        "leaky_mapping": LEAKY,
        "records": derived,
    }
    MCQ_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MCQ_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {MCQ_MANIFEST}")
    print(f"sha256 {file_sha256(MCQ_MANIFEST)}")


if __name__ == "__main__":
    main()
