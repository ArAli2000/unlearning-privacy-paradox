#!/usr/bin/env python3
"""Read-only SHA-256 hashing of the regular files directly inside the given directories (no recursion, so evals/logs/.hydra are skipped).
usage: tofu_hash_dirs.py OUT.json DIR [DIR ...]   Incremental: entries whose size+mtime match an existing record are not re-hashed."""
import hashlib, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.dont_write_bytecode = True
out, dirs = sys.argv[1], sys.argv[2:]
db = json.load(open(out)) if os.path.exists(out) else {}
def h(path):
    m = hashlib.sha256()
    with open(path, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 24), b''): m.update(ch)
    return m.hexdigest()
jobs = []
for d in dirs:
    d = os.path.abspath(d)
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if not os.path.isfile(p): continue
        st = os.stat(p); rec = db.get(d, {}).get(f)
        if rec and rec['size'] == st.st_size and rec['mtime'] == st.st_mtime: continue
        jobs.append((st.st_size, d, f, p, st))
jobs.sort(reverse=True); t0 = time.time(); done = 0
def run(j):
    size, d, f, p, st = j
    return d, f, dict(sha256=h(p), size=size, mtime=st.st_mtime, inode=st.st_ino, islink=os.path.islink(p), realpath=os.path.realpath(p))
with ThreadPoolExecutor(max_workers=6) as ex:
    for d, f, rec in ex.map(run, jobs):
        db.setdefault(d, {})[f] = rec; done += 1
        if done % 8 == 0: json.dump(db, open(out, 'w'), indent=1); print(f'{done}/{len(jobs)} files hashed, {time.time() - t0:.0f}s', flush=True)
json.dump(db, open(out, 'w'), indent=1); print(f'DONE {done} files in {time.time() - t0:.0f}s', flush=True)
