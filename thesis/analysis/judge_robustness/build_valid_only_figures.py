#!/usr/bin/env python3
"""Build valid-only vs. original FR@1 supervisor-update figures, strictly from
the checked-in gemma_valid_only_fr1_recompute.csv (itself produced by
recompute_valid_only.py, which reuses the repo's existing validity classifier
and PersistBench's failure_rates.py FR@K formula verbatim -- see that script's
docstring for exact provenance). Follows the same style conventions as
build_supervisor_update_figures.py (same palette, same finish() helper).
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "supervisor_update_2026-09-16"
OUT.mkdir(exist_ok=True)

COLORS = {
    "BASE": "#6b7280",
    "RMU": "#2563eb",
    "WGA": "#f59e0b",
    "SimNPO": "#10b981",
    "SatImp": "#8b5cf6",
    "WORSE": "#c2413b",
    "BETTER": "#2f855a",
    "SAME": "#718096",
    "ORIGINAL": "#94a3b8",
    "VALID_ONLY": "#2563eb",
    "EXCLUDED": "#c2413b",
}

TRACK_LABELS = {
    "MUSE-News": "News / Qwen",
    "MUSE-Books/Llama-2": "Books / Llama",
    "MUSE-Books/Qwen2.5": "Books / Qwen",
}
TRACK_ORDER = ["MUSE-News", "MUSE-Books/Llama-2", "MUSE-Books/Qwen2.5"]
METHOD_ORDER = ["RMU", "WGA", "SimNPO", "SatImp"]


def finish(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=220, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def fig_a_before_after(df):
    """A) Before vs after filtering FR@1 comparison, all 12 method conditions."""
    labels, orig_vals, valid_vals, excluded_flags = [], [], [], []
    for track in TRACK_ORDER:
        for method in METHOD_ORDER:
            row = df[(df.track == track) & (df.method == method)].iloc[0]
            labels.append(f"{TRACK_LABELS[track]}\n{method}")
            orig_vals.append(row.method_fr1_unfiltered)
            valid_vals.append(row.method_fr1_valid_only if row.evaluable else np.nan)
            excluded_flags.append(not row.evaluable)

    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(14.5, 5.6))
    b1 = ax.bar(x - width / 2, orig_vals, width, label="Original FR@1 (unfiltered)", color=COLORS["ORIGINAL"])
    ax.bar_label(b1, fmt="%.1f", fontsize=8, padding=2)

    NA_MARKER_HEIGHT = 8
    valid_vals_plot = [NA_MARKER_HEIGHT if excl else v for v, excl in zip(valid_vals, excluded_flags)]
    b2 = ax.bar(x + width / 2, valid_vals_plot, width, label="Valid-only FR@1", color=COLORS["VALID_ONLY"])
    for bar, v, excl in zip(b2, valid_vals, excluded_flags):
        if excl:
            bar.set_color(COLORS["EXCLUDED"])
            bar.set_hatch("//")
            bar.set_edgecolor("white")
            ax.text(bar.get_x() + bar.get_width() / 2, NA_MARKER_HEIGHT + 2, "N/A\n(0% valid)",
                    ha="center", va="bottom", fontsize=7.5, color=COLORS["EXCLUDED"], fontweight="bold")
        else:
            ax.text(bar.get_x() + bar.get_width() / 2, v + 1, f"{v:.1f}",
                    ha="center", va="bottom", fontsize=8)

    for i, track in enumerate(TRACK_ORDER):
        if i > 0:
            ax.axvline(i * 4 - 0.5, color="#e2e8f0", linewidth=1, zorder=0)

    ax.set_xticks(x, labels, fontsize=8.5)
    ax.set_ylabel("Cross-domain failure rate, FR@1 (%)")
    ax.set_ylim(0, 90)
    ax.set_title("Before vs. after generation-validity filtering (Gemma-3 judge, cross-domain FR@1)")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="y", alpha=0.2)
    finish(fig, "gemma_valid_only_before_after")


def fig_b_valid_only_base_vs_unlearning(df):
    """B) Valid-only BASE vs unlearning comparison (mirrors the original chart)."""
    methods = ["BASE", "RMU", "WGA", "SimNPO", "SatImp"]
    x = np.arange(len(TRACK_ORDER))
    width = 0.16
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    for i, method in enumerate(methods):
        values, excluded = [], []
        for track in TRACK_ORDER:
            row = df[(df.track == track) & (df.method == METHOD_ORDER[0])].iloc[0] if method == "BASE" else \
                df[(df.track == track) & (df.method == method)].iloc[0]
            if method == "BASE":
                values.append(row.base_fr1_valid_only)
                excluded.append(False)
            else:
                if row.evaluable:
                    values.append(row.method_fr1_valid_only)
                    excluded.append(False)
                else:
                    values.append(8)
                    excluded.append(True)
        bars = ax.bar(x + (i - 2) * width, values, width, label=method, color=COLORS[method])
        for bar, v, excl in zip(bars, values, excluded):
            if excl:
                bar.set_hatch("//")
                bar.set_edgecolor("white")
                bar.set_color(COLORS["EXCLUDED"])
                ax.text(bar.get_x() + bar.get_width() / 2, v + 2, "N/A\n(0%\nvalid)", ha="center", va="bottom",
                        fontsize=6, color=COLORS["EXCLUDED"], fontweight="bold")
            else:
                ax.text(bar.get_x() + bar.get_width() / 2, v + 1, f"{v:.1f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x, [TRACK_LABELS[t] for t in TRACK_ORDER])
    ax.set_ylabel("Cross-domain failure rate, FR@1 (%) — valid generations only")
    ax.set_ylim(0, 90)
    ax.set_title("Independent Gemma-3 judge, valid-only: BASE vs unlearning")
    ax.legend(ncol=5, frameon=False, loc="upper left")
    ax.grid(axis="y", alpha=0.2)
    finish(fig, "gemma_valid_only_base_vs_unlearning")


def fig_c_removed_cases(df):
    """C) Highlight removed/invalid cases: invalid generation count per condition."""
    labels, invalid_n, total_n = [], [], []
    for track in TRACK_ORDER:
        for method in METHOD_ORDER:
            row = df[(df.track == track) & (df.method == method)].iloc[0]
            labels.append(f"{TRACK_LABELS[track]}\n{method}")
            invalid_n.append(row.method_n - row.method_valid_n)
            total_n.append(row.method_n)

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(14.5, 5.2))
    colors = [COLORS["EXCLUDED"] if n == 200 else ("#f59e0b" if n > 0 else "#cbd5e1") for n in invalid_n]
    bars = ax.bar(x, invalid_n, color=colors, width=0.55)
    for bar, n, tot in zip(bars, invalid_n, total_n):
        if n > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, n + 3, f"{n}/{tot}",
                    ha="center", va="bottom", fontsize=8, fontweight="bold" if n == 200 else None)
    ax.set_xticks(x, labels, fontsize=8.5)
    ax.set_ylabel("Invalid generations (cross-domain, gen. index 0)")
    ax.set_ylim(0, 220)
    ax.set_title("Removed / invalid generations by condition (gibberish, empty, web- or tool-contaminated)")
    ax.grid(axis="y", alpha=0.2)
    finish(fig, "gemma_valid_only_removed_cases")


def main():
    df = pd.read_csv(ROOT / "gemma_valid_only_fr1_recompute.csv")
    df["evaluable"] = df["evaluable"].astype(str).str.lower().map({"true": True, "false": False})
    fig_a_before_after(df)
    fig_b_valid_only_base_vs_unlearning(df)
    fig_c_removed_cases(df)


if __name__ == "__main__":
    main()
