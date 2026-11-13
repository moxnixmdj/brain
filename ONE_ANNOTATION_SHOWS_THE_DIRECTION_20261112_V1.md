# One annotation shows the direction: +27 points, and the family follows

**2026-11-12 · 15 pull requests / 89 files / 1,674 developers' changes · no model, no network, $0**

## The answer to the question, again, in the form the corpus can defend

*Does one try in a new environment make the model permanently capable?* **No.** The model does
not learn from the try. What can happen is smaller and real: the try is an **example**, and an
example can be turned into a **typed operator** that covers a family of changes the example never
showed. This record adds the largest such operator so far: one changed annotation says which way
a PEP 585 migration goes, and the operator applies the family.

The measured effect on one example: **29.45% → 56.87% of the developers' changes**, precision
**91.81% → 92.79%**, wrong changes 36 → 48, whole files exactly right 117 → 155. Two pull
requests account for the gain, and on one of them the coverage is **280/280 with zero wrong
changes**.

## What the operator is

Python has two spellings for the same generic annotation: the builtin subscript (`list[int]`,
`dict[str, int]`) and the `typing` name (`List[int]`, `Dict[str, int]`). A migration changes one
spelling to the other for the whole family. One changed annotation in the example is enough to
say which way:

```
before: list[Any]     after: List[Any]      -> up   (builtin -> typing)
before: List[Any]     after: list[Any]      -> down (typing -> builtin)
```

The family is fixed knowledge, not an inference:

```
list <-> List    dict <-> Dict    set <-> Set    tuple <-> Tuple
frozenset <-> FrozenSet    type <-> Type
```

and the PEP 585 companions move with it: `Callable`, `Iterable`, `Iterator`, `Mapping`,
`Sequence` and the rest of `collections.abc` leave `typing` for `collections.abc` on the way
down, on the line the typing import stood on.

The edit replaces the identifier bytes of each subscript base and splices the import lines; the
rest of the file keeps its formatting. The result is parsed before it is returned. If the example
shows both directions (one pair up, another down), nothing is applied.

## The measurement

`canonical/tools/generic_alias_measure_20261112_v1.py`, one example per pull request and every
other file a target, 440 askings:

| arm | right | changes | coverage | precision | wrong | whole files |
|---|---:|---:|---:|---:|---:|---:|
| base (organ as shipped) | 493 | 1,674 | 29.45% | 91.81% | 36 | 117 |
| + the family | **952** | 1,674 | **56.87%** | **92.79%** | **48** | **155** |

+459 correct changes, +27.42 points, and precision **rises** one point: the operator reproduces
what the developers did more often than the organ's own rules did. The error count rises by 12.

Per pull request:

| pull request | base | + family |
|---|---:|---:|
| `env-inspector#72` (`dict`/`set`/`tuple` → `Dict`/`Set`/`Tuple`) | 34/280 | **280/280**, 0 wrong, 30/30 whole files |
| `fgpyo#300` (`List`/`Dict`/`Tuple` → builtins, `Callable` → `collections.abc`) | 2/220 | **215/220**, 25 wrong |
| the other thirteen | unchanged | unchanged |

`fgpyo` is at 97.7% coverage; its remaining five changes are a bare `Type` used as an annotation
(not a subscript, so outside this operator) and import placement that differs by a few lines.
Those are named, not hidden.

## What this settles, and what it does not

It settles that the **annotation-spelling class** is the largest reachable class in this corpus
and that one example is enough to choose its direction. It does not settle Problem 2:

* one example still reaches 56.87%, not 100%;
* the family assumption is real: a project that migrates `list` and deliberately keeps `dict`
  is not distinguished, and the measurement is the only justification for the assumption;
* only bare-name subscripts are changed; a bare `Type` annotation, `typing.List[...]` written
  qualified, and `Callable` used without an import are not;
* `automagician#55`, `CompressAI-Vision#40`, `invenio-pidstore#189`, `nibabel#1609` and
  `jupyter-sphinx#301` remain at zero in this arm. The first three are heterogeneous or
  import-only examples; the last two are the string-change class the f-string operator was
  measured on;
* no project's tests were run; precision is agreement with the developers.

## Why this is the honest shape of "generalization"

A single example cannot identify a rule: it fixes one point. What makes a rule possible is a
**constrained space of operators** plus a **direction the example chooses inside it**. Here the
space is the six PEP 585 pairs and the abc companions; the example fixes the direction; the
measurement says whether that choice matches people. That is generalization in the only sense the
corpus can demonstrate — a typed transform, chosen by one example, verified against developers.

It is not permanent learning, not sentience, and not a solution to arbitrary computer use. The
2026 evidence says the same thing from the other side: more instances do not raise coverage
(SkillLearnBench 36.05 / 34.09 / 31.35 for 1 / 3 / 5), self-generated skills often hurt
(SkillsBench −1.3 points), and no harness method gains on unseen tasks without expert guidance
(Continual-ARC). An operator is that guidance, written down once.

## Context: the organ was unavailable this morning

`main` carried its merge markers in `edit_by_example_v1.py`; the module did not parse, so no
one-example measurement could run. That was resolved first (PR #6820) by keeping both additive
sides — the module-level rename (`Swapped`) and the standing-import extension
(`aliases_to_add`) — and adding an import test for the package. The base arm here is the repaired
organ, which already includes the standing-import extension: 493/1,674 before this operator.

## Reproduce

```bash
python3 canonical/tools/repeated_change_one_example_measure_v1.py \
  --collect /tmp/pulls.json \
  --as-recorded-in canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json
python3 canonical/tools/generic_alias_measure_20261112_v1.py \
  --pulls /tmp/pulls.json --json /tmp/alias_measure.json
python3 -m unittest canonical.tests.test_generic_alias_v1
```

The corpus is reproducible from the recorded verification record and the GitHub API; it is not
stored in the tree. The measurement is a sandbox measurement, not a receipt. `truth.achieved`
stays false.

## Limits

* Fifteen pull requests, six files each, chosen because they repeat one change.
* No test of any of the fifteen projects was run.
* The family is knowledge; the example supplies only the direction.
* Formatting is preserved except on the import lines this operator splices.
* The next measured class is the string-change operator (`nibabel#1609`,
  `jupyter-sphinx#301`), then the heterogeneous/import-only examples.
