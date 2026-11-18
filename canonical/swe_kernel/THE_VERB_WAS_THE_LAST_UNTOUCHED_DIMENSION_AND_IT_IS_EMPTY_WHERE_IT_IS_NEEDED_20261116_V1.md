# The verb was the last untouched dimension, and it is empty where it is needed

Rounds 16 to 19 changed the **seeds** four times — the tests' own literals, mutated literals, the values the
program's own comparisons want, and the repositories' own 5,949 documents — and the pinned count never moved off
2 of 8. Every one of those searches kept the same **verb**: build a value, call the function the test calls, read
what came back.

The verb was the last dimension nothing had varied, and the corpus pointed straight at it. `pypa/packaging`'s own
fix `46167dcd` carries a failing case named `test_copy_and_pickle_preserve_state[False--None-copy]`: what changed
is what `copy.copy` and `pickle` do to a `Version`, not what `Version(...)` returns. `checkability_by_differential_pin_v1`
had driven every public callable of the touched module through an alphabet of empty-ish arguments and converted
**0 of 13** drivable unguarded commits — with the wrong verb, no alphabet can help.

So this round held the seeds *exactly* as they were — the same 5–6 literal calls that produced 2 of 8 — and varied
only the operation applied to the value they produce:

```
pickle.loads(pickle.dumps(v))     copy.copy(v)      copy.deepcopy(v)      repr(v)      str(v)
copy.copy(v) == v                 pickle round-trip == v
state(v) == state(copy.copy(v))   state(v) == state(pickle round-trip)
```

Each `(seed, operation)` pair is executed at **both** states — the fixed file and the same file with the audited
part reverted — in one child process per state. A pin is an outcome that is stable at the fixed state, differs at
the reverted one, and whose assertion **fails on the reverted part** when executed. Anything else is not counted.

`state(v)` is the object's own `__dict__` plus every slot on its MRO, with identity masked. That was not a
refinement, it was a defect fix: `canon()` renders objects by `repr`, and
`<Version('1.0')> == <Version('1.0')>` while one of them has forgotten its prereleases override. Testing the
hypothesis with `repr` alone would have measured the blindness of the instrument, not the emptiness of the
dimension.

## Measured

Two populations, because a hypothesis must be tested where it applies:

| population | tasks | parts the suite accepts without | pins from operations | separating outcomes |
| --- | --- | --- | --- | --- |
| random sample (`--limit 24`) | 17 | 8 | **0** | 0 in 333 executions |
| fixes whose own failing case is **named after an operation** | 36 | 10 | **0** | 0 in 621 executions |

The literal-call baseline on the operation population is **0** as well, and on the random population 2 of 8. So
the operation dimension gains nothing over the seed search, on either population, and the kill criterion written
before the run — *"if it does not pin strictly more than 2 of 8, the dimension is dead"* — fired.

## Why the zero is structural, not an implementation miss

The residual parts are transparent in the receipt. On `packaging 46167dcd` — the copy/pickle fix — the parts that
survive the suite's own coverage are `__lazy_modules__ = {...}` and `SupportsIndex,`: import and typing hunks. The
hunk that changes copy/pickle semantics was **skipped before it was ever searched**, because the suite already
pins it. On that population, **27 of 36 fixes are fully pinned by their own suites.**

That is the result, and it is stronger than a failure:

> The operation dimension is **empty where it is needed and needed where it is empty**. A fix that changes what
> `copy`, `pickle` or `==` do ships the test that names it — so the part is not open. A part that *is* open is one
> whose operation nobody tested, and there the two states do not differ on any operation the test's own values can
> reach.

Every open part in both populations produced **zero** separating outcomes: not a wrong operation, not a missed
pin — no observable difference at all between the fixed file and the file with that part reverted, under ten
operations over every value the test itself constructs.

## What this closes

Five mechanisms have now been priced against the same residual work:

| round | dimension varied | new pins beyond the suite's own |
| --- | --- | --- |
| 16 | the tests themselves as probe | 0 of 8 |
| 17 | input **shape** (mutation) | 2 of 8 |
| 18 | the **value** a condition wants | 0 more |
| 19 | the **corpus** (5,949 real documents) | 0 more, one lost |
| 20 | the **verb** (the language's protocol) | 0 more |

Input, value, corpus, verb. Four dimensions, zero new pins beyond what the change's own test already provided.
What remains is not a fifth dimension of the same kind. The residual work has no discriminating input **inside the
artifact**, and that is now established from the operation side as well as from the checkability side: the tree's
own `CHECKABILITY_BY_DIFFERENTIAL_PIN` already ended at the same place — 0 of 13 — and the 2026 field states the
same law from its own measurements (in 64.8% of Python PRs not one changed line is executed by any test;
*All Smoke, No Alarm*, 80.2% of 86,156 agent-authored test patches carry weak or absent oracle signals).

## What is real and what is not

Real: a demonstration permanently yields what it **separates**, and its own test is the best separator there is —
that is why 27 of 36 fixes needed nothing from us. Real: the language's protocol is a free action space and it
works — the fire proof pins a real behaviour change through `copy.copy(x) == x` alone, with the tree restored and
the pin verified to fail on the reverted part. Real: the instrument's first version reported nothing because it
was blind to state, and that was found before the zero was published.

Not real: that a better verb, a bigger corpus, a smarter seed or a richer probe can manufacture a discriminating
input. Not real: that "experience it once" transfers a behaviour the demonstration does not distinguish. Not real:
that another dimension of the same kind is waiting — four have now been spent.

The single bottleneck stands, and it is the one the tree named before this round: **the discriminating input is
knowledge, it arrives with the change, and it cannot be derived from the artifact.** Everything that remains must
manufacture it from *stated intent* — the sentence the human wrote about what the change should do — because that
is the only source in the loop that contains what the artifact does not.
