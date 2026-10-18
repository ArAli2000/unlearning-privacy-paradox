#!/usr/bin/env python3
"""Build thesis/manifests/selection/selected_checkpoint_metrics.tsv from tracked records only.

Inputs (all tracked, read-only):
  thesis/manifests/selection/*_SELECTED_MODEL_PATHS.tsv   selected step and best_metric per run
  thesis/manifests/trainer_states/*_trainer_state.json    trainer_state.json of the selected checkpoint
  thesis/manifests/muse_eval/*_MUSE_SUMMARY.json          MUSE summary of the selected checkpoint

For each of the 12 selected runs (3 settings x RMU, WGA, SatImp, SimNPO) the row holds the selection score
(`eval_best_agg` logged at the selected step) and the MUSE metrics logged at that step. Values are copied
unchanged from the JSON files (no rounding, nothing computed except the consistency checks). A field that
is absent from a record stays empty. The script stops with an error if the selected step is not in the
trainer state's log, or if `best_metric`, the logged score and the selection TSV disagree.

Run from anywhere:  python3 thesis/scripts/validation/build_selected_checkpoint_metrics.py [--check]
  --check   do not write; exit 1 if the tracked TSV differs from what the records give.
"""
import csv
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
SETTINGS = [
    ('muse_news_qwen25_7b_instruct', 'MUSE-News', 'Qwen2.5-7B-Instruct'),
    ('muse_books_qwen25_7b_instruct', 'MUSE-Books', 'Qwen2.5-7B-Instruct'),
    ('muse_books_llama2_7b', 'MUSE-Books', 'Llama-2-7b'),
]
METHODS = ['RMU', 'WGA', 'SATIMP', 'SIMNPO']
PRETTY = {'RMU': 'RMU', 'WGA': 'WGA', 'SATIMP': 'SatImp', 'SIMNPO': 'SimNPO'}
METRICS = ['forget_knowmem_ROUGE', 'forget_verbmem_ROUGE', 'retain_knowmem_ROUGE', 'extraction_strength', 'privleak']
COLS = ['dataset', 'base_model', 'method', 'selected_step', 'selection_score_best_agg', 'best_metric', 'forget_knowmem_ROUGE', 'forget_verbmem_ROUGE',
        'retain_knowmem_ROUGE', 'extraction_strength', 'privleak', 'summary_file_matches_trainer_state', 'source_trainer_state', 'source_summary_file']


def num(x):
    return '' if x is None else repr(x)


def build():
    rows = []
    for stem, dataset, model in SETTINGS:
        sel = {r['method']: r for r in csv.DictReader(open(R / f'thesis/manifests/selection/{stem}_SELECTED_MODEL_PATHS.tsv'), delimiter='\t')}
        for meth in METHODS:
            step = int(sel[meth]['model_path'].rsplit('-', 1)[1])
            ts_rel = f'thesis/manifests/trainer_states/{stem}_{meth.lower()}_checkpoint-{step}_trainer_state.json'
            sm_rel = f'thesis/manifests/muse_eval/{stem}_{meth.lower()}_checkpoint-{step}_MUSE_SUMMARY.json'
            ts = json.load(open(R / ts_rel))
            summary = json.load(open(R / sm_rel))
            entries = [h for h in ts['log_history'] if h.get('step') == step and 'eval_best_agg' in h]
            if len(entries) != 1:
                sys.exit(f'{ts_rel}: expected exactly one evaluation entry at step {step}, found {len(entries)}')
            e = entries[0]
            if ts['best_global_step'] != step or e['eval_best_agg'] != ts['best_metric'] or float(sel[meth]['best_metric']) != ts['best_metric']:
                sys.exit(f'{ts_rel}: best_metric / logged score / selection TSV disagree')
            same = all(e.get(k) == summary.get(k) for k in METRICS if k in e and k in summary)
            rows.append([dataset, model, PRETTY[meth], step, num(e['eval_best_agg']), num(ts['best_metric'])] + [num(e.get(k)) for k in METRICS]
                        + ['yes' if same else 'NO', ts_rel, sm_rel])
    return rows


def render(rows):
    import io
    buf = io.StringIO()
    w = csv.writer(buf, delimiter='\t', lineterminator='\n')
    w.writerow(COLS)
    w.writerows(rows)
    return buf.getvalue()


if __name__ == '__main__':
    text = render(build())
    out = R / 'thesis/manifests/selection/selected_checkpoint_metrics.tsv'
    if '--check' in sys.argv:
        sys.exit(0 if out.exists() and out.read_text() == text else 1)
    out.write_text(text)
    print(f'wrote {out.relative_to(R)} ({len(text.splitlines()) - 1} runs)')
