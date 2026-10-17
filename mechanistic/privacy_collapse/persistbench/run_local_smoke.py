#!/usr/bin/env python3
"""Generate exactly one frozen PersistBench pair from a local vLLM server."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import validate as validate_schema
from openai import OpenAI
from transformers import AutoTokenizer

import pipeline as pp
from run_remote import PAIR_SCHEMA
from token_audit import ordinary_token_ids, tokenize_rendered_text


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def words(text: str) -> int:
    return len(text.split())


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    gen = cfg["generator"]
    workflow = cfg["workflow"]
    root = pp.HERE / "outputs" / workflow["output_namespace"]
    job_id = os.environ.get("SLURM_JOB_ID", "local")
    raw_artifact = root / f"smoke_generation_raw_{job_id}.json"
    audit_artifact = root / f"smoke_token_audit_{job_id}.json"
    audit_failure = root / f"smoke_token_audit_failure_{job_id}.json"
    if list(root.glob("smoke_generation_raw_*.json")):
        raise RuntimeError("a valid raw smoke generation already exists; refusing another request")

    assert gen["backend"] == "vllm_openai_compatible"
    assert gen["model"] == "mistralai/Mistral-7B-Instruct-v0.3"
    assert gen["revision"] == "c170c708c41dac9275d15a8fff4eca08d52bab71"
    assert Path(gen["snapshot"]).is_dir()
    assert gen["dtype"] == "bfloat16"
    assert gen["temperature"] == 0
    assert gen["seed"] == 26082450
    assert gen["max_tokens"] == 1200
    assert gen["response_format"] == "json_schema"
    assert workflow["output_namespace"] == "local_mistral_qwen_v1"

    records = json.loads(pp.MANIFEST.read_text())["records"]
    row = next(x for x in records if x["pair_id"] == workflow["smoke_pair_id"])
    request = {
        "model": gen["served_model"],
        "messages": [
            {"role": "system", "content": pp.GEN_SYSTEM},
            {"role": "user", "content": pp.generation_prompt(row)},
        ],
        "temperature": gen["temperature"],
        "seed": gen["seed"],
        "max_tokens": gen["max_tokens"],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "persistbench_pair_v1",
                "strict": True,
                "schema": PAIR_SCHEMA,
            },
        },
    }
    client = OpenAI(base_url=gen["base_url"], api_key=gen["api_key"], max_retries=0)
    started = now()
    response = client.chat.completions.create(**request)
    completed = now()
    choice = response.choices[0]
    generated = json.loads(choice.message.content or "{}")
    validate_schema(generated, PAIR_SCHEMA)
    idx = generated["leaked_memory_index"]
    assert generated["pair_id"] == row["pair_id"]
    assert isinstance(idx, int) and 0 <= idx < len(row["memories"])
    assert generated["leaked_memory_quote"] == row["memories"][idx]

    provenance = {
        "backend": gen["backend"],
        "requested_model": gen["model"],
        "served_model": gen["served_model"],
        "returned_model": response.model,
        "snapshot": gen["snapshot"],
        "revision": gen["revision"],
        "dtype": gen["dtype"],
        "parameters": {
            "temperature": gen["temperature"],
            "seed": gen["seed"],
            "max_tokens": gen["max_tokens"],
            "response_format": "strict_json_schema",
            "schema_name": "persistbench_pair_v1",
        },
        "started_utc": started,
        "completed_utc": completed,
        "response_id": response.id,
        "finish_reason": choice.finish_reason,
        "stop_reason": getattr(choice, "stop_reason", None),
        "usage": response.usage.model_dump() if response.usage else None,
        "system_prompt": pp.GEN_SYSTEM,
        "user_prompt": pp.generation_prompt(row),
    }
    raw_result = {
        "schema_version": 1,
        "job_id": job_id,
        "pair_id": row["pair_id"],
        "attempt": 1,
        "memories": row["memories"],
        "original_query": row["query"],
        "safe_response": generated["safe_response"],
        "leaky_response": generated["leaky_response"],
        "leaked_memory_index": idx,
        "leaked_memory_text": generated["leaked_memory_quote"],
        "contextual_mismatch": generated["contextual_mismatch"],
        "matching_strategy": generated["matching_strategy"],
        "generated": generated,
        "schema_validation": {
            "pair_schema_valid": True,
            "pair_id_exact": True,
            "attribution_index_in_range": True,
            "attribution_quote_exact": True,
        },
        "generator_provenance": provenance,
    }
    write_json_exclusive(raw_artifact, raw_result)

    try:
        tokenizer = AutoTokenizer.from_pretrained(gen["snapshot"], local_files_only=True)
        token_audit: dict[str, Any] = {}
        base_messages = request["messages"]
        prompt_rendered = tokenizer.apply_chat_template(
            base_messages, tokenize=False, add_generation_prompt=True
        )
        prompt_ids = tokenize_rendered_text(tokenizer, prompt_rendered)
        for condition in ("safe", "leaky"):
            text = generated[f"{condition}_response"]
            lexical_ids = ordinary_token_ids(tokenizer(text, add_special_tokens=False))
            full_rendered = tokenizer.apply_chat_template(
                base_messages + [{"role": "assistant", "content": text}],
                tokenize=False,
                add_generation_prompt=False,
            )
            full_ids = tokenize_rendered_text(tokenizer, full_rendered)
            response_char_start = full_rendered.rfind(text)
            if response_char_start < 0:
                raise ValueError("response text is absent from rendered full conversation")
            response_char_end = response_char_start + len(text)
            through_lexical_ids = tokenize_rendered_text(tokenizer, full_rendered[:response_char_end])
            lexical_end = len(through_lexical_ids) - 1
            eos_appended = full_ids[-1] == tokenizer.eos_token_id and lexical_end < len(full_ids) - 1
            token_audit[condition] = {
                "word_count": words(text),
                "full_sequence_token_count": len(full_ids),
                "prompt_token_count": len(prompt_ids),
                "response_lexical_token_count": len(lexical_ids),
                "last_full_sequence_token_id": full_ids[-1],
                "last_full_sequence_token_text": tokenizer.decode([full_ids[-1]]),
                "last_lexical_response_token_id": through_lexical_ids[-1],
                "last_lexical_response_token_text": tokenizer.decode([through_lexical_ids[-1]]),
                "last_lexical_response_position_in_full_sequence": lexical_end,
                "eos_automatically_appended_by_template": eos_appended,
                "later_extraction_position": lexical_end,
                "later_extraction_target": "last lexical response token, excluding template-added EOS",
            }
        audit_result = {
            "schema_version": 1,
            "job_id": job_id,
            "pair_id": row["pair_id"],
            "raw_generation_artifact": str(raw_artifact),
            "status": "passed",
            "tokenizer": gen["snapshot"],
            "eos_token_id": tokenizer.eos_token_id,
            "token_audit": token_audit,
        }
        write_json_exclusive(audit_artifact, audit_result)
    except Exception as exc:
        write_json_exclusive(audit_failure, {
            "schema_version": 1,
            "job_id": job_id,
            "pair_id": row["pair_id"],
            "raw_generation_artifact": str(raw_artifact),
            "status": "failed",
            "error": {"type": type(exc).__name__, "message": str(exc), "timestamp_utc": now()},
        })
        raise
    print(json.dumps({"status": "passed", "raw_artifact": str(raw_artifact),
                      "audit_artifact": str(audit_artifact), "pair_id": row["pair_id"]}, indent=2))


if __name__ == "__main__":
    main()
