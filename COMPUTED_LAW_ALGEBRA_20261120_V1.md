# Compute the law algebra — 2026-11-20

Authority: `NONE__PRODUCER_RUN_SANDBOX`. No independent verification, capability/acceptance/
terminal credit, benchmark score, model call or stored parameter.

## What this removes

All prior closure experiments supplied five law names (`ref_preserve`, `target_content_preserve`,
`tracking_preserve`, `stash_restore`, `reference_ancestor`). The judgments were real, but the set of
statements the selector could form was written by the experimenter. This round computes that set
from the key/value structure of the readings:

- `preserve(prefix)`, `no_new(prefix)`, `clear(prefix)`;
- `restore(from_prefix, to_prefix)` induced from suffix pairs that actually occurred;
- exception rules induced from the keys that actually broke a preservation rule;
- structural flags only (no path names, digest values or file names).

The selector receives no named law, no task string, no commit digest, no file name and no judge
answer. It keeps the smallest conjunction that accepts every legitimate row and refuses every
hole, deduplicating laws by their truth vector. The old named closure is evaluated only afterwards,
as a baseline, never as an input.

## First design killed

The first candidate set had only constant-preserving/restore templates and flag rules. It produced
six nonconstant truth vectors on real repositories and **no closure** (`NO_CLOSURE_IN_COMPUTED_ALGEBRA`,
`met=false`). The failed console result was not preserved as a receipt; this paragraph records it
rather than replacing it with a success. The cause was measurable: a real repair may move the ref
for the branch it is standing on, which a bare `preserve(ref)` cannot express. The second design
induces the exception from the observed broken key and the `head.branch` fact, and adds the missing
`no_new` family. No hand-written exception for this case was inserted.

## Measured result

Tool: `canonical/tools/computed_law_algebra_v1.py`; tests:
`canonical/tests/test_computed_law_algebra_v1.py`; receipt:
`canonical/verification/COMPUTED_LAW_ALGEBRA_20261120_V1.json`; external store:
`canonical/state/COMPUTED_LAW_STORE_20261120_V1.json`.

- 179 training rows and 180 held rows from `pypa/packaging` and `pypa/pyproject-hooks`.
- Eight nonconstant computed truth vectors. The unique minimum closure of size 3 is:
  `restore(stash_content -> content)`, `no_new(content)`, and
  `preserve_except_value(ref; key=head.branch; scope=after)`.
- Training: 160 holes, 19 legitimate; held: 161 holes, 19 legitimate; **0 false accepts and
  0 false rejects** on both.
- The old named three-law closure also had 0/0 on both sets, so the computed closure did not buy
  accuracy by weakening the verifier. It removed a supplied vocabulary without adding an error.
- F1–F5 true; 4/4 new tests pass; full run 252.1 s; 0 model calls; 0 parameters.

## What remains

The template grammar (preserve/no_new/clear/restore/flag), the damage classes, the target commits and
the search bounds are still supplied. This is a git-only producer-run result, not a GUI/browser/
open benchmark result, not independent verification and not general computer use. The next
bottleneck is to compute the template grammar itself from a new machine's reader, then repeat the
selection on an environment whose relations were not in this grammar. §6 is not met.
