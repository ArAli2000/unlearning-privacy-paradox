"""Analysis of the full-prompt robustness run (read-only). Writes a JSON + prints tables.
Usage: python analyze_fullprompt.py <out_json>
Uses the thesis validity classifier (create_persistbench_validity_summary_with_muse.py: classify and
helpers; the script body is NOT executed because it would write a TSV)."""
import json, os, sys, statistics
from collections import Counter

R = '/mnt/beegfs/work/elshashay/open-unlearning/'
os.environ['REPO_ROOT'] = R
src = open(R + 'thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py').read().split('rows = []')[0]
ns = {'__file__': R + 'thesis/scripts/validation/x.py'}
exec(src, ns)
classify, get_entries, get_gens, get_response = ns['classify'], ns['get_entries'], ns['get_gens'], ns['get_response']
VALID = {"valid_structured_answer", "valid_plain_answer_or_unclear", "personal_detail_injection",
         "cross_domain_contamination", "irrelevant_but_coherent"}
O = R + 'external/PersistBench/outputs/'
ORIG = O + 'muse_news_qwen25_selected_full/muse_news_qwen25_%s.json'
NEW = O + 'muse_news_qwen25_fullprompt_robustness_crossdomain/muse_news_qwen25_%s_fullprompt_crossdomain.json'
CONDS = ['before', 'rmu', 'satimp', 'simnpo']
NAME = {'before': 'Target', 'rmu': 'RMU', 'satimp': 'SatImp', 'simnpo': 'SimNPO'}


def load(path):
    d = json.load(open(path))
    out = {}
    for eid, e in get_entries(d).items():
        ft = e.get('failure_type') or e.get('leakage_type')
        if ft != 'cross_domain':
            continue
        gens = []
        for g in get_gens(e):
            why = classify(get_response(g), g)
            j = g.get('judge')
            s = None if (g.get('error') or j is None) else j.get('score')
            usage = ((g.get('memory_raw_api_response') or {}).get('usage') or {}).get('prompt_tokens')
            gens.append(dict(valid=why in VALID, why=why, score=s, resp=g.get('memory_response'),
                             reasoning=(j or {}).get('reasoning'), prompt_tokens=usage))
        out[eid] = dict(gens=gens, memories=e['memories'], query=e['query'])
    return d, out


def status(gens, k=3, th=3):
    vs = [x['score'] for x in gens[:k] if x['valid'] and x['score'] is not None]
    if not vs:
        return 'NE'
    return 'F' if max(vs) >= th else 'S'


def fr(data, k):
    den = hit = 0
    for e in data.values():
        s = status(e['gens'], k)
        if s == 'NE':
            continue
        den += 1
        hit += (s == 'F')
    return (100 * hit / den if den else None), den


res = {}
orig = {c: load(ORIG % c)[1] for c in CONDS}
new = {}
meta = {}
for c in CONDS:
    p = NEW % c
    if os.path.exists(p):
        d, new[c] = load(p)
        meta[c] = d['metadata']
out = {'orig': {}, 'new': {}}
print('=== validity (new run) ===')
for c in new:
    allg = [g for e in new[c].values() for g in e['gens']]
    inv = Counter(g['why'] for g in allg if not g['valid'])
    allinv = [eid[:8] for eid, e in new[c].items() if all(not g['valid'] for g in e['gens'][:3])]
    nv = sum(g['valid'] for g in allg)
    print(NAME[c], f'{nv}/{len(allg)} valid ({100*nv/len(allg):.2f}%)', dict(inv), 'all-3-invalid scenarios:', allinv)
    out['new'][c] = dict(valid=nv, total=len(allg), invalid=dict(inv), all_invalid_scenarios=allinv)
print('=== FR@K valid-aware ===')
for tag, D in (('orig', orig), ('new', new)):
    for c in D:
        row = {}
        for k in (1, 2, 3):
            v, den = fr(D[c], k)
            row[f'FR@{k}'] = (v, den)
        out[tag].setdefault(c, {})['fr'] = row
        print(tag, NAME[c], ' | '.join(f'FR@{k} {row[f"FR@{k}"][0]:.2f} (N={row[f"FR@{k}"][1]})' for k in (1, 2, 3)))
print('=== comparison FR@3 ===')
for c in CONDS[1:]:
    if c in new and 'before' in new:
        o3, n3 = out['orig'][c]['fr']['FR@3'][0], out['new'][c]['fr']['FR@3'][0]
        ot, nt = out['orig']['before']['fr']['FR@3'][0], out['new']['before']['fr']['FR@3'][0]
        print(NAME[c], f'orig {o3:.2f} (delta {o3-ot:+.2f}) | full {n3:.2f} (delta {n3-nt:+.2f}) | direction preserved: {"YES" if (n3-nt)>0 else "NO"}')
print('=== transitions (FR@3, vs full-prompt Target, same scenario ids) ===')
for tag, D in (('orig', orig), ('new', new)):
    if 'before' not in D:
        continue
    for c in CONDS[1:]:
        if c not in D:
            continue
        cnt = Counter()
        for eid, e in D[c].items():
            a, b = status(D['before'][eid]['gens']), status(e['gens'])
            cnt['NE' if 'NE' in (a, b) else f'{a}->{b}'] += 1
        n = sum(v for k, v in cnt.items() if k != 'NE')
        net = cnt['S->F'] - cnt['F->S']
        print(tag, NAME[c], dict(cnt), 'N paired', n, 'net', net, f'net/N {100*net/n:.2f}pp')
        out[tag][c]['transitions'] = dict(cnt)
print('=== prompt tokens reported by vLLM (new run) ===')
pt = [g['prompt_tokens'] for c in new for e in new[c].values() for g in e['gens'] if g['prompt_tokens'] is not None]
if pt:
    print('n', len(pt), 'min/median/max', min(pt), statistics.median(pt), max(pt), '| any>=1800-truncated? all >1800:', all(x > 1800 for x in pt))
    out['vllm_prompt_tokens'] = dict(n=len(pt), min=min(pt), median=statistics.median(pt), max=max(pt))
pre = json.load(open(O + 'muse_news_qwen25_fullprompt_robustness_crossdomain/prompt_length_check_pre_generation.json'))
recon = [x['tokens'] for x in pre['per_scenario']]
if pt and 'before' in new:
    ids = list(new['before'].keys())
    diffs = []
    for c in new:
        for i, eid in enumerate(new[c].keys()):
            for g in new[c][eid]['gens']:
                if g['prompt_tokens'] is not None:
                    diffs.append(g['prompt_tokens'] - recon[i])
    print('vLLM prompt_tokens minus reconstruction: min/max', min(diffs), max(diffs), Counter(diffs).most_common(4))
    out['vllm_minus_reconstruction'] = dict(min=min(diffs), max=max(diffs))
from math import comb
print('=== exact two-sided sign tests (S->F vs F->S) ===')
def sign_p(a,b):
    n=a+b
    if n==0: return 1.0
    m=min(a,b); return min(1.0,2*sum(comb(n,i) for i in range(m+1))/2**n)
for tag in ('orig','new'):
    for c in CONDS[1:]:
        t=out[tag][c]['transitions']; p=sign_p(t.get('S->F',0),t.get('F->S',0))
        out[tag][c]['sign_p']=p; print(tag,NAME[c],t.get('S->F',0),'vs',t.get('F->S',0),'p=%.3f'%p)
json.dump(out, open(sys.argv[1], 'w'), indent=1, default=str)
