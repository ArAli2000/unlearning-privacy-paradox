#!/usr/bin/env python3
"""Build a read-only repository inventory of thesis-specific additions.

Writes only inside thesis_cleanup_audit/. Never touches the rest of the repo.

Scope is deliberately restricted to files the thesis author actually added or
modified (per git status + the directories named in the audit request). It
excludes vendored dependency internals (.venv, .git, __pycache__, egg-info
build artifacts) so counts reflect the thesis's own footprint rather than
third-party packages that happen to be nested underneath it.
"""
from __future__ import annotations
import csv, hashlib, os, re, subprocess, tarfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent

CLASSES = [
    "source code", "experiment launcher", "SLURM script", "configuration",
    "reusable utility", "frozen manifest", "generated result", "plot", "log",
    "temporary/debug", "obsolete experiment", "backup",
    "duplicate/near-duplicate", "external/upstream code", "checkpoint/model data",
]

def git_lines(*args):
    p = subprocess.run(["git", *args], cwd=ROOT, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
    return p.stdout.splitlines()

tracked = set(git_lines("ls-files"))
status = {}
for line in git_lines("status", "--porcelain=v1", "--untracked-files=all"):
    code = line[:2].strip() or "tracked"
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    status[path] = code

EXCLUDE_DIR_NAMES = {".git", "__pycache__", ".venv", "benchmark.egg-info", "open_unlearning.egg-info"}

def walk(base: Path):
    out = []
    for dp, dns, fns in os.walk(base):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIR_NAMES]
        for f in fns:
            out.append(Path(dp) / f)
    return out

paths = set()

# 1. Thesis-specific top-level directories (recursive, vendor-internals excluded)
for base in ["mechanistic", "external/PersistBench", "external/privacy-collapse",
             "supervisor_update", "meeting_updates", "tmp_paths"]:
    b = ROOT / base
    if b.exists():
        for p in walk(b):
            paths.add(str(p.relative_to(ROOT)))

# 2. Root-level launcher/table/test files
for p in ROOT.iterdir():
    if p.is_file() and (
        (p.name.startswith("run_") and (p.suffix == ".sh" or ".sh.bak" in p.name))
        or p.suffix == ".sbatch"
        or p.name.startswith("make_")
        or p.name.startswith("select_muse_")
        or p.name.startswith("test_muse_")
        or p.name.startswith("meeting_updates_")
        or p.suffix == ".tar.gz" or p.name.endswith(".tar.gz")
    ):
        paths.add(p.name)

# 3. scripts/eval_privacylens*
for p in (ROOT / "scripts").glob("eval_privacylens*"):
    if p.is_file():
        paths.add(str(p.relative_to(ROOT)))

# 4. Specific tracked/modified or new config + trainer + template files named in the audit request
for extra in [
    "configs/eval/tofu.yaml", "configs/eval/tofu_partial_backup.yaml",
    "configs/model/Qwen2.5-14B-Instruct.yaml", "configs/model/sedxTQNOq",
    "src/trainer/base.py", "src/trainer/base.py.bak_before_agg_proxy",
    "src/trainer/base.py.bak_before_bestagg_patch",
    "templates/simple_llama_chat_template.jinja",
]:
    if (ROOT / extra).exists():
        paths.add(extra)

backup_re = re.compile(r"(?:\.bak|_backup|backup_|\.orig|before_|~$)", re.I)
obsolete_re = re.compile(r"(?:smoke|debug|_test0|failed|retry|ckpt_sweep|limit50|partial|preview|remaining|pilot)", re.I)
manifest_dir_re = re.compile(r"/(manifests|annotations|model_lists|trainer_states)/", re.I)
code_ext = {".py", ".sh", ".sbatch"}
result_ext = {".json", ".jsonl", ".csv", ".tsv"}
plot_ext = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
doc_ext = {".md", ".txt"}

PERSISTBENCH_UPSTREAM_PREFIXES = (
    "external/PersistBench/src/", "external/PersistBench/pyproject.toml",
    "external/PersistBench/uv.lock", "external/PersistBench/README.md",
    "external/PersistBench/.gitignore",
)

