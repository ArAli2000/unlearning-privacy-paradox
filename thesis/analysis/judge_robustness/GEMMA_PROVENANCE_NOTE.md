# Gemma judge provenance note

**Canonical identity**: `google/gemma-2-9b-it`

**Local path**: `/storage/ukp/shared/shared_model_weights/models--google--gemma-2-9b-it`

**Revision**: **unknown**. This is a flat shared-cluster copy of the model files, not a standard Hugging Face hub cache layout (no `refs/`, `snapshots/`, or `.lock` metadata directories exist alongside it), and no `_commit_hash` is embedded in `config.json` or `tokenizer_config.json`. The exact git revision on Hugging Face Hub that these files correspond to **cannot be determined from local cache metadata** and is not claimed here. (Earlier in this investigation, the current HF `main`-branch SHA, `11c9b309abf73637e4b6f9a3fa1e92e615547819`, was fetched from the public HF API for reference — this is the *current remote* revision, not a confirmed match to this local copy, and must not be read as such.)

## Reproducibility fingerprints (small metadata files only — the ~18.5GB weight shards were not hashed)

| File | SHA-256 |
|---|---|
| `config.json` | `8ecc124513fdb0bb31bf51b4f0dd6c8658a68296dc8cd30af612205ff4a1bc49` |
| `tokenizer_config.json` | `cb32b7929c62608d46572e813112b3ad8a841fb98fdd6a4da8559e368a951c89` |
| `generation_config.json` | absent from this local copy |
| `model.safetensors.index.json` | `c38b39b80b2d7aa422464a9b816af4c30d2177e471b89e5325df1336a23ad284` |
| `special_tokens_map.json` | `baec30ea10906f16adb8c18af7a34023002c1746542612b8b41c9f09e1351351` |
| `tokenizer.json` | `3f289bc05132635a8bc7aca7aa21255efd5e18f3710f43e3cdb96bcd41be4922` |

These fingerprints identify *this exact local copy's metadata/tokenizer files*, independent of any HF revision hash — anyone who wants to confirm they are using the same local model can re-hash these same small files rather than re-hashing the full weights.

## Completeness/architecture evidence (for full detail, see `smoke_test/gemma_availability_check.md`)

- `config.json`: `Gemma2ForCausalLM`, `hidden_size=3584`, `num_hidden_layers=42` — matches the published Gemma-2-9B architecture.
- All 4 `model-0000{1..4}-of-00004.safetensors` shards present; sizes sum exactly to the `total_size: 18483411968` declared in `model.safetensors.index.json`.
- `tokenizer_config.json` has a Gemma-format `chat_template` (`user`/`model` turns, no system role); `special_tokens_map.json` has `<start_of_turn>`/`<end_of_turn>` — confirms instruction-tuned.
