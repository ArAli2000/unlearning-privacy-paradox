import json
from common import *
from collections import Counter
TR = [('MUSE-News', 'Qwen2.5-7B-Instruct', 'muse_news', 'muse_news_qwen25_{k}'), ('MUSE-Books', 'Qwen2.5-7B-Instruct', 'muse_books', 'muse_books_qwen25_{k}'), ('MUSE-Books', 'Llama-2-7B', 'muse_books', 'muse_books_llama2_{k}')]
KS = {'cross_domain': (1, 2, 3), 'sycophancy': (1, 2, 3), 'beneficial_memory_usage': (1,)}
byk = {(x['dataset'], x['model'], x['cond']): x for x in MAIN}
def gem(dirn, stem, k):
    d = json.load(open(R / f'external/PersistBench/outputs_gemma3_judge/{dirn}/{stem.format(k=k)}.gemma3.json')); out = {}
    for eid, e in get_entries(d).items():
        out[eid] = [None if (g.get('error') or g.get('judge') is None) else g['judge'].get('score') for g in get_gens(e)]
    return out
stored = json.load(open(R / 'thesis/analysis/judge_robustness/qwen_vs_gemma_frk.json'))
tm = {'muse_news': 'muse_news', 'muse_books_llama2': 'muse_books_llama2', 'muse_books_qwen25': 'muse_books_qwen25'}
def scen_with(x, cat, scores):
    out = {}
    for eid, gens in x['L'][cat].items():
        sc = scores.get(eid)
        assert sc is not None and len(sc) == len(gens), (eid,)
        out[eid] = [dict(q, score=s) for q, s in zip(gens, sc)]
    return out
rows = []; FRJ = {}
for ds, model, dirn, stem in TR:
    for judge in ('qwen', 'gemma'):
        for cond, k in METHODS:
            x = byk[(ds, model, cond)]
            for cat in CATS:
                sc = x['L'][cat] if judge == 'qwen' else scen_with(x, cat, gem(dirn, stem, k))
                for K in KS[cat]:
                    o = frk(sc, cat, K, 'official'); v = frk(sc, cat, K, 'v2'); FRJ[(ds, model, judge, cond, cat, K)] = (o, v)
for (ds, model, judge, cond, cat, K), (o, v) in FRJ.items():
    t = FRJ[(ds, model, judge, 'Target', cat, K)]
    d_o = None if cond == 'Target' or o[0] is None or t[0][0] is None else o[0] - t[0][0]
    d_v = None if cond == 'Target' or v[0] is None or t[1][0] is None else v[0] - t[1][0]
    rows.append([ds, model, judge, cond, cat, K, fmt(o[0]), o[1], fmt(v[0]), v[1], 'ref' if cond == 'Target' else fmt(d_o), 'ref' if cond == 'Target' else fmt(d_v)])
tsv('judge_robustness_v2.tsv', ['dataset', 'model', 'judge', 'condition', 'category', 'K', 'official FR (%)', 'official N', 'validity v2 FR (%)', 'v2 N', 'delta vs Target official (pp)', 'delta vs Target v2 (pp)'], rows)
# check against stored official judge-robustness table
mism = 0; chk = 0
for tkey, td in stored.items():
    ds_, model_ = {'muse_news': ('MUSE-News', 'Qwen2.5-7B-Instruct'), 'muse_books_llama2': ('MUSE-Books', 'Llama-2-7B'), 'muse_books_qwen25': ('MUSE-Books', 'Qwen2.5-7B-Instruct')}[tkey]
    for meth, v in td['methods'].items():
        cond = 'Target' if meth == 'BASE' else meth
        for judge in ('qwen', 'gemma'):
            for cat, vals in v[judge].items():
                for K in KS[cat]:
                    a = vals.get(f'FR@{K}'); b = FRJ[(ds_, model_, judge, cond, cat, K)][0][0]; chk += 1
                    if a is None or b is None or abs(a - b) > 0.011: mism += 1
print('stored judge-robustness official values reproduced:', chk - mism, '/', chk)
# does the Qwen-vs-Gemma gap in the Target->Unlearned story change?
big = [(r[0], r[1], r[2], r[3], r[4], r[5], r[10], r[11]) for r in rows if r[3] != 'Target' and r[10] not in ('ref', 'NA') and r[11] not in ('NA',) and abs(float(r[10]) - float(r[11])) >= 0.5]
print('judge rows with |delta official - delta v2| >= 0.5pp:', len(big)); [print('  ', b) for b in big[:12]]
flip = [(r[0], r[1], r[2], r[3], r[4], r[5], r[10], r[11]) for r in rows if r[3] != 'Target' and r[10] not in ('ref', 'NA') and r[11] != 'NA' and (float(r[10]) > 0.5) != (float(r[11]) > 0.5) or False]
# ---------------- scenario-level judge agreement (MUSE-News sycophancy, 5 conds) under v1 / v2
def kappa(pairs):
    vals = sorted({v for p in pairs for v in p}); n = len(pairs); ix = {v: i for i, v in enumerate(vals)}
    m = [[0] * len(vals) for _ in vals]
    for a, b in pairs: m[ix[a]][ix[b]] += 1
    po = sum(m[i][i] for i in range(len(vals))) / n; rm = [sum(r) for r in m]; cm = [sum(m[i][j] for i in range(len(vals))) for j in range(len(vals))]
    pe = sum(rm[i] * cm[i] for i in range(len(vals))) / n / n
    return (po - pe) / (1 - pe), po
res = {}
for md in ('official', 'v1', 'v2'):
    pairs = []
    for cond, k in METHODS:
        x = byk[('MUSE-News', 'Qwen2.5-7B-Instruct', cond)]; g = gem('muse_news', 'muse_news_qwen25_{k}', k)
        for eid, gens in x['L']['sycophancy'].items():
            key = None if md == 'official' else {'v1': 'valid', 'v2': 'v2valid'}[md]
            qa = [q['score'] for q, s in zip(gens[:3], g[eid][:3]) if q['score'] is not None and (key is None or q[key])]
            gb = [s for q, s in zip(gens[:3], g[eid][:3]) if s is not None and (key is None or q[key])]
            if qa and gb: pairs.append((int(max(qa) >= 3), int(max(gb) >= 3)))
    kk, po = kappa(pairs); res[md] = (100 * po, kk, len(pairs))
print('scenario-level FR@3 status agreement, MUSE-News sycophancy:', {m: (round(a, 2), round(b, 4), n) for m, (a, b, n) in res.items()})
json.dump(res, open(str(Path(__file__).parent/'_agree.json'), 'w'))
