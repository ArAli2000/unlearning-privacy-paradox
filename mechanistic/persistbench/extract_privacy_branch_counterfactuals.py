#!/usr/bin/env python3

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


ROOT = Path(__file__).resolve().parents[2]


CASES = [
    {
        "case": "RMU Case 1",
        "case_dir": ROOT / "mechanistic/outputs/single_persistbench_case_rmu_case1",
        "target_model": "RMU",

        # We deliberately include "my" in the shared prefix.
        # The meaningful decision is therefore:
        #     home  vs  current
        "marker": "related to my",

        "private": " home and financial stability",
        "safe": " current workload and academic responsibilities",
    },

    {
        "case": "RMU Case 2",
        "case_dir": ROOT / "mechanistic/outputs/single_persistbench_case_rmu_case2",
        "target_model": "RMU",

        # Decision:
        #     perspective  vs  goal
        "marker": "Given your",

        "private": (
            " perspective on capitalist systems and your belief "
            "in ethical wealth distribution"
        ),

        "safe": (
            " goal of minimizing estate taxes and protecting "
            "your children's assets"
        ),
    },

    {
        "case": "WGA Case 1",
        "case_dir": ROOT / "mechanistic/outputs/single_persistbench_case_wga_case1",
        "target_model": "WGA",

        # Decision:
        #     user  vs  natural
        "marker": "Incorporate motifs inspired by the",

        "private": (
            " user’s favorite hiking spots, like the Columbia River Gorge"
        ),

        "safe": (
            " natural landscape, such as rivers, forests, and mountain settings"
        ),
    },
]


MODEL_ROOTS = {
    "BASE": ROOT / "saves/finetune/tofu_Qwen2.5-7B-Instruct_full",

    "RMU": (
        ROOT
        / "saves/unlearn/"
          "proper_qwen25_7b_rmu_from_tofufull_selectionproxy_savebest/"
          "checkpoint-104"
    ),

    "WGA": (
        ROOT
        / "saves/unlearn/"
          "proper_qwen25_7b_wga_from_tofufull_selectionproxy_savebest/"
          "checkpoint-104"
    ),
}


def resolve_model_path(path: Path) -> Path:
    """Use path directly if it is a HF model, otherwise latest checkpoint."""
    if (path / "config.json").exists():
        return path

    checkpoints = list(path.glob("checkpoint-*"))

    if not checkpoints:
        raise FileNotFoundError(
            f"No config.json or checkpoint-* found under {path}"
        )

    def number(p: Path) -> int:
        try:
            return int(p.name.split("-")[-1])
        except Exception:
            return -1

    return max(checkpoints, key=number)


def collect_strings(
    value: Any,
    path: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], str]]:
    out = []

    if isinstance(value, str):
        out.append((path, value))

    elif isinstance(value, dict):
        for key, child in value.items():
            out.extend(
                collect_strings(child, path + (str(key),))
            )

    elif isinstance(value, list):
        for i, child in enumerate(value):
            out.extend(
                collect_strings(child, path + (str(i),))
            )

    return out


def find_target_response(
    case_dir: Path,
    target_model: str,
    injection_phrase: str,
) -> tuple[str, str]:

    selected_path = case_dir / "selected_case.json"

    selected = json.loads(
        selected_path.read_text(encoding="utf-8")
    )

    matches = []

    for path, text in collect_strings(selected):
        if injection_phrase.lower() not in text.lower():
            continue

        path_text = ".".join(path).lower()

        score = 0

        if target_model.lower() in path_text:
            score += 100

        if any(
            word in path_text
            for word in ["response", "generation", "output"]
        ):
            score += 50

        if "memory" in path_text:
            score -= 200

        if "query" in path_text:
            score -= 100

        # Responses are normally much longer than a memory item.
        score += min(len(text), 5000) / 5000

        matches.append(
            (score, ".".join(path), text)
        )

    if not matches:
        raise RuntimeError(
            f"Could not find target response in {selected_path} "
            f"containing injection phrase:\n{injection_phrase}"
        )

    matches.sort(key=lambda x: x[0], reverse=True)

    _, chosen_path, response = matches[0]

    return chosen_path, response


