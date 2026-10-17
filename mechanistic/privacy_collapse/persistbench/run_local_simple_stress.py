#!/usr/bin/env python3
"""Run exactly three independent SAFE calls and three independent LEAKY calls."""
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
from pair_validation import target_expression, words
from token_audit import ordinary_token_ids, tokenize_rendered_text

MANIFEST = pp.HERE / "manifests/cross_domain_simple_50_v1.json"
MANIFEST_SHA256 = "94b16f53180a20d9683dae9f4bc169c0834a55d3e40a14ac0f12d5aa61a90b57"
STRESS_TARGETS = [
    ("pb-paired-008-cda672613fff", 2),
    ("pb-paired-026-c24dc8d5a24c", 7),
    ("pb-paired-036-d75dbf84413d", 4),
]
SAFE_SCHEMA = {
    "type": "object", "properties": {"safe_response": {"type": "string"}},
    "required": ["safe_response"], "additionalProperties": False,
}
LEAKY_SCHEMA = {
    "type": "object", "properties": {
        "target_memory_index": {"type": "integer"},
        "target_memory_text": {"type": "string"},
        "leaky_response": {"type": "string"},
    },
    "required": ["target_memory_index", "target_memory_text", "leaky_response"],
    "additionalProperties": False,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def model_call(client: OpenAI, cfg: dict[str, Any], messages: list[dict[str, str]],
               schema_name: str, schema: dict[str, Any], transport_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    started = now()
    response = client.chat.completions.create(
        model=cfg["served_model"], messages=messages, temperature=cfg["temperature"],
        seed=cfg["seed"], max_tokens=cfg["max_tokens"],
        response_format={"type": "json_schema", "json_schema": {
            "name": schema_name, "strict": True, "schema": schema,
        }},
    )
    choice = response.choices[0]
    content = choice.message.content or "{}"
    # This is deliberately the first operation after receiving the response.
    write_json_exclusive(transport_path, {
        "response_id": response.id, "returned_model": response.model,
        "finish_reason": choice.finish_reason, "stop_reason": getattr(choice, "stop_reason", None),
        "content": content, "usage": response.usage.model_dump() if response.usage else None,
        "received_utc": now(),
    })
    value = json.loads(content)
    validate_schema(value, schema)
    return value, {
        "started_utc": started, "completed_utc": now(), "response_id": response.id,
        "returned_model": response.model, "finish_reason": choice.finish_reason,
        "usage": response.usage.model_dump() if response.usage else None,
        "system_prompt": messages[0]["content"], "user_prompt": messages[1]["content"],
    }


def eos_audit(tokenizer: Any, query: str, safe: str, leaky: str) -> dict[str, Any]:
    base = [{"role": "user", "content": query}]
    result: dict[str, Any] = {}
    for condition, text in (("safe", safe), ("leaky", leaky)):
        lexical_ids = ordinary_token_ids(tokenizer(text, add_special_tokens=False))
        rendered = tokenizer.apply_chat_template(
            base + [{"role": "assistant", "content": text}],
            tokenize=False, add_generation_prompt=False,
        )
        full_ids = tokenize_rendered_text(tokenizer, rendered)
        response_start = rendered.rfind(text)
        if response_start < 0:
            raise ValueError("response is absent from rendered conversation")
        through_ids = tokenize_rendered_text(tokenizer, rendered[:response_start + len(text)])
        endpoint = len(through_ids) - 1
        result[condition] = {
            "response_lexical_token_count": len(lexical_ids),
            "last_lexical_response_position_in_full_sequence": endpoint,
            "last_lexical_response_token_id": through_ids[-1],
            "last_lexical_response_token_text": tokenizer.decode([through_ids[-1]]),
            "template_final_token_id": full_ids[-1],
            "template_final_token_text": tokenizer.decode([full_ids[-1]]),
            "eos_token_id": tokenizer.eos_token_id,
            "eos_automatically_appended_by_template": full_ids[-1] == tokenizer.eos_token_id and endpoint < len(full_ids) - 1,
            "later_extraction_position": endpoint,
            "later_extraction_target": "last lexical response token, excluding template-added EOS",
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())["generator"]
    assert sha256(MANIFEST) == MANIFEST_SHA256
    assert cfg["backend"] == "vllm_openai_compatible"
    assert cfg["model"] == "mistralai/Mistral-7B-Instruct-v0.3"
    assert cfg["revision"] == "c170c708c41dac9275d15a8fff4eca08d52bab71"
    assert cfg["temperature"] == 0 and cfg["seed"] == 26082450 and cfg["max_tokens"] == 1200
    assert Path(cfg["snapshot"]).is_dir()

    manifest = json.loads(MANIFEST.read_text())
    design = manifest["generation_design"]
    rows = {row["pair_id"]: row for row in manifest["records"]}
    for pair_id, target_index in STRESS_TARGETS:
        assert rows[pair_id]["target_memory_index"] == target_index
        assert rows[pair_id]["target_memory_text"] == rows[pair_id]["memories"][target_index]

    job_id = os.environ.get("SLURM_JOB_ID", "local")
    root = pp.HERE / "outputs/local_mistral_simple_stress_v1" / f"job_{job_id}"
    root.mkdir(parents=True, exist_ok=False)
    tokenizer = AutoTokenizer.from_pretrained(cfg["snapshot"], local_files_only=True)
    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"], max_retries=0)
    summaries: list[dict[str, Any]] = []
    request_count = 0

    for ordinal, (pair_id, _) in enumerate(STRESS_TARGETS, start=1):
        row = rows[pair_id]
        stem = f"{ordinal:02d}_{pair_id}"
        try:
            safe_prompt = design["safe_user_prompt_template"].format(query=row["query"])
            safe_messages = [{"role": "system", "content": design["safe_system_prompt"]},
                             {"role": "user", "content": safe_prompt}]
            safe_prompt_text = "\n".join(message["content"] for message in safe_messages)
            assert design["safe_inputs"] == ["original_query"]
            assert all(memory not in safe_prompt_text for memory in row["memories"])
            assert row["memory_domain"] not in safe_prompt_text and row["query_domain"] not in safe_prompt_text
            request_count += 1
            safe_value, safe_provenance = model_call(
                client, cfg, safe_messages, "persistbench_simple_safe_v1", SAFE_SCHEMA,
                root / f"{stem}_safe_transport_raw.json",
            )
            write_json_exclusive(root / f"{stem}_safe_parsed.json", {
                "schema_version": 1, "job_id": job_id, "pair_id": pair_id,
                "safe_response": safe_value["safe_response"], "schema_validation": "passed",
                "safe_prompt_memory_isolation": "passed", "generator_provenance": safe_provenance,
            })

            target_json = json.dumps(row["target_memory_text"], ensure_ascii=False)
            leaky_prompt = design["leaky_user_prompt_template"].format(
                query=row["query"], target_memory_index=row["target_memory_index"],
                target_memory_text=row["target_memory_text"], target_memory_text_json=target_json,
            )
            leaky_messages = [{"role": "system", "content": design["leaky_system_prompt"]},
                              {"role": "user", "content": leaky_prompt}]
            leaky_prompt_text = "\n".join(message["content"] for message in leaky_messages)
            assert design["leaky_inputs"] == ["original_query", "target_memory_index", "target_memory_text"]
            assert all(memory not in leaky_prompt_text for i, memory in enumerate(row["memories"])
                       if i != row["target_memory_index"])
            request_count += 1
            leaky_value, leaky_provenance = model_call(
                client, cfg, leaky_messages, "persistbench_simple_leaky_v1", LEAKY_SCHEMA,
                root / f"{stem}_leaky_transport_raw.json",
            )
            attribution = {
                "index_exact": leaky_value["target_memory_index"] == row["target_memory_index"],
                "text_exact": leaky_value["target_memory_text"] == row["target_memory_text"],
                "manifest_memory_exact": row["target_memory_text"] == row["memories"][row["target_memory_index"]],
            }
            attribution["status"] = "passed" if all(attribution.values()) else "failed"
            write_json_exclusive(root / f"{stem}_leaky_parsed.json", {
                "schema_version": 1, "job_id": job_id, "pair_id": pair_id,
                "generated": leaky_value, "schema_validation": "passed",
                "target_attribution_validation": attribution,
                "leaky_prompt_non_target_memory_isolation": "passed", "generator_provenance": leaky_provenance,
            })

            safe, leaky = safe_value["safe_response"], leaky_value["leaky_response"]
            safe_words, leaky_words = len(words(safe)), len(words(leaky))
            ratio = leaky_words / safe_words if safe_words else float("inf")
            result_path = root / f"{stem}_result.json"
            write_json_exclusive(result_path, {
                "schema_version": 1, "job_id": job_id, "pair_id": pair_id,
                "persistbench_id": row["persistbench_id"], "query": row["query"],
                "target_memory_index": row["target_memory_index"], "target_memory_text": row["target_memory_text"],
                "safe_response": safe, "leaky_response": leaky,
                "safe_word_count": safe_words, "leaky_word_count": leaky_words,
                "leaky_to_safe_word_ratio": ratio, "word_ratio_target_range": [0.8, 1.2],
                "word_ratio_in_target_range": 0.8 <= ratio <= 1.2,
                "safe_schema_validation": "passed", "leaky_schema_validation": "passed",
                "target_attribution_validation": attribution,
                "lexical_target_expression_diagnostic": {
                    "safe": target_expression(safe, row["target_memory_text"]),
                    "leaky": target_expression(leaky, row["target_memory_text"]),
                },
            })
            audit_path = root / f"{stem}_eos_audit.json"
            write_json_exclusive(audit_path, {
                "schema_version": 1, "job_id": job_id, "pair_id": pair_id,
                "result_artifact": str(result_path), "status": "passed",
                "tokenizer": cfg["snapshot"], "token_audit": eos_audit(tokenizer, row["query"], safe, leaky),
            })
            summaries.append({"pair_id": pair_id, "status": "completed", "result_artifact": str(result_path),
                              "audit_artifact": str(audit_path), "target_attribution_status": attribution["status"]})
        except Exception as exc:
            failure_path = root / f"{stem}_failure.json"
            write_json_exclusive(failure_path, {
                "schema_version": 1, "job_id": job_id, "pair_id": pair_id, "status": "failed",
                "error": {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()},
            })
            summaries.append({"pair_id": pair_id, "status": "failed", "failure_artifact": str(failure_path)})

    write_json_exclusive(root / "summary.json", {
        "schema_version": 1, "job_id": job_id, "requested_pair_count": 3,
        "expected_model_call_count": 6, "model_request_count": request_count, "pairs": summaries,
        "manifest": str(MANIFEST), "manifest_sha256": MANIFEST_SHA256,
    })
    print(json.dumps(summaries, indent=2))
    if request_count != 6 or any(item["status"] == "failed" for item in summaries):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
