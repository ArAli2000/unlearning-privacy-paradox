#!/usr/bin/env python3
"""CPU-only analysis of layer-wise BASE-vs-unlearned divergence in the teacher-forced preference for the
"safe" (BASE) over the "alt" (method) response, on SAFE_TO_FAILURE rows vs SAFE_TO_SAFE controls.

score_M(example, layer) = mean_logprob_M(text_safe, layer) - mean_logprob_M(text_alt, layer)
divergence(example, layer) = score_BASE(example, layer) - score_method(example, layer)

A positive divergence means BASE prefers its own text over the method's text by more than the method
prefers BASE's text over its own. The question is whether divergence, and the layer where it becomes
large, is bigger for SAFE_TO_FAILURE than for SAFE_TO_SAFE rows.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
IN_CSV = HERE / "representations" / "teacher_forced_layer_logprobs.csv"
OUT_DIR = HERE / "analysis"
PLOT_DIR = HERE / "plots"
BOOTSTRAP_N = 2000
SEED = 20260919
METHODS = ["SatImp", "SimNPO"]
GROUPS = ["SAFE_TO_SAFE", "SAFE_TO_FAILURE"]


def bootstrap_diff_ci(a: np.ndarray, b: np.ndarray, n: int = BOOTSTRAP_N, seed: int = SEED) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    if len(a) == 0 or len(b) == 0:
        return float("nan"), float("nan"), float("nan")
    ia = rng.integers(0, len(a), size=(n, len(a)))
    ib = rng.integers(0, len(b), size=(n, len(b)))
    d = a[ia].mean(axis=1) - b[ib].mean(axis=1)
    lo, hi = np.percentile(d, [2.5, 97.5])
    return float(a.mean() - b.mean()), float(lo), float(hi)


def bootstrap_mean_ci(values: np.ndarray, n: int = BOOTSTRAP_N, seed: int = SEED) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    if len(values) == 0:
        return float("nan"), float("nan"), float("nan")
    idx = rng.integers(0, len(values), size=(n, len(values)))
    resamples = values[idx].mean(axis=1)
    lo, hi = np.percentile(resamples, [2.5, 97.5])
    return float(values.mean()), float(lo), float(hi)


def main() -> None:
    df = pd.read_csv(IN_CSV)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    # score_M(example, layer) = logprob(text_safe) - logprob(text_alt), per evaluating model.
    wide = df.pivot_table(
        index=["method", "evaluating_model", "persistbench_id", "group", "layer"],
        columns="text_role", values="mean_logprob",
    ).reset_index()
    wide["score"] = wide["safe"] - wide["alt"]

    score_rows = []
    divergence_rows = []
    for method in METHODS:
        for group in GROUPS:
            sub = wide[(wide["method"] == method) & (wide["group"] == group)]
            for evaluating_model in ("BASE", method):
                sub_m = sub[sub["evaluating_model"] == evaluating_model]
                for layer in sorted(sub_m["layer"].unique()):
                    vals = sub_m[sub_m["layer"] == layer]["score"].to_numpy()
                    mean, lo, hi = bootstrap_mean_ci(vals)
                    score_rows.append(
                        {"method": method, "group": group, "evaluating_model": evaluating_model,
                         "layer": layer, "n": len(vals), "mean_score": mean, "ci_lo": lo, "ci_hi": hi}
                    )

            base_pivot = sub[sub["evaluating_model"] == "BASE"].set_index(["persistbench_id", "layer"])["score"]
            method_pivot = sub[sub["evaluating_model"] == method].set_index(["persistbench_id", "layer"])["score"]
            joined = pd.concat([base_pivot.rename("base_score"), method_pivot.rename("method_score")], axis=1).dropna()
            joined["divergence"] = joined["base_score"] - joined["method_score"]
            joined = joined.reset_index()
            for layer in sorted(joined["layer"].unique()):
                vals = joined[joined["layer"] == layer]["divergence"].to_numpy()
                mean, lo, hi = bootstrap_mean_ci(vals)
                divergence_rows.append(
                    {"method": method, "group": group, "layer": layer, "n": len(vals),
                     "mean_divergence": mean, "ci_lo": lo, "ci_hi": hi}
                )

    score_df = pd.DataFrame(score_rows)
    div_df = pd.DataFrame(divergence_rows)
    score_df.to_csv(OUT_DIR / "teacher_forced_score_by_layer.csv", index=False)
    div_df.to_csv(OUT_DIR / "teacher_forced_divergence_by_layer.csv", index=False)

    # Plot: divergence(layer) for SAFE_TO_FAILURE vs SAFE_TO_SAFE, one panel per method.
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, method in zip(axes, METHODS):
        for group, color in zip(GROUPS, ("tab:blue", "tab:red")):
            d = div_df[(div_df["method"] == method) & (div_df["group"] == group)].sort_values("layer")
            n = d["n"].iloc[0] if len(d) else 0
            ax.plot(d["layer"], d["mean_divergence"], label=f"{group} (n={n})", color=color)
            ax.fill_between(d["layer"], d["ci_lo"], d["ci_hi"], color=color, alpha=0.2)
        ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
        ax.set_title(f"MUSE-News sycophancy, BASE vs {method}\n(Qwen2.5-7B-Instruct, legacy local-Qwen judge)")
        ax.set_xlabel("layer (0=embedding, 28=final)")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("divergence(layer) = score_BASE - score_method\n(bootstrap 95% CI, n examples)")
    fig.suptitle(
        "Phase 8: teacher-forced BASE-vs-unlearned preference divergence between the\n"
        "actual BASE response and the actual unlearned response, generation index 0",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(PLOT_DIR / "teacher_forced_divergence_by_layer.png", dpi=150)
    print(f"Wrote {OUT_DIR / 'teacher_forced_score_by_layer.csv'}")
    print(f"Wrote {OUT_DIR / 'teacher_forced_divergence_by_layer.csv'}")
    print(f"Wrote {PLOT_DIR / 'teacher_forced_divergence_by_layer.png'}")

    late = div_df[div_df["layer"].between(20, 28)]
    print(late.pivot_table(index=["method", "group", "layer"], values="mean_divergence").round(3))

    # SAFE_TO_FAILURE - SAFE_TO_SAFE contrast on divergence itself (is the correlational
    # late-layer growth actually group-specific, or generic/shared -- Phase 11 style check).
    contrast_rows = []
    for method in METHODS:
        for layer in sorted(wide["layer"].unique()):
            base_l = wide[(wide.method == method) & (wide.evaluating_model == "BASE") & (wide.layer == layer)]
            meth_l = wide[(wide.method == method) & (wide.evaluating_model == method) & (wide.layer == layer)]
            merged = base_l.merge(meth_l, on=["persistbench_id", "group"], suffixes=("_base", "_method"))
            merged["divergence"] = merged["score_base"] - merged["score_method"]
            fail = merged[merged.group == "SAFE_TO_FAILURE"]["divergence"].to_numpy()
            safe = merged[merged.group == "SAFE_TO_SAFE"]["divergence"].to_numpy()
            mean, lo, hi = bootstrap_diff_ci(fail, safe)
            contrast_rows.append({
                "method": method, "layer": layer, "n_failure": len(fail), "n_safe": len(safe),
                "mean_diff_failure_minus_safe": mean, "ci_lo": lo, "ci_hi": hi,
            })
    contrast_df = pd.DataFrame(contrast_rows)
    contrast_path = OUT_DIR / "teacher_forced_divergence_safe_to_failure_vs_safe_to_safe_diff.csv"
    contrast_df.to_csv(contrast_path, index=False)
    print(f"\nWrote {contrast_path}")
    print(contrast_df[contrast_df.layer.between(20, 28)].to_string(index=False))


if __name__ == "__main__":
    main()
