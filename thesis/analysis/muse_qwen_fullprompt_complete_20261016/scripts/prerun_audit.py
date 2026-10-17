#!/usr/bin/env python3
"""PRE-RUN audit for the MUSE-Qwen full-prompt completion. Read-only on every existing artifact; writes only into this analysis directory.
Produces: existing_artifact_audit.tsv, checkpoint_verification.tsv, dataset_identity_prelaunch.tsv, prompt_length_audit.tsv, prompt_samples.md, missing_scope.tsv, prerun_summary.json
Run with the project conda env (needs transformers + jinja2):  python -I prerun_audit.py
"""
import csv, hashlib, json, os, re, statistics, sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
R = Path('/mnt/beegfs/work/elshashay/open-unlearning')
OUT = R / 'thesis/analysis/muse_qwen_fullprompt_complete_20261016'
PBD = R / 'external/PersistBench'
PBSRC = R / 'thesis/scripts/persistbench_fullprompt_robustness/pb_src'
sys.path.insert(0, str(PBSRC))
import jinja2  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
from benchmark.prompts import build_generation_prompt  # noqa: E402  (the sandbox package used by the existing full-prompt runs)
from benchmark.utils import generate_hash_id  # noqa: E402

CATS = ['cross_domain', 'sycophancy', 'beneficial_memory_usage']
CATFILE = {'cross_domain': 'cross_domain.jsonl', 'sycophancy': 'sycophancy.jsonl', 'beneficial_memory_usage': 'beneficial_samples.jsonl'}
NGEN = {'cross_domain': 3, 'sycophancy': 3, 'beneficial_memory_usage': 1}
EXPECT = {'cross_domain': 200, 'sycophancy': 200, 'beneficial_memory_usage': 100}
CONDS = ['Target', 'RMU', 'WGA', 'SatImp', 'SimNPO']
LABEL = {'Target': 'before', 'RMU': 'rmu', 'WGA': 'wga', 'SatImp': 'satimp', 'SimNPO': 'simnpo'}
DS = {'news': dict(name='MUSE-News', alias='muse_news_qwen25', manifest='thesis/manifests/model_lists/muse_news_qwen25_persistbench_models.tsv', prefix='muse_news_qwen25',
                   orig_dir='muse_news_qwen25_selected_full', orig_file='muse_news_qwen25_{k}.json'),
      'books': dict(name='MUSE-Books', alias='muse_books_qwen25', manifest='thesis/manifests/model_lists/muse_books_qwen25_persistbench_models.tsv', prefix='muse_books_qwen25',
                    orig_dir='muse_books_qwen25_selected_full', orig_file='muse_books_qwen25_{k}.json')}
FULL_EXIST = {('news', 'sycophancy'): ('muse_news_qwen25_fullprompt_robustness', 'muse_news_qwen25_{k}_fullprompt.json'),
              ('news', 'cross_domain'): ('muse_news_qwen25_fullprompt_robustness_crossdomain', 'muse_news_qwen25_{k}_fullprompt_crossdomain.json')}
PB = 'external/PersistBench/outputs/'
MAXTOK = 96; CTX = 8192


