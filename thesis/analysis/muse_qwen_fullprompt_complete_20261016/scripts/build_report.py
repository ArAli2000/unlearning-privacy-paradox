import csv
from pathlib import Path
D = Path(__file__).resolve().parents[1]
rd = lambda n: list(csv.DictReader(open(D / n), delimiter='\t'))
def md(h, rows): return '\n'.join(['| ' + ' | '.join(h) + ' |', '|' + '---|' * len(h)] + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows])
fr = rd('frk_fullprompt_v2.tsv')
def frk_tab(ds):
    rows = []
    for r in fr:
        if r['Dataset'] != ds: continue
        cat = r['Category']; bm = cat == 'beneficial_memory_usage'
        rows.append([cat, r['Condition'], f"{r['FR@1 (%)']} ({r['N1']})", 'n/a (1 generation)' if bm else f"{r['FR@2 (%)']} ({r['N2']})", 'n/a (1 generation)' if bm else f"{r['FR@3 (%)']} ({r['N3']})", r['Validity %'], r['Delta FR@3 vs Target (pp) [BM: FR@1]']])
    return md(['category', 'condition', 'FR@1', 'FR@2', 'FR@3', 'validity %', 'Δ vs Target (pp)'], rows)
tr = rd('target_unlearned_transitions.tsv')
def pf(x): return '< 0.0001' if float(x) < 1e-4 else x
TR = md(['dataset', 'category', 'vs Target', 'S→F', 'F→S', 'paired N', 'non-eval.', 'Δ (pp)', 'exact p'],
        [[r['dataset'], r['category'], r['condition vs Target'], r['SAFE->FAILURE'], r['FAILURE->SAFE'], r['paired N'], r['non-evaluable'], r['delta (pp)'], pf(r['exact two-sided p (McNemar/binomial)']) + (' *' if r['p<0.05 (uncorrected)'] == 'YES' else '')] for r in tr]) + '\n\n`*` p < 0.05, uncorrected.'
tw = rd('three_way_all_cells.tsv')
TW = md(['dataset', 'condition', 'category', 'original truncated Δ (A100)', 'replicated truncated Δ (H200)', 'full prompt Δ (H200)'],
        [[r['Dataset'], r['Condition'], r['Category'], f"{float(r['Original truncated delta (A100)']):+.2f}", f"{float(r['Replicated truncated delta (H200)']):+.2f}", f"{float(r['Full prompt delta (H200)']):+.2f}"] for r in tw])
t = (D / 'scripts/REPORT_template.md').read_text()
for k, v in (('{{FRK_NEWS}}', frk_tab('MUSE-News')), ('{{FRK_BOOKS}}', frk_tab('MUSE-Books')), ('{{TRANS}}', TR), ('{{THREEWAY}}', TW)):
    assert k in t; t = t.replace(k, v)
(D / 'REPORT.md').write_text(t); print('REPORT.md', len(t), 'chars; placeholders left:', t.count('{{'))
