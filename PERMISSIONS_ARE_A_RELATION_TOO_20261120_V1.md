# Permissions are a relation too — 2026-11-20

Authority: `NONE__PRODUCER_RUN_SANDBOX`. No independent verification, benchmark score, capability/
acceptance/terminal credit, runtime model call or stored parameter.

## The bottleneck

`THE_VOCABULARY_IS_THE_ARTIFACT_20261125_V1.md` states its own limit: a machine whose only
difference is permissions or ownership would defeat its five relations. That is not a missing
action or judge; it is a missing statement the selector can form. This round tests whether the
computed key/value law algebra, which received no law name in the git round, can state a previously
invisible relation on a completely different real machine: a directory whose reader reports bytes
and octal modes.

## What was built

Only the machine is new; the selector is reused from `computed_law_algebra_v1.py`.

- Reader: `target.*` bytes, `targetmode.*`, worktree `content.*`, worktree `mode.*`, `extra.*` paths.
- Derived judge: every target path has target bytes and target mode, and no extra path exists.
- Discovery: generic real mutations (break bytes, break mode, add extra path) from a clean tree.
- Selection: computed preserve/no_new/restore/flag templates and induced exceptions, smallest
  separator on a training tree, no file name, law name, mode rule or task string as input.
- Transfer: independently discovered origins in a different tree with different file names,
  counts and modes.

## Three designs killed before the result

1. Two action lambdas returned the integer from `write_bytes` instead of `True`, so only mode damage
   was discovered and the run had no closure. Fixed by making all actions return a boolean.
2. Even after discovery worked, the origin reading omitted the target facts, so `restore(target ->
   content)` and `restore(targetmode -> mode)` were never generated; only `preserve(mode)`,
   `preserve(content)` and `preserve(extra)` appeared and no closure existed. Fixed by merging the
   target facts into every reading, as the git reader already did.
3. The first criterion build used wrong report keys and crashed before writing a receipt. Fixed;
   the failing runs are not relabelled as successes.

## Measured result

Tool: `canonical/tools/permissions_are_a_relation_too_v1.py`; tests:
`canonical/tests/test_permissions_are_a_relation_too_v1.py`; receipt:
`canonical/verification/PERMISSIONS_ARE_A_RELATION_TOO_20261120_V1.json`; external store:
`canonical/state/PERMISSIONS_LAW_STORE_20261120_V1.json`.

- Discovery: 56 real mutations on the training tree, 90 on the held tree; both found content,
  mode and extra-path defect families independently.
- Training: 642 rows, 604 holes, 38 legitimate; held: 704 rows, 660 holes, 44 legitimate.
- Unique minimum closure of size 2: `restore(target -> content)` and
  `restore(targetmode -> mode)`. 7 nonconstant computed vectors.
- Both sets: **0 false accepts, 0 false rejects**. The closure contains the mode relation and no
  file name. G1–G5 true. Full run 1.3 s; 2/2 new tests pass; 0 model calls, 0 parameters.

## What remains

This is a real filesystem but a bounded experiment. The action vocabulary, target trees and depth
bounds are supplied; ownership, pixels, widget trees and long-horizon interference are still
untested. This is not a GUI/browser/open benchmark result, not independent verification, and not
§6 completion. Next bottleneck: run the same computation on an environment whose reader exposes a
field no template family currently covers, and let the failed selection specify the new generic
template rather than hand-writing it.
