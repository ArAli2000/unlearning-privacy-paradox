#!/usr/bin/env python3
"""CPU-only magnitude, direction, uncertainty, and PCA analysis for the 12-vs-12 study."""

import argparse
import csv
import itertools
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "mechanistic/outputs/privacy_population_12v12"
ACTIVATION_ROOT = ROOT / "mechanistic/outputs"
EXPECTED_SHAPE = (29, 3584)
EPS = 1e-12
PCA_LAYERS = (11, 17, 20, 24, 28)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def cosine(left: torch.Tensor, right: torch.Tensor) -> float:
    ln, rn = torch.linalg.vector_norm(left), torch.linalg.vector_norm(right)
    if ln.item() <= EPS or rn.item() <= EPS:
        return math.nan
    return (torch.dot(left, right) / (ln * rn)).item()


def pairwise_cosines(vectors: torch.Tensor, other: torch.Tensor | None = None) -> list[float]:
    values = []
    if other is None:
        for i, j in itertools.combinations(range(vectors.shape[0]), 2):
            values.append(cosine(vectors[i], vectors[j]))
    else:
        for left in vectors:
            for right in other:
                values.append(cosine(left, right))
    return [value for value in values if not math.isnan(value)]


def stats(values: list[float]) -> tuple[float, float, float]:
    tensor = torch.tensor(values, dtype=torch.float64)
    return tensor.mean().item(), tensor.median().item(), tensor.std(unbiased=True).item()


def paired_uncertainty(differences: torch.Tensor) -> tuple[float, float, float]:
    generator = torch.Generator().manual_seed(20260815)
    indices = torch.randint(
        0, differences.numel(), (10000, differences.numel()), generator=generator
    )
    bootstrap_means = differences[indices].mean(dim=1)
    low, high = torch.quantile(bootstrap_means, torch.tensor([0.025, 0.975], dtype=torch.float64))
    signs = torch.tensor(list(itertools.product((-1.0, 1.0), repeat=differences.numel())))
    null_means = (signs * differences.unsqueeze(0)).mean(dim=1).abs()
    observed = differences.mean().abs()
    p_value = ((null_means >= observed).sum().item() + 1) / (null_means.numel() + 1)
    return low.item(), high.item(), p_value


def load_states(sample_id: str) -> dict[str, torch.Tensor]:
    states = {}
    for method in ("base", "rmu", "wga"):
        path = ACTIVATION_ROOT / sample_id / f"{method}_last_prompt_token.pt"
        tensor = torch.load(path, map_location="cpu", weights_only=True)
        if tuple(tensor.shape) != EXPECTED_SHAPE or tensor.dtype != torch.float32:
            raise ValueError(f"Invalid tensor shape/dtype: {path}: {tensor.shape}/{tensor.dtype}")
        if not torch.isfinite(tensor).all().item():
            raise ValueError(f"Non-finite tensor: {path}")
        states[method] = tensor.to(torch.float64)
    return states


def layer_label(index: int) -> str:
    return "Embedding" if index == 0 else f"L{index}"


def plot_magnitude(per_sample: list[dict], method: str, output: Path) -> None:
    fig, axis = plt.subplots(figsize=(12, 6))
    colors = {"stable": "#2878B5", "degraded": "#D95319"}
    for group in ("stable", "degraded"):
        sample_ids = sorted({r["sample_id"] for r in per_sample if r["group"] == group})
        matrix = []
        for sid in sample_ids:
            values = [float(r[f"{method}_relative_drift"]) for r in per_sample if r["sample_id"] == sid]
            matrix.append(values)
            axis.plot(range(29), values, color=colors[group], alpha=0.18, linewidth=1)
        mean = torch.tensor(matrix).mean(0)
        axis.plot(range(29), mean, color=colors[group], linewidth=2.8, label=f"{group} mean")
    axis.set_xticks(range(29)); axis.set_xticklabels(["Emb"] + [f"L{i}" for i in range(1, 29)], rotation=45, ha="right")
    axis.set_xlabel("Representation position"); axis.set_ylabel(f"{method.upper()} relative L2 drift")
    axis.set_title(f"{method.upper()} drift: individual samples and group means"); axis.grid(alpha=.25); axis.legend()
    fig.tight_layout(); fig.savefig(output, dpi=200); plt.close(fig)


def plot_direction(rows: list[dict], field_groups: list[tuple[str, str]], title: str, output: Path) -> None:
    fig, axis = plt.subplots(figsize=(12, 5.5))
    for field, label in field_groups:
        axis.plot(range(29), [float(r[field]) for r in rows], marker="o", markersize=3, label=label)
    axis.set_xticks(range(29)); axis.set_xticklabels(["Emb"] + [f"L{i}" for i in range(1, 29)], rotation=45, ha="right")
    axis.set_xlabel("Representation position"); axis.set_ylabel("Cosine similarity"); axis.set_title(title)
    axis.grid(alpha=.25); axis.legend(); fig.tight_layout(); fig.savefig(output, dpi=200); plt.close(fig)


