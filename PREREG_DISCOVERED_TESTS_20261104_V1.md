# Pre-registration — discovering the tests, not the kinds

**2026-11-04 · round 13 · before implementation · authority NONE**

## The gap round 12 named against itself

Round 12 recovered a *periodic* hypothesis and then said so plainly: the pathway that found it is a
partition test, `mod 3` was induced only because **I had already written that test**, and "writing the
test is still my job". So the ontology grew, but the thing that decides *what can be recovered* did
not. Same shape as the defect round 12 was written to fix, one level up: **vocabulary was hard-coded,
then became learned; the tests that license vocabulary are still hard-coded.**

Also measured this round, and worth recording because it constrains the design: the survivor
vocabulary is already heterogeneous per target, which is the raw material such a system would need.

```
mod 2     75 survivors   ops = %, -, /
floor     67 survivors   ops = *, +, -, /, //
monotone   0 survivors
```

## The claim

**A test can be preferred by its record of discovery, and that preference is measurable against a
fixed order.**

Concretely: several structural tests exist (periodic, floor-level, sign-step). Give each a record of
how many targets it has historically recovered, prefer the best-recorded test first, and admit any new
test only if it does not duplicate a discovery already made. Then the *rate of discovery per attempt*
should improve with experience even though no test is added.

That is a much smaller claim than "it invents tests", and it is the one I can actually falsify. An
honest name for the mechanism: **a discovery record that reorders a fixed test library.** I will say
so in the writeup rather than dressing it as invention.

## Predictions

| id | prediction | how scored |
|---|---|---|
| **T1** | `floor`-structured data is recovered by a *level-composition* test (constant per integer part of the input) and not by the periodic test — the tests are genuinely different and only one applies. | test chosen, per target |
| **T2** | The recovery attempt on a target the library cannot explain is recorded, so the same failing attempt is not repeated blindly on the same input. | attempt record |
| **T3** | Ordering tests by their discovery record changes which test is tried first, and the ordering is genuinely per-target rather than a re-sorting of a constant. | order before/after a success |
| **T4** | With the record in place, the number of tests tried before a successful recovery **strictly decreases** relative to a fixed order — measured as attempts-per-discovery, not asserted. | sum over a run |
| **T5** | **The negative, and the one that matters:** a test that succeeds is not automatically believed. Six random points must still be refused, and a test that would fit them (a large period, a level per observation) must be *rejected by the same degrees-of-freedom constraint* that round 12 needed. | refusal |
| **T6** | Duplicate discoveries are not admitted twice: if two tests both recover the same law for the same target, the ontology records one, so the "number of kinds" is not inflated by the size of the test library. | kinds count |
| **T7** | Recovery still works where the string search finds nothing (`mod 3` had 0 survivors) — the test library must not become dependent on the survivor vocabulary it was built beside. | 0-survivor case |

T4 is the only one that says the mechanism *improves with experience*, and it is measured as a count,
so failing it is unambiguous. If T4 fails I will report that the ordering is decorative.

## Stop condition

If T1 fails — the level test also handles period-2 data, or the periodic test handles floor data — then
the "library of distinct tests" is one test wearing several names, T3 and T4 measure nothing, and the
round should be reported as a null result rather than as progress.
