#!/usr/bin/env python3
"""Steps 1-3: reconstruct the ORIGINAL truncated MUSE PersistBench pipeline from primary evidence and verify that the intended replication
configuration agrees with it, for all 20 conditions. Read-only: reads manifests, original vLLM logs, original output JSON metadata, sacct, checkpoints.

Writes (next to this script's parent):
  configuration_audit.tsv  - one row per (setting, condition): original evidence vs replication intent, with agreement flags
  dataset_identity.tsv     - scenario-ID identity of the original outputs vs the benchmark input, per setting/condition/category
Exit code 1 if ANY intended-vs-original discrepancy exists (the launcher gate)."""
import ast, csv, hashlib, json, re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[3] if False else Path('/mnt/beegfs/work/elshashay/open-unlearning')
OUT = Path(__file__).resolve().parents[1]
PB = R / 'external/PersistBench'
LABELS = ['before', 'rmu', 'wga', 'simnpo', 'satimp']

# setting -> (dataset, model, manifest, manifest label fmt, original out dir + file fmt, original vllm log fmt + job map, served-name fmt)
S = {
    'A_muse_news_qwen25': dict(dataset='MUSE-News', model='Qwen2.5-7B-Instruct', manifest='thesis/manifests/model_lists/muse_news_qwen25_persistbench_models.tsv',
                              label='muse_news_qwen25_{l}', outdir='muse_news_qwen25_selected_full', outfile='muse_news_qwen25_{l}.json', log='vllm_muse_news_qwen25_{l}_408558_{i}.log', job='408558_{i}', family='qwen'),
    'B_muse_books_qwen25': dict(dataset='MUSE-Books', model='Qwen2.5-7B-Instruct', manifest='thesis/manifests/model_lists/muse_books_qwen25_persistbench_models.tsv',
                               label='muse_books_qwen25_{l}', outdir='muse_books_qwen25_selected_full', outfile='muse_books_qwen25_{l}.json', log='vllm_muse_books_qwen25_{l}_409517_{i}.log', job='409517_{i}', family='qwen'),
    'C_muse_news_llama2': dict(dataset='MUSE-News', model='Llama-2-7B', manifest='research_history/04_muse_track_a/manifests/muse_news_persistbench_models.tsv',
                              label=None, outdir='muse_news_selected_full', outfile=None, log=None, job=None, family='llama2'),
    'D_muse_books_llama2': dict(dataset='MUSE-Books', model='Llama-2-7B', manifest='thesis/manifests/model_lists/muse_books_llama2_persistbench_models.tsv',
                               label='muse_books_llama2_{l}', outdir='muse_books_llama2_selected_full', outfile='muse_books_llama2_{l}.json', log='vllm_muse_books_llama2_{l}_408885_{i}.log', job='408885_{i}', family='llama2'),
}
# Track-A MUSE-News Llama-2 uses its own labels / final logs (jobs 407769_0 for Target, 407781_1..4 for the unlearned checkpoints)
NEWS_L2 = {'before': ('muse_news_before', 'muse_news_before.json', 'vllm_muse_news_before_407769_0.log', '407769_0'),
           'rmu': ('muse_news_rmu_selected', 'muse_news_rmu_selected.json', 'vllm_muse_news_rmu_selected_407781_1.log', '407781_1'),
           'wga': ('muse_news_wga_selected', 'muse_news_wga_selected.json', 'vllm_muse_news_wga_selected_407781_2.log', '407781_2'),
           'simnpo': ('muse_news_simnpo_selected', 'muse_news_simnpo_selected.json', 'vllm_muse_news_simnpo_selected_407781_3.log', '407781_3'),
           'satimp': ('muse_news_satimp_selected', 'muse_news_satimp_selected.json', 'vllm_muse_news_satimp_selected_407781_4.log', '407781_4')}
NEWS_L2_FILE = {'before': 'muse_news_before.json', 'rmu': 'muse_news_rmu_selected.json', 'wga': 'muse_news_wga_selected.json', 'simnpo': 'muse_news_simnpo_selected.json', 'satimp': 'muse_news_satimp_selected.json'}
# The replication launcher uses these EXACT values (single source of truth = launcher; mirrored here so the gate can compare)
INTENT = dict(temperature=0.0, max_tokens=96, max_model_len=2048, truncate_prompt_tokens=1800, dtype='bfloat16', gpu_memory_utilization=0.9,
              chat_template='templates/simple_llama_chat_template.jinja', extra_body_keys=['truncate_prompt_tokens'], concurrency=1)
