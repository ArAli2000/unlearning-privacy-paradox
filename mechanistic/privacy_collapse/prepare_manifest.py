#!/usr/bin/env python3
"""Freeze the model-independent 50-example PrivacyLens pilot manifest."""
from __future__ import annotations

import json
import random
from datetime import datetime, timezone

from common import CONFIG_PATH, DATA_PATH, MANIFEST_PATH, LEAKY, SAFE


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text())
    data = json.loads(DATA_PATH.read_text())
    names = [item["name"] for item in data]
    if len(names) != len(set(names)):
        raise RuntimeError("PrivacyLens source IDs are not unique")
    rng = random.Random(config["privacy_sample_seed"])
    selected = rng.sample(names, config["privacy_sample_size"])
    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "selection": {
            "source": str(DATA_PATH.relative_to(DATA_PATH.parents[2])),
            "source_count": len(data),
            "method": "python random.Random(seed).sample over source-order case IDs",
            "seed": config["privacy_sample_seed"],
            "sample_size": len(selected),
            "model_independent": True,
        },
        "answer_semantics": {"safe": SAFE, "leaky": LEAKY},
        "case_ids": selected,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {len(selected)} unique IDs to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
