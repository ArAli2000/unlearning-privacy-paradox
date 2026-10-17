#!/usr/bin/env python3
"""CPU-only analysis of the cleaned Phase-9 rerun: per-example shifts, bootstrap CIs,
medians, fraction-in-predicted-direction, per-example plots, and an old-vs-clean
comparison table. Reads only the clean CSVs written by run_activation_patching_clean.py
plus the ORIGINAL (unmodified) analysis/activation_patching_shift_from_unpatched.csv for
the comparison table. Writes only into this directory.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
ORIGINAL_SHIFT_CSV = EXP / "analysis" / "activation_patching_shift_from_unpatched.csv"
PLOT_DIR = HERE / "plots"
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
    path = HERE / f"activation_patching_clean_{direction}.csv"
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
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    df_fwd = load_direction("unlearned_recipient")
    df_rev = load_direction("base_recipient")
    df_all = pd.concat([df_fwd, df_rev], ignore_index=True)
    shifts = per_example_shift_table(df_all)
    shifts.to_csv(HERE / "clean_per_example_shifts.csv", index=False)

    # --- A. Clean aggregate results with bootstrap CIs, medians, fraction-in-predicted-direction ---
    summary_rows = []
    for direction in ["unlearned_recipient", "base_recipient"]:
        # predicted sign: forward (donor=BASE) -> positive shift = more safe (expected +).
        # reverse (donor=method) -> negative shift = less safe (expected -).
        predicted_positive = direction == "unlearned_recipient"
        for method in sorted(shifts.method.unique()):
            for group in ["HIGH_CONFIDENCE_FAILURE", "SAFE_TO_SAFE_MATCHED_CONTROL"]:
                for cond in CONDITIONS:
                    d = shifts[(shifts.direction == direction) & (shifts.method == method) &
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
                        "direction": direction, "method": method, "group": group, "layer_range": LABELS[cond],
                        "n": len(vals), "mean_shift": mean, "median_shift": median,
                        "ci_lo": lo, "ci_hi": hi, "frac_in_predicted_direction": frac_predicted,
                        "per_example_shifts": ";".join(f"{v:.4f}" for v in vals),
                    })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(HERE / "clean_activation_patching_summary.csv", index=False)

    # --- Old vs clean comparison (HIGH_CONFIDENCE_FAILURE / clean vs SAFE_TO_FAILURE / old-noisy) ---
    old = pd.read_csv(ORIGINAL_SHIFT_CSV)
    old = old[old.group == "SAFE_TO_FAILURE"].copy()
    old["layer_range"] = old["condition"].map(LABELS)
    comp_rows = []
    for direction in ["unlearned_recipient", "base_recipient"]:
        for method in sorted(shifts.method.unique()):
            for lr in LABELS.values():
                o = old[(old.direction == direction) & (old.method == method) & (old.layer_range == lr)]
                c = summary[(summary.direction == direction) & (summary.method == method) &
                            (summary.group == "HIGH_CONFIDENCE_FAILURE") & (summary.layer_range == lr)]
                if len(o) == 0 or len(c) == 0:
                    continue
                comp_rows.append({
                    "direction": direction, "method": method, "layer_range": lr,
                    "old_n": int(o["n"].iloc[0]), "old_mean_shift": float(o["mean_shift"].iloc[0]),
                    "old_ci_lo": float(o["ci_lo"].iloc[0]), "old_ci_hi": float(o["ci_hi"].iloc[0]),
                    "clean_n": int(c["n"].iloc[0]), "clean_mean_shift": float(c["mean_shift"].iloc[0]),
                    "clean_ci_lo": float(c["ci_lo"].iloc[0]), "clean_ci_hi": float(c["ci_hi"].iloc[0]),
                })
    comparison = pd.DataFrame(comp_rows)
    comparison.to_csv(HERE / "old_vs_clean_comparison.csv", index=False)

    # --- Per-example plots (points, not just means) ---
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), sharex=True)
    for row, direction in enumerate(["unlearned_recipient", "base_recipient"]):
        for col, method in enumerate(sorted(shifts.method.unique())):
            ax = axes[row, col]
            for group, color, marker in [
                ("HIGH_CONFIDENCE_FAILURE", "tab:red", "o"),
                ("SAFE_TO_SAFE_MATCHED_CONTROL", "tab:blue", "s"),
            ]:
                d = shifts[(shifts.direction == direction) & (shifts.method == method) & (shifts.group == group)]
                if len(d) == 0:
                    continue
                for i, cond in enumerate(CONDITIONS):
                    dd = d[d.condition == cond]
                    x = np.full(len(dd), i) + (0.08 if group.startswith("SAFE_TO_SAFE") else -0.08)
                    ax.scatter(x, dd["shift"], color=color, marker=marker, alpha=0.75, s=40,
                               label=f"{group} (n={dd['persistbench_id'].nunique()})" if i == 0 else None)
                    if len(dd) > 0:
                        ax.plot([i - 0.2, i + 0.2], [dd["shift"].mean()] * 2, color=color, linewidth=2)
            ax.axhline(0, color="black", linewidth=0.8, linestyle=":")
            ax.set_xticks(range(len(CONDITIONS)))
            ax.set_xticklabels([LABELS[c] for c in CONDITIONS])
            recipient = "unlearned" if direction == "unlearned_recipient" else "BASE"
            donor = "BASE" if direction == "unlearned_recipient" else "unlearned"
            ax.set_title(f"{method}: donor={donor} -> recipient={recipient}", fontsize=9)
            if col == 0:
                ax.set_ylabel("patch shift (patched - unpatched score)")
            if row == 0 and col == 0:
                ax.legend(fontsize=7, loc="best")
    fig.suptitle(
        "Cleaned Phase-9 rerun: per-example patch shifts\n"
        "(HIGH_CONFIDENCE_FAILURE only, vs. matched SAFE_TO_SAFE controls) -- MUSE-News sycophancy, Qwen2.5-7B",
        fontsize=11,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(PLOT_DIR / "clean_per_example_shifts.png", dpi=150)
    print(f"Wrote {PLOT_DIR / 'clean_per_example_shifts.png'}")

    # --- Old vs clean comparison plot ---
    fig2, axes2 = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, direction in zip(axes2, ["unlearned_recipient", "base_recipient"]):
        d = comparison[comparison.direction == direction]
        x = np.arange(len(CONDITIONS))
        width = 0.18
        for i, method in enumerate(sorted(d.method.unique())):
            dm = d[d.method == method].set_index("layer_range").reindex(LABELS.values())
            offset = (i - 0.5) * width * 2
            ax.errorbar(x + offset - width / 2, dm["old_mean_shift"],
                        yerr=[dm["old_mean_shift"] - dm["old_ci_lo"], dm["old_ci_hi"] - dm["old_mean_shift"]],
                        fmt="o", color="gray", label=f"{method} old (noisy n={dm['old_n'].iloc[0] if len(dm) else '?'})" if i == 0 else None, alpha=0.7)
            ax.errorbar(x + offset + width / 2, dm["clean_mean_shift"],
                        yerr=[dm["clean_mean_shift"] - dm["clean_ci_lo"], dm["clean_ci_hi"] - dm["clean_mean_shift"]],
                        fmt="s", color="tab:red" if method == "SatImp" else "tab:orange",
                        label=f"{method} clean (n={dm['clean_n'].iloc[0] if len(dm) else '?'})")
        ax.axhline(0, color="black", linewidth=0.8, linestyle=":")
        ax.set_xticks(x)
        ax.set_xticklabels(LABELS.values())
        ax.set_title(f"direction={direction}")
        ax.legend(fontsize=7)
    axes2[0].set_ylabel("mean patch shift (bootstrap 95% CI)")
    fig2.suptitle("Original noisy selection vs. cleaned HIGH_CONFIDENCE_FAILURE selection", fontsize=11)
    fig2.tight_layout(rect=(0, 0, 1, 0.92))
    fig2.savefig(PLOT_DIR / "old_vs_clean_comparison.png", dpi=150)
    print(f"Wrote {PLOT_DIR / 'old_vs_clean_comparison.png'}")

    print("\n=== Clean summary (HIGH_CONFIDENCE_FAILURE) ===")
    print(summary[summary.group == "HIGH_CONFIDENCE_FAILURE"][
        ["direction", "method", "layer_range", "n", "mean_shift", "median_shift", "ci_lo", "ci_hi", "frac_in_predicted_direction"]
    ].to_string(index=False))
    print("\n=== Old vs clean comparison ===")
    print(comparison.to_string(index=False))


if __name__ == "__main__":
    main()
