# SWE-bench Pro V2 (smoke: 3 qutebrowser HARD-51 tasks) — engine eval (measured run)

- upstream/eval commit recorded by CI: `3c5b04356a6aea4c30332679374ed23fbd30ba5d`
- Resolve decisions come from each task's own verifier inside the official container image.
- `nop` must resolve 0/N and `oracle` must resolve N/N or the causal number is not interpretable.

| arm | resolved | tasks | resolve % | model calls | cost USD | wall s (total) | wall s (mean) | missing trials |
|---|---|---|---|---|---|---|---|---|
| causal | 0 | 3 | 0.0 | 0 | 0.0 | None | None | 3 |
| nop | 0 | 3 | 0.0 | 0 | 0.0 | None | None | 3 |
| oracle | 0 | 3 | 0.0 | 0 | 0.0 | None | None | 3 |

## Harness gates

- `oracle_gate_pass`: **FAIL**
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
| `instance_qutebrowser__qutebrowser-3e21c8214a998cb1058def` | None | no | NOT_RUN | None | 0 |
| `instance_qutebrowser__qutebrowser-c09e1439f145c66ee3af57` | None | no | NOT_RUN | None | 0 |
| `instance_qutebrowser__qutebrowser-deeb15d6f009b3ca0c3bd5` | None | no | NOT_RUN | None | 0 |

What the engine did across the causal arm (behaviour, not a score): `NOT_RUN`×3. Resolve rate is decided only by each task's own verifier.

