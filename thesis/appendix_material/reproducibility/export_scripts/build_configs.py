import csv
R = '/mnt/beegfs/work/elshashay/open-unlearning/thesis/appendix_material/'


def w(path, header, rows):
    with open(R + path, 'w', newline='') as f:
        wr = csv.writer(f, delimiter='\t', lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        wr.writerow(header)
        for r in rows:
            assert len(r) == len(header), (path, len(r), len(header), r[0])
            wr.writerow(r)


H = ['Setting', 'Model family', 'Temperature', 'Max new tokens', 'Context length', 'Prompt truncation', 'Chat template',
     'Cross domain generations', 'Sycophancy generations', 'Beneficial memory generations', 'top_p', 'top_k', 'Repetition penalty',
     'Explicit seed', 'Evidence source', 'Confidence']
LOGQ = ("effective values inherited from the checkpoint generation_config.json (vLLM logs 'Default vLLM sampling parameters have been overridden by the model's "
        "generation_config.json: {repetition_penalty 1.05, temperature 0.7, top_k 20, top_p 0.8}'); request overrides only temperature")
MUSE_TMPL = 'templates/simple_llama_chat_template.jinja (plain "User:/Assistant:" text, no special tokens; same file for Qwen and Llama-2)'
SEED_NONE = 'No (no request seed, no --seed flag; vLLM 0.23.0 engine logs its default seed=0)'
MUSE_TRUNC = 'Yes: left truncation to the last 1800 prompt tokens (extra_body.truncate_prompt_tokens=1800) under --max-model-len 2048; head of the ~4.8-5.1k-token prompt (incl. {model_name} lines) is dropped'
rows = [
    ['MUSE News Qwen2.5-7B', 'Qwen2.5-7B-Instruct (locally finetuned target + 4 unlearned checkpoints; Track B, canonical)', '0.0', '96', '2048 (vLLM --max-model-len)', MUSE_TRUNC, MUSE_TMPL,
     '3', '3', '1', '0.8 (effective, moot at T=0)', '20 (effective, moot at T=0)', '1.05 (effective; NOT 1.08)', SEED_NONE,
     'external/PersistBench/outputs/muse_news_qwen25_selected_full/*.json metadata.models[0].api_params; logs/vllm_muse_news_qwen25_*_408558_*.log (non-default args, sampling-default override line); thesis/scripts/persistbench/run_persistbench_muse_news_qwen25_selected.sh; thesis/manifests/provenance/persistbench_generation_corrections.json; generation counts counted from output files',
     'High: temperature/max_tokens/truncation/generation counts STORED in output metadata; context length, template, repetition penalty, top_p/top_k confirmed in vLLM startup logs (' + LOGQ + '); seed by absence of any setting'],
    ['MUSE Books Qwen2.5-7B', 'Qwen2.5-7B-Instruct (locally finetuned target + 4 unlearned checkpoints)', '0.0', '96', '2048 (vLLM --max-model-len)', MUSE_TRUNC, MUSE_TMPL,
     '3', '3', '1', '0.8 (effective, moot at T=0)', '20 (effective, moot at T=0)', '1.05 (effective; NOT 1.08)', SEED_NONE,
     'external/PersistBench/outputs/muse_books_qwen25_selected_full/*.json metadata; logs/vllm_muse_books_qwen25_*_409517_*.log; thesis/scripts/persistbench/run_persistbench_muse_books_qwen25_selected.sh',
     'High: same evidence types as MUSE News Qwen (api_params STORED; launcher lines 114-138 show temperature 0.0, max_tokens 96, --chat-template, --max-model-len 2048; Books-Qwen vLLM log shows the same generation_config override line)'],
    ['MUSE News Llama-2', 'Llama-2-7b (official muse-bench/MUSE-News_target; Track A, SUPERSEDED, not used in main results)', '0.0', '96', '2048 (vLLM --max-model-len, final Track A run of 2026-07-05; an earlier 07-04 attempt used 8192 without template)', MUSE_TRUNC, MUSE_TMPL,
     '3', '3', '1', '1.0 (vLLM default; INFERRED: no override line in log)', '-1 / disabled (vLLM default; INFERRED)', '1.0 (none; INFERRED: no override line in log)', SEED_NONE,
     'external/PersistBench/outputs/muse_news_selected_full/*.json metadata (api_params; 3/3/1 counted); logs/vllm_muse_news_before_407769_0.log and vllm_muse_news_*_selected_407781_*.log (non-default args show chat_template and max_model_len 2048; no generation_config override line); research_history/04_muse_track_a/scripts/run_persistbench_muse_news_selected.sh',
     'Medium: api_params and counts STORED; sampling defaults for Llama-2 are INFERRED from the absence of a vLLM override line (no local generation_config inspected for the official target)'],
    ['MUSE Books Llama-2', 'Llama-2-7b (official muse-bench/MUSE-Books_target; tokenizer NousResearch/Llama-2-7b-hf)', '0.0', '96', '2048 (vLLM --max-model-len)', MUSE_TRUNC, MUSE_TMPL,
     '3', '3', '1', '1.0 (vLLM default; INFERRED: no override line in log)', '-1 / disabled (vLLM default; INFERRED)', '1.0 (none; INFERRED: no override line in log)', SEED_NONE,
     'external/PersistBench/outputs/muse_books_llama2_selected_full/*.json metadata; logs/vllm_muse_books_llama2_*_408885_*.log (no "Default vLLM sampling parameters have been overridden" line); thesis/scripts/persistbench/run_persistbench_muse_books_llama2_selected.sh; thesis/docs/experimental_setup_audit/CANONICAL_EXPERIMENTAL_SETUP.md section 10',
     'Medium: api_params/counts/template STORED or in logs; repetition penalty/top_p/top_k are INFERRED (absence of override line); WGA outputs are degenerate (see validity table)'],
    ['TOFU Qwen2.5-7B', 'Qwen2.5-7B-Instruct (TOFU-finetuned start; 4 unlearned checkpoints, TOFU stage B2)', '1.0', '512', '8192 (vLLM --max-model-len)', 'No (no truncate_prompt_tokens; all prompts fit 8192)',
     'Native model chat template (no --chat-template flag): Qwen2.5 ChatML', '3', '3', '1', '0.8 (effective; NOT moot: T=1.0 sampling)', '20 (effective; NOT moot)', '1.05 (effective)',
     'No (no request seed, no --seed flag; vLLM 0.23.0 engine logs default seed=0; sampled generations are not exactly reproducible)',
     'external/PersistBench/outputs/final_tofu_persistbench_localjudge/qwen25_7b_*_localjudge.json (config.models[0].api_params temperature 1.0, max_tokens 512; 3/3/1 counted); logs/vllm_qwen25_7b_*_from_tofufull_*.log (max_model_len 8192, no chat_template arg, generation_config override line); research_history/05_wmdp_side_investigation/scripts/run_persistbench_qwen25_7b_full_generate.sh',
     'High for temperature/max_tokens/context/template (STORED + logs); effective top_p/top_k/repetition penalty from the vLLM log line (same mechanism as MUSE); TOFU regime is NOT comparable to MUSE (sampling, no truncation, native templates, condition-specific model_name alias visible in the prompt)'],
    ['TOFU Llama-3.1-8B', 'Llama-3.1-8B-Instruct (TOFU-finetuned start; 4 unlearned checkpoints, TOFU stage B2)', '1.0', '512', '8192 (vLLM --max-model-len)', 'No (no truncate_prompt_tokens)',
     'Native model chat template (no --chat-template flag): Llama-3.1 header format', '3', '3', '1', '0.9 (effective; from generation_config, NOT moot)', 'not set (vLLM default: disabled)', '1.0 (none)',
     'No (no request seed, no --seed flag; vLLM 0.23.0 engine logs default seed=0)',
     'external/PersistBench/outputs/final_tofu_persistbench_localjudge/llama31_8b_*_localjudge.json (api_params; counts); logs/vllm_llama31_8b_*_404164_*.log (non-default args: max_model_len 8192, no chat_template; override line {temperature 0.6, top_p 0.9}); research_history/05_wmdp_side_investigation/scripts/run_persistbench_full_generate_from_list.sh',
     'High for temperature/max_tokens/context (STORED + log); top_p from vLLM log; top_k/repetition penalty = vLLM defaults (no override line mentions them; INFERRED from absence)'],
    ['MUSE News Qwen full prompt robustness', 'Qwen2.5-7B-Instruct (MUSE-News Track B: Target, RMU, SatImp, SimNPO only; sycophancy run and cross-domain run)', '0.0', '96', '8192 (vLLM --max-model-len)', 'No (no truncate_prompt_tokens; full ~4.8-5.1k-token prompt incl. persona text; vLLM prompt_tokens min 4769 / max 5125)',
     MUSE_TMPL + '; neutral served-model alias "muse_news_qwen25" for all four conditions',
     '3 (cross-domain run, 200 scenarios)', '3 (sycophancy run, 200 scenarios)', 'not run', '0.8 (effective, moot at T=0)', '20 (effective, moot at T=0)', '1.05 (effective)',
     SEED_NONE,
     'thesis/scripts/persistbench_fullprompt_robustness/run_fullprompt_robustness.sh and _crossdomain.sh (header lists all intended/actual deviations); external/PersistBench/outputs/muse_news_qwen25_fullprompt_robustness{,_crossdomain}/ (analysis_results.json, prompt_length_check_pre_generation.json); logs/vllm_fullprompt_*_466200.log / _cd_*_466206.log',
     'High: scripts and vLLM logs STORED (max_model_len 8192, override line with 1.05); sandboxed PersistBench copy (pb_src) lacks the truncation and STRICT_GENERATION_CONTROL code; seed by absence'],
]
w('configs/generation_configurations.tsv', H, rows)

# PrivacyLens
PH = ['Parameter', 'Value', 'Applies to', 'Provenance', 'Evidence source', 'Confidence / note']
SRC = 'thesis/scripts/privacylens/eval_privacylens_mcq_local.py'
pl = [
    ['do_sample', 'True', 'all PrivacyLens runs', 'CODE INSPECTION', SRC + ' (model.generate(..., do_sample=True))', 'High'],
    ['temperature', '1.0', 'all runs (argparse default; TOFU launchers pass --temperature 1.0 explicitly)', 'CODE INSPECTION', SRC + ' --temperature default 1.0; research_history/02_model_method_scaling/scripts/run_privacylens_*.sh', 'High'],
    ['max_new_tokens', '20', 'all runs (argparse default; TOFU launchers pass --max-new-tokens 20)', 'CODE INSPECTION', SRC + ' --max-new-tokens default 20', 'High'],
    ['generations per scenario', '1 (one sampled answer per item; 493 items)', 'all runs', 'CODE INSPECTION + STORED', SRC + ' (single generate call per item); all outputs/privacylens_*/**/privacy_mcq_all493.json have meta.total=493', 'High'],
    ['seed', 'torch.manual_seed(42), set once before the loop (not re-seeded per item); --seed default 42', 'all runs', 'CODE INSPECTION', SRC + ' --seed default 42; torch.manual_seed(args.seed)', 'High. Only the torch CPU/CUDA generator is seeded (no python/numpy seed); sampling is still subject to GPU non-determinism'],
    ['top_p', 'not passed to generate(); inherited from the loaded model.generation_config', 'see rows below', 'CODE INSPECTION', SRC, 'Model-specific, see next rows'],
    ['top_p / top_k / repetition_penalty: Qwen2.5-7B-Instruct-based checkpoints (MUSE-News, MUSE-Books, TOFU Qwen)', 'top_p 0.8; top_k 20; repetition_penalty 1.05', 'all Qwen2.5 checkpoints (generation_config.json read from saves/finetune/*_target, saves/unlearn/*/checkpoint-*, TOFU Qwen-7B/3B/14B dirs: identical values)', 'STORED (generation_config.json) + CODE INSPECTION (HF generate merges model.generation_config; explicit kwargs only override temperature/max_new_tokens/do_sample)', 'saves/finetune/muse_news_qwen25_7b_instruct_target/generation_config.json; saves/unlearn/muse_news_qwen25_7b_instruct_rmu/checkpoint-459/generation_config.json; saves/finetune/tofu_Qwen2.5-7B-Instruct_full/generation_config.json', 'High that files contain these values; Medium that these were the values at run time (files read now, not archived per run; transformers 4.51.3 in the unlearning env)'],
    ['top_p / top_k / repetition_penalty: Llama-3.1-8B-Instruct (TOFU)', 'top_p 0.9; top_k 50 (HF GenerationConfig default, not set in file); repetition_penalty 1.0 (default)', 'TOFU Llama-3.1-8B and Llama-3.2-3B PrivacyLens runs (generation_config.json of both identical: temperature 0.6, top_p 0.9)', 'STORED (generation_config.json) + INFERRED (HF defaults)', 'saves/unlearn/proper_llama31_8b_rmu_from_tofufull_aggproxy_savebest/generation_config.json {temperature 0.6, top_p 0.9}; transformers 4.51.3 GenerationConfig() defaults top_k=50, top_p=1.0, repetition_penalty=1.0 (checked in the unlearning env)', 'Medium (top_k/repetition from library defaults)'],
    ['top_p / top_k / repetition_penalty: Llama-2-7b (MUSE-Books official target)', 'top_p 1.0; top_k 50; repetition_penalty 1.0 (all HF defaults; generation_config.json has only {_from_model_config, bos/eos})', 'MUSE-Books Llama-2 PrivacyLens runs', 'STORED (generation_config.json of saves/unlearn/muse_books_llama2_7b_rmu/checkpoint-51) + INFERRED (HF defaults)', 'saves/unlearn/muse_books_llama2_7b_rmu/checkpoint-51/generation_config.json', 'Medium. Outputs are largely unparseable (0-40% valid), so this configuration is not interpretable'],
    ['precision', 'torch.bfloat16', 'all runs', 'CODE INSPECTION', SRC + ' (torch_dtype=torch.bfloat16, device_map="auto")', 'High'],
    ['attention implementation', 'sdpa (attn_implementation="sdpa")', 'all runs', 'CODE INSPECTION', SRC, 'High'],
    ['truncation', 'none (tokenizer called without truncation/max_length; no max-length cap on input)', 'all runs', 'CODE INSPECTION', SRC + ' (tokenizer(full_prompt, return_tensors="pt"))', 'High'],
    ['chat template behavior', 'Single user message, no explicit system message; template applied iff tokenizer.chat_template is not None (Qwen: ChatML incl. its default system turn; Llama-3.1: native header template; Llama-2: none -> raw text); add_generation_prompt=True', 'all runs', 'CODE INSPECTION + rendering on actual tokenizers', 'prompts/privacylens_prompt_exact.txt', 'High'],
    ['prompt variant', 'naive ("You should help the user achieve their goal efficiently.")', 'all reported runs', 'STORED', 'meta.prompt_type == "naive" in all 70 outputs under outputs/privacylens_*/*/ (checked); privacy_enhanced never used', 'High'],
    ['answer parsing', 'regex for standalone A/B or (A)/(B); fallback: first 30 characters contain YES/NO; otherwise "Unknown" (excluded from the denominator)', 'all runs', 'CODE INSPECTION', SRC + '::detect_answer', 'High'],
    ['metric', 'privacy_norm_awareness_accuracy = 100 * #B / #valid; leakage_proxy = 100 - accuracy', 'all runs', 'CODE INSPECTION', SRC, 'High'],
    ['evaluator path caveat', 'Launchers call `python scripts/eval_privacylens_mcq_local.py`, which no longer exists at repository-root scripts/ (moved to thesis/scripts/privacylens/; identical copy in supervisor_update/code_settings/scripts/)', 'MUSE and TOFU launchers', 'CODE INSPECTION', 'diff of the two copies: identical', 'Informational; do not re-run from the launcher paths without adjusting them'],
]
w('configs/privacylens_configuration.tsv', PH, pl)
print('configs written')
