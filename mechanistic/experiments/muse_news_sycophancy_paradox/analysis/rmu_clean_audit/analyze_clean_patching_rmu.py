#!/usr/bin/env python3
"""RMU replication of the clean-patching CPU-only analysis stage.

Identical statistics to
`../activation_patching_clean_audit/analyze_clean_patching.py`: per-example shift =
patched_score - unpatched_score, bootstrap 95% CI (2000 reps, same seed 20260919),
median, fraction-in-predicted-direction using the SAME sign convention coded there
(predicted_positive = direction == "unlearned_recipient", i.e. BASE-donor patching is
predicted to shift toward the safe continuation (+); method-donor patching into BASE is
predicted to shift toward the sycophantic continuation (-)). This convention was read
directly from the canonical script, not assumed.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PATCH_DIR = HERE / "activation_patching"
BOOTSTRAP_N = 2000
SEED = 20260919

CONDITIONS = ["patched_early_L0-6", "patched_early_mid_L7-13", "patched_mid_late_L14-20", "patched_late_L21-27"]
LABELS = {
    "patched_early_L0-6": "L0-6",
    "patched_early_mid_L7-13": "L7-13",
    "patched_mid_late_L14-20": "L14-20",
    "patched_late_L21-27": "L21-27",
}


def bootstrap_ci(values: np.ndarray, n: int = BOOTSTRAP_N, seed: int = SEED):
    rng = np.random.default_rng(seed)
    if len(values) == 0:
        return float("nan"), float("nan"), float("nan")
    idx = rng.integers(0, len(values), size=(n, len(values)))
    means = values[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(values.mean()), float(lo), float(hi)


def load_direction(direction: str) -> pd.DataFrame:
    path = PATCH_DIR / f"activation_patching_rmu_{direction}.csv"
    df = pd.read_csv(path)
    df["direction"] = direction
    return df


def per_example_shift_table(df: pd.DataFrame) -> pd.DataFrame:
    unpatched = df[df.condition == "unpatched"][["method", "direction", "persistbench_id", "group", "score"]]
    unpatched = unpatched.rename(columns={"score": "unpatched_score"})
    patched = df[df.condition != "unpatched"]
    merged = patched.merge(unpatched, on=["method", "direction", "persistbench_id", "group"])
    merged["shift"] = merged["score"] - merged["unpatched_score"]
    return merged


def main() -> None:
    df_fwd = load_direction("unlearned_recipient")
    df_rev = load_direction("base_recipient")
    df_all = pd.concat([df_fwd, df_rev], ignore_index=True)
    shifts = per_example_shift_table(df_all)
    shifts.to_csv(HERE / "rmu_per_example_shifts.csv", index=False)

    summary_rows = []
    for direction in ["unlearned_recipient", "base_recipient"]:
        predicted_positive = direction == "unlearned_recipient"
        for group in ["HIGH_CONFIDENCE_FAILURE", "SAFE_TO_SAFE_MATCHED_CONTROL"]:
            for cond in CONDITIONS:
                d = shifts[(shifts.direction == direction) & (shifts.method == "RMU") &
                           (shifts.group == group) & (shifts.condition == cond)]
                if len(d) == 0:
                    continue
                vals = d["shift"].to_numpy()
                mean, lo, hi = bootstrap_ci(vals)
                median = float(np.median(vals))
                if predicted_positive:
                    frac_predicted = float((vals > 0).mean())
                else:
                    frac_predicted = float((vals < 0).mean())
                summary_rows.append({
                    "direction": direction, "method": "RMU", "group": group, "layer_range": LABELS[cond],
                    "n": len(vals), "mean_shift": mean, "median_shift": median,
                    "ci_lo": lo, "ci_hi": hi, "frac_in_predicted_direction": frac_predicted,
                    "per_example_shifts": ";".join(f"{v:.4f}" for v in vals),
                })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(HERE / "rmu_clean_activation_patching_summary.csv", index=False)
    print(summary[summary.group == "HIGH_CONFIDENCE_FAILURE"][
        ["direction", "layer_range", "n", "mean_shift", "median_shift", "ci_lo", "ci_hi", "frac_in_predicted_direction"]
    ].to_string(index=False))


if __name__ == "__main__":
    main()
