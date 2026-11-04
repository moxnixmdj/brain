# Pre-registration — the search has a blind spot it cannot report, and hypotheses it cannot form

**2026-11-04 · round 10 · before implementation · authority NONE**

## The two defects, measured before either is fixed

**D1 — the search lies about the grammar.** `y = 2x + 1` is inside the grammar: `((x + 1) + x) / 1`
reproduces all three points. The search returns `UNRESOLVED` anyway, with `why = "no body in the
grammar reproduces the examples"`. That sentence is false. The truth is that the bank capped at
`max_bank_size=900` filled up before the weight-4 tier reached the body. Measured sweep:

| task | bank 900 | bank 5k | bank 50k |
|---|---|---|---|
| `x+1` | 21 | 38 | 73 |
| `2x+1` | **0** | 21 | 32 |
| `x*x+1` | **0** | 18 | 20 |
| `2x` (the session's case) | 12 | 12 | 12 |

The last row is the important one: every conclusion this session rests on is **stable** across a
60× change in the budget. The cap is not corrupting the epistemics; it is silently corrupting the
*coverage*, and coverage failure is reported as a fact about the world.

**D2 — the creature has no hypothesis with free parameters.** Its ontology is closed expressions
over the inputs plus a frozen constant list `[0, 1, 2, -1, 100, ...]`. Consequences:

- `3x+1` is unreachable at any budget I can afford, because slope 3 has to be *spelled*
  (`(x+x)+x`) and each spelling costs weight. Nothing in the system can say `a·x + b` and solve
  for `a`, `b`.
- `2x` from three points yields **12 programs / 3 explanations**, all of them spellings of one
  linear function. The creature cannot say `y = a·x`, so it enumerates syntax and then has to
  *guess* which spellings are the same idea — by probing a finite range and hoping.

That second consequence is what makes the whole apparatus feel like static code: it counts
sentences because it has no sentences-with-slots to count instead.

## Predictions

| id | prediction | how scored |
|---|---|---|
| **H1** | The completeness of an enumeration is **decidable** from state the search already has: the bank filled iff `len(seen_sigs) >= max_bank_size`, and if it did not fill and the weight sweep finished, the enumeration is complete over the grammar at that weight bound. | a flag that is true at 50k and false at 900 for `2x+1` |
| **H2** | With completeness reported, `2x+1` at bank 900 is classified **`SEARCH_TRUNCATED`**, not `UNRESOLVED` — the report no longer attributes a budget failure to the grammar. | status string, both bank sizes |
| **H3** | The affine family `a·x + b` determines its two parameters exactly from three points and detects inconsistency exactly (rational arithmetic, no tolerance). `3x+1` fits with `a=3, b=1`; the two-point case `2x` leaves the pair underdetermined; a genuinely non-affine point set is rejected. | fitted parameters and a rejected case |
| **H4** | The number of points a hypothesis class *needs* is computable from the class, not discovered by trial: `a·x + b` needs 2, and a third point is a **consistency test**, not new information. | `needed=2, supplied=3, surplus=1` |
| **H5** | For bodies that instantiate a fitted family, grouping is **algebraic and exact** — same family, same parameters — so the probe-range caveat disappears for them. For the rest, the probe basis remains and the report says which basis was used per group. | per-group `basis` field; the `2x` ten-member group is algebraic |
| **H6** | `a·x + b` fitted to the three `2x` points yields `a=2, b=0`, and the affine hypothesis alone explains the data with **one** explanation and **zero** free parameters — where the string search needed 12 programs to do the same. | counts side by side |

I expect H6 to be the uncomfortable one: if the affine class makes the 12-program enumeration
redundant, then a large fraction of this session's machinery is scaffolding around a missing
ontology. I will say so plainly if that is what the numbers show.

Non-predictions: this does not make `3x+1` reachable by the *string* search, does not compose
families, and does not claim any family is true — a fitted family is still a guess that fits.

## Stop condition

If H1 fails — completeness is not decidable from available state — then the search's budget is
entangled with its results in a way no flag can untangle, and the honest response is to make the
budget an explicit argument of every claim rather than to report a flag.
