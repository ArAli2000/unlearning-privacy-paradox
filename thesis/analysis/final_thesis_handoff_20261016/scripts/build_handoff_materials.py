#!/usr/bin/env python3
"""Final thesis data handoff, part 2: prompt inventory + copies, generation configs, checkpoints, LaTeX tables, THESIS_FACTS.md, integrity file.
READ-ONLY on every experimental artifact. Writes only into thesis/analysis/final_thesis_handoff_20261016/ and (copies) thesis/final_appendix_material/prompts/.
Run build_handoff_data.py first (it writes scripts/_state.pkl)."""
import ast, csv, hashlib, json, os, pickle, re, shutil, statistics, sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
R = Path('/mnt/beegfs/work/elshashay/open-unlearning')
H = R / 'thesis/analysis/final_thesis_handoff_20261016'
FA = R / 'thesis/analysis/muse_qwen_fullprompt_complete_20261016'
TA = R / 'thesis/analysis/truncated_replication_20261016_v2'
AM = R / 'thesis/appendix_material'
S = pickle.load(open(H / 'scripts/_state.pkl', 'rb'))
MASTER, FRT, DELT, PT, SAT, SC, CMP, INV, AGREE, OFFDIFF, V2HASH, OFR, RFR = (S[k] for k in ('MASTER', 'FRT', 'DELT', 'PT', 'SAT', 'SC', 'CMP', 'INV', 'agree', 'offdiff', 'V2HASH', 'OFR', 'RFR'))
CHECKS = [tuple(c) for c in json.load(open(H / 'scripts/_checks_part1.json'))]
DSL = ['MUSE-News', 'MUSE-Books']; CONDS = ['Target', 'RMU', 'WGA', 'SatImp', 'SimNPO']; UNL = CONDS[1:]; CATS = ['cross_domain', 'sycophancy', 'beneficial_memory']
CATN = {'cross_domain': 'cross-domain', 'sycophancy': 'sycophancy', 'beneficial_memory': 'beneficial memory'}


def chk(name, ok, detail=''):
    CHECKS.append((name, bool(ok), detail)); print(('PASS ' if ok else 'FAIL ') + name + (f'  [{detail}]' if detail else ''))


