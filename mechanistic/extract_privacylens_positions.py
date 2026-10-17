#!/usr/bin/env python3
"""GPU-only position-resolved extraction for the frozen PrivacyLens population."""
import argparse,csv,gc,hashlib,json,platform
from collections import defaultdict
from pathlib import Path
import torch,transformers
from transformers import AutoModelForCausalLM,AutoTokenizer
from extract_single_privacylens import DATA_PATH,MODEL_PATHS,REPO_ROOT,build_prompt,build_prompt_text

EXPECTED=(29,3584); ROOT=REPO_ROOT/'mechanistic/outputs/privacy_position_analysis'

def main():
 p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,default=ROOT/'position_manifest.csv'); p.add_argument('--overwrite',action='store_true'); a=p.parse_args()
 if not torch.cuda.is_available(): raise RuntimeError('CUDA required: submit through SLURM')
 rows=list(csv.DictReader(a.manifest.open())); by=defaultdict(dict)
 for r in rows: by[r['sample_id']][r['role']]=r
 if len(by)!=24 or any(len(x)!=6 for x in by.values()): raise RuntimeError('Expected 24 samples x 6 roles')
 data={x['name']:x for x in json.loads(DATA_PATH.read_text())}
 tok=AutoTokenizer.from_pretrained(MODEL_PATHS['BASE'],use_fast=True,trust_remote_code=True,local_files_only=True)
 if tok.pad_token is None: tok.pad_token=tok.eos_token
 canonical={}; metadata={}
 for sid,roles in by.items():
  prompt=build_prompt(data[sid],tok); raw=build_prompt_text(data[sid]); enc=tok(prompt,return_tensors='pt'); ids=enc['input_ids'].contiguous(); mask=enc['attention_mask'].contiguous(); digest=hashlib.sha256(ids.numpy().tobytes()).hexdigest()
  if digest!=next(iter(roles.values()))['token_ids_sha256'] or ids.shape[1]!=int(next(iter(roles.values()))['sequence_length']): raise RuntimeError(f'Manifest token mismatch {sid}')
  for role,r in roles.items():
   idx=json.loads(r['token_indices']);
   if not idx or min(idx)<0 or max(idx)>=ids.shape[1]: raise RuntimeError(f'Bad indices {sid}/{role}')
   if [ids[0,j].item() for j in idx]!=json.loads(r['token_ids']): raise RuntimeError(f'Token ID mismatch {sid}/{role}')
  canonical[sid]=(ids,mask)
  metadata[sid]={'sample_id':sid,'raw_constructed_prompt':raw,'exact_prompt':prompt,'token_ids':ids[0].tolist(),'decoded_tokens':tok.convert_ids_to_tokens(ids[0].tolist()),'token_ids_sha256':digest,'sequence_length':ids.shape[1],'tokenizer_path':str(MODEL_PATHS['BASE']),'roles':{role:{k:r[k] for k in ['selected_text','char_start','char_end','token_indices','token_ids','decoded_selected_tokens','selection_method','confidence_notes']} for role,r in roles.items()},'models':{},'software':{'python':platform.python_version(),'torch':torch.__version__,'transformers':transformers.__version__,'cuda_runtime':torch.version.cuda},'device':{'name':torch.cuda.get_device_name(0),'index':0}}
 for label,path in MODEL_PATHS.items():
  print(f'Loading {label} once: {path}',flush=True); model=AutoModelForCausalLM.from_pretrained(path,torch_dtype=torch.bfloat16,device_map='auto',trust_remote_code=True,local_files_only=True,attn_implementation='sdpa'); model.eval(); device=model.get_input_embeddings().weight.device
  if (model.config.num_hidden_layers+1,model.config.hidden_size)!=EXPECTED: raise RuntimeError('Unexpected model dimensions')
  for n,(sid,roles) in enumerate(by.items(),1):
   outdir=ROOT/'activations'/sid; outdir.mkdir(parents=True,exist_ok=True); target=outdir/f'{label.lower()}_position_activations.pt'
   ids,mask=canonical[sid]; di,dm=ids.to(device),mask.to(device)
   if not torch.equal(di.cpu(),ids) or not torch.equal(dm.cpu(),mask): raise RuntimeError(f'Canonical tensor mismatch {label}/{sid}')
   with torch.inference_mode(): out=model(input_ids=di,attention_mask=dm,output_hidden_states=True,use_cache=False,return_dict=True)
   saved={}
   for role,r in roles.items():
    idx=json.loads(r['token_indices']); per=torch.stack([h[0,idx].detach().cpu().float() for h in out.hidden_states],dim=1).contiguous() # token,layer,hidden
    mean=per.mean(0)
    if tuple(mean.shape)!=EXPECTED or per.shape[1:]!=EXPECTED or not torch.isfinite(per).all(): raise RuntimeError(f'Invalid {label}/{sid}/{role}')
    saved[role]={'mean':mean,'per_token':per,'token_indices':idx,'token_ids':json.loads(r['token_ids']),'selected_text':r['selected_text']}
   torch.save({'sample_id':sid,'model_label':label,'token_ids_sha256':metadata[sid]['token_ids_sha256'],'roles':saved},target)
   metadata[sid]['models'][label]={'model_path':str(path),'activation_path':str(target),'model_type':model.config.model_type,'hidden_size':model.config.hidden_size,'layer_count':model.config.num_hidden_layers,'state_count':29,'dtype':'torch.float32','attention_backend':model.config._attn_implementation,'token_ids_sha256':metadata[sid]['token_ids_sha256'],'token_ids_identical_to_canonical':True}
   print(f'[{n}/24] {label}/{sid}',flush=True); del out,di,dm,saved
  del model; gc.collect(); torch.cuda.empty_cache()
 for sid in by:
  if len({v['token_ids_sha256'] for v in metadata[sid]['models'].values()})!=1: raise RuntimeError(f'Cross-model mismatch {sid}')
  d=ROOT/'activations'/sid; (d/'metadata.json').write_text(json.dumps(metadata[sid],indent=2)+'\n')
 print('Position extraction complete',flush=True)
if __name__=='__main__': main()
