import json, re, csv, shutil
from pathlib import Path

before_path = Path("saves/eval/muse_news_target_before_eval/MUSE_SUMMARY.json")
before = json.load(open(before_path))

runs = {
    "SimNPO": Path("saves/unlearn/muse_news_simnpo_ckpts_bs1_gc_sbatch"),
    "WGA": Path("saves/unlearn/muse_news_wga_ckpts_bs1_gc_sbatch"),
    "RMU": Path("saves/unlearn/muse_news_rmu_ckpts_bs1_gc_sbatch"),
    "SatImp": Path("saves/unlearn/muse_news_satimp_ckpts_bs1_gc_sbatch"),
}

final_root = Path("saves/final_muse_news_openunlearning_selection")
final_root.mkdir(parents=True, exist_ok=True)

def hmean(vals, eps=1e-12):
    vals = [max(float(v), eps) for v in vals]
    return len(vals) / sum(1.0 / v for v in vals)

def ckpt_num(path):
    m = re.search(r"checkpoint-(\d+)", str(path))
    return int(m.group(1)) if m else -1

all_rows = []

for method, root in runs.items():
    files = sorted(root.glob("checkpoint-*/evals/MUSE_SUMMARY.json"), key=ckpt_num)
    if not files:
        print(f"Skipping {method}: no checkpoint summaries found in {root}")
        continue

    rows = []
    for f in files:
        d = json.load(open(f))
        ckpt = f.parts[-3]

        knowmem_forget_score = max(0.0, 1.0 - d["forget_knowmem_ROUGE"] / before["forget_knowmem_ROUGE"])
        verbmem_forget_score = max(0.0, 1.0 - d["forget_verbmem_ROUGE"] / before["forget_verbmem_ROUGE"])
        extraction_forget_score = max(0.0, 1.0 - d["extraction_strength"] / before["extraction_strength"])

        Mem_proxy = hmean([
            knowmem_forget_score,
            verbmem_forget_score,
            extraction_forget_score,
        ])

        Utility_proxy = max(0.0, d["retain_knowmem_ROUGE"] / before["retain_knowmem_ROUGE"])
        Selection_proxy = hmean([Mem_proxy, Utility_proxy])

        row = {
            "method": method,
            "checkpoint": ckpt,
            "checkpoint_path": str(root / ckpt),
            "forget_knowmem_ROUGE": d["forget_knowmem_ROUGE"],
            "forget_verbmem_ROUGE": d["forget_verbmem_ROUGE"],
            "extraction_strength": d["extraction_strength"],
            "retain_knowmem_ROUGE": d["retain_knowmem_ROUGE"],
            "privleak_report_only": d.get("privleak"),
            "knowmem_forget_score": knowmem_forget_score,
            "verbmem_forget_score": verbmem_forget_score,
            "extraction_forget_score": extraction_forget_score,
            "Mem_proxy": Mem_proxy,
            "Utility_proxy": Utility_proxy,
            "Selection_proxy": Selection_proxy,
        }
        rows.append(row)
        all_rows.append(row)

    rows = sorted(rows, key=lambda x: x["Selection_proxy"], reverse=True)
    best = rows[0]

    method_dir = final_root / method
    method_dir.mkdir(parents=True, exist_ok=True)

    with open(method_dir / f"MUSE_News_{method}_checkpoint_selection.csv", "w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    shutil.copy2(root / best["checkpoint"] / "evals" / "MUSE_SUMMARY.json",
                 method_dir / f"MUSE_News_{method}_{best['checkpoint']}_SUMMARY.json")
    shutil.copy2(root / best["checkpoint"] / "evals" / "MUSE_EVAL.json",
                 method_dir / f"MUSE_News_{method}_{best['checkpoint']}_EVAL.json")

    with open(method_dir / "SELECTED_CHECKPOINT.txt", "w") as fp:
        fp.write(f"method: {method}\n")
        fp.write(f"selected_checkpoint: {best['checkpoint']}\n")
        fp.write(f"checkpoint_path: {best['checkpoint_path']}\n")
        fp.write(f"Selection_proxy: {best['Selection_proxy']}\n")
        fp.write(f"Mem_proxy: {best['Mem_proxy']}\n")
        fp.write(f"Utility_proxy: {best['Utility_proxy']}\n")
        fp.write("Selection rule: harmonic_mean(Mem_proxy, Utility_proxy); privleak reported only.\n")

    print("=" * 80)
    print(f"{method}: selected {best['checkpoint']}")
    print(f"Selection_proxy: {best['Selection_proxy']:.6f}")
    print(f"Mem_proxy: {best['Mem_proxy']:.6f}")
    print(f"Utility_proxy: {best['Utility_proxy']:.6f}")
    print(f"Path: {best['checkpoint_path']}")
    print()

if all_rows:
    all_rows = sorted(all_rows, key=lambda x: (x["method"], -x["Selection_proxy"]))
    out = final_root / "MUSE_News_all_methods_checkpoint_selection.csv"
    with open(out, "w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    print("Saved combined table:", out)
