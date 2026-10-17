import csv, json
from pathlib import Path

muse_csv = Path("saves/final_muse_news_openunlearning_selection/MUSE_News_selected_methods_summary.csv")

privacy_paths = {
    "before": "outputs/privacylens_muse_news_selected/muse_news_before/privacy_mcq_all493.json",
    "RMU": "outputs/privacylens_muse_news_selected/muse_news_rmu_selected/privacy_mcq_all493.json",
    "WGA": "outputs/privacylens_muse_news_selected/muse_news_wga_selected/privacy_mcq_all493.json",
    "SimNPO": "outputs/privacylens_muse_news_selected/muse_news_simnpo_selected/privacy_mcq_all493.json",
    "SatImp": "outputs/privacylens_muse_news_selected/muse_news_satimp_selected/privacy_mcq_all493.json",
}

selection_info = {
    "before": {
        "selected_checkpoint": "target",
        "selection_proxy": "",
        "mem_proxy": "",
        "utility_proxy": "",
    },
    "RMU": {
        "selected_checkpoint": "checkpoint-500",
        "selection_proxy": 0.540936208372925,
        "mem_proxy": 0.38219282668172244,
        "utility_proxy": 0.9252291431796247,
    },
    "WGA": {
        "selected_checkpoint": "checkpoint-357",
        "selection_proxy": 0.5033701140529139,
        "mem_proxy": 0.3720787370040039,
        "utility_proxy": 0.777836994090135,
    },
    "SimNPO": {
        "selected_checkpoint": "checkpoint-459",
        "selection_proxy": 0.2359898560493042,
        "mem_proxy": 0.13677233049917728,
        "utility_proxy": 0.8594607968226154,
    },
    "SatImp": {
        "selected_checkpoint": "checkpoint-500",
        "selection_proxy": 0.21155984735182545,
        "mem_proxy": 0.12057542307914175,
        "utility_proxy": 0.8620499182149219,
    },
}

with open(muse_csv) as f:
    muse_rows = {r["method"]: r for r in csv.DictReader(f)}

rows = []
for method in ["before", "RMU", "WGA", "SimNPO", "SatImp"]:
    m = muse_rows[method]
    p = json.load(open(privacy_paths[method]))["meta"]
    s = selection_info[method]

    rows.append({
        "method": method,
        "selected_checkpoint": s["selected_checkpoint"],
        "selection_proxy": s["selection_proxy"],
        "mem_proxy": s["mem_proxy"],
        "utility_proxy": s["utility_proxy"],

        "muse_forget_knowmem_ROUGE": m["forget_knowmem_ROUGE"],
        "muse_delta_forget_knowmem": m["delta_forget_knowmem"],
        "muse_forget_verbmem_ROUGE": m["forget_verbmem_ROUGE"],
        "muse_delta_forget_verbmem": m["delta_forget_verbmem"],
        "muse_extraction_strength": m["extraction_strength"],
        "muse_delta_extraction_strength": m["delta_extraction_strength"],
        "muse_retain_knowmem_ROUGE": m["retain_knowmem_ROUGE"],
        "muse_delta_retain_knowmem": m["delta_retain_knowmem"],
        "muse_privleak_report_only": m["privleak_report_only"],

        "privacylens_valid_responses": p["valid_responses"],
        "privacylens_total": p["total"],
        "privacylens_valid_rate": p["valid_rate"],
        "privacylens_privacy_awareness_accuracy": p["privacy_norm_awareness_accuracy"],
        "privacylens_leakage_proxy": p["leakage_proxy"],
        "model_path": p["model_path"],
    })

out = Path("saves/final_muse_news_openunlearning_selection/FINAL_MUSE_News_MUSE_plus_PrivacyLens.csv")
with open(out, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print("Saved:", out)
print()
print("method | checkpoint | MUSE selection | retain | extraction | PL acc | PL leak | PL valid")
for r in rows:
    print(
        f'{r["method"]:7s} | '
        f'{str(r["selected_checkpoint"]):14s} | '
        f'{str(r["selection_proxy"]):18s} | '
        f'{float(r["muse_retain_knowmem_ROUGE"]):.4f} | '
        f'{float(r["muse_extraction_strength"]):.4f} | '
        f'{float(r["privacylens_privacy_awareness_accuracy"]):.2f} | '
        f'{float(r["privacylens_leakage_proxy"]):.2f} | '
        f'{p["valid_responses"] if False else r["privacylens_valid_responses"]}/{r["privacylens_total"]}'
    )
