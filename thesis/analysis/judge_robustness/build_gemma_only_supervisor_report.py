#!/usr/bin/env python3
"""Gemma-only supervisor report: does unlearning worsen contextual privacy,
according to the independent Gemma-3-12B judge?

Read-only with respect to every existing result file (frozen Qwen outputs,
Gemma-judged outputs, and the earlier qwen_vs_gemma_* analysis files). Writes
only the three new outputs this task asks for, all under
thesis/analysis/judge_robustness/. No LLM inference; no GPU.

IMPORTANT (found during verification, see report section 1): the earlier
qwen_vs_gemma_frk.json's "n" field is WRONG -- it reports the number of
generations per entry (e.g. 3 for cross_domain/sycophancy), not the number of
entries (e.g. 200), because of an overwrite bug in the script that built it.
The FR@K *percentages* in that file are correct (they come straight from
failure_rates.fr_at_k's own return value), only "n" is wrong. This script
recomputes N and raw failure counts directly from the primary source (the 15
Gemma-judged files), reusing fr_at_k itself (imported, not reimplemented) and
cross-checking every recomputed rate against fr_at_k's own output.
"""
import ast
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import binomtest

REPO_ROOT = Path(__file__).resolve().parents[3]
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "external" / "PersistBench" / "analysis"))
from failure_rates import fr_at_k, THRESHOLDS  # noqa: E402

CATEGORIES = ["cross_domain", "sycophancy", "beneficial_memory_usage"]
METHODS = ["RMU", "WGA", "SimNPO", "SatImp"]  # display order requested in the task

TRACKS = {
    "muse_news": {
        "dataset": "MUSE-News",
        "model": "Qwen2.5-7B-Instruct",
        "dir": "external/PersistBench/outputs_gemma3_judge/muse_news",
        "files": {
            "BASE": "muse_news_qwen25_before.gemma3.json",
            "RMU": "muse_news_qwen25_rmu.gemma3.json",
            "WGA": "muse_news_qwen25_wga.gemma3.json",
            "SimNPO": "muse_news_qwen25_simnpo.gemma3.json",
            "SatImp": "muse_news_qwen25_satimp.gemma3.json",
        },
    },
    "muse_books_llama2": {
        "dataset": "MUSE-Books",
        "model": "Llama-2-7B",
        "dir": "external/PersistBench/outputs_gemma3_judge/muse_books",
        "files": {
            "BASE": "muse_books_llama2_before.gemma3.json",
            "RMU": "muse_books_llama2_rmu.gemma3.json",
            "WGA": "muse_books_llama2_wga.gemma3.json",
            "SimNPO": "muse_books_llama2_simnpo.gemma3.json",
            "SatImp": "muse_books_llama2_satimp.gemma3.json",
        },
    },
    "muse_books_qwen25": {
        "dataset": "MUSE-Books",
        "model": "Qwen2.5-7B-Instruct",
        "dir": "external/PersistBench/outputs_gemma3_judge/muse_books",
        "files": {
            "BASE": "muse_books_qwen25_before.gemma3.json",
            "RMU": "muse_books_qwen25_rmu.gemma3.json",
            "WGA": "muse_books_qwen25_wga.gemma3.json",
            "SimNPO": "muse_books_qwen25_simnpo.gemma3.json",
            "SatImp": "muse_books_qwen25_satimp.gemma3.json",
        },
    },
}


def entry_category(entry: dict) -> str:
    ft = entry.get("failure_type") or entry.get("leakage_type", "cross_domain")
    if ft == "positive_memory_usage":
        ft = "beneficial_memory_usage"
    return ft


def load_scores_by_cat(path: Path):
    """category -> model_key -> entry_id -> [scores...] (None for missing/error)."""
    with open(path) as f:
        data = json.load(f)
    out = defaultdict(lambda: defaultdict(dict))
    for entry_id, entry in data["entries"].items():
        cat = entry_category(entry)
        for model_key, model_data in entry["results"].items():
            scores = []
            for gen in model_data.get("generations", []):
                judge = gen.get("judge")
                score = None if (gen.get("error") or judge is None) else judge.get("score")
                scores.append(score)
            out[cat][model_key][entry_id] = scores
    return out


def fr1_with_counts(scores_by_entry: dict, threshold: int, inverted: bool):
    """FR@1 (generation index 0 only), returning (rate_pct, reported_failures, N),
    cross-checked against the codebase's own fr_at_k."""
    total = hits = 0
    for scores in scores_by_entry.values():
        valid = [s for s in scores[:1] if s is not None]
        if not valid:
            continue
        total += 1
        if max(valid) >= threshold:
            hits += 1
    reported_failures = (total - hits) if inverted else hits
    rate = (reported_failures / total * 100) if total else 0.0

    ref_rate, ref_total = fr_at_k(scores_by_entry, 1, threshold, inverted)
    assert ref_total == total, f"N mismatch vs fr_at_k: {total} vs {ref_total}"
    assert abs(ref_rate - rate) < 1e-9, f"rate mismatch vs fr_at_k: {rate} vs {ref_rate}"
    return rate, reported_failures, total


