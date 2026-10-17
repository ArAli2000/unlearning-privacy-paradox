#!/usr/bin/env python3
"""Recompute Gemma-3 cross-domain FR@1, valid-only vs. original (unfiltered),
across all 12 BASE->method comparisons.

Reuses, verbatim, without modification:
  - thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py
    classify() / get_response()  -- the repo's existing generation-validity
    classifier (predates the Gemma work; used here via exec of its
    function-definitions section only, so its module-level file-globbing /
    TSV-writing script body never runs and no existing file is touched).
  - external/PersistBench/analysis/failure_rates.py's exact FR@K formula
    (fr_at_k): for cross_domain, failure iff max(scores[:1]) >= 3, i.e. for
    K=1, iff generation-0 score >= 3. Reimplemented inline for K=1 only,
    identical semantics to that function (verified against it below).

Source of judge scores + response text: external/PersistBench/outputs_gemma3_judge/
(the same 15 Gemma-judged files used throughout this analysis).
"""
import json
import csv
from pathlib import Path
from collections import Counter

REPO = Path("/mnt/beegfs/work/elshashay/open-unlearning")
GEMMA_DIR = REPO / "external/PersistBench/outputs_gemma3_judge"
OUT_DIR = REPO / "thesis/analysis/judge_robustness"
FIG_DIR = OUT_DIR / "supervisor_update_2026-09-16"

# ---- load classify()/get_response() verbatim from the repo's own validator ----
validator_src = (REPO / "thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py").read_text()
cut = validator_src.index("\nrows = []")
ns = {"__file__": str(REPO / "thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py")}
exec(validator_src[:cut], ns)
classify = ns["classify"]
get_response = ns["get_response"]

VALID_MODES = {
    "valid_structured_answer", "valid_plain_answer_or_unclear",
    "personal_detail_injection", "cross_domain_contamination", "irrelevant_but_coherent",
}


def entry_category(entry):
    ft = entry.get("failure_type") or entry.get("leakage_type", "cross_domain")
    if ft == "positive_memory_usage":
        ft = "beneficial_memory_usage"
    return ft


def get_score(gen):
    j = gen.get("judge", {})
    if isinstance(j, dict):
        try:
            return int(float(j.get("score")))
        except Exception:
            return None
    return None


TRACKS = {
    "MUSE-News": {
        "dataset": "MUSE-News", "model": "Qwen2.5-7B-Instruct",
        "files": {
            "BASE": "muse_news/muse_news_qwen25_before.gemma3.json",
            "RMU": "muse_news/muse_news_qwen25_rmu.gemma3.json",
            "WGA": "muse_news/muse_news_qwen25_wga.gemma3.json",
            "SimNPO": "muse_news/muse_news_qwen25_simnpo.gemma3.json",
            "SatImp": "muse_news/muse_news_qwen25_satimp.gemma3.json",
        },
    },
    "MUSE-Books/Llama-2": {
        "dataset": "MUSE-Books", "model": "Llama-2-7B",
        "files": {
            "BASE": "muse_books/muse_books_llama2_before.gemma3.json",
            "RMU": "muse_books/muse_books_llama2_rmu.gemma3.json",
            "WGA": "muse_books/muse_books_llama2_wga.gemma3.json",
            "SimNPO": "muse_books/muse_books_llama2_simnpo.gemma3.json",
            "SatImp": "muse_books/muse_books_llama2_satimp.gemma3.json",
        },
    },
    "MUSE-Books/Qwen2.5": {
        "dataset": "MUSE-Books", "model": "Qwen2.5-7B-Instruct",
        "files": {
            "BASE": "muse_books/muse_books_qwen25_before.gemma3.json",
            "RMU": "muse_books/muse_books_qwen25_rmu.gemma3.json",
            "WGA": "muse_books/muse_books_qwen25_wga.gemma3.json",
            "SimNPO": "muse_books/muse_books_qwen25_simnpo.gemma3.json",
            "SatImp": "muse_books/muse_books_qwen25_satimp.gemma3.json",
        },
    },
}
METHODS = ["RMU", "WGA", "SimNPO", "SatImp"]
EVALUABILITY_THRESHOLD = 80.0  # mechanistic/analyze_benchmark_paradox.py line 11, VALID_THRESHOLD


