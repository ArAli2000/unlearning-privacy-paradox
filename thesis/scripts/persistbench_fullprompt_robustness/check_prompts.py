"""Step 2 of the full-prompt robustness run: reconstruct all 200 sycophancy prompts
(no truncation) with the Qwen tokenizer + simple_llama_chat_template.jinja and check they fit in 8192.
Read-only. Usage: python check_prompts.py <alias> <out_json>"""
import json, sys, statistics, jinja2
ROOT = '/mnt/beegfs/work/elshashay/open-unlearning/'
alias, out = sys.argv[1], sys.argv[2]
src = open(ROOT + 'external/PersistBench/src/benchmark/prompts.py').read().split(')\n', 1)[1]
ns = {'FAILURE_TYPE_BENEFICIAL_MEMORY': 'beneficial_memory_usage', 'FAILURE_TYPE_CROSS_DOMAIN': 'cross_domain', 'FAILURE_TYPE_SYCOPHANCY': 'sycophancy'}
exec(src, ns)
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained(ROOT + 'saves/finetune/muse_news_qwen25_7b_instruct_target')
tmpl = jinja2.Environment().from_string(open(ROOT + 'templates/simple_llama_chat_template.jinja').read())
rows = [json.loads(l) for l in open(ROOT + 'external/PersistBench/benchmark_samples/sycophancy.jsonl')]
MAXTOK = 96; res = []
anchors = ['system_message:', '# Tools', '## bio', '## canmore', '## file_search', '## Time Frame Filter', '## python', '## guardian_tool', '# Closing Instructions', 'End of system prompt.']
for r in rows:
    sysp = ns['build_generation_prompt'](r['memories'], alias)
    text = tmpl.render(messages=[{'role': 'system', 'content': sysp}, {'role': 'user', 'content': r['query']}])
    n = len(tok(text)['input_ids'])
    res.append(dict(tokens=n, anchors_present=all(a in text for a in anchors),
                    memories_present=all(m in text for m in r['memories']), query_present=r['query'] in text,
                    starts_with_header=text.lstrip().startswith('system_message:'), fits=(n + MAXTOK < 8192)))
t = [x['tokens'] for x in res]
summ = dict(alias=alias, n=len(res), min=min(t), median=statistics.median(t), max=max(t), max_plus_96=max(t) + MAXTOK,
            all_fit_8192=all(x['fits'] for x in res), all_anchors=all(x['anchors_present'] for x in res),
            all_memories=all(x['memories_present'] for x in res), all_queries=all(x['query_present'] for x in res),
            all_start_with_header=all(x['starts_with_header'] for x in res))
json.dump(dict(summary=summ, per_scenario=res), open(out, 'w'), indent=1)
print(json.dumps(summ))
