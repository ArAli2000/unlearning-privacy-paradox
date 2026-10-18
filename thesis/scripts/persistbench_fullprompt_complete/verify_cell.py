#!/usr/bin/env python3
"""Verify one full-prompt cell file.  usage: verify_cell.py FILE CATEGORY ALIAS [--judged] [--quiet]
Checks: scenario ids + order == per-category benchmark input; N generations per scenario; every response present and error-free; single model alias; no truncation param in api_params;
with --judged every generation has a judge score. Exit 0 = OK."""
import json, os, sys
sys.dont_write_bytecode = True
import os as _os; _ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), *['..']*3))
PB = (_ROOT + '/external/PersistBench')
sys.path.insert(0, (_ROOT + '/thesis/scripts/persistbench_fullprompt_robustness/pb_src'))
from benchmark.utils import generate_hash_id
INP = {'cross_domain': 'cross_domain.jsonl', 'sycophancy': 'sycophancy.jsonl', 'beneficial_memory_usage': 'beneficial_samples.jsonl'}
NS = {'cross_domain': (200, 3), 'sycophancy': (200, 3), 'beneficial_memory_usage': (100, 1)}
path, cat, alias = sys.argv[1:4]; judged = '--judged' in sys.argv; quiet = '--quiet' in sys.argv
res = dict(ok=False, problems=[])
def fin(code):
    if not quiet or code: print(json.dumps(res))
    sys.exit(code)
if not os.path.exists(path): res['problems'].append('missing file'); fin(1)
try: d = json.load(open(path))
except Exception as e: res['problems'].append(f'unreadable json: {e}'); fin(1)
ids = [generate_hash_id(r['memories'], r['query']) for r in map(json.loads, open(f'{PB}/benchmark_samples/{INP[cat]}'))]
ns, ng = NS[cat]; ent = d.get('entries', {})
if list(ent) != ids: res['problems'].append(f'scenario ids/order differ from input ({len(ent)} entries)')
gens = resp = jud = err = 0
for e in ent.values():
    if e.get('failure_type') != cat: res['problems'].append('wrong failure_type'); break
    if set(e['results']) != {alias}: res['problems'].append(f'alias mismatch {set(e["results"])}'); break
    g = e['results'][alias]['generations']
    if len(g) != ng: res['problems'].append(f'{len(g)} generations for a scenario (expected {ng})'); break
    for x in g:
        gens += 1; resp += bool(x.get('memory_response')); err += bool(x.get('error')); jud += (x.get('judge') or {}).get('score') is not None
api = json.dumps(d['metadata']['models'][0].get('api_params'))
if 'truncate' in api: res['problems'].append('truncation parameter present')
if len(ent) != ns or gens != ns * ng: res['problems'].append(f'counts {len(ent)} scenarios / {gens} generations, expected {ns}/{ns * ng}')
if resp != gens or err: res['problems'].append(f'{gens - resp} missing responses, {err} errors')
if judged and jud != gens: res['problems'].append(f'{gens - jud} generations without judge score')
res.update(scenarios=len(ent), generations=gens, responses=resp, errors=err, judged=jud, api_params=api); res['ok'] = not res['problems']
fin(0 if res['ok'] else 1)
