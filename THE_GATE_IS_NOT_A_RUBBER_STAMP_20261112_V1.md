# The gate is not a rubber stamp — except where it is

**2026-11-12.** Base `310151c6`. Branch `arena/71ed47be-brain`. Round 4.

Last round's census ended on an uncomfortable number: **113 of 145 capabilities have a runtime
success predicate that reads a field the capability itself emits.** I wrote that it meant "the
runtime gate cannot, by itself, distinguish a correct answer from a confident one." That was an
inference, not a measurement, and it is the kind of inference this repository has been burned by
before. So this round tests it statically.

The question is narrow and decidable:

> Given the adapter's source, is there any way the declared `expect` predicate evaluates to false?

Authority **NONE**. Static analysis of source text. Nothing is executed, no capability is run, and
`truth.achieved` stays `false`. $0, zero model.

---

## 1. The result, which mostly clears the gate

`runtime_predicate_falsifiability_probe_20261112.py` parses each adapter and classifies the
declared predicate:

| class | count | meaning |
|---|---|---|
| `DYNAMIC` | **47** | the field is assigned a computed value; the predicate can differ from success |
| `ALWAYS_TRUE_GUARDED_RAISES` | **37** | the expected literal is assigned only under a condition, and the module raises |
| `NOT_STATICALLY_VISIBLE` | **53** | the field is set somewhere this probe cannot see; unknown, not defective |
| `ALWAYS_TRUE_UNGUARDED_RAISES` | **7** | success assigned unconditionally; failure signalled only by a raise elsewhere |
| `DECLARATION_MISMATCH` | **1** | the predicate reads a field the capability does not declare |
| `ALWAYS_TRUE_NO_RAISE` | **0** | success assigned unconditionally with no failure signal at all |

**Zero capabilities report success unconditionally with nothing able to signal failure.** I
expected to find a crowd of them; there are none. The implied "rubber stamp" reading of the 113
was wrong, and the correction is the point of this round.

Most of the surface is stronger than the last note implied: 47 compute the success value, and 37
only assign it inside a condition, so the predicate carries real information. The 41% from Round 3
survives, and it survives because the adapters do their own checking, not because a receipt says so.

## 2. Where it is a rubber stamp, and it is exactly where it hurts

Seven capabilities assign the expected literal **unconditionally**; the only thing that can report
failure is an exception raised somewhere in the module.

```
python.fault.localize.dynamic.dataflow.v1
python.fault.provenance.interprocedural.value.v1
python.patch.search.test_guided.ast.v1
python.software.repair.guided.provenance.coupled.v1
python.software.repair.loop.coupled.ast.v1
python.software.repair.loop.strict_progress.ast.v1
python.software.repair.loop.test_guided.ast.v1
```

**All seven are the software repair and fault-localisation family** — the part of the surface the
owner cares about most, and the same family that produced the 5/5 false success that only became
5/5 honest after a hand-written admission rule was added. The pattern is not a coincidence: these
adapters return `output_verified: True` on the path that returns at all, so *whether a patch is
kept is decided by whether an exception escaped, not by the predicate.*

That is a real defect and it is small enough to fix in an afternoon: guard the assignment on the
check that already exists in each adapter, and the predicate starts carrying information.

One more, of a different shape:

```
task.acceptance.objective.lossless.v1   — the predicate reads `output_verified`,
                                          which is not among the capability's declared
                                          result_fields
```

The template and the tool's contract disagree. This is the fifth instance in this tree of *one
module naming an input shape differently from the one reading it*, and the first one found
mechanically rather than by hand.

## 3. What I cannot see, stated as the next work item

**Fifty-three capabilities** set the field somewhere the AST walk does not reach: a helper, a
framework, a callee, a decorator. They are not cleared and they are not condemned. This probe says
`NOT_STATICALLY_VISIBLE`, which is the honest answer and also the largest remaining hole in the
audit.

The next instrument is not more static analysis. For those 53 the question is empirical — *drive
the capability to a known failure and see whether the predicate says no* — and that requires a
sandboxed negative-control harness, which this repository already has (`NEGATIVE_CONTROLS: 5/5
PASS` in the unified model verifier). Pointing it at the registry is the work.

## 4. Why this matters for "learn once, permanently"

A learner's safety is the product of its acceptance test. Round 2 measured that one demonstration
leaves 14 of 47 programs standing. Round 3 counted 60 capabilities structurally able to learn from
one try. This round says: for 84 of them the runtime predicate can express failure, for 8 it
cannot or does not, and for 53 nobody has looked.

The order in which to fix them is now forced:

1. **7 unguarded assignments** — guard them on the check each adapter already performs.
2. **1 declaration mismatch** — make the template read a field the tool produces, or produce it.
3. **53 invisible** — negative controls, one known-failure probe each.
4. **Only then** point a learner at the surface. A lesson admitted through a gate that cannot say
   no is not a lesson; it is a habit.

## 5. Receipts

```
python3 runtime_predicate_falsifiability_probe_20261112.py --list-defects
canonical/tests/test_runtime_predicate_falsifiability_v1.py     9 tests, all passing
```

The tests exercise the classifier on synthetic source rather than only on the registry, because a
classifier that is only ever run on data it was written against has not been tested. They pin:
unguarded vs guarded detection; that a computed value is `DYNAMIC`; that an undeclared predicate
field is a mismatch; that `raise` inside a docstring does not count as a failure signal; and that
the run partitions the registry (145) with `ALWAYS_TRUE_NO_RAISE == 0` and the weaker class
non-empty.

## 6. Non-claims

"This module contains a raise" is not "this adapter raises on failure." The 37
`ALWAYS_TRUE_GUARDED_RAISES` rows are stronger evidence than the 7, not proof; the exception path
was not traced to the assignment. Nothing here executes an adapter, replays a receipt, or re-runs
an independent check. The classification is a property of source text at this commit. No capability
registered, no family flipped, no terminal or sentience credit. $0, zero model dependency.
