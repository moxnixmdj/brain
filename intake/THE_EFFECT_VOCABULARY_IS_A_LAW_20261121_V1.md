# The effect vocabulary is a law, not a table — and two of my numbers were meaningless

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls · 8 tests pass

This receipt corrects the one it replaces. I published "the vocabulary names 5 of 80 small diffs
(6.25%)" and "the law names 19". **Both denominators were impossible**, and the error is worth
recording because a green test can be built on nonsense.

---

## The error: `change` is not an independent coordinate

I enumerated a grid of three integers — `change` −2..2, `arrived` 0..3, `departed` 0..3 — and
counted how many shapes the classifier named. But an entity that arrives or departs **moves the
count**, so the only diffs that can occur satisfy:

```
change == arrived - departed
```

| | |
|---|---|
| grid cells I measured on | 80 |
| **impossible cells** | **66** |
| possible small diffs | **14** |
| named by the old table | **5** |
| described by the law | **14** |

So the honest fraction was **5 of 14**, not 5 of 80. Every percentage I computed on that grid was
a fraction of things that cannot happen.

## The law

Any possible diff is described by two integers, with no table:

```
net      = change              how many entities the surface gained (+) or lost (-)
replaced = min(arrived, departed)   how many left while another arrived
moved    = |net| + replaced
```

| net | replaced | name |
|---|---|---|
| +1 | 0 | `PERSIST` |
| −1 | 0 | `REMOVE` |
| 0 | 1 | `REPLACE` |
| +1 | 1 *(a copy taken, original kept)* | `APPEND` |
| 0 | 0 | `INERT` |

**The law reproduces all five original names with zero mismatches.** That is what makes it a
generalisation rather than a redefinition, and it is the test that carries it.

A change of twenty entities is not "unclassified": it is `net = 20`, described by the same two
integers.

## Two more errors, both mine, both caught by tests I had written

**1. `is_single` was `|net| <= 1 and replaced <= 1`.** That calls `(-2, 1, 3)` — two net plus one
replaced, three entities moved — single. It claimed 36 single shapes where the table named 5.

**2. "Named" and "single" are different questions.** `APPEND` moves three and `INERT` moves none,
and both are named. I had used one predicate for both, so the moment `APPEND` existed the claim
"every named shape is single" became false. The law now reports `is_named` and `is_single`
separately, and a test pins that they disagree for exactly those two shapes.

**And my own test asserted on an impossible diff.** `test_a_multi_entity_change...` used
`(-1, 0, 2)`, which cannot occur. A test can be green and meaningless at the same time.

## What actually stands

| claim | status |
|---|---|
| every **possible** small diff is described | **14 of 14** — no diff is ever "UNKNOWN" again |
| the law reproduces the original table's names | **5 of 5, no mismatch** |
| the table covered the possible space | 5 of 14 (36%) |
| a larger change needs a new name | **no** — same two integers |

This is "the best part is no part" applied to the vocabulary: a five-row dict was five constants
pretending to be a theory, and the theory is two integers over a constrained space.

`truth.achieved` remains `false`.
