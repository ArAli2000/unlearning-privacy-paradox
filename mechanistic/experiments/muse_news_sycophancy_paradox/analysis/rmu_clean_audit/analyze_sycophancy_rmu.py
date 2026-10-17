#!/usr/bin/env python3
"""RMU replication of the sycophancy failure-contrast analysis.

Same token position, residual-stream states and bootstrap methods (1000 reps; basic bootstrap
for norms, percentile for cosines/means) as
../../../../privacy_collapse/persistbench_native/analyze_sycophancy.py.

One deliberate difference: the SatImp/SimNPO version used all raw BASE-SAFE -> method-FAILURE
transitions as the failure group (15 and 12), whereas here only the 8 manually audited
HIGH_CONFIDENCE_FAILURE cases are used. The stable group is still the full raw SAFE->SAFE
population (n=168). The RMU estimate is therefore stricter and has smaller n.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

ROOT = Path("/mnt/beegfs/work/elshashay/open-unlearning")
HERE = Path(__file__).resolve().parent
NATIVE = ROOT / "mechanistic/privacy_collapse/persistbench_native"
NATIVE_MANIFEST = NATIVE / "manifests/native_sycophancy_200_v1.json"
BASE_TENSOR = NATIVE / "representations/sycophancy/base_prompt_end.pt"
RMU_TENSOR = HERE / "representations/rmu_prompt_end.pt"
OUT = HERE / "representations_analysis"
LAYERS = list(range(29))
THRESHOLD = 3
BOOTSTRAPS = 1000
SEED = 20260828  # identical seed to the canonical run, for a like-for-like bootstrap procedure

HIGH_CONFIDENCE_FAILURE_IDS = {
    "90378899c28ad8ac7abdf68bc32d0d45", "f03cff21af525d2c2b13cc520880c152",
    "6967d0670f978355d3584249157e6878", "c292da8159886d736a2c6cffe36a0c1c",
    "e24b2945e99c6300efc13cd3fda775f8", "80be14202c0510bbabc817bda834e7bd",
    "192b362d25e4eb63cce8f1bce0e594a6", "7b1e019824a5da43f90afcebcc813873",
}


def ci(values: np.ndarray) -> list[float]:
    return [float(x) for x in np.quantile(values, [0.025, 0.975])]


def basic_norm_ci(estimate: float, bootstrap_values: np.ndarray) -> list[float]:
    low_q, high_q = np.quantile(bootstrap_values, [0.025, 0.975])
    return [max(0.0, float(2 * estimate - high_q)), max(0.0, float(2 * estimate - low_q))]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else float("nan")


def bootstrap_layer(stable: np.ndarray, failure: np.ndarray, rng: np.random.Generator) -> dict[str, Any]:
    result: dict[str, Any] = {}
    boot_means = {}
    for name, values in (("non_to_non", stable), ("non_to_syc", failure)):
        n = len(values)
        indices = rng.integers(0, n, size=(BOOTSTRAPS, n))
        means = values[indices].mean(axis=1)
        example_norms = np.linalg.norm(values, axis=1)
        boot_example_norm = example_norms[indices].mean(axis=1)
        boot_means[name] = means
        mean_delta_norm = float(np.linalg.norm(values.mean(axis=0)))
        result[name] = {
            "N": n,
            "mean_delta_norm": mean_delta_norm,
            "mean_delta_norm_ci95": basic_norm_ci(mean_delta_norm, np.linalg.norm(means, axis=1)),
            "mean_per_example_delta_norm": float(example_norms.mean()),
            "mean_per_example_delta_norm_ci95": ci(boot_example_norm),
        }
    stable_mean = stable.mean(axis=0)
    failure_mean = failure.mean(axis=0)
    result["group_mean_cosine"] = cosine(stable_mean, failure_mean)
    boot_cos = np.array([cosine(a, b) for a, b in zip(boot_means["non_to_non"], boot_means["non_to_syc"], strict=True)])
    result["group_mean_cosine_ci95"] = ci(boot_cos[np.isfinite(boot_cos)])
    contrast = failure_mean - stable_mean
    boot_contrast = boot_means["non_to_syc"] - boot_means["non_to_non"]
    result["failure_contrast_norm"] = float(np.linalg.norm(contrast))
    result["failure_contrast_norm_ci95"] = basic_norm_ci(
        result["failure_contrast_norm"], np.linalg.norm(boot_contrast, axis=1)
    )
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(NATIVE_MANIFEST.read_text(encoding="utf-8"))
    records = manifest["records"]
    ids = [r["persistbench_id"] for r in records]
    id_to_index = {pid: i for i, pid in enumerate(ids)}

    base_tensor = torch.load(BASE_TENSOR, map_location="cpu", weights_only=True).numpy()
    rmu_tensor = torch.load(RMU_TENSOR, map_location="cpu", weights_only=True).numpy()
    for name, tensor in (("BASE", base_tensor), ("RMU", rmu_tensor)):
        if tensor.shape != (200, 29, 3584) or not np.isfinite(tensor).all():
            raise RuntimeError(f"Invalid {name} tensor")

    # Raw transition data (already computed and audited in this directory).
    transitions = json.loads((HERE / "sycophancy_transition_groups.json").read_text(encoding="utf-8"))
    safe_to_safe_ids = {r["persistbench_id"] for r in transitions["groups"]["SAFE_to_SAFE"]}

    stable_idx = [id_to_index[pid] for pid in safe_to_safe_ids]
    failure_idx = [id_to_index[pid] for pid in HIGH_CONFIDENCE_FAILURE_IDS]
    print(f"stable (SAFE->SAFE) N={len(stable_idx)}, failure (audited HIGH_CONFIDENCE_FAILURE) N={len(failure_idx)}")

    delta = rmu_tensor - base_tensor
    rng = np.random.default_rng(SEED)
    layers = []
    layer_csv = []
    for layer in LAYERS:
        stats = bootstrap_layer(delta[stable_idx, layer], delta[failure_idx, layer], rng)
        stats["layer"] = layer
        layers.append(stats)
        row = {"method": "RMU", "layer": layer, "exploratory": len(failure_idx) < 5}
        for group in ("non_to_non", "non_to_syc"):
            for key in ("N", "mean_delta_norm", "mean_per_example_delta_norm"):
                row[f"{group}_{key}"] = stats[group][key]
            row[f"{group}_mean_delta_norm_ci_low"], row[f"{group}_mean_delta_norm_ci_high"] = stats[group]["mean_delta_norm_ci95"]
            row[f"{group}_mean_example_norm_ci_low"], row[f"{group}_mean_example_norm_ci_high"] = stats[group]["mean_per_example_delta_norm_ci95"]
        row["group_mean_cosine"] = stats["group_mean_cosine"]
        row["group_mean_cosine_ci_low"], row["group_mean_cosine_ci_high"] = stats["group_mean_cosine_ci95"]
        row["failure_contrast_norm"] = stats["failure_contrast_norm"]
        row["failure_contrast_norm_ci_low"], row["failure_contrast_norm_ci_high"] = stats["failure_contrast_norm_ci95"]
        layer_csv.append(row)

    import csv
    with (OUT / "rmu_sycophancy_layer_metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(layer_csv[0]))
        writer.writeheader()
        writer.writerows(layer_csv)

    failure_profile = np.array([x["failure_contrast_norm"] for x in layers])
    peak_layer = int(np.argmax(failure_profile))
    top5 = sorted(np.argsort(failure_profile)[-5:].tolist())

    # Compare against existing SatImp/SimNPO profiles.
    satimp_simnpo_csv = NATIVE / "analysis/sycophancy/sycophancy_layer_metrics.csv"
    import csv as csv_mod
    satimp_profile = [None] * 29
    simnpo_profile = [None] * 29
    with satimp_simnpo_csv.open() as fh:
        for row in csv_mod.DictReader(fh):
            layer_i = int(row["layer"])
            if row["method"] == "SatImp":
                satimp_profile[layer_i] = float(row["failure_contrast_norm"])
            elif row["method"] == "SimNPO":
                simnpo_profile[layer_i] = float(row["failure_contrast_norm"])
    satimp_profile = np.array(satimp_profile)
    simnpo_profile = np.array(simnpo_profile)

    corr_satimp = float(np.corrcoef(failure_profile, satimp_profile)[0, 1])
    corr_simnpo = float(np.corrcoef(failure_profile, simnpo_profile)[0, 1])

    summary = {
        "method": "RMU",
        "protocol_note": (
            "Failure group = 8 manually-audited HIGH_CONFIDENCE_FAILURE cases only "
            "(not all 13 raw SAFE->FAILURE transitions, unlike the canonical SatImp/SimNPO "
            "run which used the unaudited raw transition set). Stable group = full raw "
            "SAFE->SAFE population (N=168), matching canonical protocol for that side."
        ),
        "judge": "legacy_local_qwen_judge / Qwen/Qwen2.5-7B-Instruct",
        "failure_threshold": THRESHOLD,
        "generation_index": 0,
        "stable_N": len(stable_idx),
        "failure_N": len(failure_idx),
        "peak_layer": peak_layer,
        "top5_layers": top5,
        "pearson_r_vs_satimp": corr_satimp,
        "pearson_r_vs_simnpo": corr_simnpo,
    }
    (OUT / "rmu_analysis_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))

    plt.figure(figsize=(9, 5.2))
    plt.plot(LAYERS, satimp_profile, marker="o", markersize=2.5, linewidth=1.3, label="SatImp (n=15 raw transitions)")
    plt.plot(LAYERS, simnpo_profile, marker="o", markersize=2.5, linewidth=1.3, label="SimNPO (n=12 raw transitions)")
    plt.plot(LAYERS, failure_profile, marker="o", markersize=2.5, linewidth=1.8, label="RMU (n=8 audited genuine)", color="#8E44AD")
    plt.xlabel("State index (0=embedding, 1-28=transformer layers)")
    plt.ylabel("Descriptive failure-associated divergence (norm)")
    plt.xticks(LAYERS[::2])
    plt.legend()
    plt.title("Descriptive failure-associated divergence -- not causal")
    plt.tight_layout()
    plt.savefig(OUT / "rmu_vs_satimp_simnpo_failure_contrast_norm.png", dpi=180)
    plt.close()


if __name__ == "__main__":
    main()
