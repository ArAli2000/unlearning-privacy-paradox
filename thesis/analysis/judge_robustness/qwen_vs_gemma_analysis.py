#!/usr/bin/env python3
"""Compare the existing Qwen judgments (frozen, in external/PersistBench/outputs/)
against the new Gemma-3 judgments (external/PersistBench/outputs_gemma3_judge/)
for all 15 canonical PersistBench generation sets.

Read-only with respect to both judged trees; writes only into
thesis/analysis/judge_robustness/. Reuses external/PersistBench/analysis/
failure_rates.py's own fr_at_k (unmodified) rather than reimplementing FR@K.

Produces:
  - qwen_vs_gemma_frk.json / .md      : FR@K per track/category/method, both judges
  - qwen_vs_gemma_agreement.json      : exact-match rate + Cohen's kappa (unweighted
                                        and linear-weighted) per category/track
  - qwen_vs_gemma_disagreements.csv   : every generation where |qwen-gemma| >= 2
  - qwen_vs_gemma_mechanistic_transitions.json / .md :
        re-checks the existing MUSE-News sycophancy BASE->SatImp/SimNPO
        generation-0 transition groups (mechanistic/privacy_collapse/
        persistbench_native/analysis/sycophancy/sycophancy_transitions.json)
        against Gemma's scores for the same rows.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "external" / "PersistBench" / "analysis"))
from failure_rates import fr_at_k, THRESHOLDS  # noqa: E402

TRACKS = {
    "muse_news": {
        "label": "MUSE-News (Qwen2.5-7B-Instruct)",
        "qwen_dir": "external/PersistBench/outputs/muse_news_qwen25_selected_full",
        "gemma_dir": "external/PersistBench/outputs_gemma3_judge/muse_news",
        "methods": [
            ("BASE", "muse_news_qwen25_before"),
            ("SatImp", "muse_news_qwen25_satimp"),
            ("SimNPO", "muse_news_qwen25_simnpo"),
            ("RMU", "muse_news_qwen25_rmu"),
            ("WGA", "muse_news_qwen25_wga"),
        ],
        "gemma_suffix": ".gemma3.json",
    },
    "muse_books_llama2": {
        "label": "MUSE-Books (Llama-2-7B track)",
        "qwen_dir": "external/PersistBench/outputs/muse_books_llama2_selected_full",
        "gemma_dir": "external/PersistBench/outputs_gemma3_judge/muse_books",
        "methods": [
            ("BASE", "muse_books_llama2_before"),
            ("SatImp", "muse_books_llama2_satimp"),
            ("SimNPO", "muse_books_llama2_simnpo"),
            ("RMU", "muse_books_llama2_rmu"),
            ("WGA", "muse_books_llama2_wga"),
        ],
        "gemma_suffix": ".gemma3.json",
    },
    "muse_books_qwen25": {
        "label": "MUSE-Books (Qwen2.5-7B-Instruct track)",
        "qwen_dir": "external/PersistBench/outputs/muse_books_qwen25_selected_full",
        "gemma_dir": "external/PersistBench/outputs_gemma3_judge/muse_books",
        "methods": [
            ("BASE", "muse_books_qwen25_before"),
            ("SatImp", "muse_books_qwen25_satimp"),
            ("SimNPO", "muse_books_qwen25_simnpo"),
            ("RMU", "muse_books_qwen25_rmu"),
            ("WGA", "muse_books_qwen25_wga"),
        ],
        "gemma_suffix": ".gemma3.json",
    },
}

CATEGORIES = ["cross_domain", "sycophancy", "beneficial_memory_usage"]


def entry_category(entry: dict) -> str:
    ft = entry.get("failure_type") or entry.get("leakage_type", "cross_domain")
    if ft == "positive_memory_usage":
        ft = "beneficial_memory_usage"
    return ft


def load_scores(path: Path):
    """Return category -> model_key -> entry_id -> [scores...] (None for missing/error),
    plus a flat list of (entry_id, model_key, gen_index, category, score, reasoning)."""
    with open(path) as f:
        data = json.load(f)
    by_cat_model = defaultdict(lambda: defaultdict(dict))
    flat = []
    for entry_id, entry in data["entries"].items():
        cat = entry_category(entry)
        for model_key, model_data in entry["results"].items():
            scores = []
            for gi, gen in enumerate(model_data.get("generations", [])):
                judge = gen.get("judge")
                score = None if (gen.get("error") or judge is None) else judge.get("score")
                reasoning = None if judge is None else judge.get("reasoning")
                scores.append(score)
                flat.append((entry_id, model_key, gi, cat, score, reasoning))
            by_cat_model[cat][model_key][entry_id] = scores
    return by_cat_model, flat


def cohens_kappa(pairs, weighted=False):
    """pairs: list of (a, b) int score pairs, both in a small fixed rating range."""
    if not pairs:
        return None
    all_vals = sorted(set(v for pair in pairs for v in pair))
    n_cat = len(all_vals)
    idx = {v: i for i, v in enumerate(all_vals)}
    n = len(pairs)
    confusion = [[0] * n_cat for _ in range(n_cat)]
    for a, b in pairs:
        confusion[idx[a]][idx[b]] += 1
    row_marg = [sum(row) for row in confusion]
    col_marg = [sum(confusion[i][j] for i in range(n_cat)) for j in range(n_cat)]

    if weighted:
        max_diff = max(all_vals) - min(all_vals) or 1
        w = [[1 - abs(all_vals[i] - all_vals[j]) / max_diff for j in range(n_cat)] for i in range(n_cat)]
    else:
        w = [[1.0 if i == j else 0.0 for j in range(n_cat)] for i in range(n_cat)]

    po = sum(w[i][j] * confusion[i][j] for i in range(n_cat) for j in range(n_cat)) / n
    pe = sum(w[i][j] * row_marg[i] * col_marg[j] for i in range(n_cat) for j in range(n_cat)) / (n * n)
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else 0.0
    return (po - pe) / (1 - pe)


def main():
    all_flat = {}  # track -> method -> flat list
    all_by_cat_model = {}  # track -> method -> "qwen"/"gemma" -> by_cat_model

    for track_key, track in TRACKS.items():
        for method, fname in track["methods"]:
            qwen_path = REPO_ROOT / track["qwen_dir"] / f"{fname}.json"
            gemma_path = REPO_ROOT / track["gemma_dir"] / f"{fname}{track['gemma_suffix']}"
            if not qwen_path.is_file() or not gemma_path.is_file():
                print(f"FATAL: missing file for {track_key}/{method}: "
                      f"{qwen_path if not qwen_path.is_file() else gemma_path}", file=sys.stderr)
                sys.exit(1)
            qwen_by_cat_model, qwen_flat = load_scores(qwen_path)
            gemma_by_cat_model, gemma_flat = load_scores(gemma_path)
            all_by_cat_model[(track_key, method)] = {"qwen": qwen_by_cat_model, "gemma": gemma_by_cat_model}
            all_flat[(track_key, method)] = {"qwen": qwen_flat, "gemma": gemma_flat}

    # ---- FR@K tables ----
    frk_results = {}
    for track_key, track in TRACKS.items():
        frk_results[track_key] = {"label": track["label"], "methods": {}}
        for method, fname in track["methods"]:
            entry = {"qwen": {}, "gemma": {}}
            for judge in ("qwen", "gemma"):
                by_cat_model = all_by_cat_model[(track_key, method)][judge]
                for cat in CATEGORIES:
                    threshold, inverted = THRESHOLDS[cat]
                    model_keys = list(by_cat_model.get(cat, {}).keys())
                    if not model_keys:
                        continue
                    mk = model_keys[0]  # exactly one model_key per file, per discovery_report.md
                    scores_by_entry = by_cat_model[cat][mk]
                    max_k = max((len([s for s in v if s is not None]) for v in scores_by_entry.values()), default=0)
                    per_k = {}
                    for k in range(1, max_k + 1):
                        rate, n = fr_at_k(scores_by_entry, k, threshold, inverted)
                        per_k[f"FR@{k}"] = round(rate, 2)
                    per_k["n"] = max((len(v) for v in scores_by_entry.values()), default=0)
                    entry[judge][cat] = per_k
            frk_results[track_key]["methods"][method] = entry

    with open(THIS_DIR / "qwen_vs_gemma_frk.json", "w") as f:
        json.dump(frk_results, f, indent=2)

    # ---- Agreement (exact-match, kappa) per category (pooled across all 15 files) and per track ----
    agreement = {"overall": {}, "by_track": {}}
    pooled_pairs_by_cat = defaultdict(list)
    track_pairs_by_cat = defaultdict(lambda: defaultdict(list))
    disagreement_rows = []

    for (track_key, method), flats in all_flat.items():
        qwen_flat = {(e, m, gi): (cat, score, reasoning) for e, m, gi, cat, score, reasoning in flats["qwen"]}
        gemma_flat = {(e, m, gi): (cat, score, reasoning) for e, m, gi, cat, score, reasoning in flats["gemma"]}
        common_keys = set(qwen_flat) & set(gemma_flat)
        for key in common_keys:
            qcat, qscore, qreason = qwen_flat[key]
            gcat, gscore, greason = gemma_flat[key]
            if qscore is None or gscore is None:
                continue
            cat = qcat  # category is judge-independent (derived from entry, not from judge)
            pooled_pairs_by_cat[cat].append((qscore, gscore))
            track_pairs_by_cat[track_key][cat].append((qscore, gscore))
            if abs(qscore - gscore) >= 2:
                entry_id, model_key, gi = key
                disagreement_rows.append({
                    "track": track_key,
                    "method": method,
                    "entry_id": entry_id,
                    "model_key": model_key,
                    "generation_index": gi,
                    "category": cat,
                    "qwen_score": qscore,
                    "gemma_score": gscore,
                    "abs_diff": abs(qscore - gscore),
                    "qwen_reasoning": (qreason or "")[:200],
                    "gemma_reasoning": (greason or "")[:200],
                })

    for cat in CATEGORIES:
        pairs = pooled_pairs_by_cat[cat]
        n = len(pairs)
        exact = sum(1 for a, b in pairs if a == b) / n if n else None
        within1 = sum(1 for a, b in pairs if abs(a - b) <= 1) / n if n else None
        agreement["overall"][cat] = {
            "n": n,
            "exact_match_rate": round(exact, 4) if exact is not None else None,
            "within_1_rate": round(within1, 4) if within1 is not None else None,
            "cohens_kappa_unweighted": round(cohens_kappa(pairs, weighted=False), 4) if pairs else None,
            "cohens_kappa_linear_weighted": round(cohens_kappa(pairs, weighted=True), 4) if pairs else None,
        }

    for track_key in TRACKS:
        agreement["by_track"][track_key] = {}
        for cat in CATEGORIES:
            pairs = track_pairs_by_cat[track_key][cat]
            n = len(pairs)
            exact = sum(1 for a, b in pairs if a == b) / n if n else None
            agreement["by_track"][track_key][cat] = {
                "n": n,
                "exact_match_rate": round(exact, 4) if exact is not None else None,
                "cohens_kappa_unweighted": round(cohens_kappa(pairs, weighted=False), 4) if pairs else None,
                "cohens_kappa_linear_weighted": round(cohens_kappa(pairs, weighted=True), 4) if pairs else None,
            }

    with open(THIS_DIR / "qwen_vs_gemma_agreement.json", "w") as f:
        json.dump(agreement, f, indent=2)

    disagreement_rows.sort(key=lambda r: (-r["abs_diff"], r["track"], r["method"]))
    with open(THIS_DIR / "qwen_vs_gemma_disagreements.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(disagreement_rows[0].keys()) if disagreement_rows else
                                 ["track", "method", "entry_id", "model_key", "generation_index", "category",
                                  "qwen_score", "gemma_score", "abs_diff", "qwen_reasoning", "gemma_reasoning"])
        writer.writeheader()
        writer.writerows(disagreement_rows)

    # ---- Mechanistic transition-group check (MUSE-News sycophancy, generation index 0) ----
    mech_path = (REPO_ROOT / "mechanistic/privacy_collapse/persistbench_native/analysis/sycophancy/sycophancy_transitions.json")
    mech_check = {}
    if mech_path.is_file():
        with open(mech_path) as f:
            mech = json.load(f)
        gemma_before = all_by_cat_model[("muse_news", "BASE")]["gemma"]["sycophancy"]["muse_news_qwen25_before"]
        for method_name, method_key in (("SatImp", "SatImp"), ("SimNPO", "SimNPO")):
            gemma_method_dir = {"SatImp": "muse_news_qwen25_satimp", "SimNPO": "muse_news_qwen25_simnpo"}[method_name]
            gemma_method = all_by_cat_model[("muse_news", method_name)]["gemma"]["sycophancy"][gemma_method_dir]
            buckets = mech[method_key]
            recount = defaultdict(int)
            reclass_mismatches = []
            for bucket_name, bucket in buckets.items():
                for rec in bucket["records"]:
                    pid = rec["persistbench_id"]
                    gemma_base_scores = gemma_before.get(pid)
                    gemma_method_scores = gemma_method.get(pid)
                    if gemma_base_scores is None or gemma_method_scores is None:
                        continue
                    gb0 = gemma_base_scores[0] if gemma_base_scores else None
                    gm0 = gemma_method_scores[0] if gemma_method_scores else None
                    if gb0 is None or gm0 is None:
                        continue
                    gb_syc = gb0 >= 3
                    gm_syc = gm0 >= 3
                    gemma_bucket = f"{'sycophantic' if gb_syc else 'non_sycophantic'}_to_{'sycophantic' if gm_syc else 'non_sycophantic'}"
                    recount[gemma_bucket] += 1
                    if gemma_bucket != bucket_name:
                        reclass_mismatches.append({
                            "persistbench_id": pid,
                            "qwen_bucket": bucket_name,
                            "qwen_base_score": rec["base_score"],
                            "qwen_method_score": rec["method_score"],
                            "gemma_base_score": gb0,
                            "gemma_method_score": gm0,
                            "gemma_bucket": gemma_bucket,
                        })
            mech_check[method_key] = {
                "qwen_bucket_counts": {k: v["count"] for k, v in buckets.items()},
                "gemma_bucket_counts": dict(recount),
                "n_reclassified": len(reclass_mismatches),
                "n_total_checked": sum(v["count"] for v in buckets.values()),
                "reclassified_records": reclass_mismatches,
            }
    else:
        mech_check = {"error": f"expected manifest not found: {mech_path}"}

    with open(THIS_DIR / "qwen_vs_gemma_mechanistic_transitions.json", "w") as f:
        json.dump(mech_check, f, indent=2)

    write_markdown(frk_results, agreement, disagreement_rows, mech_check, THIS_DIR / "QWEN_VS_GEMMA_ANALYSIS.md")
    print("Wrote qwen_vs_gemma_frk.json, qwen_vs_gemma_agreement.json, "
          "qwen_vs_gemma_disagreements.csv, qwen_vs_gemma_mechanistic_transitions.json, "
          "QWEN_VS_GEMMA_ANALYSIS.md", file=sys.stderr)


def write_markdown(frk_results, agreement, disagreement_rows, mech_check, out_path):
    lines = ["# Qwen judge vs. Gemma-3 judge: full comparison\n"]

    lines.append("## Agreement (pooled across all 15 files, per category)\n")
    lines.append("| Category | N | Exact match | Within 1 | Kappa (unweighted) | Kappa (linear-weighted) |")
    lines.append("|---|---|---|---|---|---|")
    for cat, s in agreement["overall"].items():
        lines.append(f"| {cat} | {s['n']} | {s['exact_match_rate']} | {s['within_1_rate']} | "
                      f"{s['cohens_kappa_unweighted']} | {s['cohens_kappa_linear_weighted']} |")

    lines.append("\n## Agreement by track\n")
    lines.append("| Track | Category | N | Exact match | Kappa (unweighted) | Kappa (linear) |")
    lines.append("|---|---|---|---|---|---|")
    for track_key, cats in agreement["by_track"].items():
        for cat, s in cats.items():
            lines.append(f"| {track_key} | {cat} | {s['n']} | {s['exact_match_rate']} | "
                          f"{s['cohens_kappa_unweighted']} | {s['cohens_kappa_linear_weighted']} |")

    lines.append(f"\n## Disagreements (|Qwen - Gemma| >= 2): {len(disagreement_rows)} rows\n")
    lines.append("Full list in `qwen_vs_gemma_disagreements.csv`. Top 10 by absolute difference:\n")
    lines.append("| Track | Method | Category | Entry | Gen# | Qwen | Gemma | Diff |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in disagreement_rows[:10]:
        lines.append(f"| {r['track']} | {r['method']} | {r['category']} | {r['entry_id'][:8]} | "
                      f"{r['generation_index']} | {r['qwen_score']} | {r['gemma_score']} | {r['abs_diff']} |")

    lines.append("\n## FR@K: Qwen vs. Gemma, per track/category/method\n")
    for track_key, track_data in frk_results.items():
        lines.append(f"\n### {track_data['label']}\n")
        for cat in CATEGORIES:
            lines.append(f"\n**{cat}**\n")
            lines.append("| Method | Judge | FR@1 | FR@2 | FR@3 | N |")
            lines.append("|---|---|---|---|---|---|")
            for method, judges in track_data["methods"].items():
                for judge_name in ("qwen", "gemma"):
                    stats = judges[judge_name].get(cat)
                    if not stats:
                        continue
                    lines.append(f"| {method} | {judge_name} | {stats.get('FR@1','-')} | "
                                  f"{stats.get('FR@2','-')} | {stats.get('FR@3','-')} | {stats.get('n','-')} |")

    lines.append("\n## Mechanistic transition-group check "
                  "(MUSE-News sycophancy, generation index 0, BASE->SatImp/SimNPO)\n")
    lines.append("Source manifest: `mechanistic/privacy_collapse/persistbench_native/analysis/sycophancy/sycophancy_transitions.json` "
                  "(built from Qwen judge scores). Re-checked against Gemma-3 scores for the identical "
                  "`persistbench_id`s and generation index 0.\n")
    for method_key, check in mech_check.items():
        if method_key == "error":
            lines.append(f"ERROR: {mech_check['error']}")
            continue
        lines.append(f"\n**{method_key}** (N checked: {check['n_total_checked']}, "
                      f"reclassified under Gemma: {check['n_reclassified']})\n")
        lines.append(f"- Qwen bucket counts: {check['qwen_bucket_counts']}")
        lines.append(f"- Gemma bucket counts (same rows, same generation index): {check['gemma_bucket_counts']}")

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
