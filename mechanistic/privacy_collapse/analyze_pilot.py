#!/usr/bin/env python3
"""CPU-only aggregation and plotting after the GPU extraction."""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import torch

from common import OUTPUT_ROOT


MODELS = ("BASE", "SatImp", "SimNPO")
DATASETS = ("privacy", "control")
STATE_LABELS = ["Embedding"] + [f"L{i}" for i in range(1, 29)]


def label_states(axis: plt.Axes) -> None:
    axis.set_xticks(range(len(STATE_LABELS)), STATE_LABELS)
    axis.set_xlabel("Residual-stream state")
    axis.tick_params(axis="x", labelrotation=60, labelsize=9)
    plt.setp(axis.get_xticklabels(), ha="right")


def cosine(a: torch.Tensor, b: torch.Tensor) -> float:
    denominator = torch.linalg.vector_norm(a) * torch.linalg.vector_norm(b)
    return math.nan if denominator <= 1e-12 else float(torch.dot(a, b) / denominator)


def main() -> None:
    frames = []
    directions = {}
    for model in MODELS:
        frames.append(pd.read_csv(OUTPUT_ROOT / "models" / model / "logit_lens_per_example.csv"))
        for dataset in DATASETS:
            directions[model, dataset] = torch.load(
                OUTPUT_ROOT / "models" / model / f"{dataset}_directions.pt", map_location="cpu", weights_only=True
            )
    per_example = pd.concat(frames, ignore_index=True)
    per_example.to_csv(OUTPUT_ROOT / "logit_lens_per_example_all_models.csv", index=False)
    metrics = [
        "safe_probability", "leaky_probability", "probability_difference", "safe_logprob", "leaky_logprob",
        "continuation_logprob_difference", "single_token_logit_difference"
    ]
    summary = per_example.groupby(["model", "dataset", "state_index", "state_label"])[metrics].agg(["mean", "median", "std", "count"])
    summary.columns = ["_".join(column) for column in summary.columns]
    summary = summary.reset_index()
    summary.to_csv(OUTPUT_ROOT / "logit_lens_summary.csv", index=False)

    vector_rows = []
    for dataset in DATASETS:
        base = directions["BASE", dataset]["mean_direction"].double()
        ids = directions["BASE", dataset]["example_ids"]
        for model in MODELS:
            obj = directions[model, dataset]
            if obj["example_ids"] != ids:
                raise RuntimeError(f"Direction example ordering mismatch: {model}/{dataset}")
            vector = obj["mean_direction"].double()
            for state_index, (base_layer, layer) in enumerate(zip(base, vector)):
                vector_rows.append({
                    "dataset": dataset, "model": model, "state_index": state_index,
                    "state_label": obj["state_labels"][state_index],
                    "direction_norm": float(torch.linalg.vector_norm(layer)),
                    "base_direction_norm": float(torch.linalg.vector_norm(base_layer)),
                    "cosine_to_base": 1.0 if model == "BASE" else cosine(base_layer, layer),
                })
    vectors = pd.DataFrame(vector_rows)
    vectors.to_csv(OUTPUT_ROOT / "direction_norms_and_cosines.csv", index=False)

    for dataset in DATASETS:
        fig, axis = plt.subplots(figsize=(10, 5.5))
        selected = summary[summary.dataset == dataset]
        for model in MODELS:
            values = selected[selected.model == model]
            axis.plot(values.state_index, values.probability_difference_mean, label=model)
        axis.axhline(0, color="black", linewidth=.8)
        axis.set(xlabel="Residual-stream state", ylabel="Mean P(safe) - P(leaky)", title=f"{dataset}: safe-minus-leaky logit-lens trajectory")
        axis.legend(); axis.grid(alpha=.25); fig.tight_layout()
        fig.savefig(OUTPUT_ROOT / f"{dataset}_safe_minus_leaky_probability.png", dpi=190); plt.close(fig)

        fig, axis = plt.subplots(figsize=(10, 5.5))
        selected = vectors[(vectors.dataset == dataset) & (vectors.model != "BASE")]
        for model in ("SatImp", "SimNPO"):
            values = selected[selected.model == model]
            axis.plot(values.state_index, values.cosine_to_base, label=f"BASE↔{model}")
        axis.axhline(0, color="black", linewidth=.8)
        axis.set(xlabel="Residual-stream state", ylabel="Cosine similarity", title=f"{dataset}: direction alignment to BASE")
        axis.legend(); axis.grid(alpha=.25); fig.tight_layout()
        fig.savefig(OUTPUT_ROOT / f"{dataset}_direction_cosine.png", dpi=190); plt.close(fig)

    # Presentation plots use explicit state names; the original figures above are kept.
    selected = summary[summary.dataset == "privacy"]
    fig, axis = plt.subplots(figsize=(10, 5.5))
    for model in MODELS:
        values = selected[selected.model == model]
        axis.plot(values.state_index, values.single_token_logit_difference_mean, label=model)
    axis.axhline(0, color="black", linewidth=.8)
    label_states(axis)
    axis.set_ylabel("Mean logit(safe) - logit(leaky)")
    axis.set_title("PrivacyLens: safe-minus-leaky logit-difference trajectory")
    axis.legend(); axis.grid(alpha=.25); fig.tight_layout()
    fig.savefig(OUTPUT_ROOT / "privacy_safe_minus_leaky_logit_difference.png", dpi=190); plt.close(fig)

    selected = summary[summary.dataset == "control"]
    for metric, ylabel, filename in (
        ("probability_difference_mean", "Mean P(correct) - P(incorrect)", "control_correct_minus_incorrect_probability.png"),
        ("single_token_logit_difference_mean", "Mean logit(correct) - logit(incorrect)", "control_correct_minus_incorrect_logit_difference.png"),
    ):
        fig, axis = plt.subplots(figsize=(10, 5.5))
        for model in MODELS:
            values = selected[selected.model == model]
            axis.plot(values.state_index, values[metric], label=model)
        axis.axhline(0, color="black", linewidth=.8)
        label_states(axis)
        axis.set_ylabel(ylabel)
        axis.set_title(f"Commonsense control: {filename.removeprefix('control_').removesuffix('.png').replace('_', ' ')}")
        axis.legend(); axis.grid(alpha=.25); fig.tight_layout()
        fig.savefig(OUTPUT_ROOT / filename, dpi=190); plt.close(fig)

    fig, axis = plt.subplots(figsize=(10, 5.5))
    for dataset, prefix in (("privacy", "Privacy"), ("control", "Commonsense")):
        selected = vectors[(vectors.dataset == dataset) & (vectors.model != "BASE")]
        for model in ("SatImp", "SimNPO"):
            values = selected[selected.model == model]
            axis.plot(values.state_index, values.cosine_to_base, label=f"{prefix} BASE↔{model}")
    axis.axhline(0, color="black", linewidth=.8)
    label_states(axis)
    axis.set_ylabel("Cosine similarity")
    axis.set_title("Direction alignment to BASE")
    axis.legend(ncol=2); axis.grid(alpha=.25); fig.tight_layout()
    fig.savefig(OUTPUT_ROOT / "combined_direction_alignment.png", dpi=190); plt.close(fig)

    report = {
        "status": "passed", "models": list(MODELS), "datasets": list(DATASETS),
        "per_example_rows": len(per_example), "summary_rows": len(summary), "vector_rows": len(vectors),
        "primary_direction": "mean(h_safe) - mean(h_leaky)",
        "presentation_plots": [
            "privacy_safe_minus_leaky_logit_difference.png",
            "control_correct_minus_incorrect_probability.png",
            "control_correct_minus_incorrect_logit_difference.png",
            "combined_direction_alignment.png",
        ],
    }
    (OUTPUT_ROOT / "analysis_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
