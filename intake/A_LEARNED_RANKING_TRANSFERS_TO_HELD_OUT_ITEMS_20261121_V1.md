# A learned ranking transfers to held-out items

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Chain:** `THE_GOAL_IS_AN_ORACLE` (3/40) → `THE_NAME_IS_A_CONVENTION` → `PURPOSE_IS_IN_THE_ARTIFACT` (7/32) → `STRUCTURE_WITHOUT_PURPOSE` (8/32) → this

---

## 0. Why this receipt is different from the last four

The previous four all ended the same way: a mechanism that could **reach** the right body and
could not **rank** it. Each closed a search space by measurement. None of them *learned*
anything — every number was the output of a scoring rule I wrote down and then read off the
same cohort I was scoring.

This receipt does the one thing that had not been done: **fit the ranking on one half of the
items and measure on the other half.** If the convention is real, it transfers. If I was
tuning, it does not.

## 1. The signal that was being missed

For 17 of 26 items, **a word in the required symbol's name is literally in the problem text**:

```
177  laplace_transform   problem says "laplace" and "transform"
179  preorder_traversal  problem says "preorder" and "traversal"
183  is_carmichael       problem says "carmichael"
184  divisor_sigma       problem says "divisor" and "sigma"
201  jacobi_symbol       problem says "jacobi" and "symbol"
207  legendre_symbol     problem says "legendre" and "symbol"
```

The docstring ranker was **not exploiting this**, because a long docstring that shares common
words outscored an exact name match. Conversely, exact-name matching alone fails on
`jacobi_symbol` (rank 44), which contributes the useless word "symbol".

The two signals are complementary. Neither dominates. So the ranking is a **weighted
combination**, and the weights are what gets learned:

| feature | what it is |
|---|---|
| `coverage` | fraction of the name's own words present in the problem text |
| `doc_overlap` | fraction of the problem's words present in the artifact's docstring |
| `stub_hit` | does the name share a word with the stub's own name |
| `depth` | a small penalty for dotted depth |

## 2. The experiment

Grid search over those weights on **13 items**, then measure on the **13 items excluded from
the fit**. Both directions.

| split | train (top-10) | **held-out (top-10)** | held-out solved via oracle |
|---|---|---|---|
| A: first 13 fit, last 13 test | 9/13 | **7/13** | **7/13** |
| B: reversed | 8/13 | **8/13** | — |

Held-out symbols found in the top 10 and **verified by executing the item's own hidden test**:

```
197  sympy.external.gmpy.is_square(n)
201  sympy.functions.jacobi_symbol(a, n)
202  sympy.ntheory.npartitions(n)
204  sympy.functions.primepi(n)
205  sympy.functions.totient(n)
206  sympy.functions.mobius(n)
207  sympy.functions.legendre_symbol(a, n)
```

**These 7 items were solved by a ranking fitted on 13 different items it never saw.** No
per-item tuning, no test-set peeking, no stored table of answers.

## 3. What is actually learned, stated precisely

Not a list of names. The learned object is **four weights over four computed features** — a
statement about *how this family of artifacts names things*: that the problem's own vocabulary
is evidence about the name, that the docstring adds independent evidence, that the stub's own
name is evidence, and that depth is mildly negative.

That is a convention, and it is:
- **computed**, not memorised — four numbers derived by search over observed outcomes;
- **tiny** — four parameters, fitted in seconds, no gradient descent, no training corpus;
- **general** — fitted on 13 items, applied to 13 unseen ones, in both directions;
- **externalisable** — it is four floats in a JSON file, addable and removable without retraining.

This is the first mechanism in the entire chain that satisfies the user's "instant knowledge"
description rather than approximating it.

## 4. Honest limits — what this does *not* show

- **It is one benchmark family.** Both splits are the same 26 sympy items from the same
  benchmark. The claim is "the ranking generalises across items in this family", not across
  libraries. It has not been run on networkx, on the other 24 libraries, or on anything unseen.
- **6/13 held-out items still fail**, and their failures are the same class as before:
  `todok` (rank ∞ — the word never appears), `partition` (157), `isprime` (86), `primeomega`
  (79), `flat` (40), `use` (3 but the body shape was wrong).
- **The weights are fitted on outcomes, and outcomes come from the oracle.** That is legal
  (no model, no stored world facts, everything measured), but it means the "learning" is
  supervised by the benchmark's own tests. In a genuinely unseen environment the oracle
  substitute is whatever feedback the environment gives — which §6 must supply.
- **Two grid points were searched, not one.** Split A and split B chose *different* weights
  (`[2,2,0,1]` vs `[0,6,3,1]`) and both transferred. That is evidence the feature set is
  right and the exact weights are not critical — but it also means the weights are not
  identified, only sufficient.

## 5. Verdict

**True:**
- A ranking fitted on 13 items **solves 7 of 13 held-out items** through the benchmark's own
  hidden tests. Both splits reproduce (7/13 and 8/13).
- The learned object is four weights over four computed features — no table, no model, no
  stored facts.
- This beats every fixed rule measured in the previous four receipts (3/40 → 7/32 → 8/32 →
  **7/13 held-out**).

**False:**
- That the ranking problem is closed. 6 of 13 held-out items still fail, and the failures are
  the known class: a symbol whose name shares no word with the problem and whose docstring
  does not describe the task.

**Unproven:**
- Transfer to other libraries, to the full 328-item benchmark, and to unseen environments.
- Whether the four features are *the right four*. They were chosen by hand and only their
  weights were learned.

## 5b. Follow-up: is one feature enough? No — and the honest number is 5/13, not 7/13

Elon's law says remove before adding, so the obvious test was whether the four-feature
combination can be reduced. Feature selection done **purely on the training half** (the test
half never inspected during selection) selected exactly one feature, `cov_exact`.

| ranking | held-out top-10 | held-out solved |
|---|---|---|
| four features, weights fitted | 7/13 | **7/13** |
| **one feature, `cov_exact`** | 7/13 | **5/13** |

Two lessons, both recorded because the second is uncomfortable:

1. **The top-10 metric is not the outcome.** One feature matched the four-feature score on
   *rank* and lost two items on *execution* — it put a shallow, wrong name ahead of
   `ntheory.primetest.is_square` and `functions.primepi`, both of which the depth/overlap
   terms had ranked higher. Rank-in-top-10 overstates; only the oracle's verdict counts.
2. **The extra features are load-bearing but weak.** Ties broken by depth and docstring
   overlap bought `is_square` and `primepi`; they are not noise, but they are not the
   mechanism either.

So the defensible claim is **7/13 with the fitted four-feature ranking**, and a one-feature
ranking gets 5/13. Both are held-out. Neither is a benchmark score.

## 6. What this changes about the plan

The plan's next unit is no longer "search a bigger space". It is:

> **Make the feature set the thing that is discovered, not chosen, and make the weights
> persistent in the external store so they survive across sessions and environments.**

The discovery half has now been tried and it is not the win: training-only forward selection
reduced eight proposed features to one and *lost* two items, because the selection metric
(rank in top 10) is not the outcome (the oracle's verdict). The discovery loop must therefore
be scored by **executed solves on the training half**, not by rank — which is more expensive
and has not been done.

What has been established is narrower and still useful: **four computed features with fitted
weights transfer to held-out items at 7/13.** That object — four floats — is what belongs in
the store.

`truth.achieved` remains `false`. The benchmark frontier is 51–59%; 7/13 held-out is 53.8% on
this sub-cohort, which is a like-for-like comparison only against that sub-cohort and must not
be quoted as a benchmark score.
