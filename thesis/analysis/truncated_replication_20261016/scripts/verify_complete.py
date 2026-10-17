#!/usr/bin/env python3
"""Step 7 completeness check for ONE replication output JSON. Exit 0 iff complete (and, with --judged, fully judged).
Checks: no duplicate scenario entries; 500 entries; scenario IDs == benchmark input IDs in the same order; categories 200/200/100;
3/3/1 generations per scenario with indices {0..n-1}; no generation errors; no empty responses; (--judged) every generation has a numeric judge score and no judge error."""
import argparse, hashlib, json, sys
from collections import Counter
from pathlib import Path

BENCH = Path('/mnt/beegfs/work/elshashay/open-unlearning/external/PersistBench/benchmark_samples/full_benchmark.jsonl')
NEED = {'cross_domain': 3, 'sycophancy': 3, 'beneficial_memory_usage': 1}
EXPECT_N = {'cross_domain': 200, 'sycophancy': 200, 'beneficial_memory_usage': 100}


def hid(x):
    return hashlib.md5(json.dumps({'memories': sorted(x['memories']), 'query': x['query']}, sort_keys=True).encode()).hexdigest()


def cat(e):
    ft = e.get('failure_type') or e.get('leakage_type', 'cross_domain')
    return 'beneficial_memory_usage' if ft == 'positive_memory_usage' else ft


def check(path, judged=False):
    dup = []
    def hook(pairs):
        ks = [k for k, _ in pairs]
        c = Counter(ks)
        dup.extend(k for k, v in c.items() if v > 1 and len(k) == 32)
        return dict(pairs)
    p = Path(path)
    if not p.exists():
        return dict(ok=False, problems=['file missing'])
    j = json.load(open(p), object_pairs_hook=hook)
    ent = j.get('entries', {})
    bench_ids = [hid(json.loads(l)) for l in open(BENCH)]
    pr = []
    if dup: pr.append(f'duplicate scenario entries: {len(dup)}')
    if list(ent.keys()) != bench_ids:
        pr.append('scenario IDs/order differ from benchmark input' if set(ent) != set(bench_ids) or len(ent) == 500 else f'{len(ent)} of 500 scenarios present (generation incomplete)')
    cc = Counter(cat(e) for e in ent.values())
    cnt = Counter(); nerr = nempty = nunj = njerr = 0
    for eid, e in ent.items():
        c = cat(e); res = e.get('results', {}); gens = next(iter(res.values()), {}).get('generations', []) if len(res) == 1 else None
        if gens is None: pr.append(f'{eid}: results has {len(res)} model keys'); continue
        if len(gens) != NEED[c] or sorted(int(g['generation_index']) for g in gens) != list(range(NEED[c])):
            pr.append(f'{eid}: {len(gens)} generations (need {NEED[c]})'); continue
        for g in gens:
            cnt[c] += 1
            if g.get('error'): nerr += 1
            r = g.get('memory_response')
            if not isinstance(r, str) or not r.strip(): nempty += 1
            if judged:
                jd = g.get('judge')
                if not isinstance(jd, dict) or jd.get('score') is None: nunj += 1
                elif jd.get('error'): njerr += 1
    for c, n in EXPECT_N.items():
        if cc.get(c, 0) != n: pr.append(f'{c}: {cc.get(c, 0)} scenarios (need {n})')
        if cnt.get(c, 0) != n * NEED[c]: pr.append(f'{c}: {cnt.get(c, 0)} generations (need {n * NEED[c]})')
    if nerr: pr.append(f'{nerr} generations with API error')
    if nempty: pr.append(f'{nempty} empty responses')
    if judged and nunj: pr.append(f'{nunj} generations without a judge score')
    if judged and njerr: pr.append(f'{njerr} judge errors')
    return dict(ok=not pr, scenarios=len(ent), categories=dict(cc), generations=dict(cnt), total_generations=sum(cnt.values()), api_errors=nerr, empty=nempty, unjudged=nunj, problems=pr[:12])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('file'); ap.add_argument('--judged', action='store_true'); ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args(); r = check(a.file, a.judged)
    if not a.quiet: print(json.dumps(r))
    sys.exit(0 if r['ok'] else 1)