def pca(vectors: torch.Tensor) -> tuple[torch.Tensor, float, float]:
    centered = vectors - vectors.mean(0, keepdim=True)
    _, singular, vh = torch.linalg.svd(centered, full_matrices=False)
    scores = centered @ vh[:2].T
    variance = singular.square()
    fractions = variance / variance.sum()
    return scores, fractions[0].item(), fractions[1].item()


def pca_plot(scores: torch.Tensor, manifest: list[dict], title: str, output: Path) -> tuple[float, float]:
    groups = [row["group"] for row in manifest]
    fig, axis = plt.subplots(figsize=(7, 6))
    for pair_id in sorted({r["pair_id"] for r in manifest}):
        indexes = [i for i, row in enumerate(manifest) if row["pair_id"] == pair_id]
        axis.plot(scores[indexes, 0], scores[indexes, 1], color="0.75", linewidth=.8, zorder=1)
    for group, color, marker in (("stable", "#2878B5", "o"), ("degraded", "#D95319", "^")):
        indexes = [i for i, value in enumerate(groups) if value == group]
        axis.scatter(scores[indexes, 0], scores[indexes, 1], c=color, marker=marker, label=group, s=45, zorder=2)
        for i in indexes:
            axis.annotate(manifest[i]["sample_id"], scores[i].tolist(), fontsize=6, alpha=.8)
    axis.axhline(0, color="0.85", linewidth=.7); axis.axvline(0, color="0.85", linewidth=.7)
    axis.set_xlabel("PC1"); axis.set_ylabel("PC2"); axis.set_title(title); axis.legend()
    fig.tight_layout(); fig.savefig(output, dpi=200); plt.close(fig)
    stable_scores = scores[[i for i, g in enumerate(groups) if g == "stable"]]
    degraded_scores = scores[[i for i, g in enumerate(groups) if g == "degraded"]]
    centroid_distance = torch.linalg.vector_norm(stable_scores.mean(0) - degraded_scores.mean(0)).item()
    pooled_rms = math.sqrt(0.5 * (
        (stable_scores - stable_scores.mean(0)).square().sum(1).mean().item()
        + (degraded_scores - degraded_scores.mean(0)).square().sum(1).mean().item()
    ))
    return centroid_distance, pooled_rms


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()
    manifest = read_csv(args.study_dir / "sample_manifest.csv")
    if len(manifest) != 24 or len({r["sample_id"] for r in manifest}) != 24:
        raise ValueError("Expected exactly 24 unique manifest samples")
    states = {row["sample_id"]: load_states(row["sample_id"]) for row in manifest}
    group_ids = {group: [r["sample_id"] for r in manifest if r["group"] == group] for group in ("stable", "degraded")}
    deltas = {
        method: {sid: states[sid][method] - states[sid]["base"] for sid in states}
        for method in ("rmu", "wga")
    }

    per_sample = []
    for row in manifest:
        sid = row["sample_id"]
        for layer in range(29):
            base = states[sid]["base"][layer]
            record = {"pair_id": row["pair_id"], "sample_id": sid, "group": row["group"], "layer": layer_label(layer), "layer_index": layer}
            for method in ("rmu", "wga"):
                after, delta = states[sid][method][layer], deltas[method][sid][layer]
                record[f"{method}_cosine_base"] = cosine(base, after)
                record[f"{method}_l2"] = torch.linalg.vector_norm(delta).item()
                record[f"{method}_relative_drift"] = record[f"{method}_l2"] / torch.linalg.vector_norm(base).item()
                record[f"{method}_state_norm"] = torch.linalg.vector_norm(after).item()
            record["base_state_norm"] = torch.linalg.vector_norm(base).item()
            record["rmu_wga_delta_cosine"] = cosine(deltas["rmu"][sid][layer], deltas["wga"][sid][layer])
            per_sample.append(record)
    write_csv(args.study_dir / "per_sample_layer_metrics.csv", per_sample)

    group_metrics, directional = [], []
    contrast_vectors = []
    for layer in range(29):
        for method in ("rmu", "wga"):
            values = {
                group: torch.tensor([
                    next(float(r[f"{method}_relative_drift"]) for r in per_sample if r["sample_id"] == sid and int(r["layer_index"]) == layer)
                    for sid in group_ids[group]
                ], dtype=torch.float64) for group in ("stable", "degraded")
            }
            differences = values["degraded"] - values["stable"]
            low, high, p_value = paired_uncertainty(differences)
            sm, smed, ssd = stats(values["stable"].tolist()); dm, dmed, dsd = stats(values["degraded"].tolist())
            pdm, pdmed, pdsd = stats(differences.tolist())
            group_metrics.append({
                "layer": layer_label(layer), "layer_index": layer, "method": method.upper(),
                "stable_mean": sm, "stable_median": smed, "stable_std": ssd,
                "degraded_mean": dm, "degraded_median": dmed, "degraded_std": dsd,
                "paired_difference_mean": pdm, "paired_difference_median": pdmed,
                "paired_difference_std": pdsd, "paired_bootstrap_95ci_low": low,
                "paired_bootstrap_95ci_high": high, "paired_signflip_p": p_value,
            })
            stable_vectors = torch.stack([deltas[method][sid][layer] for sid in group_ids["stable"]])
            degraded_vectors = torch.stack([deltas[method][sid][layer] for sid in group_ids["degraded"]])
            stable_mean, degraded_mean = stable_vectors.mean(0), degraded_vectors.mean(0)
            within_stable, within_degraded = pairwise_cosines(stable_vectors), pairwise_cosines(degraded_vectors)
            between = pairwise_cosines(stable_vectors, degraded_vectors)
            ws_mean, ws_median, _ = stats(within_stable); wd_mean, wd_median, _ = stats(within_degraded); b_mean, b_median, _ = stats(between)
            contrast = degraded_mean - stable_mean
            norm_denominator = 0.5 * (torch.linalg.vector_norm(stable_mean) + torch.linalg.vector_norm(degraded_mean)).item()
            directional.append({
                "layer": layer_label(layer), "layer_index": layer, "method": method.upper(),
                "group_mean_delta_cosine": cosine(stable_mean, degraded_mean),
                "within_stable_pairwise_cosine_mean": ws_mean, "within_stable_pairwise_cosine_median": ws_median,
                "within_degraded_pairwise_cosine_mean": wd_mean, "within_degraded_pairwise_cosine_median": wd_median,
                "between_group_pairwise_cosine_mean": b_mean, "between_group_pairwise_cosine_median": b_median,
                "group_contrast_norm": torch.linalg.vector_norm(contrast).item(),
                "normalized_group_contrast_norm": torch.linalg.vector_norm(contrast).item() / norm_denominator if norm_denominator > EPS else math.nan,
            })
            if method == "rmu":
                contrast_vectors.append(contrast.to(torch.float32))
    write_csv(args.study_dir / "group_layer_metrics.csv", group_metrics)
    write_csv(args.study_dir / "directional_similarity.csv", directional)
    torch.save({
        "label": "exploratory population-level RMU stable-vs-degraded contrast; not a privacy direction",
        "definition": "mean(delta_rmu_degraded) - mean(delta_rmu_stable)",
        "stable_sample_ids": group_ids["stable"], "degraded_sample_ids": group_ids["degraded"],
        "contrast": torch.stack(contrast_vectors),
    }, args.study_dir / "rmu_group_contrast.pt")

    plot_magnitude(per_sample, "rmu", args.study_dir / "rmu_magnitude_population.png")
    plot_magnitude(per_sample, "wga", args.study_dir / "wga_magnitude_population.png")
    rmu_dir = [r for r in directional if r["method"] == "RMU"]
    wga_dir = [r for r in directional if r["method"] == "WGA"]
    plot_direction(rmu_dir, [("group_mean_delta_cosine", "RMU group-mean cosine")], "RMU stable/degraded group-mean direction", args.study_dir / "rmu_group_mean_direction.png")
    plot_direction(wga_dir, [("group_mean_delta_cosine", "WGA group-mean cosine")], "WGA stable/degraded group-mean direction", args.study_dir / "wga_group_mean_direction.png")
    for method, rows in (("rmu", rmu_dir), ("wga", wga_dir)):
        plot_direction(rows, [
            ("within_stable_pairwise_cosine_mean", "within stable"),
            ("within_degraded_pairwise_cosine_mean", "within degraded"),
            ("between_group_pairwise_cosine_mean", "between groups"),
        ], f"{method.upper()} directional coherence", args.study_dir / f"{method}_directional_coherence.png")

    pca_dir = args.study_dir / "pca"; pca_dir.mkdir(exist_ok=True)
    pca_rows = []
    for layer in PCA_LAYERS:
        for method in ("rmu", "wga"):
            raw = torch.stack([deltas[method][row["sample_id"]][layer] for row in manifest])
            for normalization, vectors in (("raw", raw), ("unit", raw / torch.linalg.vector_norm(raw, dim=1, keepdim=True).clamp_min(EPS))):
                scores, pc1, pc2 = pca(vectors)
                filename = f"{method}_{normalization}_delta_pca_L{layer}.png"
                centroid, pooled = pca_plot(scores, manifest, f"{method.upper()} {normalization} delta PCA — L{layer}", pca_dir / filename)
                pca_rows.append({
                    "layer": f"L{layer}", "method": method.upper(), "normalization": normalization,
                    "pc1_explained_variance": pc1, "pc2_explained_variance": pc2,
                    "pc1_pc2_total_variance": pc1 + pc2, "centroid_distance_pc12": centroid,
                    "pooled_within_group_rms_pc12": pooled,
                    "centroid_distance_over_pooled_rms": centroid / pooled if pooled > EPS else math.nan,
                    "plot": str(pca_dir / filename),
                })
    write_csv(args.study_dir / "pca_explained_variance.csv", pca_rows)
    print(f"Completed population analysis in {args.study_dir}")


if __name__ == "__main__":
    main()
