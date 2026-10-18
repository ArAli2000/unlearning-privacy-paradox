#!/usr/bin/env python3
"""Lightweight, CPU-only integrity check of the repository (standard library and git only; no experiment artifacts needed).

Run from anywhere:  python3 thesis/scripts/validation/check_repo_integrity.py
Exit code 0 = all checks pass, 1 = at least one check failed.

Checks
  1. Every local script (.py/.sh/.sbatch under thesis/, mechanistic/, scripts/, src/) that a tracked launcher
     (thesis/**/*.sh, mechanistic/**/*.{sh,sbatch}) calls exists in the tracked tree (or is untracked but not git-ignored). Paths into submodules
     (external/) and generated outputs (mechanistic/outputs/) are not checked.
  2. No launcher still calls the removed PrivacyLens path `scripts/eval_privacylens_mcq_*.py`, and the three
     canonical PrivacyLens evaluator scripts exist under thesis/scripts/privacylens/.
  3. compute_tables.py runs its input preflight (`--check-inputs`) without crashing, lists its inputs, and every input
     it declares as tracked is present and not git-ignored. Untracked inputs (raw experiment artifacts) may be missing; that is reported
     as information, not as a failure, because they are not part of the repository.
  4. thesis/manifests/selection/selected_checkpoint_metrics.tsv is exactly what build_selected_checkpoint_metrics.py
     builds from the tracked trainer states, MUSE summaries and selection TSVs.
  5. No launcher contains a personal or cluster-specific absolute path in an executable (non-comment) line.
  6. The evidence files meant for publication (public artifact manifests, stored inputs, PrivacyLens results, trainer
     states, MUSE summaries, CITATION.cff) contain no absolute cluster or home path (which would carry an account name).
"""
import re
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[3]
failures, notes = [], []


def git_files():
    # tracked files plus untracked-but-not-ignored ones (files that are about to be committed); in a clean clone this is the tracked set
    out = subprocess.run(['git', '-C', str(R), 'ls-files', '--cached', '--others', '--exclude-standard'], capture_output=True, text=True, check=True).stdout
    return set(out.split('\n')) - {''}


TRACKED = git_files()

# Scripts that are referenced by tracked launchers but deliberately live only in thesis_archive.zip.
KNOWN_ARCHIVE_ONLY = set()  # none at present
SKIP_PREFIXES = ('external/', 'mechanistic/outputs/')
REF = re.compile(r'(?<![\w/.-])(?:\$\{?(?:REPO_ROOT|PROJECT_ROOT|REPO)\}?/)?((?:thesis|mechanistic|scripts|src)/[A-Za-z0-9_./\-]+\.(?:py|sh|sbatch))')

# 1 + 2: script references in launchers
launchers = sorted(f for f in TRACKED if f.endswith(('.sh', '.sbatch')) and f.startswith(('thesis/', 'mechanistic/')))
n_refs = 0
for f in launchers:
    for ln, line in enumerate((R / f).read_text(errors='ignore').splitlines(), 1):
        code = line.split('#', 1)[0] if line.lstrip().startswith('#') else line
        if line.lstrip().startswith('#'):
            continue
        for m in REF.finditer(code):
            rel = m.group(1)
            if rel.startswith(SKIP_PREFIXES):
                continue
            n_refs += 1
            if rel in TRACKED:
                continue
            if rel in KNOWN_ARCHIVE_ONLY:
                notes.append(f'{f}:{ln}: {rel} is in thesis_archive.zip only (allow-listed)')
            else:
                failures.append(f'{f}:{ln}: referenced script does not exist in the tracked tree: {rel}')
print(f'checked {n_refs} script references in {len(launchers)} launchers')

for f in launchers:
    for ln, line in enumerate((R / f).read_text(errors='ignore').splitlines(), 1):
        if re.search(r'(?<![\w/])scripts/eval_privacylens_mcq_\w+\.py', line) and not line.lstrip().startswith('#'):
            failures.append(f'{f}:{ln}: uses the removed path scripts/eval_privacylens_mcq_*.py; use thesis/scripts/privacylens/')
for name in ('eval_privacylens_mcq_local.py', 'eval_privacylens_mcq_local_strict.py', 'eval_privacylens_mcq_forced_choice.py'):
    if f'thesis/scripts/privacylens/{name}' not in TRACKED:
        failures.append(f'canonical PrivacyLens script missing: thesis/scripts/privacylens/{name}')
