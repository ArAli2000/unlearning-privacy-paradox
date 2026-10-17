#!/usr/bin/env python3
"""Analyze layerwise representation drift for one extracted PrivacyLens sample."""

import argparse
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SHAPE = (29, 3584)
NEAR_ZERO_NORM = 1e-12


def load_states(path: Path) -> torch.Tensor:
    states = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(states, torch.Tensor):
        raise TypeError(f"Expected a tensor in {path}, got {type(states).__name__}")
    if tuple(states.shape) != EXPECTED_SHAPE:
        raise ValueError(f"Expected {EXPECTED_SHAPE} in {path}, got {tuple(states.shape)}")
    if not torch.isfinite(states).all().item():
        raise ValueError(f"Non-finite values found in {path}")
    return states.to(dtype=torch.float64)


def safe_cosine(left: torch.Tensor, right: torch.Tensor) -> float:
    left_norm = torch.linalg.vector_norm(left)
    right_norm = torch.linalg.vector_norm(right)
    if left_norm.item() <= NEAR_ZERO_NORM or right_norm.item() <= NEAR_ZERO_NORM:
        return math.nan
    return (torch.dot(left, right) / (left_norm * right_norm)).item()


def make_rows(base: torch.Tensor, rmu: torch.Tensor, wga: torch.Tensor) -> list[dict]:
    rows = []
    for index in range(base.shape[0]):
        base_state = base[index]
        rmu_state = rmu[index]
        wga_state = wga[index]
        delta_rmu = rmu_state - base_state
        delta_wga = wga_state - base_state

        base_norm = torch.linalg.vector_norm(base_state).item()
        rmu_l2 = torch.linalg.vector_norm(delta_rmu).item()
        wga_l2 = torch.linalg.vector_norm(delta_wga).item()
        if base_norm <= NEAR_ZERO_NORM:
            rmu_relative_l2 = math.nan
            wga_relative_l2 = math.nan
        else:
            rmu_relative_l2 = rmu_l2 / base_norm
            wga_relative_l2 = wga_l2 / base_norm

        rows.append(
            {
                "layer": "Embedding" if index == 0 else f"L{index}",
                "cosine_base_rmu": safe_cosine(base_state, rmu_state),
                "cosine_base_wga": safe_cosine(base_state, wga_state),
                "l2_base_rmu": rmu_l2,
                "l2_base_wga": wga_l2,
                "relative_l2_rmu": rmu_relative_l2,
                "relative_l2_wga": wga_relative_l2,
                "norm_base": base_norm,
                "norm_rmu": torch.linalg.vector_norm(rmu_state).item(),
                "norm_wga": torch.linalg.vector_norm(wga_state).item(),
                "cosine_delta_rmu_delta_wga": safe_cosine(delta_rmu, delta_wga),
            }
        )
    return rows


def save_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_lines(
    rows: list[dict],
    columns: list[tuple[str, str]],
    ylabel: str,
    title: str,
    output_path: Path,
) -> None:
    x = list(range(len(rows)))
    labels = ["Emb" if row["layer"] == "Embedding" else row["layer"] for row in rows]
    fig, axis = plt.subplots(figsize=(12, 5.5))
    for column, legend in columns:
        axis.plot(x, [row[column] for row in rows], marker="o", markersize=3.5, label=legend)
    axis.set_xticks(x)
    axis.set_xticklabels(labels, rotation=45, ha="right")
    axis.set_xlabel("Representation position")
    axis.set_ylabel(ylabel)
    axis.set_title(title)
    axis.grid(True, alpha=0.3)
    if len(columns) > 1:
        axis.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-id", default="main1")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Defaults to mechanistic/outputs/<sample-id>/ under the repository root.",
    )
    args = parser.parse_args()

    if not args.sample_id or Path(args.sample_id).name != args.sample_id:
        raise ValueError("--sample-id must be a non-empty dataset ID, not a path")
    input_dir = args.input_dir or REPO_ROOT / "mechanistic/outputs" / args.sample_id

    base = load_states(input_dir / "base_last_prompt_token.pt")
    rmu = load_states(input_dir / "rmu_last_prompt_token.pt")
    wga = load_states(input_dir / "wga_last_prompt_token.pt")
    rows = make_rows(base, rmu, wga)

    csv_path = input_dir / "representation_drift.csv"
    save_csv(rows, csv_path)
    plot_lines(
        rows,
        [("cosine_base_rmu", "BASE vs RMU"), ("cosine_base_wga", "BASE vs WGA")],
        "Cosine similarity",
        "Similarity to BASE by representation position",
        input_dir / "cosine_similarity.png",
    )
    plot_lines(
        rows,
        [("relative_l2_rmu", "RMU"), ("relative_l2_wga", "WGA")],
        "Relative L2 drift",
        "Relative L2 drift from BASE",
        input_dir / "relative_l2_drift.png",
    )
    plot_lines(
        rows,
        [("cosine_delta_rmu_delta_wga", "RMU delta vs WGA delta")],
        "Cosine similarity",
        "Similarity of unlearning-induced change directions",
        input_dir / "delta_direction_similarity.png",
    )
    print(f"Saved {csv_path}")
    print("layer, cos(B,R), cos(B,W), L2(B,R), L2(B,W), relL2(R), relL2(W), "
          "||B||, ||R||, ||W||, cos(deltaR,deltaW)")
    for row in rows:
        values = [row["layer"]] + [
            "nan" if math.isnan(row[key]) else f"{row[key]:.8f}"
            for key in list(row)[1:]
        ]
        print(", ".join(values))


if __name__ == "__main__":
    main()
