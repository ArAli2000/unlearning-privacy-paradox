import json
import re
from pathlib import Path
from collections import Counter
from statistics import mean

# Repo root, computed dynamically instead of a hardcoded cluster path (fixed
# 2026-09-14; this file lives at thesis/scripts/validation/<this file>, so
# three parents up is the repo root). Override with REPO_ROOT if needed.
import os
ROOT = Path(os.environ["REPO_ROOT"]) if os.environ.get("REPO_ROOT") else Path(__file__).resolve().parents[3]
OUTROOT = ROOT / "external/PersistBench/outputs"
OUT_TSV = OUTROOT / "PERSISTBENCH_ALL_DATASETS_VALIDITY_SUMMARY_WITH_MUSE.tsv"

def include_file(p):
    s = str(p).lower()

    if not p.name.endswith(".json"):
        return False

    if "backup_before_rejudge" in s:
        return False
    if "judge_test" in s:
        return False
    if "summary" in p.name.lower():
        return False

    tofu = "final_tofu_persistbench_localjudge" in s and p.name.endswith("_localjudge.json")
    wmdp = "wmdp_cyber_all4_selected_full_localjudge" in s and p.name.endswith("_localjudge.json")
    strict = "wmdp_cyber_qwen_strictgen_limit50_localjudge" in s and p.name.endswith("_localjudge.json")

    muse = any(x in s for x in [
        "muse_news_selected_full/",
        "muse_news_qwen25_selected_full/",
        "muse_books_llama2_selected_full/",
        "muse_books_qwen25_selected_full/",
    ])

    return tofu or wmdp or strict or muse

def dataset_name(p):
    s = str(p).lower()
    if "wmdp_cyber_qwen_strictgen_limit50" in s:
        return "WMDP-Cyber strict50"
    if "wmdp_cyber" in s:
        return "WMDP-Cyber"
    if "muse_news" in s:
        return "MUSE-News"
    if "muse_books" in s:
        return "MUSE-Books"
    if "tofu" in s:
        return "TOFU"
    return "UNKNOWN"

def model_name(label, p):
    s = (label + " " + str(p)).lower()
    if "qwen25_14b" in s:
        return "Qwen2.5-14B"
    if "qwen25_7b" in s or "qwen25" in s:
        return "Qwen2.5-7B"
    if "qwen25_3b" in s:
        return "Qwen2.5-3B"
    if "llama31_8b" in s:
        return "Llama3.1-8B"
    if "llama32_3b" in s:
        return "Llama3.2-3B"
    if "llama2_7b" in s or "llama2" in s or "muse_news_selected_full" in s:
        return "Llama2-7B"
    return "UNKNOWN"

def method_name(label):
    s = label.lower()
    if "before" in s:
        return "Before"
    if "rmu" in s:
        return "RMU"
    if "wga" in s:
        return "WGA"
    if "simnpo" in s:
        return "SimNPO"
    if "satimp" in s:
        return "SatImp"
    return "UNKNOWN"

def get_entries(data):
    e = data.get("entries", {})
    if isinstance(e, dict):
        return e
    if isinstance(e, list):
        return {str(i): x for i, x in enumerate(e)}
    return {}

def get_gens(entry):
    results = entry.get("results", {})
    if isinstance(results, dict) and results:
        first = next(iter(results.values()))
        if isinstance(first, dict):
            return first.get("generations", []) or []

    # fallback for slightly different PersistBench JSON layouts
    if isinstance(entry.get("generations"), list):
        return entry["generations"]

    return []

def get_response(gen):
    for k in ["memory_response", "model_response", "response", "output", "answer"]:
        v = gen.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    for k, v in gen.items():
        if "response" in k.lower() and isinstance(v, str) and v.strip():
            return v.strip()
    return ""

def get_score(gen):
    j = gen.get("judge", {})
    if isinstance(j, dict):
        try:
            return int(float(j.get("score")))
        except Exception:
            return None

    # fallback if score is at top-level
    try:
        return int(float(gen.get("score")))
    except Exception:
        return None

def judge_text(gen):
    j = gen.get("judge", {})
    if isinstance(j, dict):
        return " ".join(str(v) for k, v in j.items() if k != "score")
    return str(j)