def classify(path: str, size: int) -> str:
    low = path.lower()
    name = Path(path).name
    ext = Path(path).suffix.lower()

    if path.startswith("external/privacy-collapse/"):
        return "external/upstream code"
    if path.startswith(PERSISTBENCH_UPSTREAM_PREFIXES) and ".bak" not in low and "before_strict" not in low:
        return "external/upstream code"
    if backup_re.search(name):
        return "backup"
    if "/model_cache/" in low or ext in {".safetensors", ".bin", ".ckpt"}:
        return "checkpoint/model data"
    if ext in {".out", ".err", ".log"} or "/logs/" in low or low.startswith("logs/"):
        return "log"
    if ext in plot_ext:
        return "plot"
    if ext == ".sbatch":
        return "SLURM script"
    if manifest_dir_re.search("/" + low):
        return "frozen manifest"
    if ext in {".yaml", ".yml", ".toml", ".ini"} or "/configs/" in low or "/configs_local/" in low or low.startswith("configs/"):
        return "configuration"
    if low.startswith("tmp_paths/") and ext in code_ext:
        return "temporary/debug"
    if low.startswith("tmp_paths/"):
        return "temporary/debug"
    if "/work/" in low or ("debug" in low and ext in code_ext):
        return "temporary/debug"
    if obsolete_re.search(name) and ext in code_ext:
        return "obsolete experiment"
    if ext == ".sh":
        return "experiment launcher"
    if ext == ".py":
        if any(x in name for x in ["common", "util", "validate", "build_manifest", "prepare", "reconcile", "build_inventory"]):
            return "reusable utility"
        return "source code"
    if ext in result_ext:
        return "generated result"
    if ext in doc_ext:
        return "generated result" if any(x in low for x in ["/analysis/", "/results/", "supervisor_update"]) else "generated result"
    if ext == ".pt":
        return "generated result"
    if ext == ".gz":
        return "generated result"
    return "generated result"

def domain(path: str) -> str:
    low = path.lower()
    if "wmdp" in low or "meeting_updates" in low:
        return "WMDP side-investigation (out of final scope)"
    if "muse_books" in low and ("reconcil" in low or "comparison" in low):
        return "comparison/reconciliation"
    if "persistbench_sycophancy_mcq" in low or "persistbench_mcq" in low:
        return "controlled MCQ/A-B probe"
    if "persistbench_native" in low:
        return "native hidden states/sycophancy"
    if "privacy_collapse" in low or "privacylens" in low:
        return "PrivacyLens/representations"
    if "persistbench" in low:
        return "PersistBench"
    if "tofu" in low or "wga" in low and "tofu" in low:
        return "TOFU (legacy/broader, out of final scope)"
    if "muse_news" in low:
        return "MUSE-News"
    if "muse_books" in low:
        return "MUSE-Books"
    if "supervisor" in low:
        return "supervisor bundle/documentation"
    if path.startswith("external/privacy-collapse/"):
        return "external dependency (privacy-collapse)"
    if path.startswith("external/PersistBench/"):
        return "external dependency (PersistBench)"
    return "broader thesis/legacy"

def action(cls: str, path: str):
    low = path.lower()
    p = Path(path)
    d = domain(path)
    if cls == "external/upstream code":
        return "KEEP IN PLACE", path, "Vendored external dependency source; do not reorganize."
    if low.startswith("external/persistbench/") or low.startswith("external/privacy-collapse/"):
        if cls in {"generated result", "log", "checkpoint/model data", "plot"}:
            return "GENERATED OUTPUT / DO NOT COMMIT", path, "Vendored tool's own run output; gitignore in place, do not move."
        if cls == "configuration":
            return "KEEP IN PLACE", path, "Thesis-authored config for the vendored tool; must stay relative to the tool's own root to run."
    if cls in {"checkpoint/model data", "log"}:
        return "GENERATED OUTPUT / DO NOT COMMIT", f"(stays outside repo / on scratch storage) {path}", "Large/runtime artifact; document provenance, never commit."
    if cls in {"generated result", "plot"}:
        return "GENERATED OUTPUT / DO NOT COMMIT", f"outputs/{d.lower().replace('/', '_').replace(' ', '_').replace('(', '').replace(')', '')}/{p.name}", "Derived artifact; keep outside source tree, publish only curated small summaries."
    if cls == "backup":
        return "ARCHIVE", f"archive/{path}", "Superseded snapshot; keep for provenance, not on the active code path."
    if cls == "obsolete experiment":
        return "DELETE CANDIDATE (but DO NOT delete)", f"archive/{path}", "Naming/content suggests a smoke-test or superseded attempt; verify against final-result chain before discarding."
    if cls == "temporary/debug":
        return "DELETE CANDIDATE (but DO NOT delete)", f"archive/{path}", "One-off/debug artifact; verify nothing downstream depends on it, then archive or delete."
    if cls == "SLURM script":
        return "IMPORT/PATH UPDATE REQUIRED", f"thesis/slurm/{d.lower().replace('/', '_').replace(' ', '_').replace('(', '').replace(')', '')}/{p.name}", "Launcher embeds repository-relative/absolute paths; update on move."
    if cls == "experiment launcher":
        return "IMPORT/PATH UPDATE REQUIRED", f"thesis/scripts/{p.name}", "Move only together with any called-script/config path updates."
    if cls == "configuration":
        return "IMPORT/PATH UPDATE REQUIRED", f"thesis/configs/{p.name}", "Hydra/script references to this path must be updated on move."
    if cls == "frozen manifest":
        return "SAFE MOVE", f"thesis/manifests/{d.lower().replace('/', '_').replace(' ', '_').replace('(', '').replace(')', '')}/{p.name}", "Data-only frozen input; update any hard-coded consumer paths."
    if cls in {"source code", "reusable utility"}:
        sub = "probes" if "mcq" in low else "representations" if any(x in low for x in ["hidden", "representation", "extract", "position", "layer", "logit"]) else "behavioral"
        return "IMPORT/PATH UPDATE REQUIRED", f"thesis/analysis/{sub}/{p.name}", "Python imports and relative-path assumptions require coordinated update."
    return "KEEP IN PLACE", path, "No migration recommended."

