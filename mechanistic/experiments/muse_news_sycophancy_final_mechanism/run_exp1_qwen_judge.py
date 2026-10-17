#!/usr/bin/env python3
"""Judge every generation from run_exp1_generate.py with the legacy local Qwen2.5-7B-Instruct
PersistBench sycophancy judge (`simplified_local_judge_score`, imported dynamically), the same
judge as in the clean audit. All conditions are scored fresh. Results are written after every
case and already-judged cases are skipped on restart.

Input:  exp1_generation/exp1_generations.json
Output: exp1_generation/exp1_generations_qwen_judged.json
"""
from __future__ import annotations

import argparse
import gc
import importlib.util
import json
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[3]
EXP_DIR = Path(__file__).resolve().parent
OUT_DIR = EXP_DIR / "exp1_generation"

_spec = importlib.util.spec_from_file_location(
    "muse_news_activation_patching", ROOT / "mechanistic/muse_news/muse_news_activation_patching.py"
)
apatch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(apatch)

JUDGE_MODEL_ID = apatch.JUDGE_MODEL_ID  # Qwen/Qwen2.5-7B-Instruct


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-name", default="exp1_generations.json")
    parser.add_argument("--out-name", default="exp1_generations_qwen_judged.json")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; submit via SLURM")

    in_path = OUT_DIR / args.in_name
    out_path = OUT_DIR / args.out_name
    results: list[dict[str, Any]] = json.loads(in_path.read_text(encoding="utf-8"))

    already_judged = 0
    if out_path.exists():
        judged_by_key = {
            f"{r['persistbench_id']}::{r['method']}::{r['group']}": r
            for r in json.loads(out_path.read_text(encoding="utf-8"))
        }
        for r in results:
            key = f"{r['persistbench_id']}::{r['method']}::{r['group']}"
            if key in judged_by_key:
                r["conditions"] = judged_by_key[key]["conditions"]
                already_judged += 1
        print(f"Resuming: {already_judged}/{len(results)} cases already judged", flush=True)

    build_judge_prompt, judge_system_prompts = apatch.load_prompt_and_judge_builders()

    print(f"Loading local judge: {JUDGE_MODEL_ID}", flush=True)
    judge_tokenizer = AutoTokenizer.from_pretrained(JUDGE_MODEL_ID, use_fast=True, local_files_only=True)
    judge_model = AutoModelForCausalLM.from_pretrained(
        JUDGE_MODEL_ID, torch_dtype=torch.bfloat16, device_map="auto", local_files_only=True, attn_implementation="sdpa",
    ).eval()
    judge_model.requires_grad_(False)

    for i, record in enumerate(results):
        key = f"{record['persistbench_id']}::{record['method']}::{record['group']}"
        if any("judge_qwen" in c for c in record["conditions"].values()):
            continue  # already judged (resumed)
        for cond_name, gen in record["conditions"].items():
            gen["judge_qwen"] = apatch.simplified_local_judge_score(
                judge_model, judge_tokenizer, build_judge_prompt, judge_system_prompts,
                "sycophancy", record["memories"], record["query"], gen["text"],
            )
            print(
                f"  [{i+1}/{len(results)}] {record['persistbench_id'][:8]} [{record['method']}/{record['group']}] "
                f"{cond_name}: qwen_score={gen['judge_qwen']['score']}",
                flush=True,
            )
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    del judge_model, judge_tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    print(f"Wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
