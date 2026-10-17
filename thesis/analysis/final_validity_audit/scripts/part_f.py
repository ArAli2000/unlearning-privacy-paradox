import pickle, csv, json
from pathlib import Path
from common import *
from math import comb
from collections import Counter
S=str(Path(__file__).parent)+'/'
P=pickle.load(open(S+'_partb.pkl','rb')); CMP, FR, VAL = P['CMP'], P['FR'], P['VAL']
rows=[]
def add(tbl, cell, cur_proc, cur, fin, diff, interp): rows.append([tbl, cell, cur_proc, cur, fin, diff, interp])
f2=lambda v: 'NA' if v is None else f'{v:.2f}'
# A/B: FR@K cells
for k,v in FR.items():
    grp,ds,model,cond,cat,K=k
    if grp!='main': continue
    o,v1,v2=v['official'],v['v1'],v['v2']
    cell=f'{ds} | {model} | {cond} | {cat} | FR@{K}'
    wga=(ds,model,cond)==('MUSE-Books','Llama-2-7B','WGA')
    if (v1[0]!=v2[0]) or (v1[1]!=v2[1]):
        add('appendix persistbench_frk_complete.tsv [validity-aware rows]; mechanistic/.../muse_news_category_comparison_validated.csv; muse_books_weekly_update_analysis/persistbench_fr_at_k.csv', cell, 'validity-aware v1', f'{f2(v1[0])} (N={v1[1]})', f'{f2(v2[0])} (N={v2[1]})',
            'NA' if v1[0] is None or v2[0] is None else f'{v2[0]-v1[0]:+.2f} pp', 'no (direction and significance vs Target unchanged)' if not wga else 'no (non-evaluable before and after)')
    if (o[0]!=v2[0]) or (o[1]!=v2[1]):
        add('official FR@K tables: presentation_figures_final/persistbench_all_methods_all_corpora.csv; thesis_defense_assets_bundle/data/...; thesis/analysis/judge_robustness/qwen_vs_gemma_frk.json (Qwen-judge rows); appendix persistbench_frk_complete.tsv [official rows]', cell, 'official', f'{f2(o[0])} (N={o[1]})', f'{f2(v2[0])} (N={v2[1]})',
            'NA' if o[0] is None or v2[0] is None else f'{v2[0]-o[0]:+.2f} pp', 'YES for WGA: a number becomes "not evaluable"' if wga else 'no (direction and significance vs Target unchanged)')
# C: validity counts
for k,v in VAL.items():
    grp,ds,model,cond,cat=k
    if grp!='main' or (v['v1']==v['v2'] and v['z1']==v['z2']): continue
    add('appendix generation_validity_complete.tsv', f'{ds} | {model} | {cond} | {cat}', 'v1', f"valid {v['v1']}/{v['n']} ({100*v['v1']/v['n']:.2f}%), zero-valid scenarios {v['z1']}", f"valid {v['v2']}/{v['n']} ({100*v['v2']/v['n']:.2f}%), zero-valid scenarios {v['z2']}", f"{v['v2']-v['v1']:+d} valid generations", 'no')
# D: full-prompt robustness (recompute with each validator)
def status(gens,k,key):
    vs=[q['score'] for q in gens[:k] if q['score'] is not None and (key is None or q[key])]
    return None if not vs else (max(vs)>=3)
def sign_p(a,b):
    n=a+b
    if n==0: return 1.0
    m=min(a,b); return min(1.0,2*sum(comb(n,i) for i in range(m+1))/2**n)
byk={(x['group'],x['dataset'],x['model'],x['cond']):x for x in ALL}
fp_rows=[]
for cat in ('sycophancy','cross_domain'):
    ds=f'MUSE-News fullprompt-{cat}'
    for cond in ('Target','RMU','SatImp','SimNPO'):
        orig=byk[('main','MUSE-News','Qwen2.5-7B-Instruct',cond)]; full=byk[('fullprompt',ds,'Qwen2.5-7B-Instruct',cond)]
        ot=byk[('main','MUSE-News','Qwen2.5-7B-Instruct','Target')]; ft=byk[('fullprompt',ds,'Qwen2.5-7B-Instruct','Target')]
        rec={}
        for var,key in (('v1','valid'),('v2','v2valid')):
            fo=frk(orig['L'][cat],cat,3,var); ff=frk(full['L'][cat],cat,3,var); fot=frk(ot['L'][cat],cat,3,var); fft=frk(ft['L'][cat],cat,3,var)
            tr=Counter()
            for eid,gens in full['L'][cat].items():
                a=status(ft['L'][cat][eid],3,key); b=status(gens,3,key)
                if a is None or b is None: tr['NE']+=1
                else: tr[f"{'F' if a else 'S'}->{'F' if b else 'S'}"]+=1
            nval=sum(q[key] for gens in full['L'][cat].values() for q in gens); ntot=sum(len(gens) for gens in full['L'][cat].values())
            rec[var]=dict(orig=fo,full=ff,dorig=None if fo[0] is None else fo[0]-fot[0],dfull=None if ff[0] is None else ff[0]-fft[0],sf=tr['S->F'],fs=tr['F->S'],p=sign_p(tr['S->F'],tr['F->S']),nval=nval,ntot=ntot)
        fp_rows.append((cat,cond,rec))
