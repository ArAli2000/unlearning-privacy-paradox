#!/usr/bin/env python3
"""CPU-only strict validation of completed pilot outputs."""
import json

import pandas as pd
import torch

from common import OUTPUT_ROOT


def main() -> None:
    prepared = json.loads((OUTPUT_ROOT / "prepared_examples.json").read_text())
    expected = {"privacy": 50, "control": 20}
    for model in ("BASE", "SatImp", "SimNPO"):
        csv_path = OUTPUT_ROOT / "models" / model / "logit_lens_per_example.csv"
        frame = pd.read_csv(csv_path)
        if len(frame) != (50 + 20) * 29:
            raise RuntimeError(f"Unexpected logit row count for {model}: {len(frame)}")
        if frame[["probability_difference", "continuation_logprob_difference"]].isna().any().any():
            raise RuntimeError(f"Missing primary logit metric for {model}")
        for dataset, count in expected.items():
            obj = torch.load(OUTPUT_ROOT / "models" / model / f"{dataset}_directions.pt", map_location="cpu", weights_only=True)
            if tuple(obj["per_example_differences"].shape) != (count, 29, 3584):
                raise RuntimeError(f"Bad per-example direction shape: {model}/{dataset}")
            if tuple(obj["mean_direction"].shape) != (29, 3584) or not torch.isfinite(obj["mean_direction"]).all():
                raise RuntimeError(f"Bad mean direction: {model}/{dataset}")
            if obj["example_ids"] != [row["example_id"] for row in prepared[dataset]]:
                raise RuntimeError(f"Example ordering mismatch: {model}/{dataset}")
    print("All GPU output schemas, shapes, finiteness checks, and example orderings passed.")


if __name__ == "__main__":
    main()
