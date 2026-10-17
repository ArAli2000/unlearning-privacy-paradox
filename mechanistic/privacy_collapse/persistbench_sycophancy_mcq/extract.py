#!/usr/bin/env python3
import csv,gc,json,platform
from datetime import datetime,timezone
import torch,transformers
from transformers import AutoModelForCausalLM
from common import *
@torch.inference_mode()
def endpoint(model,ids):
 o=model(torch.tensor([ids],device=model.device),output_hidden_states=True,use_cache=False,return_dict=True)
 return torch.stack([h[0,-1].float().cpu() for h in o.hidden_states])
def projections(model,states):
 out=[]
 for i,h in enumerate(states):
  v=h[0,-1];v=v if i==len(states)-1 else model.model.norm(v);out.append(model.lm_head(v).float())
 return out
def main():
 assert torch.cuda.is_available(); static=json.loads((WORK/'analysis/static_validation.json').read_text());assert static['status']=='passed'
 records=json.loads((WORK/'analysis/prepared_examples.json').read_text())['records'];cfg=json.loads(CONFIG.read_text())
 prov={'started_utc':datetime.now(timezone.utc).isoformat(),'software':{'python':platform.python_version(),'torch':torch.__version__,'transformers':transformers.__version__},'models':{}}
 for label,rel in cfg['models'].items():
  path=(ROOT/rel).resolve();print('Loading',label,path,flush=True)
  model=AutoModelForCausalLM.from_pretrained(path,torch_dtype=torch.bfloat16,device_map='auto',local_files_only=True,trust_remote_code=True,attn_implementation=cfg['attention_implementation']);model.eval()
  rows=[]; dirs={'original':[],'swapped':[]}
  for n,r in enumerate(records,1):
   for variant in ('original','swapped'):
    z=r[variant]; prompt=torch.tensor([z['prompt_ids']],device=model.device);o=model(prompt,output_hidden_states=True,use_cache=False,return_dict=True)
    sid=z['safe_continuation_ids'][0];vid=z['violating_continuation_ids'][0]
    for i,logits in enumerate(projections(model,o.hidden_states)):
     probs=torch.softmax(logits,dim=0);margin=float(logits[sid]-logits[vid])
     rows.append({'model':label,'variant':variant,'example_id':r['example_id'],'state_index':i,'state_label':'embedding' if i==0 else f'L{i}',
      'safe_logit':float(logits[sid]),'violating_logit':float(logits[vid]),'safe_minus_syc_logit_margin':margin,
      'P_safe':float(probs[sid]),'P_violating':float(probs[vid]),'probability_gap':float(probs[sid]-probs[vid]),'safe_correct':int(margin>0)})
    dirs[variant].append(endpoint(model,z['safe_ids'])-endpoint(model,z['violating_ids']));del prompt,o
   print(f'[{n}/50] {r["example_id"]}',flush=True)
  d=WORK/'representations'/label.lower();d.mkdir(parents=True,exist_ok=True)
  with (d/'mcq_readout_per_example.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  for variant,values in dirs.items():
   per=torch.stack(values);torch.save({'model':label,'variant':variant,'example_ids':[r['example_id'] for r in records],
    'definition':'h_non_sycophantic - h_sycophantic','per_example_differences':per,'mean_direction':per.mean(0),
    'direction_norms':torch.linalg.vector_norm(per.mean(0),dim=-1),'state_labels':['embedding']+[f'L{i}' for i in range(1,29)],'answer_position':'last answer token; no EOS'},d/f'{variant}_directions.pt')
  prov['models'][label]={'path':str(path)};del model;gc.collect();torch.cuda.empty_cache()
 prov['completed_utc']=datetime.now(timezone.utc).isoformat();(WORK/'analysis/gpu_extraction_provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
if __name__=='__main__':main()
