# SWE-bench Pro V2 (smoke: 3 qutebrowser HARD-51 tasks) — engine eval (measured run)

- upstream/eval commit recorded by CI: `080753b7197460d6de72aadfc2c4af63d121a0bc`
- Resolve decisions come from each task's own verifier inside the official container image.
- `nop` must resolve 0/N and `oracle` must resolve N/N or the causal number is not interpretable.

| arm | resolved | tasks | resolve % | model calls | cost USD | trial wall s (total) | engine s (total) | missing trials |
|---|---|---|---|---|---|---|---|---|
| causal | 0 | 3 | 0.0 | 0 | 0.0 | 160.85 | 15.521 | 0 |
| nop | 0 | 3 | 0.0 | 0 | 0.0 | 145.62 | None | 0 |
| oracle | 3 | 3 | 100.0 | 0 | 0.0 | 146.44 | None | 0 |

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

| task | reward | resolved | agent status | engine status | engine pass | files | harness error |
|---|---|---|---|---|---|---|---|
| `instance_qutebrowser__qutebrowser-3e21c8214a998cb1058def` | 0.0 | no | EDITS_UPLOADED | PASS | True | 1 |  |
| `instance_qutebrowser__qutebrowser-c09e1439f145c66ee3af57` | 0.0 | no | NO_EDITS | FAIL_CLOSED | False | 0 |  |
| `instance_qutebrowser__qutebrowser-deeb15d6f009b3ca0c3bd5` | 0.0 | no | HARNESS_ERROR | None | None | 0 | URLError: <urlopen error [Errno 111] Connection  |

**1 of 3 causal trials are not attributable to the engine** (harness error, blocked upload, or no trial read). The measured rate stays 0/3 as a benchmark number — a run counts what actually ran, failures included — but the engine-attributable denominator is 2, and that is the number to quote about the engine.

What the engine did across the causal arm (behaviour, not a score): `EDITS_UPLOADED`×1, `HARNESS_ERROR`×1, `NO_EDITS`×1. Resolve rate is decided only by each task's own verifier.

