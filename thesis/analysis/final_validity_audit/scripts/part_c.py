import pickle, csv, json
from pathlib import Path
from common import *
from collections import Counter
S=str(Path(__file__).parent)+'/'
P=pickle.load(open(S+'_partb.pkl','rb')); CMP, FR, VAL = P['CMP'], P['FR'], P['VAL']
f=lambda v, nd=2: 'NA' if v is None else f'{v:.{nd}f}'
# ---------- overall magnitude of differences (main, excluding WGA-Books-Llama2)
diffs=[(k,abs(v['r']['v2'][0]-v['r']['official'][0]),abs(v['r']['v2'][0]-v['r']['v1'][0]),abs(v['r']['v1'][0]-v['r']['official'][0])) for k,v in CMP.items() if k[0]=='main' and not v['wga'] and v['r']['v2'][0] is not None and v['r']['official'][0] is not None]
print('main cells x K (excl WGA):',len(diffs),'max |v2-off|',max(d[1] for d in diffs),'max |v2-v1|',max(d[2] for d in diffs),'max |v1-off|',max(d[3] for d in diffs))
for lab,i in (('v1-off',3),('v2-off',1),('v2-v1',2)):
    top=sorted(diffs,key=lambda d:-d[i])[:6]; print(lab,[(d[0][1][:9]+'/'+d[0][2][:5]+'/'+d[0][3]+'/'+d[0][4][:5]+'/K'+str(d[0][5]),round(d[i],2)) for d in top])
# ---------- headline checks
def g(group,ds,model,cond,cat,k,md): return FR[(group,ds,model,cond,cat,k)][md]
rows=[]
def check(name, fn):
    res={md:fn(md) for md in ('official','v1','v2','v2r')}
    rows.append([name]+[res[m] for m in ('official','v1','v2','v2r')])
NQ=('main','MUSE-News','Qwen2.5-7B-Instruct'); BQ=('main','MUSE-Books','Qwen2.5-7B-Instruct'); BL=('main','MUSE-Books','Llama-2-7B')
def delta(base,cond,cat,k,md):
    a=g(*base,cond,cat,k,md)[0]; t=g(*base,'Target',cat,k,md)[0]
    return None if a is None or t is None else a-t
for cat in ('sycophancy','cross_domain'):
    for cond in ('SatImp','SimNPO','RMU','WGA'):
        check(f'MUSE-News Qwen {cat} {cond}: delta vs Target at K=1/2/3 (pp)', lambda md,cat=cat,cond=cond: ' / '.join(f(delta(NQ,cond,cat,k,md)) for k in (1,2,3)))
check('MUSE-News Qwen beneficial_memory (K=1) delta RMU/WGA/SatImp/SimNPO (pp)', lambda md: ' / '.join(f(delta(NQ,c,'beneficial_memory_usage',1,md)) for c in ('RMU','WGA','SatImp','SimNPO')))
H1=lambda md: all((delta(NQ,c,'sycophancy',k,md) or 0)>0 for c in ('SatImp','SimNPO') for k in (1,2,3))
check('CLAIM: MUSE-News Qwen sycophancy worsens at every K for SatImp AND SimNPO', lambda md: 'HOLDS' if H1(md) else 'FAILS')
H2=lambda md: all((delta(NQ,c,'cross_domain',k,md) if delta(NQ,c,'cross_domain',k,md) is not None else 9)<0 for c in ('SatImp','SimNPO') for k in (1,2,3))
check('CLAIM: MUSE-News Qwen cross-domain improves (delta<0) for SatImp AND SimNPO at every K', lambda md: 'HOLDS' if H2(md) else 'FAILS')
for cond in ('SatImp','SimNPO'):
    check(f'MUSE-Books Qwen sycophancy {cond}: delta vs Target K=1/2/3 (pp)  [claim: does not replicate (<=0)]', lambda md,cond=cond: ' / '.join(f(delta(BQ,cond,'sycophancy',k,md)) for k in (1,2,3)))
check('MUSE-Books Llama-2 WGA: FR@3 cross_domain / sycophancy (N)', lambda md: ' / '.join(f"{f(g(*BL,'WGA',c,3,md)[0])} (N={g(*BL,'WGA',c,3,md)[1]})" for c in ('cross_domain','sycophancy')))
# full prompt
for cat in ('sycophancy','cross_domain'):
    gp='fullprompt'; ds=f'MUSE-News fullprompt-{cat}'
    for cond in ('RMU','SatImp','SimNPO'):
        k=3
        check(f'FULL-PROMPT {cat} {cond}: FR@3 (N) / delta vs Target (pp) / paired p', lambda md,cat=cat,cond=cond,ds=ds: f"{f(g(gp,ds,'Qwen2.5-7B-Instruct',cond,cat,3,md)[0])} (N={g(gp,ds,'Qwen2.5-7B-Instruct',cond,cat,3,md)[1]}) / {f(delta((gp,ds,'Qwen2.5-7B-Instruct'),cond,cat,3,md))} / {f(CMP[(gp,ds,'Qwen2.5-7B-Instruct',cond,cat,3)]['ps'].get(md),3)}")
with open(OUT/'headline_conclusion_checks.tsv','w',newline='') as fo:
    w=csv.writer(fo,delimiter='\t',lineterminator='\n'); w.writerow(['check','official','validity v1','validity v2','v2r (repetition sensitivity)']); w.writerows(rows)
for r in rows: print(' | '.join(map(str,r)))
