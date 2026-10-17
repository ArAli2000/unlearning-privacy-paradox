import csv, json
from pathlib import Path
D = Path(__file__).resolve().parents[1]
rd = lambda n: list(csv.DictReader(open(D / n), delimiter='\t'))
def md(h, rows): return '\n'.join(['| ' + ' | '.join(h) + ' |', '|' + '---|' * len(h)] + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows])
SETN = {'A_muse_news_qwen25': 'A. MUSE-News Qwen2.5-7B', 'B_muse_books_qwen25': 'B. MUSE-Books Qwen2.5-7B', 'C_muse_news_llama2': 'C. MUSE-News Llama-2-7B', 'D_muse_books_llama2': 'D. MUSE-Books Llama-2-7B'}
SHORT = {'A_muse_news_qwen25': 'A News-Qwen', 'B_muse_books_qwen25': 'B Books-Qwen', 'C_muse_news_llama2': 'C News-Llama2', 'D_muse_books_llama2': 'D Books-Llama2'}
ov = [r for r in rd('original_vs_replication_v2.tsv') if r['primary K'] == 'yes']
out = []
for sk, nm in SETN.items():
    rows = []
    for c in ('Target', 'RMU', 'WGA', 'SatImp', 'SimNPO'):
        cells = []
        for cat in ('cross_domain', 'sycophancy', 'beneficial_memory_usage'):
            r = [x for x in ov if x['setting'] == sk and x['condition'] == c and x['category'] == cat][0]
            cells.append(f"{r['Original FR (%)']} → {r['Replication FR (%)']}")
        rows.append([c] + cells)
    out.append(f'**{nm}** (FR@3 cross-domain / FR@3 sycophancy / FR@1 beneficial-memory; `NA` = non-evaluable)\n\n' + md(['condition', 'cross-domain', 'sycophancy', 'beneficial'], rows))
FR3 = '\n\n'.join(out)
fl = [r for r in rd('delta_sign_replication_v2.tsv') if r['strict sign flip (opposite non-zero)'] == 'YES']
FLIPS = md(['setting', 'category', 'method', 'orig Δ', 'repl Δ', 'involves |Δ|≤0.5', '|Δ|>0.5 both'], [[r['setting'], r['category'], r['method'], f"{float(r['original delta (pp, exact)']):+.2f}", f"{float(r['replication delta (pp, exact)']):+.2f}", r['flip involves |delta|<=0.5 on either run'], r['flip with |delta|>0.5 on both']] for r in fl])
POOLED = md(['group', 'categories', 'paired evaluable N', 'changed', 'change %', 'agreement %', 'S→F', 'F→S', 'identical text %'], [[r['group'], r['categories'], r['paired evaluable N'], r['changed'], r['change %'], r['agreement %'], r['SAFE->FAILURE'], r['FAILURE->SAFE'], r['identical response text %']] for r in rd('scenario_repeatability_pooled_v2.tsv')])
tr = rd('replication_target_unlearned_transitions_v2.tsv')
TRANS = md(['setting', 'category', 'vs Target', 'S→F', 'F→S', 'paired N', 'non-eval.', 'Δ FR@3 (pp)', 'exact p'], [[SHORT[r['setting']], r['category'], r['condition vs Target'], r['SAFE->FAILURE'], r['FAILURE->SAFE'], r['paired N'], r['non-evaluable'], r['delta FR@3 (pp)'], ('NA (non-evaluable)' if r['paired N'] == '0' else r['exact two-sided p (McNemar/binomial)'] + (' *' if r['p<0.05'] == 'YES' else ''))] for r in tr]) + '\n\n`*` p < 0.05, uncorrected.'
tw = rd('muse_news_qwen_three_way_v2.tsv')
THREE = md(list(tw[0].keys()), [list(r.values()) for r in tw])
t = (D / 'scripts/REPORT_template.md').read_text()
for k, v in (('{{FR3_TABLES}}', FR3), ('{{FLIPS}}', FLIPS), ('{{POOLED}}', POOLED), ('{{TRANS}}', TRANS), ('{{THREEWAY}}', THREE)):
    assert k in t; t = t.replace(k, v)
(D / 'REPORT.md').write_text(t); print('REPORT.md', len(t), 'chars')
