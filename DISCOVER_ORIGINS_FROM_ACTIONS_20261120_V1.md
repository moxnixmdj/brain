# Discover the origin by executing generic actions — 2026-11-20

Authority: `NONE__PRODUCER_RUN_SANDBOX`. No independent verification, capability/acceptance/
terminal credit, benchmark score, model call or stored parameter.

## What was removed

`one_origin_derives_the_judge_v1` computed the verifier from one observed origin, but the origins
were still made by four named damage sequences. This round starts from a clean clone and executes
a small vocabulary of generic mutations: edit a tracked file, create an untracked file, stage all,
stash, check out a branch, merge, check out main, remove a tracked file. No damage-class name or
task-specific file name enters discovery or judging. An origin is retained only when the machine's
own facts show a defect (stash, untracked, dirty tracked file, wrong branch, non-target content).
One verifier is derived per discovered origin; the existing real-successor enumerator judges rows;
the smallest closure is refit and tested on origins discovered independently in another repository.

## Measured result

Tool: `canonical/tools/discover_origins_from_actions_v1.py`; tests:
`canonical/tests/test_discover_origins_from_actions_v1.py`; receipt:
`canonical/verification/DISCOVER_ORIGINS_FROM_ACTIONS_20261120_V1.json`.

- Discovery used 320 real action executions in each repository and kept three origins: a stash with
  an untracked file, an untracked-file-only state, and a branch/content-mismatch state. The same
  three families were found independently in `pypa/packaging` and `pypa/pyproject-hooks`.
- The discovered rows selected the same unique closure as the supplied-origin experiments:
  `ref_preserve + tracking_preserve + stash_restore`.
- Training: 44 holes, 16 legitimate states; held: 44 holes, 16 legitimate states; **0 false accepts
  and 0 false rejects** on both. All criteria E1–E5 true. Full run 96.1 s; 4/4 new tests pass.

## What remains

The mutation vocabulary, law algebra, target commit and depth/cap bounds are supplied. This is a
bounded discovery result on git, not a GUI, browser, or open benchmark result and not general
computer use. There is still no way to choose the mutation vocabulary or the origin set from the
task itself; that is the next falsifiable bottleneck, and §6 is still unmet.
