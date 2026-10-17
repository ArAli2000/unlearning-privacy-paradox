#!/usr/bin/env python3
"""Experiment A: construct + extract MCQ logit-margin readouts for the 5
HIGH_CONFIDENCE_FAILURE persistbench_ids NOT already covered by the existing
curated 50-example MCQ manifest
(`mechanistic/privacy_collapse/persistbench_sycophancy_mcq/manifests/
persistbench_sycophancy_mcq_clear_no_50_v1.json`).

Reuses the existing MCQ construction and extraction code UNCHANGED (imported
directly from `persistbench_sycophancy_mcq/common.py` and the same
`projections`/`endpoint` logit-lens logic as `extract.py`) -- no new probe
design, no new prompt template. The only difference from the original 50 is
which persistbench_ids are included; memories/query come straight from the
clean HIGH_CONFIDENCE_FAILURE audit
(`analysis/activation_patching_clean_audit/clean_selection.json`).

Covered (from the existing 50-example manifest, reused, not recomputed):
  aa71a70f (SatImp, SimNPO), 3c6606c5 (SatImp), 2740209d (SimNPO)
Missing (constructed + extracted here):
  3ccf8e85 (SatImp), b934289e (SatImp), 7b1e0198 (SatImp),
  7079a34e (SatImp, SimNPO), e549f564 (SimNPO)

Output: expA_mcq/missing5_readout.csv (same schema as the existing
mcq_readout_per_example.csv), expA_mcq/missing5_prepared.json (provenance).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[4]
MCQ_DIR = ROOT / "mechanistic/privacy_collapse/persistbench_sycophancy_mcq"
sys.path.insert(0, str(MCQ_DIR))
from common import prompt, chat, pair, enc  # noqa: E402  (reused unmodified)

CLEAN_SELECTION = (
    ROOT / "mechanistic/experiments/muse_news_sycophancy_paradox/analysis/"
    "activation_patching_clean_audit/clean_selection.json"
)
CONFIG = MCQ_DIR / ".." / "configs/muse_news_qwen25_7b.json"
OUT_DIR = Path(__file__).resolve().parent

MISSING_IDS = {
    "3ccf8e8567a5ac273dd7658d27d36e2b",
    "b934289ef05f5a132dd217a3c4587a2d",
    "7b1e019824a5da43f90afcebcc813873",
    "7079a34e3ff4d823075aed89e981adde",
    "e549f5644172a76c2c09e9cbfbea903d",
}


def endpoint(model, ids):
    with torch.inference_mode():
        o = model(torch.tensor([ids], device=model.device), output_hidden_states=True, use_cache=False, return_dict=True)
    return torch.stack([h[0, -1].float().cpu() for h in o.hidden_states])


def projections(model, states):
    out = []
    for i, h in enumerate(states):
        v = h[0, -1]
        v = v if i == len(states) - 1 else model.model.norm(v)
        out.append(model.lm_head(v).float())
    return out


def build_records() -> list[dict]:
    selection = json.loads(CLEAN_SELECTION.read_text(encoding="utf-8"))
    by_pid = {}
    for method, mv in selection["methods"].items():
        for rec in mv["treatment"]:
            if rec["persistbench_id"] in MISSING_IDS:
                by_pid.setdefault(rec["persistbench_id"], rec)  # memories/query identical across methods for shared ids

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    tok = Tokenizer.from_file(str((ROOT / config["models"]["BASE"]).resolve() / "tokenizer.json"))

    records = []
    for pid, rec in by_pid.items():
        row = {"memories": rec["memories"], "query": rec["query"]}
        p = prompt(row)
        sp = prompt(row, swapped=True)
        original = pair(tok, chat(p), "B", "A")
        swapped = pair(tok, chat(sp), "A", "B")
        assert len(original["safe_continuation_ids"]) == len(original["violating_continuation_ids"]) == 1
        assert len(swapped["safe_continuation_ids"]) == len(swapped["violating_continuation_ids"]) == 1
        records.append({
            "persistbench_id": pid,
            "example_id": f"expA-missing5-{pid[:12]}",
            "query": rec["query"],
            "memories": rec["memories"],
            "prompt": p,
            "swapped_prompt": sp,
            "original": original,
            "swapped": swapped,
        })
    return records


def main() -> None:
    assert torch.cuda.is_available()
    records = build_records()
    print(f"Built {len(records)} missing MCQ records: {[r['persistbench_id'][:8] for r in records]}", flush=True)

    (OUT_DIR / "missing5_prepared.json").write_text(
        json.dumps({"records": records}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = []
    for label, rel in config["models"].items():
        path = (ROOT / rel).resolve()
        print(f"Loading {label} ({path})...", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            path, torch_dtype=torch.bfloat16, device_map="auto",
            local_files_only=True, trust_remote_code=True, attn_implementation=config["attention_implementation"],
        ).eval()
        model.requires_grad_(False)

        for r in records:
            for variant in ("original", "swapped"):
                z = r[variant]
                prompt_ids = torch.tensor([z["prompt_ids"]], device=model.device)
                with torch.inference_mode():
                    o = model(prompt_ids, output_hidden_states=True, use_cache=False, return_dict=True)
                sid, vid = z["safe_continuation_ids"][0], z["violating_continuation_ids"][0]
                for i, logits in enumerate(projections(model, o.hidden_states)):
                    probs = torch.softmax(logits, dim=0)
                    margin = float(logits[sid] - logits[vid])
                    rows.append({
                        "model": label, "variant": variant, "example_id": r["example_id"],
                        "persistbench_id": r["persistbench_id"], "state_index": i,
                        "state_label": "embedding" if i == 0 else f"L{i}",
                        "safe_logit": float(logits[sid]), "violating_logit": float(logits[vid]),
                        "safe_minus_syc_logit_margin": margin,
                        "P_safe": float(probs[sid]), "P_violating": float(probs[vid]),
                        "probability_gap": float(probs[sid] - probs[vid]), "safe_correct": int(margin > 0),
                    })
                del prompt_ids, o
            print(f"  {label} {r['persistbench_id'][:8]} done", flush=True)

        del model
        import gc
        gc.collect()
        torch.cuda.empty_cache()

    out_path = OUT_DIR / "missing5_readout.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
