#!/usr/bin/env python3
"""CPU-only analysis of layer-wise safe-vs-failure continuation preference for MUSE-News
sycophancy/cross-domain SAFE_TO_FAILURE cases versus matched SAFE_TO_SAFE controls.

score(layer) = mean_token_logprob(candidate_A=BASE response) - mean_token_logprob(candidate_B=unlearned-method response)
under the ordinary logit lens of the case's own unlearned method (or of BASE as a control model),
teacher-forced on the same prompt. Positive: the layer still favors the safe/reference continuation.
Negative: it favors the alternative.

Bootstrap: 2,000 resamples over cases, percentile 95% CI, seed 20260919.

Output: mechanistic/outputs/muse_news_sycophancy_mechanistic/
  continuation_preference_summary.csv
  continuation_preference_by_layer.png
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "mechanistic/outputs/muse_news_sycophancy_mechanistic"
SEED = 20260919
N_BOOTSTRAP = 2000


def bootstrap_ci(values: np.ndarray, n: int = N_BOOTSTRAP, seed: int = SEED) -> tuple[float, float]:
    if len(values) == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = np.empty(n)
    idx_pool = np.arange(len(values))
    for i in range(n):
        sample = rng.choice(idx_pool, size=len(values), replace=True)
        means[i] = values[sample].mean()
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)))


def main() -> None:
    df = pd.read_csv(OUT_ROOT / "continuation_layer_logprobs.csv")
    manifest = json.loads((OUT_ROOT / "manifests/continuation_cases_v1.json").read_text(encoding="utf-8"))
    n_cases_by_key = {}
    for c in manifest["cases"]:
        key = (c["category"], c["method"], c["group"])
        n_cases_by_key[key] = n_cases_by_key.get(key, 0) + 1

    rows = []
    for category in df.category.unique():
        for method in df[df.category == category].method.unique():
            sub = df[(df.category == category) & (df.method == method) & (df.evaluating_model == method)]
            if sub.empty:
                continue
            piv = sub.pivot_table(
                index=["persistbench_id", "group", "layer"], columns="candidate", values="mean_logprob"
            ).reset_index()
            piv["score"] = piv["candidate_A"] - piv["candidate_B"]
            for group in piv.group.unique():
                n_cases = n_cases_by_key.get((category, method, group), 0)
                for layer in range(29):
                    vals = piv[(piv.group == group) & (piv.layer == layer)]["score"].to_numpy()
                    if len(vals) == 0:
                        continue
                    lo, hi = bootstrap_ci(vals)
                    rows.append(
                        {
                            "category": category,
                            "method": method,
                            "group": group,
                            "layer": layer,
                            "n_cases": n_cases,
                            "mean_score": float(vals.mean()),
                            "ci_lower": lo,
                            "ci_upper": hi,
                        }
                    )

    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_ROOT / "continuation_preference_summary.csv", index=False)
    print(f"Wrote {(OUT_ROOT / 'continuation_preference_summary.csv').relative_to(ROOT)}")

    categories = summary.category.unique()
    fig, axes = plt.subplots(1, len(categories), figsize=(7 * len(categories), 5), squeeze=False)
    for ax, category in zip(axes[0], categories):
        cat_summary = summary[summary.category == category]
        for method in cat_summary.method.unique():
            for group, style in (("FAILURE", "-"), ("CONTROL", "--")):
                m = cat_summary[(cat_summary.method == method) & (cat_summary.group == group)].sort_values("layer")
                if m.empty:
                    continue
                n = m.n_cases.iloc[0]
                ax.plot(m.layer, m.mean_score, style, label=f"{method} {group} (n={n})")
                ax.fill_between(m.layer, m.ci_lower, m.ci_upper, alpha=0.12)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.axvspan(22, 25, alpha=0.08, color="tab:orange")
        ax.axvspan(26, 28, alpha=0.08, color="tab:red")
        ax.set_xlabel("Residual state (0=embedding, 1-28=L1-L28)")
        ax.set_ylabel("score(layer) = logP(safe) - logP(alternative), mean per-token")
        ax.set_title(
            f"MUSE-News / Qwen2.5-7B-Instruct / {category}\nSAFE_TO_FAILURE vs matched SAFE_TO_SAFE, own-method logit lens"
        )
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT_ROOT / "continuation_preference_by_layer.png", dpi=180)
    plt.close(fig)
    print(f"Wrote {(OUT_ROOT / 'continuation_preference_by_layer.png').relative_to(ROOT)}")

    print("\nFAILURE-group mean score at key layers:")
    print(
        summary[(summary.group == "FAILURE") & (summary.layer.isin([0, 17, 20, 22, 24, 26, 28]))]
        .sort_values(["category", "method", "layer"])
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
