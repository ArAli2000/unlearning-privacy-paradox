#!/usr/bin/env python3
"""CPU-only population analysis of privacy-role mean-pooled representations."""
import csv,json,math
from itertools import combinations
from pathlib import Path
import torch
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np,pandas as pd

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'mechanistic/outputs/privacy_position_analysis'; POP=ROOT/'mechanistic/outputs/privacy_population_12v12/sample_manifest.csv'
ROLES=['sensitive_information','data_subject','recipient','transmission_action','decision_instruction','final_prompt_token']; LABELS=['Emb']+[f'L{i}' for i in range(1,29)]
def cos(a,b):
 n=np.linalg.norm(a)*np.linalg.norm(b); return float(np.dot(a,b)/n) if n>1e-12 else np.nan
def stats(x):
 a=np.asarray(x,float); return float(np.mean(a)),float(np.median(a)),float(np.std(a,ddof=1))
def boot_ci(x,n=10000):
 a=np.asarray(x,float); rng=np.random.default_rng(415); means=np.mean(rng.choice(a,(n,len(a)),replace=True),axis=1); return np.quantile(means,[.025,.975]).tolist()
def signflip_p(x,n=20000):
 a=np.asarray(x,float); obs=abs(a.mean()); rng=np.random.default_rng(1); null=np.abs((rng.choice([-1,1],(n,len(a)))*a).mean(1)); return float((1+(null>=obs).sum())/(n+1))
