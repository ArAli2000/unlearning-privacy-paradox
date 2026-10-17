#!/usr/bin/env python3
"""Experiment 1: does BASE<->unlearned activation patching change free-generation
sycophancy on the cleaned HIGH_CONFIDENCE_FAILURE set?

The clean teacher-forced patching result (analysis/activation_patching_clean_audit/CLEAN_RERUN_REPORT.md)
is a fixed-continuation likelihood contrast. This script applies the same intervention
under autoregressive generation on the same examples.

Cases: analysis/activation_patching_clean_audit/clean_selection.json (10 HIGH_CONFIDENCE_FAILURE
treatment + 10 matched SAFE_TO_SAFE controls). See ../EXPERIMENT_PLAN.md.

Patching reuses ActivationDonor/generate from mechanistic/muse_news/muse_news_activation_patching.py
(dynamic import). At each decoding step the donor is rerun on the recipient's generated-so-far
sequence and only its last-position activation is spliced in, so no stale donor tensor is needed.

Layer ranges (0-indexed; translated to the 1-indexed `layers[i-1]` convention of generate()):
  early_L0-6       localization control
  mid_late_L14-20  primary range
  late_L21-27      primary range

Conditions per case:
  A_base_unpatched
  B_unlearned_unpatched
  C_forward_patch_<range>   recipient=unlearned, donor=BASE
  D_reverse_patch_<range>   recipient=BASE, donor=unlearned

Judging is done in separate scripts so a judge bug does not force a rerun of generation.
Results are written after every case and completed (persistbench_id, method, group)
triples are skipped on restart.

Output: exp1_generation/exp1_generations.json, exp1_generation_metadata.json
"""
from __future__ import annotations

import argparse
import gc
import importlib.util
import json
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[3]
EXP_DIR = Path(__file__).resolve().parent
OUT_DIR = EXP_DIR / "exp1_generation"

CLEAN_AUDIT_DIR = (
    ROOT / "mechanistic/experiments/muse_news_sycophancy_paradox/analysis/activation_patching_clean_audit"
)
CLEAN_SELECTION = CLEAN_AUDIT_DIR / "clean_selection.json"
NATIVE_MANIFEST = ROOT / "mechanistic/privacy_collapse/persistbench_native/manifests/native_sycophancy_200_v1.json"

# Reuse the autoregressive patching code as is.
_spec = importlib.util.spec_from_file_location(
    "muse_news_activation_patching", ROOT / "mechanistic/muse_news/muse_news_activation_patching.py"
)
apatch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(apatch)

MODEL_PATHS = apatch.MODEL_PATHS  # BASE / SatImp / SimNPO, see EXPERIMENT_PLAN.md
MAX_NEW_TOKENS = apatch.MAX_NEW_TOKENS  # 96, matches original PersistBench generation settings

# Translated from 0-indexed labels to apatch's 1-indexed `layers[i-1]` convention.
LAYER_RANGES_0IDX_LABELS = {
    "early_L0-6": list(range(1, 8)),  # -> 0-idx layers 0-6, == apatch.LAYER_RANGES["early"]
    "mid_late_L14-20": list(range(15, 22)),  # -> 0-idx layers 14-20, == apatch.LAYER_RANGES["middle_late"]
    "late_L21-27": list(range(22, 29)),  # -> 0-idx layers 21-27, == apatch.LAYER_RANGES["late"]
}


def load_cases() -> list[dict[str, Any]]:
    selection = json.loads(CLEAN_SELECTION.read_text(encoding="utf-8"))
    native = json.loads(NATIVE_MANIFEST.read_text(encoding="utf-8"))
    prompt_ids_by_id = {r["persistbench_id"]: r["prompt"]["effective_prompt_token_ids"] for r in native["records"]}

    cases = []
    for method, mv in selection["methods"].items():
        for group, transition in (("treatment", "SAFE_TO_FAILURE"), ("control", "SAFE_TO_SAFE")):
            for rec in mv[group]:
                pid = rec["persistbench_id"]
                if pid not in prompt_ids_by_id:
                    raise KeyError(f"{pid} not found in native sycophancy manifest {NATIVE_MANIFEST}")
                cases.append(
                    {
                        "persistbench_id": pid,
                        "method": method,
                        "group": group,
                        "transition": transition,
                        "manual_audit_reason": rec.get("manual_audit_reason"),
                        "matched_to_treatment_id": rec.get("matched_to_treatment_id"),
                        "base_score_teacher_forced_selection": rec["base_score"],
                        "unlearned_score_teacher_forced_selection": rec["unlearned_score"],
                        "query": rec["query"],
                        "memories": rec["memories"],
                        "prompt_token_ids": prompt_ids_by_id[pid],
                    }
                )
    return cases


