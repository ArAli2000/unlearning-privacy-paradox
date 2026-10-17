#!/usr/bin/env python3
"""Strict post-GPU schema/order validation."""
import json
import pandas as pd
import torch
from common import OUTPUT_ROOT


def main():
    ids = [r["example_id"] for r in json.loads((OUTPUT_ROOT / "prepared_examples.json").read_text())["records"]]
    for model in ("BASE", "SatImp", "SimNPO"):
        frame = pd.read_csv(OUTPUT_ROOT / "models" / model / "mcq_readout_per_example.csv")
        if len(frame) != 50 * 29 or frame.isna().any().any(): raise RuntimeError(f"Invalid readout rows for {model}")
        obj = torch.load(OUTPUT_ROOT / "models" / model / "persistbench_mcq_directions.pt", map_location="cpu", weights_only=True)
        if obj["example_ids"] != ids or tuple(obj["per_example_differences"].shape) != (50, 29, 3584): raise RuntimeError(f"Invalid directions for {model}")
        if tuple(obj["mean_direction"].shape) != (29, 3584) or not torch.isfinite(obj["mean_direction"]).all(): raise RuntimeError(f"Invalid mean direction for {model}")
    print("PersistBench-MCQ GPU outputs passed schema, order, shape, and finiteness checks.")


if __name__ == "__main__": main()
