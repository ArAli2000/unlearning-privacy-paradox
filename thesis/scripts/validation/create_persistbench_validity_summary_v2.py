"""Generation-validity classifier v2 for PersistBench outputs (text-only, category/model/outcome independent).

v2 differs from create_persistbench_validity_summary_with_muse.py::classify (v1) ONLY in the web/page-contamination rule.
Every other rule (empty, tool/schema, collapse) is reproduced verbatim. See thesis/analysis/final_validity_audit/REPORT.md.

Changes vs v1 (each justified by the blind manual audit, thesis/analysis/final_validity_audit/invalid_manual_audit.tsv):
  W1  Phrase matching is word-bounded. v1 used `term in text`, so "sign in" matched inside "de[sign in]dustry", "de[sign in]tuitive",
      "de[sign in] the ..." -> 64 of 97 stored web flags were of this kind.
  W2  "github", "repository", "pull requests" are no longer evidence by themselves. They are ordinary vocabulary of software answers
      (and of non-software ones: "a repository of knowledge"). Genuine GitHub/page scrapes still trip the navigation-chrome phrases below.
Unchanged: empty rule, tool/schema rule, all collapse rules. The original script is not modified.

Optional (OFF by default, used only as a pre-specified sensitivity "v2r"): repetition-loop rule R1 (`repetition_rule=True`).

Usage as a library:  label, rule = classify_v2(text);  valid = label.startswith('valid')
CLI (no models, reads existing JSON only):  python3 create_persistbench_validity_summary_v2.py OUT.tsv FILE.json [FILE.json ...]
"""
import json
import re
import sys
from collections import Counter

# --- web/page contamination --------------------------------------------------------------------------------------------
# Navigation / page-chrome boilerplate. Matched as whole phrases (W1). "github", "repository", "pull requests" removed (W2).
WEB_CHROME = ["skip to content", "toggle navigation", "comments feed", "techie delight", "ace your coding interview", "(button) product"]
# UI verb phrase; kept from v1 but only as a whole phrase (W1).
WEB_UI = ["sign in"]
WEB_TERMS_V2 = WEB_CHROME + WEB_UI

TOOL_TERMS = ['"source_filter"', '"search_query"', '"tool_calls"', '"time_frame_filter"', '"intent": "nav"']
GIB_TERMS = ["0x0000", "pushaccessval", "jmpnothing", "#100%", "__;__", "tro tro", "b640000000000", "backpage#gaussian", "backpage backpage", "));"]


def _phrase_re(p):
    return re.compile(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])")


_WEB_RE = [(p, _phrase_re(p)) for p in WEB_TERMS_V2]


def _collect_strings(obj):
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in _collect_strings(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in _collect_strings(v)]
    return [obj] if isinstance(obj, str) else []


def _parse(txt):
    try:
        return json.loads(txt)
    except Exception:
        return None


def _meaningful_json(obj):
    if obj in ({}, []):
        return False
    return sum(c.isalpha() for c in " ".join(_collect_strings(obj))) > 40


def _rep3(raw):
    """(#words, share of word-trigrams that repeat an earlier trigram)"""
    w = re.findall(r"\w+", raw.lower())
    tri = [tuple(w[i:i + 3]) for i in range(len(w) - 2)]
    if not tri:
        return len(w), 0.0
    return len(w), sum(v - 1 for v in Counter(tri).values()) / len(tri)


def classify_v2(txt, gen=None, repetition_rule=False):
    """-> (label, rule). label in {empty_json_or_empty, web_or_page_contamination, tool_schema_output,
    gibberish_or_generation_collapse, valid}. `gen` is accepted for call-compatibility with v1 and ignored (no judge info is used)."""
    raw = (txt or "").strip()
    low = raw.lower()
    if raw in ["", "{}", "{ }", "[]", "[ ]"]:
        return "empty_json_or_empty", "empty:literal-empty-or-{}/[]"
    obj = _parse(raw)
    if obj is not None and not _meaningful_json(obj):
        return "empty_json_or_empty", "empty:json-without->40-letters"

    hit = [p for p, rx in _WEB_RE if rx.search(low)]
    if hit:
        return "web_or_page_contamination", "web:" + "|".join(hit)

    th = [t for t in TOOL_TERMS if t in low]
    if th:
        return "tool_schema_output", "tool:" + "|".join(th)

    letters = sum(c.isalpha() for c in raw)
    words = re.findall(r"[A-Za-z0-9_#]+", low)
    gh = [t for t in GIB_TERMS if t in low]
    if gh:
        return "gibberish_or_generation_collapse", "collapse:gibterm:" + "|".join(gh)
    if len(raw) < 30:
        return "gibberish_or_generation_collapse", "collapse:len<30"
    if letters / max(len(raw), 1) < 0.25:
        return "gibberish_or_generation_collapse", "collapse:alpha-ratio<0.25"
    if len(words) >= 30 and Counter(words).most_common(1)[0][1] / len(words) > 0.30:
        return "gibberish_or_generation_collapse", "collapse:top-token>30%"

    if repetition_rule:  # R1 (optional sensitivity only): >=50% of word-trigrams are repeats in a >=20-word response
        n, r = _rep3(raw)
        if n >= 20 and r >= 0.5:
            return "gibberish_or_generation_collapse", "collapse:repeated-trigram>=50%"

    return "valid", ""


def _gens(entry):
    res = entry.get("results", {})
    if isinstance(res, dict) and res:
        first = next(iter(res.values()))
        if isinstance(first, dict):
            return first.get("generations", []) or []
    return entry.get("generations", []) if isinstance(entry.get("generations"), list) else []


def _response(g):
    for k in ["memory_response", "model_response", "response", "output", "answer"]:
        v = g.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    for k, v in g.items():
        if "response" in k.lower() and isinstance(v, str) and v.strip():
            return v.strip()
    return ""


if __name__ == "__main__":
    out, files = sys.argv[1], sys.argv[2:]
    with open(out, "w") as f:
        f.write("file\tn\tvalid\tinvalid\tempty\tweb\ttool\tcollapse\n")
        for p in files:
            d = json.load(open(p))
            e = d.get("entries", {})
            e = e.values() if isinstance(e, dict) else e
            c = Counter(classify_v2(_response(g), g)[0] for en in e for g in _gens(en))
            n = sum(c.values())
            f.write(f"{p}\t{n}\t{c['valid']}\t{n - c['valid']}\t{c['empty_json_or_empty']}\t{c['web_or_page_contamination']}\t{c['tool_schema_output']}\t{c['gibberish_or_generation_collapse']}\n")
    print("written", out)
