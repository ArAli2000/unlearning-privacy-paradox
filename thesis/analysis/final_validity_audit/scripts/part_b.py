from common import *
from math import comb
from collections import Counter, defaultdict
KS = {'cross_domain': (1, 2, 3), 'sycophancy': (1, 2, 3), 'beneficial_memory_usage': (1,)}
INV = {'cross_domain': False, 'sycophancy': False, 'beneficial_memory_usage': True}

# ------------------------------------------------------------------ Step 6: validity v2
hdr = ['regime', 'dataset', 'model', 'condition', 'category', 'total generations', 'valid v1', 'validity v1 %', 'valid v2', 'validity v2 %', 'invalid v2: empty', 'invalid v2: collapse',
       'invalid v2: web', 'invalid v2: tool/schema', 'zero-valid scenarios v1', 'zero-valid scenarios v2', 'valid v2r (sensitivity)', 'validity v2r %', 'zero-valid scenarios v2r', 'source artifact']
rows = []; VAL = {}
for x in ALL:
    for cat in x['cats']:
        sc = x['L'][cat]; g = [q for gens in sc.values() for q in gens]; n = len(g)
        v1 = sum(q['valid'] for q in g); v2 = sum(q['v2valid'] for q in g); v2r = sum(q['v2rvalid'] for q in g)
        c = Counter(q['v2why'] for q in g if not q['v2valid'])
        z1 = sum(1 for gens in sc.values() if not any(q['valid'] for q in gens)); z2 = sum(1 for gens in sc.values() if not any(q['v2valid'] for q in gens)); zr = sum(1 for gens in sc.values() if not any(q['v2rvalid'] for q in gens))
        VAL[(x['group'], x['dataset'], x['model'], x['cond'], cat)] = dict(n=n, v1=v1, v2=v2, v2r=v2r, z1=z1, z2=z2, zr=zr)
        rows.append([x['group'], x['dataset'], x['model'], x['cond'], cat, n, v1, fmt(100 * v1 / n), v2, fmt(100 * v2 / n), c['empty_json_or_empty'], c['gibberish_or_generation_collapse'], c['web_or_page_contamination'],
                     c['tool_schema_output'], z1, z2, v2r, fmt(100 * v2r / n), zr, x['path']])
tsv('validity_v2.tsv', hdr, rows)
for grp in ('main', 'fullprompt', 'scan_extra'):
    t = [v for k, v in VAL.items() if k[0] == grp]
    print(grp, 'gens', sum(v['n'] for v in t), 'invalid v1', sum(v['n'] - v['v1'] for v in t), 'invalid v2', sum(v['n'] - v['v2'] for v in t), 'invalid v2r', sum(v['n'] - v['v2r'] for v in t),
          '| zero-valid v1/v2/v2r', sum(v['z1'] for v in t), sum(v['z2'] for v in t), sum(v['zr'] for v in t))
m = [v for k, v in VAL.items() if k[0] == 'main' and k[1:4] != ('MUSE-Books', 'Llama-2-7B', 'WGA')]
print('main excl. WGA: gens', sum(v['n'] for v in m), 'invalid v1', sum(v['n'] - v['v1'] for v in m), 'invalid v2', sum(v['n'] - v['v2'] for v in m), 'invalid v2r', sum(v['n'] - v['v2r'] for v in m))

# ------------------------------------------------------------------ Step 7: FR@K v2
hdr = ['regime', 'dataset', 'model', 'condition', 'category', 'K', 'FR@K v2 (%)', 'N_K v2', 'failures v2', 'scenarios total', 'scenarios excluded (no valid output in first K)', 'FR@K v2r (%) [sensitivity]', 'N_K v2r']
rows = []; FR = {}
for x in ALL:
    for cat in x['cats']:
        sc = x['L'][cat]
        for k in KS[cat]:
            r = {md: frk(sc, cat, k, md) for md in ('official', 'v1', 'v2', 'v2r')}
            FR[(x['group'], x['dataset'], x['model'], x['cond'], cat, k)] = r
            rows.append([x['group'], x['dataset'], x['model'], x['cond'], cat, k, fmt(r['v2'][0]), r['v2'][1], r['v2'][2], len(sc), len(sc) - r['v2'][1], fmt(r['v2r'][0]), r['v2r'][1]])
tsv('frk_validity_v2.tsv', hdr, rows)

# ------------------------------------------------------------------ Step 8: three-way comparison (+ paired exact sign tests vs Target)
def status(gens, cat, k, md):
    th, inv = TH[cat]; key = {'official': None, 'v1': 'valid', 'v2': 'v2valid', 'v2r': 'v2rvalid'}[md]
    vs = [q['score'] for q in gens[:k] if q['score'] is not None and (key is None or q[key])]
    if not vs: return None
    return (max(vs) >= th) != inv   # True = failure

def sign_p(a, b):
    n = a + b
    if n == 0: return 1.0
    mm = min(a, b); return min(1.0, 2 * sum(comb(n, i) for i in range(mm + 1)) / 2 ** n)

def paired(xc, xt, cat, k, md):
    sa = Counter()
    for eid, gens in xc['L'][cat].items():
        a = status(xt['L'][cat][eid], cat, k, md); b = status(gens, cat, k, md)
        if a is None or b is None: continue
        sa[(a, b)] += 1
    sf, fs = sa[(False, True)], sa[(True, False)]
    return sf, fs, sign_p(sf, fs), sum(sa.values())

