# One solve, at the design point

Date: 2026-11-24 · V41 · branch `arena/1ac14ac1-brain`

## What I set out to do

The previous round ended with a named lever: `candidates_screened 0` on a task
whose failure is a single `AttributeError`, in a file the engine was explicitly
told to look at. This round went after exactly that.

## The defect, isolated

On a mined fail-to-pass task (pypa/packaging, parent `dec6213e`, added test
`test_invalid_marker_defers_argument_formatting`):

| step | measured |
|---|---|
| localisation | **correct** — lands on `markers.py:89`, site `__init__:IFEXP_BODY@89:28`, `orig_code` `str(self)` |
| witnesses | 5 |
| `synthesize_candidates_for_witness` | **0 candidates for all 5** |
| repair status | `UNSOLVED`, `candidates_screened 0`, 691 ms |

So localisation is not the wall here, and the engine never proposes an edit. It
cannot be said to have tried and failed.

## Why the obvious repairs all fail

Holding everything fixed except the located expression, and running the real test:

```
AS_IS (control)                      fail
str(self) -> super().__str__()       fail
str(self) -> repr(self)              fail
hoist the value above the line       fail
```

The test constructs `InvalidMarker(message)`, **then** sets `message.text`, **then**
reads `err.message`. Any evaluation performed during construction is wrong by
construction. No substitution of the eager expression can be right — not because
the search is unlucky, but because the requirement is deferral.

The fix is a **definition-level** edit. Two spellings both work:

```
deferred @property (with setter + stored-value lookup)   PASS, module green
functools.cached_property                                PASS, module green
```

## The one genuine solve

The form flips the target test **and** leaves the whole module green (2493 tests).
That is a real fail-to-pass solve with the oracle untouched, which ten previous
rounds did not produce.

## The calibration, and why it overrules the celebration

V38's failure mode was adding a sixth form to rescue a calibration it had already
failed. So the rule was written down **before** measuring: *a form is only worth
having if it fires on tasks that are not the one that suggested it.*

| | |
|---|---|
| eligible tasks | 27 (23 pypa/packaging + 5 hukkin/tomli − 1 not fail-to-pass) |
| solved | **1** |
| solved task | `dec6213e` — the task that suggested the form |
| transfer | **none observed** |

On the other 26 the detector does not fire at all: their tracebacks do not show a
re-entrant self failure, so no candidate is emitted.

**One solve at the design point is a fit, not a capability.** The vocabulary is
still keyed to a failure shape a human noticed. This round walked into the exact
trap V38 named, which is why the calibration was fixed in advance — the number
was going to be 1/27 either way, and writing it down first is what stops it being
reported as progress.

## A contamination I must disclose

The form is described above as derived from the traceback alone. That is true of
the *code path* — `emit_for_traceback` receives only the traceback and the source
file, and never reads the fix commit. But it is **not** true of my own knowledge:
in the previous round, while checking that round's report for leakage, I printed
the upstream fix diff for this very task. It showed `functools.cached_property`
and `super().__str__()`.

So the design point was not blind to me. This makes the 1-of-27 result *more*
damning rather than less: a form built with prior knowledge of the answer still
generalises to nothing. Any future version of this form should be derived by
someone who has not seen the fix, and the honest place to record that is here
rather than in a claim of clean-room provenance.

## Six bugs in my own instruments, all caught by measuring

Each of these would have produced a plausible, wrong number:

1. The detector read the class name from the `AttributeError` — but that class is
   defined **inside the test**, not in the source file. The deferral target is the
   `__init__` frame's file and line.
2. The emitter matched `ast.Assign` and missed `AnnAssign` (`self.x: str = ...`),
   the spelling actually used, so it emitted nothing.
3. An inline property **ended `__init__` early**, absorbing the statements below it
   — measured: `source` missing, 2 tests failed while the target passed.
4. `@cached_property` emitted unqualified raised `NameError` at class creation (rc=4).
5. A plain `@property` conflicted with the conditional assignment until a setter and
   stored-value lookup were added.
6. The detector accepted only one pytest traceback spelling. The harness ran
   `--tb=short`, and the form scored **0 on all 23 tasks** until both spellings were
   accepted.

Bug 6 is the instructive one: it would have reported "the form fires on nothing"
when the form actually solves its design task. A harness that cannot reproduce a
known positive is a broken instrument, not a finding.

## What this round establishes

**Verified:** a definition-level DEFER form solves 1 of 27 mined fail-to-pass tasks,
the one it was derived from, with the full test module green and the oracle
untouched. The engine's zero-candidate emission is now explained mechanically:
its operators replace expressions that already exist, and this repair requires
changing what kind of thing the attribute is.

**Not established, not claimed:**
- No capability gain. `capability_credit_delta` 0.
- **1 of 27 is a fit.** No transfer was demonstrated.
- No benchmark row. **§6 DONE is not met.**
- The form is a separate tool. It is **not** wired into the engine's repair path,
  and the engine still emits 0 candidates there.

## The next lever, stated plainly

The form only fires when a human-noticed traceback shape is present. The
generalisation that would matter is detecting *"this value is computed too early"*
from the failure **without** requiring re-entrancy to be visible — for instance
from the observable fact that mutating an argument after construction changes the
expected result. That is a property of the test, not of the bug class, and it is
falsifiable: it should fire on tasks where the DEFER class is the right repair and
on no others. Until it does, the honest count stays at 1 of 27.
