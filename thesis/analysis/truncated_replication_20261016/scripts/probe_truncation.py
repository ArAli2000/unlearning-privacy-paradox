#!/usr/bin/env python3
"""Runtime evidence that left-truncation is ACTIVE: sends 1-token requests (never stored as data) for the first scenario of each category through the
running server and records usage.prompt_tokens (vLLM reports the count AFTER truncation; expected == 1800 when the raw prompt is longer)."""
import json, sys
sys.path.insert(0, sys.argv[4]) if len(sys.argv) > 4 else None
from openai import OpenAI
from benchmark.prompts import build_generation_prompt
port, label, out = int(sys.argv[1]), sys.argv[2], sys.argv[3]
c = OpenAI(base_url=f'http://127.0.0.1:{port}/v1', api_key='dummy')
rows = [json.loads(l) for l in open('/mnt/beegfs/work/elshashay/open-unlearning/external/PersistBench/benchmark_samples/full_benchmark.jsonl')]
seen, res = set(), []
for x in rows:
    ft = x.get('failure_type') or x.get('leakage_type', 'cross_domain')
    if ft in seen: continue
    seen.add(ft)
    r = c.chat.completions.create(model=label, messages=[{'role': 'system', 'content': build_generation_prompt(x['memories'], label)}, {'role': 'user', 'content': x['query']}],
                                  max_tokens=1, temperature=0.0, extra_body={'truncate_prompt_tokens': 1800})
    res.append(dict(category=ft, prompt_tokens=r.usage.prompt_tokens))
json.dump(res, open(out, 'w'))
print('truncation probe', label, res)
sys.exit(0 if all(x['prompt_tokens'] == 1800 for x in res) else 2)