def prepare_case(cfg, tokenizer):
    case_dir = cfg["case_dir"]

    meta = json.loads(
        (case_dir / "extraction_metadata.json")
        .read_text(encoding="utf-8")
    )

    prompt_ids = meta["prompt_reconstruction"]["token_ids"]

    injection_phrase = meta["injection"]["phrase"]

    response_path, target_response = find_target_response(
        case_dir,
        cfg["target_model"],
        injection_phrase,
    )

    marker = cfg["marker"]

    marker_pos = target_response.lower().find(
        marker.lower()
    )

    if marker_pos < 0:
        raise RuntimeError(
            f"\nMarker not found for {cfg['case']}:\n"
            f"  {marker}\n\n"
            f"Target response begins:\n"
            f"{target_response[:1500]}"
        )

    end = marker_pos + len(marker)

    # Preserve exact capitalization / punctuation from the stored response.
    response_prefix = target_response[:end]

    prefix_ids = tokenizer.encode(
        response_prefix,
        add_special_tokens=False,
    )

    branches = {}

    for branch_name in ["private", "safe"]:
        continuation = cfg[branch_name]

        complete_response = response_prefix + continuation

        complete_ids = tokenizer.encode(
            complete_response,
            add_special_tokens=False,
        )

        if complete_ids[:len(prefix_ids)] != prefix_ids:
            raise RuntimeError(
                f"Tokenizer boundary changed for "
                f"{cfg['case']} / {branch_name}.\n"
                f"Prefix should be a token-prefix of full branch."
            )

        continuation_ids = complete_ids[len(prefix_ids):]

        if not continuation_ids:
            raise RuntimeError(
                f"No continuation tokens for "
                f"{cfg['case']} / {branch_name}"
            )

        branches[branch_name] = {
            "text": continuation,
            "ids": continuation_ids,
            "tokens": tokenizer.convert_ids_to_tokens(
                continuation_ids
            ),
        }

    if (
        branches["private"]["ids"][0]
        == branches["safe"]["ids"][0]
    ):
        raise RuntimeError(
            f"{cfg['case']} does not actually branch at the "
            f"first candidate token."
        )

    return {
        **cfg,
        "prompt_ids": prompt_ids,
        "response_path": response_path,
        "response_prefix": response_prefix,
        "prefix_ids": prefix_ids,
        "branches": branches,
        "prompt_sha256": (
            meta["prompt_reconstruction"]["prompt_ids_sha256"]
        ),
    }


def project_hidden_to_logits(model, h, layer_index, last_index):
    """Intermediate hidden states -> final RMS norm -> lm_head. The final saved hidden state is already normalized."""

    if layer_index == last_index:
        projected = h
    else:
        projected = model.model.norm(h)

    return model.lm_head(projected).float()


def token_logprob_and_rank(logits, token_id: int):
    logits = logits.squeeze(0)

    chosen = logits[token_id]

    log_z = torch.logsumexp(logits, dim=-1)

    logprob = chosen - log_z

    rank = int(
        (logits > chosen).sum().item() + 1
    )

    return float(logprob.item()), rank


@torch.inference_mode()
def score_first_branch_across_layers(
    model,
    prepared,
    device,
):
    """Same context for PRIVATE and SAFE; at every hidden layer compute
        score(private first token) - score(safe first token). This is the branch-point test.
    """

    ids = (
        prepared["prompt_ids"]
        + prepared["prefix_ids"]
    )

    input_ids = torch.tensor(
        [ids],
        dtype=torch.long,
        device=device,
    )

    outputs = model.model(
        input_ids=input_ids,
        output_hidden_states=True,
        use_cache=False,
        return_dict=True,
    )

    hidden_states = outputs.hidden_states

    private_id = prepared["branches"]["private"]["ids"][0]
    safe_id = prepared["branches"]["safe"]["ids"][0]

    rows = []

    last_index = len(hidden_states) - 1

    for layer, hidden in enumerate(hidden_states):

        # Last input position predicts the next token.
        h = hidden[:, -1, :]

        logits = project_hidden_to_logits(
            model,
            h,
            layer,
            last_index,
        )

        private_lp, private_rank = token_logprob_and_rank(
            logits,
            private_id,
        )

        safe_lp, safe_rank = token_logprob_and_rank(
            logits,
            safe_id,
        )

        rows.append(
            {
                "layer": layer,

                "private_first_token_id": private_id,
                "private_first_token": (
                    prepared["branches"]["private"]["tokens"][0]
                ),

                "safe_first_token_id": safe_id,
                "safe_first_token": (
                    prepared["branches"]["safe"]["tokens"][0]
                ),

                "private_log_probability": private_lp,
                "safe_log_probability": safe_lp,

                "private_minus_safe": (
                    private_lp - safe_lp
                ),

                "private_rank": private_rank,
                "safe_rank": safe_rank,
            }
        )

    del outputs, hidden_states, input_ids

    return rows


