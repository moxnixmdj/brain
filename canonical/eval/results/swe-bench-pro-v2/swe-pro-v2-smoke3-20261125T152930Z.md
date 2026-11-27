# SWE-bench Pro V2 (smoke: 3 qutebrowser HARD-51 tasks) — engine eval (measured run)

- upstream/eval commit recorded by CI: `e49d7b6f2ae682832bab7a16fb0c51431c0827d4`
- Resolve decisions come from each task's own verifier inside the official container image.
- `nop` must resolve 0/N and `oracle` must resolve N/N or the causal number is not interpretable.

| arm | resolved | tasks | resolve % | model calls | cost USD | wall s (total) | wall s (mean) | missing trials |
|---|---|---|---|---|---|---|---|---|
| causal | 0 | 3 | 0.0 | 0 | 0.0 | 10.63 | 3.54 | 0 |
| nop | 0 | 3 | 0.0 | 0 | 0.0 | 145.85 | 48.62 | 0 |
| oracle | 3 | 3 | 100.0 | 0 | 0.0 | 150.78 | 50.26 | 0 |

## Harness gates

- `oracle_gate_pass`: **PASS**
- `nop_gate_pass`: **PASS**

## Shard diagnostics (harness truth: did harbor even start trials?)

| artifact | harbor exit | log lines kept | last line |
|---|---|---|---|
| `causal-s0.meta.json` | 0 | 28 | `` |
| `nop-s0.meta.json` | 0 | 27 | `` |
| `oracle-s0.meta.json` | 0 | 28 | `` |

## Per-task (causal arm)

| task | reward | resolved | agent status | engine status | files changed |
|---|---|---|---|---|---|
| `instance_qutebrowser__qutebrowser-3e21c8214a998cb1058def` | 0.0 | no | EDITS_UPLOADED | PASS | 1 |
| `instance_qutebrowser__qutebrowser-c09e1439f145c66ee3af57` | 0.0 | no | NO_EDITS | FAIL_CLOSED | 0 |
| `instance_qutebrowser__qutebrowser-deeb15d6f009b3ca0c3bd5` | 0.0 | no | HARNESS_ERROR | None | 0 |

What the engine did across the causal arm (behaviour, not a score): `EDITS_UPLOADED`×1, `HARNESS_ERROR`×1, `NO_EDITS`×1. Resolve rate is decided only by each task's own verifier.

