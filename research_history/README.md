# Research history

This tree preserves the thesis's earlier research phases — work that is no longer part of the final reported MUSE-News/MUSE-Books pipeline (which lives in `../thesis/`), but that documents how the final scope, models, methods, and checkpoint-selection methodology were reached.

**Nothing here is obsolete clutter.** Every phase folder below represents genuine, completed research with real results, kept for grading and reproducibility. Large generated outputs, model checkpoints, and tensors are **not** copied here — only the scripts, configs, and small provenance records (manifests, frozen selection tables, trainer-state snapshots) needed to understand, and in principle reproduce, each phase. See `../thesis/docs/experiment_history.md` for the full narrative timeline connecting every phase below to the final thesis work, and `../thesis_cleanup_audit/MIGRATION_PLAN.md` for the exact source→destination mapping this tree was built from.

- **`01_tofu_baselines/`** — the first working unlearning pipeline: all 10 open-unlearning methods on TOFU, small models (Llama-3.2-1B, Qwen2.5-1.5B/3B).
- **`02_model_method_scaling/`** — scaling the same methods to larger models (up to 14B) and the full TOFU forget set; PrivacyLens introduced as a second evaluation axis.
- **`03_checkpoint_selection_development/`** — where the harmonic-mean utility/forgetting checkpoint-selection metric (the direct ancestor of the final `best_agg`) was invented and first validated.
- **`04_muse_track_a/`** — the first complete MUSE-News result, using the official HuggingFace target directly. Superseded by the locally-finetuned-target track used in the final thesis (see `../thesis_cleanup_audit/MUSE_NEWS_TRACK_RESOLUTION.md`), but a real, complete, working result in its own right.
- **`05_wmdp_side_investigation/`** — a safety-generalization side investigation on WMDP-cyber/bio that directly motivated the pivot to the mechanistic-interpretability phase now in `../thesis/`.

Each phase folder has its own `README.md` with: the question investigated, dataset/models/methods used, key scripts/configs, what was learned, why the thesis moved on, and whether/how it influenced the final methodology.
