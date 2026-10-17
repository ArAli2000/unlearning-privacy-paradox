#!/usr/bin/env python3
import csv,json,math,os
from pathlib import Path
import numpy as np,pandas as pd,torch
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from common import *
MODELS=('BASE','SatImp','SimNPO');SEED=20260828;BOOT=2000
def cos(a,b):
 d=torch.linalg.vector_norm(a,dim=-1)*torch.linalg.vector_norm(b,dim=-1);return torch.sum(a*b,dim=-1)/d
def main():
 (WORK/'plots').mkdir(exist_ok=True);frames=[];D={}
 for m in MODELS:
  frames.append(pd.read_csv(WORK/'representations'/m.lower()/'mcq_readout_per_example.csv'))
  D[m]={v:torch.load(WORK/'representations'/m.lower()/f'{v}_directions.pt',map_location='cpu',weights_only=True) for v in ('original','swapped')}
 f=pd.concat(frames,ignore_index=True); f.to_csv(WORK/'analysis/mcq_readout_per_example.csv',index=False)
 summary=f.groupby(['model','variant','state_index','state_label']).agg(n=('example_id','count'),mean_margin=('safe_minus_syc_logit_margin','mean'),mean_probability_gap=('probability_gap','mean'),accuracy=('safe_correct','mean')).reset_index()
 first={}
 for (m,v),g in summary.groupby(['model','variant']):
  z=g[g.mean_margin>0];first[f'{m}:{v}']=int(z.state_index.min()) if len(z) else None
 rows=[];bootrows=[];rng=np.random.default_rng(SEED)
 for variant in ('original','swapped'):
  base=D['BASE'][variant]['mean_direction'].double()
  for m in MODELS:
   x=D[m][variant]['mean_direction'].double(); c=cos(base,x)
   for i in range(29): rows.append({'variant':variant,'model':m,'state_index':i,'state_label':'embedding' if i==0 else f'L{i}','cosine_to_BASE':float(c[i]),'direction_norm':float(torch.linalg.vector_norm(x[i]))})
  if not (WORK/'analysis/bootstrap_intervals.csv').exists():
   indices=rng.integers(0,50,size=(BOOT,50))
   for m in ('SatImp','SimNPO'):
    a=D['BASE'][variant]['per_example_differences'].double();b=D[m][variant]['per_example_differences'].double(); vals=[]
    for ix in indices:
     vals.append(cos(a[ix].mean(0),b[ix].mean(0)).numpy())
    vals=np.asarray(vals);point=cos(a.mean(0),b.mean(0)).numpy()
    for i in range(29):bootrows.append({'variant':variant,'model':m,'state_index':i,'state_label':'embedding' if i==0 else f'L{i}','point_estimate':point[i],'ci_lower_2_5':np.percentile(vals[:,i],2.5),'ci_upper_97_5':np.percentile(vals[:,i],97.5),'bootstrap_n':BOOT,'seed':SEED})
 # Semantic original-vs-swapped within each model.
 for m in MODELS:
  c=cos(D[m]['original']['mean_direction'].double(),D[m]['swapped']['mean_direction'].double())
  for i in range(29):rows.append({'variant':'original_vs_swapped_semantic','model':m,'state_index':i,'state_label':'embedding' if i==0 else f'L{i}','cosine_to_BASE':float(c[i]),'direction_norm':math.nan})
 lm=pd.DataFrame(rows);lm.to_csv(WORK/'analysis/layer_metrics.csv',index=False)
 if bootrows: pd.DataFrame(bootrows).to_csv(WORK/'analysis/bootstrap_intervals.csv',index=False)
 def plot_lines(data,y,title,file,groups=('BASE','SatImp','SimNPO')):
  fig,ax=plt.subplots(figsize=(10,5.5));
  for m in groups:
   q=data[data.model==m];ax.plot(q.state_index,q[y],label=m)
  ax.axhline(0,color='k',lw=.7);ax.grid(alpha=.25);ax.legend();ax.set(xlabel='State (0=embedding, 1–28=layers)',ylabel=y,title=title);fig.tight_layout();fig.savefig(WORK/'plots'/file,dpi=190);plt.close(fig)
 plot_lines(summary[summary.variant=='original'],'mean_margin','Sycophancy MCQ safe-minus-sycophantic logit','sycophancy_mcq_safe_minus_syc_logit.png')
 plot_lines(lm[(lm.variant=='original') & (lm.model!='BASE')],'cosine_to_BASE','Sycophancy MCQ direction cosine to BASE','sycophancy_mcq_direction_cosine.png',('SatImp','SimNPO'))
 privacy=pd.read_csv(ROOT/os.environ.get('SYCOPHANCY_MCQ_PRIVACY_DIRECTIONS','mechanistic/outputs/privacy_collapse_muse_news_qwen25_7b/direction_norms_and_cosines.csv'))
 fig,ax=plt.subplots(figsize=(11,6))
 for m in ('SatImp','SimNPO'):
  p=privacy[(privacy.dataset=='privacy')&(privacy.model==m)];s=lm[(lm.variant=='original')&(lm.model==m)]
  ax.plot(p.state_index,p.cosine_to_base,label=f'PrivacyLens {m}');ax.plot(s.state_index,s.cosine_to_BASE,':',lw=2,label=f'PB sycophancy {m}')
 ax.grid(alpha=.25);ax.legend(ncol=2);ax.set(xlabel='State',ylabel='Cosine to BASE',title='Controlled probe direction comparison');fig.tight_layout();fig.savefig(WORK/'plots/controlled_probe_direction_comparison.png',dpi=190);plt.close(fig)
 native=pd.read_csv(ROOT/os.environ.get('SYCOPHANCY_MCQ_NATIVE_FR','mechanistic/outputs/muse_books_weekly_update_analysis/persistbench_fr_at_k.csv'))
 fr={m:float(native[(native.category=='sycophancy')&(native.model==m)&(native.k==1)].rate_pct.iloc[0]) for m in MODELS}
 final=summary[(summary.variant=='original')&(summary.state_index==28)].set_index('model')
 fig,ax=plt.subplots(figsize=(8,5));x=np.arange(3);ax.bar(x-.18,[100*final.loc[m,'accuracy'] for m in MODELS],.36,label='Controlled MCQ accuracy');ax.bar(x+.18,[fr[m] for m in MODELS],.36,label='Native sycophancy FR@1');ax.set_xticks(x,MODELS);ax.set_ylabel('Percent');ax.legend();ax.set_title('Explicit recognition vs native behavior');fig.tight_layout();fig.savefig(WORK/'plots/recognition_vs_native_behavior.png',dpi=190);plt.close(fig)
 behavior={}
 for m in MODELS:
  behavior[m]={}
  for v in ('original','swapped'):
   q=summary[(summary.model==m)&(summary.variant==v)&(summary.state_index==28)].iloc[0]
   raw=f[(f.model==m)&(f.variant==v)&(f.state_index==28)]
   behavior[m][v]={'choosing_safe':int(raw.safe_correct.sum()),'choosing_violating':int(50-raw.safe_correct.sum()),'accuracy':float(q.accuracy),'mean_safe_minus_syc_logit_margin':float(q.mean_margin),'mean_probability_gap':float(q.mean_probability_gap),'first_positive_mean_margin_state':first[f'{m}:{v}']}
 report={'status':'passed','judge_note':'Native behavior uses legacy_local_qwen_judge, not canonical Kimi-K2. MCQ labels are controlled ground truth.','behavioral':behavior,'native_sycophancy_fr1_pct':fr,
  'final_layer_cosines':{v:{m:float(lm[(lm.variant==v)&(lm.model==m)&(lm.state_index==28)].cosine_to_BASE.iloc[0]) for m in ('SatImp','SimNPO')} for v in ('original','swapped')},
  'final_layer_original_vs_swapped_semantic_cosine':{m:float(lm[(lm.variant=='original_vs_swapped_semantic')&(lm.model==m)&(lm.state_index==28)].cosine_to_BASE.iloc[0]) for m in MODELS},'bootstrap_seed':SEED,'bootstrap_n':BOOT}
 (WORK/'analysis/behavioral_summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
