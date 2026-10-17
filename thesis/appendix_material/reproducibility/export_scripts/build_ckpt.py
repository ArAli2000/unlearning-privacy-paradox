import csv, os, glob
REPO = '/mnt/beegfs/work/elshashay/open-unlearning/'
OUT = REPO + 'thesis/appendix_material/reproducibility/model_checkpoints.tsv'
HFC = '/mnt/beegfs/work/elshashay/.cache/huggingface/'
missing = []


def ex(p):
    """returns 'yes'/'NO'/'HF-id (cached)' for a path or hub id; also records misses"""
    if not p:
        return ''
    if p.startswith('muse-bench/') or p.startswith('NousResearch/'):
        c = HFC + 'models--' + p.replace('/', '--')
        ok = os.path.isdir(c)
        if not ok:
            missing.append(p)
        return 'HF hub id; local cache ' + ('present' if ok else 'ABSENT')
    full = p if p.startswith('/') else REPO + p
    ok = os.path.exists(full)
    if not ok:
        missing.append(p)
    return 'yes' if ok else 'NO'


H = ['Dataset', 'Model', 'Condition', 'Base/Target checkpoint', 'Selected unlearned checkpoint', 'Selection manifest', 'Behavioral output path',
     'Target/checkpoint path exists', 'Behavioral outputs exist', 'Other behavioral artifacts', 'Status / notes']
rows = []


def add(ds, model, cond, target, sel, manifest, outs, other, notes):
    t_ok = ex(target)
    s_ok = ex(sel.split(' ')[0]) if sel and not sel.startswith('n/a') else ''
    o_ok = 'yes' if all(os.path.exists(REPO + o) for o in outs) else 'NO'
    if o_ok == 'NO':
        missing.extend(o for o in outs if not os.path.exists(REPO + o))
    rows.append([ds, model, cond, target, sel, manifest, ' | '.join(outs), (t_ok + ('; ' + s_ok if s_ok else '')), o_ok, other, notes])


def O(p):
    return p


METH = [('Target', 'before'), ('RMU', 'rmu'), ('WGA', 'wga'), ('SatImp', 'satimp'), ('SimNPO', 'simnpo')]
# MUSE-News Track B
T = 'saves/finetune/muse_news_qwen25_7b_instruct_target'
CK = {'rmu': 459, 'wga': 306, 'satimp': 459, 'simnpo': 459}
for c, k in METH:
    sel = 'n/a (Target)' if k == 'before' else f'saves/unlearn/muse_news_qwen25_7b_instruct_{k}/checkpoint-{CK[k]}'
    add('MUSE-News', 'Qwen2.5-7B-Instruct (Track B, canonical)', c, T, sel,
        'thesis/manifests/selection/muse_news_qwen25_7b_instruct_SELECTED_MODEL_PATHS.tsv; thesis/manifests/model_lists/muse_news_qwen25_persistbench_models.tsv',
        [f'external/PersistBench/outputs/muse_news_qwen25_selected_full/muse_news_qwen25_{k}.json',
         f'outputs/privacylens_muse_news_qwen25_selected/muse_news_qwen25_{k}/privacy_mcq_all493.json'],
        f'Gemma-3 re-judge: external/PersistBench/outputs_gemma3_judge/muse_news/muse_news_qwen25_{k}.gemma3.json',
        'Selection by best_agg (no privacy term). Tokenizer for PrivacyLens/PersistBench = the target directory.')
# MUSE-Books Qwen
T = 'saves/finetune/muse_books_qwen25_7b_instruct_target'
CK = {'rmu': 102, 'wga': 102, 'satimp': 51, 'simnpo': 51}
for c, k in METH:
    sel = 'n/a (Target)' if k == 'before' else f'saves/unlearn/muse_books_qwen25_7b_instruct_{k}/checkpoint-{CK[k]}'
    add('MUSE-Books', 'Qwen2.5-7B-Instruct (canonical)', c, T, sel,
        'thesis/manifests/selection/muse_books_qwen25_7b_instruct_SELECTED_MODEL_PATHS.tsv; thesis/manifests/model_lists/muse_books_qwen25_persistbench_models.tsv',
        [f'external/PersistBench/outputs/muse_books_qwen25_selected_full/muse_books_qwen25_{k}.json',
         f'outputs/privacylens_muse_books_qwen25_selected/muse_books_qwen25_{k}/privacy_mcq_all493.json'],
        f'Gemma-3 re-judge: external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_qwen25_{k}.gemma3.json',
        'Finetune-time MUSE evals of this target ran on the News split (config bug); Books-Qwen RMU loses all utility after ~step 153; SatImp/SimNPO selected best_agg is below the step-0 baseline.' if k != 'before' else 'Finetune-time MUSE evals ran on the News split (config bug); use unlearn step-0 log for BASE MUSE metrics.')
