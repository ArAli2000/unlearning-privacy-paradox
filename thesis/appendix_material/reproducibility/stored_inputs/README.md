# Stored cross-check inputs of `compute_tables.py`

Two small stored result tables that `export_scripts/compute_tables.py` compares with the FR@K values it recomputes from the raw PersistBench outputs. They affect the `Provenance` and `Source artifact` columns of `../../tables/persistbench_frk_complete.tsv` ("STORED (recomputed value identical)"), so they are part of byte-identical regeneration. Both are original files, copied byte for byte.

| File | Original location (historical label kept in the regenerated tables) | SHA-256 |
|---|---|---|
| `persistbench_all_methods_all_corpora.csv` | `presentation_figures_final/persistbench_all_methods_all_corpora.csv` | `a87f323b770941b12dd06a4bd7fe72ccbcc42acfb79287d714a6630ab81dbc72` |
| `persistbench_fr_at_k_muse_books_qwen25.csv` | `mechanistic/outputs/muse_books_weekly_update_analysis/persistbench_fr_at_k.csv` | `16884c88b1c79a60f8c8b354f8a8dfc2acf1b4078f261cf9dc81779191daf2a8` |

Digests are also in `SHA256SUMS` in this directory.

## Why `persistbench_all_methods_all_corpora.csv` is accepted as the canonical input

- **Documented source.** `thesis_defense_assets_bundle/PROVENANCE.md` (kept outside Git) records an "ORIGINAL COPY" of this file with the hash prefix `a87f323b770941b1`, which is the prefix of the digest above. `thesis/appendix_material/README.md` and `script_map.tsv` name it as a stored copy of the official `failure_rates.py` FR@K numbers (column `exclusions: none`, local Qwen2.5-7B-Instruct judge). A script that wrote the file was not preserved; it is not claimed here.
- **Schema.** 45 rows = 3 corpora (MUSE-News, MUSE-Books, TOFU-full) x 5 conditions (BASE, RMU, WGA, SatImp, SimNPO) x 3 categories (cross_domain, sycophancy, beneficial_memory); columns `corpus, method, category, fr1, fr2, fr3, numerator_fr3, denominator_fr3, checkpoint, base_model, judge, exclusions`. Checkpoint paths are repository-relative and match `thesis/manifests/selection/`.
- **Agreement with the frozen results.** In the tracked `persistbench_frk_complete.tsv`, all 45 rows that cite this file are labelled "STORED (recomputed value identical)": `compute_tables.py` recomputed FR@1/2/3 from the raw judged outputs and every stored value agreed within 0.011.
- **Byte-identical regeneration.** With this file, all five tracked tables are reproduced byte for byte (checked 2026-10-18 with the complete input set; see `thesis/README.md`).
- **Not proven:** which program produced the file. The checks above establish that its content is correct and is what the tables cite.

`persistbench_fr_at_k_muse_books_qwen25.csv` is written by `mechanistic/outputs/muse_books_weekly_update_analysis/analyze_existing_outputs.py` (line 108; that script is not tracked). All 9 rows of the tracked table that cite it are "STORED (recomputed value identical)".
