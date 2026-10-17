# RMU vs BASE weight-locality verification

Direct byte-level diff of BASE (`saves/finetune/muse_news_qwen25_7b_instruct_target`) and
RMU (`saves/unlearn/muse_news_qwen25_7b_instruct_rmu/checkpoint-459`) safetensors weights
(bf16 upcast to fp32 by left-shifting the raw uint16 into a uint32 and reinterpreting as
float32), computed CPU-only with no model loading -- the login node lacks the
safetensors/torch packages, so shards were parsed manually via the safetensors binary
format (8-byte little-endian header length + JSON header + raw tensor bytes).

## Per-layer MLP down_proj.weight

| Layer | diff_norm | base_norm | relative diff |
|---:|---:|---:|---:|
| 0 | 1.5669 | 114.9672 | 0.013629 |
| 1 | 1.2075 | 101.1578 | 0.011936 |
| 2 | 1.0065 | 115.2341 | 0.008735 |
| 3 | 1.1159 | 130.8310 | 0.008529 |
| 4 | 1.1334 | 128.3681 | 0.008829 |
| 5 | 1.1779 | 131.6352 | 0.008948 |
| 6 | 1.3477 | 127.2564 | 0.010590 |
| 7 | 2.3829 | 132.2619 | 0.018017 |
| 8 | 0.0000 | 133.6883 | 0.000000 |
| 9 | 0.0000 | 122.9033 | 0.000000 |
| 10 | 0.0000 | 131.9980 | 0.000000 |
| 11 | 0.0000 | 133.7020 | 0.000000 |
| 12 | 0.0000 | 135.4292 | 0.000000 |
| 13 | 0.0000 | 133.3014 | 0.000000 |
| 14 | 0.0000 | 134.5099 | 0.000000 |
| 15 | 0.0000 | 135.5273 | 0.000000 |
| 16 | 0.0000 | 134.6672 | 0.000000 |
| 17 | 0.0000 | 134.8880 | 0.000000 |
| 18 | 0.0000 | 137.4892 | 0.000000 |
| 19 | 0.0000 | 136.7310 | 0.000000 |
| 20 | 0.0000 | 137.5746 | 0.000000 |
| 21 | 0.0000 | 137.5301 | 0.000000 |
| 22 | 0.0000 | 138.5797 | 0.000000 |
| 23 | 0.0000 | 138.4502 | 0.000000 |
| 24 | 0.0000 | 140.6486 | 0.000000 |
| 25 | 0.0000 | 143.4077 | 0.000000 |
| 26 | 0.0000 | 143.3317 | 0.000000 |
| 27 | 0.0000 | 133.0266 | 0.000000 |

## Additional spot checks (all consistent with the same pattern)

- `model.embed_tokens.weight`: diff=1.5397, base=303.4142, rel=0.005074 (small nonzero)
- `model.norm.weight`: diff=0.0 (bit-identical)
- `lm_head.weight`: diff=0.0 (bit-identical)
- `self_attn.o_proj.weight` layers 0, 5, 6, 7: nonzero (relative diff 0.0108-0.0116)
- `self_attn.o_proj.weight` layers 8, 9: diff=0.0 (bit-identical)
- `input_layernorm.weight` layers 6, 7: tiny nonzero (~1e-5 relative)
- `input_layernorm.weight` layer 8: diff=0.0 (bit-identical)

## Conclusion

This RMU checkpoint (checkpoint-459) differs from BASE only in layers 0-7 (peak magnitude
at layer 7) plus a small embedding-table shift. Layers 8-27, the final norm, and the LM
head are bit-identical to BASE.

This is why any activation-patching block whose earliest layer is >=7 (i.e. L7-13, L14-20,
L21-27) fully collapses to the donor model's exact natural output: a forward hook
overwrites the recipient's layer output entirely, discarding whatever the recipient's own
(possibly-modified) earlier layers computed. Once that overwritten layer is at or after
the sole modified region (layer 7), every subsequent layer is weight-identical between
donor and recipient, so the remaining computation exactly reproduces the donor's own
natural forward pass -- regardless of which specific later block was nominally patched.
Only the L0-6 block (which does not fully cover layer 7) leaves RMU's actual modified
computation partially in the causal path, producing a result that differs from both the
unpatched score and from full donor substitution.

This is a genuine architectural property of this checkpoint (consistent with RMU-style
methods that concentrate their training objective on a small number of early-to-mid
layers), not a bug in the activation-patching script -- the same script code, applied to
SatImp/SimNPO (which fine-tune all layers), produces genuinely distinct values at each
layer block (verified against `../activation_patching_clean_audit/clean_activation_patching_summary.csv`).
