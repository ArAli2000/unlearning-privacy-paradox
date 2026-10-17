#!/usr/bin/env python3
"""Merge Gemma-3-12b-it judgments (from thesis/analysis/judge_robustness/gemma_judge.py,
run on the file written by exp1_to_gemma_schema.py) into the exp1 generation records as a
`judge_gemma` field per condition. `judge_qwen` is left untouched.

Input:  exp1_generation/exp1_generations_qwen_judged.json
        exp1_generation/exp1_generations_gemma_schema.gemma3.json
Output: exp1_generation/exp1_generations_fully_judged.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
OUT_DIR = EXP_DIR / "exp1_generation"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-name", default="exp1_generations_qwen_judged.json")
    parser.add_argument("--gemma-name", default="exp1_generations_gemma_schema.gemma3.json")
    parser.add_argument("--out-name", default="exp1_generations_fully_judged.json")
    args = parser.parse_args()

    records = json.loads((OUT_DIR / args.base_name).read_text(encoding="utf-8"))
    gemma_out = json.loads((OUT_DIR / args.gemma_name).read_text(encoding="utf-8"))

    n_merged = 0
    for record in records:
        entry_id = f"{record['persistbench_id']}::{record['method']}::{record['group']}"
        entry = gemma_out["entries"].get(entry_id)
        if entry is None:
            print(f"WARNING: no Gemma entry for {entry_id}")
            continue
        for cond_name, gen in record["conditions"].items():
            model_key = f"{entry_id}::{cond_name}"
            model_data = entry["results"].get(model_key)
            if model_data is None:
                print(f"WARNING: no Gemma model_key {model_key}")
                continue
            gen["judge_gemma"] = model_data["generations"][0].get("judge")
            n_merged += 1

    out_path = OUT_DIR / args.out_name
    out_path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Merged {n_merged} conditions with Gemma judgments. Wrote {out_path}")


if __name__ == "__main__":
    main()
