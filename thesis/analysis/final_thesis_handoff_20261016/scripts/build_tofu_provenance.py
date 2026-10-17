#!/usr/bin/env python3
"""TOFU weight provenance: compare the weights the behavioural evaluations loaded (top-level run directory) with the selected checkpoint-N.
READ-ONLY: only reads the hash database written by tofu_hash_dirs.py and existing logs/metadata; writes only into thesis/analysis/final_thesis_handoff_20261016/."""
import csv, glob, json, os, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
R = Path('/mnt/beegfs/work/elshashay/open-unlearning')
H = R / 'thesis/analysis/final_thesis_handoff_20261016'
DB = json.load(open(H / 'scripts/_tofu_hashes.json'))
SU = R / 'saves/unlearn'
WEIGHT = re.compile(r'^model.*\.safetensors$')
CFGSET = ['config.json', 'generation_config.json', 'model.safetensors.index.json', 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json', 'vocab.json', 'merges.txt', 'added_tokens.json']
RUNS = []
for fam, model, suffix, sel in (('qwen25_7b', 'Qwen2.5-7B-Instruct (TOFU, forget10/retain90, B2)', '_from_tofufull_selectionproxy_savebest', {'rmu': 104, 'wga': 104, 'satimp': 104, 'simnpo': 104}),
                                ('llama31_8b', 'Llama-3.1-8B-Instruct (TOFU, forget10/retain90, B2)', '_from_tofufull_aggproxy_savebest', {'rmu': 65, 'wga': 117, 'satimp': 52, 'simnpo': 120})):
    for m in ('rmu', 'wga', 'satimp', 'simnpo'):
        RUNS.append((fam, model, m, f'proper_{fam}_{m}{suffix}', sel[m]))
CONDN = {'rmu': 'RMU', 'wga': 'WGA', 'satimp': 'SatImp', 'simnpo': 'SimNPO'}


def rec(d, f): return DB.get(str(Path(d).resolve()), {}).get(f)
def listing(d): return DB.get(str(Path(d).resolve()), {})


def compare(top, ck):
    T, C = listing(top), listing(ck)
    wt = sorted(f for f in T if WEIGHT.match(f)); wc = sorted(f for f in C if WEIGHT.match(f))
    same_names = wt == wc and len(wt) > 0
    wid = same_names and all(T[f]['sha256'] == C[f]['sha256'] for f in wt)
    n_eq = sum(1 for f in wt if f in C and T[f]['sha256'] == C[f]['sha256'])
    cfg = {f: (T[f]['sha256'] == C[f]['sha256']) for f in CFGSET if f in T and f in C}
    cfg_missing = [f for f in CFGSET if (f in T) != (f in C)]
    return dict(weights=wt, weights_ck=wc, weights_identical=wid, n_weight_equal=n_eq, cfg=cfg, cfg_missing=cfg_missing, cfg_identical=all(cfg.values()) and not [f for f in cfg_missing if f != 'added_tokens.json'] and len(cfg) > 0)


def pl_meta_path(fam, m):
    d = {'qwen25_7b': 'privacylens_qwen_tofufull_methods', 'llama31_8b': 'privacylens_llama31_8b_tofufull_methods'}[fam]
    cands = sorted(glob.glob(str(R / 'outputs' / d / f'{fam}_after_{m}_from_to*' / 'privacy_mcq_all493.json')))
    j = json.load(open(cands[0])); return str(cands[0].replace(str(R) + '/', '')), j['meta'].get('model_path')


def pb_log_path(fam, m):
    logs = sorted(glob.glob(str(R / 'logs' / f'vllm_{fam}_after_{m}_from_tofufull_*.log')))
    mm = re.search(r"model='([^']+)'", open(logs[-1], errors='ignore').read(20000)); return logs[-1].replace(str(R) + '/', ''), mm.group(1)


rows = []; FACTS = []
for fam, model, m, run, step in RUNS:
    top = SU / run; ck = top / f'checkpoint-{step}'
    cmpr = compare(top, ck)
    ts = json.load(open(top / 'trainer_state.json'))
    ts_ck = json.load(open(ck / 'trainer_state.json')) if (ck / 'trainer_state.json').exists() else {}
    best = (top / 'BEST_CHECKPOINT.txt').read_text().strip() if (top / 'BEST_CHECKPOINT.txt').exists() else ''
    others = {}
    for c in sorted(top.glob('checkpoint-*'), key=lambda p: int(p.name.split('-')[1])):
        if c == ck: continue
        on_disk = any(WEIGHT.match(x) for x in os.listdir(c))
        cc = compare(top, c) if listing(c) else ('NOT_HASHED' if on_disk else None)
        others[c.name] = cc
    pbn, pbp = pb_log_path(fam, m); pln, plp = pl_meta_path(fam, m)
    FACTS.append(dict(model=model, fam=fam, m=m, run=run, step=step, cmp=cmpr, ts_best=ts.get('best_model_checkpoint'), ts_step=ts.get('global_step'), ts_best_step=ts.get('best_global_step'), best_txt=best, others=others, pb=(pbn, pbp), pl=(pln, plp),
                      mtimes=(rec(top, 'model-00001-of-00004.safetensors') or {}).get('mtime'), ck_mtime=(rec(ck, 'model-00001-of-00004.safetensors') or {}).get('mtime')))

# ---- table rows: one row per (benchmark, condition)
def loaded_kind(p, top, ck):
    q = str((R / p).resolve()) if not p.startswith('/') else str(Path(p).resolve())
    return 'top-level run directory' if q == str(top.resolve()) else ('selected checkpoint directory' if q == str(ck.resolve()) else 'other: ' + q)


HDR = ['benchmark/model', 'condition', 'behavioural_evaluation_model_path', 'evaluation_path_evidence', 'what_was_loaded', 'selected_checkpoint_path', 'selected_checkpoint_step', 'selection_record', 'weight_filenames',
       'weights_hashes_identical (top-level vs selected checkpoint)', 'config_and_tokenizer_identical', 'weight_shards_equal (n/total)', 'top_level_weights_equal_to_other_checkpoints', 'top_level_represents', 'conclusion']
out = []
for F in FACTS:
    fam, m, run, step, model = F['fam'], F['m'], F['run'], F['step'], F['model']; top = SU / run; ck = top / f'checkpoint-{step}'; c = F['cmp']
    ident = c['weights_identical']
    othn = '; '.join(f"{k}: " + ('not hashed (not required: top-level already byte-identical to the selected checkpoint)' if v == 'NOT_HASHED' else ('identical' if (v and v['weights_identical']) else ('not byte-identical (SHA-256), shards equal %d/%d' % (v['n_weight_equal'], len(v['weights'])) if v else 'no weight files on disk (pruned)'))) for k, v in F['others'].items()) or 'no other checkpoint directory'
    if ident:
        rep = f'checkpoint-{step} (byte-identical weights)'; cfgtxt = 'yes' if c['cfg_identical'] else 'no'
    else:
        rep = 'NOT checkpoint-%d; see conclusion' % step; cfgtxt = 'yes' if c['cfg_identical'] else 'no'
    ses = f"selected checkpoint step {step}; top-level trainer_state: global_step {F['ts_step']}, best_global_step {F['ts_best_step']}, best_model_checkpoint {F['ts_best']}" + (f"; BEST_CHECKPOINT.txt -> {F['best_txt']}" if F['best_txt'] else '')
    model_label = model
    for bench, (srcname, path) in (('PersistBench', F['pb']), ('PrivacyLens', F['pl'])):
        kind = loaded_kind(path, top, ck)
        if ident and kind == 'top-level run directory':
            concl = f'Evaluation loaded the top-level run directory; its {len(c["weights"])} weight shards are byte-identical (SHA-256) to those of the selected checkpoint-{step}, so the evaluated weights ARE the selected checkpoint.'
        elif ident and kind == 'selected checkpoint directory':
            concl = f'Evaluation loaded checkpoint-{step} directly: the selected checkpoint.'
        elif not ident and kind == 'top-level run directory':
            concl = 'Evaluation loaded the top-level run directory whose weights are NOT byte-identical to the selected checkpoint (see top_level_weights_equal_to_other_checkpoints / notes).'
        else:
            concl = 'Evaluation loaded ' + kind + '; weights not byte-identical to the selected checkpoint.' if not ident else 'see notes'
        out.append([f'{bench} / {model_label}', CONDN[m], path, srcname, kind, str(ck.relative_to(R)), step, 'thesis/docs/experimental_setup_audit/selected_checkpoints.tsv; run-dir trainer_state best_model_checkpoint' + (' ; BEST_CHECKPOINT.txt' if F['best_txt'] else ''),
                    ','.join(c['weights']), 'yes' if ident else 'no', cfgtxt, f"{c['n_weight_equal']}/{len(c['weights'])}", othn, rep, concl])
# Targets (start models): no selected checkpoint
for fam, model, tgt, plpath in (('qwen25_7b', 'Qwen2.5-7B-Instruct (TOFU, forget10/retain90, B2)', 'saves/finetune/tofu_Qwen2.5-7B-Instruct_full', None), ('llama31_8b', 'Llama-3.1-8B-Instruct (TOFU, forget10/retain90, B2)', None, None)):
    pbl = sorted(glob.glob(str(R / 'logs' / f'vllm_{fam}_tofufull_before_*.log')))[-1]
    pbp = re.search(r"model='([^']+)'", open(pbl, errors='ignore').read(20000)).group(1)
    d = {'qwen25_7b': 'privacylens_qwen_tofufull_methods', 'llama31_8b': 'privacylens_llama31_8b_tofufull_methods'}[fam]
    plf = sorted(glob.glob(str(R / 'outputs' / d / f'{fam}_tofufull_before' / 'privacy_mcq_all493.json')))[0]; plp = json.load(open(plf))['meta']['model_path']
    for bench, srcname, path in (('PersistBench', pbl.replace(str(R) + '/', ''), pbp), ('PrivacyLens', plf.replace(str(R) + '/', ''), plp)):
        out.append([f'{bench} / {model}', 'Target', path, srcname, 'start model directory (no checkpoint selection)', 'n/a', 'n/a', 'n/a (Target is the TOFU-finetuned start model, not an unlearning checkpoint)', 'not compared', 'n/a', 'n/a', 'n/a', 'n/a', 'start model', 'Not applicable: the Target condition has no selected checkpoint; the evaluated path is the recorded Target path.'])
with open(H / 'tofu_weight_provenance.tsv', 'w', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerow(HDR)
    for r in out: assert len(r) == len(HDR), r; w.writerow(r)
json.dump(FACTS, open(H / 'scripts/_tofu_facts.json', 'w'), indent=1, default=str)
print(len(out), 'rows'); print('weights identical per run:', {(F['fam'], F['m']): F['cmp']['weights_identical'] for F in FACTS})
print('config identical per run:', {(F['fam'], F['m']): F['cmp']['cfg_identical'] for F in FACTS})
