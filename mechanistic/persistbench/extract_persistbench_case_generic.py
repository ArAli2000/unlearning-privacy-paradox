#!/usr/bin/env python3
"""GPU extraction for one frozen PersistBench case (own and aligned RMU replay)."""
import argparse,gc,hashlib,importlib.util,json,sys,time,types
from pathlib import Path
import pandas as pd
import torch
from transformers import AutoModelForCausalLM,AutoTokenizer

ROOT=Path(__file__).resolve().parents[2]
PB_SRC=ROOT/'external/PersistBench/src/benchmark'
# Load only the exact upstream config/prompt modules. Importing benchmark's package
# initializer also imports optional API providers that are irrelevant to extraction.
pkg=types.ModuleType('benchmark'); pkg.__path__=[str(PB_SRC)]; sys.modules['benchmark']=pkg
for modname in ['config','prompts']:
 spec=importlib.util.spec_from_file_location(f'benchmark.{modname}',PB_SRC/f'{modname}.py')
 mod=importlib.util.module_from_spec(spec); sys.modules[f'benchmark.{modname}']=mod; spec.loader.exec_module(mod)
build_generation_prompt=sys.modules['benchmark.prompts'].build_generation_prompt

MODELS={
 'BASE':ROOT/'saves/finetune/tofu_Qwen2.5-7B-Instruct_full',
 'RMU':ROOT/'saves/unlearn/proper_qwen25_7b_rmu_from_tofufull_selectionproxy_savebest/checkpoint-104',
 'WGA':ROOT/'saves/unlearn/proper_qwen25_7b_wga_from_tofufull_selectionproxy_savebest/checkpoint-104'}
NAMES={'BASE':'qwen25_7b_tofufull_before','RMU':'qwen25_7b_after_rmu_from_tofufull','WGA':'qwen25_7b_after_wga_from_tofufull'}
STRICT=("You are a helpful assistant. Answer the user's current question directly in normal natural language. "
 "Do not output code, JSON, website text, navigation menus, logs, stack traces, repeated tokens, or random symbols. "
 "If the question asks for advice or writing help, give a concise useful answer.")
MAX_PROMPT=1800; WINDOW=8

def subseq(hay,needle):
 hits=[]
 for i in range(len(hay)-len(needle)+1):
  if hay[i:i+len(needle)]==needle:hits.append((i,i+len(needle)))
 return hits
def make_ids(tok,case,name):
 system=STRICT+'\n\n'+build_generation_prompt(case['memories'],name)
 ids=tok.apply_chat_template([{'role':'system','content':system},{'role':'user','content':case['query']}],tokenize=True,add_generation_prompt=True)
 return ids[-MAX_PROMPT:],system,len(ids)
def span_row(tok,prompt_ids,label,text,notes,required=True):
 ids=tok(text,add_special_tokens=False).input_ids; hits=subseq(prompt_ids,ids)
 if not hits:
  decoded=tok.decode(prompt_ids); starts=[]; pos=0
  while True:
   pos=decoded.find(text,pos)
   if pos<0: break
   starts.append(pos); pos+=1
  if len(starts)==1:
   enc=tok(decoded,add_special_tokens=False,return_offsets_mapping=True)
   if enc.input_ids==prompt_ids:
    a0=starts[0]; a1=a0+len(text); overlap=[i for i,(a,b) in enumerate(enc.offset_mapping) if b>a0 and a<a1]
    if overlap: hits=[(min(overlap),max(overlap)+1)]
 if not hits and not required:
  return {'span_label':label,'text':text,'token_start':-1,'token_end_exclusive':-1,'token_count':0,'decoded_tokens':'[]','confidence':'exact absence','notes':notes+'; absent because original vLLM left truncation removed it'}
 if len(hits)!=1: raise RuntimeError(f'{label}: expected one token match, got {hits}')
 a,b=hits[0]
 return {'span_label':label,'text':text,'token_start':a,'token_end_exclusive':b,'token_count':b-a,'decoded_tokens':json.dumps(tok.convert_ids_to_tokens(ids),ensure_ascii=False),'confidence':'exact token subsequence','notes':notes}
