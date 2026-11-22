# The name is a convention, not a derivation

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Instrument:** `canonical/tools/surface_search_v1.py`
**Predecessor:** `intake/THE_GOAL_IS_AN_ORACLE_NOT_A_SENTENCE_20261121_V1.md` (3/40)

---

## 0. The route under test, and why it was the right one to try

The last receipt ended with the only constraint-legal route: *synthesis over the artifact's
own surface, with the test as the oracle.* Not a description→call table (forbidden: memorised
world knowledge, and merely the frontier's method renamed). So the question became:

> Given a stub with typed parameters and a declared return type, can searching the artifact's
> own vocabulary find the symbol that satisfies the test?

**Answer: no, and the reason is specific enough to close the direction.**

## 1. What the search actually does

Three stages, cheapest first. Measured on the real benchmark:

| stage | mechanism | measured |
|---|---|---|
| **surface** | `dir()` of the alias the stub itself declared (`import networkx as nx` → `nx`) | 928–944 public names |
| **type filter** | call each name with the stub's own parameters in one process; keep those that do not raise and whose return satisfies the **annotation the stub wrote** | 928 → **40** for item 198 |
| **oracle** | run the item's hidden test on survivors | the only judge |

The type filter is a genuine 23× reduction from **stated information** — the stub declares
`-> bool`, so only bool-returning no-argument calls survive. That part works and is honest.

It is also **useless for this problem**, and the measurement says why.

## 2. The measurement that closes it

The filter narrows by **type**, but the item needs a symbol chosen by **purpose**. Those are
different axes. What the filter keeps for item 198 — "determine whether n is prime":

```
kept: are_similar, bottom_up, check_assumptions, comp, doctest, gcd_terms, ...
required: isprime
```

`isprime` is in the kept set only by luck of type. Nothing in the ordering prefers it.

Ranking the required symbol by name-overlap with the problem text, over the full surface:

| item | required symbol | rank / 928 | overlap score |
|---|---|---|---|
| 201 | `jacobi_symbol` | **1** | 2 |
| 207 | `legendre_symbol` | **1** | 2 |
| 206 | `mobius` | 5 | 1 |
| 205 | `totient` | 21 | 1 |
| 198 | `isprime` | **597** | **0** |
| 203 | `primeomega` | **743** | **0** |
| 204 | `primepi` | **743** | **0** |

Two rank first. Three rank near-last with a **zero** overlap score. `isprime` for "determine
if n is prime" scores 0 against the problem's words, because the function is called *isprime*
and the problem says *prime* — and `primeomega`/`primepi` are one character apart from words
the problem never uses.

> **The mapping from meaning to name is a naming convention, not a derivation.** No amount of
> reading the description recovers it, because the description does not contain the string.

### The cost if we simply brute-forced the oracle

One oracle call on item 198 costs **0.97 s**. The required symbol ranks 597th.

```
597 × 0.97 s ≈ 9.6 minutes for one item
37 items at that cost ≈ 5.9 hours
```

Legal, and it would even work. It is also the opposite of "everything must be insanely fast,"
and it degrades as surfaces grow — sympy exposes 928 names, real ecosystems expose millions.

## 3. And some items are not a symbol at all

Three reference bodies were executed to confirm the oracle accepts them:

| item | body | passes | what it is |
|---|---|---|---|
| 199 | `n % p == 0` | True | arithmetic over two parameters |
| 187 | `eq.lhs - eq.rhs` | True | an attribute path on one parameter |
| 191 | `index.free_symbols` | True | a property, not a call |

A surface search cannot produce any of these. They are **expressions over the parameters**, so
the search space would have to be expressions — a program-synthesis space, not a vocabulary.

## 4. The verdict on §3, stated plainly

**True:**
- The oracle is real and discriminating (37/40 no-dependency items).
- Deriving a body from stated declarations works, and its win conditions are understood
  (3/40: closed expressions, annotated constructible types).
- The type filter is a real, cheap, honest reduction (928→40).

**False:**
- "Scan the environment, diff against memory, fetch what is missing" is a complete solution.
  The missing thing here is not a fact to be fetched; it is a **name**, and the name is not
  implied by anything in the environment or the description.
- Surface search closes the gap. It cannot rank by purpose, and some items need an
  expression rather than a symbol.

**Unproven:**
- Expression-level synthesis over typed parameters with the oracle as judge. This is legal
  under every constraint and is *the* remaining route. It has not been attempted.

**The real bottleneck, precisely:**
> An item states a purpose, declares types, and ships an oracle. Reaching the body requires
> either (a) a meaning→name convention table — forbidden as memorised world knowledge — or
> (b) synthesising an expression over the parameters and submitting it to the oracle, where
> the search space is exponential in expression size and the only signal is pass/fail.

## 5. What this does to the constraints

This is the first measurement that puts pressure on a hard constraint from *evidence* rather
than taste, so it is recorded carefully and no constraint is changed.

The zero-knowledge-house rule forbids parameters that are a lookup of memorised world facts.
The measurement above shows that on this benchmark the single largest missing ingredient is
exactly a **convention table**: `meaning → artifact symbol name`. It is not derivable, it is
not in the environment, and it is what the frontier's models carry in their weights.

Two honest responses, and the second is the one to pursue:

1. **Put the convention table in the external store, not the weights.** It is knowledge, it is
   inspectable, it can be added and removed without retraining, and the store is allowed. This
   does not violate the letter of the constraint. It does mean the system's competence depends
   on a store it must acquire from somewhere — and "acquire it from the web at run time" is
   the instant-knowledge claim, which then has to be *measured* rather than assumed.
2. **Synthesise expressions and lean on the oracle.** Legal, no store required, and its cost
   is the thing to measure next.

Neither is done. `truth.achieved` remains `false`.