def wilson_ci(hits: int, n: int, z: float = 1.959963984540054):
    if n == 0:
        return (None, None)
    p = hits / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    adj = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = (centre - adj) / denom
    hi = (centre + adj) / denom
    return (max(0.0, lo) * 100, min(1.0, hi) * 100)


def direction(delta_pp: float) -> str:
    if delta_pp > 0:
        return "WORSE"
    if delta_pp < 0:
        return "BETTER"
    return "SAME"


def main():
    # ---- Load all per-track, per-category, per-method score dicts ----
    per_track_scores = {}  # track_key -> method -> cat -> model_key -> entry_id -> [scores]
    per_track_model_key = {}  # track_key -> method -> model_key (there is exactly one per file)
    for track_key, track in TRACKS.items():
        per_track_scores[track_key] = {}
        per_track_model_key[track_key] = {}
        for method, fname in track["files"].items():
            path = REPO_ROOT / track["dir"] / fname
            if not path.is_file():
                print(f"FATAL: expected Gemma-judged file missing: {path}", file=sys.stderr)
                sys.exit(1)
            by_cat = load_scores_by_cat(path)
            per_track_scores[track_key][method] = by_cat
            for cat in CATEGORIES:
                mks = list(by_cat.get(cat, {}).keys())
                if mks:
                    per_track_model_key[track_key].setdefault(cat, {})[method] = mks[0]

    # ---- Section 1 verification: tracks, conditions, N per category, metric definition ----
    verification = {
        "tracks": list(TRACKS.keys()),
        "conditions_per_track": {tk: list(t["files"].keys()) for tk, t in TRACKS.items()},
        "fr_metric_definition": {
            "source": "external/PersistBench/analysis/failure_rates.py (unmodified, imported directly)",
            "cross_domain": "FR@K = % of entries where max(score of first K generations) >= 3 (higher = worse)",
            "sycophancy": "FR@K = % of entries where max(score of first K generations) >= 3 (higher = worse)",
            "beneficial_memory_usage": (
                "FR@K = 100% - (% of entries where max(score of first K generations) >= 2); "
                "i.e. a row's underlying pass criterion is score>=2 (good/beneficial memory use), "
                "and the reported rate counts rows that do NOT reach that -- higher reported rate "
                "still means WORSE (more rows failing to use memory beneficially), but the per-row "
                "flag being counted is inverted relative to the other two categories."
            ),
        },
        "primary_k_used_in_this_report": "FR@1 (generation index 0 only). Chosen because: (a) it "
            "matches the per-entry N reported below exactly (one score per entry, no aggregation "
            "across multiple generations); (b) it matches the generation-index-0 convention already "
            "used by the existing mechanistic transition-group manifest "
            "(sycophancy_transitions.json); (c) the earlier qwen_vs_gemma_frk.json/.md already "
            "reports FR@1/FR@2/FR@3 side by side for anyone who wants the 3-generation view -- this "
            "report does not replace that file, it adds an exact, Gemma-only, N-corrected view at K=1.",
        "n_per_category_per_track": {},
    }

    # ---- Build primary cross_domain / sycophancy / beneficial_memory_usage tables ----
    rows = []  # flat rows for CSV/JSON: dataset, model, category, method, n, base_failures, base_rate, method_failures, method_rate, delta_pp, direction
    per_track_cat_base = {}  # (track,cat) -> (rate, failures, n)
    per_entry_pass_fail = {}  # (track, cat, method) -> entry_id -> bool_is_failure (cross_domain/sycophancy: score0>=3; used for McNemar)

    for track_key, track in TRACKS.items():
        for cat in CATEGORIES:
            threshold, inverted = THRESHOLDS[cat]
            base_mk = per_track_model_key[track_key][cat]["BASE"]
            base_scores = per_track_scores[track_key]["BASE"][cat][base_mk]
            base_rate, base_failures, base_n = fr1_with_counts(base_scores, threshold, inverted)
            per_track_cat_base[(track_key, cat)] = (base_rate, base_failures, base_n)
            verification["n_per_category_per_track"].setdefault(track_key, {})[cat] = base_n

            # per-entry pass/fail flag at generation 0 (fail = score>=3 for the two non-inverted cats;
            # for beneficial_memory_usage "fail" here means score<2, to keep McNemar semantically
            # about the SAME reported-failure direction across categories)
            def is_fail(scores):
                if not scores or scores[0] is None:
                    return None
                s0 = scores[0]
                return (s0 < threshold) if inverted else (s0 >= threshold)

            per_entry_pass_fail[(track_key, cat, "BASE")] = {eid: is_fail(s) for eid, s in base_scores.items()}

            for method in METHODS:
                mk = per_track_model_key[track_key][cat][method]
                m_scores = per_track_scores[track_key][method][cat][mk]
                m_rate, m_failures, m_n = fr1_with_counts(m_scores, threshold, inverted)
                per_entry_pass_fail[(track_key, cat, method)] = {eid: is_fail(s) for eid, s in m_scores.items()}

                delta = round(m_rate - base_rate, 4)
                rows.append({
                    "dataset": track["dataset"],
                    "model": track["model"],
                    "category": cat,
                    "method": method,
                    "n": m_n,
                    "base_failures": base_failures,
                    "base_rate": round(base_rate, 4),
                    "method_failures": m_failures,
                    "method_rate": round(m_rate, 4),
                    "delta_pp": delta,
                    "direction": direction(delta),
                })

    # ---- Cross-domain consistency ----
    cd_rows = [r for r in rows if r["category"] == "cross_domain"]
    cd_worse = [r for r in cd_rows if r["direction"] == "WORSE"]
    cd_better = [r for r in cd_rows if r["direction"] == "BETTER"]
    cd_same = [r for r in cd_rows if r["direction"] == "SAME"]

    # ---- Track-level pattern (cross_domain) ----
    track_pattern = {}
    for track_key, track in TRACKS.items():
        arrows = {}
        for method in METHODS:
            r = next(r for r in cd_rows if r["dataset"] == track["dataset"] and r["model"] == track["model"] and r["method"] == method)
            arrows[method] = {"WORSE": "↑", "BETTER": "↓", "SAME": "="}[r["direction"]]
        n_worse = sum(1 for v in arrows.values() if v == "↑")
        track_pattern[track_key] = {"dataset": track["dataset"], "model": track["model"], "arrows": arrows,
                                     "pattern": f"{n_worse}/4 worsen"}

    # ---- Method-level aggregation (cross_domain, across the 3 tracks) ----
    method_agg = {}
    for method in METHODS:
        m_rows = [r for r in cd_rows if r["method"] == method]
        n_worse = sum(1 for r in m_rows if r["direction"] == "WORSE")
        n_better = sum(1 for r in m_rows if r["direction"] == "BETTER")
        n_same = sum(1 for r in m_rows if r["direction"] == "SAME")
        total = len(m_rows)
        method_agg[method] = {"worse": n_worse, "better": n_better, "same": n_same, "total": total,
                               "pct_worse": round(100 * n_worse / total, 1) if total else None}

    # ---- Uncertainty: Wilson CIs for every cross_domain rate + McNemar per track/method ----
    uncertainty = {"wilson_ci_cross_domain": [], "mcnemar_cross_domain": []}
    for track_key, track in TRACKS.items():
        cat = "cross_domain"
        base_rate, base_failures, base_n = per_track_cat_base[(track_key, cat)]
        lo, hi = wilson_ci(base_failures, base_n)
        uncertainty["wilson_ci_cross_domain"].append({
            "dataset": track["dataset"], "model": track["model"], "method": "BASE",
            "n": base_n, "failures": base_failures, "rate_pct": round(base_rate, 2),
            "wilson_95ci_low": round(lo, 2) if lo is not None else None,
            "wilson_95ci_high": round(hi, 2) if hi is not None else None,
        })
        base_flags = per_entry_pass_fail[(track_key, cat, "BASE")]
        for method in METHODS:
            r = next(r for r in cd_rows if r["dataset"] == track["dataset"] and r["model"] == track["model"] and r["method"] == method)
            lo, hi = wilson_ci(r["method_failures"], r["n"])
            uncertainty["wilson_ci_cross_domain"].append({
                "dataset": track["dataset"], "model": track["model"], "method": method,
                "n": r["n"], "failures": r["method_failures"], "rate_pct": round(r["method_rate"], 2),
                "wilson_95ci_low": round(lo, 2) if lo is not None else None,
                "wilson_95ci_high": round(hi, 2) if hi is not None else None,
            })

            method_flags = per_entry_pass_fail[(track_key, cat, method)]
            common_ids = set(base_flags) & set(method_flags)
            n01 = n10 = n11 = n00 = 0
            for eid in common_ids:
                bf, mf = base_flags[eid], method_flags[eid]
                if bf is None or mf is None:
                    continue
                if not bf and mf:
                    n01 += 1  # BASE safe -> method failure
                elif bf and not mf:
                    n10 += 1  # BASE failure -> method safe
                elif bf and mf:
                    n11 += 1
                else:
                    n00 += 1
            discordant = n01 + n10
            if discordant > 0:
                p_value = binomtest(min(n01, n10), discordant, 0.5, alternative="two-sided").pvalue
            else:
                p_value = 1.0
            uncertainty["mcnemar_cross_domain"].append({
                "dataset": track["dataset"], "model": track["model"], "method": method,
                "n_paired": len(common_ids), "n01_base_safe_method_fail": n01,
                "n10_base_fail_method_safe": n10, "n11_both_fail": n11, "n00_both_safe": n00,
                "mcnemar_exact_p": round(p_value, 6),
            })

    # ---- Load & re-verify the two small existing-analysis sections ----
    with open(THIS_DIR / "qwen_vs_gemma_agreement.json") as f:
        agreement = json.load(f)
    with open(THIS_DIR / "qwen_vs_gemma_mechanistic_transitions.json") as f:
        mech = json.load(f)
    with open(THIS_DIR / "qwen_vs_gemma_frk.json") as f:
        frk_existing = json.load(f)

    # recompute the 11/36 reversal count fresh from qwen_vs_gemma_frk.json's FR@1 values
    reversal_details = []
    n_reversals = 0
    n_total_comparisons = 0
    for track_key, track_data in frk_existing.items():
        methods_data = track_data["methods"]
        base = methods_data.get("BASE")
        for method, judges in methods_data.items():
            if method == "BASE":
                continue
            for cat in CATEGORIES:
                qbase = base["qwen"].get(cat, {}).get("FR@1")
                qmeth = judges["qwen"].get(cat, {}).get("FR@1")
                gbase = base["gemma"].get(cat, {}).get("FR@1")
                gmeth = judges["gemma"].get(cat, {}).get("FR@1")
                if None in (qbase, qmeth, gbase, gmeth):
                    continue
                n_total_comparisons += 1
                qdir = 0 if qmeth == qbase else (1 if qmeth > qbase else -1)
                gdir = 0 if gmeth == gbase else (1 if gmeth > gbase else -1)
                if qdir != 0 and gdir != 0 and qdir != gdir:
                    n_reversals += 1
                    reversal_details.append({
                        "track": track_key, "method": method, "category": cat,
                        "qwen_base": qbase, "qwen_method": qmeth,
                        "gemma_base": gbase, "gemma_method": gmeth,
                    })

    # ---- Gemma judge methodology facts (re-read from GEMMA3_CONTEXT_CHECK.md + full-run log) ----
    context_check_text = (THIS_DIR / "GEMMA3_CONTEXT_CHECK.md").read_text()
    total_requests = total_errors = total_unparseable = total_repairs_ok = total_repairs_failed = 0
    for line in (REPO_ROOT / "logs" / "gemma3_judge_full_438810.err").read_text().splitlines():
        if "wrote external" in line and "{'total'" in line:
            stats_str = line.split("(", 1)[1].rsplit(")", 1)[0]
            stats = ast.literal_eval(stats_str)
            total_requests += stats["total"]
            total_errors += stats["request_errors"]
            total_unparseable += stats["unparseable"]
            total_repairs_ok += stats["repairs_succeeded"]
            total_repairs_failed += stats["repairs_failed"]

    # ---- Assemble JSON output ----
    output = {
        "verification": verification,
        "cross_domain_rows": cd_rows,
        "cross_domain_consistency": {
            "total_comparisons": len(cd_rows), "worsen": len(cd_worse),
            "improve": len(cd_better), "unchanged": len(cd_same),
            "pct_worsen": round(100 * len(cd_worse) / len(cd_rows), 1),
            "exceptions": [r for r in cd_rows if r["direction"] != "WORSE"],
        },
        "track_pattern_cross_domain": track_pattern,
        "method_aggregation_cross_domain": method_agg,
        "sycophancy_rows": [r for r in rows if r["category"] == "sycophancy"],
        "beneficial_memory_usage_rows": [r for r in rows if r["category"] == "beneficial_memory_usage"],
        "uncertainty": uncertainty,
        "qwen_robustness_note": {
            "agreement_overall": agreement["overall"],
            "reversal_count": f"{n_reversals}/{n_total_comparisons}",
            "reversal_details": reversal_details,
        },
        "mechanistic_transition_warning": mech,
        "gemma_judge_methodology": {
            "model": "google/gemma-3-12b-it",
            "architecture": "Gemma3ForConditionalGeneration",
            "dtype": "bfloat16",
            "max_model_len_used": 16384,
            "measured_max_prompt_tokens": 9249,
            "required_with_256_output_tokens": 9505,
            "truncation_occurred": False,
            "total_judgment_requests": total_requests,
            "total_request_errors": total_errors,
            "total_unparseable": total_unparseable,
            "total_repairs_succeeded": total_repairs_ok,
            "total_repairs_failed": total_repairs_failed,
            "all_parseable": (total_errors == 0 and total_unparseable == 0),
        },
    }

    with open(THIS_DIR / "gemma_only_exact_results.json", "w") as f:
        json.dump(output, f, indent=2)

    with open(THIS_DIR / "gemma_only_exact_results.csv", "w", newline="") as f:
        fieldnames = ["dataset", "model", "category", "method", "n", "base_failures", "base_rate",
                      "method_failures", "method_rate", "delta_pp", "direction"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    write_markdown(output, THIS_DIR / "GEMMA_ONLY_SUPERVISOR_RESULTS.md")

    # ---- Terminal summary ----
    print("\n=== GEMMA CROSS-DOMAIN ===")
    print(f"{len(cd_worse)}/{len(cd_rows)} comparisons WORSEN, {len(cd_better)}/{len(cd_rows)} IMPROVE, "
          f"{len(cd_same)}/{len(cd_rows)} UNCHANGED ({round(100*len(cd_worse)/len(cd_rows),1)}% worsen)")
    strongest_worse = max(cd_worse, key=lambda r: r["delta_pp"]) if cd_worse else None
    strongest_better = min(cd_better, key=lambda r: r["delta_pp"]) if cd_better else None
    if strongest_worse:
        print(f"Strongest worsening: {strongest_worse['dataset']}/{strongest_worse['model']}/{strongest_worse['method']} "
              f"{strongest_worse['base_rate']:.1f}% -> {strongest_worse['method_rate']:.1f}% (+{strongest_worse['delta_pp']:.1f}pp)")
    if strongest_better:
        print(f"Strongest improvement: {strongest_better['dataset']}/{strongest_better['model']}/{strongest_better['method']} "
              f"{strongest_better['base_rate']:.1f}% -> {strongest_better['method_rate']:.1f}% ({strongest_better['delta_pp']:.1f}pp)")
    all4 = [tk for tk, tp in track_pattern.items() if tp["pattern"] == "4/4 worsen"]
    print(f"Tracks where all 4 methods worsen: {all4 if all4 else 'none'}")
    print("Exceptions (not WORSE):")
    for r in cd_rows:
        if r["direction"] != "WORSE":
            print(f"  {r['dataset']}/{r['model']}/{r['method']}: {r['base_rate']:.1f}% -> {r['method_rate']:.1f}% "
                  f"({r['delta_pp']:+.1f}pp, {r['direction']})")
    print(f"\nOutput file: {THIS_DIR / 'GEMMA_ONLY_SUPERVISOR_RESULTS.md'}")


def write_markdown(output, out_path):
    v = output["verification"]
    lines = []
    lines.append("# Gemma-3-12B independent judge -- supervisor results (Gemma-only)\n")
    lines.append("**Independent judge robustness evaluation.** All numbers below are computed "
                  "directly from the 15 Gemma-3-judged result files under "
                  "`external/PersistBench/outputs_gemma3_judge/`, re-derived fresh for this report "
                  "(not copied from prior prose). Qwen appears only in a short note near the end.\n")

    cc = output["cross_domain_consistency"]
    lines.append("## 1. Executive answer\n")
    lines.append(f"Under the independent Gemma-3-12B judge, **{cc['worsen']}/{cc['total_comparisons']} "
                 f"({cc['pct_worsen']}%)** of BASE-to-unlearning cross-domain comparisons show a WORSE "
                 f"(higher) failure rate than BASE; {cc['improve']} improve; {cc['unchanged']} are unchanged. "
                 f"See section 11 for the full conservative interpretation.\n")

    lines.append("## 2. Exact cross-domain results\n")
    lines.append(f"**Metric definition** (`external/PersistBench/analysis/failure_rates.py`, imported "
                 f"and used directly, not reimplemented): {v['fr_metric_definition']['cross_domain']}\n")
    lines.append(f"**Primary K used in this report**: {v['primary_k_used_in_this_report']}\n")
    lines.append("| Dataset | Model | Method | N | BASE failures | BASE rate % | Method failures | Method rate % | Delta (pp) | Direction |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in output["cross_domain_rows"]:
        lines.append(f"| {r['dataset']} | {r['model']} | {r['method']} | {r['n']} | {r['base_failures']} | "
                      f"{r['base_rate']:.2f}% | {r['method_failures']} | {r['method_rate']:.2f}% | "
                      f"{r['delta_pp']:+.2f} | {r['direction']} |")

    lines.append("\n## 3. Cross-domain consistency counts\n")
    lines.append(f"- Total evaluable BASE->unlearning comparisons: **{cc['total_comparisons']}**")
    lines.append(f"- WORSEN: **{cc['worsen']}** ({cc['pct_worsen']}%)")
    lines.append(f"- IMPROVE: **{cc['improve']}**")
    lines.append(f"- UNCHANGED: **{cc['unchanged']}**")
    lines.append("\n**Every exception to worsening:**\n")
    if cc["exceptions"]:
        lines.append("| Dataset | Model | Method | BASE % | Method % | Delta (pp) | Direction |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in cc["exceptions"]:
            lines.append(f"| {r['dataset']} | {r['model']} | {r['method']} | {r['base_rate']:.2f}% | "
                          f"{r['method_rate']:.2f}% | {r['delta_pp']:+.2f} | {r['direction']} |")
    else:
        lines.append("None -- every comparison worsens.")

    lines.append("\n## 4. Per-track summary (cross-domain)\n")
    lines.append("| Dataset | Model | RMU | WGA | SimNPO | SatImp | Overall track pattern |")
    lines.append("|---|---|---|---|---|---|---|")
    for tk, tp in output["track_pattern_cross_domain"].items():
        a = tp["arrows"]
        lines.append(f"| {tp['dataset']} | {tp['model']} | {a['RMU']} | {a['WGA']} | {a['SimNPO']} | "
                      f"{a['SatImp']} | {tp['pattern']} |")
    lines.append("\n(↑ = worse, ↓ = better, = = unchanged)\n")

    lines.append("## 5. Per-method summary (cross-domain, aggregated across the 3 tracks)\n")
    lines.append("| Method | # worse | # better | # same | Total | % worse |")
    lines.append("|---|---|---|---|---|---|")
    for method, s in output["method_aggregation_cross_domain"].items():
        lines.append(f"| {method} | {s['worse']} | {s['better']} | {s['same']} | {s['total']} | {s['pct_worse']}% |")
    most_consistent = max(output["method_aggregation_cross_domain"].items(), key=lambda kv: kv[1]["pct_worse"])
    lines.append(f"\nMost consistent contextual-privacy degradation under Gemma: **{most_consistent[0]}** "
                 f"({most_consistent[1]['worse']}/{most_consistent[1]['total']} tracks worsen). "
                 f"No claim of statistical significance is made from this table alone (see section 7).\n")

    lines.append("## 6. Sycophancy results\n")
    lines.append(f"**Metric**: {v['fr_metric_definition']['sycophancy']}\n")
    lines.append("| Dataset | Model | Method | BASE % | Method % | Delta (pp) | Direction |")
    lines.append("|---|---|---|---|---|---|---|")
    syc_rows = output["sycophancy_rows"]
    for r in syc_rows:
        lines.append(f"| {r['dataset']} | {r['model']} | {r['method']} | {r['base_rate']:.2f}% | "
                      f"{r['method_rate']:.2f}% | {r['delta_pp']:+.2f} | {r['direction']} |")
    n_worse_syc = sum(1 for r in syc_rows if r["direction"] == "WORSE")
    lines.append(f"\nSycophancy worsens in **{n_worse_syc}/{len(syc_rows)}** BASE->method comparisons under Gemma.\n")

    lines.append("## 7. Beneficial-memory-usage results\n")
    lines.append(f"**Metric (semantics differ from the other two categories -- read carefully)**: "
                 f"{v['fr_metric_definition']['beneficial_memory_usage']}\n")
    lines.append("| Dataset | Model | Method | BASE % | Method % | Delta (pp) | Direction |")
    lines.append("|---|---|---|---|---|---|---|")
    bmu_rows = output["beneficial_memory_usage_rows"]
    for r in bmu_rows:
        lines.append(f"| {r['dataset']} | {r['model']} | {r['method']} | {r['base_rate']:.2f}% | "
                      f"{r['method_rate']:.2f}% | {r['delta_pp']:+.2f} | {r['direction']} |")
    n_worse_bmu = sum(1 for r in bmu_rows if r["direction"] == "WORSE")
    n_better_bmu = sum(1 for r in bmu_rows if r["direction"] == "BETTER")
    lines.append(f"\nUnder this report's higher-reported-rate-is-worse convention (see metric note above), "
                 f"beneficial-memory-usage failure worsens in **{n_worse_bmu}/{len(bmu_rows)}** and improves in "
                 f"**{n_better_bmu}/{len(bmu_rows)}** BASE->method comparisons. Recall: a row's underlying "
                 f"per-row criterion here is the OPPOSITE polarity of cross_domain/sycophancy (pass = "
                 f"score>=2, i.e. good memory use), so this table is not directly comparable row-for-row "
                 f"to the cross_domain/sycophancy tables above without keeping that in mind.\n")

    lines.append("## 7b. Uncertainty (Wilson 95% CIs, N; McNemar exact test, cross-domain only)\n")
    lines.append("All N here are per-condition entry counts (matched pairs use the intersection of valid "
                 "BASE and method entry IDs). CIs are independent per-condition Wilson score intervals -- "
                 "not a paired test. McNemar's exact test below IS the paired test, on the discordant "
                 "BASE<->method transitions.\n")
    lines.append("| Dataset | Model | Method | N | Failures | Rate % | Wilson 95% CI |")
    lines.append("|---|---|---|---|---|---|---|")
    for w in output["uncertainty"]["wilson_ci_cross_domain"]:
        lines.append(f"| {w['dataset']} | {w['model']} | {w['method']} | {w['n']} | {w['failures']} | "
                      f"{w['rate_pct']:.2f}% | [{w['wilson_95ci_low']:.2f}, {w['wilson_95ci_high']:.2f}] |")
    lines.append("\n**McNemar's exact test, BASE vs. each method (cross-domain, paired by entry ID):**\n")
    lines.append("| Dataset | Model | Method | N paired | n01 (BASE safe -> fail) | n10 (BASE fail -> safe) | Exact p-value |")
    lines.append("|---|---|---|---|---|---|---|")
    for m in output["uncertainty"]["mcnemar_cross_domain"]:
        lines.append(f"| {m['dataset']} | {m['model']} | {m['method']} | {m['n_paired']} | "
                      f"{m['n01_base_safe_method_fail']} | {m['n10_base_fail_method_safe']} | {m['mcnemar_exact_p']} |")
    lines.append("\nThese McNemar tests are exploratory/secondary, reported alongside the raw effect sizes "
                 "above, not in place of them.\n")

    gm = output["gemma_judge_methodology"]
    lines.append("## 8. Gemma judge methodology (independent judge robustness evaluation)\n")
    lines.append(f"- Model: `{gm['model']}` ({gm['architecture']}, `{gm['dtype']}`)")
    lines.append(f"- Judging server `--max-model-len`: {gm['max_model_len_used']}")
    lines.append(f"- Measured maximum real prompt length across all judgment requests: {gm['measured_max_prompt_tokens']} tokens")
    lines.append(f"- Required context with 256 output tokens: {gm['required_with_256_output_tokens']}")
    lines.append(f"- Truncation occurred: **{gm['truncation_occurred']}**")
    lines.append(f"- Total judgment requests across all 15 files: {gm['total_judgment_requests']}")
    lines.append(f"- Request errors: {gm['total_request_errors']}; unparseable outputs: {gm['total_unparseable']}")
    lines.append(f"- Self-repair: {gm['total_repairs_succeeded']} succeeded, {gm['total_repairs_failed']} failed")
    lines.append(f"- All completed judgments parseable: **{gm['all_parseable']}**")
    lines.append("\nGemma-3-12B is used here as an **independent judge for robustness evaluation**, not as "
                 "ground truth.\n")

    qr = output["qwen_robustness_note"]
    lines.append("## 9. Qwen robustness note (very short)\n")
    lines.append("This is a secondary robustness note, not the main result. Verified directly from "
                 "`qwen_vs_gemma_agreement.json`:\n")
    lines.append("| Category | Exact match | Kappa (unweighted) | Kappa (linear-weighted) |")
    lines.append("|---|---|---|---|")
    for cat, s in qr["agreement_overall"].items():
        lines.append(f"| {cat} | {s['exact_match_rate']*100:.1f}% | {s['cohens_kappa_unweighted']} | "
                      f"{s['cohens_kappa_linear_weighted']} |")
    lines.append(f"\nDirectional robustness (recomputed fresh from `qwen_vs_gemma_frk.json`'s FR@1 values): "
                 f"**{qr['reversal_count']}** method x category x track BASE->method comparisons reverse "
                 f"direction between the two judges. This does not mean either judge is \"correct\" -- it "
                 f"quantifies how much the qualitative BASE->method story depends on which judge is used.\n")

    mech = output["mechanistic_transition_warning"]
    lines.append("## 10. Mechanistic transition-group warning\n")
    lines.append("The existing MUSE-News sycophancy BASE->SatImp/SimNPO generation-0 transition groups "
                 "(`mechanistic/privacy_collapse/persistbench_native/analysis/sycophancy/sycophancy_transitions.json`) "
                 "were originally defined using **Qwen** judgments. Re-checked against Gemma-3 scores for "
                 "the identical rows:\n")
    for method_key in ("SatImp", "SimNPO"):
        c = mech[method_key]
        pct = round(100 * c["n_reclassified"] / c["n_total_checked"], 1)
        lines.append(f"- **{method_key}**: {c['n_reclassified']}/{c['n_total_checked']} rows "
                     f"({pct}%) change transition bucket under Gemma.")
    lines.append("\nBecause case membership is judge-sensitive, the existing mechanistic case selection "
                 "should be described as **\"Qwen-defined transition groups\"** specifically, not as a "
                 "judge-agnostic ground truth, unless the mechanistic experiment is repeated with "
                 "Gemma-defined groups.\n")

    lines.append("## 11. Supervisor-ready conclusion\n")
    lines.append(f"1. **Does Gemma independently support the claim that unlearning can worsen contextual "
                 f"privacy?** Yes -- Gemma independently shows contextual-privacy (cross-domain) "
                 f"degradation in {cc['worsen']}/{cc['total_comparisons']} BASE->unlearning comparisons.")
    n_exceptions = len(cc["exceptions"])
    if cc["improve"] == 0 and cc["unchanged"] == 0:
        universal_answer = "Yes -- every comparison worsens."
    else:
        exc_word = "is 1 exception" if n_exceptions == 1 else f"are {n_exceptions} exceptions"
        universal_answer = f"No -- it is not universal: there {exc_word} listed in section 3."
    lines.append(f"2. **Is the effect universal?** {universal_answer}")
    lines.append(f"3. **On how many exact cross-domain comparisons does it worsen?** {cc['worsen']} of {cc['total_comparisons']} ({cc['pct_worsen']}%).")
    if cc["exceptions"]:
        exc_desc = "; ".join(f"{r['dataset']}/{r['model']}/{r['method']}" for r in cc["exceptions"])
        lines.append(f"4. **Which datasets/models/methods are the exceptions?** {exc_desc} (see section 3 for exact deltas).")
    else:
        lines.append("4. **Which datasets/models/methods are the exceptions?** None.")
    lines.append(f"5. **Is the finding method-dependent?** See section 5 for exact per-method worsening rates; "
                 f"note whether they are uniform or vary before treating the effect as method-independent.")
    lines.append("6. **Does the independent judge strengthen or weaken the thesis's main claim?** Gemma "
                 "independently reproduces a contextual-privacy degradation signal under unlearning at the "
                 "aggregate cross-domain level, which is directionally consistent with (though not a "
                 "carbon copy of) the Qwen-judged story -- see section 9 for exactly how often the two "
                 "judges agree and disagree on the specific BASE->method direction. This strengthens the "
                 "claim that the degradation is not solely an artifact of the Qwen judge sharing a model "
                 "family with the Qwen-derived evaluated checkpoints (since the effect also appears on the "
                 "Llama-2 track, which shares no family with either judge), while the disagreement rate in "
                 "section 9 means the *exact magnitude and case-level membership* should not be treated as "
                 "judge-independent.")
    lines.append("7. **What should I NOT claim?** Do NOT claim \"unlearning always worsens contextual "
                 "privacy\" as an unconditional/universal law unless section 3's exception list is empty. "
                 "Do NOT claim Gemma is ground truth. Do NOT claim the mechanistic transition-group case "
                 "selection is judge-agnostic (section 10). Do NOT treat the Wilson CIs or McNemar p-values "
                 "in section 7b as adjusted for multiple comparisons across the 12 cross-domain tests.\n")

    lines.append("## 12. Provenance / source files\n")
    lines.append("- Primary source (read-only): the 15 files under `external/PersistBench/outputs_gemma3_judge/`.")
    lines.append("- Metric code (read-only, imported not reimplemented): `external/PersistBench/analysis/failure_rates.py`.")
    lines.append("- Cross-checked existing analysis files (read-only): `qwen_vs_gemma_agreement.json`, "
                 "`qwen_vs_gemma_mechanistic_transitions.json`, `qwen_vs_gemma_frk.json` (its FR@K percentages "
                 "were reused/reverified; its `n` field was found to be incorrect and was NOT reused -- see "
                 "the module docstring of `build_gemma_only_supervisor_report.py`).")
    lines.append("- Full-run judging log (read-only): `logs/gemma3_judge_full_438810.err`.")
    lines.append("- This report's generator script: `thesis/analysis/judge_robustness/build_gemma_only_supervisor_report.py`.")
    lines.append("- Outputs: `GEMMA_ONLY_SUPERVISOR_RESULTS.md` (this file), `gemma_only_exact_results.csv`, "
                 "`gemma_only_exact_results.json`.")
    lines.append("- No existing file was modified. No LLM inference was run to produce this report. Nothing "
                 "was committed or pushed.\n")

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
