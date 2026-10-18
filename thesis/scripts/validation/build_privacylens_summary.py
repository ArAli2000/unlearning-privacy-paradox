#!/usr/bin/env python3
"""Build thesis/results/privacylens/privacylens_selected_runs_summary.tsv, one row per in-scope PrivacyLens run (25 runs).

In-scope runs: MUSE-News Qwen2.5, MUSE-Books Qwen2.5, MUSE-Books Llama-2, TOFU Qwen2.5-7B and TOFU Llama-3.1-8B (BASE and the four methods each).
Fields are copied from each run's `meta` block; nothing is recomputed. Absolute paths in `model_path` are normalised
(everything up to and including 'open-unlearning/' removed; a Hugging Face cache path is reduced to 'hf-cache/<path after .cache/huggingface/>').

Sources, in this order for each run:
  1. the tracked original  thesis/results/privacylens/<group>/<label>/privacy_mcq_all493.json   (no personal paths; byte-identical to the cluster file)
  2. with --cluster-outputs DIR: DIR/<group>/<label>/privacy_mcq_all493.json. Used for the 6 runs whose original files contain absolute cluster paths;
     those originals are not tracked, so their row is marked 'derived (paths normalised)'.
A run found in neither source stops the script.

  python3 build_privacylens_summary.py [--cluster-outputs outputs] [--check]
"""
import csv
import io
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
TRACKED = R / 'thesis/results/privacylens'
GROUPS = {
    'privacylens_muse_news_qwen25_selected': ('MUSE-News', 'Qwen2.5-7B-Instruct', ['muse_news_qwen25_%s' % k for k in ('before', 'rmu', 'wga', 'satimp', 'simnpo')]),
    'privacylens_muse_books_qwen25_selected': ('MUSE-Books', 'Qwen2.5-7B-Instruct', ['muse_books_qwen25_%s' % k for k in ('before', 'rmu', 'wga', 'satimp', 'simnpo')]),
    'privacylens_muse_books_llama2_selected': ('MUSE-Books', 'Llama-2-7b', ['muse_books_llama2_%s' % k for k in ('before', 'rmu', 'wga', 'satimp', 'simnpo')]),
    'privacylens_qwen_tofufull_methods': ('TOFU', 'Qwen2.5-7B-Instruct', ['qwen25_7b_tofufull_before'] + ['qwen25_7b_after_%s_from_tofufull' % k for k in ('rmu', 'wga', 'satimp', 'simnpo')]),
    'privacylens_llama31_8b_tofufull_methods': ('TOFU', 'Llama-3.1-8B-Instruct', ['llama31_8b_tofufull_before', 'llama31_8b_after_rmu_from_tofufull', 'llama31_8b_after_wga_from_tofufull',
                                                                                'llama31_8b_after_satimp_from_tofull', 'llama31_8b_after_simnpo_from_tofufull']),
}
FIELDS = ['prompt_type', 'total', 'valid_responses', 'privacy_aware_B', 'non_privacy_aware_A', 'unknown', 'privacy_norm_awareness_accuracy', 'leakage_proxy']
COLS = ['dataset', 'base_model', 'group', 'model_label', 'model_path'] + FIELDS + ['source']
ABS = re.compile(rb'/mnt/|/storage/|/home/|/nfs/')


def norm(p):
    if '.cache/huggingface/' in p:
        return 'hf-cache/' + p.split('.cache/huggingface/', 1)[1]
    return p.split('open-unlearning/', 1)[1] if p.startswith('/') and 'open-unlearning/' in p else p


def build(cluster):
    rows = []
    for group, (dataset, model, labels) in GROUPS.items():
        for label in labels:
            rel = Path(group) / label / 'privacy_mcq_all493.json'
            src = None
            if (TRACKED / rel).exists():
                src, kind = TRACKED / rel, 'tracked original'
            elif cluster and (Path(cluster) / rel).exists():
                src, kind = Path(cluster) / rel, 'derived (paths normalised)'
            if src is None:
                sys.exit(f'no source for {rel} (tracked copy missing; pass --cluster-outputs DIR)')
            raw = src.read_bytes()
            if kind == 'tracked original' and ABS.search(raw):
                sys.exit(f'{src}: tracked original contains an absolute path')
            m = json.loads(raw)['meta']
            rows.append([dataset, model, group, label, norm(m['model_path'])] + [m[f] for f in FIELDS] + [kind])
    return rows


def render(rows):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter='\t', lineterminator='\n')
    w.writerow(COLS)
    w.writerows(rows)
    return buf.getvalue()


if __name__ == '__main__':
    cluster = sys.argv[sys.argv.index('--cluster-outputs') + 1] if '--cluster-outputs' in sys.argv else None
    text = render(build(cluster))
    out = TRACKED / 'privacylens_selected_runs_summary.tsv'
    if '--check' in sys.argv:
        sys.exit(0 if out.exists() and out.read_text() == text else 1)
    out.write_text(text)
    print(f'wrote {out.relative_to(R)} ({len(text.splitlines()) - 1} runs)')