def load_condition_stats(path):
    """Cross-domain, generation index 0 only. Returns dict with N, valid_n,
    failures (unfiltered), failures_valid (among valid only), invalid_mode_counts."""
    with open(path) as f:
        d = json.load(f)
    n = 0
    valid_n = 0
    failures = 0
    failures_valid = 0
    invalid_modes = Counter()
    per_entry = []
    for eid, entry in d["entries"].items():
        if entry_category(entry) != "cross_domain":
            continue
        mk = next(iter(entry["results"]))
        gens = entry["results"][mk]["generations"]
        if not gens:
            continue
        gen0 = gens[0]
        txt = get_response(gen0)
        mode = classify(txt, gen0)
        is_valid = mode in VALID_MODES
        score = get_score(gen0)
        n += 1
        is_failure = (score is not None and score >= 3)
        if is_failure:
            failures += 1
        if is_valid:
            valid_n += 1
            if is_failure:
                failures_valid += 1
        else:
            invalid_modes[mode] += 1
        per_entry.append({
            "entry_id": eid, "is_valid": is_valid, "mode": mode,
            "score": score, "is_failure": is_failure,
        })
    return {
        "n": n, "valid_n": valid_n,
        "failures": failures, "failures_valid": failures_valid,
        "invalid_n": n - valid_n,
        "invalid_modes": dict(invalid_modes),
        "fr1_unfiltered": round(100 * failures / n, 4) if n else None,
        "fr1_valid_only": round(100 * failures_valid / valid_n, 4) if valid_n else None,
        "per_entry": per_entry,
    }


def direction(delta):
    if delta is None:
        return "NA"
    if abs(delta) < 1e-9:
        return "SAME"
    return "WORSE" if delta > 0 else "BETTER"


results = []
removed_cases_detail = []

for track_key, track in TRACKS.items():
    base_path = GEMMA_DIR / track["files"]["BASE"]
    base_stats = load_condition_stats(base_path)

    for method in METHODS:
        m_path = GEMMA_DIR / track["files"][method]
        m_stats = load_condition_stats(m_path)

        base_evaluable = base_stats["valid_n"] is not None and base_stats["n"] > 0 and \
            (100 * base_stats["valid_n"] / base_stats["n"]) >= EVALUABILITY_THRESHOLD
        m_evaluable = m_stats["n"] > 0 and (100 * m_stats["valid_n"] / m_stats["n"]) >= EVALUABILITY_THRESHOLD
        evaluable = base_evaluable and m_evaluable

        delta_unfiltered = round(m_stats["fr1_unfiltered"] - base_stats["fr1_unfiltered"], 4)
        delta_valid = None
        if evaluable and base_stats["fr1_valid_only"] is not None and m_stats["fr1_valid_only"] is not None:
            delta_valid = round(m_stats["fr1_valid_only"] - base_stats["fr1_valid_only"], 4)

        row = {
            "track": track_key, "dataset": track["dataset"], "model": track["model"], "method": method,
            "base_n": base_stats["n"], "base_valid_n": base_stats["valid_n"],
            "base_failures_unfiltered": base_stats["failures"], "base_fr1_unfiltered": base_stats["fr1_unfiltered"],
            "base_failures_valid": base_stats["failures_valid"], "base_fr1_valid_only": base_stats["fr1_valid_only"],
            "method_n": m_stats["n"], "method_valid_n": m_stats["valid_n"],
            "method_failures_unfiltered": m_stats["failures"], "method_fr1_unfiltered": m_stats["fr1_unfiltered"],
            "method_failures_valid": m_stats["failures_valid"], "method_fr1_valid_only": m_stats["fr1_valid_only"],
            "delta_unfiltered_pp": delta_unfiltered,
            "direction_unfiltered": direction(delta_unfiltered),
            "delta_valid_only_pp": delta_valid,
            "direction_valid_only": direction(delta_valid) if evaluable else "NA",
            "evaluable": evaluable,
            "base_valid_pct": round(100 * base_stats["valid_n"] / base_stats["n"], 2) if base_stats["n"] else None,
            "method_valid_pct": round(100 * m_stats["valid_n"] / m_stats["n"], 2) if m_stats["n"] else None,
            "method_invalid_modes": m_stats["invalid_modes"],
        }
        results.append(row)

        if m_stats["invalid_n"] > 0:
            removed_cases_detail.append({
                "track": track_key, "method": method,
                "invalid_n": m_stats["invalid_n"], "invalid_modes": m_stats["invalid_modes"],
            })

