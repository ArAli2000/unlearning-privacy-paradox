# SLURM launch-failure diagnosis

**Root cause isolated: node `penelope` specifically. Not Gemma, not the judging pipeline, not the account/partition/QOS/resource configuration.** A minimal diagnostic job with an otherwise-identical SLURM header succeeded immediately on a different node (`rubeus`) in the same partition, with the same GRES type. Per the task's instruction, no cause beyond what the evidence directly shows is claimed below — in particular, **prolog/cgroup/PAM is not asserted as the cause**, since no node-level (syslog/prolog) evidence was collected, only SLURM accounting-level evidence.

## 1. Exact SLURM evidence for every job

| JobID | JobName | Account | Partition | QOS | ReqTRES | Node | State | ExitCode | Reason | StdOut/StdErr |
|---|---|---|---|---|---|---|---|---|---|---|
| 438606 | gemma_judge_smoke | ukp-student | gpu | gpu-small | cpu=8,mem=180G,gres/gpu:a180=1 | penelope | FAILED | 0:53 | *(scontrol expired — job no longer in live cache; sacct confirms State/ExitCode above)* | none created |
| 438607 | gemma_judge_smoke | ukp-student | gpu | gpu-small | cpu=8,mem=180G,gres/gpu:a180=1 | penelope | FAILED | 0:53 | *(same, expired from scontrol)* | none created |
| 438608 | diag_test | ukp-student | gpu | gpu-small | cpu=8,mem=180G,gres/gpu:a180=1 | penelope | FAILED | 0:53 | `RaisedSignal:53(Real-time_signal_19)` | none created |
| 438609 | diag_test_small | ukp-student | gpu | gpu-small | cpu=2,mem=8G,gres/gpu:a180=1 | penelope | FAILED | 0:53 | `RaisedSignal:53(Real-time_signal_19)` | none created |
| 438610 | diag_knowngood | ukp-student | gpu | gpu-small | cpu=8,mem=120G,gres/gpu:a180=1 | penelope | FAILED | 0:53 | `RaisedSignal:53(Real-time_signal_19)` (via sacct/scontrol) | none created |
| **438611** | diag_othernode | ukp-student | gpu | gpu-small | cpu=8,mem=120G,gres/gpu:a180=1 | **rubeus** | **COMPLETED** | **0:0** | — | **both created, real GPU output** |

For 438606/438607, `scontrol show job` returned `slurm_load_jobs error: Invalid job id specified` (they had already aged out of SLURM's live job-state cache by the time this diagnosis was performed); `sacct` (the persistent accounting database) confirms their `State=FAILED`, `ExitCode=0:53`, `NodeList=penelope` directly.

**Where "`RaisedSignal:53`" comes from, precisely**: this exact string is produced by `scontrol show job`'s `Reason=` field (SLURM's own job-state daemon output), e.g. verbatim from job 438608/438609/438610: `JobState=FAILED Reason=RaisedSignal:53(Real-time_signal_19) ... ExitCode=0:53`. This is not a guess or an interpretation on my part — it is SLURM's own diagnostic text. Separately, the `seff` tool reported job 438608 as `State: FAILED (exit code 15)` — a different number than the `0:53` shown by `sacct`/`scontrol`. This discrepancy between `seff` and `sacct`/`scontrol` is noted but not resolved here (both are downstream SLURM tools reading the same accounting record; which one is "authoritative" for the numeric exit code is not something I can determine from the outputs alone). Signal 53 on Linux corresponds to a real-time signal (`SIGRTMIN+19`, since `SIGRTMIN` is typically 34 on this platform: 34+19=53) — consistent with `scontrol`'s own parenthetical `(Real-time_signal_19)`. I have **not** independently verified what raised this signal (no node-level log access was available from a user shell), so I report the string as SLURM produced it, without asserting a root cause for it beyond "this happens specifically when the job lands on node `penelope`."

## 2. Smoke-test `#SBATCH` header inspection

```
#SBATCH --job-name=gemma_judge_smoke
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
```

No `--nodelist`/`-w`, no `--exclude`, no `--constraint` anywhere in the file. **Node `penelope` was not explicitly requested by this script — it was automatically assigned by the scheduler** (confirmed directly: `scontrol show job` for 438608/438609 shows `ReqNodeList=(null)`, yet `NodeList=penelope` in the allocation). It happened to auto-assign `penelope` on every one of the 5 auto-assigned attempts (438606–438610, the last of which explicitly re-requested `penelope` deliberately, see below) — plausibly because `penelope` was the least-loaded/highest-priority `a180` node at submission time (its `Weight=175521` and `LastBusyTime` place it as an attractive scheduling target), not because of anything in my script.

## 3. Known-good SLURM configuration from this repository

The closest, most directly comparable prior success: `thesis/scripts/persistbench/run_local_judge_server_penelope.sh` — the script this thesis already used, repeatedly and successfully, to serve a **local vLLM judge model** (the exact same kind of job as the Gemma smoke test, just with Qwen instead of Gemma):

```
#SBATCH --job-name=local_judge
#SBATCH --partition=gpu
#SBATCH --nodelist=penelope
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=120G
#SBATCH --time=12:00:00
```
(no explicit `--account` line in this particular script)

**Proof this actually ran successfully**: surviving logs `logs/local_judge_{407848,407849,407852,408628,408988}.out`, e.g. `logs/local_judge_408628.out` (2026-07-08) contains a full vLLM v0.23.0 startup banner and successfully served `Qwen/Qwen2.5-7B-Instruct` as `local-judge` on port 8001 — this is the job whose output is cited as evidence in `thesis_cleanup_audit/PERSISTBENCH_MODIFICATIONS.md`'s judge-provenance discussion.

