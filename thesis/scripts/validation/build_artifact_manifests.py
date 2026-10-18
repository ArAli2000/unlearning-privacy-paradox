#!/usr/bin/env python3
"""Build the sanitized public artifact manifests (no usernames, no absolute paths).

Writes, next to each other in thesis/appendix_material/reproducibility/:
  artifact_manifest.tsv           every piece of evidence: tracked, external (archive), withheld, or regenerable
  artifact_manifest_external.tsv  the minimum external archive: the 40 PersistBench-derived files compute_tables.py needs

Logical roots used in the portable paths:
  REPOSITORY_ROOT              a clone of this repository
  PERSISTBENCH_ARTIFACT_ROOT   root of the extracted external archive (contains outputs/ and outputs_gemma3_judge/);
                               pass it to compute_tables.py as --artifact-root
  CHECKPOINT_STORAGE           where model checkpoints would be kept (not published)
  HIDDEN_STATE_STORAGE         where extracted hidden-state tensors would be kept (not published, regenerable)
  MUSE_EVAL_STORAGE            where the per-example MUSE_EVAL.json files would be kept (optional, not in the minimal archive)

This script needs the original cluster working tree (the files it describes are not all in Git), so it is a record of
how the manifests were made, not part of CI. Run from the repository root of the cluster working tree:
  python3 thesis/scripts/validation/build_artifact_manifests.py
"""
import csv
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
os.chdir(R)
OUTDIR = R / 'thesis/appendix_material/reproducibility'
PBX = 'external/PersistBench/'
COLS = ['logical_artifact_id', 'portable_destination', 'experiment_stage', 'size_bytes', 'sha256', 'status', 'required_for', 'source_code_or_command', 'availability', 'notes']
ARCH_COLS = ['archive_path', 'logical_artifact_id', 'size_bytes', 'sha256', 'experiment_stage', 'required_for', 'publication_status', 'contains_model_text', 'notes']
BLOCK = 'BLOCKED: PersistBench-derived; PersistBench has no licence file at the pinned commit, redistribution needs the authors\' clarification'
rows, arch = [], []


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def dsize(p):
    t = n = 0
    for dp, _, fn in os.walk(p):
        for f in fn:
            try:
                t += os.path.getsize(os.path.join(dp, f)); n += 1
            except OSError:
                pass
    return t, n


def add(aid, dest, stage, path, status, req, src, avail, notes='', hashit=True):
    p = Path(path) if path else None
    size = sha_ = ''
    if p and p.exists():
        if p.is_file():
            size = p.stat().st_size
            sha_ = sha(p) if hashit else ''
        else:
            size, n = dsize(p); notes = (notes + '; ' if notes else '') + f'directory, {n} files'
    rows.append(dict(zip(COLS, [aid, dest, stage, size, sha_, status, req, src, avail, notes])))


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout


TABLES = {'frk': 'persistbench_frk_complete.tsv', 'val': 'generation_validity_complete.tsv', 'full': 'fullprompt_robustness.tsv', 'agree': 'judge_agreement.tsv', 'robust': 'judge_robustness.tsv'}
JUDGE = {'news': 'run_persistbench_muse_news_qwen25_judge_like_tofu.sh', 'books_qwen25': 'run_persistbench_muse_books_qwen25_localjudge.sh', 'books_llama2': 'run_persistbench_muse_books_llama2_judge_like_tofu.sh'}