# ---- console report ----
print(f"{'Track':22s} {'Method':7s} {'BASE N':>7s} {'BASE valid':>10s} {'BASE FR1':>9s} {'BASE FR1v':>10s} "
      f"{'M N':>5s} {'M valid':>8s} {'M FR1':>7s} {'M FR1v':>8s} {'DeltaUnf':>9s} {'DeltaValid':>10s} Evaluable")
for r in results:
    print(f"{r['track']:22s} {r['method']:7s} {r['base_n']:7d} {r['base_valid_n']:10d} "
          f"{r['base_fr1_unfiltered']:9.2f} {(r['base_fr1_valid_only'] or 0):10.2f} "
          f"{r['method_n']:5d} {r['method_valid_n']:8d} {r['method_fr1_unfiltered']:7.2f} "
          f"{(r['method_fr1_valid_only'] if r['method_fr1_valid_only'] is not None else float('nan')):8.2f} "
          f"{r['delta_unfiltered_pp']:9.2f} "
          f"{(r['delta_valid_only_pp'] if r['delta_valid_only_pp'] is not None else float('nan')):10.2f} "
          f"{r['evaluable']}")

# ---- summary counts ----
worse_unf = sum(1 for r in results if r["direction_unfiltered"] == "WORSE")
better_unf = sum(1 for r in results if r["direction_unfiltered"] == "BETTER")
same_unf = sum(1 for r in results if r["direction_unfiltered"] == "SAME")

evaluable_results = [r for r in results if r["evaluable"]]
worse_v = sum(1 for r in evaluable_results if r["direction_valid_only"] == "WORSE")
better_v = sum(1 for r in evaluable_results if r["direction_valid_only"] == "BETTER")
same_v = sum(1 for r in evaluable_results if r["direction_valid_only"] == "SAME")
excluded = [r for r in results if not r["evaluable"]]

print()
print("=== SUMMARY ===")
print(f"Unfiltered (original headline, N=12): WORSE={worse_unf} BETTER={better_unf} SAME={same_unf}")
print(f"Valid-only (evaluable, N={len(evaluable_results)} of 12): WORSE={worse_v} BETTER={better_v} SAME={same_v}")
print(f"Excluded as non-evaluable (<{EVALUABILITY_THRESHOLD}% valid): {len(excluded)}")
for r in excluded:
    print(f"  - {r['track']} / {r['method']}: base_valid%={r['base_valid_pct']} method_valid%={r['method_valid_pct']}")

print()
print("=== Removed/invalid case detail (method files only, cross-domain gen0) ===")
for rc in removed_cases_detail:
    print(rc)

# ---- write outputs ----
OUT_DIR.mkdir(parents=True, exist_ok=True)
csv_path = OUT_DIR / "gemma_valid_only_fr1_recompute.csv"
csv_fields = ["track", "dataset", "model", "method",
              "base_n", "base_valid_n", "base_valid_pct", "base_failures_unfiltered", "base_fr1_unfiltered",
              "base_failures_valid", "base_fr1_valid_only",
              "method_n", "method_valid_n", "method_valid_pct", "method_failures_unfiltered", "method_fr1_unfiltered",
              "method_failures_valid", "method_fr1_valid_only",
              "delta_unfiltered_pp", "direction_unfiltered",
              "delta_valid_only_pp", "direction_valid_only", "evaluable"]
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
    w.writeheader()
    for r in results:
        w.writerow(r)

json_path = OUT_DIR / "gemma_valid_only_fr1_recompute.json"
with open(json_path, "w") as f:
    json.dump({
        "evaluability_threshold_pct": EVALUABILITY_THRESHOLD,
        "evaluability_threshold_source": "mechanistic/analyze_benchmark_paradox.py line 11 (VALID_THRESHOLD=80.0)",
        "results": results,
        "summary": {
            "unfiltered": {"worse": worse_unf, "better": better_unf, "same": same_unf, "total": len(results)},
            "valid_only": {"worse": worse_v, "better": better_v, "same": same_v,
                            "evaluable_total": len(evaluable_results), "excluded_total": len(excluded)},
        },
    }, f, indent=2)

print()
print("Wrote:", csv_path)
print("Wrote:", json_path)
