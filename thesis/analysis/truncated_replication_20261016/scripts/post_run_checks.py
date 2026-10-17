#!/usr/bin/env python3
"""After the four jobs finished: (1) job_summary.tsv from sacct, (2) replication_config_verification.tsv = per condition, the ACTUAL replication vLLM server
configuration (from its log) vs the ORIGINAL one, (3) completeness/judging coverage per file (Step 7). Read-only.
  usage: post_run_checks.py JOBID_A JOBID_B JOBID_C JOBID_D"""
import ast, csv, glob, json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from verify_complete import check

R = Path('/mnt/beegfs/work/elshashay/open-unlearning')
OUT = Path(__file__).resolve().parents[1]
RO = R / 'external/PersistBench/outputs/truncated_replication_20261016'
SETS = ['A_muse_news_qwen25', 'B_muse_books_qwen25', 'C_muse_news_llama2', 'D_muse_books_llama2']
SUB = {'A_muse_news_qwen25': 'muse_news_qwen25', 'B_muse_books_qwen25': 'muse_books_qwen25', 'C_muse_news_llama2': 'muse_news_llama2', 'D_muse_books_llama2': 'muse_books_llama2'}
jobs = dict(zip(SETS, sys.argv[1:5]))


def parse_log(p):
    t = Path(p).read_text(errors='replace'); d = {}
    m = re.search(r'non-default args: (\{.*\})', t); d['args'] = ast.literal_eval(m.group(1)) if m else {}
    m = re.search(r'Initializing a V1 LLM engine \(v([\d.]+)\)', t); d['vllm'] = m.group(1) if m else ''
    m = re.search(r"Default vLLM sampling parameters have been overridden by the model's `generation_config.json`: `(\{.*?\})`", t); d['override'] = m.group(1) if m else 'NONE'
    m = re.search(r'GPU KV cache size: ([\d,]+) tokens', t); d['kv'] = m.group(1) if m else ''
    return d


# ---------------- job summary
rows = []
for sk, jid in jobs.items():
    o = subprocess.run(['sacct', '-j', jid, '--format=JobID,JobName%24,NodeList,AllocTRES%90,Elapsed,State,ExitCode,Start,End', '-X', '-n', '-P'], capture_output=True, text=True).stdout.strip().splitlines()
    f = o[0].split('|') if o else [''] * 9
    gpu = sorted(RO.glob(f'_meta/{SUB[sk]}/gpu_{jid}.txt'))
    gname = gpu[0].read_text().strip() if gpu else ''
    rows.append([sk, jid, f[2], gname, re.sub(r'.*gres/gpu:([a-z0-9]+)=1.*', r'\1', f[3]), f[5], f[6], f[4], f[7], f[8], str(RO / SUB[sk])])
with open(OUT / 'job_summary.tsv', 'w', newline='') as fo:
    w = csv.writer(fo, delimiter='\t', lineterminator='\n'); w.writerow(['setting', 'SLURM job ID', 'node', 'GPU (nvidia-smi)', 'GPU gres', 'state', 'exit code', 'elapsed', 'start', 'end', 'output path']); w.writerows(rows)

# ---------------- config verification: replication logs vs original logs (from configuration_audit.tsv)
aud = list(csv.DictReader(open(OUT / 'configuration_audit.tsv'), delimiter='\t'))
res = []; allgood = True
for a in aud:
    sk, label = a['setting'], a['served model name (= original label)']
    cand = sorted(glob.glob(str(R / 'logs' / f'vllm_trunc_repl_{label}_{jobs[sk]}_*.log')))
    if not cand: res.append([sk, a['condition'], label, 'NO REPLICATION LOG', '', '', '', '', '', '', '']); allgood = False; continue
    L = parse_log(cand[-1]); O = parse_log(R / 'logs' / a['orig vLLM log'])
    keys = ['dtype', 'gpu_memory_utilization', 'max_model_len', 'served_model_name', 'chat_template', 'tokenizer', 'model_tag']
    diffs = []
    for k in keys:
        x, y = L['args'].get(k), O['args'].get(k)
        if k in ('model_tag', 'tokenizer'):
            x = str(Path(x).resolve()) if x and Path(x).exists() else x; y = str(Path(y).resolve()) if y and Path(y).exists() else y
        if k == 'chat_template': x, y = Path(x).name, Path(y).name
        if x != y: diffs.append(f'{k}: orig={y} repl={x}')
    extra = sorted((set(L['args']) ^ set(O['args'])) - {'port'})
    same = (not diffs) and (not extra) and L['vllm'] == O['vllm'] and L['override'] == O['override']
    allgood &= same
    probe = RO / '_meta' / SUB[sk] / ('truncation_probe_' + label.replace('_before', '_target') + '.json')
    pr = json.load(open(probe)) if probe.exists() else None
    res.append([sk, a['condition'], label, 'IDENTICAL' if same else 'DIFFERENT', '; '.join(diffs) + (' extra-args:' + ','.join(extra) if extra else ''), f"{O['vllm']} -> {L['vllm']}", O['override'] == L['override'] and O['override'] or f"{O['override']} -> {L['override']}",
                O['kv'] + ' -> ' + L['kv'], a['orig GPU type (AllocTRES gres)'], 'prompt_tokens after truncation: ' + (','.join(str(x['prompt_tokens']) for x in pr) if pr else 'NO PROBE'), cand[-1].split('/')[-1]])
with open(OUT / 'replication_config_verification.tsv', 'w', newline='') as fo:
    w = csv.writer(fo, delimiter='\t', lineterminator='\n')
    w.writerow(['setting', 'condition', 'served name', 'server config vs original log', 'argument differences', 'vLLM version (orig -> repl)', 'effective sampling-default override line', 'GPU KV-cache tokens (orig -> repl; hardware-sensitive)', 'orig GPU', 'runtime truncation probe', 'replication vLLM log']); w.writerows(res)
print('server configuration identical for all conditions:', allgood)

# ---------------- completeness (Step 7)
tot = 0; comp = []
for sk in SETS:
    for f in sorted((RO / SUB[sk]).glob('*_truncated_replication.json')):
        c = check(f, judged=True); tot += c.get('total_generations', 0) if c['ok'] else 0
        comp.append([sk, f.name, c.get('scenarios'), json.dumps(c.get('generations')), c.get('total_generations'), c.get('api_errors'), c.get('empty'), c.get('unjudged'), 'COMPLETE+JUDGED' if c['ok'] else 'INCOMPLETE: ' + '; '.join(c['problems'])])
with open(OUT / 'completeness.tsv', 'w', newline='') as fo:
    w = csv.writer(fo, delimiter='\t', lineterminator='\n')
    w.writerow(['setting', 'file', 'scenarios', 'generations per category', 'total generations', 'API errors', 'empty responses', 'unjudged generations', 'status']); w.writerows(comp)
print(f'complete+judged files: {sum(1 for c in comp if c[-1].startswith("COMPLETE"))}/20; total verified generations: {tot}')
