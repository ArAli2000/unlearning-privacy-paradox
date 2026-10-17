#!/usr/bin/env python3
"""Corrective-validation example selection for the cleaned Phase-9 rerun.

Treatment set: ALL examples classified HIGH_CONFIDENCE_FAILURE in the manual audit
(`audit/manual_transition_audit.csv`) -- SatImp 6, SimNPO 4. AMBIGUOUS and
LIKELY_JUDGE_NOISE examples are excluded entirely, per the user's explicit instruction.

Control set: SAFE_TO_SAFE examples matched 1:1 (greedy nearest-neighbor, no replacement)
to each treatment example on, in priority order: (1) BASE judge score (exact match
required), (2) BASE response character length, (3) memory-block character length
(sum of memory strings, proxy for memory length), (4) prompt token length (from the
frozen native manifest's effective_prompt_token_ids, exact tokenized prompt length).
Approximately the same number of controls as treatments per method (6 SatImp, 4 SimNPO).

This script only reads frozen, existing files and writes new ones under this directory.
It does not modify `manifests/sycophancy_transition_groups.json` or the manual audit.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
EXP = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

AUDIT_CSV = EXP / "audit" / "manual_transition_audit.csv"
TRANSITIONS = EXP / "manifests" / "sycophancy_transition_groups.json"
NATIVE_MANIFEST = ROOT / "mechanistic/privacy_collapse/persistbench_native/manifests/native_sycophancy_200_v1.json"

METHODS = ["SatImp", "SimNPO"]


def load_audit() -> dict[str, list[dict]]:
    by_method: dict[str, list[dict]] = {m: [] for m in METHODS}
    with AUDIT_CSV.open() as fh:
        for row in csv.DictReader(fh):
            by_method[row["method"]].append(row)
    return by_method


def load_prompt_lengths() -> dict[str, int]:
    native = json.loads(NATIVE_MANIFEST.read_text(encoding="utf-8"))
    return {rec["persistbench_id"]: len(rec["prompt"]["effective_prompt_token_ids"]) for rec in native["records"]}


def memory_chars(memories: list[str]) -> int:
    return sum(len(m) for m in memories)


def main() -> None:
    audit = load_audit()
    transitions = json.loads(TRANSITIONS.read_text(encoding="utf-8"))
    prompt_len = load_prompt_lengths()

    selection = {"schema_version": 1, "name": "Cleaned Phase-9 corrective validation: example selection", "methods": {}}
    doc_lines = [
        "# Cleaned Phase-9 example selection (corrective validation)",
        "",
        "Source of truth for treatment examples: `audit/manual_transition_audit.csv`, "
        "classification == HIGH_CONFIDENCE_FAILURE only. AMBIGUOUS and LIKELY_JUDGE_NOISE excluded.",
        "",
        "Matching procedure for SAFE_TO_SAFE controls (greedy nearest-neighbor, no replacement, per method):",
        "1. BASE judge score must match exactly.",
        "2. Among score-matched candidates, minimize |base_response_chars(control) - base_response_chars(treatment)|.",
        "3. Tie-break by memory-block character length, then prompt token length.",
        "",
    ]

    for method in METHODS:
        treatment_rows = [r for r in audit[method] if r["classification"] == "HIGH_CONFIDENCE_FAILURE"]
        groups = transitions["methods"][method]["groups"]
        safe_to_failure_by_id = {it["persistbench_id"]: it for it in groups["SAFE_TO_FAILURE"]}
        safe_to_safe_pool = list(groups["SAFE_TO_SAFE"])  # copy; we will remove matched items

        treatment_items = []
        for r in treatment_rows:
            item = safe_to_failure_by_id[r["persistbench_id"]]
            item = dict(item)
            item["manual_audit_reason"] = r["reason"]
            item["prompt_token_len"] = prompt_len.get(item["persistbench_id"])
            item["base_response_chars"] = len(item["base_response"])
            item["memory_chars"] = memory_chars(item["memories"])
            treatment_items.append(item)

        matched_controls = []
        used_ids = set()
        for t in treatment_items:
            candidates = [
                c for c in safe_to_safe_pool
                if c["persistbench_id"] not in used_ids and c["base_score"] == t["base_score"]
            ]
            if not candidates:
                # relax exact score match only if no candidate exists at that score
                candidates = [c for c in safe_to_safe_pool if c["persistbench_id"] not in used_ids]
            def dist(c):
                c_resp_len = len(c["base_response"])
                c_mem_len = memory_chars(c["memories"])
                c_prompt_len = prompt_len.get(c["persistbench_id"], 0)
                return (
                    abs(c["base_score"] - t["base_score"]) * 100000,  # dominant term
                    abs(c_resp_len - t["base_response_chars"]),
                    abs(c_mem_len - t["memory_chars"]),
                    abs(c_prompt_len - (t["prompt_token_len"] or 0)),
                )
            best = min(candidates, key=dist)
            used_ids.add(best["persistbench_id"])
            best = dict(best)
            best["prompt_token_len"] = prompt_len.get(best["persistbench_id"])
            best["base_response_chars"] = len(best["base_response"])
            best["memory_chars"] = memory_chars(best["memories"])
            best["matched_to_treatment_id"] = t["persistbench_id"]
            matched_controls.append(best)

        selection["methods"][method] = {
            "n_treatment": len(treatment_items),
            "n_control": len(matched_controls),
            "treatment": treatment_items,
            "control": matched_controls,
        }

        doc_lines.append(f"## {method}")
        doc_lines.append("")
        doc_lines.append(f"Treatment (HIGH_CONFIDENCE_FAILURE, n={len(treatment_items)}):")
        doc_lines.append("")
        doc_lines.append("| persistbench_id | base_score | unl_score | base_resp_chars | mem_chars | prompt_tokens | reason |")
        doc_lines.append("|---|---|---|---|---|---|---|")
        for t in treatment_items:
            doc_lines.append(
                f"| {t['persistbench_id']} | {t['base_score']} | {t['unlearned_score']} | "
                f"{t['base_response_chars']} | {t['memory_chars']} | {t['prompt_token_len']} | "
                f"{t['manual_audit_reason'][:80]} |"
            )
        doc_lines.append("")
        doc_lines.append(f"Matched SAFE_TO_SAFE controls (n={len(matched_controls)}):")
        doc_lines.append("")
        doc_lines.append("| persistbench_id | matched_to | base_score | base_resp_chars | mem_chars | prompt_tokens |")
        doc_lines.append("|---|---|---|---|---|---|")
        for c in matched_controls:
            doc_lines.append(
                f"| {c['persistbench_id']} | {c['matched_to_treatment_id']} | {c['base_score']} | "
                f"{c['base_response_chars']} | {c['memory_chars']} | {c['prompt_token_len']} |"
            )
        doc_lines.append("")

    out_json = HERE / "clean_selection.json"
    out_json.write_text(json.dumps(selection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md = HERE / "clean_selection.md"
    out_md.write_text("\n".join(doc_lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    for method in METHODS:
        m = selection["methods"][method]
        print(method, "treatment:", [t["persistbench_id"][:10] for t in m["treatment"]])
        print(method, "controls:", [c["persistbench_id"][:10] for c in m["control"]])


if __name__ == "__main__":
    main()
