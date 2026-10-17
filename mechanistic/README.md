# Single-sample PrivacyLens hidden-state extraction

This module is the first mechanistic-interpretability sanity check. It extracts
the last prompt token's hidden representation for one PrivacyLens sample from
the BASE, RMU, and WGA Qwen2.5-7B checkpoints. It does not generate text or
perform PCA, logit-lens analysis, steering, plotting, or dataset-scale work.

The script imports `construct_prompt` and `format_chat_prompt` from the existing
PrivacyLens evaluator. It loads `--sample-id` (default: `main1`) from the repository's existing dataset,
builds the naive/default evaluation prompt with the BASE tokenizer's chat
template, tokenizes that final prompt once, and reuses the same `input_ids` and
`attention_mask` for all three sequential forward passes.

Submit from the repository root (the job has not been submitted):

```bash
sbatch mechanistic/slurm/run_single_privacylens.sbatch
sbatch mechanistic/slurm/run_single_privacylens.sbatch main415
# Alternatively: sbatch --export=ALL,SAMPLE_ID=main415 mechanistic/slurm/run_single_privacylens.sbatch
```

The job uses the existing `unlearning` conda environment and requests one A180
GPU, 160 GB host memory, 8 CPUs, and 2 hours. It loads only local model files and
does not install or upgrade packages.

Successful execution creates `mechanistic/outputs/<sample-id>/` containing:

- `base_last_prompt_token.pt`
- `rmu_last_prompt_token.pt`
- `wga_last_prompt_token.pt`
- `metadata.json`

Each `.pt` file is a CPU `torch.float32` tensor with shape `[29, 3584]`: row 0
is the embedding output and rows 1--28 are the transformer-layer outputs.
`metadata.json` records the sample ID, exact chat-formatted prompt, token IDs,
decoded token strings, sequence length, token-ID hash, and per-model paths and
shape/configuration details. The script fails if the reused IDs or attention
mask differ, a tensor shape is unexpected, or any activation is NaN or Inf.
