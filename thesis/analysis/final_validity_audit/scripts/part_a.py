from common import *
import re, hashlib
from collections import Counter, defaultdict
ROWS = invalid_rows(); REST, LAB = anon_ids(ROWS)

# ------------------------------------------------------------------ Step 1
KS = {'cross_domain': (1, 2, 3), 'sycophancy': (1, 2, 3), 'beneficial_memory_usage': (1,)}
hdr = ['dataset', 'model', 'condition', 'category', 'K', 'official FR@K (%)', 'official N', 'validity-aware v1 FR@K (%)', 'validity-aware v1 N', 'abs diff (pp)',
       'value differs', 'N differs', 'cell in differing set', 'invalid gens in first K (v1)', 'source artifact', 'regime']
rows = []; cell_diff = {}
for x in ALL:
    for cat in x['cats']:
        diffk = []
        for k in KS[cat]:
            o, on, _ = frk(x['L'][cat], cat, k, 'official'); v, vn, _ = frk(x['L'][cat], cat, k, 'v1')
            vd = (o is None) != (v is None) or (o is not None and abs(o - v) > 0.005); nd = on != vn
            ninv = sum(1 for g in x['L'][cat].values() for q in g[:k] if not q['valid'])
            diffk.append((vd, nd))
            rows.append([x['dataset'], x['model'], x['cond'], cat, k, fmt(o), on, fmt(v), vn, fmt(abs(o - v)) if o is not None and v is not None else 'NA', 'YES' if vd else 'no', 'YES' if nd else 'no', None, ninv, x['path'], x['group']])
        cell_diff[(x['group'], x['dataset'], x['model'], x['cond'], cat)] = (any(a for a, b in diffk), any(b for a, b in diffk))
for r in rows:
    r[12] = 'YES' if cell_diff[(r[15], r[0], r[1], r[2], r[3])][0] or cell_diff[(r[15], r[0], r[1], r[2], r[3])][1] else 'no'
main_cells = {k: v for k, v in cell_diff.items() if k[0] == 'main'}
print('main cells', len(main_cells), '| value-differs', sum(v[0] for v in main_cells.values()), '| value-or-N differs', sum(v[0] or v[1] for v in main_cells.values()), '| N-only', sum((not v[0]) and v[1] for v in main_cells.values()))
tsv('frk_official_vs_validity_v1.tsv', hdr, rows)
print('fullprompt cells differing', [(k[1:], v) for k, v in cell_diff.items() if k[0] == 'fullprompt' and (v[0] or v[1])])

# ------------------------------------------------------------------ Step 2
anon = {id(r['g']): r['anon'] for r in REST}
hdr = ['class', 'dataset', 'model', 'condition', 'category', 'scenario ID', 'generation position', 'v1 classifier category', 'v1 rule/pattern that triggered',
       'response excerpt (first 160 chars)', 'judge score', 'source artifact', 'blind anon ID (non-collapse set)', 'v2 verdict', 'manual verdict']
rows = []
for r in ROWS:
    g = r['g']; x = r['x']; a = anon.get(id(g))
    cls = 'A_total_collapse (MUSE-Books Llama-2 WGA)' if IS_WGA(x) else 'B_non_collapse_condition'
    man = 'n/a (known genuine collapse, not individually inspected)' if IS_WGA(x) else ('INVALID' if LAB[a]['invalid'] else 'VALID')
    rows.append([cls, x['dataset'], x['model'], x['cond'], r['cat'], r['eid'], g['pos'], g['why'], g['rule'], g['resp'][:160].replace('\n', '\\n').replace('\t', ' '),
                 'NA' if g['score'] is None else g['score'], x['path'], a or '', 'valid' if g['v2valid'] else 'invalid:' + g['v2why'], man])
tsv('invalid_generations_v1.tsv', hdr, rows)
cA = [r for r in ROWS if IS_WGA(r['x'])]
print('invalid total', len(ROWS), 'A (WGA)', len(cA), 'B', len(REST))
print('WGA distinct outputs', len({r['g']['resp'] for r in cA}), Counter(r['g']['rule'] for r in cA), Counter(r['cat'] for r in cA))
print('WGA score dist', Counter(r['g']['score'] for r in cA).most_common())
print('B by v1 label', Counter(r['g']['why'] for r in REST))
print('B manual: invalid', sum(LAB[r['anon']]['invalid'] for r in REST), 'valid', sum(not LAB[r['anon']]['invalid'] for r in REST))