# MUSE-Books Llama-2
T = 'muse-bench/MUSE-Books_target'
CK = {'rmu': 51, 'wga': 357, 'satimp': 153, 'simnpo': 408}
for c, k in METH:
    sel = 'n/a (Target)' if k == 'before' else f'saves/unlearn/muse_books_llama2_7b_{k}/checkpoint-{CK[k]}'
    note = {'before': 'Official target; weights from HF hub (tokenizer NousResearch/Llama-2-7b-hf). PrivacyLens not interpretable (0-40% parseable).',
            'wga': 'WGA ckpt-357 collapsed (all forget metrics 0; all PersistBench outputs "- - - -", 0% valid) - non-evaluable for PersistBench.',
            'satimp': 'SatImp ckpt-153 did not actually forget (verbmem 0.997 / extraction 0.916 = BASE).',
            'rmu': 'PrivacyLens not interpretable.', 'simnpo': 'PrivacyLens not interpretable.'}[k]
    add('MUSE-Books', 'Llama-2-7b (official muse-bench target)', c, T, sel,
        'thesis/manifests/selection/muse_books_llama2_7b_SELECTED_MODEL_PATHS.tsv; thesis/manifests/model_lists/muse_books_llama2_persistbench_models.tsv',
        [f'external/PersistBench/outputs/muse_books_llama2_selected_full/muse_books_llama2_{k}.json',
         f'outputs/privacylens_muse_books_llama2_selected/muse_books_llama2_{k}/privacy_mcq_all493.json'],
        f'Gemma-3 re-judge: external/PersistBench/outputs_gemma3_judge/muse_books/muse_books_llama2_{k}.gemma3.json', note)
# MUSE-News Track A (superseded)
A = {'before': ('muse-bench/MUSE-News_target', 'n/a (Target)', 'muse_news_before'),
     'rmu': ('muse-bench/MUSE-News_target', 'saves/unlearn/muse_news_rmu_ckpts_bs1_gc_sbatch/checkpoint-500', 'muse_news_rmu_selected'),
     'wga': ('muse-bench/MUSE-News_target', 'saves/unlearn/muse_news_wga_ckpts_bs1_gc_sbatch/checkpoint-357', 'muse_news_wga_selected'),
     'satimp': ('muse-bench/MUSE-News_target', 'saves/unlearn/muse_news_satimp_ckpts_bs1_gc_sbatch/checkpoint-500', 'muse_news_satimp_selected'),
     'simnpo': ('muse-bench/MUSE-News_target', 'saves/unlearn/muse_news_simnpo_ckpts_bs1_gc_sbatch/checkpoint-459', 'muse_news_simnpo_selected')}
for c, k in METH:
    t, sel, lab = A[k]
    add('MUSE-News', 'Llama-2-7b (Track A, SUPERSEDED - not used in main results)', c, t, sel,
        'research_history/04_muse_track_a/manifests/muse_news_persistbench_models.tsv (manifest paths are /storage/ukp/work/...; same files under the repo saves/ tree); research_history/04_muse_track_a/manifests/openunlearning_selection/SELECTED_MODEL_PATHS.tsv',
        [f'external/PersistBench/outputs/muse_news_selected_full/{lab}.json', f'outputs/privacylens_muse_news_selected/{lab}/privacy_mcq_all493.json'],
        'none (no Gemma re-judge for Track A)',
        'Post-hoc selection (no best_agg); PrivacyLens 30-41% parseable; never carried downstream. Do not report Track A numbers in main results.')
# TOFU Qwen2.5-7B
T = 'saves/finetune/tofu_Qwen2.5-7B-Instruct_full'
TQ = {'rmu': 104, 'satimp': 104, 'simnpo': 104, 'wga': 104}
TQL = {'before': 'qwen25_7b_tofufull_before', 'rmu': 'qwen25_7b_after_rmu_from_tofufull', 'wga': 'qwen25_7b_after_wga_from_tofufull', 'satimp': 'qwen25_7b_after_satimp_from_tofufull', 'simnpo': 'qwen25_7b_after_simnpo_from_tofufull'}
for c, k in METH:
    sel = 'n/a (Target)' if k == 'before' else f'saves/unlearn/proper_qwen25_7b_{k}_from_tofufull_selectionproxy_savebest/checkpoint-{TQ[k]}'
    add('TOFU (forget10/retain90)', 'Qwen2.5-7B-Instruct (TOFU-finetuned start; stage B2)', c, T, sel,
        'thesis/docs/experimental_setup_audit/selected_checkpoints.tsv; research_history/02_model_method_scaling/manifests/qwen25_7b_persistbench_models.tsv (lists the run directory); run-dir BEST_CHECKPOINT.txt',
        [f'external/PersistBench/outputs/final_tofu_persistbench_localjudge/{TQL[k]}_localjudge.json', f'outputs/privacylens_qwen_tofufull_methods/{TQL[k]}/privacy_mcq_all493.json'],
        'none (no Gemma re-judge for TOFU)',
        'Behavioral evals loaded the run directory (top-level weights) listed in the model list; the selected checkpoint (Selection_proxy argmax) is checkpoint-104 per trainer_state best_global_step and BEST_CHECKPOINT.txt. Top-level weights were not byte-compared with the checkpoint directory.' if k != 'before' else 'TOFU-finetuned local copy of Qwen/Qwen2.5-7B-Instruct.')