hdr=['category','condition','orig FR@3 v1','orig N v1','orig FR@3 v2','orig N v2','full-prompt FR@3 v1','full N v1','full-prompt FR@3 v2','full N v2','orig delta vs Target v1','orig delta v2','full delta vs Target v1','full delta v2','S->F v1','F->S v1','S->F v2','F->S v2','paired p v1','paired p v2','full-prompt validity v1','full-prompt validity v2']
out=[]
for cat,cond,r in fp_rows:
    a,b=r['v1'],r['v2']
    out.append([cat,cond,f2(a['orig'][0]),a['orig'][1],f2(b['orig'][0]),b['orig'][1],f2(a['full'][0]),a['full'][1],f2(b['full'][0]),b['full'][1],f2(a['dorig']),f2(b['dorig']),f2(a['dfull']),f2(b['dfull']),a['sf'],a['fs'],b['sf'],b['fs'],f"{a['p']:.4f}",f"{b['p']:.4f}",f"{a['nval']}/{a['ntot']}",f"{b['nval']}/{b['ntot']}"])
    if (a['orig'][0],a['orig'][1],a['full'][0],a['full'][1],a['sf'],a['fs'],a['nval'])!=(b['orig'][0],b['orig'][1],b['full'][0],b['full'][1],b['sf'],b['fs'],b['nval']):
        add('appendix fullprompt_robustness.tsv', f'{cat} | {cond}', 'v1', f"orig FR@3 {f2(a['orig'][0])} (N={a['orig'][1]}); full {f2(a['full'][0])} (N={a['full'][1]}); S->F/F->S {a['sf']}/{a['fs']}; p={a['p']:.4f}; validity {a['nval']}/{a['ntot']}",
            f"orig FR@3 {f2(b['orig'][0])} (N={b['orig'][1]}); full {f2(b['full'][0])} (N={b['full'][1]}); S->F/F->S {b['sf']}/{b['fs']}; p={b['p']:.4f}; validity {b['nval']}/{b['ntot']}", f"full-prompt FR@3 {b['full'][0]-a['full'][0]:+.2f} pp; orig {0 if a['orig'][0] is None else b['orig'][0]-a['orig'][0]:+.2f} pp" , 'no (same sign, same significance)')
tsv('fullprompt_robustness_v1_vs_v2.tsv',hdr,out)
# E: agreement
ag=json.load(open(S+'_agree.json'))
add('appendix judge_agreement.tsv','MUSE-News Qwen sycophancy 5 conds | scenario-level FR@3 status agreement (validity-aware)','v1',f"{ag['v1'][0]:.2f}% / kappa {ag['v1'][1]:.4f} / N={ag['v1'][2]}",f"{ag['v2'][0]:.2f}% / kappa {ag['v2'][1]:.4f} / N={ag['v2'][2]}",f"{ag['v2'][0]-ag['v1'][0]:+.2f} pp; kappa {ag['v2'][1]-ag['v1'][1]:+.4f}",'no (still poor agreement)')
# G: paradox
for r in csv.DictReader(open(OUT/'paradox_strict_broad_v1_vs_v2.tsv'),delimiter='\t'):
    if r['strict delta v1 (pp)']!=r['strict delta v2 (pp)'] or r['PB validity before v1 %']!=r['PB validity before v2 %'] or r['PB validity after v1 %']!=r['PB validity after v2 %']:
        add('mechanistic/outputs/benchmark_paradox/{condition_level_results,strict_paradox_classification,validity_summary,intersection_valid_results}.csv', f"{r['dataset']} | {r['model']} | {r['method']}",'v1 (as stored)',
            f"validity {r['PB validity before v1 %']}%->{r['PB validity after v1 %']}%; strict {r['strict failure before v1 %']}->{r['strict failure after v1 %']} ({r['strict delta v1 (pp)']} pp); quadrant {r['strict quadrant v1 (recomputed)']}",
            f"validity {r['PB validity before v2 %']}%->{r['PB validity after v2 %']}%; strict {r['strict failure before v2 %']}->{r['strict failure after v2 %']} ({r['strict delta v2 (pp)']} pp); quadrant {r['strict quadrant v2']}",
            f"strict delta {float(r['strict delta change v2-v1 (pp)']):+.2f} pp", 'QUADRANT LABEL CHANGES (|delta|<0.25 pp on both sides of zero)' if r['quadrant changes v1->v2']=='YES' else 'no')
# F: judge robustness table (official -> v2)
for r in csv.DictReader(open(OUT/'judge_robustness_v2.tsv'),delimiter='\t'):
    if (r['official FR (%)'],r['official N'])!=(r['validity v2 FR (%)'],r['v2 N']):
        add('appendix judge_robustness.tsv (stored thesis/analysis/judge_robustness/qwen_vs_gemma_frk.json)', f"{r['dataset']} | {r['model']} | {r['judge']} judge | {r['condition']} | {r['category']} | FR@{r['K']}",'official (not validity-gated)',f"{r['official FR (%)']} (N={r['official N']})",f"{r['validity v2 FR (%)']} (N={r['v2 N']})",
            'NA' if 'NA' in (r['official FR (%)'],r['validity v2 FR (%)']) else f"{float(r['validity v2 FR (%)'])-float(r['official FR (%)']):+.2f} pp",'YES for WGA (not evaluable)' if (r['model'],r['condition'])==('Llama-2-7B','WGA') else 'no')
tsv('thesis_impact_changes.tsv',['table / artifact','cell','current procedure','current number','final number (v2)','difference','interpretation changes?'],rows)
print('impact rows',len(rows)); print(Counter(r[0][:60] for r in rows))
for c in out: print(c)
