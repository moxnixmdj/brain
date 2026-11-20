# Targeted refutation of a PROVISIONAL rule — measured, not assumed

Date: 2026-11-20. Branch: `arena/5856d496-brain`. Authority: **NONE** (producer-run
sandbox measurement). Machine receipt:
`canonical/verification/PROVISIONAL_REFUTATION_20261120_V1.json`.

## What was tested

The external instant-knowledge store held
`git_stash_pop -> PROVISIONAL__LEAST_DEMANDING_SURVIVOR` requiring only
`stash.present`. That was the least-demanding survivor from earlier source
evidence, not a proven precondition. The question: when the real program
disagrees in a repository never used to buy the rule, can the stored rule be
repaired from **one falsifying execution plus one already-recorded support
fact-set**, without buying a new condition on the target and without deleting
the action's capability?

Source: `pallets/click` at upstream `08b803cf32ceb2ae6a772c62d5da42757a897d44`
(constructed base HEAD `51a6913e64333d47fb91bcf5679a56c4287234e6`).
Target (fourth repository): `pallets/flask` at upstream
`49943b5a94413a530761350f04e896f76e8d620e` (constructed base HEAD
`abf16e6119ea29792da3e26defb4ce19eb46f259`). The constructed HEAD is not an
upstream commit: the harness adds real branches and commits to each clone.

Execution budget: **0** target learning executions, **1** targeted refutation
execution, **2** support-acquisition executions in the source. The oracle is
each program's own exit status; no answer label is written into the harness.

## Measured result

| quantity | before | after |
|---|---|---|
| stored requirement | `stash.present` | `stash.present`, `worktree.clean` |
| stored status | PROVISIONAL | PROVISIONAL |
| prediction on the falsifying state | `APPLIES` | `DOES_NOT_APPLY` |
| real oracle on that state | `DOES_NOT_APPLY` | `DOES_NOT_APPLY` |
| `git_stash_pop` accuracy on target states | 1.0 | 1.0 |
| `tar_extract` accuracy (unrepaired control) | 1.0 | 1.0 |
| false applies across both actions | 0 | 0 |

The counterexample is a real conflict: a stash that changes a tracked file is
set aside, the same file is then changed differently, and `git stash pop`
itself exits nonzero. The single distinguishing observable is `worktree.dirty`
in the falsifying state versus `worktree.clean` in the recorded support state.
The computed repair **adds one fact** to the existing rule; it does not replace
it. A dynamic shift of the same state, with no learning call between decisions,
changed the prediction from `APPLIES` to `DOES_NOT_APPLY` and the real oracle
agreed (`flipped_without_learning: true`).

Store digests: before `ee71dd15bfb5a0c45e73546e9b77195d993a6cc8740d0a476b7cc5803eea767f`,
with support `5c3a615b149fa6ec4b0d7ed904529d8f56da08bd56c6fbdbefbf9ba9b1bf4985`,
after `b295bf32965969dd90adad3b027ba2a8f2bd015b00b2ba6357e8e33105256f47`.
The store reloads with an identical digest after the write. Model calls `0`,
stored parameters `0`, spend `$0`.

## Two failed designs were measured and rejected

1. Writing an untracked file into the copied state did not make the program
   refuse: the prediction matched the outcome, repair correctly returned
   `UNCHANGED__PREDICTION_MATCHED_OUTCOME`. No refutation was manufactured.
2. The first repair used the learner's `most_general` survivor directly,
   replacing `stash.present` with `worktree.clean`. That blocked the
   counterexample but dropped accuracy to 0.75 and produced 4 false applies,
   because clean states with no stash now matched. The final repair preserves
   every previously required fact and adds one separating fact; a test now
   guards against the replacement error.

## Hard checks run here

- `canonical/tests/test_provisional_repair_v1.py` — 6 passed; includes fail-closed
  quarantine, minimality, preservation of existing requirements, and unchanged
  prediction.
- Store/probe suites (`test_instant_condition_store_v1.py`,
  `test_observable_probe_v1.py`) with the new tests — 14 passed.
- Declaration floor test plus new tests — 32 passed; floor report held at
  `595 == 595` declarations-without-a-check (the floor may fall, not rise).
- Unified model compiler and verifier regenerated and run: `33/33 PASS`,
  `AUTHORITY NONE — SANDBOX MEASUREMENT`.

## What this does NOT establish

This is one action, one rule, one counterexample, and one repository transfer.
It does not establish general single-experience learning, GUI or browser
competence, OSWorld/SWE/Terminal/benchmark credit, an independent evaluator,
sentience, or §6 completion. The sensor vocabulary and the repair mechanism
were built earlier; the store records their computed output, not learned
weights or a world fact inside parameters. The `PROVISIONAL` label is retained
deliberately: a single successful narrowing is not identification.
