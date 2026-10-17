#!/usr/bin/env python3
"""Compare extracted representation drift for two PrivacyLens samples on CPU."""

import argparse
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS_ROOT = REPO_ROOT / "mechanistic/outputs"
EXPECTED_SHAPE = (29, 3584)
NEAR_ZERO_NORM = 1e-12


def validate_sample_id(sample_id: str) -> None:
    if not sample_id or Path(sample_id).name != sample_id:
        raise ValueError("Sample IDs must be non-empty dataset IDs, not paths")


def load_sample(sample_id: str) -> dict[str, torch.Tensor]:
    sample_dir = OUTPUTS_ROOT / sample_id
    states = {}
    for model_name in ("base", "rmu", "wga"):
        path = sample_dir / f"{model_name}_last_prompt_token.pt"
        tensor = torch.load(path, map_location="cpu", weights_only=True)
        if not isinstance(tensor, torch.Tensor):
            raise TypeError(f"Expected a tensor in {path}, got {type(tensor).__name__}")
        if tuple(tensor.shape) != EXPECTED_SHAPE:
            raise ValueError(f"Expected {EXPECTED_SHAPE} in {path}, got {tuple(tensor.shape)}")
        if not torch.isfinite(tensor).all().item():
            raise ValueError(f"Non-finite values found in {path}")
        states[model_name] = tensor.to(dtype=torch.float64)
    return states


def safe_ratio(numerator: float, denominator: float) -> float:
    return math.nan if denominator <= NEAR_ZERO_NORM else numerator / denominator


def safe_cosine(left: torch.Tensor, right: torch.Tensor) -> float:
    left_norm = torch.linalg.vector_norm(left).item()
    right_norm = torch.linalg.vector_norm(right).item()
    if left_norm <= NEAR_ZERO_NORM or right_norm <= NEAR_ZERO_NORM:
        return math.nan
    return (torch.dot(left, right) / (left_norm * right_norm)).item()


def calculate(
    stable: dict[str, torch.Tensor], degraded: dict[str, torch.Tensor]
) -> tuple[list[dict], torch.Tensor]:
    rows = []
    contrast_vectors = []
    for index in range(EXPECTED_SHAPE[0]):
        stable_base = stable["base"][index]
        degraded_base = degraded["base"][index]
        stable_delta_rmu = stable["rmu"][index] - stable_base
        degraded_delta_rmu = degraded["rmu"][index] - degraded_base
        stable_delta_wga = stable["wga"][index] - stable_base
        degraded_delta_wga = degraded["wga"][index] - degraded_base
        contrast = degraded_delta_rmu - stable_delta_rmu
        contrast_vectors.append(contrast.to(dtype=torch.float32))

        stable_base_norm = torch.linalg.vector_norm(stable_base).item()
        degraded_base_norm = torch.linalg.vector_norm(degraded_base).item()
        stable_rmu_norm = torch.linalg.vector_norm(stable_delta_rmu).item()
        degraded_rmu_norm = torch.linalg.vector_norm(degraded_delta_rmu).item()
        stable_wga_norm = torch.linalg.vector_norm(stable_delta_wga).item()
        degraded_wga_norm = torch.linalg.vector_norm(degraded_delta_wga).item()
        contrast_norm = torch.linalg.vector_norm(contrast).item()
        mean_rmu_delta_norm = 0.5 * (stable_rmu_norm + degraded_rmu_norm)

        rows.append(
            {
                "layer": "Embedding" if index == 0 else f"L{index}",
                "rmu_relative_drift_stable": safe_ratio(stable_rmu_norm, stable_base_norm),
                "rmu_relative_drift_degraded": safe_ratio(degraded_rmu_norm, degraded_base_norm),
                "wga_relative_drift_stable": safe_ratio(stable_wga_norm, stable_base_norm),
                "wga_relative_drift_degraded": safe_ratio(degraded_wga_norm, degraded_base_norm),
                "rmu_delta_cosine_across_samples": safe_cosine(
                    stable_delta_rmu, degraded_delta_rmu
                ),
                "wga_delta_cosine_across_samples": safe_cosine(
                    stable_delta_wga, degraded_delta_wga
                ),
                "rmu_contrast_norm": contrast_norm,
                "rmu_contrast_norm_over_mean_delta_norm": safe_ratio(
                    contrast_norm, mean_rmu_delta_norm
                ),
                "rmu_delta_norm_stable": stable_rmu_norm,
                "rmu_delta_norm_degraded": degraded_rmu_norm,
                "wga_delta_norm_stable": stable_wga_norm,
                "wga_delta_norm_degraded": degraded_wga_norm,
            }
        )
    return rows, torch.stack(contrast_vectors)


