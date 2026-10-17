#!/usr/bin/env python3
import json
import pandas as pd
from common import *
MODELS=('BASE','SatImp','SimNPO')
def main():
 f=pd.read_csv(HERE/'analysis/mcq_readout_per_example.csv');lm=pd.read_csv(HERE/'analysis/layer_metrics.csv');boot=pd.read_csv(HERE/'analysis/bootstrap_intervals.csv')
 summary=f.groupby(['model','variant','state_index']).agg(mean_margin=('safe_minus_syc_logit_margin','mean'),mean_probability_gap=('probability_gap','mean'),accuracy=('safe_correct','mean')).reset_index()
 native=json.loads((ROOT/'mechanistic/privacy_collapse/persistbench_native/analysis/muse_news_category_comparison_validated.json').read_text())
 fr={m:native['metrics']['raw']['sycophancy'][m]['FR@1'][2] for m in MODELS};behavior={}
 for m in MODELS:
  behavior[m]={}
  for v in ('original','swapped'):
   allv=summary[(summary.model==m)&(summary.variant==v)];q=allv[allv.state_index==28].iloc[0];raw=f[(f.model==m)&(f.variant==v)&(f.state_index==28)]
   pos=allv[allv.mean_margin>0]
   behavior[m][v]={'choosing_safe':int(raw.safe_correct.sum()),'choosing_violating':int(50-raw.safe_correct.sum()),'accuracy':float(q.accuracy),
    'mean_safe_minus_syc_logit_margin':float(q.mean_margin),'mean_probability_gap':float(q.mean_probability_gap),
    'first_positive_mean_margin_state':int(pos.state_index.min()) if len(pos) else None}
 final_cos={v:{m:float(lm[(lm.variant==v)&(lm.model==m)&(lm.state_index==28)].cosine_to_BASE.iloc[0]) for m in ('SatImp','SimNPO')} for v in ('original','swapped')}
 swapcos={m:float(lm[(lm.variant=='original_vs_swapped_semantic')&(lm.model==m)&(lm.state_index==28)].cosine_to_BASE.iloc[0]) for m in MODELS}
 # Audit bootstrap: point estimate must equal layer table separately from percentile CI.
 audit=[]
 for _,r in boot.iterrows():
  point=float(lm[(lm.variant==r.variant)&(lm.model==r.model)&(lm.state_index==r.state_index)].cosine_to_BASE.iloc[0])
  audit.append(abs(point-r.point_estimate)<1e-6 and r.ci_lower_2_5<=r.ci_upper_97_5)
 assert all(audit)
 report={'status':'passed','judge_note':'Native behavior uses legacy_local_qwen_judge, not canonical Kimi-K2. MCQ labels are controlled ground truth.',
  'behavioral':behavior,'native_sycophancy_fr1_pct':fr,'final_layer_cosines':final_cos,'final_layer_original_vs_swapped_semantic_cosine':swapcos,
  'bootstrap':{'n':int(boot.bootstrap_n.iloc[0]),'seed':int(boot.seed.iloc[0]),'point_estimates_separate_and_match_layer_metrics':True,'all_interval_bounds_ordered':True}}
 (HERE/'analysis/behavioral_summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
