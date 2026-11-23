# The list-call production, and a zero that was already counted

**Date:** 2026-11-21
**Status:** mechanism added, **measured at +0 items**. A correction to my own reporting.

## What was added

`sympy.Matrix([first, second])` — a constructor taking the whole parameter list as ONE
sequence literal. The grammar could only ever emit a constructor over a *single* argument, so
the `Matrix([...])` shape was unconstructible.

For this to fire, `from sympy import Matrix` had to count as an imported callable. It did not:
the earlier rule required a DOTTED module (`from scipy.ndimage import ...`) and excluded
top-level imports. The distinction that matters is not module depth, it is whether the stub
bound the name. Fixed: a capitalised name imported from anywhere is a constructor candidate.

## The error in my own reporting

I then ran items 177, 182, 187, 192, 199, 197 individually and four of them passed. I read that
as "four more items". **It was not.** All four were already in the 82 from the previous run.
Re-solving an item that is already counted and calling the difference a gain is exactly the
failure mode I am required to avoid.

The full run confirms it: **82/193, unchanged, 0 regressions, 0 new.**

## What is actually true

    before:  82/193 = 42.5%
    after:   82/193 = 42.5%
    delta:   +0

The list-call production is real and the from-import fix is real — `Matrix([first, second])` is
now in the search space where before it was not — but **it did not buy an item on this
benchmark.** It may buy one on a different one. It is not evidence of progress, and the honest
ledger does not move.

## Two mechanisms now dead

* **Replaying a saved answer**: 8/288 = 2.8%
* **Lifting identifiers (my first "generalization")**: 0/288
* **Stub-shape → body-shape rule learned leave-one-library-out**: 54.8%, **worse than always
  predicting "single call" (67.3%)**

Three attempts at the user's memory question, all negative. That is itself the finding: the
*shape* of an answer carries almost no information. What carries the information is **which
name**, and that is a property of the artifact, not of any past item.

## Hard ceiling, measured

    65 / 110 ceiling-achievable items have a goal that shares a stem with the truth's callee
    = 59.1%

In the other 45, the goal never contains the artifact's word in any recognizable form. No
ranker, no memory, no web fetch can close those — the information is not in the goal.

## Not claimed

* `truth.achieved` remains **false**. Authority remains **NONE**.
* 82/193 is the score on the 193 no-dependency items, in the environment as installed.