# ---- 1. compute_tables.py inputs (taken from the script itself)
out = sh(sys.executable, '-I', '-B', str(OUTDIR / 'export_scripts/compute_tables.py'), '--check-inputs')
inputs = [ln.split('\t')[2] for ln in out.splitlines() if ln.count('\t') >= 3]
assert len(inputs) == 46, len(inputs)
for rel in inputs:
    if not rel.startswith(PBX):
        continue
    sub = rel[len(PBX):]
    name = os.path.basename(sub)
    if 'outputs_gemma3_judge' in sub:
        stage, req, srcc = 'Judge robustness (Gemma-3-12B re-judging, MUSE-News)', 'judge_agreement.tsv (Qwen vs Gemma pairing of the same responses)', 'thesis/analysis/judge_robustness/run_gemma3_judge_full.sbatch (gemma_judge.py)'
        notes = 'provenance block holds an institutional shared model path (no username)'
        mt = 'yes'
    elif 'fullprompt' in sub and name == 'analysis_results.json':
        stage, req, srcc = 'Full-prompt robustness', 'fullprompt_robustness.tsv (cross-check asserted by compute_tables.py)', 'thesis/scripts/persistbench_fullprompt_robustness/analyze_fullprompt.py, analyze_fullprompt_crossdomain.py'
        notes = 'derived counts and rates'; mt = 'no'
    elif 'fullprompt' in sub:
        stage, req, srcc = 'Full-prompt robustness (MUSE-News Qwen2.5)', TABLES['full'], 'thesis/scripts/persistbench_fullprompt_robustness/run_fullprompt_robustness.sh, run_fullprompt_robustness_crossdomain.sh; thesis/scripts/persistbench_fullprompt_complete/run_fullprompt_complete.sbatch'
        notes = ''; mt = 'yes'
    elif 'final_tofu' in sub:
        stage, req = 'PersistBench generation and judging (TOFU)', f"{TABLES['frk']}; {TABLES['val']}"
        srcc = 'archived TOFU launchers (thesis_archive.zip: research_history/02_model_method_scaling/scripts/, 05_wmdp_side_investigation/scripts/); judge: thesis/scripts/persistbench/run_local_judge_server_penelope.sh'
        notes = 'T=1.0 sampled generations; raw prompts were not stored'; mt = 'yes'
    else:
        key = 'news' if 'muse_news' in sub else ('books_llama2' if 'llama2' in sub else 'books_qwen25')
        gen = {'news': 'run_persistbench_muse_news_qwen25_selected.sh', 'books_qwen25': 'run_persistbench_muse_books_qwen25_selected.sh', 'books_llama2': 'run_persistbench_muse_books_llama2_selected.sh'}[key]
        stage = 'PersistBench generation and judging (MUSE)'
        req = f"{TABLES['frk']}; {TABLES['val']}" + (f"; {TABLES['full']}; {TABLES['agree']}" if key == 'news' else '')
        srcc = f'generation: thesis/scripts/persistbench/{gen}; judging: thesis/scripts/persistbench/run_local_judge_server_penelope.sh + {JUDGE[key]}'
        notes = 'original generation settings are documented in thesis/docs/generation_provenance.md'; mt = 'yes'
    aid = 'persistbench:' + sub[:-5]
    add(aid, f'PERSISTBENCH_ARTIFACT_ROOT/{sub}', stage, R / rel, 'external', req, srcc, 'available on the original cluster; publication blocked (licence)', notes + ('; ' if notes else '') + BLOCK)
    arch.append(dict(zip(ARCH_COLS, [sub, aid, rows[-1]['size_bytes'], rows[-1]['sha256'], stage, req, BLOCK.split(':')[0], mt, notes])))
assert len(arch) == 40

# ---- 2. tracked evidence (original files unless noted)
def tracked(aid, rel, stage, req, srcc, notes=''):
    p = R / rel
    add(aid, f'REPOSITORY_ROOT/{rel}', stage, p, 'tracked', req, srcc, 'in the repository' if p.exists() else 'MISSING', notes)

for f in sorted((R / 'thesis/manifests/trainer_states').glob('*.json')):
    tracked('trainer_state:' + f.name[:-len('_trainer_state.json')], str(f.relative_to(R)), 'MUSE checkpoint selection', 'checkpoint-selection evidence; selected_checkpoint_metrics.tsv', 'trainer_state.json of the selected checkpoint, copied unchanged; thesis/scripts/muse_*/run_*_unlearn_*.sh', 'original bytes; no personal paths (checked)')
for f in sorted((R / 'thesis/manifests/muse_eval').glob('*.json')):
    tracked('muse_summary:' + f.name[:-len('_MUSE_SUMMARY.json')], str(f.relative_to(R)), 'standard MUSE evaluation', 'selected_checkpoint_metrics.tsv', 'evals/MUSE_SUMMARY.json of the checkpoint, copied unchanged (src/eval.py experiment=eval/muse/default)',
            'BASE of Llama-2 MUSE-Books; identity from the recorded evaluation config, see thesis/manifests/muse_eval/README.md' if 'before_official' in f.name else 'original bytes')
tracked('table:selected_checkpoint_metrics', 'thesis/manifests/selection/selected_checkpoint_metrics.tsv', 'MUSE checkpoint selection', '12-run metrics table', 'thesis/scripts/validation/build_selected_checkpoint_metrics.py', 'derived table; values copied unchanged')
for f in sorted((R / 'thesis/results/privacylens').rglob('privacy_mcq_all493.json')):
    tracked('privacylens:' + str(f.parent.relative_to(R / 'thesis/results/privacylens')), str(f.relative_to(R)), 'PrivacyLens evaluation', 'PrivacyLens accuracy/leakage tables', 'thesis/scripts/privacylens/run_privacylens_*_selected.sh', 'original bytes; per-item A/B answers only (no benchmark text)')
