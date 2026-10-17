import json, csv
from pathlib import Path

before_path = Path("saves/eval/muse_news_target_before_eval/MUSE_SUMMARY.json")

selected = {
    "before": {
        "checkpoint": "target",
        "summary": before_path,
        "model_path": "muse-bench/MUSE-News_target",
    },
    "RMU": {
        "checkpoint": "checkpoint-500",
        "summary": Path("saves/unlearn/muse_news_rmu_ckpts_bs1_gc_sbatch/checkpoint-500/evals/MUSE_SUMMARY.json"),
        "model_path": "saves/unlearn/muse_news_rmu_ckpts_bs1_gc_sbatch/checkpoint-500",
    },
    "WGA": {
        "checkpoint": "checkpoint-357",
        "summary": Path("saves/unlearn/muse_news_wga_ckpts_bs1_gc_sbatch/checkpoint-357/evals/MUSE_SUMMARY.json"),
        "model_path": "saves/unlearn/muse_news_wga_ckpts_bs1_gc_sbatch/checkpoint-357",
    },
    "SimNPO": {
        "checkpoint": "checkpoint-459",
        "summary": Path("saves/unlearn/muse_news_simnpo_ckpts_bs1_gc_sbatch/checkpoint-459/evals/MUSE_SUMMARY.json"),
        "model_path": "saves/unlearn/muse_news_simnpo_ckpts_bs1_gc_sbatch/checkpoint-459",
    },
    "SatImp": {
        "checkpoint": "checkpoint-500",
        "summary": Path("saves/unlearn/muse_news_satimp_ckpts_bs1_gc_sbatch/checkpoint-500/evals/MUSE_SUMMARY.json"),
        "model_path": "saves/unlearn/muse_news_satimp_ckpts_bs1_gc_sbatch/checkpoint-500",
    },
}

before = json.load(open(before_path))

rows = []
for method, info in selected.items():
    d = json.load(open(info["summary"]))

    row = {
        "method": method,
        "checkpoint": info["checkpoint"],
        "model_path": info["model_path"],

        "forget_knowmem_ROUGE": d.get("forget_knowmem_ROUGE"),
        "delta_forget_knowmem": None if method == "before" else d.get("forget_knowmem_ROUGE") - before.get("forget_knowmem_ROUGE"),

        "forget_verbmem_ROUGE": d.get("forget_verbmem_ROUGE"),
        "delta_forget_verbmem": None if method == "before" else d.get("forget_verbmem_ROUGE") - before.get("forget_verbmem_ROUGE"),

        "extraction_strength": d.get("extraction_strength"),
        "delta_extraction_strength": None if method == "before" else d.get("extraction_strength") - before.get("extraction_strength"),

        "retain_knowmem_ROUGE": d.get("retain_knowmem_ROUGE"),
        "delta_retain_knowmem": None if method == "before" else d.get("retain_knowmem_ROUGE") - before.get("retain_knowmem_ROUGE"),

        "privleak_report_only": d.get("privleak"),
    }
    rows.append(row)

out_dir = Path("saves/final_muse_news_openunlearning_selection")
out_dir.mkdir(parents=True, exist_ok=True)

out_csv = out_dir / "MUSE_News_selected_methods_summary.csv"
with open(out_csv, "w", newline="") as fp:
    writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print("Saved:", out_csv)
print()
print("method,checkpoint,forget_knowmem,Δknowmem,forget_verbmem,Δverbmem,extraction,Δextraction,retain,Δretain,privleak")
for r in rows:
    print(
        r["method"],
        r["checkpoint"],
        r["forget_knowmem_ROUGE"],
        r["delta_forget_knowmem"],
        r["forget_verbmem_ROUGE"],
        r["delta_forget_verbmem"],
        r["extraction_strength"],
        r["delta_extraction_strength"],
        r["retain_knowmem_ROUGE"],
        r["delta_retain_knowmem"],
        r["privleak_report_only"],
        sep=","
    )
