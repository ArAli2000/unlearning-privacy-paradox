#!/usr/bin/env python3
"""Offline check (CPU only) that, under the original 2048/1800 left-truncation, every one of the 500 prompts is actually truncated AND the retained
last-1800-token window still contains ALL of the scenario's memories and its user query, while the persona header + {model_name} lines are cut off.
Renders the real PersistBench system prompt through the real chat template with each setting's tokenizer. Writes truncation_check.tsv."""
import csv, json, sys
sys.path.insert(0, '/mnt/beegfs/work/elshashay/open-unlearning/thesis/analysis/truncated_replication_20261016/persistbench_code/src')
from transformers import AutoTokenizer
import benchmark.prompts as P
R = '/mnt/beegfs/work/elshashay/open-unlearning/'
tpl = open(R + 'templates/simple_llama_chat_template.jinja').read()
rows = [json.loads(l) for l in open(R + 'external/PersistBench/benchmark_samples/full_benchmark.jsonl')]
T = {'A_muse_news_qwen25': ('saves/finetune/muse_news_qwen25_7b_instruct_target', 'muse_news_qwen25_before'),
     'B_muse_books_qwen25': ('saves/finetune/muse_books_qwen25_7b_instruct_target', 'muse_books_qwen25_before'),
     'C_muse_news_llama2': ('NousResearch/Llama-2-7b-hf', 'muse_news_before'), 'D_muse_books_llama2': ('NousResearch/Llama-2-7b-hf', 'muse_books_llama2_before')}
out = []; bad = 0
for k, (tok, label) in T.items():
    tk = AutoTokenizer.from_pretrained(R + tok if tok.startswith('saves') else tok)
    L = []; miss_mem = miss_q = head_kept = short = 0
    for x in rows:
        msgs = [{'role': 'system', 'content': P.build_generation_prompt(x['memories'], label)}, {'role': 'user', 'content': x['query']}]
        text = tk.apply_chat_template(msgs, chat_template=tpl, tokenize=False, add_generation_prompt=False)
        ids = tk(text, add_special_tokens=False)['input_ids']; L.append(len(ids))
        if len(ids) <= 1800: short += 1
        tail = tk.decode(ids[-1800:], skip_special_tokens=False)
        miss_mem += sum(1 for m in x['memories'] if m.strip() not in tail)
        miss_q += x['query'].strip() not in tail
        head_kept += (f'You are {label}, a large language model' in tail) or ('system_message:' in tail)
    bad += miss_mem + miss_q + short
    out.append([k, tok, len(rows), min(L), round(sum(L) / len(L)), max(L), short, miss_mem, miss_q, head_kept])
    print(out[-1])
with open('/mnt/beegfs/work/elshashay/open-unlearning/thesis/analysis/truncated_replication_20261016/truncation_check.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['setting', 'tokenizer', 'scenarios', 'min raw prompt tokens', 'mean', 'max', 'prompts NOT truncated (<=1800)', 'memories missing from retained window', 'queries missing from retained window', 'prompts whose retained window still contains persona header/alias'])
    w.writerows(out)
sys.exit(1 if bad else 0)