def case_key(case: dict[str, Any]) -> str:
    return f"{case['persistbench_id']}::{case['method']}::{case['group']}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit-cases", type=int, default=None, help="Smoke-test: only run the first N cases."
    )
    parser.add_argument(
        "--layer-ranges",
        nargs="+",
        default=list(LAYER_RANGES_0IDX_LABELS.keys()),
        choices=list(LAYER_RANGES_0IDX_LABELS.keys()),
        help="Subset of layer ranges to run (default: all three).",
    )
    parser.add_argument("--out-name", default="exp1_generations.json")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; submit via SLURM")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / args.out_name

    cases = load_cases()
    if args.limit_cases:
        cases = cases[: args.limit_cases]
    print(
        f"Loaded {len(cases)} cases: "
        f"{sum(1 for c in cases if c['group']=='treatment')} treatment, "
        f"{sum(1 for c in cases if c['group']=='control')} control",
        flush=True,
    )

    layer_ranges = {k: LAYER_RANGES_0IDX_LABELS[k] for k in args.layer_ranges}
    print(f"Layer ranges this run: {list(layer_ranges.keys())}", flush=True)

    existing: dict[str, dict[str, Any]] = {}
    if out_path.exists():
        for rec in json.loads(out_path.read_text(encoding="utf-8")):
            existing[case_key(rec)] = rec
        print(f"Resuming: {len(existing)} cases already completed in {out_path}", flush=True)

    print("Loading BASE, SatImp, SimNPO...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )
    models = {}
    for label in ("BASE", "SatImp", "SimNPO"):
        models[label] = AutoModelForCausalLM.from_pretrained(
            MODEL_PATHS[label],
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
            local_files_only=True,
            attn_implementation="sdpa",
        ).eval()
        models[label].requires_grad_(False)
    base_model = models["BASE"]

    results = list(existing.values())
    for case in cases:
        key = case_key(case)
        if key in existing:
            continue
        method_model = models[case["method"]]
        prompt_ids = case["prompt_token_ids"]
        record = {k: v for k, v in case.items() if k != "prompt_token_ids"}
        record["conditions"] = {}

        t0 = time.time()
        record["conditions"]["A_base_unpatched"] = apatch.generate(
            base_model, base_model, tokenizer, prompt_ids, patch_layers=None
        )
        record["conditions"]["B_unlearned_unpatched"] = apatch.generate(
            method_model, method_model, tokenizer, prompt_ids, patch_layers=None
        )
        for range_name, layers in layer_ranges.items():
            record["conditions"][f"C_forward_patch_{range_name}"] = apatch.generate(
                method_model, base_model, tokenizer, prompt_ids, patch_layers=layers
            )
            record["conditions"][f"D_reverse_patch_{range_name}"] = apatch.generate(
                base_model, method_model, tokenizer, prompt_ids, patch_layers=layers
            )
        record["runtime_seconds"] = time.time() - t0
        print(
            f"  {case['persistbench_id'][:8]} [{case['method']}/{case['group']}] "
            f"done in {record['runtime_seconds']:.1f}s",
            flush=True,
        )

        results.append(record)
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for m in models.values():
        del m
    gc.collect()
    torch.cuda.empty_cache()

    metadata = {
        "source_selection": str(CLEAN_SELECTION.relative_to(ROOT)),
        "n_cases_requested": len(cases),
        "n_cases_completed": len(results),
        "n_treatment": sum(1 for c in cases if c["group"] == "treatment"),
        "n_control": sum(1 for c in cases if c["group"] == "control"),
        "layer_ranges_0indexed": {k: [i - 1 for i in v] for k, v in layer_ranges.items()},
        "max_new_tokens": MAX_NEW_TOKENS,
        "decoding": (
            "greedy (temperature 0) with HF-style repetition penalty 1.05; no KV cache "
            "(full recompute per step), identical to mechanistic/muse_news/muse_news_activation_patching.py"
        ),
        "conditions": [
            "A_base_unpatched",
            "B_unlearned_unpatched",
            "C_forward_patch_<range> (recipient=unlearned, donor=BASE)",
            "D_reverse_patch_<range> (recipient=BASE, donor=unlearned)",
        ],
        "note": (
            "Teacher-forced numbers reported earlier (CLEAN_RERUN_REPORT.md) are UNCHANGED and "
            "NOT reproduced here; this is the free-generation counterpart on the identical clean "
            "example set."
        ),
    }
    (OUT_DIR / "exp1_generation_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {out_path} and metadata.", flush=True)


if __name__ == "__main__":
    main()