TEMPLATE = R / INTENT['chat_template']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def real(p):
    return str(Path(p).resolve()) if p and (str(p).startswith('/') or (R / p).exists()) else p


def abspath(p):
    q = Path(p)
    return q if q.is_absolute() else R / q


def parse_log(logname):
    f = R / 'logs' / logname
    txt = f.read_text(errors='replace')
    d = {}
    m = re.search(r'non-default args: (\{.*\})', txt)
    d['args'] = ast.literal_eval(m.group(1)) if m else {}
    m = re.search(r'Initializing a V1 LLM engine \(v([\d.]+)\)', txt); d['vllm'] = m.group(1) if m else ''
    m = re.search(r'Default vLLM sampling parameters have been overridden by the model\'s `generation_config.json`: `(\{.*?\})`', txt); d['override'] = m.group(1) if m else 'NONE (no override line: vLLM defaults)'
    m = re.search(r'GPU KV cache size: ([\d,]+) tokens', txt); d['kv'] = m.group(1) if m else ''
    d['seed'] = (re.search(r"seed=(\d+)", txt) or [None, ''])[1]
    return d


def sacct(job):
    try:
        o = subprocess.run(['sacct', '-j', job, '--format=NodeList,AllocTRES%80,Elapsed,State,Start', '-X', '-n', '-P'], capture_output=True, text=True, timeout=60).stdout.strip().splitlines()
        return o[0].split('|') if o else ['', '', '', '', '']
    except Exception:
        return ['', '', '', '', '']


def gen_cfg(path):
    p = abspath(path) / 'generation_config.json'
    if p.exists():
        j = json.load(open(p))
        return json.dumps({k: j[k] for k in ('repetition_penalty', 'temperature', 'top_k', 'top_p', 'do_sample') if k in j})
    return 'none (HF id or no file)'


def has_weights(path):
    p = abspath(path)
    return p.is_dir() and any(p.glob('*.safetensors')) or any(p.glob('pytorch_model*.bin')) if p.is_dir() else False


rows, ident = [], []
def hid(x):
    return hashlib.md5(json.dumps({'memories': sorted(x['memories']), 'query': x['query']}, sort_keys=True).encode()).hexdigest()


bench = [json.loads(l) for l in open(PB / 'benchmark_samples/full_benchmark.jsonl')]
bench_cat = {}
for x in bench:
    ft = x.get('failure_type') or x.get('leakage_type', 'cross_domain')
    bench_cat.setdefault('beneficial_memory_usage' if ft == 'positive_memory_usage' else ft, []).append(x)