def paircos(v): return [cos(v[i],v[j]) for i,j in combinations(range(len(v)),2)]
def main():
 pop=pd.read_csv(POP); samples=pop.sample_id.tolist(); groups=dict(zip(pop.sample_id,pop.group)); pairs={p:{g:s for g,s in zip(x.group,x.sample_id)} for p,x in pop.groupby('pair_id')}
 acts={}; validation=[]
 for sid in samples:
  md=json.loads((OUT/'activations'/sid/'metadata.json').read_text()); hashes=[]
  for method in ['base','rmu','wga']:
   obj=torch.load(OUT/'activations'/sid/f'{method}_position_activations.pt',map_location='cpu',weights_only=True); hashes.append(obj['token_ids_sha256'])
   acts[sid,method]={}
   for role in ROLES:
    z=obj['roles'][role]; t=z['mean']; per=z['per_token']; ok=tuple(t.shape)==(29,3584) and t.dtype==torch.float32 and t.device.type=='cpu' and torch.isfinite(t).all().item() and per.dtype==torch.float32 and torch.isfinite(per).all().item() and tuple(per.shape[1:])==(29,3584)
    validation.append({'sample_id':sid,'model':method.upper(),'role':role,'mean_shape':str(list(t.shape)),'per_token_shape':str(list(per.shape)),'dtype':str(t.dtype),'device':t.device.type,'finite':bool(torch.isfinite(t).all()),'token_ids_sha256':obj['token_ids_sha256'],'token_indices':json.dumps(z['token_indices']),'valid':ok})
    if not ok: raise RuntimeError(f'Invalid {sid}/{method}/{role}')
    acts[sid,method][role]=t.numpy()
  if len(set(hashes))!=1 or hashes[0]!=md['token_ids_sha256']: raise RuntimeError(f'Hash mismatch {sid}')
 pd.DataFrame(validation).to_csv(OUT/'position_extraction_validation.csv',index=False)
 per=[]; deltas={}
 for sid in samples:
  for role in ROLES:
   b=acts[sid,'base'][role]
   for method in ['rmu','wga']:
    a=acts[sid,method][role]; d=a-b; deltas[sid,method,role]=d
    for l in range(29):
     per.append({'pair_id':pop.loc[pop.sample_id==sid,'pair_id'].iloc[0],'sample_id':sid,'group':groups[sid],'role':role,'layer':LABELS[l],'layer_index':l,'method':method.upper(),'cosine_base_after':cos(b[l],a[l]),'raw_l2':float(np.linalg.norm(d[l])),'relative_l2_drift':float(np.linalg.norm(d[l])/np.linalg.norm(b[l])),'base_norm':float(np.linalg.norm(b[l])),'after_norm':float(np.linalg.norm(a[l]))})
 perdf=pd.DataFrame(per); perdf.to_csv(OUT/'per_sample_position_layer_metrics.csv',index=False)
 group=[]; directional=[]; matched=[]; specificity=[]
 for role in ROLES:
  for l,lab in enumerate(LABELS):
   for method in ['rmu','wga']:
    stable=[s for s in samples if groups[s]=='stable']; degraded=[s for s in samples if groups[s]=='degraded']; sv=np.stack([deltas[s,method,role][l] for s in stable]); dv=np.stack([deltas[s,method,role][l] for s in degraded])
    sr=perdf.query('role==@role and layer_index==@l and method==@method.upper() and group=="stable"').relative_l2_drift.to_numpy(); dr=perdf.query('role==@role and layer_index==@l and method==@method.upper() and group=="degraded"').relative_l2_drift.to_numpy()
    pdiff=[]
    for pid,q in pairs.items():
     x=q['stable']; y=q['degraded']; rs=float(np.linalg.norm(deltas[x,method,role][l])/np.linalg.norm(acts[x,'base'][role][l])); rd=float(np.linalg.norm(deltas[y,method,role][l])/np.linalg.norm(acts[y,'base'][role][l])); pc=cos(deltas[x,method,role][l],deltas[y,method,role][l]); pdiff.append(rd-rs)
     if method=='rmu': matched.append({'pair_id':pid,'stable_sample_id':x,'degraded_sample_id':y,'role':role,'layer':lab,'layer_index':l,'rmu_stable_relative_drift':rs,'rmu_degraded_relative_drift':rd,'rmu_pair_delta_cosine':pc,'rmu_pair_separation':1-pc})
     else:
      matched[-len(pairs)+list(pairs).index(pid)].update({'wga_stable_relative_drift':rs,'wga_degraded_relative_drift':rd,'wga_pair_delta_cosine':pc,'wga_pair_separation':1-pc})
    sm,sdm,ss=stats(sr); dm,ddm,ds=stats(dr); pm,pmed,ps=stats(pdiff); ci=boot_ci(pdiff)
    gmcos=cos(sv.mean(0),dv.mean(0)); ws=paircos(sv); wd=paircos(dv); bg=[cos(x,y) for x in sv for y in dv]
    group.append({'role':role,'layer':lab,'layer_index':l,'method':method.upper(),'stable_mean_relative_drift':sm,'stable_median_relative_drift':sdm,'stable_std_relative_drift':ss,'degraded_mean_relative_drift':dm,'degraded_median_relative_drift':ddm,'degraded_std_relative_drift':ds,'paired_diff_mean':pm,'paired_diff_median':pmed,'paired_diff_std':ps,'paired_bootstrap_ci_low':ci[0],'paired_bootstrap_ci_high':ci[1],'paired_signflip_p':signflip_p(pdiff)})
    directional.append({'role':role,'layer':lab,'layer_index':l,'method':method.upper(),'group_mean_delta_cosine':gmcos,'separation':1-gmcos,'within_stable_mean_cosine':np.mean(ws),'within_stable_median_cosine':np.median(ws),'within_degraded_mean_cosine':np.mean(wd),'within_degraded_median_cosine':np.median(wd),'between_group_mean_cosine':np.mean(bg),'between_group_median_cosine':np.median(bg)})
   rr=directional[-2]; ww=directional[-1]; mrows=[x for x in matched if x['role']==role and x['layer_index']==l]; gaps=np.array([x['rmu_pair_separation']-x['wga_pair_separation'] for x in mrows]); ci=boot_ci(gaps)
   for x,g in zip(mrows,gaps): x['pair_specificity_gap']=g
   specificity.append({'role':role,'layer':lab,'layer_index':l,'rmu_separation':rr['separation'],'wga_separation':ww['separation'],'specificity_gap':rr['separation']-ww['separation'],'matched_gap_mean':gaps.mean(),'matched_gap_median':np.median(gaps),'matched_gap_std':gaps.std(ddof=1),'matched_bootstrap_ci_low':ci[0],'matched_bootstrap_ci_high':ci[1],'matched_signflip_p':signflip_p(gaps)})
 gdf=pd.DataFrame(group); ddf=pd.DataFrame(directional); mdf=pd.DataFrame(matched); sdf=pd.DataFrame(specificity)
 gdf.to_csv(OUT/'group_position_layer_metrics.csv',index=False); ddf.to_csv(OUT/'directional_position_layer_metrics.csv',index=False); mdf.to_csv(OUT/'matched_pair_position_metrics.csv',index=False); sdf.to_csv(OUT/'rmu_vs_wga_specificity.csv',index=False)
 anchor=[]
 for role in ROLES:
  for l,lab in enumerate(LABELS):
   rc=cos(deltas['main1','rmu',role][l],deltas['main415','rmu',role][l]); wc=cos(deltas['main1','wga',role][l],deltas['main415','wga',role][l]); anchor.append({'role':role,'layer':lab,'layer_index':l,'rmu_delta_cosine':rc,'wga_delta_cosine':wc,'specificity_gap':(1-rc)-(1-wc)})
 pd.DataFrame(anchor).to_csv(OUT/'anchor_main1_main415.csv',index=False)
 regions={'early':range(0,11),'middle':range(11,20),'late':range(20,29)}; reg=[]
 for role in ROLES:
  for name,ix in regions.items():
   q=sdf[(sdf.role==role)&sdf.layer_index.isin(ix)]; reg.append({'role':role,'region':name,'centroid_specificity_gap_mean':q.specificity_gap.mean(),'matched_specificity_gap_mean':q.matched_gap_mean.mean(),'matched_specificity_gap_median_across_layers':q.matched_gap_median.mean()})
 pd.DataFrame(reg).to_csv(OUT/'role_region_summary.csv',index=False)
 # Individual trajectories and group means remain visible in magnitude plots.
 for role in ROLES:
  for method in ['RMU','WGA']:
   fig,ax=plt.subplots(figsize=(11,5)); q=perdf[(perdf.role==role)&(perdf.method==method)]
   for grp,color in [('stable','C0'),('degraded','C1')]:
    z=q[q.group==grp];
    for _,s in z.groupby('sample_id'): ax.plot(s.layer_index,s.relative_l2_drift,color=color,alpha=.22,lw=.8)
    mean=z.groupby('layer_index').relative_l2_drift.mean(); ax.plot(mean.index,mean,color=color,lw=2.5,label=grp)
   ax.set(xticks=range(29),xticklabels=LABELS,ylabel='Relative L2 drift',title=f'{method}: {role}'); ax.tick_params(axis='x',rotation=60); ax.legend(); fig.tight_layout(); fig.savefig(OUT/f'magnitude_{method.lower()}_{role}.png',dpi=180); plt.close(fig)
 for value,name,title in [('rmu_separation','rmu_separation_heatmap','RMU separation'),('wga_separation','wga_separation_heatmap','WGA separation'),('specificity_gap','rmu_minus_wga_specificity_heatmap','RMU minus WGA specificity')]:
  mat=sdf.pivot(index='role',columns='layer_index',values=value).reindex(ROLES); fig,ax=plt.subplots(figsize=(14,4)); im=ax.imshow(mat,aspect='auto'); ax.set(xticks=range(29),xticklabels=LABELS,yticks=range(6),yticklabels=ROLES,title=title); ax.tick_params(axis='x',rotation=60); fig.colorbar(im,ax=ax); fig.tight_layout(); fig.savefig(OUT/f'{name}.png',dpi=180); plt.close(fig)
 print('Validated and analyzed 24 samples; strongest specificity rows:'); print(sdf.nlargest(15,'specificity_gap')[['role','layer','rmu_separation','wga_separation','specificity_gap','matched_gap_mean']].to_string(index=False))
if __name__=='__main__': main()