@torch.inference_mode()
def score_sequence(
    model,
    prepared,
    branch_name,
    device,
):
    """
    Teacher-force one candidate continuation and compute the final-model
    log probability of every continuation token.
    """

    prompt_ids = prepared["prompt_ids"]
    prefix_ids = prepared["prefix_ids"]

    candidate_ids = prepared["branches"][branch_name]["ids"]

    all_ids = (
        prompt_ids
        + prefix_ids
        + candidate_ids
    )

    input_ids = torch.tensor(
        [all_ids],
        dtype=torch.long,
        device=device,
    )

    outputs = model.model(
        input_ids=input_ids,
        output_hidden_states=False,
        use_cache=False,
        return_dict=True,
    )

    hidden = outputs.last_hidden_state

    candidate_start = (
        len(prompt_ids)
        + len(prefix_ids)
    )

    candidate_end = (
        candidate_start
        + len(candidate_ids)
    )

    # Hidden at position t predicts token t+1.
    predictor_hidden = hidden[
        :,
        candidate_start - 1 : candidate_end - 1,
        :,
    ]

    logits = model.lm_head(
        predictor_hidden
    ).float()[0]

    target = torch.tensor(
        candidate_ids,
        dtype=torch.long,
        device=device,
    )

    chosen_logits = logits.gather(
        1,
        target.unsqueeze(1),
    ).squeeze(1)

    log_z = torch.logsumexp(
        logits,
        dim=-1,
    )

    token_logprobs = (
        chosen_logits - log_z
    )

    chosen_ranks = (
        (logits > chosen_logits.unsqueeze(1))
        .sum(dim=1)
        + 1
    )

    token_rows = []

    tokens = prepared["branches"][branch_name]["tokens"]

    for i, (
        token_id,
        token,
        lp,
        rank,
    ) in enumerate(
        zip(
            candidate_ids,
            tokens,
            token_logprobs.tolist(),
            chosen_ranks.tolist(),
        )
    ):
        token_rows.append(
            {
                "branch": branch_name,
                "branch_token_index": i,
                "token_id": token_id,
                "token": token,
                "log_probability": float(lp),
                "rank": int(rank),
            }
        )

    result = {
        "branch": branch_name,
        "token_count": len(candidate_ids),

        # Total log probability naturally penalizes longer sequences.
        "sum_log_probability": float(
            token_logprobs.sum().item()
        ),

        # Main sequence-level comparison because branches have
        # slightly different token lengths.
        "mean_log_probability": float(
            token_logprobs.mean().item()
        ),

        "first_token_log_probability": float(
            token_logprobs[0].item()
        ),

        "first_token_rank": int(
            chosen_ranks[0].item()
        ),
    }

    del (
        outputs,
        hidden,
        predictor_hidden,
        logits,
        input_ids,
    )

    return result, token_rows


def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate branches and tokenization without loading a model.",
    )

    p.add_argument(
        "--output-dir",
        type=Path,
        default=(
            ROOT
            / "mechanistic/outputs/"
              "privacy_branch_counterfactuals"
        ),
    )

    return p.parse_args()


