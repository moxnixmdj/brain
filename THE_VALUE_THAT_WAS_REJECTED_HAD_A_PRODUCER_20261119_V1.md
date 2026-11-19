# The value that was rejected had a producer — and the producer is not the answer

**Round 25. Receipt: `canonical/verification/THE_VALUE_THAT_WAS_REJECTED_HAD_A_PRODUCER_20261119_V1.json`. Tool: `canonical/tools/the_value_that_was_rejected_had_a_producer_v1.py`. 13 tests. 82 real refused suites executed under a tracer. Zero model calls, zero parameters.**

## What this round tested

Round 24 left exactly one unmeasured route: the observation that identifies an edit is **the provenance of the rejected value** — not the assertion ("wrong"), not the traceback (only exists if something raised), but the expression instance that produced the value and the operands it used. So: trace the failing run, find the producer, and ask whether the shipped fix changed the function that produced it. Only the file under repair is traced, so the tracer answers one question and costs almost nothing.

## The numbers

| | |
|---|---|
| refused states executed under the tracer | **82 / 87** (3 could not run; every failure recorded) |
| median returns traced per failure | 23 |
| **producer of the rejected value found** | **1 / 82 = 1.2%** |
| …and it is a function the real fix changed | **0** |
| failures the traceback cannot localise ("unframed") | **69 / 82 = 84%** |
| of those, localised by value provenance | **0** |
| **of those, a function the fix changed was on the executed path** | **45 / 69 = 65.2%** |

## The verdict on this round's own hypothesis

**Value provenance, as implemented, is dead.** Two reasons, both measured:

1. **Most refusals reject no value.** `assert False`, `assert True`, and exceptions carry no operand. Reading only the checker's own text, 81 of 82 failures have nothing to trace back.
2. **When a value is rejected, its producer is usually not in the file under repair.** The test calls a public entry point; the value is built behind it, in another module. The tracer was deliberately restricted to the file being repaired — that restriction is what makes it cheap, and it is also why it comes back empty.

So the third wall is the same wall as the first two: **the machine's output does not contain the observation.** Not the words (round 23: 32%), not the words plus the check (round 24: 2.7% ceiling), and not the value's producer (this round: 0 of 69).

## The result that survives, and it is worth more than the one that died

**65% of the failures the traceback cannot localise executed a function the real fix changed.** Not a value, not a word, not a line — a *set of functions that were on the path*. That is an observation the machine produces for free, it exists for two thirds of the corpus, and every earlier round ignored it by asking for a line.

The consequence is arithmetic, and it is the most concrete thing this line of work has produced:

- Round 22 priced a search over **a whole file**: median 4,581 candidate programs per fix, because a file has hundreds of slots.
- 65% of unframed fixes live in **a handful of functions**, so their slot count is the slot count of those functions — typically one to two orders of magnitude smaller.
- So the reachable target is not "synthesise the patch" but **"execute the path, then search only inside the functions on it"**, with the assertion as the grader.

## The single bottleneck, stated so it can be attacked

**Localisation below the function.** The machine gives a file (18% of failures), or nothing at all (84%). Tracing gives the set of executed functions (65%). What is still missing is *which expression inside those functions* — and that is now a small, bounded, executable question rather than an open one.

## The next build, named and predicted before it is written

**Path-restricted search.** For a failing test: trace the run, take the executed functions in the file under repair, enumerate single-token substitutions inside them (round 22's alphabet — the file's own tokens, the machine's `dir()`, the assertion's literals), and grade each candidate by running that one test. Then measure, on the same corpus:

1. **containment** — is the true fix inside the path-restricted candidate set?
2. **cost** — how many executions to reach it, against round 22's 4,581 baseline.

Prediction, stated now so it can be falsified: containment in the high tens of percent, cost in the low hundreds of executions — a one-to-two-order reduction, not a solution. If containment is not clearly above the 2.7% ceiling that killed the last mechanism, this route joins the same graveyard, and the honest conclusion becomes that no parameter-free proposal mechanism reaches real repair.

## What is real in the original claim, restated for the fifth time with a new number

Instant learning and instant learning in new environments are **solved for every capability whose observable the world produces** — operators, effects, composition, exactly and permanently, with no weights. They do not extend to edits, and the reason is now measured from four independent directions: the word is not supplied (8.8%), the site is not localised (18%), the check cannot substitute (2.7% ceiling), and the value has no visible producer (1.2%). What *is* visible, for two thirds of cases, is the **path**.

The creature is still not needed. What is needed is one more observation, one level finer than the path.

## Limits

- The producer is matched by repr equality; a repr collision would misattribute, and identity capture inside the assertion is not implemented.
- Only the file under repair is traced, so a producer in another module is invisible **by design**; that design choice is what the round falsifies.
- "A function the fix changed was on the path" is necessary, not sufficient: the fix may be in that function for an unrelated reason.
- 3 tasks could not run under the tracer and are recorded, never scored.
- Value-based fault localisation exists with learned rankers; this asks the narrower parameter-free question and does not compare with those rankers.
- No independent verification.
