#!/usr/bin/env python3
"""CPU-only memory-influence analysis: SAFE_TO_FAILURE vs SAFE_TO_SAFE contrast, with a control for generic unlearning drift.

delta_memory_M(i, layer) = h_with_memory_M(i, layer) - h_no_memory_M(i, layer)

for model M in {BASE, method} and example i, at the prompt-end position. The generic-drift control
is h_with_memory_method(i, layer) - h_with_memory_BASE(i, layer), which does not depend on memory removal.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NATIVE_DIR = ROOT / "mechanistic/privacy_collapse/persistbench_native"
WITH_MEMORY_DIR = NATIVE_DIR / "representations" / "sycophancy"
NO_MEMORY_DIR = HERE / "representations"
TRANSITIONS = HERE / "manifests" / "sycophancy_transition_groups.json"
NATIVE_MANIFEST = NATIVE_DIR / "manifests" / "native_sycophancy_200_v1.json"
OUT_DIR = HERE / "analysis"
NUM_LAYERS = 29
BOOTSTRAP_N = 2000
SEED = 20260919
METHODS = ["SatImp", "SimNPO"]


def load_tensor(path: Path) -> torch.Tensor:
    t = torch.load(path, map_location="cpu", weights_only=True)
    assert t.shape[1:] == (NUM_LAYERS, 3584), t.shape
    return t


def bootstrap_mean_ci(values: np.ndarray, n: int = BOOTSTRAP_N, seed: int = SEED) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    if len(values) == 0:
        return float("nan"), float("nan"), float("nan")
    idx = rng.integers(0, len(values), size=(n, len(values)))
    resamples = values[idx].mean(axis=1)
    lo, hi = np.percentile(resamples, [2.5, 97.5])
    return float(values.mean()), float(lo), float(hi)


def bootstrap_diff_ci(failure: np.ndarray, safe: np.ndarray, n: int = BOOTSTRAP_N, seed: int = SEED) -> tuple[float, float, float]:
    """Bootstrap CI for mean(failure) - mean(safe), resampling each group independently."""
    rng = np.random.default_rng(seed)
    if len(failure) == 0 or len(safe) == 0:
        return float("nan"), float("nan"), float("nan")
    idx_f = rng.integers(0, len(failure), size=(n, len(failure)))
    idx_s = rng.integers(0, len(safe), size=(n, len(safe)))
    diffs = failure[idx_f].mean(axis=1) - safe[idx_s].mean(axis=1)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(failure.mean() - safe.mean()), float(lo), float(hi)


def main() -> None:
    id_to_source_index = {
        rec["persistbench_id"]: rec["source_index"]
        for rec in json.loads(NATIVE_MANIFEST.read_text(encoding="utf-8"))["records"]
    }
    transitions = json.loads(TRANSITIONS.read_text(encoding="utf-8"))

    with_mem = {
        label: load_tensor(WITH_MEMORY_DIR / f"{label.lower()}_prompt_end.pt")
        for label in ["BASE", "SatImp", "SimNPO"]
    }
    no_mem = {
        label: load_tensor(NO_MEMORY_DIR / f"{label.lower()}_prompt_end_no_memory.pt")
        for label in ["BASE", "SatImp", "SimNPO"]
    }

    rows = []
    raw_arrays: dict[tuple, np.ndarray] = {}  # (method, group, quantity, evaluating_model) -> (N, 29)
    for method in METHODS:
        groups = transitions["methods"][method]["groups"]
        for group_name in ("SAFE_TO_SAFE", "SAFE_TO_FAILURE"):
            ids = [item["persistbench_id"] for item in groups[group_name]]
            idxs = [id_to_source_index[i] for i in ids]
            if len(idxs) == 0:
                continue
            idxs_t = torch.tensor(idxs, dtype=torch.long)

            for label in ("BASE", method):
                delta_mem = with_mem[label][idxs_t] - no_mem[label][idxs_t]  # (N, 29, 3584)
                norms = delta_mem.norm(dim=-1).numpy()  # (N, 29)
                raw_arrays[(method, group_name, "memory_influence_norm", label)] = norms
                for layer in range(NUM_LAYERS):
                    mean, lo, hi = bootstrap_mean_ci(norms[:, layer])
                    rows.append(
                        {
                            "method": method, "group": group_name, "quantity": "memory_influence_norm",
                            "evaluating_model": label, "layer": layer, "n": len(idxs),
                            "mean": mean, "ci_lo": lo, "ci_hi": hi,
                        }
                    )

            # Cosine between BASE's and the method's memory-influence vector, per example.
            delta_base = with_mem["BASE"][idxs_t] - no_mem["BASE"][idxs_t]
            delta_method = with_mem[method][idxs_t] - no_mem[method][idxs_t]
            cos = torch.nn.functional.cosine_similarity(delta_base, delta_method, dim=-1).numpy()  # (N, 29)
            raw_arrays[(method, group_name, "memory_influence_cosine_base_vs_method", method)] = cos
            for layer in range(NUM_LAYERS):
                mean, lo, hi = bootstrap_mean_ci(cos[:, layer])
                rows.append(
                    {
                        "method": method, "group": group_name, "quantity": "memory_influence_cosine_base_vs_method",
                        "evaluating_model": method, "layer": layer, "n": len(idxs),
                        "mean": mean, "ci_lo": lo, "ci_hi": hi,
                    }
                )

            # Generic-drift control: with-memory BASE-vs-method distance, independent of memory removal.
            drift = with_mem[method][idxs_t] - with_mem["BASE"][idxs_t]
            drift_norm = drift.norm(dim=-1).numpy()
            for layer in range(NUM_LAYERS):
                mean, lo, hi = bootstrap_mean_ci(drift_norm[:, layer])
                rows.append(
                    {
                        "method": method, "group": group_name, "quantity": "generic_unlearning_drift_norm",
                        "evaluating_model": method, "layer": layer, "n": len(idxs),
                        "mean": mean, "ci_lo": lo, "ci_hi": hi,
                    }
                )

    df = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "memory_influence_layer_metrics.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {out_path} ({len(df)} rows)")

    # SAFE_TO_FAILURE minus SAFE_TO_SAFE contrast, per layer, per quantity/model (Phase 11 style).
    diff_rows = []
    keys = {k[:1] + k[2:] for k in raw_arrays}  # (method, quantity, evaluating_model)
    for method, quantity, evaluating_model in sorted(keys):
        failure_arr = raw_arrays.get((method, "SAFE_TO_FAILURE", quantity, evaluating_model))
        safe_arr = raw_arrays.get((method, "SAFE_TO_SAFE", quantity, evaluating_model))
        if failure_arr is None or safe_arr is None:
            continue
        for layer in range(NUM_LAYERS):
            mean, lo, hi = bootstrap_diff_ci(failure_arr[:, layer], safe_arr[:, layer])
            diff_rows.append(
                {"method": method, "quantity": quantity, "evaluating_model": evaluating_model, "layer": layer,
                 "n_failure": failure_arr.shape[0], "n_safe": safe_arr.shape[0],
                 "mean_diff": mean, "ci_lo": lo, "ci_hi": hi}
            )
    diff_df = pd.DataFrame(diff_rows)
    diff_path = OUT_DIR / "memory_influence_safe_to_failure_vs_safe_to_safe_diff.csv"
    diff_df.to_csv(diff_path, index=False)
    print(f"Wrote {diff_path} ({len(diff_df)} rows)")

    # Compact printed summary at the previously-implicated L24-L28 late-layer band.
    summary = df[(df["layer"].between(24, 28))]
    print(summary.pivot_table(index=["method", "quantity", "evaluating_model", "layer"], values="mean").round(3))
    print()
    print("SAFE_TO_FAILURE - SAFE_TO_SAFE (positive = larger/more-rotated for failure rows):")
    print(diff_df[diff_df["layer"].between(20, 28)].pivot_table(
        index=["method", "quantity", "evaluating_model", "layer"], values="mean_diff"
    ).round(4))

    # Plots.
    plot_dir = HERE / "plots"
    plot_dir.mkdir(parents=True, exist_ok=True)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, method in zip(axes, METHODS):
        for label, color in zip(("BASE", method), ("tab:gray", "tab:orange")):
            for group_name, style in zip(("SAFE_TO_SAFE", "SAFE_TO_FAILURE"), ("--", "-")):
                d = df[(df.method == method) & (df.quantity == "memory_influence_norm")
                       & (df.evaluating_model == label) & (df.group == group_name)].sort_values("layer")
                if len(d) == 0:
                    continue
                n = d["n"].iloc[0]
                ax.plot(d["layer"], d["mean"], style, color=color, label=f"{label} {group_name} (n={n})", alpha=0.9)
        ax.set_title(f"{method}: ||memory-influence delta|| by layer")
        ax.set_xlabel("layer (0=embedding, 28=final)")
        ax.legend(fontsize=6.5, loc="upper left")
    axes[0].set_ylabel("||h(with memory) - h(no memory)||")
    fig.suptitle(
        "Phase 7: MUSE-News sycophancy memory-influence norm, BASE vs unlearned,\n"
        "SAFE→SAFE vs SAFE→FAILURE (Qwen2.5-7B-Instruct, legacy local-Qwen judge)", fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(plot_dir / "memory_influence_norm_by_layer.png", dpi=150)

    fig2, ax2 = plt.subplots(figsize=(6.5, 4.5))
    for method, color in zip(METHODS, ("tab:blue", "tab:red")):
        d = diff_df[(diff_df.method == method) & (diff_df.quantity == "memory_influence_cosine_base_vs_method")].sort_values("layer")
        ax2.plot(d["layer"], d["mean_diff"], color=color, label=f"{method} (n_fail={d['n_failure'].iloc[0]}, n_safe={d['n_safe'].iloc[0]})")
        ax2.fill_between(d["layer"], d["ci_lo"], d["ci_hi"], color=color, alpha=0.2)
    ax2.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax2.set_xlabel("layer (0=embedding, 28=final)")
    ax2.set_ylabel("SAFE→FAILURE minus SAFE→SAFE\ncos(delta_memory_BASE, delta_memory_method)")
    ax2.set_title("Phase 7/11: does unlearning rotate the memory-influence\ndirection more for rows that become failures?")
    ax2.legend(fontsize=8)
    fig2.tight_layout()
    fig2.savefig(plot_dir / "memory_influence_cosine_diff_by_layer.png", dpi=150)
    print(f"Wrote {plot_dir / 'memory_influence_norm_by_layer.png'}")
    print(f"Wrote {plot_dir / 'memory_influence_cosine_diff_by_layer.png'}")


if __name__ == "__main__":
    main()
