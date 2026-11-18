# The missing assertion is about inputs the tests never use

Round 16. Branch `arena/35586c4a-brain`, from `b655fe40`.

## What round 15 promised, and what happened when it was attempted

Round 15 measured that a real suite certifies **71.4%** of the behavioural parts of real fixes, and it named
the next move: *synthesise the assertion that would pin each unpinned part* — the only move that raises the
number instead of describing it.

Before writing anything I searched the tree, and it already owns both halves under non-obvious names:

* `checkability_by_differential_pin_v1` — canonical outcome signatures of a module's calls, determinism measured;
* `test_oracle_strength_measure_20261113_v1` — surviving mutants turned into concrete next assertions.

Neither reaches a real fix, because **both invent their inputs** from the artifact's own literals. A literal
harvested from a module is almost never the input that reaches a specific error path. So this round reuses
their comparison machinery and changes exactly one thing: the inputs are taken from **the human's own test
file** — the arguments it literally passes — and the mutant is **one part of the human's own change**.

## What came back

16 real fixes audited, 8 parts the suite accepts without, on the 5 tasks whose test files yield literal calls:

| | |
|---|---|
| unpinned behavioural parts audited | **8** |
| pinned by a synthesised assertion | **0** |
| differences observed at all between fix and mutant on the tests' own inputs | **0** |

And the zero is not an accident, it is a consequence:

> A suite that **passes** cannot differ on the outcomes it asserts. If it asserts only the exception *type*
> while the *message* moves, the difference is visible — but only for inputs the suite actually uses. The
> unpinned parts of a real change are precisely the ones no input reaches and no assertion covers.

So the missing observation cannot be recovered from the tests, because **the tests are exactly the set of
observations that were already made**. Asking them for a new one is asking a photograph for the room behind it.

## The instrument is proven able to fire

Three bugs in my own instrument were caught before the zero was believed, and each is worth naming because a
zero from an unproven instrument is the self-congratulation you told me to kill:

1. The tree's own `public_callables` **skips any function with keyword-only arguments**, and tomli's
   `loads(s, *, parse_float=...)` is exactly that — so *zero* calls were collected and every part trivially
   showed "no difference". The call surface must come from the **test's** imports, not the artifact's.
2. Builtin exceptions were emitted as `_m.ValueError`, which no module has; the generated test errored on
   import and every verification was "not green". Exceptions now resolve module-first, then builtins.
3. A pytest plugin that installed the profile hook captured **only import-time frames** (27 records, no
   `loads`) — three variants of it failed before the channel was replaced by a plain subprocess probe.

With those fixed, the fire proof holds: a fixture whose suite asserts only the exception type, and whose fix
moves only the message, yields a synthesised

```python
with pytest.raises(_exc('ValueError'), match=re.escape('bad statement (at line 1)')):
    _m.load('abc')
```

that is **green on the fix and red on the reverted part** (`test_the_instrument_pins_a_message_the_suite_never_asserted`).
The instrument can do the job. On real fixes it has nothing to work with.

## What this actually tells us — and it changes the next move

A test suite is not a set of assertions. It is a set of **inputs that reach code**, plus assertions about what
those inputs produced. Certified share is therefore bounded by **input generation**, not by assertion
generation:

> To pin a part you must first produce an input that **reaches** it. Only then is there an outcome to assert.

That reframes the roadmap and kills my own last-round plan. The next organ is not an assertion synthesiser.
It is **path-reaching input generation**: given a changed site, construct a value that satisfies the branch
conditions leading to it, then assert the outcome there. Zero model, no network, and it composes with
everything already measured:

| question | measured | round |
|---|---|---|
| can a candidate fix be built at all? | **1 of 17** | 11–14 |
| does the verifier prefer the right one? | **0 of 4** | 13 |
| is the accepted change observed? | **0.714** | 15 |
| can the missing observation be recovered from the tests? | **0 of 8** | 16 |

Read down that column and the field's economics stop being surprising: *"RLVR works only where a grader
exists"* — and a grader that observes a change must contain an input that reaches it. Suites are expensive
because reaching inputs are expensive, not because assertions are.

## What would be dishonest to claim

* That assertion synthesis is useless. It is proven to work wherever a reaching input exists — which is
  exactly the set of places the suite already covered.
* That 0 of 8 means the parts are unobservable. They are unobserved *by these tests*; a generated input that
  reaches them would make them observable, and that generation is the missing capability, not a conclusion.
* That this round added capability. It removed a plan that would have wasted the next two rounds, and it
  located the real term. That is worth less than a capability and more than a hope.

## Reproduce

```
.venv/bin/python -m pytest canonical/tests/test_pins_from_the_reverted_part_v1.py -q
.venv/bin/python canonical/swe_kernel/pins_from_the_reverted_part_v1.py --limit 9 \
    --json canonical/verification/PINS_FROM_THE_REVERTED_PART_20261116_V1.json
.venv/bin/python canonical/swe_kernel/pins_from_the_reverted_part_v1.py --limit 24 \
    --json canonical/verification/PINS_FROM_THE_REVERTED_PART_WIDER_20261116_V1.json
```

Model calls 0. Network calls 0. Spend $0. Authority: sandbox measurement, not independent verification.
