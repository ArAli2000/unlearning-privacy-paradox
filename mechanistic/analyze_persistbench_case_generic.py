#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

import pandas as pd
import torch
import torch.nn.functional as F


ROOT = Path(__file__).resolve().parents[1]


def cosine(a, b):
    return float(F.cosine_similarity(a, b, dim=0))


def relative_l2(base, other):
    return float((other - base).norm() / base.norm())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-dir", required=True)
    args = ap.parse_args()

    out = ROOT / args.case_dir

    case = json.loads((out / "selected_case.json").read_text())
    meta = json.loads((out / "extraction_metadata.json").read_text())
    manifest = pd.read_csv(out / "position_manifest.csv")
    lens = pd.read_csv(out / "logit_lens_trajectory.csv")
    continuation = pd.read_csv(out / "continuation_comparison.csv")

    target_model = case["target_model"]
    control_model = case["control_model"]

    print("=" * 80)
    print("CASE")
    print("=" * 80)
    print("entry_id:", case["entry_id"])
    print("generation_index:", case["generation_index"])
    print("target_model:", target_model)
    print("control_model:", control_model)
    print("first_injected_phrase:", case["first_injected_phrase"])
    print("non_personal_alternative:", case["non_personal_alternative"])

    reps = {}
    for model in ["BASE", "RMU", "WGA"]:
        path = out / f"{model.lower()}_representations.pt"
        reps[model] = torch.load(
            path,
            map_location="cpu",
            weights_only=True,
        )

    # Prompt representation drift

    selected_positions = sorted(
        {
            pos
            for _, row in manifest.iterrows()
            if int(row["token_start"]) >= 0
            for pos in range(
                int(row["token_start"]),
                int(row["token_end_exclusive"]),
            )
        }
    )

    prompt_pos_to_saved_index = {
        pos: idx for idx, pos in enumerate(selected_positions)
    }

    prompt_rows = []

    for _, span in manifest.iterrows():
        start = int(span["token_start"])
        end = int(span["token_end_exclusive"])

        if start < 0:
            continue

        saved_indices = [
            prompt_pos_to_saved_index[pos]
            for pos in range(start, end)
            if pos in prompt_pos_to_saved_index
        ]

        if not saved_indices:
            continue

        for layer in range(29):
            base = reps["BASE"]["prompt_selected"][
                layer, saved_indices
            ].mean(dim=0)

            target = reps[target_model]["prompt_selected"][
                layer, saved_indices
            ].mean(dim=0)

            control = reps[control_model]["prompt_selected"][
                layer, saved_indices
            ].mean(dim=0)

            prompt_rows.append(
                {
                    "span": span["span_label"],
                    "layer": layer,
                    "target_model": target_model,
                    "control_model": control_model,
                    "cosine_base_target": cosine(base, target),
                    "relative_l2_target_minus_base": relative_l2(
                        base, target
                    ),
                    "cosine_base_control": cosine(base, control),
                    "relative_l2_control_minus_base": relative_l2(
                        base, control
                    ),
                }
            )

    prompt_df = pd.DataFrame(prompt_rows)
    prompt_df.to_csv(
        out / "representation_drift_generic.csv",
        index=False,
    )

    # Shared target-response hidden-state trajectory

    inj = meta["injection"]
    lo = int(inj["window_generated_token_start"])
    hi = int(inj["window_generated_token_end_exclusive"])
    first = int(inj["generated_token_start"])

    trajectory_rows = []

    for gi in range(lo, hi):
        for layer in range(29):
            base = reps["BASE"]["shared_generated"][layer, gi]
            target = reps[target_model]["shared_generated"][layer, gi]
            control = reps[control_model]["shared_generated"][layer, gi]

            trajectory_rows.append(
                {
                    "generated_token_index": gi,
                    "relative_to_injection": gi - first,
                    "layer": layer,
                    "target_model": target_model,
                    "control_model": control_model,
                    "cosine_base_target": cosine(base, target),
                    "relative_l2_target_minus_base": relative_l2(
                        base, target
                    ),
                    "cosine_base_control": cosine(base, control),
                    "relative_l2_control_minus_base": relative_l2(
                        base, control
                    ),
                }
            )

    trajectory_df = pd.DataFrame(trajectory_rows)
    trajectory_df.to_csv(
        out / "generated_trajectory_generic.csv",
        index=False,
    )

    # First injected token: target-vs-BASE logit-lens difference

    first_lens = lens[
        lens["generated_token_index"] == first
    ].copy()

    base_lens = (
        first_lens[first_lens["model"] == "BASE"]
        .set_index("layer")
    )

    target_lens = (
        first_lens[first_lens["model"] == target_model]
        .set_index("layer")
    )

    control_lens = (
        first_lens[first_lens["model"] == control_model]
        .set_index("layer")
    )

    logit_rows = []

    for layer in sorted(
        set(base_lens.index)
        & set(target_lens.index)
        & set(control_lens.index)
    ):
        b = base_lens.loc[layer]
        t = target_lens.loc[layer]
        c = control_lens.loc[layer]

        logit_rows.append(
            {
                "layer": int(layer),
                "target_token": t["target_token"],
                "base_log_probability": float(b["log_probability"]),
                "target_log_probability": float(t["log_probability"]),
                "control_log_probability": float(c["log_probability"]),
                "target_minus_base_logprob": float(
                    t["log_probability"] - b["log_probability"]
                ),
                "control_minus_base_logprob": float(
                    c["log_probability"] - b["log_probability"]
                ),
                "base_rank": int(b["rank"]),
                "target_rank": int(t["rank"]),
                "control_rank": int(c["rank"]),
            }
        )

    first_token_df = pd.DataFrame(logit_rows)
    first_token_df.to_csv(
        out / "first_private_token_logit_delta.csv",
        index=False,
    )

    # Compact findings

    print("\n" + "=" * 80)
    print("PROMPT REPRESENTATION DRIFT")
    print("=" * 80)

    strongest_prompt_rows = (
        prompt_df.loc[
            prompt_df.groupby("span")[
                "relative_l2_target_minus_base"
            ].idxmax()
        ]
        .sort_values(
            "relative_l2_target_minus_base",
            ascending=False,
        )
    )

    print(
        strongest_prompt_rows[
            [
                "span",
                "layer",
                "relative_l2_target_minus_base",
                "relative_l2_control_minus_base",
            ]
        ].to_string(index=False)
    )

    print("\n" + "=" * 80)
    print("STATE IMMEDIATELY BEFORE FIRST INJECTED TOKEN")
    print("=" * 80)

    if first > 0:
        pre = trajectory_df[
            trajectory_df["generated_token_index"] == first - 1
        ].copy()

        print(
            pre[
                [
                    "layer",
                    "relative_l2_target_minus_base",
                    "relative_l2_control_minus_base",
                ]
            ].to_string(index=False)
        )

        strongest_pre = pre.loc[
            pre["relative_l2_target_minus_base"].idxmax()
        ]

        print(
            "\nStrongest target-vs-BASE pre-injection drift:"
        )
        print(
            "layer",
            int(strongest_pre["layer"]),
            "relative_l2 =",
            float(
                strongest_pre[
                    "relative_l2_target_minus_base"
                ]
            ),
        )
    else:
        print(
            "Injected phrase starts at generated token 0; "
            "prompt-final state was used by the logit lens."
        )

    print("\n" + "=" * 80)
    print("FIRST PRIVATE TOKEN LOGIT LENS")
    print("=" * 80)

    print(
        first_token_df[
            [
                "layer",
                "target_token",
                "target_minus_base_logprob",
                "control_minus_base_logprob",
                "base_rank",
                "target_rank",
                "control_rank",
            ]
        ].to_string(index=False)
    )

    positive = first_token_df[
        first_token_df["target_minus_base_logprob"] > 0
    ]

    if len(positive):
        first_positive = int(positive.iloc[0]["layer"])
        print(
            "\nFirst layer where target model gives greater "
            "support than BASE:",
            first_positive,
        )
    else:
        print(
            "\nTarget model never exceeds BASE support "
            "for the first private token."
        )

    final = first_token_df[
        first_token_df["layer"] == 28
    ]

    if len(final):
        r = final.iloc[0]
        print(
            "Final-layer target-minus-BASE log-probability:",
            float(r["target_minus_base_logprob"]),
        )
        print(
            "Final-layer BASE rank:",
            int(r["base_rank"]),
        )
        print(
            "Final-layer target rank:",
            int(r["target_rank"]),
        )
        print(
            "Final-layer control rank:",
            int(r["control_rank"]),
        )

    print("\n" + "=" * 80)
    print("PRIVATE VS NON-PERSONAL CONTINUATION")
    print("=" * 80)
    print(continuation.to_string(index=False))

    summary = {
        "entry_id": case["entry_id"],
        "generation_index": case["generation_index"],
        "target_model": target_model,
        "control_model": control_model,
        "first_injected_phrase": case["first_injected_phrase"],
        "first_target_above_base_layer": (
            int(positive.iloc[0]["layer"])
            if len(positive)
            else None
        ),
        "final_layer_target_minus_base_logprob": (
            float(
                final.iloc[0]["target_minus_base_logprob"]
            )
            if len(final)
            else None
        ),
    }

    (out / "generic_analysis_summary.json").write_text(
        json.dumps(summary, indent=2)
    )

    print("\nSaved:")
    print(" representation_drift_generic.csv")
    print(" generated_trajectory_generic.csv")
    print(" first_private_token_logit_delta.csv")
    print(" generic_analysis_summary.json")


if __name__ == "__main__":
    main()