tracked('table:privacylens_selected_runs_summary', 'thesis/results/privacylens/privacylens_selected_runs_summary.tsv', 'PrivacyLens evaluation', 'summary of the 25 in-scope runs', 'thesis/scripts/validation/build_privacylens_summary.py', 'derived; 6 rows derived from originals whose absolute paths were normalised (those originals are withheld)')
for rel, aid in [('thesis/appendix_material/reproducibility/stored_inputs/persistbench_all_methods_all_corpora.csv', 'stored_input:persistbench_all_methods_all_corpora'),
                 ('thesis/appendix_material/reproducibility/stored_inputs/persistbench_fr_at_k_muse_books_qwen25.csv', 'stored_input:persistbench_fr_at_k_muse_books_qwen25'),
                 ('thesis/analysis/judge_robustness/qwen_vs_gemma_frk.json', 'stored_result:qwen_vs_gemma_frk'),
                 ('thesis/analysis/judge_robustness/qwen_vs_gemma_agreement.json', 'stored_result:qwen_vs_gemma_agreement'),
                 ('mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_category_comparison_validated.csv', 'stored_result:muse_news_category_comparison_validated')]:
    tracked(aid, rel, 'FR@K cross-check inputs of compute_tables.py' if 'stored_input' in aid else 'Judge robustness / FR@K', 'compute_tables.py', 'see stored_inputs/README.md' if 'stored_input' in aid else 'thesis/analysis/judge_robustness/qwen_vs_gemma_analysis.py' if 'qwen_vs_gemma' in aid else 'tracked table', 'original bytes')
for rel in ['thesis/analysis/judge_robustness/gemma_judge.py', 'thesis/analysis/judge_robustness/qwen_vs_gemma_analysis.py', 'thesis/analysis/judge_robustness/run_gemma3_judge_full.sbatch', 'thesis/scripts/validation/create_persistbench_validity_summary_with_muse.py',
            'thesis/appendix_material/reproducibility/export_scripts/compute_tables.py']:
    tracked('code:' + os.path.basename(rel), rel, 'code', 'regeneration of tables', 'source file', 'portability edits documented in thesis/appendix_material/README.md' if 'gemma' in rel else '')
for t in TABLES.values():
    tracked('table:' + t[:-4], f'thesis/appendix_material/tables/{t}', 'appendix tables', 'reported tables', 'thesis/appendix_material/reproducibility/export_scripts/compute_tables.py [--artifact-root PATH]', 'target of byte-identical regeneration')

# ---- 3. external, not in the minimal archive (optional, withheld, or regenerable)
for f in sorted(Path('saves/unlearn').glob('*/checkpoint-*/evals/MUSE_EVAL.json')):
    d = f.parts[2]
    if not re.match(r'muse_(news|books)_(qwen25_7b_instruct|llama2_7b)_(rmu|wga|satimp|simnpo)$', d):
        continue
    sel = {r['model_path'] for stem in ('muse_news_qwen25_7b_instruct', 'muse_books_qwen25_7b_instruct', 'muse_books_llama2_7b') for r in csv.DictReader(open(R / f'thesis/manifests/selection/{stem}_SELECTED_MODEL_PATHS.tsv'), delimiter='\t')}
    if str(f.parent.parent) not in sel:
        continue
    add('muse_eval_full:' + d + ':' + f.parts[3], f'MUSE_EVAL_STORAGE/{d}_{f.parts[3]}_MUSE_EVAL.json', 'standard MUSE evaluation', f, 'external-optional',
        'per-example MUSE evaluation; not needed for any table (selected_checkpoint_metrics.tsv holds the metrics)', 'evals/MUSE_EVAL.json of the selected checkpoint', 'available on the original cluster; not in the minimal archive',
        'MUSE benchmark text and model generations; check MUSE redistribution terms')
for f in sorted(Path('external/PersistBench/outputs_gemma3_judge/muse_books').glob('*.json')):
    add('gemma_rejudge:' + f.stem, f'PERSISTBENCH_ARTIFACT_ROOT/outputs_gemma3_judge/muse_books/{f.name}', 'Judge robustness (Gemma-3-12B, MUSE-Books)', f, 'external-optional', 'only to re-derive qwen_vs_gemma_*.json, which are tracked',
        'thesis/analysis/judge_robustness/run_gemma3_judge_full.sbatch', 'available on the original cluster; not in the minimal archive', BLOCK)
