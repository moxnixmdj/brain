# The run already contains the intervention

*2026-11-19 · measurement: `canonical/verification/THE_SAME_GUARD_TWICE_IS_THE_DISCRIMINATOR_20261119_V1.json`
· answer in full: `THE_RUN_ALREADY_CONTAINS_THE_INTERVENTION_20261119_V1.md` (repository root)*

## The claim being answered

> "Give the model a try in each new environment and the smartest actions once, and it owns them
> permanently — so coding and computer use are solved."

## What was built

`canonical/tools/the_same_guard_twice_is_the_discriminator_v1.py` — every `if`/`while` test in a copy of
the module is wrapped in a switch that counts firings and can flip exactly one of them. One flip is one
bit from the project's own pytest. The refinement is not searched for: the same hook logs what was in
scope at every firing, and the predicate is selected by exact fit against those values.

```
parameters_stored: 0        bits_from_the_oracle: 409 (15 commits)
```

## What it found

| | arm A: the failure text | arm B: the flipped firing |
|---|---|---|
| fresh real commits | 15 | 15 |
| seconds | 56.8 | 251.1 |
| at the human's changed line | 1 | 3 |
| the human's expression | **0** | **0** |
| flips that passed the failing test | — | 7 |
| of those that kept the suite green | — | **0** |
| of those with an exact-fit refinement | — | **0** |

The one verified repair is `click@1b0e19f505`, **in-sample**: 90 flips, 53.7 s, the human's expression,
144 tests green. It is the commit the tool was built on, and it is reported as such.

## The bottleneck, narrowed

Not parameters (zero). Not the observation device (the counterfactual is now executed, not approximated).
Not the index (three of fifteen sites reached at one bit each). **The replacement expression**: the run can
say where the wrong value was produced and which firing let it through, and cannot say what the right
value is. Twelve of the fifteen human fixes are a value the run never produced; three are behaviour that
did not exist, which the insufficiency certificate already proves no trace can supply.

## Falsifier

The claim dies if forcing the **value** at a flip-identified firing, and synthesizing from the artifact's
own vocabulary, does not beat 0/15 on a fresh corpus of the same construction — or beats it only by reading
the commit's diff.

## Integrity

Three instrument defects were found by running on real code and fixed: a `SKIPPED` test read as a failing
test; test ids containing a space truncated by `(\S+::\S+)`; and `if template[:2] == './'` producing the
operands `:2` and `2`, which made jinja2's `loaders.py` unimportable. Each has a regression test. Seven
single-firing flips that would have been reported as repairs were refused by the suite-green and
exact-fit gates.
