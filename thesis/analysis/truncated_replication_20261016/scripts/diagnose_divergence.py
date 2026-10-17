#!/usr/bin/env python3
"""Diagnostic (existing outputs only): WHERE do original and replication texts diverge? A systematic config/prompt difference would diverge at the very start;
numerical (hardware) non-determinism diverges late and unevenly. Also checks whether divergence is concentrated in particular settings/conditions."""
import json, statistics, sys
from collections import Counter, defaultdict
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))
import analyze as A
rows = defaultdict(list); first = []
for sk in A.SET:
    for cond in A.CONDS:
        po, pr = A.paths(sk, cond)
        O, Rr = A.load(po), A.load(pr)
        for cat in A.CATS:
            for eid, og in O[cat].items():
                for x, y in zip(og, Rr[cat][eid]):
                    a, b = x['resp'], y['resp']; same = a == b
                    if same: d = None
                    else:
                        n = min(len(a), len(b)); d = next((i for i in range(n) if a[i] != b[i]), n)
                    rows[(sk, cond)].append((same, d, len(a), len(b)))
                    if not same: first.append((d, len(a), len(b), sk))
print('identical-text rate by setting x condition:')
for sk in A.SET:
    print(' ', sk, ' '.join(f"{c[:3]}={100*sum(r[0] for r in rows[(sk,c)])/len(rows[(sk,c)]):.0f}%" for c in A.CONDS))
ds = [d for d, *_ in first]
print('differing generations:', len(ds), '| first-divergence char index: median', statistics.median(ds), '| p10', sorted(ds)[len(ds)//10], '| p25', sorted(ds)[len(ds)//4], '| p75', sorted(ds)[3*len(ds)//4])
print('diverge within first 10 chars:', f'{100*sum(d<10 for d in ds)/len(ds):.1f}%', '| within first 30:', f'{100*sum(d<30 for d in ds)/len(ds):.1f}%', '| after char 100:', f'{100*sum(d>=100 for d in ds)/len(ds):.1f}%')
rel = [d / max(1, min(la, lb)) for d, la, lb, _ in first]
print('relative divergence position (0=start,1=end): median', round(statistics.median(rel), 2))
byfam = defaultdict(list)
for d, la, lb, sk in first: byfam[sk].append(d)
for sk, v in byfam.items(): print(' ', sk, 'n_diff', len(v), 'median first-diverging char', statistics.median(v))