for rel in ['outputs/privacylens_qwen_tofufull_methods/%s/privacy_mcq_all493.json' % l for l in ('qwen25_7b_tofufull_before', 'qwen25_7b_after_rmu_from_tofufull', 'qwen25_7b_after_wga_from_tofufull', 'qwen25_7b_after_satimp_from_tofufull', 'qwen25_7b_after_simnpo_from_tofufull')] + ['outputs/privacylens_llama31_8b_tofufull_methods/llama31_8b_tofufull_before/privacy_mcq_all493.json']:
    add('privacylens_withheld:' + rel.split('/')[1] + '/' + rel.split('/')[2], 'withheld (contains absolute cluster paths)', 'PrivacyLens evaluation (TOFU)', rel, 'withheld', 'summary row derived in privacylens_selected_runs_summary.tsv', 'thesis/scripts/validation/build_privacylens_summary.py', 'available on the original cluster; not published as is',
        'original file embeds absolute cluster paths in its meta block; the tracked summary row has them normalised')
logs = sorted(l for l in set(re.findall(r'logs/[A-Za-z0-9_.\-]+\.(?:log|out|err)', ''.join(open(f, errors='ignore').read() for f in sh('git', 'ls-files').split('\n') if f.endswith(('.md', '.json', '.tsv', '.csv')) and not f.startswith('external')))) if os.path.exists(l))
tot = sum(os.path.getsize(l) for l in logs)
rows.append(dict(zip(COLS, [f'provenance_logs:{len(logs)}_files', 'withheld', 'Generation provenance', tot, '', 'withheld', 'evidence behind thesis/docs/generation_provenance.md and manifests/provenance/', 'vLLM and job logs',
                            'available on the original cluster; not published', 'logs embed usernames and absolute cluster paths; the tracked documents quote the relevant lines (repetition penalty, max_tokens, truncation)'])))
for d in sorted(Path('mechanistic').rglob('representations')):
    add('hidden_states:' + str(d), f'HIDDEN_STATE_STORAGE/{d}', 'Mechanistic analysis', d, 'regenerable', 'analyze_* scripts that read tensors', 'mechanistic extract_* scripts (see mechanistic/README.md, script_map.tsv)', 'available on the original cluster; not published', 'regenerable from checkpoints and generations', hashit=False)
for d in sorted(Path('mechanistic/outputs').iterdir()):
    if d.is_dir():
        add('mechanistic_output:' + d.name, f'HIDDEN_STATE_STORAGE/{d}', 'Mechanistic analysis', d, 'regenerable', 'mechanistic figures and intermediate tables', 'mechanistic analysis scripts', 'available on the original cluster; not published', 'regenerable; final tables are tracked under mechanistic/**/analysis', hashit=False)
sel_ck = set()
for stem in ('muse_news_qwen25_7b_instruct', 'muse_books_qwen25_7b_instruct', 'muse_books_llama2_7b'):
    for r in csv.DictReader(open(R / f'thesis/manifests/selection/{stem}_SELECTED_MODEL_PATHS.tsv'), delimiter='\t'):
        if not r['model_path'].startswith('muse-bench'):
            sel_ck.add(r['model_path'])
for r in csv.DictReader(open(R / 'thesis/analysis/final_thesis_handoff_20261016/tofu_weight_provenance.tsv'), delimiter='\t'):
    p = r['selected_checkpoint_path']
    if p and not p.startswith('n/a'):
        sel_ck.add(p.split('open-unlearning/', 1)[1] if 'open-unlearning/' in p else p)
sel_ck.add('saves/finetune/tofu_Qwen2.5-7B-Instruct_full')
for p in sorted(sel_ck):
    add('checkpoint:' + p, f'CHECKPOINT_STORAGE/{p}', 'Training / unlearning', p, 'external', 'every model evaluation and mechanistic analysis of this condition', 'thesis/scripts/muse_*/run_*.sh (MUSE); archived launchers (TOFU)',
        'available on the original cluster; not published (size, base-model licences)', 'provenance only: base model, launcher, trainer_state, best_metric; SHA-256 of weight shards not computed', hashit=False)
add('checkpoint:muse-bench/MUSE-Books_target', 'public Hugging Face model muse-bench/MUSE-Books_target (not stored)', 'Target model (Llama-2 MUSE-Books BASE)', None, 'external', 'BASE condition of Llama-2 MUSE-Books', 'downloaded by the launchers',
    'public; revision not recorded', 'Llama 2 Community License; published by the MUSE authors', hashit=False)

def w(path, cols, data):
    with open(path, 'w', newline='') as f:
        wr = csv.writer(f, delimiter='\t', lineterminator='\n')
        wr.writerow(cols)
        for r in data:
            wr.writerow([str(r[c]).replace('\t', ' ').replace('\n', ' ') for c in cols])


w(OUTDIR / 'artifact_manifest.tsv', COLS, rows)
w(OUTDIR / 'artifact_manifest_external.tsv', ARCH_COLS, arch)
print(len(rows), 'manifest rows;', len(arch), 'archive files;', sum(int(a['size_bytes']) for a in arch), 'archive bytes')
