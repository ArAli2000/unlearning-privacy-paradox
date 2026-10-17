#!/usr/bin/env python3
"""Analyze the frozen single-case PersistBench representation extraction."""
import json
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np,pandas as pd,torch

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'mechanistic/outputs/single_persistbench_case'
def metrics(a,b):
 d=b-a; return float(torch.nn.functional.cosine_similarity(a,b,dim=0)),float(d.norm()),float(d.norm()/a.norm()),float(a.norm()),float(b.norm())
def main():
 meta=json.loads((OUT/'extraction_metadata.json').read_text()); man=pd.read_csv(OUT/'position_manifest.csv'); reps={x:torch.load(OUT/f'{x.lower()}_representations.pt',map_location='cpu',weights_only=True) for x in ['BASE','RMU','WGA']}
 for x in reps.values():
  for v in x.values(): assert v.dtype==torch.float32 and torch.isfinite(v).all()
 selected=sorted(set(i for _,r in man.iterrows() if r.token_start>=0 for i in range(int(r.token_start),int(r.token_end_exclusive))))
 ix={p:i for i,p in enumerate(selected)}; rows=[]
 for _,s in man[man.token_start>=0].iterrows():
  jj=[ix[i] for i in range(int(s.token_start),int(s.token_end_exclusive))]
  for layer in range(29):
   b=reps['BASE']['prompt_selected'][layer,jj].mean(0)
   r=reps['RMU']['prompt_selected'][layer,jj].mean(0); w=reps['WGA']['prompt_selected'][layer,jj].mean(0)
   c,l,rel,bn,rn=metrics(b,r); _,wl,wrel,_,wn=metrics(b,w); dc=float(torch.nn.functional.cosine_similarity(r-b,w-b,dim=0))
   rows.append({'analysis_mode':'shared_prompt','position':s.span_label,'layer':layer,'cosine_base_rmu':c,'l2_rmu_minus_base':l,'relative_l2_rmu_minus_base':rel,'base_norm':bn,'rmu_norm':rn,'l2_wga_minus_base':wl,'relative_l2_wga_minus_base':wrel,'wga_norm':wn,'rmu_vs_wga_delta_cosine':dc})
 drift=pd.DataFrame(rows); drift.to_csv(OUT/'representation_drift.csv',index=False)
 inj=meta['injection']; lo=inj['window_generated_token_start']; hi=inj['window_generated_token_end_exclusive']; shared=[]
 for gi in range(lo,hi):
  for layer in range(29):
   b=reps['BASE']['shared_generated'][layer,gi]; r=reps['RMU']['shared_generated'][layer,gi]; w=reps['WGA']['shared_generated'][layer,gi]
   c,l,rel,bn,rn=metrics(b,r); _,wl,wrel,_,wn=metrics(b,w)
   shared.append({'analysis_mode':'shared_rmu_response','generated_token_index':gi,'relative_to_injection':gi-inj['generated_token_start'],'token':meta['prompt_reconstruction']['decoded_tokens'][0] if False else '', 'layer':layer,'cosine_base_rmu':c,'l2_rmu_minus_base':l,'relative_l2_rmu_minus_base':rel,'base_norm':bn,'rmu_norm':rn,'l2_wga_minus_base':wl,'relative_l2_wga_minus_base':wrel,'wga_norm':wn,'rmu_vs_wga_delta_cosine':float(torch.nn.functional.cosine_similarity(r-b,w-b,dim=0))})
 traj=pd.DataFrame(shared); lens=pd.read_csv(OUT/'logit_lens_trajectory.csv'); tokenmap=lens[['generated_token_index','target_token']].drop_duplicates().set_index('generated_token_index').target_token.to_dict(); traj['token']=traj.generated_token_index.map(tokenmap)
 # Own trajectories are descriptive only: record each model's norm at every own token/layer.
 own=[]
 for model in reps:
  x=reps[model]['own_generated']
  for layer in range(29):
   for gi in range(x.shape[1]): own.append({'analysis_mode':'own_trajectory','model':model,'generated_token_index':gi,'layer':layer,'hidden_norm':float(x[layer,gi].norm())})
 pd.concat([traj,pd.DataFrame(own)],ignore_index=True,sort=False).to_csv(OUT/'generated_token_trajectory.csv',index=False)
 # Plots focused on the state predicting the first injected token (response index gi-1).
 first=inj['generated_token_start']; pred=traj[traj.generated_token_index==first-1]
 fig,ax=plt.subplots(figsize=(8,5));ax.plot(pred.layer,pred.relative_l2_rmu_minus_base,label='RMU−BASE');ax.plot(pred.layer,pred.relative_l2_wga_minus_base,label='WGA−BASE');ax.axvspan(14,19,alpha=.1);ax.axvspan(22,28,alpha=.1);ax.set(xlabel='Layer/state (0=embedding)',ylabel='Relative L2 drift',title='Shared replay: state immediately before first private token');ax.legend();fig.tight_layout();fig.savefig(OUT/'pre_injection_representation_drift.png',dpi=190);plt.close(fig)
 q=lens[lens.generated_token_index==first]
 fig,ax=plt.subplots(figsize=(9,5));
 for model,g in q.groupby('model'):ax.plot(g.layer,g.log_probability,label=model)
 ax.axvspan(14,19,alpha=.1);ax.axvspan(22,28,alpha=.1);ax.set(xlabel='Projected layer/state',ylabel='Log probability of first injected token',title='Ordinary logit lens before first injection');ax.legend();fig.tight_layout();fig.savefig(OUT/'first_injected_token_logit_lens.png',dpi=190);plt.close(fig)
 # Phrase heatmap: RMU minus BASE target-token log probability across injected tokens.
 z=lens[lens.is_injected_phrase].pivot_table(index='generated_token_index',columns=['model','layer'],values='log_probability'); arr=np.vstack([z['RMU'].loc[i].values-z['BASE'].loc[i].values for i in z.index])
 fig,ax=plt.subplots(figsize=(10,4));im=ax.imshow(arr,aspect='auto',cmap='coolwarm');ax.set(yticks=range(len(z)),yticklabels=[tokenmap[i] for i in z.index],xlabel='Layer/state',ylabel='Injected target token',title='RMU − BASE logit-lens support');fig.colorbar(im,ax=ax,label='Δ log probability');fig.tight_layout();fig.savefig(OUT/'injected_phrase_logit_difference.png',dpi=190);plt.close(fig)
 # Machine-readable compact findings for report generation/audit.
 firstq=q.pivot(index='layer',columns='model',values=['probability','rank','log_probability']); firstq.columns=['_'.join(map(str,x)) for x in firstq.columns]; firstq.reset_index().to_csv(OUT/'first_injected_token_summary.csv',index=False)
 print('Prompt largest RMU relative drift:',drift.loc[drift.groupby('position').relative_l2_rmu_minus_base.idxmax(),['position','layer','relative_l2_rmu_minus_base']].to_string(index=False))
 print('\nFirst-token lens L22-28:\n',q[q.layer>=22][['model','layer','target_token','probability','rank','log_probability']].to_string(index=False))
 print('\nContinuations:\n',pd.read_csv(OUT/'continuation_comparison.csv').to_string(index=False))
if __name__=='__main__':main()