# TOFU Llama-3.1-8B
T = '/mnt/beegfs/work/elshashay/.cache/huggingface/models--open-unlearning--tofu_Llama-3.1-8B-Instruct_full/snapshots/1a5c5b1a557f8c99bdadecd5168ebd03f640b00e'
TL = {'rmu': 65, 'satimp': 52, 'simnpo': 120, 'wga': 117}
TLL = {'before': 'llama31_8b_tofufull_before', 'rmu': 'llama31_8b_after_rmu_from_tofufull', 'wga': 'llama31_8b_after_wga_from_tofufull', 'satimp': 'llama31_8b_after_satimp_from_tofufull', 'simnpo': 'llama31_8b_after_simnpo_from_tofufull'}
PLL = dict(TLL, satimp='llama31_8b_after_satimp_from_tofull')  # sic: the PrivacyLens output directory has the typo "from_tofull"
for c, k in METH:
    d = 'simnpo' if k == 'simnpo' else k
    sel = 'n/a (Target)' if k == 'before' else f'saves/unlearn/proper_llama31_8b_{k}_from_tofufull_aggproxy_savebest/checkpoint-{TL[k]}'
    notes = 'open-unlearning/tofu_Llama-3.1-8B-Instruct_full (HF snapshot 1a5c5b1a557f...).' if k == 'before' else (
        'Behavioral evals loaded the run directory (top-level weights) listed in research_history/02_model_method_scaling/manifests/llama31_8b_privacylens_models.tsv; selection criterion per audit: Agg_proxy for RMU/SatImp/WGA, Selection_proxy for SimNPO. '
        + ('SatImp selected ckpt ~ start model (little forgetting). PrivacyLens output directory name contains the typo "from_tofull".' if k == 'satimp' else 'SimNPO selected checkpoint is the last step (120), close to the start model; trainer_state best_model_checkpoint records ...simnpo_from_tofufull_selectionproxy_savebest/checkpoint-120 while the directory on disk is named ...aggproxy_savebest (name mismatch, same step).' if k == 'simnpo' else ''))
    add('TOFU (forget10/retain90)', 'Llama-3.1-8B-Instruct (TOFU-finetuned start; stage B2)', c, T, sel,
        'thesis/docs/experimental_setup_audit/selected_checkpoints.tsv; research_history/02_model_method_scaling/manifests/llama31_8b_privacylens_models.tsv; research_history/02_model_method_scaling/manifests/llama31_8b_tofufull_path.txt',
        [f'external/PersistBench/outputs/final_tofu_persistbench_localjudge/{TLL[k]}_localjudge.json', f'outputs/privacylens_llama31_8b_tofufull_methods/{PLL[k]}/privacy_mcq_all493.json'],
        'none (no Gemma re-judge for TOFU)', notes)
# Full prompt robustness
for c, k in (('Target', 'before'), ('RMU', 'rmu'), ('SatImp', 'satimp'), ('SimNPO', 'simnpo')):
    sel = 'n/a (Target)' if k == 'before' else f'saves/unlearn/muse_news_qwen25_7b_instruct_{k}/checkpoint-459'
    add('MUSE-News (FULL-PROMPT robustness; sycophancy + cross-domain)', 'Qwen2.5-7B-Instruct (Track B)', c, 'saves/finetune/muse_news_qwen25_7b_instruct_target', sel,
        'thesis/manifests/model_lists/muse_news_qwen25_persistbench_models.tsv (same checkpoints as the original MUSE-News run)',
        [f'external/PersistBench/outputs/muse_news_qwen25_fullprompt_robustness/muse_news_qwen25_{k}_fullprompt.json',
         f'external/PersistBench/outputs/muse_news_qwen25_fullprompt_robustness_crossdomain/muse_news_qwen25_{k}_fullprompt_crossdomain.json'],
        'analysis: external/PersistBench/outputs/muse_news_qwen25_fullprompt_robustness{,_crossdomain}/analysis_results.json',
        'Generated 2026-10-15/16 with --max-model-len 8192, no truncation, neutral alias; WGA was not part of this robustness run.')

with open(OUT, 'w', newline='') as f:
    wr = csv.writer(f, delimiter='\t', lineterminator='\n')
    wr.writerow(H)
    for r in rows:
        assert len(r) == len(H)
        wr.writerow(r)
print(len(rows), 'rows; missing:', missing)
