#!/usr/bin/env python3
"""Build supervisor-update figures strictly from checked-in result tables."""

from pathlib import Path
import json

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
}


def finish(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=220, bbox_inches="tight")
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    plt.close(fig)


def base_vs_unlearning(df):
    df = df[df.category == "cross_domain"].copy()
    tracks = [
        ("MUSE-News", "Qwen2.5-7B-Instruct", "News / Qwen"),
        ("MUSE-Books", "Llama-2-7B", "Books / Llama"),
        ("MUSE-Books", "Qwen2.5-7B-Instruct", "Books / Qwen"),
    ]
    methods = ["BASE", "RMU", "WGA", "SimNPO", "SatImp"]
    x = np.arange(len(tracks))
    width = 0.16
    fig, ax = plt.subplots(figsize=(10.5, 5.4))
    for i, method in enumerate(methods):
        values = []
        for dataset, model, _ in tracks:
            rows = df[(df.dataset == dataset) & (df.model == model)]
            values.append(rows.base_rate.iloc[0] if method == "BASE" else rows[rows.method == method].method_rate.iloc[0])
        bars = ax.bar(x + (i - 2) * width, values, width, label=method, color=COLORS[method])
        ax.bar_label(bars, fmt="%.1f", fontsize=8, padding=2)
    ax.set_xticks(x, [t[2] for t in tracks])
    ax.set_ylabel("Cross-domain failure rate, FR@1 (%)")
    ax.set_ylim(0, 90)
    ax.set_title("Independent Gemma-3 judge: BASE vs unlearning")
    ax.legend(ncol=5, frameon=False, loc="upper left")
    ax.grid(axis="y", alpha=0.2)
    finish(fig, "gemma_cross_domain_base_vs_unlearning")


def agreement_plot(data):
    keys = ["cross_domain", "sycophancy", "beneficial_memory_usage"]
    labels = ["Cross-domain", "Sycophancy", "Beneficial memory\nusage"]
    agreement = [100 * data["overall"][k]["exact_match_rate"] for k in keys]
    kappa = [100 * data["overall"][k]["cohens_kappa_unweighted"] for k in keys]
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    b1 = ax.bar(x - 0.19, agreement, 0.38, label="Exact agreement", color="#2563eb")
    b2 = ax.bar(x + 0.19, kappa, 0.38, label="Cohen's kappa (×100)", color="#94a3b8")
    ax.bar_label(b1, fmt="%.1f%%", padding=3)
    ax.bar_label(b2, labels=[f"{v/100:.4f}" for v in kappa], padding=3)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Percentage / kappa scaled to 0–100")
    ax.set_ylim(0, 75)
    ax.set_title("Qwen vs Gemma: partial, category-dependent agreement")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2)
    finish(fig, "qwen_vs_gemma_agreement")


def method_consistency(df):
    d = df[df.category == "cross_domain"]
    methods = ["RMU", "SimNPO", "WGA", "SatImp"]
    counts = {direction: [int(((d.method == m) & (d.direction == direction)).sum()) for m in methods]
              for direction in ["WORSE", "BETTER", "SAME"]}
    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    bottom = np.zeros(len(methods))
    for direction in ["WORSE", "BETTER", "SAME"]:
        vals = np.array(counts[direction])
        bars = ax.bar(methods, vals, bottom=bottom, label=direction.title(), color=COLORS[direction])
        for bar, val, base in zip(bars, vals, bottom):
            if val:
                ax.text(bar.get_x() + bar.get_width()/2, base + val/2, str(val), ha="center", va="center", color="white", fontweight="bold")
        bottom += vals
    ax.set_ylabel("Number of dataset/model tracks (out of 3)")
    ax.set_ylim(0, 3.35)
    ax.set_title("Cross-domain direction consistency under Gemma-3")
    ax.legend(frameon=False, ncol=3)
    ax.grid(axis="y", alpha=0.2)
    finish(fig, "gemma_method_consistency")


def transitions_plot(data):
    methods = ["SatImp", "SimNPO"]
    changed = [data[m]["n_reclassified"] for m in methods]
    total = [data[m]["n_total_checked"] for m in methods]
    pct = [100 * c / n for c, n in zip(changed, total)]
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    bars = ax.bar(methods, pct, color=[COLORS[m] for m in methods], width=0.55)
    ax.bar_label(bars, labels=[f"{c}/{n} ({p:.0f}%)" for c, n, p in zip(changed, total, pct)], padding=4)
    ax.set_ylabel("Rows assigned to a different transition group (%)")
    ax.set_ylim(0, 75)
    ax.set_title("Gemma changes many Qwen-defined sycophancy groups")
    ax.grid(axis="y", alpha=0.2)
    finish(fig, "mechanistic_transition_reclassification")


def main():
    df = pd.read_csv(ROOT / "gemma_only_exact_results.csv")
    agreement = json.loads((ROOT / "qwen_vs_gemma_agreement.json").read_text())
    transitions = json.loads((ROOT / "qwen_vs_gemma_mechanistic_transitions.json").read_text())
    base_vs_unlearning(df)
    agreement_plot(agreement)
    method_consistency(df)
    transitions_plot(transitions)


if __name__ == "__main__":
    main()