def tsv(name, header, rows):
    with open(OUT / name, 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerow(header)
        for r in rows: assert len(r) == len(header), (name, r); w.writerow(r)


def sha(p):
    h = hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()


OUT.mkdir(parents=True, exist_ok=True)
summary = {}; problems = []

# ------------------------------------------------------------------------------------------------ 1. checkpoints
rows = []; ck = {}
for dk, d in DS.items():
    lines = [l.rstrip('\n').split('\t') for l in open(R / d['manifest'])]
    for lab, mp, tp in lines:
        cond = {v: k for k, v in LABEL.items()}[lab.replace(d['prefix'] + '_', '')]
        real = (R / mp).resolve(); step = re.search(r'checkpoint-(\d+)', mp); treal = (R / tp).resolve()
        wfiles = sorted(p.name for p in real.glob('*.safetensors')); exists = real.is_dir() and (real / 'config.json').exists() and len(wfiles) > 0
        # original behavioural evaluation: model path logged by the original vLLM server for this label (news job 408558, books job 409517)
        logs = sorted((R / 'logs').glob(f'vllm_{lab}_40[0-9]*.log'))
        logs = [l for l in logs if 'trunc' not in l.name and 'fullprompt' not in l.name]
        served = None
        for l in logs:
            m = re.search(r"model='([^']+)'", l.read_text(errors='ignore')[:20000])
            if m: served = (m.group(1), l.name); break
        match = served is not None and Path(served[0]).resolve() == real
        gcfg = json.load(open(real / 'generation_config.json')) if (real / 'generation_config.json').exists() else {}
        ck[(dk, cond)] = dict(label=lab, path=str(real), tok=str(treal), step=step.group(1) if step else 'final (fine-tuned target)', exists=exists, match=match)
        if not (exists and match): problems.append(f'checkpoint {dk}/{cond}: exists={exists} matches_original={match}')
        rows.append([d['name'], cond, lab, mp, str(real), step.group(1) if step else 'n/a (fine-tuned target)', d['manifest'], 'YES' if exists else 'NO', f'{len(wfiles)} safetensors shards' if wfiles else 'none',
                     served[1] if served else 'NOT FOUND', served[0] if served else '', 'YES' if match else 'NO', tp, json.dumps({k: gcfg[k] for k in ('temperature', 'top_p', 'top_k', 'repetition_penalty') if k in gcfg})])
tsv('checkpoint_verification.tsv', ['dataset', 'condition', 'manifest label', 'checkpoint path (manifest)', 'checkpoint realpath', 'checkpoint step', 'manifest source', 'exists?', 'weights', 'original vLLM log',
                                    'model path served in original evaluation', 'matches original behavioural evaluation?', 'tokenizer path', 'checkpoint generation_config sampling keys (vLLM default source)'], rows)
print('checkpoints:', 'ALL VERIFIED' if not any(p.startswith('checkpoint') for p in problems) else [p for p in problems if p.startswith('checkpoint')])

# ------------------------------------------------------------------------------------------------ 2. dataset identity
scen = {}; rows = []
for cat in CATS:
    scen[cat] = [json.loads(l) for l in open(PBD / 'benchmark_samples' / CATFILE[cat])]
fb = [json.loads(l) for l in open(PBD / 'benchmark_samples/full_benchmark.jsonl')]
ids = {cat: [generate_hash_id(r['memories'], r['query']) for r in scen[cat]] for cat in CATS}
for cat in CATS:
    ft = {r.get('failure_type') for r in scen[cat]}
    sub = [generate_hash_id(r['memories'], r['query']) for r in fb if (r.get('failure_type') == cat)]
    rows.append(['benchmark input', cat, len(ids[cat]), EXPECT[cat], 'full_benchmark.jsonl subset identical (ids + order)', 'YES' if sub == ids[cat] else 'NO', ','.join(map(str, ft)), len(set(ids[cat]))])
    if sub != ids[cat] or len(ids[cat]) != EXPECT[cat]: problems.append(f'dataset identity benchmark/{cat}')


def entry_ids(path):
    d = json.load(open(R / path)); out = {c: [] for c in CATS}
    for eid, e in d['entries'].items():
        ft = e.get('failure_type'); ft = 'beneficial_memory_usage' if ft == 'positive_memory_usage' else ft; out[ft].append(eid)
    return out


for dk, d in DS.items():
    for cond in CONDS:
        po = PB + d['orig_dir'] + '/' + d['orig_file'].format(k=LABEL[cond])
        eo = entry_ids(po)
        for cat in CATS:
            same = eo[cat] == ids[cat]
            rows.append([f'{d["name"]} original truncated / {cond}', cat, len(eo[cat]), EXPECT[cat], 'ids + order vs per-category input', 'YES' if same else 'NO', Path(po).name, len(set(eo[cat]))])
            if not same: problems.append(f'dataset identity original {dk}/{cond}/{cat}')
for (dk, cat), (dd, ff) in FULL_EXIST.items():
    for cond in ['Target', 'RMU', 'SatImp', 'SimNPO']:
        pf = PB + dd + '/' + ff.format(k=LABEL[cond]); e = entry_ids(pf)[cat]; same = e == ids[cat]
        rows.append([f'{DS[dk]["name"]} existing full-prompt / {cond}', cat, len(e), EXPECT[cat], 'ids + order vs per-category input', 'YES' if same else 'NO', Path(pf).name, len(set(e))])
        if not same: problems.append(f'dataset identity existing fullprompt {dk}/{cond}/{cat}')
tsv('dataset_identity_prelaunch.tsv', ['artifact', 'category', 'n scenarios', 'expected', 'comparison', 'identical?', 'file', 'unique ids'], rows)
print('dataset identity:', 'ALL IDENTICAL' if not any(p.startswith('dataset') for p in problems) else [p for p in problems if p.startswith('dataset')])

# ------------------------------------------------------------------------------------------------ 3. existing full-prompt artifact audit
rows = []; exist = {}
CFG_OK = {'temperature': 0.0, 'max_tokens': 96}
for (dk, cat), (dd, ff) in FULL_EXIST.items():
    for cond in ['Target', 'RMU', 'SatImp', 'SimNPO']:
        pf = PB + dd + '/' + ff.format(k=LABEL[cond]); j = json.load(open(R / pf)); m = j['metadata']; c = j.get('config', {})
        ng = nj = 0; pt = []; aliases = set(); err = 0
        for e in j['entries'].values():
            for k, r in e['results'].items():
                aliases.add(k)
                for g in r['generations']:
                    ng += 1; nj += (g.get('judge') or {}).get('score') is not None; err += bool(g.get('error'))
                    mm = re.search(r"prompt_tokens['\"]?\s*[=:]\s*(\d+)", str(g.get('memory_raw_api_response')))
                    if mm: pt.append(int(mm.group(1)))
        api = m['models'][0]['api_params']; ok = (len(j['entries']) == 200 and ng == 600 and nj == 600 and err == 0 and api == CFG_OK and aliases == {DS[dk]['alias']} and m['judge_model'] == 'local-judge'
                                                  and 'truncate_prompt_tokens' not in json.dumps(api) and pt and max(pt) + MAXTOK < CTX)
        exist[(dk, cond, cat)] = dict(file=pf, ok=bool(ok), sha=sha(R / pf), ng=ng)
        if not ok: problems.append(f'existing artifact {pf} failed verification')
        rows.append([DS[dk]['name'], cond, cat, pf, ck[(dk, cond)]['path'].split('/saves/')[1], len(j['entries']), ng, nj, err, json.dumps(api), ','.join(sorted(aliases)), m['judge_model'], m['timestamp'], m['store_raw_api_responses'],
                     f'{min(pt)}/{int(statistics.median(pt))}/{max(pt)}', 'YES' if ok else 'NO', sha(R / pf)[:16]])
tsv('existing_artifact_audit.tsv', ['dataset', 'condition', 'category', 'file', 'checkpoint (manifest)', 'scenarios', 'generations', 'judgments', 'generation errors', 'api_params (stored)', 'model alias in prompt', 'judge', 'timestamp',
                                    'raw responses stored', 'vLLM prompt_tokens min/median/max', 'verified complete & configured as intended?', 'sha256[:16]'], rows)
print('existing full-prompt cells verified:', sum(v['ok'] for v in exist.values()), '/', len(exist))

# ------------------------------------------------------------------------------------------------ 4. prompt reconstruction + length audit (all scenarios, all datasets)
tmpl = jinja2.Environment().from_string((R / 'templates/simple_llama_chat_template.jinja').read_text())
ANCH = ['system_message:', '# Tools', '## bio', '## canmore', '## file_search', '## Time Frame Filter', '## python', '## guardian_tool', '# Closing Instructions', 'End of system prompt.']
rows = []; samples = []; lens = {}
FORBID = re.compile(r'(before|rmu|wga|satimp|simnpo|target|unlearn)', re.I)
for dk, d in DS.items():
    tok = AutoTokenizer.from_pretrained(ck[(dk, 'Target')]['tok'])
    # every condition uses this same tokenizer path? (manifest column 3)
    assert len({ck[(dk, c)]['tok'] for c in CONDS}) == 1, 'tokenizer paths differ across conditions'
    for cat in CATS:
        res = []; calib = []
        # calibration against vLLM-reported prompt_tokens in the existing News runs
        ex = None
        if dk == 'news' and cat in ('sycophancy', 'cross_domain'):
            dd, ff = FULL_EXIST[(dk, cat)]; ex = json.load(open(R / PB / dd / ff.format(k='before')))
        for i, r in enumerate(scen[cat]):
            sysp = build_generation_prompt(r['memories'], d['alias'])
            text = tmpl.render(messages=[{'role': 'system', 'content': sysp}, {'role': 'user', 'content': r['query']}])
            n = len(tok(text)['input_ids'])
            res.append(dict(n=n, anchors=all(a in text for a in ANCH), mem=all(m in text for m in r['memories']), q=r['query'] in text, head=text.lstrip().startswith('system_message:'), fits=n + MAXTOK < CTX,
                            alias_in=(f'You are {d["alias"]}' in text), leak=bool(FORBID.search(d['alias'])),
                            memtail=len(tok(text[text.index('<memories>'):])['input_ids']) if '<memories>' in text else -1))
            if ex is not None:
                g = ex['entries'][ids[cat][i]]['results'][d['alias']]['generations'][0]; mm = re.search(r"prompt_tokens['\"]?\s*[=:]\s*(\d+)", str(g.get('memory_raw_api_response')))
                calib.append(int(mm.group(1)) - n if mm else None)
            if i == 0 and cat in ('sycophancy', 'beneficial_memory_usage'): samples.append((d['name'], cat, text, r['query'], n))
        t = sorted(x['n'] for x in res); lens[(dk, cat)] = t
        allok = all(x['anchors'] and x['mem'] and x['q'] and x['head'] and x['fits'] and x['alias_in'] and not x['leak'] for x in res)
        cal = Counter(calib) if calib else None
        if not allok: problems.append(f'prompt audit {dk}/{cat}')
        if cal and max(abs(k) for k in cal if k is not None) > 3: problems.append(f'prompt-token calibration {dk}/{cat}: {dict(cal)}')
        rows.append([d['name'], cat, len(res), t[0], int(statistics.median(t)), t[-1], t[-1] + MAXTOK, CTX, sum(x['n'] > 1800 for x in res), sum(x['memtail'] <= 1800 for x in res), 'YES' if all(x['head'] for x in res) else 'NO', 'YES' if all(x['anchors'] for x in res) else 'NO',
                     'YES' if all(x['mem'] for x in res) else 'NO', 'YES' if all(x['q'] for x in res) else 'NO', 'YES' if all(x['fits'] for x in res) else 'NO', d['alias'], 'none (alias identical for all 5 conditions)',
                     (f'vLLM prompt_tokens - reconstruction = {dict(cal)} (constant ~2-token special-token offset; existing News run)' if cal else 'n/a (no existing run; same builder/tokenizer/template)'), 'PASS' if allok else 'FAIL'])
tsv('prompt_length_audit.tsv', ['dataset', 'category', 'n scenarios', 'min tokens', 'median tokens', 'max tokens', 'max + 96 generated', 'context (max_model_len)', 'scenarios > 1800 (would have been truncated in the original runs)', 'scenarios whose <memories> block start lay within the last 1800 tokens (survived old truncation)', 'starts with system header',
                                'all system/tool anchors present', 'complete memories block present', 'complete query present', 'prompt+96 fits in 8192', 'alias in prompt', 'condition leakage via alias', 'calibration vs vLLM', 'result'], rows)
for dsn, cat, text, q, n in samples:
    pass
with open(OUT / 'prompt_samples.md', 'w') as f:
    f.write('# Representative reconstructed prompts (first scenario of each dataset/category; neutral alias; no truncation)\n\n')
    for dsn, cat, text, q, n in samples:
        f.write(f'## {dsn} / {cat}  ({n} tokens)\n\n- first 600 chars:\n```\n{text[:600]}\n```\n- memories block / query region (last 1200 chars):\n```\n{text[-1200:]}\n```\n\n')
for k, t in lens.items(): print('prompt tokens', k, t[0], int(statistics.median(t)), t[-1])

# ------------------------------------------------------------------------------------------------ 5. missing scope
rows = []; need = {}
for dk, d in DS.items():
    for cond in CONDS:
        for cat in CATS:
            have = exist.get((dk, cond, cat))
            nscen = EXPECT[cat]; gens = nscen * NGEN[cat]
            reuse = bool(have and have['ok'])
            rows.append([d['name'], cond, cat, nscen, NGEN[cat], gens, 'REUSE (verified)' if reuse else 'GENERATE', have['file'] if reuse else '', 0 if reuse else gens])
            need[(dk, cond, cat)] = 0 if reuse else gens
tsv('missing_scope.tsv', ['dataset', 'condition', 'category', 'scenarios', 'generations/scenario', 'cell generations', 'status', 'existing source file', 'new generations needed'], rows)
tot = {dk: sum(v for (a, _, _), v in need.items() if a == dk) for dk in DS}; allnew = sum(need.values())
reused = sum(EXPECT[c] * NGEN[c] for (_, _, c), v in need.items() if v == 0)
print('new generations needed:', tot, 'TOTAL', allnew, '| reused', reused, '| matrix total', allnew + reused)
summary.update(problems=problems, new_generations=tot, total_new=allnew, reused_generations=reused, matrix_total=allnew + reused,
               existing_verified=sum(v['ok'] for v in exist.values()), existing_cells=len(exist), prompt_len={f'{a}/{b}': [t[0], int(statistics.median(t)), t[-1]] for (a, b), t in lens.items()})
json.dump(summary, open(OUT / 'prerun_summary.json', 'w'), indent=1)
print('PROBLEMS:', problems or 'NONE')
