#!/usr/bin/env python3
"""GPU extraction: layer-wise ordinary-logit-lens teacher-forced log
probability of each candidate continuation, for Phase 8 (safe-vs-failure
continuation preference across layers) of the MUSE-News sycophancy /
cross-domain mechanistic experiment.

For every case in `continuation_cases_v1.json`, and for BASE plus the case's
own unlearned method, teacher-forces [prompt_token_ids + candidate_token_ids]
and records, at every residual state L0..L28 (embedding + 28 transformer
layers), the log-probability the evaluating model's own final RMSNorm +
LM head assign to the actual observed candidate tokens (ordinary logit lens;
L28 is already post-final-RMSNorm and is not re-normed, matching the
convention established in `mechanistic/extract_single_persistbench_case.py`).

Each evaluating model is loaded once and used for every case that needs it
(BASE evaluates all 60 cases; SatImp evaluates its 36 cases; SimNPO evaluates
its 24 cases), to avoid repeated 7B loads.

Output: mechanistic/outputs/muse_news_sycophancy_mechanistic/
  continuation_layer_logprobs.csv
  continuation_extraction_metadata.json
"""

from __future__ import annotations

import gc
import json
import platform
import socket
import time
from pathlib import Path

import pandas as pd
import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "mechanistic/outputs/muse_news_sycophancy_mechanistic"
MANIFEST_PATH = OUT_ROOT / "manifests/continuation_cases_v1.json"
MODEL_PATHS = {
    "BASE": ROOT / "saves/finetune/muse_news_qwen25_7b_instruct_target",
    "SatImp": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_satimp/checkpoint-459",
    "SimNPO": ROOT / "saves/unlearn/muse_news_qwen25_7b_instruct_simnpo/checkpoint-459",
}
NUM_LAYERS = 28


def layerwise_logprobs(model, prompt_ids: list[int], response_ids: list[int]) -> list[dict]:
    """Return, for every layer 0..NUM_LAYERS, the total and mean log-probability
    the ordinary logit lens assigns to the observed response_ids, teacher-forced
    after prompt_ids."""
    device = model.get_input_embeddings().weight.device
    full_ids = torch.tensor([prompt_ids + response_ids], dtype=torch.long, device=device)
    attention_mask = torch.ones_like(full_ids)
    with torch.inference_mode():
        outputs = model(
            input_ids=full_ids,
            attention_mask=attention_mask,
            output_hidden_states=True,
            use_cache=False,
            return_dict=True,
        )
    if outputs.hidden_states is None or len(outputs.hidden_states) != NUM_LAYERS + 1:
        raise RuntimeError("Unexpected hidden_states length")

    prompt_len = len(prompt_ids)
    resp_len = len(response_ids)
    # Predicting response token j (0-indexed) uses the hidden state at absolute position prompt_len+j-1.
    pred_positions = torch.tensor(
        [prompt_len + j - 1 for j in range(resp_len)], device=device, dtype=torch.long
    )
    targets = torch.tensor(response_ids, device=device, dtype=torch.long)

    rows = []
    for layer in range(NUM_LAYERS + 1):
        hidden = outputs.hidden_states[layer][0, pred_positions]  # [resp_len, hidden]
        if layer != NUM_LAYERS:
            hidden = model.model.norm(hidden)
        logits = model.lm_head(hidden).float()  # [resp_len, vocab]
        log_probs = torch.log_softmax(logits, dim=-1)
        target_logprobs = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)  # [resp_len]
        ranks = (logits > logits.gather(1, targets.unsqueeze(1))).sum(dim=1) + 1
        rows.append(
            {
                "layer": layer,
                "seq_logprob": float(target_logprobs.sum().item()),
                "mean_logprob": float(target_logprobs.mean().item()),
                "mean_rank": float(ranks.float().mean().item()),
                "token_count": resp_len,
            }
        )
        del hidden, logits, log_probs, target_logprobs, ranks
    del outputs, full_ids, attention_mask
    return rows


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; submit via SLURM")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    cases = manifest["cases"]

    all_rows: list[dict] = []
    metadata = {
        "manifest": str(MANIFEST_PATH.relative_to(ROOT)),
        "case_count": len(cases),
        "num_layers": NUM_LAYERS,
        "execution": {
            "hostname": socket.gethostname(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "cuda_device": torch.cuda.get_device_name(0),
            "dtype_model": "bfloat16",
            "attention": "sdpa",
        },
        "models": {},
    }

    # Evaluate BASE against every case; then each unlearned method against its own cases only.
    eval_plan = [("BASE", cases)]
    for method in ("SatImp", "SimNPO"):
        method_cases = [c for c in cases if c["method"] == method]
        if method_cases:
            eval_plan.append((method, method_cases))

    for evaluating_model, model_cases in eval_plan:
        model_path = MODEL_PATHS[evaluating_model]
        print(f"Loading {evaluating_model}: {model_path} ({len(model_cases)} cases)", flush=True)
        started = time.time()
        tokenizer = AutoTokenizer.from_pretrained(
            model_path, use_fast=True, trust_remote_code=True, local_files_only=True
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
            local_files_only=True,
            attn_implementation="sdpa",
        ).eval()
        model.requires_grad_(False)
        if model.config.num_hidden_layers != NUM_LAYERS or model.config.hidden_size != 3584:
            raise RuntimeError(f"Unexpected architecture for {evaluating_model}")

        for index, case in enumerate(model_cases, 1):
            for candidate_key in ("candidate_A", "candidate_B"):
                candidate = case[candidate_key]
                layer_rows = layerwise_logprobs(
                    model, case["prompt_token_ids"], candidate["token_ids"]
                )
                for row in layer_rows:
                    row.update(
                        {
                            "persistbench_id": case["persistbench_id"],
                            "category": case["category"],
                            "method": case["method"],
                            "group": case["group"],
                            "transition": case["transition"],
                            "evaluating_model": evaluating_model,
                            "candidate": candidate_key,
                            "candidate_label": candidate["label"],
                        }
                    )
                all_rows.extend(layer_rows)
            if index == 1 or index % 10 == 0 or index == len(model_cases):
                print(f"{evaluating_model}: {index}/{len(model_cases)}", flush=True)

        metadata["models"][evaluating_model] = {
            "checkpoint": str(model_path.relative_to(ROOT)),
            "cases_evaluated": len(model_cases),
            "runtime_seconds": time.time() - started,
        }
        del model, tokenizer
        gc.collect()
        torch.cuda.empty_cache()

    frame = pd.DataFrame(all_rows)
    if not torch.isfinite(torch.tensor(frame["seq_logprob"].to_numpy())).all():
        raise RuntimeError("Non-finite seq_logprob values found")
    out_csv = OUT_ROOT / "continuation_layer_logprobs.csv"
    frame.to_csv(out_csv, index=False)
    (OUT_ROOT / "continuation_extraction_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {out_csv.relative_to(ROOT)}: {len(frame)} rows", flush=True)


if __name__ == "__main__":
    main()