A second comparison point, `thesis/scripts/persistbench/run_persistbench_muse_news_qwen25_selected.sh` (the canonical Track-B generation script, confirmed successfully run 2026-07-08 per `thesis/docs/generation_provenance.md`):
```
#SBATCH --account=ukp-student
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a180:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=180G
#SBATCH --time=12:00:00
```
This is nearly identical to the failed smoke test's header (same account, partition, gres, cpus, mem) — the only structural difference is an `--array=0-4%1` directive it also carries, and no explicit nodelist (auto-assigned at the time, unknown which node from the surviving evidence alone).

**Test A (§5) replicated the `run_local_judge_server_penelope.sh` header exactly** (`--nodelist=penelope`, `mem=120G`, no explicit `--account`) with a trivial `hostname`/`nvidia-smi` payload — **it failed identically** (job 438610, `RaisedSignal:53`). This rules out every configuration difference between the historical known-good script and the failed smoke test as the cause — the same exact header that worked in July fails now, on this same node.

## 4. Current cluster state (read-only inspection)

- `scontrol show node penelope`: `State=IDLE`, no DOWN/DRAIN/FAIL/RESERVED flag, `Gres=gpu:a180:8`, `AllocTRES=` (nothing allocated), `CPULoad=0.32`. **Nothing in the node's reported state itself indicates a problem.**
- `BootTime=2026-09-13T10:53:03` — the node rebooted the day before this diagnosis (2026-09-14). Noted as a timing coincidence with the failures; not confirmed as the cause.
- `sinfo -R` (nodes with a reported problem reason): only `melvin` (2026-04-30) and `scratchy`/`thanos` (2026-04-22) are flagged, both with old timestamps — **`penelope` is not flagged by SLURM's own health-reporting mechanism.**
- `scontrol show partition gpu`: `AllowAccounts=ukp-researcher,ukp-student,ukp-gpu-large,system-admin`, `AllowQos=interactive,gpu,gpu-small,gpu-large`, `State=UP` — `ukp-student` is explicitly permitted.
- `sacctmgr show assoc user=<me>`: confirms `ukp-student` account has `cpu,gpu-small,interactive` QOS access — matches what every job above was actually granted (`QOS=gpu-small`), so **the account/QOS association is not the issue**.

**Conclusion of this section**: nothing observable from a normal-user SLURM inspection explains the failure other than the plain empirical fact that it happens on `penelope` and not on `rubeus`.

## 5. Minimal control tests (3 submitted, in order)

| # | Test | Header vs. failed smoke test | Node | Result |
|---|---|---|---|---|
| A | `diag_knowngood` (438610) | Exact `run_local_judge_server_penelope.sh` header (`--nodelist=penelope`, `mem=120G`, no `--account`) | penelope (explicitly requested) | **FAILED**, `RaisedSignal:53`, no output — identical to every other penelope attempt |
| B | *(not run as a distinct step — the original smoke test already had no node constraint to remove; every one of tests 438606–438609 already represents "no explicit node constraint," and all were auto-assigned penelope)* | — | — | — |
| C | `diag_othernode` (438611) | Same as Test A, but `--nodelist=rubeus` instead of `penelope` | **rubeus** | **COMPLETED**, exit 0:0, real output: `rubeus.ukp.informatik.tu-darmstadt.de` / `NVIDIA A100-SXM4-80GB, 81920 MiB` |

Per the task's instruction to stop as soon as one minimal GPU job runs successfully: **stopped after test C (438611).**

## 6. What differed between the failing and succeeding configuration

**Only the node.** Test A and Test C are byte-for-byte identical `#SBATCH` headers except for `--nodelist=penelope` vs. `--nodelist=rubeus`, and the same trivial payload. Account, partition, QOS, GRES type/count, CPU count, memory, and time limit were all identical. This isolates the failure to node `penelope` specifically, at this point in time, for this account — not to anything about the Gemma judging job, the SLURM resource request shape, or the account/QOS/partition configuration.

## 7. Correction applied

`run_gemma_judge_smoketest.sbatch` updated with the **one necessary change**: `#SBATCH --nodelist=rubeus` added (pinning to the node just proven to work), leaving every other directive as it already was (this also matches `run_local_judge_server_penelope.sh`'s own precedent of pinning to a specific node explicitly, just now pointing at a currently-healthy one). No Python/Gemma/vLLM code was changed.

## 8. Cluster-support information (for reference, in case `penelope` needs administrator attention regardless of whether the Gemma smoke test now succeeds on `rubeus`)

- Failed job IDs: 438606, 438607, 438608, 438609, 438610 (all on `penelope`)
- Succeeded: 438611 (identical config, `rubeus`)
- Account: `ukp-student` / Partition: `gpu` / QOS: `gpu-small` (auto-assigned)
- Node: `penelope`, `State=IDLE` per `scontrol`, rebooted 2026-09-13T10:53:03
- Exact failure: `JobState=FAILED Reason=RaisedSignal:53(Real-time_signal_19)`, `ExitCode=0:53` (via `sacct`/`scontrol`); `seff` separately reports `exit code 15` for the same job — discrepancy not resolved
- Proof the job fails before user code starts: no `--output`/`--error` files are created at all, for any of the 5 failed attempts, including a header identical to a script (`run_local_judge_server_penelope.sh`) that ran successfully on this same node as recently as 2026-07-08 (`logs/local_judge_408988.out`)
- A byte-for-byte-identical header succeeds immediately when `--nodelist` is changed to `rubeus`
