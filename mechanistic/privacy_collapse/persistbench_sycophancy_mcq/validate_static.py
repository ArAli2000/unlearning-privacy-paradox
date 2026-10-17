#!/usr/bin/env python3
import json
from tokenizers import Tokenizer
from common import *
TOKFILES=('tokenizer.json','tokenizer_config.json','vocab.json','merges.txt')
def main():
 rows=[json.loads(x) for x in SOURCE.read_text().splitlines() if x.strip()]; m=json.loads(MANIFEST.read_text()); rec=m['records']
 assert len(rows)==200 and len(rec)==50 and len({x['persistbench_id'] for x in rec})==50
 assert all(x['clarity_label']=='CLEAR_NO' and x['safe']==SAFE and x['violating']==VIOLATING for x in rec)
 assert len({x['prompt'] for x in rec})==50
 for x in rec:
  r=rows[x['source_index']]; assert x['persistbench_id']==pbid(r) and x['query']==r['query'] and x['memories']==r['memories']
  assert x['prompt']==prompt(r) and x['swapped_prompt']==prompt(r,True)
 cfg=json.loads(CONFIG.read_text()); paths={k:(ROOT/v).resolve() for k,v in cfg['models'].items()}
 hashes={k:{f:sha(p/f) for f in TOKFILES} for k,p in paths.items()};assert len({canonical(v) for v in hashes.values()})==1
 configs={k:json.loads((p/'config.json').read_text()) for k,p in paths.items()};assert {(x['num_hidden_layers'],x['hidden_size'],x['vocab_size']) for x in configs.values()}=={(28,3584,152064)}
 tok=Tokenizer.from_file(str(paths['BASE']/'tokenizer.json')); prepared=[]
 for x in rec:
  original=pair(tok,chat(x['prompt']),'B','A'); swapped=pair(tok,chat(x['swapped_prompt']),'A','B')
  assert len(original['safe_continuation_ids'])==len(original['violating_continuation_ids'])==1
  assert len(swapped['safe_continuation_ids'])==len(swapped['violating_continuation_ids'])==1
  prepared.append({**x,'original':original,'swapped':swapped})
 tids={'A':enc(tok,'A'),'B':enc(tok,'B')};assert tids=={'A':[32],'B':[33]}
 (WORK/'analysis/prepared_examples.json').write_text(json.dumps({'records':prepared},indent=2,ensure_ascii=False)+'\n')
 report={'status':'passed','record_count':50,'unique_ids':50,'source_sha256':sha(SOURCE),'manifest_sha256':sha(MANIFEST),
  'A_token_ids':tids['A'],'B_token_ids':tids['B'],'safe_original':'B / No','violating_original':'A / Yes',
  'safe_swapped':'A / No','violating_swapped':'B / Yes','uniform_templates':True,'source_rows_exact':True,
  'chat_format':'same literal single-user Qwen boundary as PrivacyLens/PersistBench-MCQ',
  'endpoint':'last answer-completion token; no EOS','states':'embedding + L1-L28','dimensions':[29,3584],
  'checkpoint_dimensions':{k:[v['num_hidden_layers'],v['hidden_size'],v['vocab_size']] for k,v in configs.items()},'tokenizer_hashes':hashes}
 (WORK/'analysis/static_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
