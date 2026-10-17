"""v2 against the blind manual audit (137 non-collapse v1-invalid responses) and against v1 on every generation."""
from common import *
rows = invalid_rows(); rest, lab = anon_ids(rows)
tp = fn = fp = tn = 0; miss = []
for r in rest:
    v2inv = not r['g']['v2valid']; man = lab[r['anon']]['invalid']
    tp += v2inv and man; fn += (not v2inv) and man; fp += v2inv and not man; tn += (not v2inv) and not man
    if (not v2inv) and man: miss.append((r['anon'], lab[r['anon']]['group'], 'borderline' if lab[r['anon']]['borderline'] else ''))
print(f'v2 vs manual on the 137 v1-flagged responses: TP {tp}  FN {fn}  FP {fp}  TN {tn}; missed: {miss}')
n = new_inv = dropped = 0
for x in ALL:
    for sc in x['L'].values():
        for gens in sc.values():
            for g in gens:
                n += 1; new_inv += (not g['v2valid']) and g['valid']; dropped += g['v2valid'] and not g['valid']
print(f'generations {n}; newly invalid under v2: {new_inv}; invalid->valid under v2: {dropped}')
