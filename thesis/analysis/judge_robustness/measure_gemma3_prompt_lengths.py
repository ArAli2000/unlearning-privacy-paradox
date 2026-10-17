#!/usr/bin/env python3
"""Category-aware Gemma-3 judge prompt-length measurement.

Supersedes the earlier /tmp/measure_prompt_lens.py (Gemma-2) and
/tmp/measure_prompt_lens_gemma3_v2.py scans: those paired every generation
with all three judge rubrics, which is not what the real judging code does
and so overstated/misattributed prompt sizes. This script instead measures,
for each REAL generation in each of the 15 canonical PersistBench files,
exactly the one request the actual Gemma-3 judge (gemma_judge.py) would send
for that generation's own category -- nothing more.

Reuses gemma_judge.py's own STRICT_INSTRUCTION constant and prompt-assembly
logic (imported directly, not copy-pasted) so this measurement cannot drift
from what the real judging code does. Tokenizer-only: no model weights, no
GPU, no torch model load -- CPU-safe, intended for the `cpu` SLURM partition.

Memory discipline: files are processed one at a time; only per-category
aggregate statistics (counts, a bounded top-K of largest examples, and the
list of token-count integers needed for percentiles) are retained across the
whole corpus. Full prompt strings and tokenizer output arrays are discarded
immediately after each request is counted.
"""
import json
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[2]
PB_SRC = REPO_ROOT / "external" / "PersistBench" / "src"
sys.path.insert(0, str(PB_SRC))
sys.path.insert(0, str(THIS_DIR))

from benchmark.prompts import build_judge_prompt, get_judge_system_prompt  # noqa: E402
from gemma_judge import STRICT_INSTRUCTION, GEMMA_LOCAL_PATH  # noqa: E402

from transformers import AutoTokenizer  # noqa: E402

# Judge output allowance actually configured in gemma_judge.py's judge_one().
CONFIGURED_JUDGE_MAX_OUTPUT_TOKENS = 256

CANONICAL_FILES = [
    "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_before.json",
    "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_satimp.json",
    "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_simnpo.json",
    "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_rmu.json",
    "external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_wga.json",
    "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_before.json",
    "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_satimp.json",
    "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_simnpo.json",
    "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_rmu.json",
    "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_wga.json",
    "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_before.json",
    "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_satimp.json",
    "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_simnpo.json",
    "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_rmu.json",
    "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_wga.json",
]

CATEGORIES = ["cross_domain", "sycophancy", "beneficial_memory_usage"]

TOP_K = 5  # bounded per-category "largest examples" retained for provenance


def entry_category(entry: dict) -> str:
    # Exactly gemma_judge.py's own category-resolution logic (main_async loop).
    failure_type = entry.get("failure_type") or entry.get("leakage_type", "cross_domain")
    if failure_type == "positive_memory_usage":
        failure_type = "beneficial_memory_usage"
    return failure_type


def build_request_token_count(tokenizer, system_prompt: str, user_message: str) -> int:
    # Byte-for-byte the same construction as gemma_judge.py's judge_one():
    # system + STRICT_INSTRUCTION + user content, concatenated into a single
    # user-role message (Gemma-3's chat template folds a leading system
    # message into the first user turn's prefix identically -- see
    # GEMMA3_CONTEXT_CHECK.md section 6 -- so this is not a shortcut, it
    # reproduces the exact text gemma_judge.py sends).
    combined_content = (
        system_prompt + "\n\n" + STRICT_INSTRUCTION
        + "\n\n" + user_message + "\n\nReturn compact JSON only."
    )
    messages = [{"role": "user", "content": combined_content}]
    # NOTE: apply_chat_template(tokenize=True, ...) on this tokenizer returns a
    # BatchEncoding (dict-like, keyed by 'input_ids'/'attention_mask'), so a
    # bare len(...) on its return value counts dict keys (bug found during a
    # dry run: reported "2 tokens" for an obviously-long prompt). Render to
    # text first (exactly what vLLM's OpenAI-compatible server does: apply
    # the chat template to get the final prompt string, then tokenize that
    # string), then tokenize explicitly and take len() of the actual
    # input_ids list -- this avoids the BatchEncoding pitfall entirely.
    rendered = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    encoding = tokenizer(rendered, add_special_tokens=False, padding=False, truncation=False)
    return len(encoding["input_ids"])