def seq_logprob(model,prompt,prefix,cont):
 ids=torch.tensor([prompt+prefix+cont],device=model.device); att=torch.ones_like(ids)
 with torch.inference_mode(): logits=model(ids,attention_mask=att,use_cache=False).logits[0]
 start=len(prompt)+len(prefix); vals=[]
 for pos,target in enumerate(cont,start=start): vals.append(torch.log_softmax(logits[pos-1].float(),-1)[target].item())
 return vals

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--case-dir',required=True)
 args=ap.parse_args()
 OUT=ROOT/args.case_dir
 if not torch.cuda.is_available(): raise RuntimeError('CUDA required: submit the SLURM script')
 case=json.loads((OUT/'selected_case.json').read_text())
 target=case['target_model']
 tok=AutoTokenizer.from_pretrained(MODELS['BASE'],use_fast=True,local_files_only=True,trust_remote_code=True)
 prompt_ids,system,full_n=make_ids(tok,case,NAMES[target]); variants={k:make_ids(tok,case,NAMES[k])[0] for k in MODELS}
 if any(v!=prompt_ids for v in variants.values()): raise RuntimeError('Left-truncated original model prompts are not token-identical')
 responses={k:tok(case['models'][k]['response'],add_special_tokens=False).input_ids for k in MODELS}
 rtext=case['models'][target]['response']; phrase=case['first_injected_phrase']; char0=rtext.index(phrase); char1=char0+len(phrase)
 enc=tok(rtext,add_special_tokens=False,return_offsets_mapping=True); offsets=enc.offset_mapping
 inj_tokens=[i for i,(a,b) in enumerate(offsets) if b>char0 and a<char1]
 inj_start=min(inj_tokens); inj_end=max(inj_tokens)+1
 token_char_start=offsets[inj_start][0]; token_char_end=offsets[inj_end-1][1]
 prefix_text=rtext[:token_char_start]; prefix_ids=responses[target][:inj_start]; phrase_ids=responses[target][inj_start:inj_end]
 injected_token_text=rtext[token_char_start:token_char_end]
 lo=max(0,inj_start-WINDOW); hi=min(len(responses[target]),inj_end+WINDOW)
 rows=[span_row(tok,prompt_ids,f'memory_{i+1}',m,f'memory item {i+1}',required=False) for i,m in enumerate(case['memories'])]
 rows.append(span_row(tok,prompt_ids,'user_query',case['query'],'complete current request'))
 rows.append({'span_label':'final_prompt_token','text':tok.decode([prompt_ids[-1]]),'token_start':len(prompt_ids)-1,'token_end_exclusive':len(prompt_ids),'token_count':1,'decoded_tokens':json.dumps(tok.convert_ids_to_tokens([prompt_ids[-1]]),ensure_ascii=False),'confidence':'exact','notes':'last token of chat-formatted prompt'})
 pd.DataFrame(rows).to_csv(OUT/'position_manifest.csv',index=False)
 alt=(' ' if injected_token_text.startswith(' ') else '')+case['non_personal_alternative']; alt_ids=tok(alt,add_special_tokens=False).input_ids
 metadata={'entry_id':case['entry_id'],'generation_index':case['generation_index'],'prompt_reconstruction':{'strict_prefix':STRICT,'generator_system_prompt':system,'full_chat_token_count_before_server_truncation':full_n,'truncate_prompt_tokens':MAX_PROMPT,'truncation_side':'left (vLLM truncate_prompt_tokens)','exact_formatted_prompt_after_truncation':tok.decode(prompt_ids),'token_ids':prompt_ids,'decoded_tokens':tok.convert_ids_to_tokens(prompt_ids),'token_count':len(prompt_ids),'prompt_text_sha256':hashlib.sha256(tok.decode(prompt_ids).encode()).hexdigest(),'prompt_ids_sha256':hashlib.sha256(torch.tensor(prompt_ids).numpy().tobytes()).hexdigest(),'model_specific_original_prompts_identical_after_truncation':True},'responses':{k:{'token_count':len(v)} for k,v in responses.items()},'injection':{'phrase':phrase,'response_char_start':char0,'response_char_end_exclusive':char1,'token_aligned_text':injected_token_text,'token_aligned_char_span':[token_char_start,token_char_end],'generated_token_start':inj_start,'generated_token_end_exclusive':inj_end,'token_ids':phrase_ids,'tokens':tok.convert_ids_to_tokens(phrase_ids),'window_generated_token_start':lo,'window_generated_token_end_exclusive':hi},'alternative':{'text':alt,'token_ids':alt_ids,'tokens':tok.convert_ids_to_tokens(alt_ids)},'execution':{'torch_dtype':'bfloat16','attention':'sdpa','use_cache':False,'output_hidden_states':True,'saved_dtype':'float32','window':WINDOW},'models':{}}
 p=torch.tensor([prompt_ids]); shared=responses[target]; all_cont=[]; lens=[]
 selected_positions=sorted(set(x for row in rows if int(row['token_start'])>=0 for x in range(int(row['token_start']),int(row['token_end_exclusive']))))
 for label,path in MODELS.items():
  t=time.time(); print('Loading',label,path,flush=True)
  model=AutoModelForCausalLM.from_pretrained(path,torch_dtype=torch.bfloat16,attn_implementation='sdpa',local_files_only=True,trust_remote_code=True).cuda().eval()
  model.requires_grad_(False)
  # Tokenizer compatibility is checked directly for prompt and all stored responses.
  mt=AutoTokenizer.from_pretrained(path,use_fast=True,local_files_only=True,trust_remote_code=True)
  if mt.get_vocab()!=tok.get_vocab(): raise RuntimeError(f'{label} tokenizer vocabulary differs')
  saved={}
  for mode,resp in [('own',responses[label]),('shared_target',shared)]:
   ids=torch.tensor([prompt_ids+resp],device='cuda'); att=torch.ones_like(ids)
   with torch.inference_mode(): out=model(ids,attention_mask=att,output_hidden_states=True,use_cache=False,return_dict=True)
   hs=torch.stack([x[0].detach().float().cpu() for x in out.hidden_states])
   assert hs.shape[0]==29 and hs.shape[2]==3584 and torch.isfinite(hs).all()
   if mode=='shared_target':
    saved['prompt_selected']=hs[:,selected_positions,:].contiguous(); saved['shared_generated']=hs[:,len(prompt_ids):,:].contiguous()
    # Ordinary logit lens: final RMSNorm then tied/untied LM head, at state before each target.
    for gi in range(lo,hi):
     target_token_id=shared[gi]; abs_prev=len(prompt_ids)+gi-1
     for layer,hstate in enumerate(out.hidden_states):
      # hidden_states[-1] is already post-final-RMSNorm in Qwen2; earlier
      # residual states require the model's final norm for an ordinary logit lens.
      h=hstate[0,abs_prev] if layer==model.config.num_hidden_layers else model.model.norm(hstate[0,abs_prev])
      with torch.inference_mode():
       logits=model.lm_head(h.unsqueeze(0)).float()[0]
       lp=torch.log_softmax(logits,-1)
       rank=int((logits>logits[target_token_id]).sum().item())+1
      lens.append({'model':label,'generated_token_index':gi,'relative_to_injection':gi-inj_start,'layer':layer,'target_token_id':target_token_id,'target_token':tok.decode([target_token_id]),'probability':float(lp[target_token_id].exp()),'log_probability':float(lp[target_token_id]),'rank':rank,'is_injected_phrase':inj_start<=gi<inj_end})
   else: saved['own_generated']=hs[:,len(prompt_ids):,:].contiguous()
   del out,hs,ids,att; torch.cuda.empty_cache()
  injected_lp=seq_logprob(model,prompt_ids,prefix_ids,phrase_ids); alt_lp=seq_logprob(model,prompt_ids,prefix_ids,alt_ids)
  for kind,text_,ids_,vals in [('injected_private',injected_token_text,phrase_ids,injected_lp),('non_personal_alternative',alt,alt_ids,alt_lp)]:
   all_cont.append({'model':label,'continuation_type':kind,'text':text_,'token_count':len(ids_),'sequence_log_probability':sum(vals),'mean_token_log_probability':sum(vals)/len(vals),'sequence_probability':float(torch.tensor(sum(vals)).exp()),'per_token_log_probabilities':json.dumps(vals)})
  for k,v in saved.items(): assert v.dtype==torch.float32 and torch.isfinite(v).all()
  torch.save(saved,OUT/f'{label.lower()}_representations.pt')
  metadata['models'][label]={'path':str(path),'runtime_seconds':time.time()-t,'representation_file':f'{label.lower()}_representations.pt','own_response_tokens':len(responses[label]),'shared_response_tokens':len(shared),'saved_shapes':{k:list(v.shape) for k,v in saved.items()},'tokenizer_compatible':True}
  del model,saved,mt; gc.collect(); torch.cuda.empty_cache()
 pd.DataFrame(lens).to_csv(OUT/'logit_lens_trajectory.csv',index=False); pd.DataFrame(all_cont).to_csv(OUT/'continuation_comparison.csv',index=False)
 metadata['execution']['hostname']=__import__('socket').gethostname(); metadata['execution']['cuda_device']=torch.cuda.get_device_name(0)
 (OUT/'extraction_metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+'\n')
 print('Extraction complete',flush=True)
if __name__=='__main__':main()
