#!/usr/bin/env python3

from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

CASES = [
    {
        "case": "RMU Case 1",
        "case_dir": "mechanistic/outputs/single_persistbench_case_rmu_case1",
        "target": "RMU",
        "control": "WGA",
        "groups": {
            "home": [139],
            "financial": [141],
            "stability": [142],
            "home + financial stability": [139, 141, 142],
        },
    },
    {
        "case": "RMU Case 2",
        "case_dir": "mechanistic/outputs/single_persistbench_case_rmu_case2",
        "target": "RMU",
        "control": "WGA",
        "groups": {
            "capitalist": [4],
            "capitalist systems": [4, 5],
            "ethical": [10],
            "wealth": [11],
            "distribution": [12],
            "ethical wealth distribution": [10, 11, 12],
            "all informative tokens": [4, 5, 10, 11, 12],
        },
    },
    {
        "case": "WGA Case 1",
        "case_dir": "mechanistic/outputs/single_persistbench_case_wga_case1",
        "target": "WGA",
        "control": "RMU",
        "groups": {
            "Columbia": [99],
            "River": [100],
            "Gorge": [101, 102],
            "Columbia River Gorge": [99, 100, 101, 102],
        },
    },
]


def band_mean(frame, column, lo, hi):
    x = frame[(frame["layer"] >= lo) & (frame["layer"] <= hi)]
    if x.empty:
        return float("nan")
    return float(x[column].mean())