for f in launchers:
    if f.startswith('thesis/scripts/privacylens/run_') and not re.search(r'thesis/scripts/privacylens/eval_privacylens_mcq_\w+\.py', (R / f).read_text()):
        failures.append(f'{f}: does not call a canonical thesis/scripts/privacylens/eval_privacylens_mcq_*.py')

# 3: compute_tables.py preflight
ct = 'thesis/appendix_material/reproducibility/export_scripts/compute_tables.py'
if ct not in TRACKED:
    failures.append(f'{ct} is not tracked')
else:
    r = subprocess.run([sys.executable, '-I', '-B', str(R / ct), '--check-inputs'], capture_output=True, text=True, cwd='/')
    lines = [ln.split('\t') for ln in r.stdout.splitlines() if ln.count('\t') >= 4]
    if r.returncode not in (0, 2):
        failures.append(f'{ct} --check-inputs crashed (exit {r.returncode}): {r.stderr.strip()[-300:]}')
    elif not lines:
        failures.append(f'{ct} --check-inputs listed no inputs')
    else:
        for status, trk, rel, declared, actual in lines:
            # declared-tracked inputs must be present and must not be git-ignored (tracked, or about to be committed)
            if declared == 'declared-tracked' and (status != 'present' or subprocess.run(['git', '-C', str(R), 'check-ignore', '-q', actual]).returncode == 0):
                failures.append(f'{ct}: input declared as tracked is missing or git-ignored: {actual}')
        missing = [ln[2] for ln in lines if ln[0] == 'MISSING']
        untracked_present = sum(1 for ln in lines if ln[0] == 'present' and ln[1] != 'tracked')
        notes.append(f'compute_tables.py: {len(lines)} inputs, {len(missing)} missing, {untracked_present} present but untracked (raw experiment artifacts are not part of the repository)')

# 5: launchers are free of personal absolute paths (comments may mention provenance)
LAUNCHER_PRIVATE = re.compile(r'/storage/ukp/work|/mnt/beegfs/work|/home/[A-Za-z]')
for f in launchers:
    for ln, line in enumerate((R / f).read_text(errors='ignore').splitlines(), 1):
        if not line.lstrip().startswith('#') and LAUNCHER_PRIVATE.search(line):
            failures.append(f'{f}:{ln}: personal or cluster-specific absolute path in an executable line')

# 4: normalised metrics table is consistent with its sources
bm = 'thesis/scripts/validation/build_selected_checkpoint_metrics.py'
if bm in TRACKED:
    rc = subprocess.run([sys.executable, '-I', '-B', str(R / bm), '--check']).returncode
    if rc != 0:
        failures.append('thesis/manifests/selection/selected_checkpoint_metrics.tsv does not match what build_selected_checkpoint_metrics.py builds from the tracked records')
else:
    failures.append(f'{bm} is not tracked')

# 6: publishable evidence is free of usernames and absolute cluster paths
PRIVATE = re.compile(r'/mnt/beegfs|/storage/ukp/work|/nfs/|/home/\w')  # absolute cluster/home paths (they carry the account name)
PUBLISHABLE = ('thesis/appendix_material/reproducibility/artifact_manifest', 'thesis/appendix_material/reproducibility/ARTIFACT_MANIFEST_README.md', 'thesis/appendix_material/reproducibility/stored_inputs/',
               'thesis/results/privacylens/', 'thesis/manifests/trainer_states/', 'thesis/manifests/muse_eval/', 'thesis/manifests/selection/selected_checkpoint_metrics.tsv', 'CITATION.cff')
n_pub = 0
for f in sorted(TRACKED):
    if f.startswith(PUBLISHABLE):
        n_pub += 1
        m = PRIVATE.search((R / f).read_text(errors='ignore'))
        if m:
            failures.append(f'{f}: contains a username or absolute cluster path ({m.group(0)})')
print(f'scanned {n_pub} publishable evidence files for usernames and absolute paths')

for n in notes:
    print('note:', n)
if failures:
    print(f'\nFAILED: {len(failures)} problem(s)')
    for f in failures:
        print('  -', f)
    sys.exit(1)
print('OK: repository integrity checks passed')
