# SWE-bench Pro V2 (HARD-51, 51 tasks) — engine eval (measured run)

- upstream/eval commit recorded by CI: `dda506c12153b9138399949052742943cfc64ac5`
- Resolve decisions come from each task's own verifier inside the official container image.
- `nop` must resolve 0/N and `oracle` must resolve N/N or the causal number is not interpretable.

| arm | resolved | tasks | resolve % | model calls | cost USD | trial wall s (total) | engine s (total) | missing trials |
|---|---|---|---|---|---|---|---|---|

## Harness gates

- `oracle_gate_pass`: **FAIL**
- `nop_gate_pass`: **FAIL**

> **NO TRIAL DATA — THIS RUN PRODUCED NO BENCHMARK NUMBER.**
> No `result.json` was found for any expected task, so the 0/N columns below are
> a harness failure, not a score. Do not quote them as a resolve rate.

## Shard diagnostics (harness truth: did harbor even start trials?)

| artifact | harbor exit | log lines kept | last line |
|---|---|---|---|
| `causal-s0.meta.json` | 0 | 28 | `` |
| `causal-s1.meta.json` | 0 | 28 | `` |
| `causal-s2.meta.json` | 0 | 28 | `` |
| `causal-s3.meta.json` | 0 | 28 | `` |
| `causal-s4.meta.json` | 0 | 28 | `` |
| `causal-s5.meta.json` | 0 | 90 | `` |
| `nop-s0.meta.json` | 0 | 27 | `` |
| `nop-s1.meta.json` | 0 | 27 | `` |
| `nop-s2.meta.json` | 0 | 27 | `` |
| `nop-s3.meta.json` | 0 | 27 | `` |
| `nop-s4.meta.json` | 0 | 27 | `` |
| `nop-s5.meta.json` | 0 | 27 | `` |
| `oracle-s0.meta.json` | 0 | 28 | `` |
| `oracle-s1.meta.json` | 0 | 28 | `` |
| `oracle-s2.meta.json` | 0 | 28 | `` |
| `oracle-s3.meta.json` | 0 | 28 | `` |
| `oracle-s4.meta.json` | 0 | 28 | `` |
| `oracle-s5.meta.json` | 0 | 28 | `` |

## Per-task (causal arm)

| task | reward | resolved | agent status | engine status | engine pass | files | harness error |
|---|---|---|---|---|---|---|---|


## Incomplete shards in this run

These shard artifacts reported a collection error, so their tasks are counted as missing rather than resolved — the run is qualified, not discarded:

- `causal-s0`
- `causal-s1`
- `causal-s2`
- `causal-s3`
- `causal-s4`
- `causal-s5`
- `nop-s0`
- `nop-s1`
- `nop-s2`
- `nop-s3`
- `nop-s4`
- `nop-s5`
- `oracle-s0`
- `oracle-s1`
- `oracle-s2`
- `oracle-s3`
- `oracle-s4`
- `oracle-s5`