def hardcoded(path: str, size: int) -> str:
    if size > 2_000_000 or Path(path).suffix.lower() not in {".py", ".sh", ".sbatch", ".yaml", ".yml", ".md", ".json", ".tsv", ".txt"}:
        return ""
    try:
        s = (ROOT / path).read_text(errors="ignore")
    except Exception:
        return ""
    hits = [tok for tok in ["/storage/ukp/", "/mnt/beegfs/", "/home/", "/tmp/", "ukp-student", "elshashay"] if tok in s]
    return ";".join(hits)

rows = []
for path in sorted(paths):
    fp = ROOT / path
    try:
        size = fp.stat().st_size
    except OSError:
        continue
    cls = classify(path, size)
    act, proposal, why = action(cls, path)
    gitstat = status.get(path, "tracked" if path in tracked else "ignored/untracked")
    rows.append(dict(
        current_path=path, classification=cls, domain=domain(path), size_bytes=size,
        git_status=gitstat, tracked_upstream="yes" if path in tracked else "no",
        proposed_action=act, proposed_path=proposal,
        hard_coded_environment=hardcoded(path, size),
        reproducibility_priority="critical" if any(x in path.lower() for x in [
            "manifest", "config", "selected_model", "reconciliation", "trainer_state", "make_final", "make_muse", "select_muse"
        ]) and cls not in {"backup", "obsolete experiment", "temporary/debug"} else "supporting",
        rationale=why,
    ))