TOL = 0.5  # pp; same stability band the thesis uses elsewhere (+-0.5 pp). |delta| < TOL is 'stable'
def direction(d, tol=TOL):
    if d is None: return 'NA'
    return 'worse' if d > tol else ('better' if d < -tol else 'stable')

def sig(p): return 'NA' if p is None else ('p<.05' if p < 0.05 else 'n.s.')

hdr = ['regime', 'dataset', 'model', 'condition', 'category', 'K', 'official FR', 'official N', 'v1 FR', 'v1 N', 'v2 FR', 'v2 N', 'v2r FR [sens]', 'v2r N',
       'abs diff v1-official (pp)', 'abs diff v2-official (pp)', 'abs diff v2-v1 (pp)',
       'delta vs Target official (pp)', 'delta vs Target v1 (pp)', 'delta vs Target v2 (pp)', 'delta vs Target v2r (pp)',
       'direction official (tol 0.5pp)', 'direction v1', 'direction v2', 'direction v2r', 'direction changes across official/v1/v2', 'raw sign (tol 0) differs across official/v1/v2',
       'paired S->F / F->S vs Target (v2)', 'paired exact sign p official', 'paired p v1', 'paired p v2', 'paired p v2r', 'significance changes across official/v1/v2', 'qualitative change?']
rows = []; CMP = {}
byg = {(x['group'], x['dataset'], x['model'], x['cond']): x for x in ALL}
for x in ALL:
    for cat in x['cats']:
        for k in KS[cat]:
            key = (x['group'], x['dataset'], x['model'], x['cond'], cat, k); r = FR[key]
            tkey = (x['group'], x['dataset'], x['model'], 'Target', cat, k); rt = FR[tkey]
            isT = x['cond'] == 'Target'
            def d(md): return None if isT or r[md][0] is None or rt[md][0] is None else r[md][0] - rt[md][0]
            ds = {md: d(md) for md in ('official', 'v1', 'v2', 'v2r')}
            dirs = {md: ('ref' if isT else direction(ds[md])) for md in ds}
            diffs = lambda a, b: None if r[a][0] is None or r[b][0] is None else abs(r[a][0] - r[b][0])
            ps = {}; sf = fs = ''
            if not isT:
                xt = byg[(x['group'], x['dataset'], x['model'], 'Target')]
                for md in ('official', 'v1', 'v2', 'v2r'):
                    a, b, p, nn = paired(x, xt, cat, k, md); ps[md] = p if nn else None
                    if md == 'v2': sf, fs = a, b
            dch = (not isT) and len({dirs['official'], dirs['v1'], dirs['v2']}) > 1
            rawsg = (not isT) and len({direction(ds[m_], 0.005) for m_ in ('official', 'v1', 'v2')}) > 1
            wga = (x['dataset'], x['model'], x['cond']) == ('MUSE-Books', 'Llama-2-7B', 'WGA')
            sch = (not isT) and len({sig(ps.get('official')), sig(ps.get('v1')), sig(ps.get('v2'))}) > 1
            edge = dch and all(abs(v_) <= 0.75 for v_ in ds.values() if v_ is not None) and all((p_ is None or p_ >= 0.05) for p_ in ps.values())
            qual = 'YES (WGA: official scores collapsed output; v1/v2 non-evaluable)' if wga else ('YES' if (sch or (dch and not edge)) else ('edge (|delta| ~ 0.5pp tolerance; n.s. in all variants)' if dch else 'no'))
            CMP[key] = dict(r=r, ds=ds, dirs=dirs, ps=ps, dch=dch and not wga, sch=sch and not wga, wga=wga, rawsg=rawsg)
            rows.append([x['group'], x['dataset'], x['model'], x['cond'], cat, k, fmt(r['official'][0]), r['official'][1], fmt(r['v1'][0]), r['v1'][1], fmt(r['v2'][0]), r['v2'][1], fmt(r['v2r'][0]), r['v2r'][1],
                         fmt(diffs('v1', 'official')), fmt(diffs('v2', 'official')), fmt(diffs('v2', 'v1')),
                         fmt(ds['official']) if not isT else 'ref', fmt(ds['v1']) if not isT else 'ref', fmt(ds['v2']) if not isT else 'ref', fmt(ds['v2r']) if not isT else 'ref',
                         dirs['official'], dirs['v1'], dirs['v2'], dirs['v2r'], 'YES' if dch else 'no', 'YES' if rawsg else 'no',
                         f'{sf}/{fs}' if not isT else '', *(fmt(ps.get(m_), 4) if not isT else '' for m_ in ('official', 'v1', 'v2', 'v2r')), 'YES' if sch else 'no', qual])
tsv('frk_three_way_comparison.tsv', hdr, rows)
ch = [(k, v) for k, v in CMP.items() if v['dch'] or v['sch']]
print('raw-sign differences (tol 0), excl WGA:', sum(v['rawsg'] and not v['wga'] for v in CMP.values()))
print('rows', len(rows), '| direction changes', sum(v['dch'] for v in CMP.values()), '| significance changes', sum(v['sch'] for v in CMP.values()))
for k, v in ch: print('  CHANGE', k[1:], '| dirs', v['dirs']['official'], v['dirs']['v1'], v['dirs']['v2'], '| d', *(fmt(v['ds'][m_]) for m_ in ('official', 'v1', 'v2')), '| p', *(fmt(v['ps'].get(m_), 3) for m_ in ('official', 'v1', 'v2')))
import pickle; pickle.dump(dict(CMP=CMP, FR=FR, VAL=VAL), open(str(Path(__file__).parent/'_partb.pkl'), 'wb'))
