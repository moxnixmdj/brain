# The name was already imported: +6.4 points, three wrong changes, and what that settles

**2026-11-12 · measured on the 15-PR / 89-file / 1,674-change corpus · no model, no network, $0**

## The question, answered in one paragraph

*Is instant learning in arbitrary environments solved, and does giving the model the most
advanced actions once make it learn them permanently?* **No.** One demonstration reaches 23.06%
of the developers' changes with the shipped organ, 29.45% once the operator below is added, and 0% on five of the fifteen pull requests. The 8.13× speedup on the record is a cached refusal, not a solved Problem 1. What is real is narrower and useful: a
demonstration can be turned into a **typed operator**, which can be written down, measured and reused; that is how the number moves. Experience buys bindings;
code buys operators. The model is not sentient, does not learn permanently from one exposure,
and the corpus says so.

## What this operator does

The organ refuses a change whose new code reads a name the target does not provide. Its import
machinery deliberately declines one case: when the name came from an import the example already
had (a *standing* import, not a line the example added) and the target already imports from that
module, the organ leaves the file's own import line alone. That is conservative and defensible,
and it is exactly the case people hit:

```
example (unchanged import line):   from datetime import UTC, datetime
example change:                    datetime.utcnow()  ->  datetime.now(UTC)
target:                            from datetime import date, datetime, timedelta
                                   datetime.utcnow()
```

The developer extends the line that is already there. `bring_names_v1.py` does the same: it takes
the name the lesson says it needs, finds the target's `from M import ...` line for the same
module, and inserts the name **where its spelling sorts** (the order a formatter keeps). It then
runs the organ's own gate on the result. It changes nothing else:

* a star import, a relative import, a name the target already binds, or a module that cannot be
  found in the project is refused;
* if the organ applies **no** rule after the import is brought, the import is not returned: the
  original text is.

That last condition was added after the first measurement, and it is the difference between a
gain and a leak. The first run brought imports into 51 target files; on most of them no rule
applied, and the lone import line counted as a wrong change. Thirty-four wrong changes instead of
fourteen. With the fallback, the same coverage is kept and the wrong count returns to
seventeen.

## The measurement

`canonical/tools/bring_names_measure_20261112_v1.py`, one example per pull request and every
other file a target, 440 askings:

| arm | right | changes | coverage | precision | wrong changes | whole files exact |
|---|---:|---:|---:|---:|---:|---:|
| base (organ as shipped) | 386 | 1,674 | 23.06% | 94.61% | 14 | 117 |
| + bring the name | **493** | 1,674 | **29.45%** | 91.30% | **17** | **134** |

The gain is **+107 correct changes, +6.39 points, +17 files exactly as the developers left
them**, at the cost of **three** additional changes the developers did not make. Precision falls
3.31 points because the metric counts an added import line in the denominator but excludes it
from the numerator (`right_not_imports`); the error count, which does not have that convention,
moves from 14 to 17.

The whole gain is one pull request, and it is a real and common migration:

| pull request | base | + bring |
|---|---:|---:|
| `Project-Go-Forward#483` (`utcnow` → `now(UTC)`) | 43/155 | **150/155** |
| `automagician#55` (`typing.Union`) | 0/40 | 0/40 |
| `env-inspector#72` (`typing.List`) | 34/280 | 34/280 |
| `libcloud#2217` (`datetime.timezone`) | 12/30 | 12/30 |

On the last three the names were brought and no rule applied; the fallback returned the original
file, so the arm is neutral rather than harmful. That is the correct behaviour for an operator
with no oracle: **when the edit does not follow, do not leave the preparation behind.**

## What this does and does not settle

It settles that the `NAME_NOT_AVAILABLE` class — 22 askings, 107 changes in the recorded census —
is reachable, and that the recorded estimate (+6.39 points) was exact. It does not settle Problem
2:

* one example still reaches 29.45%, not 100%;
* five pull requests remain at zero: `automagician#55` (a grab bag), `CompressAI-Vision#40` and
  `invenio-pidstore#189` (library removals), `nibabel#1609` and `jupyter-sphinx#301` (string
  changes). The first three need a learner for import lines and block changes; the last two are
  the f-string operator's class, measured separately; no single operator reads an example the
  organ cannot learn from;
* the operator helps one class of migration; it is not a general rule;
* precision is agreement with the developers, not correctness, and no project's tests were run.

## Why this is the shape of the answer to the larger question

The 2026 evidence is consistent with what the corpus shows. **SkillsBench** (2026): curated
skills +16.2 points, self-generated skills −1.3. **SkillLearnBench** (COLM'26): more instances do
not raise coverage (36.05 / 34.09 / 31.35 for 1 / 3 / 5). **SkillEvolBench** (2026): agents adapt
locally but rarely form reusable skills, and raw trajectories often beat distilled ones.
**Continual-ARC** (2026): harness methods generally fail to persist without expert guidance, and
none gains on unseen tasks. The thing that moves is not another exposure or another environment;
it is a typed operator with a check and a refusal, which is what this file adds.

So the honest answer to "is this revolutionary?" is: it is a **disciplined, measurable way to
turn one example into one reusable operator**, and that is worth more than another demonstration.
It is not sentience, not permanent learning from experience, and not a solution to arbitrary
computer use. The fastest real path is the one this record follows: take the largest refusal
class, write the smallest operator that covers it, measure coverage and error count together,
and keep the operator only if the errors stay near the base.

## Reproduce

```bash
python3 canonical/tools/repeated_change_one_example_measure_v1.py \
  --collect /tmp/pulls.json \
  --as-recorded-in canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json
python3 canonical/tools/bring_names_measure_20261112_v1.py \
  --pulls /tmp/pulls.json --json /tmp/bring_measure.json
python3 -m unittest canonical.tests.test_bring_names_v1
```

The corpus is reproducible from the recorded verification record and the GitHub API; it is not
stored in the tree. The measurement is a sandbox measurement, not a receipt. `truth.achieved`
stays false.

## Limits

* Fifteen pull requests, six files each, chosen because they repeat one change.
* No test of any of the fifteen projects was run.
* The operator only extends a `from module import ...` line (or adds one) for a module the
  target already imports, or one resolvable from the project; a relative import is refused.
* The measurement arm is a companion to the organ; the organ itself is unchanged.
* The composition with the expression operators (rename, f-string) is not measured here.