def main():
    print(f"Loading Gemma-3 tokenizer (CPU, tokenizer-only) from {GEMMA_LOCAL_PATH} ...", file=sys.stderr)
    tokenizer = AutoTokenizer.from_pretrained(GEMMA_LOCAL_PATH)

    per_category = {
        cat: {
            "count": 0,
            "token_counts": [],
            "top": [],  # list of dicts, kept sorted desc by tokens, capped at TOP_K
        }
        for cat in CATEGORIES
    }
    unknown_category_count = 0
    files_missing = []

    for rel_path in CANONICAL_FILES:
        abs_path = REPO_ROOT / rel_path
        if not abs_path.is_file():
            files_missing.append(rel_path)
            print(f"ERROR: canonical file missing, not regenerating: {rel_path}", file=sys.stderr)
            continue

        with open(abs_path) as f:
            data = json.load(f)

        for entry_id, entry in data["entries"].items():
            category = entry_category(entry)
            if category not in per_category:
                unknown_category_count += 1
                continue
            system_prompt = get_judge_system_prompt(category)
            memories = entry.get("memories", [])
            query = entry.get("query", "")

            for model_key, model_data in entry["results"].items():
                for gi, gen in enumerate(model_data.get("generations", [])):
                    if gen.get("error") or not gen.get("memory_response"):
                        continue
                    user_message = build_judge_prompt(memories, query, gen["memory_response"])
                    n_tokens = build_request_token_count(tokenizer, system_prompt, user_message)

                    bucket = per_category[category]
                    bucket["count"] += 1
                    bucket["token_counts"].append(n_tokens)

                    record = {
                        "tokens": n_tokens,
                        "file": rel_path,
                        "entry_id": entry_id,
                        "model_key": model_key,
                        "generation_index": gi,
                    }
                    top = bucket["top"]
                    top.append(record)
                    top.sort(key=lambda r: r["tokens"], reverse=True)
                    del top[TOP_K:]

        print(f"[done] {rel_path}", file=sys.stderr)

    if files_missing:
        print("FATAL: one or more canonical files were missing; refusing to report partial "
              "statistics as if complete. See stderr above for the list.", file=sys.stderr)
        sys.exit(1)

    def percentile(sorted_vals, p):
        if not sorted_vals:
            return None
        k = (len(sorted_vals) - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, len(sorted_vals) - 1)
        if f == c:
            return sorted_vals[f]
        return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)

    GEMMA3_NATIVE_CONTEXT = 131072
    # Planned serving max-model-len: chosen after seeing real measured maxima
    # (see decision note in GEMMA3_CONTEXT_CHECK.md); recorded here as the
    # threshold used for the "exceeds planned max-model-len" statistic.
    PLANNED_MAX_MODEL_LEN = 16384

    result = {
        "model": "google/gemma-3-12b-it",
        "model_local_path": GEMMA_LOCAL_PATH,
        "model_native_context_length": GEMMA3_NATIVE_CONTEXT,
        "configured_judge_max_output_tokens": CONFIGURED_JUDGE_MAX_OUTPUT_TOKENS,
        "planned_max_model_len": PLANNED_MAX_MODEL_LEN,
        "unknown_category_generations_skipped": unknown_category_count,
        "categories": {},
    }

    overall_counts = []
    overall_total_requests = 0
    overall_max_record = None

    for cat in CATEGORIES:
        bucket = per_category[cat]
        vals = sorted(bucket["token_counts"])
        n = len(vals)
        overall_total_requests += n
        overall_counts.extend(vals)

        if n == 0:
            result["categories"][cat] = {"request_count": 0}
            continue

        exceed_8192 = sum(1 for v in vals if v > 8192)
        exceed_planned = sum(1 for v in vals if v > PLANNED_MAX_MODEL_LEN - CONFIGURED_JUDGE_MAX_OUTPUT_TOKENS)

        cat_max_record = bucket["top"][0]
        if overall_max_record is None or cat_max_record["tokens"] > overall_max_record["tokens"]:
            overall_max_record = dict(cat_max_record, category=cat)

        result["categories"][cat] = {
            "request_count": n,
            "min_tokens": vals[0],
            "median_tokens": percentile(vals, 50),
            "p95_tokens": percentile(vals, 95),
            "p99_tokens": percentile(vals, 99),
            "max_tokens": vals[-1],
            "max_example": bucket["top"][0],
            "top_examples": bucket["top"],
            "required_total_context_for_max": vals[-1] + CONFIGURED_JUDGE_MAX_OUTPUT_TOKENS,
            "count_exceeding_8192_input_tokens": exceed_8192,
            "pct_exceeding_8192_input_tokens": 100.0 * exceed_8192 / n,
            "count_exceeding_planned_max_model_len_minus_output": exceed_planned,
            "pct_exceeding_planned_max_model_len_minus_output": 100.0 * exceed_planned / n,
        }

    overall_counts.sort()
    overall_max_input = overall_counts[-1] if overall_counts else None
    result["overall"] = {
        "total_real_judgment_requests": overall_total_requests,
        "overall_max_input_tokens": overall_max_input,
        "overall_max_example": overall_max_record,
        "required_total_context_for_overall_max": (
            overall_max_input + CONFIGURED_JUDGE_MAX_OUTPUT_TOKENS if overall_max_input is not None else None
        ),
        "count_exceeding_8192_input_tokens": sum(1 for v in overall_counts if v > 8192),
        "pct_exceeding_8192_input_tokens": (
            100.0 * sum(1 for v in overall_counts if v > 8192) / overall_total_requests
            if overall_total_requests else None
        ),
        "fits_without_truncation_at_planned_max_model_len": (
            overall_max_input + CONFIGURED_JUDGE_MAX_OUTPUT_TOKENS <= PLANNED_MAX_MODEL_LEN
            if overall_max_input is not None else None
        ),
    }

    out_json = THIS_DIR / "gemma3_prompt_length_analysis.json"
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote {out_json}", file=sys.stderr)

    write_markdown_report(result, THIS_DIR / "GEMMA3_CONTEXT_CHECK.md")
    print(f"Wrote {THIS_DIR / 'GEMMA3_CONTEXT_CHECK.md'}", file=sys.stderr)