with (OUT / "inventory.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

counts = Counter(r["classification"] for r in rows)
actions = Counter(r["proposed_action"] for r in rows)
domains = Counter(r["domain"] for r in rows)
actual_source = sum(counts[x] for x in ["source code", "reusable utility"])
launchers = counts["experiment launcher"] + counts["SLURM script"]
generated = sum(counts[x] for x in ["generated result", "plot", "log"])

# Exact-duplicate detection among small/medium files (source, config, docs) only.
hashes = defaultdict(list)
DUP_SKIP_CLASSES = {"log", "checkpoint/model data", "external/upstream code"}
for r in rows:
    if r["size_bytes"] == 0:
        continue  # zero-byte files trivially "match"; not meaningful duplicates
    if r["size_bytes"] <= 5_000_000 and r["classification"] not in DUP_SKIP_CLASSES:
        try:
            h = hashlib.sha256((ROOT / r["current_path"]).read_bytes()).hexdigest()
            hashes[h].append(r["current_path"])
        except OSError:
            pass
dups = [v for v in hashes.values() if len(v) > 1]

# tar.gz archive contents, listed (not extracted) for the record.
archive_listing = []
for name in ["supervisor_update/code_settings_bundle.tar.gz", "supervisor_update/code_settings_bundle_full.tar.gz", "tofu_qwen15_npo_f10_fixed.tar.gz"]:
    fp = ROOT / name
    if fp.exists():
        try:
            with tarfile.open(fp) as tf:
                members = tf.getnames()
            archive_listing.append((name, len(members), fp.stat().st_size))
        except Exception as e:
            archive_listing.append((name, -1, fp.stat().st_size))

inv = f"""# Thesis cleanup inventory

This audit is read-only with respect to the existing repository; nothing outside `thesis_cleanup_audit/` was created, moved, or modified. The inventory below is scoped to the thesis author's own additions/modifications: `mechanistic/`, `external/PersistBench/` and `external/privacy-collapse/` (vendored tool trees, excluding their internal `.venv`/`.git`), `supervisor_update/`, `meeting_updates/`, `tmp_paths/`, root-level `run_*.sh`/`*.sbatch`/`make_*.py` launchers, `scripts/eval_privacylens*`, the modified/added `configs/` and `src/trainer/base.py` files, and the two `.tar.gz` bundles. It deliberately **excludes** the rest of the upstream open-unlearning tree (which should not be reorganized) and excludes the multi-terabyte `saves/`, `logs/`, `outputs/`, `data/` directories that are already covered by the repository's existing `.gitignore` (`saves*/`, `logs/`, `output*/`, `data/`) — those are addressed qualitatively in `PROPOSED_STRUCTURE.md` rather than enumerated file-by-file.

**Correction vs. an earlier pass of this audit**: a prior inventory run (still visible in git history of this script, if kept) accidentally walked `external/PersistBench/.venv/` (a ~1.1&nbsp;GB installed Python virtualenv with ~28,000 files) and counted it as "PersistBench" thesis content, which inflated "source code" to 15,251 files and manufactured a fake "950-file duplicate group" out of trivially-identical empty `__init__.py`/`py.typed` stub files. That data has been discarded; this version excludes `.venv`, `.git`, `__pycache__`, and `*.egg-info` from every walk. `tracked_upstream=yes` means Git currently tracks the path; it does not mean the content is scientifically upstream (e.g. `configs/eval/tofu.yaml` and `src/trainer/base.py` are tracked upstream files the thesis modified in place).

## Summary

- Actual thesis source/reusable Python files: **{actual_source:,}**
- Experiment and SLURM launchers: **{launchers:,}** ({counts['experiment launcher']} shell launchers; {counts['SLURM script']} SLURM scripts)
- Generated results/plots/logs: **{generated:,}**
- Backups: **{counts['backup']:,}**
- Checkpoint/model/cache files (metadata only; large binaries not read): **{counts['checkpoint/model data']:,}**
- Temporary/debug files: **{counts['temporary/debug']:,}**
- Likely obsolete experiment files: **{counts['obsolete experiment']:,}**
- Vendored external/upstream files (kept in place, not thesis code): **{counts['external/upstream code']:,}**
- Exact duplicate groups (non-empty files <=5&nbsp;MB, excluding logs/checkpoints/vendored code): **{len(dups):,}**
- Total files inventoried: **{len(rows):,}**

## Classification counts

""" + "\n".join(f"- {k}: {counts[k]:,}" for k in CLASSES) + "\n\n## Proposed-action counts\n\n" + "\n".join(f"- {k}: {v:,}" for k, v in actions.most_common()) + "\n\n## Domain counts\n\n" + "\n".join(f"- {k}: {v:,}" for k, v in domains.most_common()) + "\n\n## Archive bundle contents (listed only, not extracted)\n\n" + "\n".join(f"- `{n}` ({sz:,} bytes): {cnt} members" if cnt >= 0 else f"- `{n}` ({sz:,} bytes): could not list" for n, cnt, sz in archive_listing) + "\n\n## Interpretation\n\nCounts are audit classifications, not deletion instructions. Generated artifacts that are small and thesis-critical may be selectively published, but raw benchmark JSONs, tensors, logs, and checkpoints should remain outside the source commit. See `inventory.csv` for every path and proposed action, `DUPLICATION_REPORT.md` for duplicate groups, and `MIGRATION_PLAN.md` for the per-file CURRENT -> PROPOSED mapping.\n"

(OUT / "INVENTORY.md").write_text(inv)

dup = "# Duplication report\n\nExact-duplicate groups below are content-hash matches (SHA-256) among non-empty files <=5 MB, excluding logs, checkpoint binaries, and vendored external/upstream code. A prior pass of this report was contaminated by an accidental scan of `external/PersistBench/.venv/`, which produced a bogus 950-file 'duplicate' group made entirely of trivially-identical empty stub files; that scan is discarded and excluded here.\n\n## Exact duplicate groups\n\n"
if not dups:
    dup += "(none found within the corrected thesis-scoped file set; see DUPLICATION_REPORT.md's hand-authored sections for *near*-duplicate scripts, which differ byte-for-byte but are functionally redundant.)\n\n"
for i, g in enumerate(sorted(dups, key=lambda x: (-len(x), x[0])), 1):
    dup += f"### Group {i} ({len(g)} files)\n\n" + "\n".join(f"- `{x}`" for x in g) + "\n\n"
dup += "## Variant-name candidates (final/fixed/v2/debug/backup/retry/remaining/smoke/test naming)\n\n"
variants = [r["current_path"] for r in rows if re.search(r"(?:final|fixed|v\d+|debug|backup|bak|old|retry|remaining|smoke|test)", Path(r["current_path"]).name, re.I)]
dup += "\n".join(f"- `{x}`" for x in variants) + "\n"
(OUT / "DUPLICATION_REPORT_AUTO.md").write_text(dup)

print(dict(files=len(rows), actual_source=actual_source, launchers=launchers, generated=generated,
           backups=counts['backup'], duplicate_groups=len(dups), obsolete=counts['obsolete experiment'],
           external_upstream=counts['external/upstream code']))
