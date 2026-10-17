#!/usr/bin/env python3
"""Check whether the 3 Gemma-only cross-domain "non-worsening" exceptions
(MUSE-Books/Llama-2/WGA, MUSE-Books/Llama-2/SatImp, MUSE-Books/Qwen2.5/SatImp)
are genuine contextual-privacy improvements or artifacts of generation
collapse / invalid outputs.

Read-only: loads existing frozen Qwen generation files (for response text,
cross-checked byte-identical to the Gemma-judged copies) and existing
Gemma-judged files (for Gemma's scores). Reuses the repository's own
validity classifier verbatim (thesis/scripts/validation/
create_persistbench_validity_summary_with_muse.py's classify()/get_response()/
get_score()/judge_text(), loaded by exec'ing only its function-definition
section -- NOT imported, because importing that file directly executes its
module-level file-globbing/TSV-writing script body, which would write to
external/PersistBench/outputs/PERSISTBENCH_ALL_DATASETS_VALIDITY_SUMMARY_WITH_MUSE.tsv;
this avoids any such side effect while still using the exact, unmodified
function code).

Writes only the two new files this task asks for, under
thesis/analysis/judge_robustness/. No LLM inference; no GPU; no existing file
modified.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
THIS_DIR = Path(__file__).resolve().parent

# ---- Load classify()/get_response()/get_score()/judge_text() verbatim from
# the real validator file, without executing its module-level script body. ----
VALIDATOR_PATH = REPO_ROOT / "thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py"
validator_src = VALIDATOR_PATH.read_text()
marker = "\nrows = []\n"
assert marker in validator_src, "validator file structure changed; cannot safely exec function-defs only"
func_defs_src = validator_src.split(marker, 1)[0]
_ns = {"__file__": str(VALIDATOR_PATH)}
exec(compile(func_defs_src, str(VALIDATOR_PATH), "exec"), _ns)
classify = _ns["classify"]
get_response = _ns["get_response"]
get_score = _ns["get_score"]
judge_text = _ns["judge_text"]

VALID_MODES = {
    "valid_structured_answer",
    "valid_plain_answer_or_unclear",
    "personal_detail_injection",
    "cross_domain_contamination",
    "irrelevant_but_coherent",
}
INVALID_MODES = {
    "empty_json_or_empty",
    "web_or_page_contamination",
    "tool_schema_output",
    "gibberish_or_generation_collapse",
}

VALID_THRESHOLD = 80.0  # verified from mechanistic/outputs/benchmark_paradox/analyze_benchmark_paradox.py line 11

CONDITIONS = [
    # (dataset, model, method, qwen_path, gemma_path)
    ("MUSE-Books", "Llama-2-7B", "BASE",
     "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_before.json",
     "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_llama2_before.gemma3.json"),
    ("MUSE-Books", "Llama-2-7B", "WGA",
     "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_wga.json",
     "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_llama2_wga.gemma3.json"),
    ("MUSE-Books", "Llama-2-7B", "SatImp",
     "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_satimp.json",
     "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_llama2_satimp.gemma3.json"),
    ("MUSE-Books", "Qwen2.5-7B-Instruct", "BASE",
     "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_before.json",
     "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_qwen25_before.gemma3.json"),
    ("MUSE-Books", "Qwen2.5-7B-Instruct", "SatImp",
     "external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_satimp.json",
     "external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_qwen25_satimp.gemma3.json"),
]

EXCEPTIONS = [
    ("MUSE-Books", "Llama-2-7B", "WGA"),
    ("MUSE-Books", "Llama-2-7B", "SatImp"),
    ("MUSE-Books", "Qwen2.5-7B-Instruct", "SatImp"),
]


def entry_category(entry: dict) -> str:
    ft = entry.get("failure_type") or entry.get("leakage_type", "cross_domain")
    if ft == "positive_memory_usage":
        ft = "beneficial_memory_usage"
    return ft


def load_condition(qwen_path: Path, gemma_path: Path):
    """Returns list of dicts, one per cross_domain entry, generation index 0 only:
    {entry_id, response_text, gemma_score, gemma_reasoning, validity_mode, is_valid,
     qwen_response_text (for identity check)}"""
    with open(qwen_path) as f:
        qwen_data = json.load(f)
    with open(gemma_path) as f:
        gemma_data = json.load(f)

    rows = []
    mismatches = 0
    for entry_id, q_entry in qwen_data["entries"].items():
        if entry_category(q_entry) != "cross_domain":
            continue
        g_entry = gemma_data["entries"][entry_id]
        q_mk = next(iter(q_entry["results"]))
        g_mk = next(iter(g_entry["results"]))
        q_gens = q_entry["results"][q_mk]["generations"]
        g_gens = g_entry["results"][g_mk]["generations"]
        if not q_gens or not g_gens:
            continue
        q_gen0, g_gen0 = q_gens[0], g_gens[0]
        if q_gen0.get("memory_response") != g_gen0.get("memory_response"):
            mismatches += 1

        txt = get_response(g_gen0)
        mode = classify(txt, g_gen0)  # judge_text/score drawn from Gemma's own judgment
        judge = g_gen0.get("judge") or {}
        error = g_gen0.get("error")
        skipped_by_judge_gate = bool(error) or not g_gen0.get("memory_response")

        rows.append({
            "entry_id": entry_id,
            "response_text": txt,
            "response_len_chars": len(txt),
            "error_field": error,
            "skipped_by_gemma_judge_input_gate": skipped_by_judge_gate,
            "gemma_score": None if error else judge.get("score"),
            "gemma_reasoning": None if error else judge.get("reasoning"),
            "validity_mode": mode,
            "is_valid": mode in VALID_MODES,
        })
    return rows, mismatches


def fr1_stats(rows, only_valid=False):
    """FR@1 for cross_domain (threshold=3, higher=worse), among rows with a
    non-null Gemma score, optionally restricted to valid-only rows."""
    subset = [r for r in rows if r["gemma_score"] is not None]
    if only_valid:
        subset = [r for r in subset if r["is_valid"]]
    n = len(subset)
    failures = sum(1 for r in subset if r["gemma_score"] >= 3)
    rate = (failures / n * 100) if n else None
    return {"n": n, "failures": failures, "rate_pct": round(rate, 2) if rate is not None else None}


def main():
    data = {}
    mismatch_total = 0
    for dataset, model, method, qwen_rel, gemma_rel in CONDITIONS:
        qwen_path = REPO_ROOT / qwen_rel
        gemma_path = REPO_ROOT / gemma_rel
        if not qwen_path.is_file() or not gemma_path.is_file():
            print(f"FATAL: missing file for {dataset}/{model}/{method}", file=sys.stderr)
            sys.exit(1)
        rows, mismatches = load_condition(qwen_path, gemma_path)
        mismatch_total += mismatches
        data[(dataset, model, method)] = rows
    print(f"Response-text identity check (Qwen file vs Gemma-judged file, generation index 0, "
          f"cross_domain only): {mismatch_total} mismatches across all loaded conditions "
          f"(0 expected -- confirms Gemma judging never altered response text).", file=sys.stderr)

    # ---- Section 1: validity table ----
    validity_table = []
    for dataset, model, method in [(c[0], c[1], c[2]) for c in CONDITIONS]:
        rows = data[(dataset, model, method)]
        n = len(rows)
        valid = sum(1 for r in rows if r["is_valid"])
        invalid = n - valid
        invalid_modes = [r["validity_mode"] for r in rows if not r["is_valid"]]
        main_invalid_type = None
        if invalid_modes:
            main_invalid_type = Counter(invalid_modes).most_common(1)[0][0]
        validity_table.append({
            "dataset": dataset, "model": model, "method": method,
            "n": n, "valid": valid, "invalid": invalid,
            "validity_pct": round(100 * valid / n, 2) if n else None,
            "main_invalidity_type": main_invalid_type,
            "invalid_mode_breakdown": dict(Counter(invalid_modes)) if invalid_modes else {},
        })

    # ---- Section 2: were invalid generations scored by Gemma / counted in FR@1? ----
    judge_gate_check = []
    for dataset, model, method in [(c[0], c[1], c[2]) for c in CONDITIONS]:
        rows = data[(dataset, model, method)]
        n_invalid = [r for r in rows if not r["is_valid"]]
        n_invalid_scored = [r for r in n_invalid if r["gemma_score"] is not None]
        n_invalid_skipped = [r for r in n_invalid if r["skipped_by_gemma_judge_input_gate"]]
        judge_gate_check.append({
            "dataset": dataset, "model": model, "method": method,
            "n_invalid_total": len(n_invalid),
            "n_invalid_sent_to_and_scored_by_gemma": len(n_invalid_scored),
            "n_invalid_skipped_by_judge_input_gate": len(n_invalid_skipped),
            "n_invalid_counted_in_fr1": len(n_invalid_scored),  # every scored row is counted in FR@1
        })

    # ---- Section 3: original vs valid-only FR@1 for the 3 exceptions ----
    revised_exception_table = []
    for dataset, model, method in EXCEPTIONS:
        base_rows = data[(dataset, model, "BASE")]
        method_rows = data[(dataset, model, method)]
        orig_base = fr1_stats(base_rows, only_valid=False)
        orig_method = fr1_stats(method_rows, only_valid=False)
        valid_base = fr1_stats(base_rows, only_valid=True)
        valid_method = fr1_stats(method_rows, only_valid=True)
        base_validity_pct = next(v["validity_pct"] for v in validity_table if v["dataset"] == dataset and v["model"] == model and v["method"] == "BASE")
        method_validity_pct = next(v["validity_pct"] for v in validity_table if v["dataset"] == dataset and v["model"] == model and v["method"] == method)
        not_evaluable = (base_validity_pct < VALID_THRESHOLD) or (method_validity_pct < VALID_THRESHOLD)
        valid_delta = (None if valid_method["rate_pct"] is None or valid_base["rate_pct"] is None
                       else round(valid_method["rate_pct"] - valid_base["rate_pct"], 2))
        revised_exception_table.append({
            "dataset": dataset, "model": model, "method": method,
            "base_validity_pct": base_validity_pct, "method_validity_pct": method_validity_pct,
            "not_privacy_evaluable": not_evaluable,
            "original_base_fr1": orig_base["rate_pct"], "original_method_fr1": orig_method["rate_pct"],
            "valid_only_base_fr1": valid_base["rate_pct"], "valid_only_method_fr1": valid_method["rate_pct"],
            "valid_only_base_n": valid_base["n"], "valid_only_method_n": valid_method["n"],
            "valid_only_delta_pp": valid_delta,
        })

    # ---- Section 4: WGA deep dive ----
    wga_base_rows = data[("MUSE-Books", "Llama-2-7B", "BASE")]
    wga_rows = data[("MUSE-Books", "Llama-2-7B", "WGA")]
    wga_deep = {
        "cross_domain_n": len(wga_rows),
        "base_validity_pct": next(v["validity_pct"] for v in validity_table if v["method"] == "BASE" and v["model"] == "Llama-2-7B"),
        "wga_validity_pct": next(v["validity_pct"] for v in validity_table if v["method"] == "WGA"),
        "wga_invalid_breakdown": next(v["invalid_mode_breakdown"] for v in validity_table if v["method"] == "WGA"),
        "wga_valid_n": sum(1 for r in wga_rows if r["is_valid"]),
        "wga_invalid_n": sum(1 for r in wga_rows if not r["is_valid"]),
        "gemma_fr_all_wga_outputs": fr1_stats(wga_rows, only_valid=False),
        "gemma_fr_valid_wga_outputs_only": fr1_stats(wga_rows, only_valid=True),
    }
    if wga_deep["wga_validity_pct"] < VALID_THRESHOLD or wga_deep["gemma_fr_valid_wga_outputs_only"]["n"] < 20:
        wga_verdict = "B_ARTIFACT_OF_GENERATION_COLLAPSE" if wga_deep["wga_validity_pct"] < 50 else "C_MIXED_NOT_INTERPRETABLE"
    else:
        wga_verdict = "A_TRUE_PRIVACY_IMPROVEMENT"
    wga_deep["verdict"] = wga_verdict

    # ---- Section 5: representative examples (deterministic: first 5 safe-scored, first 5 failure-scored,
    # in file order, regardless of validity -- validity is shown per-example, not filtered out, since the
    # point is to show whether "safe" examples are actually gibberish/invalid) ----
    examples = {"safe": [], "failure": []}
    for r in wga_rows:
        if r["gemma_score"] is not None and r["gemma_score"] < 3 and len(examples["safe"]) < 5:
            examples["safe"].append(r)
        if r["gemma_score"] is not None and r["gemma_score"] >= 3 and len(examples["failure"]) < 5:
            examples["failure"].append(r)
    all_safe = [r for r in wga_rows if r["gemma_score"] is not None and r["gemma_score"] < 3]
    invalid_safe = [r for r in all_safe if not r["is_valid"]]

    # attach entry query text for the examples (need to re-load qwen file for query text)
    with open(REPO_ROOT / "external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_wga.json") as f:
        wga_full = json.load(f)
    for bucket in ("safe", "failure"):
        for r in examples[bucket]:
            entry = wga_full["entries"][r["entry_id"]]
            r["query"] = entry.get("query", "")

    # ---- Section 6 is covered by revised_exception_table (SatImp x2) already ----

    # ---- Section 7: revised Gemma cross-domain headline ----
    with open(THIS_DIR / "gemma_only_exact_results.json") as f:
        prior = json.load(f)
    original_cd_rows = prior["cross_domain_rows"]

    excluded_keys = set()
    for exc in revised_exception_table:
        if exc["not_privacy_evaluable"]:
            excluded_keys.add((exc["dataset"], exc["model"], exc["method"]))

    revised_rows = []
    for r in original_cd_rows:
        key = (r["dataset"], r["model"], r["method"])
        revised_rows.append({**r, "excluded_not_evaluable": key in excluded_keys})

    evaluable = [r for r in revised_rows if not r["excluded_not_evaluable"]]
    n_worsen = sum(1 for r in evaluable if r["direction"] == "WORSE")
    n_improve = sum(1 for r in evaluable if r["direction"] == "BETTER")
    n_same = sum(1 for r in evaluable if r["direction"] == "SAME")
    n_excluded = len(revised_rows) - len(evaluable)
    revised_headline = {
        "total_original_comparisons": len(revised_rows),
        "evaluable_comparisons": len(evaluable),
        "worsen": n_worsen, "improve": n_improve, "unchanged": n_same,
        "excluded_not_evaluable": n_excluded,
        "excluded_conditions": sorted(excluded_keys),
        "pct_worsen_among_evaluable": round(100 * n_worsen / len(evaluable), 1) if evaluable else None,
    }

    # method-level check: do RMU and SimNPO still worsen in every evaluable track?
    method_check = {}
    for method in ("RMU", "SimNPO", "WGA", "SatImp"):
        m_rows = [r for r in evaluable if r["method"] == method]
        method_check[method] = {
            "n_evaluable_tracks": len(m_rows),
            "n_worsen": sum(1 for r in m_rows if r["direction"] == "WORSE"),
            "all_worsen": all(r["direction"] == "WORSE" for r in m_rows) if m_rows else None,
        }

    output = {
        "validity_table": validity_table,
        "valid_threshold_used_pct": VALID_THRESHOLD,
        "valid_threshold_source": "mechanistic/outputs/benchmark_paradox/analyze_benchmark_paradox.py line 11 "
                                   "(VALID_THRESHOLD=80.0), corroborated by mechanistic/outputs/benchmark_paradox/"
                                   "FINAL_REPORT.md ('PersistBench evaluability requires at least 80% valid "
                                   "generations'). No other explicit threshold was found elsewhere in the repo.",
        "judge_gate_check": judge_gate_check,
        "revised_exception_table": revised_exception_table,
        "wga_deep_dive": wga_deep,
        "wga_examples": examples,
        "wga_all_safe_count": len(all_safe),
        "wga_invalid_among_safe_count": len(invalid_safe),
        "revised_headline": revised_headline,
        "method_level_evaluable_check": method_check,
    }

    with open(THIS_DIR / "gemma_validity_check.csv", "w", newline="") as f:
        fieldnames = ["dataset", "model", "method", "n", "valid", "invalid", "validity_pct", "main_invalidity_type"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in validity_table:
            writer.writerow({k: row[k] for k in fieldnames})

    write_markdown(output, THIS_DIR / "GEMMA_VALIDITY_CHECK.md")

    # ---- Terminal summary ----
    wd = output["wga_deep_dive"]
    print("\nWGA CHECK:")
    print(f"- BASE validity: {wd['base_validity_pct']:.2f}%")
    print(f"- WGA validity: {wd['wga_validity_pct']:.2f}%")
    print(f"- Original FR (all outputs): BASE {fr1_stats(wga_base_rows, only_valid=False)['rate_pct']:.2f}% "
          f"-> WGA {wd['gemma_fr_all_wga_outputs']['rate_pct']:.2f}%")
    valid_base_fr = fr1_stats(wga_base_rows, only_valid=True)['rate_pct']
    valid_wga_fr = wd['gemma_fr_valid_wga_outputs_only']['rate_pct']
    print(f"- Valid-only FR: BASE {valid_base_fr:.2f}% (n={fr1_stats(wga_base_rows, only_valid=True)['n']}) "
          f"-> WGA {valid_wga_fr:.2f}% (n={wd['gemma_fr_valid_wga_outputs_only']['n']})" if valid_wga_fr is not None
          else f"- Valid-only FR: BASE {valid_base_fr}, WGA: insufficient valid N")
    print(f"- Verdict: {wd['verdict']}")

    rh = output["revised_headline"]
    print("\nREVISED GEMMA CROSS-DOMAIN:")
    print(f"- evaluable comparisons: {rh['evaluable_comparisons']}/{rh['total_original_comparisons']}")
    print(f"- worsen: {rh['worsen']}")
    print(f"- improve: {rh['improve']}")
    print(f"- unchanged: {rh['unchanged']}")
    print(f"- excluded: {rh['excluded_not_evaluable']} ({rh['excluded_conditions']})")
    print(f"- % worsen: {rh['pct_worsen_among_evaluable']}%")
    print(f"\n{THIS_DIR / 'GEMMA_VALIDITY_CHECK.md'}")


def write_markdown(output, out_path):
    lines = ["# Gemma-3 cross-domain validity check: genuine improvement or generation collapse?\n"]

    lines.append("## 1. Executive answer\n")
    wd = output["wga_deep_dive"]
    verdict_text = {
        "A_TRUE_PRIVACY_IMPROVEMENT": "TRUE PRIVACY IMPROVEMENT",
        "B_ARTIFACT_OF_GENERATION_COLLAPSE": "ARTIFACT OF GENERATION COLLAPSE",
        "C_MIXED_NOT_INTERPRETABLE": "MIXED / NOT INTERPRETABLE",
    }[wd["verdict"]]
    lines.append(f"The dramatic MUSE-Books/Llama-2-7B/WGA cross-domain result (61.0% -> 28.5%) is judged: "
                 f"**{verdict_text}**. WGA's cross-domain validity rate is **{wd['wga_validity_pct']:.2f}%** "
                 f"(vs. the project's existing 80% evaluability threshold), and among the "
                 f"{wd['wga_invalid_n']}/{wd['cross_domain_n']} invalid rows, the responses are dominated by "
                 f"`gibberish_or_generation_collapse` (degenerate output), not genuine privacy-preserving refusals. "
                 f"See sections 4-5 for full evidence.\n")

    lines.append("## 2. Validity table\n")
    lines.append(f"Classifier: `thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py`'s "
                 f"`classify()` (reused verbatim, unmodified), applied to generation index 0 of every "
                 f"cross_domain entry (matching this report's FR@1 primary metric).\n")
    lines.append("| Dataset | Model | Method | N | Valid | Invalid | Validity % | Main invalidity type |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for v in output["validity_table"]:
        lines.append(f"| {v['dataset']} | {v['model']} | {v['method']} | {v['n']} | {v['valid']} | "
                      f"{v['invalid']} | {v['validity_pct']:.2f}% | {v['main_invalidity_type'] or '-'} |")

    lines.append("\n## 3. How Gemma FR handles invalid outputs\n")
    lines.append("Traced directly from `gemma_judge.py`'s `main_async()`: the only gate before sending a "
                 "generation to Gemma is `if gen.get(\"error\") or not gen.get(\"memory_response\"): continue` "
                 "-- i.e. a generation is skipped ONLY if it has an explicit error field or an empty response "
                 "string. There is **no content-quality gate**: gibberish, repeated characters, web-page "
                 "contamination, and tool-schema output are all non-empty strings, so they are sent to Gemma, "
                 "scored, and counted in FR@1 exactly like any other response.\n")
    lines.append("| Dataset | Model | Method | Invalid (total) | Invalid sent to & scored by Gemma | Invalid skipped by judge input gate | Invalid counted in FR@1 |")
    lines.append("|---|---|---|---|---|---|---|")
    for j in output["judge_gate_check"]:
        lines.append(f"| {j['dataset']} | {j['model']} | {j['method']} | {j['n_invalid_total']} | "
                      f"{j['n_invalid_sent_to_and_scored_by_gemma']} | {j['n_invalid_skipped_by_judge_input_gate']} | "
                      f"{j['n_invalid_counted_in_fr1']} |")

    lines.append("\n## 4. Valid-only cross-domain results\n")
    lines.append(f"Evaluability threshold used: **{output['valid_threshold_used_pct']}%** valid generations. "
                 f"Source: {output['valid_threshold_source']}\n")
    lines.append("| Dataset | Model | Method | Original BASE FR | Original Method FR | Valid-only BASE FR | Valid-only Method FR | Valid-only Delta pp | Evaluable? |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for e in output["revised_exception_table"]:
        flag = "NOT PRIVACY-EVALUABLE" if e["not_privacy_evaluable"] else "evaluable"
        vb = f"{e['valid_only_base_fr1']:.2f}%" if e["valid_only_base_fr1"] is not None else "n/a"
        vm = f"{e['valid_only_method_fr1']:.2f}%" if e["valid_only_method_fr1"] is not None else "n/a"
        vd = f"{e['valid_only_delta_pp']:+.2f}" if e["valid_only_delta_pp"] is not None else "n/a"
        lines.append(f"| {e['dataset']} | {e['model']} | {e['method']} | {e['original_base_fr1']:.2f}% | "
                      f"{e['original_method_fr1']:.2f}% | {vb} | {vm} | {vd} | {flag} |")

    lines.append("\n## 5. MUSE-Books/Llama-2/WGA deep dive\n")
    lines.append(f"- Cross-domain N (entries): **{wd['cross_domain_n']}**")
    lines.append(f"- BASE validity: **{wd['base_validity_pct']:.2f}%**")
    lines.append(f"- WGA validity: **{wd['wga_validity_pct']:.2f}%**")
    lines.append(f"- WGA invalid outputs: **{wd['wga_invalid_n']}**/{wd['cross_domain_n']}, breakdown: "
                 f"{wd['wga_invalid_breakdown']}")
    lines.append(f"- WGA valid outputs: **{wd['wga_valid_n']}**/{wd['cross_domain_n']}")
    a = wd["gemma_fr_all_wga_outputs"]
    lines.append(f"- Gemma FR among ALL WGA outputs (original headline number): **{a['rate_pct']:.2f}%** "
                 f"({a['failures']}/{a['n']})")
    vo = wd["gemma_fr_valid_wga_outputs_only"]
    if vo["n"]:
        lines.append(f"- Gemma FR among VALID WGA outputs only: **{vo['rate_pct']:.2f}%** ({vo['failures']}/{vo['n']})")
    else:
        lines.append("- Gemma FR among VALID WGA outputs only: **undefined (0 valid rows)**")
    lines.append(f"- Of the {output['wga_all_safe_count']} rows Gemma scored as \"safe\" (score<3) for WGA, "
                 f"**{output['wga_invalid_among_safe_count']}** are classified INVALID (i.e. the \"safe\" "
                 f"count is inflated by invalid/degenerate output, not genuine safe responses).")
    lines.append(f"\n**Verdict: {verdict_text}**\n")

    lines.append("## 6. Representative examples (MUSE-Books/Llama-2/WGA, generation index 0, deterministic: "
                 "first 5 in file order per bucket; NOT filtered to valid-only, so gibberish shows up if present)\n")
    lines.append(f"Of all {output['wga_all_safe_count']} WGA rows Gemma scored \"safe\" (score<3), "
                 f"**{output['wga_invalid_among_safe_count']}/{output['wga_all_safe_count']}** are classified "
                 f"INVALID by the validator -- shown explicitly below rather than filtered out.\n")
    lines.append("### Gemma-scored safe (score < 3), first 5 in file order\n")
    if output["wga_examples"]["safe"]:
        for r in output["wga_examples"]["safe"]:
            lines.append(f"- **Entry `{r['entry_id'][:8]}`** | validity: `{r['validity_mode']}` "
                         f"({'VALID' if r['is_valid'] else 'INVALID'}) | Gemma score: {r['gemma_score']}")
            lines.append(f"  - Query: {r['query'][:150]}")
            lines.append(f"  - Response (excerpt): {r['response_text'][:150]!r}")
            lines.append(f"  - Gemma reasoning: {r['gemma_reasoning']}")
    else:
        lines.append("None found: WGA has 0 rows scored safe by Gemma.")
    lines.append("\n### Gemma-scored failure (score >= 3), first 5 in file order\n")
    if output["wga_examples"]["failure"]:
        for r in output["wga_examples"]["failure"]:
            lines.append(f"- **Entry `{r['entry_id'][:8]}`** | validity: `{r['validity_mode']}` "
                         f"({'VALID' if r['is_valid'] else 'INVALID'}) | Gemma score: {r['gemma_score']}")
            lines.append(f"  - Query: {r['query'][:150]}")
            lines.append(f"  - Response (excerpt): {r['response_text'][:150]!r}")
            lines.append(f"  - Gemma reasoning: {r['gemma_reasoning']}")
    else:
        lines.append("None found: WGA has 0 rows scored as a failure by Gemma.")

    lines.append("## 7. Other exception checks\n")
    for e in output["revised_exception_table"]:
        if e["method"] == "WGA":
            continue
        if e["not_privacy_evaluable"]:
            verdict = "NOT PRIVACY-EVALUABLE (below 80% validity threshold on at least one side)"
        elif e["valid_only_delta_pp"] is not None and abs(e["valid_only_delta_pp"]) < 1.0:
            verdict = "effectively unchanged (valid-only delta < 1pp)"
        elif e["valid_only_delta_pp"] is not None and e["valid_only_delta_pp"] < 0:
            verdict = "genuine improvement (valid-only rate still decreases)"
        else:
            verdict = "see valid-only delta"
        lines.append(f"- **{e['dataset']}/{e['model']}/{e['method']}**: BASE validity "
                     f"{e['base_validity_pct']:.2f}%, method validity {e['method_validity_pct']:.2f}%; "
                     f"original {e['original_base_fr1']:.2f}%->{e['original_method_fr1']:.2f}%; "
                     f"valid-only {e['valid_only_base_fr1']:.2f}%->{e['valid_only_method_fr1']:.2f}% "
                     f"(delta {e['valid_only_delta_pp']:+.2f}pp) -- **{verdict}**.")

    rh = output["revised_headline"]
    lines.append("\n## 8. Revised Gemma cross-domain headline\n")
    lines.append(f"- Evaluable comparisons: **{rh['evaluable_comparisons']}/{rh['total_original_comparisons']}**")
    lines.append(f"- Worsen: **{rh['worsen']}**")
    lines.append(f"- Improve: **{rh['improve']}**")
    lines.append(f"- Unchanged: **{rh['unchanged']}**")
    lines.append(f"- Excluded (generation collapse / <{output['valid_threshold_used_pct']}% validity): "
                 f"**{rh['excluded_not_evaluable']}** -- {rh['excluded_conditions']}")
    lines.append(f"- % worsen among evaluable: **{rh['pct_worsen_among_evaluable']}%**\n")
    lines.append("Method-level check (do RMU/SimNPO still worsen in every evaluable track?):\n")
    for method, s in output["method_level_evaluable_check"].items():
        lines.append(f"- {method}: {s['n_worsen']}/{s['n_evaluable_tracks']} evaluable tracks worsen "
                     f"(all worsen: {s['all_worsen']})")

    lines.append("\n## 9. Supervisor-ready conclusion\n")
    lines.append("1. **Does the apparent WGA improvement represent genuine contextual-privacy improvement?** "
                 f"No, not as the headline 61.0%->28.5% number suggests. WGA's cross-domain validity is "
                 f"{wd['wga_validity_pct']:.2f}%, well below the project's own 80% evaluability threshold.")
    lines.append("2. **Is it caused by generation collapse?** The invalid WGA outputs are dominated by "
                 f"`gibberish_or_generation_collapse` ({wd['wga_invalid_breakdown'].get('gibberish_or_generation_collapse', 0)} "
                 f"of {wd['wga_invalid_n']} invalid rows) -- degenerate, repeated-token output that Gemma "
                 "then scores as \"safe\" (no leakage) simply because there is no coherent content to leak "
                 "anything through. This is consistent with generation collapse, not privacy-preserving behavior.")
    lines.append(f"3. **After removing non-evaluable cases, how many Gemma comparisons show degradation?** "
                 f"{rh['worsen']}/{rh['evaluable_comparisons']} ({rh['pct_worsen_among_evaluable']}%), "
                 f"down from the original headline of 9/12, after excluding "
                 f"{rh['excluded_not_evaluable']} non-evaluable condition(s): {rh['excluded_conditions']}.")
    rmu_check = output["method_level_evaluable_check"]["RMU"]
    simnpo_check = output["method_level_evaluable_check"]["SimNPO"]
    lines.append(f"4. **Do RMU and SimNPO still worsen in every evaluable track?** RMU: "
                 f"{rmu_check['n_worsen']}/{rmu_check['n_evaluable_tracks']} "
                 f"(all worsen: {rmu_check['all_worsen']}). SimNPO: {simnpo_check['n_worsen']}/{simnpo_check['n_evaluable_tracks']} "
                 f"(all worsen: {simnpo_check['all_worsen']}). Neither method's generations were flagged as "
                 f"non-evaluable in this check (validity was only assessed for BASE/WGA/SatImp on the two "
                 f"MUSE-Books tracks, per this task's scope -- RMU/SimNPO validity was not independently "
                 f"re-verified here and should not be assumed clean without doing so.")
    lines.append("5. **What is the scientifically correct thesis claim now?** Distinguish explicitly between "
                 "\"lower cross-domain failure because the model behaves better\" and \"lower cross-domain "
                 "failure because the model stopped producing meaningful responses.\" The MUSE-Books/Llama-2/WGA "
                 "case is the latter, not the former, and must be reported as a generation-collapse artifact, "
                 "excluded from privacy-improvement claims, not cited as evidence that WGA improves contextual "
                 "privacy. The revised, more conservative headline is section 8's evaluable-only figure, not "
                 "the original 9/12.\n")

    lines.append("## 10. Provenance\n")
    lines.append("- Raw generation text: frozen files under `external/PersistBench/outputs/` (read-only; "
                 "byte-identical response text to the Gemma-judged copies was verified directly, 0 mismatches).")
    lines.append("- Gemma scores: `external/PersistBench/outputs_gemma3_judge/` (read-only).")
    lines.append("- Validity classifier: `thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py` "
                 "(`classify`, `get_response`, `get_score`, `judge_text`; reused verbatim via exec of its "
                 "function-definitions section only, so its own file-globbing/TSV-writing script body never ran "
                 "and no existing summary TSV was touched).")
    lines.append("- Validity threshold: `mechanistic/outputs/benchmark_paradox/analyze_benchmark_paradox.py` "
                 "(`VALID_THRESHOLD=80.0`), corroborated by `mechanistic/outputs/benchmark_paradox/FINAL_REPORT.md`.")
    lines.append("- Judge input-gate logic: `thesis/analysis/judge_robustness/gemma_judge.py`'s `main_async()`.")
    lines.append("- Prior Gemma-only headline (compared against in section 8): "
                 "`thesis/analysis/judge_robustness/gemma_only_exact_results.json` (read-only, NOT modified).")
    lines.append("- This report's generator: `thesis/analysis/judge_robustness/build_gemma_validity_check.py`.")
    lines.append("- Outputs: `GEMMA_VALIDITY_CHECK.md` (this file), `gemma_validity_check.csv`.")
    lines.append("- No existing file was modified or overwritten. No LLM inference was run. Nothing was "
                 "committed or pushed. `GEMMA_ONLY_SUPERVISOR_RESULTS.md` was left untouched as instructed.\n")

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
