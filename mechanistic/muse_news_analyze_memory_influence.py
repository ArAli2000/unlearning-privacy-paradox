#!/usr/bin/env python3
"""Phase 7 analysis (CPU-only): does contextual memory exert a stronger
influence on internal representations specifically in MUSE-News sycophancy /
cross-domain examples that become privacy failures after unlearning?

For each model M in {BASE, SatImp, SimNPO} and each example, defines

    delta_memory(layer) = h_M(prompt_with_memory)[layer] - h_M(prompt_no_memory)[layer]

using the already-extracted prompt-end hidden states (with-memory:
`mechanistic/privacy_collapse/persistbench_native/representations/{,sycophancy/}*_prompt_end.pt`;
no-memory: `mechanistic/outputs/muse_news_sycophancy_mechanistic/representations/*/`.

Compares ||delta_memory(layer)|| across four groups (grouped by the
BASE-vs-unlearned behavioral transition on that same row, from
`paired_transitions.json`):
  - BASE on SAFE_TO_SAFE rows
  - BASE on SAFE_TO_FAILURE rows   (BASE's own memory-influence magnitude, on
    the rows that later flip; BASE itself is safe on these rows)
  - unlearned-method on SAFE_TO_SAFE rows
  - unlearned-method on SAFE_TO_FAILURE rows

The key question is whether the unlearned-method/SAFE_TO_FAILURE group shows
larger (or differently directed) memory influence than the other three
groups, and specifically larger than its own SAFE_TO_SAFE group (a
within-model, group-only contrast) and larger than BASE's influence on the
very same rows (a within-row, cross-model contrast) -- both comparisons
control for generic unlearning drift and generic per-prompt confounds
respectively.

Output: mechanistic/outputs/muse_news_sycophancy_mechanistic/
  memory_influence_summary.csv
  memory_influence_by_layer.png
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "mechanistic/outputs/muse_news_sycophancy_mechanistic"
NATIVE_DIR = ROOT / "mechanistic/privacy_collapse/persistbench_native"
SEED = 20260919
N_BOOTSTRAP = 2000

WITH_MEMORY_PATHS = {
    "sycophancy": {
        "BASE": NATIVE_DIR / "representations/sycophancy/base_prompt_end.pt",
        "SatImp": NATIVE_DIR / "representations/sycophancy/satimp_prompt_end.pt",
        "SimNPO": NATIVE_DIR / "representations/sycophancy/simnpo_prompt_end.pt",
    },
    "cross_domain": {
        "BASE": NATIVE_DIR / "representations/base_prompt_end.pt",
        "SatImp": NATIVE_DIR / "representations/satimp_prompt_end.pt",
        "SimNPO": NATIVE_DIR / "representations/simnpo_prompt_end.pt",
    },
}
NO_MEMORY_PATHS = {
    category: {
        "BASE": OUT_ROOT / f"representations/{category}/base_prompt_end_no_memory.pt",
        "SatImp": OUT_ROOT / f"representations/{category}/satimp_prompt_end_no_memory.pt",
        "SimNPO": OUT_ROOT / f"representations/{category}/simnpo_prompt_end_no_memory.pt",
    }
    for category in ("sycophancy", "cross_domain")
}
NATIVE_MANIFESTS = {
    "sycophancy": NATIVE_DIR / "manifests/native_sycophancy_200_v1.json",
    "cross_domain": NATIVE_DIR / "manifests/native_cross_domain_200_v1.json",
}


def bootstrap_ci(values: np.ndarray, n: int = N_BOOTSTRAP, seed: int = SEED) -> tuple[float, float]:
    if len(values) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = np.empty(n)
    for i in range(n):
        sample = rng.choice(values, size=len(values), replace=True)
        means[i] = sample.mean()
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def main() -> None:
    paired = json.loads((OUT_ROOT / "paired_transitions.json").read_text(encoding="utf-8"))

    rows = []
    for category in ("sycophancy", "cross_domain"):
        pb_ids = [
            r["persistbench_id"]
            for r in json.loads(NATIVE_MANIFESTS[category].read_text(encoding="utf-8"))["records"]
        ]
        id_to_index = {pid: i for i, pid in enumerate(pb_ids)}

        with_memory = {m: torch.load(p, map_location="cpu", weights_only=True) for m, p in WITH_MEMORY_PATHS[category].items()}
        no_memory = {m: torch.load(p, map_location="cpu", weights_only=True) for m, p in NO_MEMORY_PATHS[category].items()}
        for m in with_memory:
            assert with_memory[m].shape == no_memory[m].shape == (200, 29, 3584)

        for method in ("SatImp", "SimNPO"):
            trans_rows = paired["categories"][category][method]["rows"]
            for group_label, transition in (("SAFE_TO_SAFE", "SAFE_TO_SAFE"), ("SAFE_TO_FAILURE", "SAFE_TO_FAILURE")):
                pb_ids_in_group = [r["persistbench_id"] for r in trans_rows if r["transition"] == transition]
                if not pb_ids_in_group:
                    continue
                indices = [id_to_index[pid] for pid in pb_ids_in_group]
                for evaluating_model in ("BASE", method):
                    delta = with_memory[evaluating_model][indices] - no_memory[evaluating_model][indices]  # [n, 29, 3584]
                    norms = delta.norm(dim=-1).numpy()  # [n, 29]
                    for layer in range(29):
                        vals = norms[:, layer]
                        lo, hi = bootstrap_ci(vals)
                        rows.append(
                            {
                                "category": category,
                                "method": method,
                                "group": group_label,
                                "evaluating_model": evaluating_model,
                                "layer": layer,
                                "n": len(vals),
                                "mean_delta_memory_norm": float(vals.mean()),
                                "ci_lower": lo,
                                "ci_upper": hi,
                            }
                        )

    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_ROOT / "memory_influence_summary.csv", index=False)
    print(f"Wrote {(OUT_ROOT / 'memory_influence_summary.csv').relative_to(ROOT)}")

    for category in summary.category.unique():
        cat = summary[summary.category == category]
        methods = [m for m in cat.method.unique()]
        fig, axes = plt.subplots(1, len(methods), figsize=(7 * len(methods), 5), squeeze=False)
        for ax, method in zip(axes[0], methods):
            msub = cat[cat.method == method]
            for evaluating_model, color in (("BASE", "tab:blue"), (method, "tab:red")):
                for group, style in (("SAFE_TO_SAFE", "--"), ("SAFE_TO_FAILURE", "-")):
                    m = msub[(msub.evaluating_model == evaluating_model) & (msub.group == group)].sort_values("layer")
                    if m.empty:
                        continue
                    n = m.n.iloc[0]
                    ax.plot(m.layer, m.mean_delta_memory_norm, style, color=color, label=f"{evaluating_model} {group} (n={n})")
                    ax.fill_between(m.layer, m.ci_lower, m.ci_upper, alpha=0.10, color=color)
            ax.set_xlabel("Residual state (0=embedding, 1-28=L1-L28)")
            ax.set_ylabel("mean ||delta_memory(layer)||  (with-memory minus no-memory prompt-end state)")
            ax.set_title(f"MUSE-News / Qwen2.5-7B-Instruct / {category} / {method}\nmemory influence by transition group")
            ax.legend(fontsize=8)
        fig.tight_layout()
        out_png = OUT_ROOT / f"memory_influence_by_layer_{category}.png"
        fig.savefig(out_png, dpi=180)
        plt.close(fig)
        print(f"Wrote {out_png.relative_to(ROOT)}")

    print("\nSycophancy, layer 28 (final), all four groups:")
    print(
        summary[(summary.category == "sycophancy") & (summary.layer == 28)]
        .sort_values(["method", "evaluating_model", "group"])
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
