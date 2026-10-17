#!/usr/bin/env python3
"""Aggregate PersistBench-MCQ readouts and compare direction curves to PrivacyLens."""
from __future__ import annotations

import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import torch

from common import OUTPUT_ROOT, ROOT

MODELS = ("BASE", "SatImp", "SimNPO")
REPRESENTATIVE = (0, 8, 16, 20, 24, 28)
PRIVACY_ROOT = ROOT / "mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b"


def cosine(a, b):
    denominator = torch.linalg.vector_norm(a) * torch.linalg.vector_norm(b)
    return math.nan if denominator <= 1e-12 else float(torch.dot(a, b) / denominator)


def style(axis, ylabel, title):
    axis.axhline(0, color="black", linewidth=.8); axis.grid(alpha=.25)
    axis.set_xticks(range(29), ["Embedding"] + [f"L{i}" for i in range(1, 29)], rotation=60, ha="right")
    axis.set_xlabel("Residual-stream state"); axis.set_ylabel(ylabel); axis.set_title(title); axis.legend()


def main() -> None:
    frames, directions = [], {}
    for model in MODELS:
        frames.append(pd.read_csv(OUTPUT_ROOT / "models" / model / "mcq_readout_per_example.csv"))
        directions[model] = torch.load(OUTPUT_ROOT / "models" / model / "persistbench_mcq_directions.pt", map_location="cpu", weights_only=True)
    frame = pd.concat(frames, ignore_index=True)
    frame.to_csv(OUTPUT_ROOT / "mcq_readout_per_example_all_models.csv", index=False)
    metrics = ["logit_A", "logit_B", "safe_minus_leaky_logit_margin", "P_A", "P_B", "safe_decision_correct"]
    summary = frame.groupby(["model", "state_index", "state_label"])[metrics].agg(["mean", "median", "std", "count"])
    summary.columns = ["_".join(c) for c in summary.columns]; summary = summary.reset_index()
    summary.rename(columns={"safe_decision_correct_mean": "safe_decision_accuracy"}, inplace=True)
    summary.to_csv(OUTPUT_ROOT / "mcq_readout_summary.csv", index=False)
    rows = []
    base = directions["BASE"]["mean_direction"].double()
    for model in MODELS:
        if directions[model]["example_ids"] != directions["BASE"]["example_ids"]:
            raise RuntimeError("Direction example order mismatch")
        vector = directions[model]["mean_direction"].double()
        for index, (a, b) in enumerate(zip(base, vector)):
            rows.append({"model": model, "state_index": index, "state_label": directions[model]["state_labels"][index], "cosine_to_BASE": 1.0 if model == "BASE" else cosine(a, b)})
    cosines = pd.DataFrame(rows); cosines.to_csv(OUTPUT_ROOT / "direction_cosines_to_base.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    for model in MODELS:
        selected = summary[summary.model == model]; ax.plot(selected.state_index, selected.safe_minus_leaky_logit_margin_mean, label=model)
    style(ax, "Mean logit(B) - logit(A)", "PersistBench-MCQ: safe-minus-leaky logit trajectory")
    fig.tight_layout(); fig.savefig(OUTPUT_ROOT / "persistbench_mcq_safe_minus_leaky_logit.png", dpi=190); plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for model in ("SatImp", "SimNPO"):
        selected = cosines[cosines.model == model]; ax.plot(selected.state_index, selected.cosine_to_BASE, label=f"BASE↔{model}")
    style(ax, "Cosine similarity", "PersistBench-MCQ: direction cosine to BASE")
    fig.tight_layout(); fig.savefig(OUTPUT_ROOT / "persistbench_mcq_direction_cosine.png", dpi=190); plt.close(fig)

    privacy = pd.read_csv(PRIVACY_ROOT / "direction_norms_and_cosines.csv")
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for model in ("SatImp", "SimNPO"):
        p = privacy[(privacy.dataset == "privacy") & (privacy.model == model)]
        m = cosines[cosines.model == model]
        ax.plot(p.state_index, p.cosine_to_base, label=f"PrivacyLens BASE↔{model}")
        ax.plot(m.state_index, m.cosine_to_BASE, linestyle="--", label=f"PersistBench-MCQ BASE↔{model}")
    style(ax, "Cosine similarity", "Within-benchmark direction alignment to BASE")
    fig.tight_layout(); fig.savefig(OUTPUT_ROOT / "combined_privacylens_persistbench_mcq_direction_cosine.png", dpi=190); plt.close(fig)

    representative_rows = []
    for model in MODELS:
        direction = directions[model]["mean_direction"].double()
        for state_index in REPRESENTATIVE:
            selected = frame[(frame.model == model) & (frame.state_index == state_index)]
            representative_rows.append({
                "model": model, "state_index": state_index,
                "state_label": "embedding" if state_index == 0 else f"L{state_index}",
                "mean_safe_minus_leaky_logit_margin": float(selected.safe_minus_leaky_logit_margin.mean()),
                "privacy_direction_norm": float(torch.linalg.vector_norm(direction[state_index])),
                "cosine_to_BASE": float(cosines[(cosines.model == model) & (cosines.state_index == state_index)].cosine_to_BASE.iloc[0]),
            })
    pd.DataFrame(representative_rows).to_csv(OUTPUT_ROOT / "representative_layers.csv", index=False)
    final_layer = {}
    for model in MODELS:
        selected = frame[(frame.model == model) & (frame.state_index == 28)]
        count_b = int((selected.predicted_answer == "B").sum())
        count_a = int((selected.predicted_answer == "A").sum())
        final_layer[model] = {
            "safe_decision_accuracy": count_b / len(selected), "predicting_B": count_b, "predicting_A": count_a,
            "mean_B_minus_A_logit_margin": float(selected.safe_minus_leaky_logit_margin.mean()),
        }
    report = {
        "status": "passed", "primary_behavioral_readout": "logit(B)-logit(A)",
        "representative_layer_report": "representative_layers.csv", "final_layer": final_layer,
        "plots": ["persistbench_mcq_safe_minus_leaky_logit.png", "persistbench_mcq_direction_cosine.png", "combined_privacylens_persistbench_mcq_direction_cosine.png"],
        "cross_benchmark_raw_vector_comparison_performed": False,
    }
    (OUTPUT_ROOT / "analysis_validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