def save_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot(
    rows: list[dict],
    series: list[tuple[str, str]],
    ylabel: str,
    title: str,
    output_path: Path,
) -> None:
    x = list(range(len(rows)))
    labels = ["Emb" if row["layer"] == "Embedding" else row["layer"] for row in rows]
    fig, axis = plt.subplots(figsize=(12, 5.5))
    for column, legend in series:
        axis.plot(x, [row[column] for row in rows], marker="o", markersize=3.5, label=legend)
    axis.set_xticks(x)
    axis.set_xticklabels(labels, rotation=45, ha="right")
    axis.set_xlabel("Representation position")
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.grid(True, alpha=0.3)
    if len(series) > 1:
        axis.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stable-sample-id", default="main1")
    parser.add_argument("--degraded-sample-id", default="main415")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    validate_sample_id(args.stable_sample_id)
    validate_sample_id(args.degraded_sample_id)

    output_dir = args.output_dir or (
        OUTPUTS_ROOT / "comparisons" / f"{args.stable_sample_id}_vs_{args.degraded_sample_id}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    stable = load_sample(args.stable_sample_id)
    degraded = load_sample(args.degraded_sample_id)
    rows, contrast = calculate(stable, degraded)

    csv_path = output_dir / "stable_vs_degraded_metrics.csv"
    save_csv(rows, csv_path)
    contrast_path = output_dir / "exploratory_two_sample_rmu_contrast.pt"
    torch.save(
        {
            "label": "two-sample exploratory contrast; not a general privacy direction",
            "stable_sample_id": args.stable_sample_id,
            "degraded_sample_id": args.degraded_sample_id,
            "definition": "(RMU_degraded - BASE_degraded) - (RMU_stable - BASE_stable)",
            "contrast": contrast,
        },
        contrast_path,
    )

    plot(
        rows,
        [("rmu_relative_drift_stable", "Stable"),
         ("rmu_relative_drift_degraded", "Degraded")],
        "RMU relative L2 drift",
        "RMU relative drift: stable vs degraded sample",
        output_dir / "rmu_relative_drift_comparison.png",
    )
    plot(
        rows,
        [("wga_relative_drift_stable", "Stable"),
         ("wga_relative_drift_degraded", "Degraded")],
        "WGA relative L2 drift",
        "WGA relative drift: stable vs degraded sample",
        output_dir / "wga_relative_drift_comparison.png",
    )
    plot(
        rows,
        [("rmu_delta_cosine_across_samples", "RMU delta cosine")],
        "Cosine similarity",
        "RMU change-direction similarity across samples",
        output_dir / "rmu_change_direction_similarity.png",
    )
    plot(
        rows,
        [("wga_delta_cosine_across_samples", "WGA delta cosine")],
        "Cosine similarity",
        "WGA change-direction similarity across samples",
        output_dir / "wga_change_direction_similarity.png",
    )

    print(f"Saved metrics: {csv_path}")
    print(f"Saved exploratory contrast: {contrast_path}")
    print(", ".join(rows[0].keys()))
    for row in rows:
        values = [row["layer"]] + [
            "nan" if math.isnan(row[key]) else f"{row[key]:.8f}" for key in list(row)[1:]
        ]
        print(", ".join(values))


if __name__ == "__main__":
    main()