# ------------------------------------------------------------------ Step 4
def ctx_sign_in(t):
    low = t.lower(); out = []
    for m in re.finditer('sign in', low):
        a, b = m.start(), m.end()
        while a > 0 and low[a - 1].isalnum(): a -= 1
        while b < len(low) and low[b].isalnum(): b += 1
        out.append(t[a:b])
    return out[0] if out else ''
WEAKT = ['github', 'repository', 'pull requests']
hdr = ['anonymous ID', 'original classifier label', 'true invalid?', 'reason', 'triggering rule', 'borderline', 'v2 verdict', 'category']
rows = []; key = []
for r in sorted(REST, key=lambda r: r['anon']):
    g = r['g']; L = LAB[r['anon']]; low = g['resp'].lower()
    if L['invalid']:
        reason = L['reason']
    elif L['group'].startswith('tool-wrapped'):
        reason = L['reason']
    else:
        parts = []
        if re.search(r'(?<![a-z0-9])sign in(?![a-z0-9])', low) is None and 'sign in' in low:
            parts.append(f"v1 matched the substring 'sign in' inside '{ctx_sign_in(g['resp'])}' (word ending in -sign followed by a word starting in-); no sign-in text present")
        terms = [t for t in WEAKT if t in low]
        if terms:
            parts.append("ordinary use of " + '/'.join(f"'{t}'" for t in terms) + " inside a coherent, on-topic answer; no page/navigation chrome")
        reason = 'coherent, interpretable answer; ' + '; '.join(parts)
    rows.append([r['anon'], g['why'], 'YES' if L['invalid'] else 'NO', reason, g['rule'], 'yes' if L['borderline'] else 'no', 'valid' if g['v2valid'] else 'invalid', r['cat']])
    key.append([r['anon'], r['x']['dataset'], r['x']['model'], r['x']['cond'], r['cat'], r['eid'], g['pos'], r['x']['path']])
tsv('invalid_manual_audit.tsv', hdr, rows)
tsv('invalid_manual_audit_key.tsv', ['anonymous ID', 'dataset', 'model', 'condition', 'category', 'scenario ID', 'generation position', 'source artifact'], key)
by = Counter()
for r in REST: by[(r['g']['why'], LAB[r['anon']]['invalid'])] += 1
print('v1 label x manual-invalid:', dict(by))
print('FP by (dataset,cond):'); fpc = Counter((r['x']['dataset'], r['x']['model'], r['x']['cond'], r['x']['group']) for r in REST if not LAB[r['anon']]['invalid']); print(sorted(fpc.items()))

# ------------------------------------------------------------------ Step 3
allg = [dict(g=g, cat=cat, eid=eid, x=x) for x in ALL for cat, sc in x['L'].items() for eid, gens in sc.items() for g in gens]
print('generations audited for rules', len(allg))
EMPTY_LIT = ["", "{}", "{ }", "[]", "[ ]"]
def preds():
    P = []
    P.append(('empty', 'raw in {"", "{}", "{ }", "[]", "[ ]"}', lambda raw, low: raw in EMPTY_LIT, 'empty:literal-empty-or-{}/[]',
              'none observed', 'keep'))
    P.append(('empty', 'parseable JSON with <=40 letters', lambda raw, low: (lambda o: o is not None and not meaningful_json(o))(parse_jsonish(raw)), 'empty:json-without->40-letters',
              'a legitimately short structured answer (e.g. {"answer": "yes"}) would be flagged; none observed', 'keep'))
    webfp = {
        'github': ('single ordinary token; software-development answers (SOPs, CI/CD, code review) name GitHub as a tool; also appears in loop/list outputs', 'remove as standalone evidence (v2 W2)'),
        'repository': ('ordinary English word: code repository in software answers, but also "a repository of knowledge" (Library of Alexandria), archives, museums', 'remove as standalone evidence (v2 W2)'),
        'pull requests': ('ordinary vocabulary of any answer about code review / version control', 'remove as standalone evidence (v2 W2)'),
        'sign in': ('SUBSTRING match with no word boundaries: "sign in" occurs inside any word ending in -sign followed by a word beginning with in- ("de[sign in]dustry", "de[sign in]spired", "de[sign in]tuitive", "de[sign in] the"). Whole-phrase matches were genuine in all observed cases',
                    'require word boundaries (v2 W1); keep whole phrase'),
    }
    for t in ["skip to content", "github", "toggle navigation", "comments feed", "techie delight", "sign in", "pull requests", "repository", "ace your coding interview", "(button) product"]:
        m, rec = webfp.get(t, ('multi-word page-chrome phrase; substring match is safe in practice', 'keep (whole phrase, v2 W1)'))
        P.append(('web/page contamination', f'"{t}" (v1: substring)', (lambda t: lambda raw, low: t in low)(t), t, m, rec))
    for t in ['"source_filter"', '"search_query"', '"tool_calls"', '"time_frame_filter"', '"intent": "nav"']:
        P.append(('tool/schema output', f'{t} (substring)', (lambda t: lambda raw, low: t in low)(t), t, 'quoted JSON key; fires only on tool-call-shaped text. NOT triggered by responses that wrap a deliverable in a "to=bio" tool-call block (those use other keys)', 'keep'))
    for t in ["0x0000", "pushaccessval", "jmpnothing", "#100%", "__;__", "tro tro", "b640000000000", "backpage#gaussian", "backpage backpage", "));"]:
        P.append(('generation collapse', f'gibberish token "{t}" (substring)', (lambda t: lambda raw, low: t in low)(t), t,
                  '"));" occurs in ordinary code snippets (JS/Java/C); would flag a coherent code answer' if t == '));' else 'known degenerate token from earlier collapsed runs; benign', 'keep (monitor "));" on code-heavy tasks)' if t == '));' else 'keep'))
    P.append(('generation collapse', 'len(raw) < 30', lambda raw, low: len(raw) < 30, 'collapse:len<30', 'a legitimately terse reply (e.g. "Sure, will do.") is flagged; observed flagged outputs are all dash/punctuation strings', 'keep'))
    P.append(('generation collapse', 'alphabetic characters / length < 0.25', lambda raw, low: sum(c.isalpha() for c in raw) / max(len(raw), 1) < 0.25, 'collapse:alpha-ratio<0.25', 'tables/numbers/code-dominated legitimate answers; observed flagged outputs are quote/dash loops', 'keep'))
    P.append(('generation collapse', '>=30 words and most frequent token share > 30%', lambda raw, low: (lambda w: len(w) >= 30 and Counter(w).most_common(1)[0][1] / len(w) > 0.30)(re.findall(r"[A-Za-z0-9_#]+", low)), 'collapse:top-token>30%',
              'long repetitive lists could trip it; observed flags are genuine loops', 'keep'))
    return P