def main():
    args = parse_args()

    base_path = resolve_model_path(
        MODEL_ROOTS["BASE"]
    )

    print("Tokenizer source:", base_path)

    tokenizer = AutoTokenizer.from_pretrained(
        str(base_path),
        trust_remote_code=True,
    )

    prepared_cases = [
        prepare_case(cfg, tokenizer)
        for cfg in CASES
    ]

    print("\n" + "=" * 100)
    print("BRANCH DEFINITIONS")
    print("=" * 100)

    for case in prepared_cases:

        print(f"\n{case['case']}")
        print("Target method:", case["target_model"])
        print("Response found at:", case["response_path"])

        print(
            "\nShared prefix tail:\n",
            repr(case["response_prefix"][-250:]),
        )

        print("\nPRIVATE:")
        print(case["branches"]["private"]["text"])
        print(
            "tokens:",
            case["branches"]["private"]["tokens"],
        )

        print("\nSAFE:")
        print(case["branches"]["safe"]["text"])
        print(
            "tokens:",
            case["branches"]["safe"]["tokens"],
        )

        print(
            "\nFIRST ACTUAL DECISION:",
            case["branches"]["private"]["tokens"][0],
            "vs",
            case["branches"]["safe"]["tokens"][0],
        )

        print("-" * 100)

    if args.dry_run:
        print(
            "\nDRY RUN COMPLETE — no model loaded."
        )
        return

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is required. Do not run the full experiment "
            "on the login node."
        )

    device = torch.device("cuda")

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    layer_rows = []
    sequence_rows = []
    token_rows = []

    model_paths = {
        name: resolve_model_path(path)
        for name, path in MODEL_ROOTS.items()
    }

    for model_name in ["BASE", "RMU", "WGA"]:

        model_path = model_paths[model_name]

        print("\n" + "#" * 100)
        print("LOADING", model_name)
        print(model_path)
        print("#" * 100)

        model = AutoModelForCausalLM.from_pretrained(
            str(model_path),
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )

        model.to(device)
        model.eval()
        model.requires_grad_(False)

        for case in prepared_cases:

            print(
                f"\n{model_name} | {case['case']}"
            )

            # A) Most important analysis:
            #    the first real private-vs-safe branch token
            #    across all 29 hidden-state stages.

            layer_result = (
                score_first_branch_across_layers(
                    model,
                    case,
                    device,
                )
            )

            for row in layer_result:
                layer_rows.append(
                    {
                        "case": case["case"],
                        "target_model": (
                            case["target_model"]
                        ),
                        "model": model_name,
                        **row,
                    }
                )

            # B) Full continuation score

            branch_results = {}

            for branch in ["private", "safe"]:

                seq_result, per_token = score_sequence(
                    model,
                    case,
                    branch,
                    device,
                )

                branch_results[branch] = seq_result

                sequence_rows.append(
                    {
                        "case": case["case"],
                        "target_model": (
                            case["target_model"]
                        ),
                        "model": model_name,
                        **seq_result,
                    }
                )

                for row in per_token:
                    token_rows.append(
                        {
                            "case": case["case"],
                            "target_model": (
                                case["target_model"]
                            ),
                            "model": model_name,
                            **row,
                        }
                    )

            private = branch_results["private"]
            safe = branch_results["safe"]

            print(
                "  first-token/private-safe will be "
                "read from layerwise CSV"
            )

            print(
                "  mean sequence Δ private-safe:",
                (
                    private["mean_log_probability"]
                    - safe["mean_log_probability"]
                ),
            )

            torch.cuda.empty_cache()

        del model

        gc.collect()
        torch.cuda.empty_cache()

    layer_df = pd.DataFrame(layer_rows)
    sequence_df = pd.DataFrame(sequence_rows)
    token_df = pd.DataFrame(token_rows)

    # Compact preference table

    preference_rows = []

    for case in prepared_cases:

        case_name = case["case"]

        for model_name in ["BASE", "RMU", "WGA"]:

            s = sequence_df[
                (sequence_df["case"] == case_name)
                & (sequence_df["model"] == model_name)
            ]

            private = s[
                s["branch"] == "private"
            ].iloc[0]

            safe = s[
                s["branch"] == "safe"
            ].iloc[0]

            final_layer = layer_df[
                (layer_df["case"] == case_name)
                & (layer_df["model"] == model_name)
            ].sort_values("layer").iloc[-1]

            preference_rows.append(
                {
                    "case": case_name,
                    "target_model": (
                        case["target_model"]
                    ),
                    "model": model_name,

                    "private_first_token": (
                        final_layer[
                            "private_first_token"
                        ]
                    ),

                    "safe_first_token": (
                        final_layer[
                            "safe_first_token"
                        ]
                    ),

                    # Local branch test
                    "first_token_private_minus_safe": float(
                        final_layer[
                            "private_minus_safe"
                        ]
                    ),

                    "private_first_token_rank": int(
                        final_layer[
                            "private_rank"
                        ]
                    ),

                    "safe_first_token_rank": int(
                        final_layer[
                            "safe_rank"
                        ]
                    ),

                    # Length-normalized full continuation score
                    "private_mean_log_probability": float(
                        private[
                            "mean_log_probability"
                        ]
                    ),

                    "safe_mean_log_probability": float(
                        safe[
                            "mean_log_probability"
                        ]
                    ),

                    "mean_sequence_private_minus_safe": (
                        float(
                            private[
                                "mean_log_probability"
                            ]
                        )
                        - float(
                            safe[
                                "mean_log_probability"
                            ]
                        )
                    ),

                    # Also save raw totals, but do not use these as
                    # the main comparison when lengths differ.
                    "private_sum_log_probability": float(
                        private[
                            "sum_log_probability"
                        ]
                    ),

                    "safe_sum_log_probability": float(
                        safe[
                            "sum_log_probability"
                        ]
                    ),
                }
            )

    preference_df = pd.DataFrame(
        preference_rows
    )

    layer_path = (
        args.output_dir
        / "branch_first_token_layerwise.csv"
    )

    sequence_path = (
        args.output_dir
        / "branch_sequence_scores.csv"
    )

    token_path = (
        args.output_dir
        / "branch_token_scores.csv"
    )

    preference_path = (
        args.output_dir
        / "branch_preference_summary.csv"
    )

    layer_df.to_csv(
        layer_path,
        index=False,
    )

    sequence_df.to_csv(
        sequence_path,
        index=False,
    )

    token_df.to_csv(
        token_path,
        index=False,
    )

    preference_df.to_csv(
        preference_path,
        index=False,
    )

    metadata = {
        "cases": [
            {
                "case": x["case"],
                "target_model": x["target_model"],
                "response_path": x["response_path"],
                "prompt_sha256": x["prompt_sha256"],
                "response_prefix_tail": (
                    x["response_prefix"][-500:]
                ),
                "private": (
                    x["branches"]["private"]["text"]
                ),
                "safe": (
                    x["branches"]["safe"]["text"]
                ),
                "private_tokens": (
                    x["branches"]["private"]["tokens"]
                ),
                "safe_tokens": (
                    x["branches"]["safe"]["tokens"]
                ),
            }
            for x in prepared_cases
        ],

        "model_paths": {
            k: str(v)
            for k, v in model_paths.items()
        },

        "interpretation": {
            "first_token_private_minus_safe": (
                "Positive means that at the exact shared branch "
                "point, the model gives higher probability to the "
                "first PRIVATE token than to the first SAFE token."
            ),

            "mean_sequence_private_minus_safe": (
                "Positive means the teacher-forced private "
                "continuation has higher mean token log probability "
                "than the safe continuation. This is descriptive and "
                "not a causal result."
            ),
        },
    }

    (
        args.output_dir
        / "branch_experiment_metadata.json"
    ).write_text(
        json.dumps(
            metadata,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 100)
    print("FINAL BRANCH PREFERENCE SUMMARY")
    print("=" * 100)

    print(
        preference_df[
            [
                "case",
                "model",
                "private_first_token",
                "safe_first_token",
                "first_token_private_minus_safe",
                "private_first_token_rank",
                "safe_first_token_rank",
                "mean_sequence_private_minus_safe",
            ]
        ].to_string(index=False)
    )

    print("\nSaved:")
    print(preference_path)
    print(layer_path)
    print(sequence_path)
    print(token_path)


if __name__ == "__main__":
    main()
