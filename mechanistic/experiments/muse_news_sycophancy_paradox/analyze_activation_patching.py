#!/usr/bin/env python3
"""Phase 9 analysis/plot (CPU-only): summarize + plot the activation-patching CSVs
produced by run_activation_patching.py for both directions.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BOOTSTRAP_N = 2000
SEED = 20260919


def bootstrap_mean_ci(values: np.ndarray, n: int = BOOTSTRAP_N, seed: int = SEED) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    if len(values) == 0:
        return float("nan"), float("nan"), float("nan")
    idx = rng.integers(0, len(values), size=(n, len(values)))
    resamples = values[idx].mean(axis=1)
    lo, hi = np.percentile(resamples, [2.5, 97.5])
    return float(values.mean()), float(lo), float(hi)

HERE = Path(__file__).resolve().parent
ANALYSIS_DIR = HERE / "analysis"
PLOT_DIR = HERE / "plots"
CONDITIONS_ORDER = ["unpatched", "patched_early_L0-6", "patched_early_mid_L7-13", "patched_mid_late_L14-20", "patched_late_L21-27"]
LABELS = {
    "unpatched": "unpatched",
    "patched_early_L0-6": "early\n(L0-6)",
    "patched_early_mid_L7-13": "early-mid\n(L7-13)",
    "patched_mid_late_L14-20": "mid-late\n(L14-20)",
    "patched_late_L21-27": "late\n(L21-27)",
}


def main() -> None:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, direction in zip(axes, ["unlearned_recipient", "base_recipient"]):
        path = ANALYSIS_DIR / f"activation_patching_{direction}.csv"
        if not path.exists():
            ax.set_title(f"{direction}: (not yet run)")
            continue
        df = pd.read_csv(path)
        df["condition"] = pd.Categorical(df["condition"], categories=CONDITIONS_ORDER, ordered=True)
        summary = df.groupby(["method", "group", "condition"], observed=True)["score"].agg(["mean", "count"]).reset_index()
        for method, style in zip(sorted(summary["method"].unique()), ("-", "--")):
            for group, color in zip(["SAFE_TO_FAILURE", "SAFE_TO_SAFE"], ("tab:red", "tab:blue")):
                d = summary[(summary.method == method) & (summary.group == group)].sort_values("condition")
                if len(d) == 0:
                    continue
                n = d["count"].iloc[0]
                ax.plot(
                    [LABELS[c] for c in d["condition"]], d["mean"], style, marker="o", color=color,
                    label=f"{method} {group} (n={n})",
                )
        ax.axhline(0, color="black", linewidth=0.8, linestyle=":")
        recipient = "unlearned model" if direction == "unlearned_recipient" else "BASE"
        donor = "BASE" if direction == "unlearned_recipient" else "unlearned model"
        ax.set_title(f"recipient={recipient}, donor={donor}")
        ax.set_xlabel("patched decoder-layer range")
        ax.tick_params(axis="x", rotation=0, labelsize=8)
        ax.legend(fontsize=7)
    axes[0].set_ylabel("score = mean_logprob(text_safe) - mean_logprob(text_alt)\n(under the recipient model, higher = more BASE-like/safe)")
    fig.suptitle(
        "Phase 9: MUSE-News sycophancy activation patching -- does injecting the donor's\n"
        "layer-range activations shift the recipient's preference toward the safe continuation?",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    out_path = PLOT_DIR / "activation_patching_score_by_range.png"
    fig.savefig(out_path, dpi=150)
    print(f"Wrote {out_path}")

    shift_rows = []
    for direction in ["unlearned_recipient", "base_recipient"]:
        path = ANALYSIS_DIR / f"activation_patching_{direction}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        print(f"\n=== {direction} ===")
        print(df.groupby(["method", "group", "condition"], observed=True)["score"].mean().round(3))

        # Per-example shift = score(patched_range) - score(unpatched), bootstrapped over examples.
        wide = df.pivot_table(index=["method", "group", "persistbench_id"], columns="condition", values="score").reset_index()
        for method in wide["method"].unique():
            for group in wide["group"].unique():
                sub = wide[(wide.method == method) & (wide.group == group)]
                if len(sub) == 0:
                    continue
                for cond in [c for c in CONDITIONS_ORDER if c != "unpatched"]:
                    if cond not in sub.columns:
                        continue
                    shift = (sub[cond] - sub["unpatched"]).dropna().to_numpy()
                    mean, lo, hi = bootstrap_mean_ci(shift)
                    shift_rows.append({
                        "direction": direction, "method": method, "group": group, "condition": cond,
                        "n": len(shift), "mean_shift": mean, "ci_lo": lo, "ci_hi": hi,
                    })
    shift_df = pd.DataFrame(shift_rows)
    shift_path = ANALYSIS_DIR / "activation_patching_shift_from_unpatched.csv"
    shift_df.to_csv(shift_path, index=False)
    print(f"\nWrote {shift_path}")
    print(shift_df[shift_df.condition.isin(["patched_mid_late_L14-20", "patched_late_L21-27"])].to_string(index=False))


if __name__ == "__main__":
    main()
