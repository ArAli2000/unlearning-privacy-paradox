#!/usr/bin/env python3
"""Select auditable TOFU/Qwen RMU-failure versus WGA-control PersistBench cases."""
import json
from pathlib import Path
import pandas as pd
from analyze_benchmark_paradox import ROOT,OUT,PBROOT,pb_records,response,classify

FILES={
 'BASE':PBROOT/'final_tofu_persistbench_localjudge/qwen25_7b_tofufull_before_localjudge.json',
 'RMU':PBROOT/'final_tofu_persistbench_localjudge/qwen25_7b_after_rmu_from_tofufull_localjudge.json',
 'WGA':PBROOT/'final_tofu_persistbench_localjudge/qwen25_7b_after_wga_from_tofufull_localjudge.json'}
def raw(path):
 d=json.loads(path.read_text()); out={}
 for eid,e in d['entries'].items():
  for j,g in enumerate(next(iter(e['results'].values()))['generations']):out[eid,j]=(e,g)
 return out
def main():
 rr={k:raw(v) for k,v in FILES.items()}; cl={k:pb_records(v)[0] for k,v in FILES.items()}; rows=[]
 for key in sorted(set(rr['BASE'])&set(rr['RMU'])&set(rr['WGA'])):
  b,r,w=(cl[x][key] for x in ['BASE','RMU','WGA'])
  if not all(x['valid'] for x in [b,r,w]):continue
  group='rmu_specific_new_strict_failure' if (not b['strict'] and r['strict'] and not w['strict']) else 'triple_valid_clean_control' if not any(x['strict'] or x['broad'] for x in [b,r,w]) else 'other_triple_valid'
  if group=='other_triple_valid':continue
  e=rr['BASE'][key][0]
  rows.append({'selection_group':group,'entry_id':key[0],'generation_index':key[1],'benchmark_failure_type':e.get('failure_type'),'query':e.get('query',''),'memories_json':json.dumps(e.get('memories',[]),ensure_ascii=False),'base_mode':b['mode'],'rmu_mode':r['mode'],'wga_mode':w['mode'],'base_response':response(rr['BASE'][key][1]),'rmu_response':response(rr['RMU'][key][1]),'wga_response':response(rr['WGA'][key][1])})
 df=pd.DataFrame(rows); df.to_csv(OUT/'next_mechanistic_sample_candidates.csv',index=False)
 print(df.selection_group.value_counts().to_string())
 print('\nRMU-specific candidates:')
 print(df[df.selection_group=='rmu_specific_new_strict_failure'][['entry_id','generation_index','benchmark_failure_type','rmu_mode','query']].to_string(index=False))
if __name__=='__main__':main()
