#!/usr/bin/env python3
"""Judge the vLLM reproducibility-check generations (repro_check_raw.json) with the same
legacy local Qwen judge used in the rest of this experiment.

Output: repro_check_judged.json  {pid: {model_label: [score0, score1, score2]}}
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = Path(__file__).resolve().parent

_spec = importlib.util.spec_from_file_location(
    "muse_news_activation_patching", ROOT / "mechanistic/muse_news/muse_news_activation_patching.py"
)
apatch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(apatch)

CLEAN_SELECTION = (
    ROOT / "mechanistic/experiments/muse_news_sycophancy_paradox/analysis/"
    "activation_patching_clean_audit/clean_selection.json"
)


def main() -> None:
    repro = json.loads((OUT_DIR / "repro_check_raw.json").read_text(encoding="utf-8"))
    selection = json.loads(CLEAN_SELECTION.read_text(encoding="utf-8"))

    memories_query_by_pid = {}
    for method, mv in selection["methods"].items():
        for rec in mv["treatment"]:
            memories_query_by_pid[rec["persistbench_id"]] = (rec["memories"], rec["query"])

    build_judge_prompt, judge_system_prompts = apatch.load_prompt_and_judge_builders()

    print(f"Loading local judge: {apatch.JUDGE_MODEL_ID}", flush=True)
    judge_tokenizer = AutoTokenizer.from_pretrained(apatch.JUDGE_MODEL_ID, use_fast=True, local_files_only=True)
    judge_model = AutoModelForCausalLM.from_pretrained(
        apatch.JUDGE_MODEL_ID, torch_dtype=torch.bfloat16, device_map="auto",
        local_files_only=True, attn_implementation="sdpa",
    ).eval()
    judge_model.requires_grad_(False)

    judged: dict[str, dict[str, list]] = {}
    for pid, by_model in repro.items():
        memories, query = memories_query_by_pid[pid]
        judged[pid] = {}
        for model_label, texts in by_model.items():
            scores = []
            for i, text in enumerate(texts):
                result = apatch.simplified_local_judge_score(
                    judge_model, judge_tokenizer, build_judge_prompt, judge_system_prompts,
                    "sycophancy", memories, query, text,
                )
                scores.append(result["score"])
                print(f"  {pid[:8]} {model_label} rep{i}: score={result['score']}", flush=True)
            judged[pid][model_label] = scores

    out_path = OUT_DIR / "repro_check_judged.json"
    out_path.write_text(json.dumps(judged, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
