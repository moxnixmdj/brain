# A sensor request is computable — 2026-11-20

Authority: `NONE__PRODUCER_RUN_SANDBOX`. No independent verification, no benchmark score, no
capability/acceptance/terminal credit, no runtime model call, no stored parameter.

## The single bottleneck

The previous round closed a relation that the old grammar could not name (file mode). The project's
own older boundary is sharper: with `mkdir newdir`, the effect is real on disk while every view in
the content-only reader is empty. That is **a missing sensor, not a missing word**; no predicate
built from the same readings can reach it. The project stopped at naming the missing dimension.

The next bottleneck is therefore not another learner or larger action table. It is whether the
refusal can **compute the interface request** and then verify, after widening, that the new field
actually closes the hole — without turning the request into a hand-written fact.

## Plan killed before claiming success

Rejected: hand-writing `is_dir` (supplies the answer); a model looking at the tree (forbidden runtime
dependency); more repetitions of `mkdir` (the old law says repetition cannot create a sensor);
counting the effect with `exit 0` alone (a no-op also exits 0); treating "a new path appeared" as the
law (measured below to accept file creation and symlinks).

The design kept is deliberately small: a sensor bank of every `st_*` field the OS reports, discovered
from `os.stat_result` at run time; one positive execution; one repeat used only to discard unstable
fields; real control actions used only to price false fires; one field/value relation transferred to
a different tree.

## Two defects found, not hidden

1. The first implementation observed the copied directory **after** running the action for both the
   "before" and "after" readings. It reported `H1=true`, `H2=true` but `sensor_request=null`,
   `met=false` — the machine correctly refused to invent a field from an empty delta. Fixed by
   reading the copy before execution.
2. The naive shortcut "a new path appeared" fires on `touch`, `write_file` and `symlink` in the held
   tree (3 false accepts). It is kept as an ablation, not removed as an embarrassing result.

## Measured result

Tool: `canonical/tools/a_sensor_request_is_computable_v1.py`; tests:
`canonical/tests/test_a_sensor_request_is_computable_v1.py`; receipt:
`canonical/verification/A_SENSOR_REQUEST_IS_COMPUTABLE_20261120_V1.json`; deletable store:
`canonical/state/SENSOR_REQUEST_STORE_20261120_V1.json`.

- 16 `st_*` fields discovered from the OS at run time. 7 time/inode fields were discarded as
  unstable across the stability repeat.
- Three fields tie with zero false fires on the controls: `st_mode`, `st_nlink`, `st_size`. The
  selection rule breaks the tie alphabetically and **prints the tie**; no uniqueness is claimed.
- Selected request: `st_mode`; learned relation: a newly appearing path whose `st_mode` equals the
  value observed in the one positive execution (16877 here). No path name, action name, target
  name, goal word or hand-written kind predicate enters the request or the law.
- Training tree: 8 real action rows; held tree with different names, count and modes: 8 real rows.
  Selected relation: 0 false accepts and 0 false rejects on both. The old reader sees no change on
  `mkdir` or `mkdir_p` on either tree; the directory's existence is checked on disk.
- H1–H6 true. Full run 0.1 s. 2/2 new tests pass. 0 model calls, 0 parameters.

## What this changes, and what it does not

The older law survives: the field was not grown from the old readings, it was requested from an
interface the old readings could not see. What is new is that the *request itself* is computed,
priced against real controls, and verified after widening. If no stable field separated the effect,
the tool would return `NO_REQUEST` rather than invent one.

This is a real filesystem with a supplied action bank and depth-one mutations. It does not solve
symlink/ownership/ACL semantics, GUI affordances, browsers, long-horizon tasks or any open
benchmark. The raw mode value is an observation in an external deletable store, not a weight or a
memorized world fact. No §6 completion is claimed.

## Next bottleneck

The request currently exists only inside this experiment's reader. The next step is to make an
existing consumer accept a computed sensor request and re-run its own admission check, so a request
that merely looks narrow cannot be used without an execution verdict. Until then, this is a
mechanism measured in isolation, not an integrated computer-use capability.
