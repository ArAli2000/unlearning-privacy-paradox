#!/usr/bin/env python3
"""Freeze teacher-forced continuation cases for Phase 8 (layer-wise safe-vs-
failure continuation preference) of the MUSE-News sycophancy/cross-domain
mechanistic experiment. CPU-only; loads only the BASE tokenizer, no model
weights.

For every SAFE_TO_FAILURE row (per category/method) in
`paired_transitions.json`, and a reproducibly-sampled, size-matched control
set of SAFE_TO_SAFE rows, this freezes two teacher-forced candidate
continuations sharing the identical (with-memory) prompt:

- candidate_A: BASE's own stored generation-0 response (always the "safe"
  reference text).
- candidate_B: the unlearned method's own stored generation-0 response. For
  the FAILURE group this is the actual privacy-failing continuation; for the
  CONTROL group it is the unlearned model's own different-but-still-safe
  continuation, giving a same-machinery safe-vs-safe baseline.

Selection (which rows go in FAILURE/CONTROL) is fixed by the already-computed
transition labels in paired_transitions.json; it is not re-derived here, and
no case is chosen after inspecting activations.

Output: mechanistic/outputs/muse_news_sycophancy_mechanistic/manifests/
  continuation_cases_v1.json
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "mechanistic/outputs/muse_news_sycophancy_mechanistic"
NATIVE_DIR = ROOT / "mechanistic/privacy_collapse/persistbench_native"
PAIRED_TRANSITIONS = OUT_ROOT / "paired_transitions.json"
SEED = 20260919

NATIVE_MANIFESTS = {
    "sycophancy": NATIVE_DIR / "manifests/native_sycophancy_200_v1.json",
    "cross_domain": NATIVE_DIR / "manifests/native_cross_domain_200_v1.json",
}
BASE_MODEL_DIR = ROOT / "saves/finetune/muse_news_qwen25_7b_instruct_target"


def load_native_records(category: str) -> dict[str, dict[str, Any]]:
    data = json.loads(NATIVE_MANIFESTS[category].read_text(encoding="utf-8"))
    return {r["persistbench_id"]: r for r in data["records"]}


def main() -> None:
    paired = json.loads(PAIRED_TRANSITIONS.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(
        BASE_MODEL_DIR, use_fast=True, trust_remote_code=True, local_files_only=True
    )

    cases: list[dict[str, Any]] = []
    selection_summary: dict[str, Any] = {}

    for category in ("sycophancy", "cross_domain"):
        records = load_native_records(category)
        for method in ("SatImp", "SimNPO"):
            rows = paired["categories"][category][method]["rows"]
            failure_rows = [r for r in rows if r["transition"] == "SAFE_TO_FAILURE"]
            safe_rows = [r for r in rows if r["transition"] == "SAFE_TO_SAFE"]

            n_failure = len(failure_rows)
            rng = random.Random(SEED)
            control_rows = rng.sample(safe_rows, min(n_failure, len(safe_rows))) if n_failure > 0 else []

            selection_summary[f"{category}/{method}"] = {
                "n_failure_available": n_failure,
                "n_control_sampled": len(control_rows),
                "n_safe_available_for_sampling": len(safe_rows),
            }

            for group, group_rows in (("FAILURE", failure_rows), ("CONTROL", control_rows)):
                for row in group_rows:
                    pb_id = row["persistbench_id"]
                    record = records[pb_id]
                    prompt_ids = record["prompt"]["effective_prompt_token_ids"]
                    base_text = record["models"]["BASE"]["generated_response"]
                    method_text = record["models"][method]["generated_response"]
                    base_ids = tokenizer(base_text, add_special_tokens=False).input_ids
                    method_ids = tokenizer(method_text, add_special_tokens=False).input_ids
                    if len(base_ids) == 0 or len(method_ids) == 0:
                        raise RuntimeError(f"Empty tokenized response for {category}/{method}/{pb_id}")

                    cases.append(
                        {
                            "category": category,
                            "method": method,
                            "group": group,
                            "persistbench_id": pb_id,
                            "source_index": row["source_index"],
                            "transition": row["transition"],
                            "base_score": row["base_score"],
                            "unlearned_score": row["unlearned_score"],
                            "prompt_token_ids": prompt_ids,
                            "prompt_token_count": len(prompt_ids),
                            "candidate_A": {
                                "label": "BASE_response",
                                "text": base_text,
                                "token_ids": base_ids,
                                "token_count": len(base_ids),
                            },
                            "candidate_B": {
                                "label": f"{method}_response",
                                "text": method_text,
                                "token_ids": method_ids,
                                "token_count": len(method_ids),
                            },
                        }
                    )

    manifest = {
        "schema_version": 1,
        "name": "continuation_cases_v1",
        "seed": SEED,
        "selection_summary": selection_summary,
        "construction": (
            "candidate_A is always BASE's stored generation-0 response (safe reference). candidate_B is the "
            "unlearned method's stored generation-0 response: the actual privacy-failing text for FAILURE-group "
            "cases (SAFE_TO_FAILURE), and the method's own different-but-still-safe text for CONTROL-group cases "
            "(a size-matched random sample of SAFE_TO_SAFE rows, seed 20260919). Both candidates are teacher-forced "
            "after the identical (with-memory) prompt used for the original generation. Selection is fixed by "
            "paired_transitions.json and not re-derived from activations."
        ),
        "case_count": len(cases),
        "cases": cases,
    }
    out_path = OUT_ROOT / "manifests" / "continuation_cases_v1.json"
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path.relative_to(ROOT)}: {len(cases)} cases")
    for key, val in selection_summary.items():
        print(f"  {key}: {val}")


if __name__ == "__main__":
    main()
