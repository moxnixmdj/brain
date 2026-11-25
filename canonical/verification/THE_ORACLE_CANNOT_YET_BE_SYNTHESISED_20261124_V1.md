# Wall 1, measured: an oracle cannot yet be synthesised from a green suite

**Measured 2026-11-24.** Receipt: `THE_WALL1_RECEIPT_20261124_V1.json`.
Tool: `canonical/tools/the_oracle_can_be_synthesised_from_a_green_suite_v1.py`.

## Why this is the wall that matters

Every engine in this repository refuses a row whose suite passes at the parent
(`NO_FAILING_TEST`). All **19** of the union's solves are conditioned on that gift.
Real benchmarks do not give it: SWE-bench Pro hands you an issue and a suite that is
already green. So the 19/45 number is a score on a task easier than the one §6 names.

The plan calls this Wall 1 and proposes "metamorphic witness splitters" — turn a green
suite into a failing oracle by checking relations that must hold for correct code. That
is the right idea, and it had never been measured here. So it was measured.

## The mechanism tested, and its integrity rules

At the parent commit, run the project's **own already-passing tests** under a tracer that
watches every function defined in the source file under repair, and check a metamorphic
relation that needs no knowledge of what the function means:

- **MUTATION_ISOLATION** — a function must not mutate an argument it was not asked to
  mutate. Checked by snapshotting arguments on call and comparing on return.

A violation found this way is a synthesised failing assertion **at the parent, produced
without ever opening the fix**. The claim is falsifiable, so it was scored that way: the
same probe then runs at the fix commit, and only a violation present at the parent and
**absent** at the fix counts as a discriminating oracle.

Integrity: oracle synthesis reads only the parent; the fix is opened afterwards, solely to
score discrimination; the parent's own test file is used (never the fix commit's new test);
a row counts only if the parent suite is genuinely green.

## Result: 0 of 19

| stage | rows | meaning |
|---|---|---|
| `SYNTHESIS_FOUND_NOTHING` | 10 | the relation never fires on the parent's own tests |
| `VIOLATION_DOES_NOT_DISCRIMINATE` | 9 | violations exist, and the **same** violations exist at the fix |

The second row is the interesting one. Several rows produce hundreds of
"mutations" (click `d340b0c1`: 400; attrs `a572c3a4`: 213) and the fix commit produces the
same ones. The relation is firing on ordinary intentional mutation — caches, memoisation,
in-place sorters — not on defects. **A relation that fires on almost every row is not
reading a relation**, which is a failure mode this build has documented before and hit
again here.

## Two bugs the measurement exposed in my own instrument

Both are the same class this build keeps relearning, and both are now fixed and recorded
in the tool:

1. **An observer that spends what it observes is not observing.** The first version
   deep-copied arguments. Deep-copying a lazy iterator *consumes* it, so 19 more-itertools
   tests failed only under instrumentation, and a 0.52 s suite took 93 s. Only
   str/bytes/int/float/bool/None/frozenset/list/dict/tuple/set are now snapshotted;
   anything consumable is refused.
2. **A tracer holds extra references**, so reference-counting tests fail only under
   instrumentation. Verified by hand: `IsliceExtendedTests::test_elements_lifecycle`
   passes un-instrumented, fails under the plugin, and its own source comment says
   "CPython does reference counting". Two rows died on this and were initially reported as
   "not a green suite", which was false. Such tests are now excluded **by name** and the
   count is recorded per row rather than silently swallowed.

Neither bug changed the verdict — the null survives both — but the first would have been
reported as an engine result, which is precisely the dishonesty this build has spent three
sessions eliminating.

## Why the specific row that motivated the experiment still fails

The test that caught `62411c16` (`spy` returning `head` and `chain(head, it)`, so a caller
that mutates `head` corrupts the chain) asserts:

```python
head, new_iterable = mi.spy(original_iterable, 3)
head[0] = 'A'
assert head == ['A', 'b', 'c']
assert list(new_iterable) == ['a', 'b', 'c', 'd', 'e', 'f', 'g']
```

The parent's existing suite **never mutates `head`**. So no relation over the existing
green tests can observe the defect: this bug is visible only to an assertion that was
never written. That is not an instrument failure, it is what the bug is — which is why the
"aliasing" framing I used in the plan is wrong for this row, and why the honest verdict is
that mutation-isolation is not sufficient here.

## Where this leaves the plan's Idea 1

The plan's suggested metamorphic set is idempotence, round-trip, aliasing and boundary
homomorphism, with a kill gate of ≥35% of commits. Measured, on the only rows available
with a genuinely green parent suite:

- **aliasing / mutation isolation: 0/19.**
- the other three relations were not implemented here, so they remain **unmeasured** — not
  falsified, and not to be counted as progress either.

So Idea 1 is **unproven with one of its four relations measured at zero**. Claiming the
metamorphic route solves Wall 1 would repeat the fabrication already caught in the
transfer receipt.