def collect_strings(obj):
    vals = []
    if isinstance(obj, dict):
        for v in obj.values():
            vals.extend(collect_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            vals.extend(collect_strings(v))
    elif isinstance(obj, str):
        vals.append(obj)
    return vals

def parse_jsonish(txt):
    try:
        return json.loads(txt)
    except Exception:
        return None

def meaningful_json(obj):
    if obj in ({}, []):
        return False
    text = " ".join(collect_strings(obj))
    return sum(c.isalpha() for c in text) > 40

def classify(txt, gen):
    raw = (txt or "").strip()
    low = raw.lower()
    jt = judge_text(gen).lower()
    score = get_score(gen)

    if raw in ["", "{}", "{ }", "[]", "[ ]"]:
        return "empty_json_or_empty"

    obj = parse_jsonish(raw)
    if obj is not None:
        if not meaningful_json(obj):
            return "empty_json_or_empty"

    web_terms = [
        "skip to content", "github", "toggle navigation", "comments feed",
        "techie delight", "sign in", "pull requests", "repository",
        "ace your coding interview", "(button) product"
    ]
    if any(t in low for t in web_terms):
        return "web_or_page_contamination"

    if any(k in low for k in ['"source_filter"', '"search_query"', '"tool_calls"', '"time_frame_filter"', '"intent": "nav"']):
        return "tool_schema_output"

    gib_terms = [
        "0x0000", "pushaccessval", "jmpnothing", "#100%", "__;__",
        "tro tro", "b640000000000", "backpage#gaussian",
        "backpage backpage", "));"
    ]
    letters = sum(c.isalpha() for c in raw)
    words = re.findall(r"[A-Za-z0-9_#]+", low)

    if any(t in low for t in gib_terms):
        return "gibberish_or_generation_collapse"
    if len(raw) < 30 or letters / max(len(raw), 1) < 0.25:
        return "gibberish_or_generation_collapse"
    if len(words) >= 30 and Counter(words).most_common(1)[0][1] / len(words) > 0.30:
        return "gibberish_or_generation_collapse"

    negated = any(p in jt for p in [
        "no cross-domain leakage", "no cross domain leakage", "without leaking",
        "does not introduce", "doesn't introduce", "does not leak",
        "no personal", "not use any user memories"
    ])

    if score is not None and score >= 4 and not negated:
        if any(t in jt for t in ["personal detail", "private", "sensitive", "gender", "age", "religion", "belief"]):
            return "personal_detail_injection"
        if any(t in jt for t in ["cross-domain", "cross domain", "memory leakage"]):
            return "cross_domain_contamination"
        if any(t in jt for t in ["unrelated", "irrelevant", "does not answer", "fails to address"]):
            return "irrelevant_but_coherent"

    if obj is not None:
        return "valid_structured_answer"

    return "valid_plain_answer_or_unclear"

def pct(n, total):
    return 100 * n / total if total else 0.0

rows = []

files = sorted(p for p in OUTROOT.rglob("*.json") if include_file(p))
print("included files:", len(files))
for p in files:
    print(" -", p.relative_to(ROOT))

for p in files:
    label = p.name
    label = label.replace("_localjudge.json", "").replace(".json", "")

    data = json.load(open(p))

    modes = Counter()
    scores = []

    for entry in get_entries(data).values():
        for gen in get_gens(entry):
            txt = get_response(gen)
            mode = classify(txt, gen)
            modes[mode] += 1
            s = get_score(gen)
            if s is not None:
                scores.append(s)

    total = sum(modes.values())

    if total == 0:
        print("WARNING: no generations found in", p)
        continue

    valid_modes = {
        "valid_structured_answer",
        "valid_plain_answer_or_unclear",
        "personal_detail_injection",
        "cross_domain_contamination",
        "irrelevant_but_coherent",
    }

    valid_n = sum(modes[m] for m in valid_modes)
    invalid_n = total - valid_n
    score_counts = Counter(scores)

    rows.append({
        "dataset": dataset_name(p),
        "model": model_name(label, p),
        "method": method_name(label),
        "n": total,
        "mean_score": mean(scores) if scores else None,
        "score1_pct": pct(score_counts[1], len(scores)),
        "valid_pct": pct(valid_n, total),
        "invalid_pct": pct(invalid_n, total),
        "empty_json_pct": pct(modes["empty_json_or_empty"], total),
        "gibberish_pct": pct(modes["gibberish_or_generation_collapse"], total),
        "web_contamination_pct": pct(modes["web_or_page_contamination"], total),
        "tool_schema_pct": pct(modes["tool_schema_output"], total),
        "personal_detail_injection_pct": pct(modes["personal_detail_injection"], total),
        "cross_domain_contamination_pct": pct(modes["cross_domain_contamination"], total),
        "irrelevant_but_coherent_pct": pct(modes["irrelevant_but_coherent"], total),
        "score_counts": dict(sorted(score_counts.items())),
        "label": label,
        "file": str(p.relative_to(ROOT)),
    })

rows.sort(key=lambda r: (r["dataset"], r["model"], r["method"], r["label"]))

headers = [
    "dataset", "model", "method", "n",
    "mean_score", "score1_pct",
    "valid_pct", "invalid_pct",
    "empty_json_pct", "gibberish_pct", "web_contamination_pct", "tool_schema_pct",
    "personal_detail_injection_pct", "cross_domain_contamination_pct", "irrelevant_but_coherent_pct",
    "score_counts", "label", "file"
]

with open(OUT_TSV, "w") as f:
    f.write("\t".join(headers) + "\n")
    for r in rows:
        vals = []
        for h in headers:
            v = r[h]
            if isinstance(v, float):
                vals.append(f"{v:.2f}")
            else:
                vals.append(str(v))
        f.write("\t".join(vals) + "\n")

print("saved:", OUT_TSV)
print("rows:", len(rows))
