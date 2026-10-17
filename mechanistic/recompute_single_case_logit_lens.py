#!/usr/bin/env python3
"""Recompute corrected logit-lens projections from saved shared-replay states."""
import gc,json
from pathlib import Path
import pandas as pd,torch
from transformers import AutoModelForCausalLM,AutoTokenizer
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'mechanistic/outputs/single_persistbench_case'
MODELS={'BASE':ROOT/'saves/finetune/tofu_Qwen2.5-7B-Instruct_full','RMU':ROOT/'saves/unlearn/proper_qwen25_7b_rmu_from_tofufull_selectionproxy_savebest/checkpoint-104','WGA':ROOT/'saves/unlearn/proper_qwen25_7b_wga_from_tofull_selectionproxy_savebest/checkpoint-104'}
MODELS['WGA']=ROOT/'saves/unlearn/proper_qwen25_7b_wga_from_tofufull_selectionproxy_savebest/checkpoint-104'
def main():
 if not torch.cuda.is_available():raise RuntimeError('CUDA required')
 meta=json.loads((OUT/'extraction_metadata.json').read_text()); tok=AutoTokenizer.from_pretrained(MODELS['BASE'],local_files_only=True); inj=meta['injection']; lo=inj['window_generated_token_start'];hi=inj['window_generated_token_end_exclusive']; targets=json.loads((OUT/'selected_case.json').read_text())['models']['RMU']['response']; tids=tok(targets,add_special_tokens=False).input_ids; rows=[]
 for label,path in MODELS.items():
  print('Loading',label,flush=True); model=AutoModelForCausalLM.from_pretrained(path,torch_dtype=torch.bfloat16,local_files_only=True,attn_implementation='sdpa').cuda().eval(); rep=torch.load(OUT/f'{label.lower()}_representations.pt',map_location='cpu',weights_only=True); x=rep['shared_generated']
  for gi in range(lo,hi):
   target=tids[gi]
   for layer in range(29):
    h=x[layer,gi-1].cuda().to(torch.bfloat16); h=h if layer==28 else model.model.norm(h); logits=model.lm_head(h.unsqueeze(0)).float()[0];lp=torch.log_softmax(logits,-1)
    rows.append({'model':label,'generated_token_index':gi,'relative_to_injection':gi-inj['generated_token_start'],'layer':layer,'target_token_id':target,'target_token':tok.decode([target]),'probability':float(lp[target].exp()),'log_probability':float(lp[target]),'rank':int((logits>logits[target]).sum())+1,'is_injected_phrase':inj['generated_token_start']<=gi<inj['generated_token_end_exclusive']})
  del model,rep,x;gc.collect();torch.cuda.empty_cache()
 pd.DataFrame(rows).to_csv(OUT/'logit_lens_trajectory.csv',index=False);print('Corrected logit lens complete')
if __name__=='__main__':main()
