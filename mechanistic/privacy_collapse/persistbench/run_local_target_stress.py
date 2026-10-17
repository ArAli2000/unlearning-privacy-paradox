#!/usr/bin/env python3
"""Generate exactly three target-locked PersistBench stress pairs sequentially."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import validate as validate_schema
from openai import OpenAI
from transformers import AutoTokenizer

import pipeline as pp
from pair_validation import validate_pair
from run_remote import PAIR_SCHEMA
from token_audit import ordinary_token_ids, tokenize_rendered_text


FINAL_SELECTION_SHA256 = "a2f96ccceef6964076a9b3be83a8d12ed22152ee0d89467a502e756a3136c5bf"
STRESS_TARGETS = [
    ("pb-paired-008-cda672613fff", 2),
    ("pb-paired-026-c24dc8d5a24c", 7),
    ("pb-paired-036-d75dbf84413d", 4),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def token_audit_for_pair(tokenizer: Any, messages: list[dict[str, str]], generated: dict[str, Any]) -> dict[str, Any]:
    prompt_rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    prompt_ids = tokenize_rendered_text(tokenizer, prompt_rendered)
    result: dict[str, Any] = {}
    for condition in ("safe", "leaky"):
        text = generated[f"{condition}_response"]
        lexical_ids = ordinary_token_ids(tokenizer(text, add_special_tokens=False))
        full_rendered = tokenizer.apply_chat_template(
            messages + [{"role": "assistant", "content": text}],
            tokenize=False,
            add_generation_prompt=False,
        )
        full_ids = tokenize_rendered_text(tokenizer, full_rendered)
        response_start = full_rendered.rfind(text)
        if response_start < 0:
            raise ValueError("response text is absent from rendered full conversation")
        response_end = response_start + len(text)
        through_lexical_ids = tokenize_rendered_text(tokenizer, full_rendered[:response_end])
        lexical_end = len(through_lexical_ids) - 1
        eos_appended = full_ids[-1] == tokenizer.eos_token_id and lexical_end < len(full_ids) - 1
        result[condition] = {
            "response_lexical_token_count": len(lexical_ids),
            "full_sequence_token_count": len(full_ids),
            "prompt_token_count": len(prompt_ids),
            "last_full_sequence_token_id": full_ids[-1],
            "last_full_sequence_token_text": tokenizer.decode([full_ids[-1]]),
            "last_lexical_response_token_id": through_lexical_ids[-1],
            "last_lexical_response_token_text": tokenizer.decode([through_lexical_ids[-1]]),
            "last_lexical_response_position_in_full_sequence": lexical_end,
            "eos_automatically_appended_by_template": eos_appended,
            "later_extraction_position": lexical_end,
            "later_extraction_target": "last lexical response token, excluding template-added EOS",
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    gen = cfg["generator"]
    assert gen["backend"] == "vllm_openai_compatible"
    assert gen["model"] == "mistralai/Mistral-7B-Instruct-v0.3"
    assert gen["revision"] == "c170c708c41dac9275d15a8fff4eca08d52bab71"
    assert gen["dtype"] == "bfloat16"
    assert gen["temperature"] == 0 and gen["seed"] == 26082450 and gen["max_tokens"] == 1200
    assert gen["response_format"] == "json_schema"
    assert Path(gen["snapshot"]).is_dir()
    assert sha256(pp.FINAL_TARGET_SELECTION) == FINAL_SELECTION_SHA256

    manifest = json.loads(pp.MANIFEST.read_text())
    selection_file = json.loads(pp.FINAL_TARGET_SELECTION.read_text())
    by_pair = {row["pair_id"]: row for row in manifest["records"]}
    selections = {row["pair_id"]: row for row in selection_file["records"]}
    for pair_id, target_index in STRESS_TARGETS:
        assert selections[pair_id]["final_status"] == "GENERATION_ELIGIBLE"
        assert selections[pair_id]["selected_target_memory_index"] == target_index
        assert selections[pair_id]["selected_target_memory_text"] == by_pair[pair_id]["memories"][target_index]

    job_id = os.environ.get("SLURM_JOB_ID", "local")
    root = pp.HERE / "outputs/local_mistral_target_stress_v1" / f"job_{job_id}"
    if root.exists():
        raise RuntimeError(f"stress output directory already exists: {root}")
    root.mkdir(parents=True, exist_ok=False)
    tokenizer = AutoTokenizer.from_pretrained(gen["snapshot"], local_files_only=True)
    client = OpenAI(base_url=gen["base_url"], api_key=gen["api_key"], max_retries=0)
    summaries: list[dict[str, Any]] = []

    for ordinal, (pair_id, _) in enumerate(STRESS_TARGETS, start=1):
        row, selection = by_pair[pair_id], selections[pair_id]
        user_prompt = pp.generation_prompt(row, selection)
        messages = [{"role": "system", "content": pp.GEN_SYSTEM}, {"role": "user", "content": user_prompt}]
        raw_path = root / f"{ordinal:02d}_{pair_id}_raw.json"
        audit_path = root / f"{ordinal:02d}_{pair_id}_eos_audit.json"
        failure_path = root / f"{ordinal:02d}_{pair_id}_failure.json"
        try:
            started = now()
            response = client.chat.completions.create(
                model=gen["served_model"], messages=messages, temperature=gen["temperature"],
                seed=gen["seed"], max_tokens=gen["max_tokens"],
                response_format={"type": "json_schema", "json_schema": {
                    "name": "persistbench_target_locked_pair_v2", "strict": True, "schema": PAIR_SCHEMA,
                }},
            )
            completed = now()
            choice = response.choices[0]
            generated = json.loads(choice.message.content or "{}")
            validate_schema(generated, PAIR_SCHEMA)
            structural = validate_pair(row, selection, generated)
            raw_result = {
                "schema_version": 2, "job_id": job_id, "ordinal": ordinal,
                "pair_id": pair_id, "persistbench_id": row["persistbench_id"],
                "memory_domain": row["memory_domain"], "query_domain": row["query_domain"],
                "original_query": row["query"], "memories": row["memories"],
                "frozen_target_memory_index": selection["selected_target_memory_index"],
                "frozen_target_memory_text": selection["selected_target_memory_text"],
                "prohibited_memory_indices": [i for i in range(len(row["memories"])) if i != selection["selected_target_memory_index"]],
                "generated": generated,
                "schema_validation": {"status": "passed", "schema_name": "persistbench_target_locked_pair_v2"},
                "structural_validation": structural,
                "generator_provenance": {
                    "backend": gen["backend"], "requested_model": gen["model"],
                    "served_model": gen["served_model"], "returned_model": response.model,
                    "snapshot": gen["snapshot"], "revision": gen["revision"], "dtype": gen["dtype"],
                    "parameters": {"temperature": gen["temperature"], "seed": gen["seed"],
                                   "max_tokens": gen["max_tokens"], "response_format": "strict_json_schema"},
                    "started_utc": started, "completed_utc": completed, "response_id": response.id,
                    "finish_reason": choice.finish_reason, "stop_reason": getattr(choice, "stop_reason", None),
                    "usage": response.usage.model_dump() if response.usage else None,
                    "system_prompt": pp.GEN_SYSTEM, "user_prompt": user_prompt,
                    "final_target_selection_sha256": FINAL_SELECTION_SHA256,
                },
            }
            # Persist the complete schema/structural result before downstream EOS auditing.
            write_json_exclusive(raw_path, raw_result)
            token_audit = token_audit_for_pair(tokenizer, messages, generated)
            audit_result = {
                "schema_version": 2, "job_id": job_id, "pair_id": pair_id,
                "raw_generation_artifact": str(raw_path), "status": "passed",
                "tokenizer": gen["snapshot"], "eos_token_id": tokenizer.eos_token_id,
                "token_audit": token_audit,
            }
            write_json_exclusive(audit_path, audit_result)
            summaries.append({"pair_id": pair_id, "raw_artifact": str(raw_path),
                              "audit_artifact": str(audit_path), "schema_status": "passed",
                              "structural_status": structural["status"], "eos_audit_status": "passed"})
        except Exception as exc:
            write_json_exclusive(failure_path, {
                "schema_version": 2, "job_id": job_id, "pair_id": pair_id,
                "raw_generation_artifact": str(raw_path) if raw_path.exists() else None,
                "status": "failed", "error": {"type": type(exc).__name__, "message": str(exc),
                                                     "timestamp_utc": now(), "traceback": traceback.format_exc()},
            })
            summaries.append({"pair_id": pair_id, "status": "failed", "failure_artifact": str(failure_path),
                              "raw_artifact": str(raw_path) if raw_path.exists() else None})

    summary = {"schema_version": 2, "job_id": job_id, "requested_pair_count": 3,
               "generation_request_count": 3, "pairs": summaries}
    write_json_exclusive(root / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    if any(item.get("status") == "failed" for item in summaries):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
