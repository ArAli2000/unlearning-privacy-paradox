#!/usr/bin/env python3
"""Build the activation-blind matched PrivacyLens 12-vs-12 study manifest."""

import csv
import json
from pathlib import Path

from transformers import AutoTokenizer

from extract_single_privacylens import DATA_PATH, MODEL_PATHS, build_prompt


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "mechanistic/outputs/privacy_population_12v12"
RESULT_ROOT = ROOT / "outputs/privacylens_qwen_tofufull_methods"
RESULT_PATHS = {
    "BASE": RESULT_ROOT / "qwen25_7b_tofufull_before/privacy_mcq_all493.json",
    "RMU": RESULT_ROOT / "qwen25_7b_after_rmu_from_tofufull/privacy_mcq_all493.json",
    "WGA": RESULT_ROOT / "qwen25_7b_after_wga_from_tofufull/privacy_mcq_all493.json",
}

# Selected without using mechanistic activations. Tuple order is degraded, stable, rationale.
PAIRS = [
    ("main25", "main28", "Self-related workplace information; Gmail+Notion; similar email disclosure and length."),
    ("main82", "main321", "Landlord disclosing a tenant's property information via Messenger+Notion."),
    ("main114", "main130", "Literature-derived sibling mental-health information shared with extended family."),
    ("main118", "main129", "Same literature-derived IPV-survivor routine disclosure by a friend over Messenger."),
    ("main204", "main258", "Airport design engineer handling sensitive security/project information via Gmail+Notion."),
    ("main210", "main217", "Addiction-support coordinator potentially sharing patient/group information from Notion."),
    ("main220", "main238", "Alumni coordinator handling third-party alumni records via Gmail+Notion; close length."),
    ("main257", "main491", "School professional disclosing another student's/team member's performance or behavior over Messenger."),
    ("main290", "main96", "School professional replying to a parent about sensitive information concerning another student; Messenger+Notion."),
    ("main292", "main250", "Student/applicant essays sent externally via Gmail+Notion; nearly identical length."),
    ("main297", "main281", "Bank manager disclosing third-party account balances to a family relation via Messenger+Notion."),
    ("main415", "main1", "Lawyer discussing an active client's case with unrelated personal contacts after consulting Notion; preserved anchor."),
]


def read_results(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {row["name"]: row for row in payload["results"]}


def transition(before: dict, after: dict) -> str:
    choice = {"A": "Yes", "B": "No"}
    return f"{choice[before['detected_choice']]} -> {choice[after['detected_choice']]}"


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    by_id = {item["name"]: item for item in data}
    results = {label: read_results(path) for label, path in RESULT_PATHS.items()}
    degraded = [
        sid for sid in by_id
        if results["BASE"][sid]["detected_choice"] == "B"
        and results["RMU"][sid]["detected_choice"] == "A"
    ]
    expected_degraded = [pair[0] for pair in PAIRS]
    if degraded != expected_degraded:
        raise RuntimeError(f"Derived degraded IDs differ from study design: {degraded}")
    stable_ids = [pair[1] for pair in PAIRS]
    if len(set(stable_ids)) != 12:
        raise RuntimeError("Stable controls are not unique")
    for sid in stable_ids:
        if transition(results["BASE"][sid], results["RMU"][sid]) != "No -> No":
            raise RuntimeError(f"Stable control {sid} is not No -> No")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATHS["BASE"], use_fast=True, trust_remote_code=True, local_files_only=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    lengths = {
        sid: len(tokenizer(build_prompt(by_id[sid], tokenizer)).input_ids)
        for pair in PAIRS for sid in pair[:2]
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    behavior_rows = []
    for pair_index, (degraded_id, stable_id, rationale) in enumerate(PAIRS, start=1):
        pair_id = f"P{pair_index:02d}"
        difference = lengths[degraded_id] - lengths[stable_id]
        for group, sid in (("stable", stable_id), ("degraded", degraded_id)):
            item = by_id[sid]
            seed, trajectory, vignette = item["seed"], item["trajectory"], item["vignette"]
            row = {
                "pair_id": pair_id,
                "stable_sample_id": stable_id,
                "degraded_sample_id": degraded_id,
                "group": group,
                "sample_id": sid,
                "prompt_token_length": lengths[sid],
                "degraded_minus_stable_token_length": difference,
                "data_type": seed["data_type"],
                "data_subject": seed["data_subject"],
                "data_sender": seed["data_sender"],
                "data_recipient": seed["data_recipient"],
                "transmission_principle": seed["transmission_principle"],
                "source": seed["source"],
                "tools": " | ".join(trajectory["toolkits"]),
                "final_action": trajectory["final_action"],
                "instruction": trajectory["user_instruction"],
                "scenario": vignette["story"],
                "matching_rationale": rationale,
            }
            for label in ("BASE", "RMU", "WGA"):
                result = results[label][sid]
                row[f"{label.lower()}_response"] = result["model_response_raw"]
                row[f"{label.lower()}_privacy_aware"] = result["is_privacy_aware"]
            row["rmu_transition"] = transition(results["BASE"][sid], results["RMU"][sid])
            row["wga_transition"] = transition(results["BASE"][sid], results["WGA"][sid])
            rows.append(row)
            behavior_rows.append({key: row[key] for key in (
                "pair_id", "sample_id", "group", "base_response", "rmu_response", "wga_response",
                "base_privacy_aware", "rmu_privacy_aware", "wga_privacy_aware",
                "rmu_transition", "wga_transition",
            )})

    for filename, output_rows in (("sample_manifest.csv", rows), ("behavior_summary.csv", behavior_rows)):
        with (OUTPUT_DIR / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
            writer.writeheader()
            writer.writerows(output_rows)

    lines = ["# PrivacyLens RMU 12-vs-12 matching", "",
             "Controls were selected using behavior labels, prompt lengths, and scenario metadata only, before population activation extraction.", "",
             "| Pair | Stable | Degraded | Lengths (stable/degraded) | Rationale |", "|---|---|---|---:|---|"]
    for i, (degraded_id, stable_id, rationale) in enumerate(PAIRS, 1):
        lines.append(f"| P{i:02d} | {stable_id} | {degraded_id} | {lengths[stable_id]} / {lengths[degraded_id]} | {rationale} |")
    lines += ["", f"Verified degraded set: {', '.join(degraded)}", ""]
    (OUTPUT_DIR / "matching_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(rows)} manifest rows for {len(PAIRS)} pairs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