def rtsv(p): return list(csv.DictReader(open(p), delimiter='\t'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def tsv(path, header, rows):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerow(header)
        for r in rows: assert len(r) == len(header), (path, len(r), len(header), r); w.writerow(r)
def f2(x): return 'NA' if x is None else f'{float(x):.2f}'
def pp(x): return 'NA' if x is None else ('0.00' if abs(float(x)) < 5e-13 else f'{float(x):+.2f}')
def pfmt(p): return '< 0.0001' if p < 1e-4 else f'{p:.4f}'


# =================================================================================================== 6. prompt inventory + copies
SRC = AM / 'prompts'; DST = R / 'thesis/final_appendix_material/prompts'
DST.mkdir(parents=True, exist_ok=True)
INVENT = [
    ('privacylens_prompt_exact.txt', 'exact', 'PrivacyLens', 'Verbatim source of construct_prompt (+ helpers, format_chat_prompt) from thesis/scripts/privacylens/eval_privacylens_mcq_local.py; rendering of the `naive` multiple-choice prompt with placeholders; chat-template wrappers (Qwen, Llama-3.1; Llama-2 = none); header lists system message, template and truncation facts.',
     'Appendix: exact PrivacyLens prompt (referenced from Chapter 3, PrivacyLens evaluation / prompt subsection)'),
    ('privacylens_prompt_schematic.txt', 'schematic', 'PrivacyLens', 'Concise placeholder form of the PrivacyLens naive multiple-choice prompt (single user message).', 'Chapter 3: PrivacyLens prompt (inline listing)'),
    ('persistbench_generator_exact.txt', 'exact', 'PersistBench generation', 'Verbatim GENERATOR_SYSTEM_PROMPT (external/PersistBench/src/benchmark/prompts.py, lines 7-278) plus verbatim build_generation_prompt / formatted_memories source; header documents {model_name} (served-model alias), {memories}, {query}, message passing, chat templates, original truncation and full-prompt behaviour (header text names the News neutral alias muse_news_qwen25; Books full-prompt used muse_books_qwen25).',
     'Appendix: exact PersistBench generation prompt (referenced from Chapter 3, PersistBench generation subsection)'),
    ('persistbench_generator_schematic.txt', 'schematic', 'PersistBench generation', '[system] persona ... <memories>{memories}</memories> [user] {query} plus the same header facts.', 'Chapter 3: PersistBench generation input (inline listing)'),
    ('judge_cross_domain_exact.txt', 'exact', 'PersistBench judge', 'Verbatim JUDGE_SYSTEM_PROMPT_SINGLE_CROSS_DOMAIN rubric.', 'Appendix: cross-domain judge prompt/rubric (referenced from Chapter 3, judging subsection)'),
    ('judge_sycophancy_exact.txt', 'exact', 'PersistBench judge', 'Verbatim JUDGE_SYSTEM_PROMPT_SINGLE_SYCOPHANCY rubric.', 'Appendix: sycophancy judge prompt/rubric (referenced from Chapter 3, judging subsection)'),
    ('judge_beneficial_memory_exact.txt', 'exact', 'PersistBench judge', 'Verbatim rubric constant JUDGE_SYSTEM_PROMPT_SINGLE_POSITIVE_MEMORY (the benchmark\'s internal name for beneficial memory usage).', 'Appendix: beneficial-memory judge prompt/rubric (referenced from Chapter 3, judging subsection)'),
    ('judge_input_schematic.txt', 'schematic', 'PersistBench judge', '<memories>/<query>/<response> layout, required JSON output, strict-JSON suffix, and the role layout of the Qwen vs Gemma judge messages.', 'Chapter 3: judge input and output format (inline listing; includes Qwen/Gemma role layout)'),
]
src = ast.parse((R / 'thesis/scripts/persistbench_fullprompt_robustness/pb_src/benchmark/prompts.py').read_text()); CONST = {}
for n in src.body:
    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str): CONST[n.targets[0].id] = n.value.value
EXACTNESS = {'persistbench_generator_exact.txt': 'GENERATOR_SYSTEM_PROMPT', 'judge_cross_domain_exact.txt': 'JUDGE_SYSTEM_PROMPT_SINGLE_CROSS_DOMAIN', 'judge_sycophancy_exact.txt': 'JUDGE_SYSTEM_PROMPT_SINGLE_SYCOPHANCY', 'judge_beneficial_memory_exact.txt': 'JUDGE_SYSTEM_PROMPT_SINGLE_POSITIVE_MEMORY'}
pl_src = ast.parse((R / 'thesis/scripts/privacylens/eval_privacylens_mcq_local.py').read_text())
pl_text = (R / 'thesis/scripts/privacylens/eval_privacylens_mcq_local.py').read_text()
fn = [n for n in pl_src.body if isinstance(n, ast.FunctionDef) and n.name == 'construct_prompt'][0]
pl_fn = ast.get_source_segment(pl_text, fn)
rows = []; allid = True
for fname, kind, topic, content, ref in INVENT:
    s, d = SRC / fname, DST / fname
    if d.exists() and sha(d) != sha(s): raise SystemExit(f'refusing to overwrite differing file {d}')
    if not d.exists(): shutil.copy2(s, d)
    hs, hd = sha(s), sha(d); allid &= (hs == hd)
    txt = s.read_text()
    if fname in EXACTNESS: ver = f'verified: {EXACTNESS[fname]} appears verbatim in the file ({len(CONST[EXACTNESS[fname]])} characters; compared against thesis/scripts/persistbench_fullprompt_robustness/pb_src/benchmark/prompts.py via ast)' if CONST[EXACTNESS[fname]] in txt else 'NOT VERIFIED'
    elif fname == 'privacylens_prompt_exact.txt': ver = 'verified: source of construct_prompt from eval_privacylens_mcq_local.py appears verbatim in the file' if pl_fn in txt else 'construct_prompt source not found verbatim (see file)'
    else: ver = 'schematic (not a verbatim prompt)'
    rows.append([fname, str(s.relative_to(R)), str((DST / fname).relative_to(R)), kind, topic, content, ref, ver, hs, hd, 'identical' if hs == hd else 'DIFFERENT', s.stat().st_size, d.stat().st_size])
tsv(H / 'prompt_inventory.tsv', ['filename', 'source_path', 'copied_path', 'exact_or_schematic', 'topic', 'contents', 'thesis_reference', 'exactness_verification', 'sha256_source', 'sha256_copy', 'copy_integrity', 'bytes_source', 'bytes_copy'], rows)
chk('prompt inventory: 8 files copied, source and copy SHA-256 identical', len(rows) == 8 and allid and len(list(DST.iterdir())) == 8)
chk('exact prompt files verified verbatim against source constants', all(r[7].startswith('verified') for r in rows if r[3] == 'exact'), '; '.join(f'{r[0]}: {r[7][:9]}' for r in rows if r[3] == 'exact'))

# =================================================================================================== 7. configuration inventory
EXP, INH, INF = 'explicitly configured', 'inherited/default', 'inferred from runtime artifacts'
CFG = []
def add(setting, param, value, status, evidence): CFG.append([setting, param, value, status, evidence])
# ---- PrivacyLens
PL = 'PrivacyLens (493 items; all MUSE and TOFU behavioural models)'
EV = 'thesis/scripts/privacylens/eval_privacylens_mcq_local.py; thesis/appendix_material/configs/privacylens_configuration.tsv'
add(PL, 'decoding', 'sampling (do_sample=True)', EXP, EV + ' (model.generate(..., do_sample=True))')
add(PL, 'temperature', '1.0', INH, EV + ' (argparse default 1.0; TOFU launchers additionally pass --temperature 1.0 explicitly)')
add(PL, 'max new tokens', '20', INH, EV + ' (argparse default 20; TOFU launchers additionally pass --max-new-tokens 20)')
add(PL, 'samples per item', '1', EXP, EV + ' (single generate call per item)')
add(PL, 'seed', 'torch.manual_seed(42), set once before the item loop (torch generator only; not re-seeded per item)', INH, EV + ' (argparse --seed default 42)')
add(PL, 'prompt truncation', 'none (tokenizer called without truncation/max_length)', INH, EV)
add(PL, 'chat template', "model's own template if tokenizer.chat_template is not None, applied to one user message with no explicit system message; Qwen template inserts its default system turn; Llama-2: none (raw text)", EXP, EV + '; prompts/privacylens_prompt_exact.txt')
add(PL, 'prompt variant', 'naive', EXP, 'meta.prompt_type == naive in all 70 stored outputs (STORED)')
add(PL, 'top_p / top_k / repetition_penalty (Qwen2.5-7B-Instruct checkpoints)', '0.8 / 20 / 1.05', INH, 'checkpoint generation_config.json merged by HF generate (files read after the runs, not archived per run)')
add(PL, 'top_p / top_k / repetition_penalty (Llama-3.1-8B-Instruct, TOFU)', 'top_p 0.9 (generation_config.json); top_k 50 and repetition_penalty 1.0 (library defaults)', INF, 'generation_config.json {temperature 0.6, top_p 0.9}; HF GenerationConfig defaults')
add(PL, 'top_p / top_k / repetition_penalty (Llama-2-7b, MUSE-Books)', '1.0 / 50 / 1.0 (library defaults)', INF, 'generation_config.json contains only bos/eos; HF defaults')
# ---- MUSE original truncated Qwen
def muse_rows(setting, model_note, hw, ctx_note, gc_status, gc_val, ev):
    add(setting, 'hardware', hw, EXP if 'requested' in hw else INF, ev)
add_s = 'MUSE original, truncated (Qwen2.5-7B-Instruct, News + Books; Track B)'
EVQ = 'external/PersistBench/outputs/muse_{news,books}_qwen25_selected_full/*.json metadata.models[0].api_params; logs/vllm_muse_*_qwen25_*_{408558,409517}_*.log'
add(add_s, 'temperature', '0.0', EXP, EVQ)
add(add_s, 'max new tokens', '96', EXP, EVQ)
add(add_s, 'context length (vLLM --max-model-len)', '2048', EXP, 'launcher thesis/scripts/persistbench/run_persistbench_muse_*_qwen25_selected.sh; vLLM non-default args in logs')
add(add_s, 'prompt truncation', 'left truncation to the last 1800 prompt tokens (extra_body.truncate_prompt_tokens=1800)', EXP, EVQ + ' (stored in output metadata; injected by the then-current patched utils.py)')
add(add_s, 'chat template', 'templates/simple_llama_chat_template.jinja (plain User:/Assistant: text)', EXP, 'launcher --chat-template flag; vLLM log non-default args')
add(add_s, 'generations per scenario (cross_domain / sycophancy / beneficial memory)', '3 / 3 / 1', INH, 'PersistBench DEFAULT_GENERATIONS_BY_FAILURE_TYPE; counted in the output files')
add(add_s, 'explicit generation seed', 'none (no request seed, no --seed flag); vLLM 0.23.0 engine logs its own default seed=0', INH, 'vLLM startup logs')
add(add_s, 'top_p / top_k / repetition_penalty', '0.8 / 20 / 1.05 (effective; moot at temperature 0 for top_p/top_k, active for repetition_penalty)', INH, "checkpoint generation_config.json; confirmed by the vLLM log line 'Default vLLM sampling parameters have been overridden by the model's generation_config.json'")
add(add_s, 'served-model alias in the prompt', 'muse_{news,books}_qwen25_<condition> (condition-specific; located in the head of the prompt that the truncation removed)', EXP, 'launcher --served-model-name; prompts/persistbench_generator_exact.txt')
add(add_s, 'hardware', 'NVIDIA A100 80GB (gres a180); News job 408558_0 (node penelope), Books job 409517_0 (node rubeus); vLLM 0.23.0', INF, 'thesis/analysis/truncated_replication_20261016/configuration_audit.tsv (SLURM accounting + vLLM log)')
# ---- MUSE replicated truncated
add_s = 'MUSE truncated replication (Qwen2.5-7B-Instruct, News + Books)'
EVR = 'thesis/analysis/truncated_replication_20261016/{configuration_audit,replication_config_verification,job_summary}.tsv; external/PersistBench/outputs/truncated_replication_20261016/'
for p_, v_ in (('temperature', '0.0'), ('max new tokens', '96'), ('context length (vLLM --max-model-len)', '2048'), ('prompt truncation', 'left truncation to the last 1800 prompt tokens (truncate_prompt_tokens=1800)'),
               ('chat template', 'templates/simple_llama_chat_template.jinja')):
    add(add_s, p_, v_, EXP, EVR + ' (same server arguments as the original run, verified IDENTICAL)')
add(add_s, 'generations per scenario (cross_domain / sycophancy / beneficial memory)', '3 / 3 / 1', INH, EVR)
add(add_s, 'explicit generation seed', 'none; vLLM engine default seed=0', INH, EVR)
add(add_s, 'top_p / top_k / repetition_penalty', '0.8 / 20 / 1.05', INH, EVR + ' (override line identical to original)')
add(add_s, 'hardware', 'NVIDIA H200 NVL (gres h200nvl); News job 466261 (node lenny), Books job 466262 (node nelson); vLLM 0.23.0', INF, 'thesis/analysis/truncated_replication_20261016/job_summary.tsv (SLURM accounting + nvidia-smi)')
# ---- MUSE full prompt Qwen
add_s = 'MUSE full prompt (Qwen2.5-7B-Instruct, News + Books, complete matrix)'
EVF = 'thesis/analysis/muse_qwen_fullprompt_complete_20261016/generation_config.tsv; thesis/scripts/persistbench_fullprompt_{robustness,complete}/; stored output metadata'
add(add_s, 'temperature', '0.0', EXP, EVF + ' (api_params)')
add(add_s, 'max new tokens', '96', EXP, EVF + ' (api_params)')
add(add_s, 'context length (vLLM --max-model-len)', '8192', EXP, EVF)
add(add_s, 'prompt truncation', 'none: truncate_prompt_tokens deliberately omitted (sandboxed PersistBench copy pb_src without forced truncation); vLLM-reported prompt_tokens 4,760-5,125', EXP, EVF + ' (absence verified in stored api_params and by actual prompt_tokens)')
add(add_s, 'chat template', 'templates/simple_llama_chat_template.jinja (not the native Qwen template)', EXP, EVF)
add(add_s, 'generations per scenario (cross_domain / sycophancy / beneficial memory)', '3 / 3 / 1', INH, 'PersistBench defaults; counted in every cell file')
add(add_s, 'explicit generation seed', 'none; vLLM engine default seed=0', INH, 'vLLM startup logs')
add(add_s, 'top_p / top_k / repetition_penalty', '0.8 / 20 / 1.05', INH, 'checkpoint generation_config.json; override line present in all 30 cells\' vLLM logs')
add(add_s, 'served-model alias in the prompt', 'muse_news_qwen25 (News) / muse_books_qwen25 (Books): one neutral alias shared by all five conditions of a dataset', EXP, EVF)
add(add_s, 'judge', 'Qwen/Qwen2.5-7B-Instruct served as local-judge (temperature 0; identical rubric/code to all other PersistBench judging)', EXP, 'stored metadata.judge_model = local-judge; launcher')
add(add_s, 'hardware', 'NVIDIA H200 NVL (gres h200nvl) for all 30 cells: reused News cross-domain/sycophancy cells jobs 466206/466200 (node lenny); new cells jobs 466336-466339 (node nelson); vLLM 0.23.0, torch 2.11.0+cu130, transformers 5.12.1, CUDA 12.2', INF, 'SLURM accounting (sacct) + _meta/env_*.txt')
# ---- MUSE Llama-2
add_s = 'MUSE original, truncated (Llama-2-7b, News [Track A] + Books)'
EVL = 'external/PersistBench/outputs/muse_{news_selected,books_llama2_selected}_full/*.json; logs/vllm_muse_*llama2*; thesis/appendix_material/configs/generation_configurations.tsv'
for p_, v_ in (('temperature', '0.0'), ('max new tokens', '96'), ('context length (vLLM --max-model-len)', '2048'), ('prompt truncation', 'left truncation to the last 1800 prompt tokens'), ('chat template', 'templates/simple_llama_chat_template.jinja')):
    add(add_s, p_, v_, EXP, EVL)
add(add_s, 'generations per scenario (cross_domain / sycophancy / beneficial memory)', '3 / 3 / 1', INH, 'PersistBench defaults; counted in outputs')
add(add_s, 'explicit generation seed', 'none; vLLM engine default seed=0', INH, 'vLLM startup logs')
add(add_s, 'top_p / top_k / repetition_penalty', '1.0 / disabled (-1) / 1.0 (vLLM defaults)', INF, 'no vLLM override line in the logs and no local generation_config.json for the official target (absence of evidence)')
add(add_s, 'hardware', 'A100-class (a180), vLLM 0.23.0 (see source table)', INF, EVL)
# ---- TOFU
for nm, tpl, tp, tk, rp, st_tp, st_other, ev_ in (
        ('TOFU Qwen2.5-7B-Instruct (PersistBench)', 'native Qwen2.5 ChatML template (no --chat-template flag)', '0.8', '20', '1.05', INH, INH, 'external/PersistBench/outputs/final_tofu_persistbench_localjudge/qwen25_7b_*_localjudge.json; logs/vllm_qwen25_7b_*_from_tofufull_*.log'),
        ('TOFU Llama-3.1-8B-Instruct (PersistBench)', 'native Llama-3.1 header template (no --chat-template flag)', '0.9', 'not set (disabled)', '1.0', INH, INF, 'external/PersistBench/outputs/final_tofu_persistbench_localjudge/llama31_8b_*_localjudge.json; logs/vllm_llama31_8b_*_404164_*.log')):
    add(nm, 'temperature', '1.0', EXP, ev_ + ' (stored api_params)')
    add(nm, 'max new tokens', '512', EXP, ev_ + ' (stored api_params)')
    add(nm, 'context length (vLLM --max-model-len)', '8192', EXP, ev_)
    add(nm, 'prompt truncation', 'none (no truncate_prompt_tokens; all prompts fit 8192 by code inspection - raw prompts were not stored)', INH, ev_)
    add(nm, 'chat template', tpl, INH, ev_)
    add(nm, 'generations per scenario (cross_domain / sycophancy / beneficial memory)', '3 / 3 / 1', INH, 'PersistBench defaults; counted in outputs')
    add(nm, 'explicit generation seed', 'none; vLLM engine default seed=0 (sampled generations are not exactly reproducible at temperature 1.0)', INH, 'vLLM startup logs')
    add(nm, 'top_p', tp, st_tp, 'checkpoint generation_config.json via vLLM default override (vLLM log line)')
    add(nm, 'top_k', tk, st_other if nm.startswith('TOFU Llama') else INH, 'generation_config.json / vLLM default')
    add(nm, 'repetition_penalty', rp, st_other if nm.startswith('TOFU Llama') else INH, 'generation_config.json / vLLM default')
    add(nm, 'served-model alias in the prompt', 'condition-specific alias (e.g. qwen25_7b_after_rmu_from_tofufull); not truncated, so visible to the model', EXP, 'launcher --served-model-name; thesis/appendix_material/README.md')
tsv(H / 'final_generation_configs.tsv', ['setting', 'parameter', 'value', 'status', 'evidence'], CFG)
chk('config inventory: every row carries one of the three status labels', all(r[3] in (EXP, INH, INF) for r in CFG), f'{len(CFG)} rows')

# =================================================================================================== 8. checkpoints
mc = rtsv(AM / 'reproducibility/model_checkpoints.tsv'); HFC = Path('/storage/ukp/work/elshashay/.cache/huggingface/hub')
def exists(path):
    if path.startswith('n/a'): return None
    if path.startswith('/'): return Path(path).exists()
    if (R / path).exists(): return True
    if re.fullmatch(r'[\w.-]+/[\w.-]+', path): return (HFC / ('models--' + path.replace('/', '--'))).exists()
    return False
def real(path):
    if path.startswith('/') or (R / path).exists(): return str((R / path).resolve()) if not path.startswith('/') else str(Path(path).resolve())
    return path
lists = {}
for f in ('muse_news_qwen25', 'muse_books_qwen25', 'muse_books_llama2'):
    for l in open(R / f'thesis/manifests/model_lists/{f}_persistbench_models.tsv'):
        lab, mp, tp = l.rstrip('\n').split('\t'); lists[lab] = (mp, tp)
rows = []; mism = []
for r in mc:
    if r['Dataset'].startswith('MUSE-News (FULL-PROMPT'): continue
    ds, model, cond = r['Dataset'], r['Model'], r['Condition']; sel = r['Selected unlearned checkpoint']; tgt = r['Base/Target checkpoint']
    path = tgt if sel.startswith('n/a') else sel; m = re.search(r'checkpoint-(\d+)', path)
    ex_t, ex_s = exists(tgt), exists(sel)
    exists_all = all(x is not False for x in (ex_t, ex_s)) and (ex_s if ex_s is not None else ex_t)
    if ds.startswith('TOFU'): loaded = 'run directory top-level weights (NOT the checkpoint-N subdirectory); not byte-compared with the selected checkpoint (audit note)' if not sel.startswith('n/a') else 'start model (TOFU-finetuned target)'
    elif 'Llama-2' in model: loaded = 'selected checkpoint directory' if not sel.startswith('n/a') else 'official muse-bench target (HF hub id)'
    else: loaded = 'selected checkpoint directory' if not sel.startswith('n/a') else 'fine-tuned target directory'
    used = ('original truncated (A100); truncated replication (H200); complete full prompt (H200)' if 'Qwen2.5-7B' in model and ds.startswith('MUSE') else
            'original truncated; truncated replication (News: Track A, see notes)' if 'Llama-2' in model and ds == 'MUSE-News' else 'original truncated; truncated replication (H200)' if 'Llama-2' in model else 'TOFU PersistBench / PrivacyLens')
    # manifest cross-check for MUSE Qwen / Llama-2 Books
    lab = None
    if ds.startswith('MUSE') and ('Qwen' in model or ('Llama-2' in model and ds == 'MUSE-Books')):
        pre = f"muse_{'news' if ds == 'MUSE-News' else 'books'}_{'qwen25' if 'Qwen' in model else 'llama2'}_{ {'Target': 'before'}.get(cond, cond.lower()) }"
        if pre in lists:
            ml = lists[pre][0]; ok = (R / ml).resolve() == (R / (tgt if sel.startswith('n/a') else sel)).resolve()
            if not ok: mism.append((ds, cond, ml, sel))
    rows.append([ds, model, cond, m.group(1) if m else ('n/a (Target / start model)' if sel.startswith('n/a') else 'n/a (no checkpoint-N in path)'), real(tgt), 'n/a (Target)' if sel.startswith('n/a') else real(sel),
                 'yes' if exists_all else ('HF hub id; local cache present' if ex_t and re.fullmatch(r'[\w.-]+/[\w.-]+', tgt) and sel.startswith('n/a') else 'NO'), loaded, r['Selection manifest'], r['Status / notes'], r['Behavioral output path'], used])
tsv(H / 'final_model_checkpoints.tsv', ['benchmark', 'model', 'condition', 'checkpoint_step', 'base_or_target_path', 'selected_checkpoint_exact_path', 'exists_now', 'weights_loaded_for_behavioural_evaluation', 'provenance_selection_manifest', 'notes_from_audited_table', 'behavioural_output_path', 'used_for'], rows)
chk('checkpoints: derived from audited model_checkpoints.tsv (no selection change); every path exists now', all(r[6] != 'NO' for r in rows), f'{len(rows)} rows; missing: {[r[:3] for r in rows if r[6] == "NO"]}')
chk('checkpoints: MUSE Qwen (News, Books) and Llama-2 Books selections equal the persistbench model-list manifests', not mism, str(mism))

# =================================================================================================== 9. LaTeX tables
def esc(s): return str(s).replace('\\', r'\textbackslash{}').replace('_', r'\_').replace('%', r'\%').replace('&', r'\&').replace('#', r'\#')
def dtex(x): return '--' if x is None else ('0.00' if abs(float(x)) < 5e-13 else (f'+{float(x):.2f}' if x > 0 else f'$-${abs(float(x)):.2f}'))
def ptex(p): return '$<0.0001$' if p < 1e-4 else f'{p:.4f}'
def table(label, caption, colspec, header, rows, midrules=(), notes=None):
    L = ['\\begin{table}[tb]', '  \\centering', f'  \\caption{{{caption}}}', f'  \\label{{{label}}}', f'  \\begin{{tabular}}{{{colspec}}}', '    \\toprule', '    ' + ' & '.join(header) + ' \\\\', '    \\midrule']
    for i, r in enumerate(rows):
        if i in midrules: L.append('    \\midrule')
        L.append('    ' + ' & '.join(str(x) for x in r) + ' \\\\')
    L += ['    \\bottomrule', '  \\end{tabular}', '\\end{table}']
    return '\n'.join(L) + '\n'
HDR = '% Generated by thesis/analysis/final_thesis_handoff_20261016/scripts/build_handoff_materials.py from fullprompt_qwen_master.tsv and the other handoff TSVs. No interpretation.\n% Requires \\usepackage{booktabs}. Not compiled here (no LaTeX installation on the cluster); structure checked by script.\n'
LX = {}
def fr_row(ds, cond):
    out = [cond]
    for cat in CATS:
        r = FRT[(ds, cond, cat)][3]; out.append(f'{float(r[0]):.2f}'); out.append('ref.' if cond == 'Target' else dtex(DELT[(ds, cond, cat)]))
    return out
for key, ds, lab in (('A_fullprompt_news_fr3', 'MUSE-News', 'tab:fullprompt-news-fr3'), ('B_fullprompt_books_fr3', 'MUSE-Books', 'tab:fullprompt-books-fr3')):
    LX[key] = table(lab, f'Complete full-prompt PersistBench evaluation of Qwen2.5-7B-Instruct on {ds} (validity-aware failure rate in \\%, validity v2). Cross-domain and sycophancy: FR@3 over 200 scenarios with three generations each; beneficial memory: FR@1 over 100 scenarios with one generation. $\\Delta$ = difference to Target in percentage points. CD = cross-domain, Syc. = sycophancy, Ben. = beneficial memory.',
                    '@{}l rr rr rr@{}', ['Condition', 'CD FR@3', '$\\Delta$', 'Syc.\\ FR@3', '$\\Delta$', 'Ben.\\ FR@1', '$\\Delta$'], [fr_row(ds, c) for c in CONDS], midrules=(1,))
rows = [['Target FR@3 (\\%)', f'{float(FRT[("MUSE-News", "Target", "sycophancy")][3][0]):.2f}', '', f'{float(FRT[("MUSE-Books", "Target", "sycophancy")][3][0]):.2f}', '']]
for c in UNL:
    pn, pb = PT[('MUSE-News', c, 'sycophancy')], PT[('MUSE-Books', c, 'sycophancy')]
    rows.append([c, dtex(pn['d']), ptex(pn['p']), dtex(pb['d']), ptex(pb['p'])])
LX['C_sycophancy_deltas'] = table('tab:fullprompt-sycophancy-deltas', 'Full-prompt sycophancy: difference in FR@3 between each unlearned model and its Target (percentage points) for Qwen2.5-7B-Instruct on MUSE-News and MUSE-Books, with exact two-sided paired $p$ values over 200 scenarios (nominal, no multiple-comparison correction).',
                                  '@{}l rr rr@{}', ['', 'News $\\Delta$', 'News $p$', 'Books $\\Delta$', 'Books $p$'], rows, midrules=(1,))
vrows = []
for c in CONDS:
    out = [c]
    for ds in DSL:
        for cat in CATS:
            m = [x for x in MASTER if x[0] == ds and x[1] == c and x[2] == cat][0]; out.append(f'{m[6]}/{m[5]}')
    vrows.append(out)
totr = ['Total'] + [f'{sum(x[6] for x in MASTER if x[0] == ds and x[2] == cat)}/{sum(x[5] for x in MASTER if x[0] == ds and x[2] == cat)}' for ds in DSL for cat in CATS]
vrows.append(totr)
LX['D_validity'] = table('tab:fullprompt-validity', 'Validity of the complete full-prompt Qwen2.5-7B-Instruct matrix under the final validity classifier v2 (repetition rule off): valid / generated responses per cell. Overall 12,999 of 13,000 generations are valid. CD = cross-domain, Syc. = sycophancy, Ben. = beneficial memory.',
                         '@{}l ccc ccc@{}', ['', 'News CD', 'News Syc.', 'News Ben.', 'Books CD', 'Books Syc.', 'Books Ben.'], vrows, midrules=(5,))
srows = []
def sat(reg, cat, key): return SAT[(reg, cat)][key]
labels = {'original': 'Original truncated', 'replicated': 'Replicated truncated', 'full': 'Full prompt'}
hwtex = {'original': 'A100 80GB', 'replicated': 'H200 NVL', 'full': 'H200 NVL'}
srows = [['Hardware'] + [hwtex[r] for r in labels], ['Context length'] + ['2048', '2048', '8192'], ['Prompt truncation'] + ['last 1800 tokens', 'last 1800 tokens', 'none'], ['Max.\\ new tokens'] + ['96'] * 3, ['Temperature'] + ['0.0'] * 3]
for cat, lab in (('cross_domain', 'Cross-domain'), ('sycophancy', 'Sycophancy'), ('beneficial_memory', 'Beneficial memory')):
    kk = 'FR@1' if cat == 'beneficial_memory' else 'FR@3'
    srows += [[f'{lab} Target {kk} (\\%)'] + [f'{float(sat(r, cat, "t")):.2f}' for r in labels], [f'{lab} SatImp {kk} (\\%)'] + [f'{float(sat(r, cat, "s")):.2f}' for r in labels],
              [f'{lab} $\\Delta$ (pp)'] + [dtex(sat(r, cat, 'd')) for r in labels], [f'{lab} paired $p$'] + [ptex(sat(r, cat, 'p')) for r in labels]]
LX['E_satimp_three_way'] = table('tab:satimp-three-way', 'MUSE-News, Qwen2.5-7B-Instruct, SatImp versus Target under three evaluation settings (validity v2). Paired $p$: exact two-sided test on discordant scenarios (200 scenarios; 100 for beneficial memory), nominal.',
                                 '@{}l ccc@{}', ['', 'Original truncated', 'Replicated truncated', 'Full prompt'], srows, midrules=(5, 9, 13))
strong = [('MUSE-Books', 'RMU', 'cross_domain'), ('MUSE-Books', 'RMU', 'sycophancy'), ('MUSE-Books', 'RMU', 'beneficial_memory'), ('MUSE-News', 'WGA', 'cross_domain'), ('MUSE-News', 'SimNPO', 'cross_domain'), ('MUSE-News', 'SatImp', 'sycophancy')]
prow = []
for ds, c, cat in strong:
    v = PT[(ds, c, cat)]; prow.append([ds.replace('MUSE-', ''), c, CATN[cat], f'{float(v["t"]):.2f}', f'{float(v["u"]):.2f}', dtex(v['d']), v['sf'], v['fs'], v['n'], ptex(v['p'])])
LX['F_paired_tests_strongest'] = table('tab:fullprompt-paired-strongest', 'Full-prompt Qwen2.5-7B-Instruct: all five comparisons with nominal $p<0.05$ (first five rows) and, for reference, News SatImp sycophancy (last row). Failure rates in \\% (FR@3; beneficial memory FR@1); S$\\to$F / F$\\to$S: scenarios moving from safe to failure and from failure to safe relative to Target. $p$: exact two-sided paired test; nominal, no multiple-comparison correction was applied (24 comparisons).',
                                       '@{}l l l rr r rr r r@{}', ['Data', 'Method', 'Category', 'Target', 'Method', '$\\Delta$', 'S$\\to$F', 'F$\\to$S', 'N', '$p$'], prow, midrules=(5,))
gc = [['PrivacyLens', '1.0', '20', 'n/a', 'none', 'model template', '1', '0.8/20/1.05 (Qwen)$^{a}$', '42'],
      ['MUSE original (Qwen)', '0.0', '96', '2048', 'last 1800 tok.', 'simple template', '3/3/1', '0.8/20/1.05$^{a}$', 'none'],
      ['MUSE replication (Qwen)', '0.0', '96', '2048', 'last 1800 tok.', 'simple template', '3/3/1', '0.8/20/1.05$^{a}$', 'none'],
      ['MUSE full prompt (Qwen)', '0.0', '96', '8192', 'none', 'simple template', '3/3/1', '0.8/20/1.05$^{a}$', 'none'],
      ['MUSE original (Llama-2)', '0.0', '96', '2048', 'last 1800 tok.', 'simple template', '3/3/1', '1.0/off/1.0$^{b}$', 'none'],
      ['TOFU (Qwen)', '1.0', '512', '8192', 'none', 'native', '3/3/1', '0.8/20/1.05$^{a}$', 'none'],
      ['TOFU (Llama-3.1)', '1.0', '512', '8192', 'none', 'native', '3/3/1', '0.9/off/1.0$^{c}$', 'none']]
LX['G_generation_configs'] = table('tab:generation-configs', 'Generation settings by evaluation. Generations per scenario: cross-domain/sycophancy/beneficial memory. "simple template" = \\texttt{simple\\_llama\\_chat\\_template.jinja}. Seed ``none\'\': no explicit seed (vLLM engine default). PrivacyLens: seed 42 via \\texttt{torch.manual\\_seed}. $^{a}$ top-$p$/top-$k$/repetition penalty inherited from the checkpoint \\texttt{generation\\_config.json}; $^{b}$ inferred vLLM defaults; $^{c}$ top-$p$ inherited, top-$k$ and repetition penalty inferred defaults.',
                                   '@{}l c c c l l c l c@{}', ['Setting', 'Temp.', 'Max new', 'Context', 'Truncation', 'Template', 'Gens', 'top-$p$/$k$/rep.', 'Seed'], gc)
(H / 'latex').mkdir(exist_ok=True)
for k, v in LX.items(): (H / 'latex' / f'{k}.tex').write_text(HDR + v)
(H / 'latex' / 'all_tables.tex').write_text(HDR + '% Convenience file: \\input each snippet or paste them individually.\n' + ''.join(f'\\input{{{k}}}\n' for k in LX))
# structural validation of the snippets
bad = []
for k, v in LX.items():
    t = v.split('\n'); beg = sum('\\begin{table}' in l for l in t) == 1 == sum('\\end{table}' in l for l in t); tb = 'begin{tabular}' in v and 'end{tabular}' in v
    cols = re.search(r'\\begin\{tabular\}\{(.*)\}', v).group(1).replace('@{}', '').replace(' ', ''); ncol = len(re.findall(r'[lcr]', cols))
    for l in t:
        if l.strip().endswith('\\\\') and 'caption' not in l and '&' in l and l.count('&') != ncol - 1: bad.append((k, l[:60]))
    if not (beg and tb and v.count('{') == v.count('}')): bad.append((k, 'unbalanced'))
chk('LaTeX snippets: balanced environments/braces and consistent column counts (7 tables)', not bad and len(LX) == 7, str(bad))

# =================================================================================================== 10. THESIS_FACTS.md
man = rtsv(FA / 'fullprompt_manifest.tsv'); gcfg = rtsv(FA / 'generation_config.tsv'); pla = rtsv(FA / 'prompt_length_audit.tsv')
envtxt = '; '.join(sorted({l.strip() for f in (R / 'external/PersistBench/outputs/muse_qwen_fullprompt_complete_20261016/_meta').rglob('env_*.txt') for l in f.read_text().splitlines() if l.startswith(('vllm=', 'CUDA_HOME'))}))
jobs = rtsv(R / 'external/PersistBench/outputs/muse_qwen_fullprompt_complete_20261016/job_plan_submissions.tsv')
def g(ds, cond, cat, k): return float(FRT[(ds, cond, cat)][k][0])
pm = lambda x: pp(x)
LF = []
A = LF.append
A('# THESIS FACTS (factual reference for writing; no interpretation, no new claims)\n')
A('Generated 2026-10-16 from frozen artifacts by `scripts/build_handoff_data.py` and `scripts/build_handoff_materials.py`. Every number below was recomputed from per-generation validity-v2 labels and judge scores with exact fractions and cross-checked against the frozen analyses and against a fresh v2 classification of the raw JSON (see `integrity_check.txt`). "pp" = percentage points. Beneficial memory is called `beneficial_memory_usage` inside PersistBench files.\n')
A('## Standing warnings\n- **No multiple-comparison correction was applied anywhere.** All p-values are exact two-sided paired (McNemar/binomial on discordant scenarios) and *nominal*. 24 full-prompt comparisons were tested; about 1.2 nominal p < 0.05 are expected by chance alone.\n- **Effects of about 3 pp or smaller should be interpreted cautiously.** Between the original and replicated truncated runs of the same models, 4.95% of scenario classifications change (198/4,000, cross-domain + sycophancy), and in 3 of 24 Target-to-unlearned comparisons the sign of the delta flips.\n- The 24 Target-to-unlearned comparisons share their Target baselines, so counts of sign agreement are descriptive and not independent.\n- All FR values are the **validity-aware** FR@K (frozen validity classifier v2, `repetition_rule=False`), not the official un-gated `failure_rates.py` value; they differ in exactly one (cell, K) pair of the full-prompt matrix (Books RMU sycophancy FR@1: 11.5578 [N=199] validity-aware vs 11.50 [N=200] un-gated).\n')
A('## Complete full-prompt Qwen matrix (generation counts)\n')
A(f'- 2 datasets x 5 conditions x 3 categories = 30 cells; **13,000 generations**, all judged by the primary judge (Qwen2.5-7B-Instruct as `local-judge`). Per condition and dataset: 600 cross-domain (200 scenarios x 3) + 600 sycophancy (200 x 3) + 100 beneficial memory (100 x 1) = 1,300; per dataset 6,500.')
A('- **Reused: 4,800** generations = 8 existing News cells (Target, RMU, SatImp, SimNPO x cross-domain, sycophancy; 600 each) from `external/PersistBench/outputs/muse_news_qwen25_fullprompt_robustness/` (sycophancy, job 466200) and `..._crossdomain/` (cross-domain, job 466206). **Newly generated: 8,200** = News 1,700 (WGA 1,300 + beneficial memory for Target/RMU/SatImp/SimNPO 400; job 466336) + Books 6,500 (jobs 466337 Target+RMU, 466338 WGA+SatImp, 466339 SimNPO). New files: `external/PersistBench/outputs/muse_qwen_fullprompt_complete_20261016/{muse_news,muse_books}/`. Per-cell source file and SHA-256: `thesis/analysis/muse_qwen_fullprompt_complete_20261016/fullprompt_manifest.tsv`.')
A('- Generation settings: `max_model_len` 8192, no `truncate_prompt_tokens`, temperature 0.0, max 96 new tokens, `simple_llama_chat_template.jinja`, neutral alias `muse_news_qwen25` / `muse_books_qwen25` shared by all five conditions of a dataset; effective top_p 0.8 / top_k 20 / repetition_penalty 1.05 inherited from the checkpoint `generation_config.json`.')
A('\n## Validity (v2, repetition rule off)\n')
A(f'- **12,999 / 13,000 generations valid (99.9923%).** The one invalid generation: {INV[0][0]} {INV[0][1]} {INV[0][2]}, scenario #{INV[0][4]} of 200 in the category input order (hash `{INV[0][3]}`), generation position {INV[0][5][0]}, label `{INV[0][5][1]}`, rule `{INV[0][5][2]}`, judge score {INV[0][5][3]}; file `{INV[0][7]}`. Consequence: Books RMU sycophancy FR@1 has N = 199 (FR@2, FR@3: N = 200). Every other cell is 100% valid with full N.')
A('- No full-prompt Qwen condition collapsed (contrast: MUSE-Books Llama-2 WGA, 1,300/1,300 invalid in both truncated runs).')
A('- v2 differs from v1 only in the web/page-contamination rule (whole-phrase matching; `github`, `repository`, `pull requests` removed as evidence); source: module docstring of `thesis/scripts/validation/create_persistbench_validity_summary_v2.py` (SHA-256 `' + V2HASH + '`).')
A('\n## Hardware and software\n')
A(f'- **All 30 full-prompt cells: NVIDIA H200 NVL** (gres `h200nvl`; 8 reused News cells on node lenny, jobs 466200/466206; 22 new cells on node nelson, jobs 466336-466339). {envtxt}.')
A('- Original truncated runs: **A100 80GB** (gres a180; News job 408558_0 node penelope; Books job 409517_0 node rubeus). Truncated replication: **H200 NVL** (News job 466261 node lenny; Books job 466262 node nelson). vLLM 0.23.0 in all runs.')
A('- Therefore original-truncated vs full-prompt differs in prompt/context AND hardware; replicated-truncated vs full-prompt differs only in prompt/context (same GPU family); original vs replicated truncated differs only in hardware (plus rerun noise).')
A('\n## Prompt length and the effect of the original truncation\n')
rng = {r['category']: (r['actual min'], r['actual median'], r['actual max']) for r in pla if r['dataset'] == 'MUSE-News'}
lo = min(int(v[0]) for v in rng.values()); hi = max(int(v[2]) for v in rng.values())
A(f'- vLLM-reported `prompt_tokens` over all 13,000 full-prompt generations: **{lo:,} to {hi:,}** (min/median/max: cross-domain {rng["cross_domain"][0]}/{rng["cross_domain"][1]}/{rng["cross_domain"][2]}, sycophancy {rng["sycophancy"][0]}/{rng["sycophancy"][1]}/{rng["sycophancy"][2]}, beneficial memory {rng["beneficial_memory_usage"][0]}/{rng["beneficial_memory_usage"][1]}/{rng["beneficial_memory_usage"][2]}). News and Books prompts have identical lengths. Maximum {hi:,} + 96 generated tokens = {hi + 96:,} < 8,192.')
A(f'- The original truncation kept the last 1,800 prompt tokens, i.e. removed about **{100 * (1 - 1800 / lo):.1f}% to {100 * (1 - 1800 / hi):.1f}%** of each prompt (shortest to longest prompt) (median prompts: cross-domain {100 * (1 - 1800 / int(rng["cross_domain"][1])):.1f}%, sycophancy {100 * (1 - 1800 / int(rng["sycophancy"][1])):.1f}%, beneficial memory {100 * (1 - 1800 / int(rng["beneficial_memory_usage"][1])):.1f}%). What was removed is the persona/tool header (including the two `{{model_name}}` alias lines); the complete memories block and the query lay within the retained last 1,800 tokens in all 600 scenarios per dataset (pre-run reconstruction, `prompt_length_audit.tsv`). All 600 scenarios per dataset exceed 1,800 tokens.')
A('\n## SatImp, MUSE-News Qwen (exact values; Delta = SatImp - Target, pp)\n')
A('| regime | hardware | context / truncation | cross-domain Target / SatImp FR@3 | Delta | p | syc. Target / SatImp FR@3 | Delta | p | beneficial Target / SatImp FR@1 | Delta | p |\n|---|---|---|---|---|---|---|---|---|---|---|---|')
for reg, hw, cx in (('original', 'A100', '2048 / last 1800'), ('replicated', 'H200', '2048 / last 1800'), ('full', 'H200', '8192 / none')):
    r = [f'{reg}', hw, cx]
    for cat in CATS: r += [f'{float(SAT[(reg, cat)]["t"]):.2f} / {float(SAT[(reg, cat)]["s"]):.2f}', pm(SAT[(reg, cat)]['d']), f'{SAT[(reg, cat)]["p"]:.4f}']
    A('| ' + ' | '.join(r) + ' |')
A('\nDiscordant scenarios (S->F / F->S): ' + '; '.join(f'{reg} {CATN[cat]} {SAT[(reg, cat)]["sf"]}/{SAT[(reg, cat)]["fs"]}' for reg in ('original', 'replicated', 'full') for cat in CATS) + '. Exact values: `satimp_three_way.tsv`.')
A('\n## SimNPO, MUSE-News Qwen\n')
for cat in CATS:
    v = PT[('MUSE-News', 'SimNPO', cat)]; kk = 'FR@1' if cat == 'beneficial_memory' else 'FR@3'
    A(f'- Full prompt, {CATN[cat]}: Target {kk} {float(v["t"]):.2f}, SimNPO {float(v["u"]):.2f}, Delta {pp(v["d"])} pp; S->F {v["sf"]}, F->S {v["fs"]}, N {v["n"]}, p = {v["p"]:.4f}. Truncated Delta (original / replicated): {pp(CMP[[i for i, c in enumerate(CMP) if c["ds"] == "MUSE-News" and c["cond"] == "SimNPO" and c["cat"] == cat][0]]["d_original"])} / {pp(CMP[[i for i, c in enumerate(CMP) if c["ds"] == "MUSE-News" and c["cond"] == "SimNPO" and c["cat"] == cat][0]]["d_replicated"])} pp.')
A('\n## RMU, MUSE-Books Qwen (full prompt; truncated original / replicated Delta for reference)\n')
for cat in CATS:
    v = PT[('MUSE-Books', 'RMU', cat)]; c = [c for c in CMP if c['ds'] == 'MUSE-Books' and c['cond'] == 'RMU' and c['cat'] == cat][0]; kk = 'FR@1' if cat == 'beneficial_memory' else 'FR@3'
    A(f'- {CATN[cat]}: Target {kk} {float(v["t"]):.2f} -> RMU {float(v["u"]):.2f}, Delta {pp(v["d"])} pp; S->F {v["sf"]}, F->S {v["fs"]}, N {v["n"]}, p = {v["p"]:.3g}; truncated Delta original {pp(c["d_original"])} / replicated {pp(c["d_replicated"])} pp.')
A('\n## MUSE-Books Qwen sycophancy, full prompt (Delta vs Target, FR@3, N = 200)\n')
A(f'- Target FR@3: full prompt {float(FRT[("MUSE-Books", "Target", "sycophancy")][3][0]):.2f}; original truncated {float(OFR[("MUSE-Books", "Target", "sycophancy")][0]):.2f}; replicated truncated {float(RFR[("MUSE-Books", "Target", "sycophancy")][0]):.2f}.')
for c in ('WGA', 'SatImp', 'SimNPO'):
    v = PT[('MUSE-Books', c, 'sycophancy')]; x = [y for y in CMP if y['ds'] == 'MUSE-Books' and y['cond'] == c and y['cat'] == 'sycophancy'][0]
    A(f'- {c}: full-prompt Delta {pp(v["d"])} pp (S->F {v["sf"]}, F->S {v["fs"]}, p = {v["p"]:.4f}); truncated Delta original {pp(x["d_original"])} / replicated {pp(x["d_replicated"])} pp.')
A('\n## Beneficial memory (one generation per scenario; FR@1; failure = valid judge score < 2)\n')
for ds in DSL:
    A(f'- {ds} full prompt: ' + '; '.join(f'{c} {float(FRT[(ds, c, "beneficial_memory")][1][0]):.2f}' + ('' if c == 'Target' else f' (Delta {pp(DELT[(ds, c, "beneficial_memory")])}, p = {PT[(ds, c, "beneficial_memory")]["p"]:.4g})') for c in CONDS) + '.')
A('- FR@2 and FR@3 of beneficial memory equal FR@1 only because a single generation exists per scenario (the earlier frozen analysis tables mark them `NA`; the handoff master table repeats FR@1 in those columns and says so in its `note` column).')
A('\n## Scenario-level classification change (denominators = paired scenarios evaluable in both runs; changed = SAFE<->FAILURE)\n')
for pn in ('original truncated vs replicated truncated', 'original truncated vs full prompt', 'replicated truncated vs full prompt'):
    r = SC[(pn, '3-generation categories (cross_domain + sycophancy), News + Books, 5 conditions')]; b = SC[(pn, 'beneficial memory only (one generation; FR@1 classification), News + Books')]
    A(f'- {pn}: cross-domain + sycophancy {r["changed"]}/{r["n"]} = {100 * r["changed"] / r["n"]:.2f}%; beneficial memory {b["changed"]}/{b["n"]} = {100 * b["changed"] / b["n"]:.2f}% ({b["ne"]} scenario excluded as non-evaluable).')
A('- Same-sign counts among the 24 Target-to-unlearned deltas: ' + '; '.join(f'{k}: {v["agree"]}/24 (strict flips {v["flips"]})' for k, v in AGREE.items()) + '. Mean |difference of deltas| (pp): ' + '; '.join(f'{k.split(" ")[0] + " " + k.split(" ")[1] + " vs " + k.split(" vs ")[1].split(" ")[0]}: {v["mean"]:.2f}' for k, v in AGREE.items()) + '.')
pooled = rtsv(TA / 'scenario_repeatability_pooled_v2.tsv')
pp3 = [r for r in pooled if r['group'].startswith('POOLED 3-generation')][0]
A(f'\n## Original vs replication repeatability (truncated runs)\n- All four settings (News/Books x Qwen/Llama-2), cross-domain + sycophancy: {pp3["changed"]}/{pp3["paired evaluable N"]} = {pp3["change %"]}% classifications changed (S->F {pp3["SAFE->FAILURE"]}, F->S {pp3["FAILURE->SAFE"]}); only {pp3["identical response text %"]}% of generations byte-identical. Qwen News + Books only: 198/4,000 = 4.95%. Source: `thesis/analysis/truncated_replication_20261016_v2/`.')
A('- Replication ran on H200 versus A100 for the original; the two cannot be separated (no same-hardware rerun exists).')
A('\n## Results with nominal p < 0.05 in the complete full-prompt matrix (uncorrected; 5 of 24 tests)\n')
for (ds, c, cat), v in sorted(PT.items(), key=lambda kv: kv[1]['p']):
    if v['p'] < 0.05: A(f'- {ds} {c} {CATN[cat]}: Delta {pp(v["d"])} pp, S->F {v["sf"]} / F->S {v["fs"]}, N {v["n"]}, p = {v["p"]:.3g}')
A('- All other 19 full-prompt comparisons have nominal p >= 0.05 (e.g. News SatImp sycophancy p = %.4f, Books WGA sycophancy p = %.4f).' % (PT[('MUSE-News', 'SatImp', 'sycophancy')]['p'], PT[('MUSE-Books', 'WGA', 'sycophancy')]['p']))
A('\n## Source-document caveats (facts about existing documents)\n')
A('- `thesis/appendix_material/tables/{fullprompt_robustness,persistbench_frk_complete,generation_validity_complete}.tsv` and the validity-gate rule list in `thesis/appendix_material/README.md` were built with the **v1** classifier (per that README). Only `fullprompt_robustness.tsv` was numerically compared here: 4 of its News cells differ from v2 (listed in `integrity_check.txt`; e.g. SatImp full-prompt FR@3 15.58 with N = 199 under v1 vs 15.50 with N = 200 under v2). Do not take numbers from these three tables; use the handoff tables.')
A('- `thesis/appendix_material/configs/generation_configurations.tsv` still describes the full-prompt run as "MUSE-News only, 4 conditions, beneficial memory not run"; superseded by `final_generation_configs.tsv`.')
A('- `prompts/persistbench_generator_exact.txt` header names only the News neutral alias `muse_news_qwen25`; the Books full-prompt runs used `muse_books_qwen25`.')
A('- TOFU behavioural evaluations loaded each run directory\'s top-level weights; the selected `checkpoint-N` is recorded in the manifests, but the two were not byte-compared (audited-table note). No selection was changed.')
A('- MUSE-News Llama-2 is the official-target "Track A" setting, labelled SUPERSEDED in `thesis/appendix_material/README.md`; it was nevertheless included in the truncated replication as setting C (`research_history/04_muse_track_a/manifests/muse_news_persistbench_models.tsv`).')
(H / 'THESIS_FACTS.md').write_text('\n'.join(LF) + '\n')

# =================================================================================================== 11. final integrity checks (v1 contamination etc.)
v1 = rtsv(AM / 'tables/fullprompt_robustness.tsv'); diffs = []
for r in v1:
    if not r['Prompt regime tested'].startswith('full prompt'): continue
    cat = 'sycophancy' if 'sycophancy' in r['Category'] else 'cross_domain'; cond = r['Condition']
    o, f = OFR[('MUSE-News', cond, cat)], FRT[('MUSE-News', cond, cat)][3]
    if r['Original FR@3'] != f2(o[0]) or r['Original N'] != str(o[1]) or r['Full prompt FR@3'] != f2(f[0]) or r['Full prompt N'] != str(f[1]): diffs.append((cat, cond, f"v1 orig {r['Original FR@3']}/N{r['Original N']} full {r['Full prompt FR@3']}/N{r['Full prompt N']}", f"v2 orig {f2(o[0])}/N{o[1]} full {f2(f[0])}/N{f[1]}"))
chk('INFO v1 cross-check: old v1 appendix table differs from v2 in the listed News cells (handoff values come from the fresh v2 reclassification, verified in part 1)', True, f'{len(diffs)} v1-vs-v2 cell differences: {diffs}')
txt = ''.join((H / f).read_text() for f in ('fullprompt_qwen_master.tsv', 'paired_tests_fullprompt_qwen.tsv', 'THESIS_FACTS.md'))
chk('master table carries v2 N for the cells where v1 had N=199 (News SatImp/SimNPO/RMU sycophancy: N=200)', all(FRT[('MUSE-News', c, 'sycophancy')][3][1] == 200 for c in ('RMU', 'SatImp', 'SimNPO')))
chk('no experiment/job launched by the handoff scripts (squeue empty)', os.popen('squeue -u $USER -h 2>/dev/null | wc -l').read().strip() == '0')
out = ['FINAL INTEGRITY CHECK  (' + str(sum(1 for c in CHECKS if c[1])) + ' of ' + str(len(CHECKS)) + ' checks passed)', '']
for n, ok, d in CHECKS: out.append(('PASS  ' if ok else 'FAIL  ') + n + (f'\n        {d}' if d else ''))
out += ['', 'v1 vs v2 differences in the old appendix_material full-prompt table (News):'] + [f'  {d}' for d in diffs]
(H / 'integrity_check.txt').write_text('\n'.join(out) + '\n')
print('FAILED CHECKS:', [c for c in CHECKS if not c[1]] or 'none'); print('files in handoff dir:', sorted(p.name for p in H.iterdir()))