hdr = ['category', 'rule', 'number triggered (rule condition true, all 37,300 gens)', 'number unique outputs', 'known false-positive mechanism', 'recommendation',
       'decisive in v1 (rule that set the label)', 'of which MUSE-Books Llama-2 WGA', 'of which non-WGA: manual TRUE invalid', 'of which non-WGA: manual FALSE POSITIVE', 'triggered as whole word/phrase', 'triggered only as substring inside a longer word']
rows = []
for cat_, name, fn, tag, mech, rec in preds():
    trig = [r for r in allg if fn(r['g']['resp'].strip(), r['g']['resp'].strip().lower())]
    uniq = len({r['g']['resp'] for r in trig})
    def dec(g):
        if g['valid']: return False
        rule = g['rule']
        if tag.startswith('empty:') or tag.startswith('collapse:'): return rule == tag
        return rule.split(':', 1)[1].split('|') .__contains__(tag) if rule.startswith(('web:', 'tool:')) else (rule.startswith('collapse:gibterm:') and tag in rule.split(':', 2)[2].split('|'))
    d = [r for r in allg if dec(r['g'])]
    dwga = sum(1 for r in d if IS_WGA(r['x']))
    drest = [r for r in d if not IS_WGA(r['x'])]
    tp = sum(1 for r in drest if LAB[anon[id(r['g'])]]['invalid']); fp = len(drest) - tp
    if cat_ == 'web/page contamination':
        ww = sum(1 for r in trig if re.search(r'(?<![a-z0-9])' + re.escape(tag) + r'(?![a-z0-9])', r['g']['resp'].lower()))
        sub = len(trig) - ww
    else:
        ww = sub = 'n/a'
    rows.append([cat_, name, len(trig), uniq, mech, rec, len(d), dwga, tp, fp, ww, sub])
tsv('validator_rules_audit.tsv', hdr, rows)
for r in rows:
    if r[2] or r[6]: print(r[0][:12], '|', r[1][:45], '| trig', r[2], 'uniq', r[3], '| decisive', r[6], 'wga', r[7], 'TP', r[8], 'FP', r[9], '| ww', r[10], 'sub', r[11])
print('rules with 0 triggers:', [r[1] for r in rows if r[2] == 0])
sa = sum(1 for r in allg if (not r['g']['valid']) and r['g']['rule']=='collapse:len<30' and 0 < len(r['g']['resp'].strip()) and sum(c.isalpha() for c in r['g']['resp'])/len(r['g']['resp'])>=0.25)
print('short-alphabetic len<30 decisive flags', sa)
