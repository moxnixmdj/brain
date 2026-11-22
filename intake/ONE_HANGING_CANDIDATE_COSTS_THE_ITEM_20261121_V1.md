# One hanging candidate costs the item — 10/13 in 29 seconds

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Instruments:** `canonical/tools/shape_and_synonym_v1.py`, `canonical/tools/batched_oracle_v1.py`
**Chain:** … → `THE_RESIDUE_IS_THE_QUESTION` (9/13) → this

---

## 0. The bug that was masquerading as a knowledge limit

Item 198 was solved by the evidence: `squash_matches` put `sympy.ntheory.isprime` at position
3 of the ordered candidates, and that exact body **passes the item's hidden test** when judged
alone. Yet the full run reported `UNSOLVED`.

The cause was not ranking, not vocabulary, and not the oracle's correctness:

```
total bodies: 77
judged in 300.1s
first verdicts: [worker_timeout, worker_timeout, worker_timeout]
```

One candidate — `sympy.ntheory.prime(n)`, which searches for the *n*th prime and does not
return for `n = 4` in a way the test tolerates — consumed the entire item's budget. The worker
was killed, and **every** verdict became `worker_timeout`, including the correct one.

> A single pathological candidate silently destroyed the whole item. The system was not
> failing to find answers. It was failing to *survive* its own search.

## 1. The fix

`signal.alarm` per candidate inside the worker. A candidate that does not return in 5 s is
attributed a `candidate_timeout` **for that candidate only**; the remaining list is still
judged.

The effect is not merely correctness:

| | 9/13 run | after the fix |
|---|---|---|
| item 198 | `UNSOLVED` at 300 s (timeout) | **SOLVED** in 5.7 s |
| 13 held-out items, total wall time | 390 s | **29 s** |
| held-out solved | 9/13 | **10/13** |

**"Insanely fast" and "correct" were the same bug.** Bounding the pathological case made the
system both.

The judge was re-verified after the change: `sympy.totient(n)` → True, `n` → False, `1` → False,
matching pytest.

## 2. Result: 10/13 held-out

```
193  list(sympy.matrices.Matrix(matrix))         0.7s
195  sympy.core.bottom_up(expr, lambda x: x.doit()) 0.8s
197  sympy.external.gmpy.is_square(n)            0.5s
198  sympy.ntheory.isprime(n)                    5.7s
201  sympy.external.gmpy.jacobi(a, n)            0.4s
202  sympy.ntheory.npartitions(n)                0.5s
204  sympy.functions.primepi(n)                  0.4s
205  sympy.functions.totient(n)                  0.4s
206  sympy.functions.mobius(n)                   0.4s
207  sympy.external.gmpy.legendre(a, n)          0.4s
```

Median item time **0.5 s** including process start and the benchmark's own hidden tests.

## 3. The three remaining, classified honestly

- **194 `matrix.todok()`** — the prose says "dictionary-of-keys representation"; the name
  `todok` shares no word with it and is not a compound of two problem words. **Vocabulary.
  No run-time derivation from this text exists.** This is a genuine instance of the
  meaning→name convention.
- **196 `sympy.use(expr, lambda x: x.doit())`** — the symbol `use` *is* in the prose and was
  ranked 3rd. It fails on shape: the prose says "traverses the expression so that every
  subexpression is evaluated", which does not literally contain a lambda phrase, so no shape
  hint fires and only `use(expr)` is tried. **A shape-derivation gap, not a vocabulary gap.**
  Fixable by trying the lambda shape when a ranked symbol is a higher-order combinator —
  not yet done.
- **203 `sympy.primeomega(n)`** — **the benchmark's prose is wrong.** It says "the number of
  *distinct* prime factors". `len(primefactors(n))` satisfies that sentence exactly and fails
  the hidden test; `primeomega` counts *multiplicities* and passes. Any system that reads the
  prose correctly is marked wrong. This item is not solvable by reading, and no mechanism
  should be tuned to pass it.

So the true scoreboard for this sub-cohort is **10 solved, 1 vocabulary, 1 shape gap,
1 benchmark defect.**

## 4. What this changes

The failure taxonomy is now stable and it is not "the ranking is bad":

| class | count | status |
|---|---|---|
| solved from prose + declaration | 10 | done |
| shape-derivation gap | 1 (196) | known fix, not applied |
| meaning→name vocabulary | 1 (194) | **the real remaining limit** |
| benchmark defect | 1 (203) | not ours, must not be tuned for |

`truth.achieved` remains `false`. 10/13 is 77% of a 13-item held-out half of a 26-item sympy
sub-cohort — not a benchmark score, not comparable to the 51–59% frontier figures.