print('benchmark input: ', {k: len(v) for k, v in bench_cat.items()}, 'sha', sha(PB / 'benchmark_samples/full_benchmark.jsonl'))
disc = []
for key, s in S.items():
    man = [l.rstrip('\n').split('\t') for l in open(R / s['manifest']) if l.strip()]
    for i, (lab, mpath, tpath) in enumerate(man):
        l = LABELS[i]
        if key.startswith('C_'):
            served, ofile, logn, job = NEWS_L2[l]
        else:
            served, ofile, logn, job = s['label'].format(l=l), s['outfile'].format(l=l), s['log'].format(l=l, i=i), s['job'].format(i=i)
        assert lab == served, (lab, served)
        L = parse_log(logn); a = L['args']; sc = sacct(job)
        op = PB / 'outputs' / s['outdir'] / ofile; oj = json.load(open(op)); om = oj['metadata']['models'][0]
        ent = oj['entries']
        # dataset identity: compare entry-ID set and ORDER with benchmark input
        ids = list(ent.keys()); cats = {}
        for eid, e in ent.items():
            ft = e.get('failure_type') or e.get('leakage_type', 'cross_domain'); cats.setdefault('beneficial_memory_usage' if ft == 'positive_memory_usage' else ft, []).append(eid)
        for c, xs in bench_cat.items():
            bids = [hid(x) for x in xs]
            ident.append([key, l, c, len(bids), len(cats.get(c, [])), 'YES' if set(bids) == set(cats.get(c, [])) else 'NO', 'YES' if bids == cats.get(c, []) else 'NO'])
        gpc = {c: sorted({len(next(iter(ent[e]['results'].values()))['generations']) for e in v}) for c, v in cats.items()}
        # checks (replication intent vs ORIGINAL evidence)
        checks = {
            'temperature': om['api_params'].get('temperature') == INTENT['temperature'],
            'max_tokens': om['api_params'].get('max_tokens') == INTENT['max_tokens'],
            'truncate_prompt_tokens': om['api_params'].get('extra_body', {}).get('truncate_prompt_tokens') == INTENT['truncate_prompt_tokens'],
            'extra_body_only_truncate': sorted(om['api_params'].get('extra_body', {}).keys()) == INTENT['extra_body_keys'],
            'max_model_len': a.get('max_model_len') == INTENT['max_model_len'],
            'dtype': a.get('dtype') == INTENT['dtype'],
            'gpu_memory_utilization': a.get('gpu_memory_utilization') == INTENT['gpu_memory_utilization'],
            'chat_template': real(a.get('chat_template', '')) == str(TEMPLATE.resolve()),
            'served_name': a.get('served_model_name') == [served],
            'model_path_manifest_eq_log': (real(mpath) if not mpath.startswith('muse-bench') else mpath) == (real(a.get('model_tag')) if not str(a.get('model_tag', '')).startswith('muse-bench') else a.get('model_tag')),
            'tokenizer_manifest_eq_log': real(tpath) == real(a.get('tokenizer')),
            'checkpoint_exists': mpath.startswith('muse-bench') or has_weights(mpath),
            'gen_counts_3_3_1': gpc.get('cross_domain') == [3] and gpc.get('sycophancy') == [3] and gpc.get('beneficial_memory_usage') == [1],
            'entries_500': len(ids) == 500,
            'vllm_0.23.0': L['vllm'] == '0.23.0',
        }
        bad = [k for k, v in checks.items() if not v]
        if bad: disc.append((key, l, bad))
        rows.append([key, s['dataset'], s['model'], l, served, mpath, real(mpath) if not mpath.startswith('muse-bench') else mpath, tpath, s['manifest'],
                     gen_cfg(mpath) if not mpath.startswith('muse-bench') else 'HF id', L['override'], json.dumps(om['api_params']), a.get('max_model_len'), a.get('dtype'), a.get('gpu_memory_utilization'),
                     Path(a.get('chat_template', '')).name, sha(a['chat_template']) if a.get('chat_template') and Path(a['chat_template']).exists() else '', a.get('served_model_name'), L['vllm'], L['kv'],
                     logn, job, sc[0], re.sub(r'.*gres/gpu:([a-z0-9]+)=1.*', r'\1', sc[1]), sc[2], sc[3], str(op.relative_to(R)), oj['metadata']['timestamp'], len(ids), json.dumps(gpc),
                     'temperature=%s max_tokens=%s max_model_len=%s truncate=%s left chat_template=%s dtype=%s gpu_mem=%s' % (INTENT['temperature'], INTENT['max_tokens'], INTENT['max_model_len'], INTENT['truncate_prompt_tokens'], Path(INTENT['chat_template']).name, INTENT['dtype'], INTENT['gpu_memory_utilization']),
                     'ALL OK' if not bad else 'DISCREPANCY: ' + ','.join(bad)])
hdr = ['setting', 'dataset', 'model', 'condition', 'served model name (= original label)', 'checkpoint path (manifest)', 'checkpoint realpath', 'tokenizer path (manifest)', 'manifest source',
       'checkpoint generation_config.json (effective sampling defaults)', 'vLLM sampling-default override line (original log)', 'original api_params (stored in output JSON)',
       'orig max_model_len', 'orig dtype', 'orig gpu_memory_utilization', 'orig chat template', 'orig chat template sha256[:16]', 'orig served_model_name', 'orig vLLM version', 'orig GPU KV cache tokens',
       'orig vLLM log', 'orig SLURM job', 'orig node', 'orig GPU type (AllocTRES gres)', 'orig elapsed', 'orig state', 'original output file', 'orig output timestamp', 'orig entries', 'orig generations per category (scenario counts)',
       'REPLICATION intended configuration', 'intent vs original evidence']
with open(OUT / 'configuration_audit.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerow(hdr); w.writerows(rows)
with open(OUT / 'dataset_identity.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerow(['setting', 'condition', 'category', 'n in benchmark input', 'n in original output', 'same ID set', 'same ID order']); w.writerows(ident)
print('rows', len(rows), '| discrepancies:', disc if disc else 'NONE')
print('identity: all same set', all(r[5] == 'YES' for r in ident), '| all same order', all(r[6] == 'YES' for r in ident))
sys.exit(1 if disc or not all(r[5] == 'YES' and r[6] == 'YES' for r in ident) else 0)
