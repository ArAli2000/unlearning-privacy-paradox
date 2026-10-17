# PersistBench paired-response pilot

This additive subpipeline freezes and validates 50 cross-domain PersistBench
prompts for a later whole-model contextual-privacy direction. It does not run
BASE, SatImp, or SimNPO inference and does not alter the PrivacyLens pilot.

The upstream Privacy Collapse generator produces both members of a pair in one
JSON response. We preserve that design, but replace its invented input with a
fixed PersistBench `memories` + `query`, require exactly one attributed memory
in the leaky response, and add two independent validation views:

1. pair quality/task equivalence;
2. contextual leakage and exact-memory attribution.

Commands (all are CPU-only and make no API calls):

```bash
python mechanistic/privacy_collapse/persistbench/pipeline.py freeze
python mechanistic/privacy_collapse/persistbench/pipeline.py generation-batch
python mechanistic/privacy_collapse/persistbench/pipeline.py static-validate
```

After approval, an external Batch API runner may submit `generation_requests.jsonl`.
The returned JSONL is processed with `process-generation`, then two judge batches
are created with `judge-batches`. After judge results return, `process-judges`
constructs the accepted/rejected dataset and validation report. No command in
this file invokes a remote API or a 7B model by itself.

Selection is model-independent: compute the native PersistBench MD5 ID from
sorted memories plus query; group all 200 source rows by
`(memory_domain, query_domain)`; order domain-pair groups by
SHA-256(`persistbench-paired-v1|memory_domain|query_domain`); order rows inside
each group by SHA-256(`persistbench-paired-v1|persistbench_id`); then take one
row per group in round-robin order until 50 are selected. With the current data,
the first round alone supplies 50 distinct domain pairs.

Later representation extraction should concatenate the identical formatted
memory/query prompt with each fixed response and take the residual-stream state
at the final token of each respective response (`token_pos=-1`) at every layer.
This is the released Privacy Collapse code path: variable-length examples are
split by their own token lengths and the last token is selected independently;
there is no response pooling or cross-pair position alignment. EOS insertion
must be disabled or audited so the endpoint is the last lexical response token.

