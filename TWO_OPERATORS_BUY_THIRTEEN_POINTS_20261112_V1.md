# Two operators buy thirteen points, and neither one is a solved Problem 2

**2026-11-12 · measured on the same 15 pull requests and 89 files as the pair-selection record**

## What was asked, and what this measures

Problem 2 is: one demonstration of a change, applied correctly to code the demonstration never
saw. The selection work (PR #6789) chose the better of the two available demonstrations and
lifted the chosen pair from 23.1% to 61.8% of the developers' changes on the 220 pairs. It did
not touch the other half of the problem: when the learner refuses a target because its node
shape is different, no amount of choosing among examples helps.

This is the other half. Two changes that the tree refuses can be written down as **operators**
learned from the example itself, and their worth is measured against the same 1,674 changes the
developers made in the 15 pull requests.

## The measurement

`canonical/tools/expression_operator_pack_measure_20261112_v1.py`, one example per pull request
and every other file a target, 440 askings:

| arm | right | changes | coverage | precision | gain |
|---|---:|---:|---:|---:|---:|
| base (the organ alone) | 268 | 1,674 | 16.01% | 92.41% | — |
| + method rename | **391** | 1,674 | **23.36%** | **94.67%** | **+123** |
| + concat → f-string | 363 | 1,674 | 21.68% | 72.89% | +95 |
| + both | **486** | 1,674 | **29.03%** | 78.26% | **+218** |

Three pull requests improve under the rename alone; two under the f-string alone; five under
both. The rename does not merely add changes: its precision is *higher* than the base, because
the changes it adds are the ones the developers made, at arities the organ had refused.

Per pull request, the changes are concentrated:

| pull request | base | + rename | + f-string |
|---|---:|---:|---:|
| `advisor-backend#80` | 5/55 | **55/55** | 5/55 |
| `stem#155` | 4/50 | **45/50** | 4/50 |
| `openimis#414` | 89/315 | **121/315** | 89/315 |
| `nibabel#1609` | 0/70 | 0/70 | **55/70** |
| `jupyter-sphinx#301` | 0/110 | 0/110 | **42/110** |
| `Project-Go-Forward#483` | 43/155 | 43/155 | 41/155 |

The last row is the warning: the f-string operator *lost* two correct changes on a pull request
that already scored well. It converts every string-constant concatenation, and the developers
converted only some of them.

## What the two operators are, mechanically

Both are stdlib `ast`, deterministic, $0, no model, no network.

**Method rename.** Parse the example's before and after; walk `Call` nodes; match a call in the
before with a call in the after that has the same receiver text and the same arguments and
keyword arguments, and differs only in the called name. Keep only one-to-one name maps. Apply
the map to the target's calls with the same receiver. A bare-name rename (no receiver) is
applied only when the new name is defined, imported or builtin in the target.

This is exactly the class the tree refused 50 times (`CALL_SHAPE_NOT_SHOWN`): the example showed
`logger.warn(x)` and the target had `logger.warn(y, z)`, so the arity looked different. It is not
different; the rename does not touch the arguments. The operator emits the number of changes the
example emitted, which is why it is safe without an oracle.

**String concatenation to f-string.** Parse the target; replace `BinOp(Add)` with a string
`Constant` on one side and a non-container expression on the other by a `JoinedStr` with one
`FormattedValue`. Two constants, tuples, lists, dicts and sets are skipped. The operator is gated
on the example actually containing such a change; blanket application to every target without
the gate was measured and is worse.

This operator is a **candidate generator**, not a safe action. It has no way to know which
concatenations the change was about, so it produces more changes than the developers made and
its precision falls to 72.89%. It belongs behind a test: keep the candidates the project's tests
accept. Without a test it is a 95-change gain with a 19.5-point precision loss; with a test it
would be a gain with no such loss, but that has not been measured on these fifteen projects
because their test suites were not run in the sandbox.

## What this does to the two halves of Problem 2

Selection (shipped in #6789) picks the demonstration. Operators expand what a single
demonstration can express. A prototype composition — rename applied after the organ, with the
merged `choose()` policy — measured 139→142 of 225 chosen-pair changes (mean per pull request
0.4979→0.5368, oracle best 155/230 = 0.6739). That composition is a prototype result, not the
shipped instrument; the shipped measurement above is the one-example arm.

Together they say the useful statement is narrower than "one example generalizes":

> A demonstration carries a **change class**, not just a changed span. The class can be induced
> from the example as an operator, applied to targets with different node shapes, and measured.
> Selection chooses the example; operators choose the shape; a test verifies the result.

That is the loop that is real. It is not "the model experiences it once and knows it". It is
code written down once, per class, and reused.

## What is still not solved

The one-example number is 29.03%, not 100%. Five pull requests are far from covered:

* `automagician#55` — 0/40, a grab bag: logging renames, `|` to `Union`, `match` to `if`, typo
  fixes and added tests. No one operator covers it because it is not one change.
* `CompressAI-Vision#40` — 0/35, a library removal (`six`, `from __future__`).
* `invenio-pidstore#189` — 0/115, a library removal plus `dict(...)` to `{...}`.
* `testtools#335` — 12/44, a rename the operator did not catch because the receiver text changes.
* `fgpyo#300` — 2/220, a large mechanical change the organ's own rules do not reach.

The queue that follows from the refusals, in order of size: import-only (60 refusals), call shape
(the rename operator covers part of the 50), block shape (34), name/import scope (22), and a
check-aware filter for the f-string candidates. Each is a typed operator plus a verification, not
another demonstration.

## What the 2026 evidence says about this shape of answer

* **SkillEvolBench** (arXiv:2605.24117): agents adapt locally but rarely form reusable skills;
  raw trajectory reuse often beats distilled skills because distillation is lossy. An operator is
  the opposite bet: keep the change as a typed transform, not a summary.
* **SkillLearnBench** (arXiv:2604.20087): more instances do not raise coverage (36.05/34.09/31.35
  for 1/3/5 instances). This is direct evidence against "just give it more tries or more
  environments", and for spending the effort on the operator set.
* **Continual-ARC** (arXiv:2611.14505): harness methods generally fail to persist without expert
  guidance, and none gains on unseen tasks. A hand-written operator is expert guidance, which is
  why it is honest to call this engineering rather than learning.
* **GEN-1.5** (Generalist AI, 2026): one demonstration reaches 59%, ten gradient steps 83%.
  Prompting a single exposure is not the ceiling; an operator is a stronger form of the same
  idea, and weight training remains the stronger one.

## The answer to the larger question

*Is this a revolutionary way for agents to learn faster than current methods?* No. It is a
disciplined way to turn one example into a **reusable, typed transformation**, and it beats
retrieval because it can change node shapes. It is not sentient, it does not learn permanently
from experience, and it does not solve arbitrary computer use. What it does is raise the
one-example floor on a real corpus from 16.01% to 29.03% with two small operators, and it makes
the next operator measurable in the same way.

The smartest path is the one this record follows: measure the refusal classes, write the
smallest typed operator that covers one, compose it with selection, and keep the precision
number next to the coverage number. The fastest path is not a larger model or more environments;
it is the next operator, verified.

## Reproduce

```bash
python3 canonical/tools/repeated_change_one_example_measure_v1.py \
  --collect /tmp/pulls.json \
  --as-recorded-in canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json
python3 canonical/tools/expression_operator_pack_measure_20261112_v1.py \
  --pulls /tmp/pulls.json --json /tmp/operator_pack.json
python3 -m unittest canonical.tests.test_expression_operator_pack_v1
```

The corpus is not stored in the tree; it is reproducible from the recorded verification record
and the GitHub API, as recorded in `collect`. The measurement is a sandbox measurement, not a
receipt, and the developers' agreement is not correctness.

## Limits

* Fifteen pull requests, six files each, chosen because they repeat one change; not a random
  sample of software engineering.
* No test of any of the fifteen projects was run; precision is agreement with the developers.
* The f-string arm is a candidate generator; its 72.89% precision is a reason to gate it behind a
  test, not a reason to ship it as an action.
* The composition with selection is a prototype measurement; the shipped tool measures the
  one-example arm.
* `truth.achieved` stays false.
