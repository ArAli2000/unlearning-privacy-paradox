"""Loads every final thesis PersistBench generation once and annotates it with v1 / v2 / v2r validity. Read-only."""
import sys, csv, json, random
from pathlib import Path
from audit_lib import *
sys.path.insert(0, str(R / 'thesis/scripts/validation'))
from create_persistbench_validity_summary_v2 import classify_v2

OUT = R / 'thesis/analysis/final_validity_audit'


def tsv(name, header, rows):
    with open(OUT / name, 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n')
        w.writerow(header)
        for r in rows:
            assert len(r) == len(header), (name, r)
            w.writerow(r)


def fmt(x, nd=2):
    return 'NA' if x is None else f'{x:.{nd}f}'


def annotate(L):
    for sc in L.values():
        for gens in sc.values():
            for g in gens:
                g['v2why'], g['v2rule'] = classify_v2(g['resp'])
                g['v2valid'] = g['v2why'] == 'valid'
                g['v2rvalid'] = classify_v2(g['resp'], repetition_rule=True)[0] == 'valid'


ALL = []  # dicts: group, dataset, model, cond, path, cat_only(None|cat), L
for d, m, c, p in DATASETS:
    L = load(p); annotate(L)
    ALL.append(dict(group='main', dataset=d, model=m, cond=c, path=p, L=L, cats=CATS))
for d, m, c, p, cat in FULLPROMPT:
    L = load(p); annotate(L)
    ALL.append(dict(group='fullprompt', dataset=d, model=m, cond=c, path=p, L=L, cats=[cat]))
for c, k in METHODS:  # MUSE-News Llama-2: part of the 24-condition paradox scan only; not in the 25-condition appendix FR@K set
    p = f'{PB}muse_news_selected_full/muse_news_{k}.json' if k == 'before' else f'{PB}muse_news_selected_full/muse_news_{k}_selected.json'
    L = load(p); annotate(L)
    ALL.append(dict(group='scan_extra', dataset='MUSE-News', model='Llama-2-7B', cond=c, path=p, L=L, cats=CATS))
MAIN = [x for x in ALL if x['group'] == 'main']
IS_WGA = lambda x: (x['dataset'], x['model'], x['cond']) == ('MUSE-Books', 'Llama-2-7B', 'WGA')


def invalid_rows():
    """all v1-invalid generations in the same traversal order used for the blind-ID assignment"""
    rows = []
    for x in ALL:
        for cat, sc in x['L'].items():
            for eid, gens in sc.items():
                for g in gens:
                    if not g['valid']:
                        rows.append(dict(x=x, cat=cat, eid=eid, g=g))
    return rows


def anon_ids(rows):
    rest = [r for r in rows if not IS_WGA(r['x'])]
    random.Random(0).shuffle(rest)
    lab = json.load(open(Path(__file__).parent / 'manual_labels.json'))
    for i, r in enumerate(rest):
        r['anon'] = f'A{i + 1:03d}'
        assert r['g']['resp'][:30] == lab[r['anon']]['fp'], ('anon id drift', r['anon'])
    return rest, lab