def write_markdown_report(result: dict, out_path: Path):
    lines = []
    lines.append("# Gemma-3 judge prompt-length check (category-aware, corrected)\n")
    lines.append(
        "Corrects the earlier Gemma-2 scans (`/tmp/measure_prompt_lens.py`, "
        "`/tmp/measure_prompt_lens_gemma3_v2.py`), which paired every generation "
        "with all three judge rubrics. This measurement instead pairs each real "
        "generation with only its own actual PersistBench category's rubric -- "
        "exactly what `gemma_judge.py` sends.\n"
    )
    lines.append(f"Model: `{result['model']}` at `{result['model_local_path']}`")
    lines.append(f"Model native context length: {result['model_native_context_length']}")
    lines.append(f"Configured judge max output tokens: {result['configured_judge_max_output_tokens']}")
    lines.append(f"Planned Gemma-3 `--max-model-len`: {result['planned_max_model_len']}\n")

    lines.append("## Per-category statistics\n")
    lines.append("| Category | Requests | Min | Median | P95 | P99 | Max | Required ctx (max+output) | >8192 tok | >planned-output |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for cat, stats in result["categories"].items():
        if stats.get("request_count", 0) == 0:
            lines.append(f"| {cat} | 0 | - | - | - | - | - | - | - | - |")
            continue
        lines.append(
            f"| {cat} | {stats['request_count']} | {stats['min_tokens']} | "
            f"{stats['median_tokens']:.1f} | {stats['p95_tokens']:.1f} | {stats['p99_tokens']:.1f} | "
            f"{stats['max_tokens']} | {stats['required_total_context_for_max']} | "
            f"{stats['count_exceeding_8192_input_tokens']} ({stats['pct_exceeding_8192_input_tokens']:.2f}%) | "
            f"{stats['count_exceeding_planned_max_model_len_minus_output']} "
            f"({stats['pct_exceeding_planned_max_model_len_minus_output']:.2f}%) |"
        )

    lines.append("\n## Maximum example per category\n")
    for cat, stats in result["categories"].items():
        ex = stats.get("max_example")
        if not ex:
            continue
        lines.append(
            f"- **{cat}**: {ex['tokens']} tokens -- `{ex['file']}`, entry `{ex['entry_id']}`, "
            f"model `{ex['model_key']}`, generation index {ex['generation_index']}"
        )

    ov = result["overall"]
    lines.append("\n## Overall\n")
    lines.append(f"- Total real judgment requests (all categories): {ov['total_real_judgment_requests']}")
    lines.append(f"- Overall max input tokens: {ov['overall_max_input_tokens']}")
    if ov.get("overall_max_example"):
        ex = ov["overall_max_example"]
        lines.append(
            f"  - Producing example: category `{ex['category']}`, `{ex['file']}`, entry `{ex['entry_id']}`, "
            f"model `{ex['model_key']}`, generation index {ex['generation_index']}"
        )
    lines.append(f"- Required total context for overall max (input + {result['configured_judge_max_output_tokens']} output): "
                 f"{ov['required_total_context_for_overall_max']}")
    lines.append(f"- Count/percentage exceeding 8192 input tokens (Gemma-2's ceiling, for reference): "
                 f"{ov['count_exceeding_8192_input_tokens']} ({ov['pct_exceeding_8192_input_tokens']:.2f}%)")
    lines.append(f"- Fits without truncation at planned `--max-model-len` "
                 f"({result['planned_max_model_len']}), with output headroom: "
                 f"**{ov['fits_without_truncation_at_planned_max_model_len']}**")

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
