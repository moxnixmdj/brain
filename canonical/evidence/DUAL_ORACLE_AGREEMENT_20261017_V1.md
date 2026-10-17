# Dual-oracle agreement — 2026-10-17

The repo's own law: *a capability counts only if it passes 500 unseen instances
at 100%, judged by **two independent oracles**, zero model dependency.*

Until now one oracle existed (`crosshair_contract_oracle`, SMT/Z3). This closes
the second-oracle gap.

## Oracle 2: concrete execution

`canonical/runtime/bound_capabilities/concrete_execution_oracle.py`

Different lineage on purpose. The SMT oracle asks *"does a satisfying
assignment exist?"* — symbolic, solver-backed. This one asks *"does it break
when I run it?"* — it calls the function on enumerated concrete integers
(sample of 13 covering negatives, zero, small, large) and evaluates the
postcondition directly.

Shares no machinery, no solver, no assumptions with oracle 1.
`model_dependency_count: 0`. It evaluates Python and arithmetic.

## Results

Positive direction — 500 unseen instances:

```
instances 500   distinct sources 500   elapsed 148.2s
SMT  (symbolic)  found violations: 500/500
CONC (concrete)  found violations: 500/500
disagreements: 0
```

Negative control — 15 correct programs (each family's unmutated `correct`
expression, 3 values of k):

```
control programs: 15   SMT false positives: 0   CONC false positives: 0
```

## Why the negative control is the real evidence

Agreement on positives alone is nearly worthless: two oracles that always
answer "violation" would agree perfectly. The control pins the other
direction — both oracles stay silent on every correct program.

Both directions together: 515 judgements, 0 disagreements, 0 false positives,
0 model dependency.

## Honesty clause baked into the code

A concrete oracle can only **witness** a violation, never prove its absence.
The module states this in its own output: `proves_absence: false`. A clean
concrete run means *"no counterexample in this sample"*, not *"proven"*.
The SMT oracle remains the one that can assert absence.

## Protected by

`canonical/tests/test_dual_oracle_agreement_v1.py` — 3 tests pinning sample
agreement, the negative control, and model-freedom. 10 passed (with the
mutation-generator suite) in 7.97s.
