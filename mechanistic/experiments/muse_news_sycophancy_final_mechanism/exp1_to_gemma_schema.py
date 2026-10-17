#!/usr/bin/env python3
"""Convert exp1 generations into the entries/results/generations schema that
thesis/analysis/judge_robustness/gemma_judge.py expects.

One entry per (persistbench_id, method, group) case and one model_key per
generation condition, each holding a single generation (index 0) whose
`memory_response` is the generated text. failure_type is "sycophancy" throughout.

Input:  exp1_generation/exp1_generations_qwen_judged.json
Output: exp1_generation/exp1_generations_gemma_schema.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
OUT_DIR = EXP_DIR / "exp1_generation"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-name", default="exp1_generations_qwen_judged.json")
    parser.add_argument("--out-name", default="exp1_generations_gemma_schema.json")
    args = parser.parse_args()

    records = json.loads((OUT_DIR / args.in_name).read_text(encoding="utf-8"))

    entries = {}
    for record in records:
        entry_id = f"{record['persistbench_id']}::{record['method']}::{record['group']}"
        results = {}
        for cond_name, gen in record["conditions"].items():
            model_key = f"{entry_id}::{cond_name}"
            results[model_key] = {
                "generations": [
                    {"generation_index": 0, "error": None, "memory_response": gen["text"]}
                ]
            }
        entries[entry_id] = {
            "memories": record["memories"],
            "query": record["query"],
            "failure_type": "sycophancy",
            "results": results,
        }

    out = {
        "metadata": {
            "source": "mechanistic/experiments/muse_news_sycophancy_final_mechanism/run_exp1_generate.py",
            "purpose": "Gemma-3-12b-it second-judge scoring for Experiment 1 free-generation patching",
        },
        "entries": entries,
        "config": {},
    }
    out_path = OUT_DIR / args.out_name
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(entries)} entries, "
          f"{sum(len(e['results']) for e in entries.values())} model_keys)")


if __name__ == "__main__":
    main()
