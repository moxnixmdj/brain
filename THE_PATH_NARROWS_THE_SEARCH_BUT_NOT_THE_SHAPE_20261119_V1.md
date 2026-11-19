# The path narrows the search, but the ceiling was never the search

**Round 26. Receipt: `canonical/verification/THE_PATH_NARROWS_THE_SEARCH_BUT_NOT_THE_SHAPE_20261119_V1.json`. Tool: `canonical/tools/the_path_narrows_the_search_but_not_the_shape_v1.py`. 82 real refused suites traced. Zero model calls, zero parameters.**

## The prediction this round was written to test

Round 25 ended with a falsifiable prediction, written down before the build:

> path-restricted search — enumerate single-token substitutions only inside the executed functions of the file under repair, grade by executing that one test — should give containment in the **high tens of percent** at a cost in the **low hundreds** of executions, against round 22's whole-file median of 4,581.

## The result

| space (all restricted to executed functions) | contained | share |
|---|---|---|
| single-token substitution | **2 / 82** | **2.4%** |
| one element added to a literal or a call | 0 | 0% |
| a statement inserted whose text the file already contains | 0 | 0% |
| **either** | **2 / 82** | **2.4%** |
| of those, confirmed by executing the real suite | **2 / 2** | 100% |

**The prediction is falsified, and by two orders of magnitude.** The two fixes that *are* contained are real: the candidate reproduces the fixed file byte for byte *and* the machine passes when it is applied (2 of 2 execution-confirmed). The mechanism works exactly where it applies. It applies to 2.4%.

## Why the path did not help — the number that matters

Round 22 found **8** token-shaped fixes in 87. On this round's traced runs, only **2** of those 8 have their changed line inside a function the failing test executed. The path **excluded six of the eight fixes it was supposed to find**.

That is the opposite of the assumption behind path restriction. The failing test is not a window onto the bug: an unexecuted branch, a lazily registered import, a pickling path, an error path not taken — the fix lives exactly where the test did not go. Tracing gives a *subset of the file*, and for repair that subset is not a superset of the answer.

## What this closes

Six rounds, six walls, all in the same place — the machine's output does not contain the observation that identifies an edit:

| route | measurement |
|---|---|
| one experience per action | 123/160 wrong (operators only) |
| seed corpora, bigger vocabulary | 0 gained, 1 lost |
| the file's own alphabet | 0 of 8 one-token fixes |
| blind generate-and-verify | 4,581 executions per fix |
| the refusal's own words | 32% named, 0/5 for literals |
| check's words + local slot | ceiling 2.7% |
| rejected value's provenance | producer found 1.2%, localising 0 |
| **executed path + token search** | **2.4%, and the path removed 6 of 8 answers** |

And the structural generators die with it: statement insertion, element addition, and copying the file's own text all contain **zero** of the real fixes.

## The single bottleneck, stated for the last time

**A generator of structure.** Not localisation (four ways tried, all ≤ 18%), not vocabulary (8.8%), not the check (2.7%), not the value (1.2%), not the path (2.4%, and it subtracts). What all these routes share is that they *select* from things the machine already shows. The remaining 80 of 82 fixes require *producing* a statement the machine has never shown in that position, and no selection over what exists can produce what does not.

That is the honest end of this line, and it is not a defeat — it is the boundary of the law this project was built on. **"The best part is no part" is exactly why the operator layer is perfect**: an operator's effect is *observation-bound*, so provenance and refusals give it exactly, for zero parameters, in one execution. An edit is *generation-bound*, and generation is precisely the part that is not free. The frontier pays for that part in weights; this project has now measured, eight ways, that nothing cheaper buys it.

## The smartest thing to do next, given that

Not another selector. If the structure must be produced and no parameters are allowed, the only remaining source is **structure the repository already contains in a different arrangement** — shapes, not text. Copying statements verbatim was measured here and contains zero; so a shape-level generator (anti-unify two existing statements, instantiate at the site, grade by execution) is the only untried route, and it is untried because it is expensive, not because it is easy. If it also returns zero, the conclusion is final and should be stated plainly: **parameter-free repair is bounded at a few percent of real fixes, and the capability requires a learned generator — every bit of which must still be calculated, never a knowledge house.**

## What remains exactly true about instant learning

It is perfect, and permanently so, for every capability whose observable the world produces: the refusal surface (160/160), the effect as a provenance map (24/24 unexecuted trees), composition. That is not a small thing — it is a whole agent's worth of computer use, and it needs no weights at all. It simply does not extend to the part where the answer does not exist until it is invented.

## Limits

- Containment is byte equality with the fixed file, stricter than "a patch that passes"; the two contained fixes were both executed and passed.
- Only the file under repair is traced, so a fix in another file is invisible by design.
- 3 tasks could not run under the tracer and are recorded, never scored.
- The structural spaces measured here are text-level; shape-level anti-unification is named as untried, not measured.
- No independent verification.