def main():
    summary_rows = []
    trajectory_rows = []

    for cfg in CASES:
        case_dir = ROOT / cfg["case_dir"]
        lens_path = case_dir / "logit_lens_trajectory.csv"

        df = pd.read_csv(lens_path)

        print("\n" + "=" * 110)
        print(cfg["case"])
        print("Target model :", cfg["target"])
        print("Control model:", cfg["control"])
        print("=" * 110)

        for group_name, token_indices in cfg["groups"].items():

            selected = df[
                df["generated_token_index"].isin(token_indices)
            ].copy()

            if selected.empty:
                raise RuntimeError(
                    f"No rows found for {cfg['case']} / {group_name} / {token_indices}"
                )

            found_indices = sorted(
                selected["generated_token_index"].unique().tolist()
            )

            if found_indices != sorted(token_indices):
                raise RuntimeError(
                    f"Token mismatch for {cfg['case']} / {group_name}: "
                    f"expected {token_indices}, found {found_indices}"
                )

            # Sum token log-probabilities within each conceptual word/phrase.
            #
            # For a single token this is just that token's log probability.
            # For something like "Gorge" = ["G", "orge"], the two log
            # probabilities are summed, giving the teacher-forced sequence
            # log probability for the full word.
            agg = (
                selected
                .groupby(["model", "layer"], as_index=False)
                .agg(
                    summed_log_probability=("log_probability", "sum"),
                    mean_log_probability=("log_probability", "mean"),
                    token_count=("generated_token_index", "nunique"),
                )
            )

            pivot = agg.pivot(
                index="layer",
                columns="model",
                values="summed_log_probability",
            ).reset_index()

            required = {"BASE", cfg["target"], cfg["control"]}
            missing = required - set(pivot.columns)

            if missing:
                raise RuntimeError(
                    f"Missing models for {cfg['case']} / {group_name}: {missing}"
                )

            pivot["target_minus_base"] = (
                pivot[cfg["target"]] - pivot["BASE"]
            )

            pivot["control_minus_base"] = (
                pivot[cfg["control"]] - pivot["BASE"]
            )

            tokens = (
                selected[
                    ["generated_token_index", "target_token"]
                ]
                .drop_duplicates()
                .sort_values("generated_token_index")
            )

            token_text = " | ".join(
                f"{int(r.generated_token_index)}:{r.target_token}"
                for _, r in tokens.iterrows()
            )

            for _, r in pivot.iterrows():
                trajectory_rows.append(
                    {
                        "case": cfg["case"],
                        "target_model": cfg["target"],
                        "control_model": cfg["control"],
                        "group": group_name,
                        "token_indices": ",".join(map(str, token_indices)),
                        "tokens": token_text,
                        "layer": int(r["layer"]),
                        "base_log_probability": float(r["BASE"]),
                        "target_log_probability": float(r[cfg["target"]]),
                        "control_log_probability": float(r[cfg["control"]]),
                        "target_minus_base": float(r["target_minus_base"]),
                        "control_minus_base": float(r["control_minus_base"]),
                    }
                )

            max_row = pivot.loc[pivot["target_minus_base"].idxmax()]
            min_row = pivot.loc[pivot["target_minus_base"].idxmin()]
            final_row = pivot[pivot["layer"] == pivot["layer"].max()].iloc[0]

            summary_rows.append(
                {
                    "case": cfg["case"],
                    "target_model": cfg["target"],
                    "control_model": cfg["control"],
                    "group": group_name,
                    "token_indices": ",".join(map(str, token_indices)),
                    "tokens": token_text,

                    "max_target_minus_base": float(
                        max_row["target_minus_base"]
                    ),
                    "max_delta_layer": int(max_row["layer"]),

                    "min_target_minus_base": float(
                        min_row["target_minus_base"]
                    ),
                    "min_delta_layer": int(min_row["layer"]),

                    "early_mean_delta_L1_L12": band_mean(
                        pivot, "target_minus_base", 1, 12
                    ),

                    "middle_mean_delta_L13_L21": band_mean(
                        pivot, "target_minus_base", 13, 21
                    ),

                    "late_mean_delta_L22_L28": band_mean(
                        pivot, "target_minus_base", 22, 28
                    ),

                    "late_positive_layers": int(
                        (
                            pivot[
                                (pivot["layer"] >= 22)
                                & (pivot["layer"] <= 28)
                            ]["target_minus_base"]
                            > 0
                        ).sum()
                    ),

                    "final_layer": int(final_row["layer"]),

                    "final_target_minus_base": float(
                        final_row["target_minus_base"]
                    ),

                    "final_control_minus_base": float(
                        final_row["control_minus_base"]
                    ),
                }
            )

        print("\nPrivacy-bearing token/phrase summary:")

        case_summary = pd.DataFrame(summary_rows)
        case_summary = case_summary[
            case_summary["case"] == cfg["case"]
        ]

        print(
            case_summary[
                [
                    "group",
                    "max_target_minus_base",
                    "max_delta_layer",
                    "early_mean_delta_L1_L12",
                    "middle_mean_delta_L13_L21",
                    "late_mean_delta_L22_L28",
                    "late_positive_layers",
                    "final_target_minus_base",
                ]
            ].to_string(index=False)
        )

    summary = pd.DataFrame(summary_rows)
    trajectory = pd.DataFrame(trajectory_rows)

    out_dir = ROOT / "mechanistic/outputs/privacy_bearing_token_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary.to_csv(
        out_dir / "privacy_bearing_token_summary.csv",
        index=False,
    )

    trajectory.to_csv(
        out_dir / "privacy_bearing_token_layer_trajectory.csv",
        index=False,
    )

    print("\n" + "=" * 110)
    print("INTERPRETATION GUIDE")
    print("=" * 110)
    print(
        """
target_minus_base > 0
    The privacy-failing model gives MORE support than BASE to the
    same privacy-bearing token under the shared target-model prefix.

target_minus_base < 0
    The failing model gives LESS support than BASE.

early_mean_delta_L1_L12
    Average difference in early / early-middle processing.

middle_mean_delta_L13_L21
    Average difference in middle / later processing.

late_mean_delta_L22_L28
    Average difference close to the model output.

late_positive_layers
    Number of layers from L22-L28 where the failing model gives
    more support than BASE. Persistence is more informative than
    one tiny sign change at one layer.

IMPORTANT:
These are teacher-forced/shared-prefix comparisons. They tell us how
the models process the same continuation. They do NOT yet tell us why
the failing model naturally chose that continuation.
"""
    )

    print("Saved:")
    print(out_dir / "privacy_bearing_token_summary.csv")
    print(out_dir / "privacy_bearing_token_layer_trajectory.csv")


if __name__ == "__main__":
    main()
