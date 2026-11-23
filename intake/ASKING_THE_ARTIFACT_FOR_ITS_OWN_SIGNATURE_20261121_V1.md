# Asking the artifact for its own signature

**Date:** 2026-11-21
**Status:** measured. Three mechanisms, one idea, +8 items, zero regressions.

## The idea, stated once

Every mechanism this turn is the same move: **the environment is asked a question it can answer
about itself**, and the answer is not stored anywhere. Nothing was added to a table, a weight, or
a lookup. The signature is read at the moment the body is built.

## Why, from the measurement

scipy scored **0/34** while 22 of its items have a reference solution that passes. Of those 22,
**15 pass a stub parameter as a keyword**: `gaussian_filter1d(x, radius=radius, sigma=sigma)`.

The grammar was emitting `gaussian_filter1d(x, radius, sigma)` — the right name, the wrong
calling convention. The two are not the same call:

    gaussian_filter1d signature: (input, sigma, axis=-1, order=0, output=None,
                                  mode='reflect', cval=0.0, truncate=4.0, *, radius=None)

The stub parameter named `radius` sat in **position 1**, which is `sigma`. The slot whose name is
`radius` is keyword-only and eighth. Positional order is not derivable from the docstring. Slot
names are, from `inspect.signature`.

## The three mechanisms

| # | mechanism | derived from | effect |
|---|---|---|---|
| 1 | keyword form for a parameter whose slot is not its position | `inspect.signature(callee)` | 15 scipy items were unreachable without it |
| 2 | `return ` prefix when the stub ends in `:` | the stub's own last character | a bare expression under `def f(x):` returns `None` |
| 3 | callables imported from a submodule are candidates | the stub's own `from X import y` line | prose says "a 1D gaussian filter"; the import says `gaussian_filter1d` |

Mechanism 3 matters because it is the general statement of a specific miss: **the prose states
the concept, the artifact's import states the symbol, and neither alone is the body.**

## Result

    before (alias only):  43/193
    after:                51/193 = 26.4%
    delta: +8, 0 regressions
    ceiling:              110/193
    we reach:             46.4% of the ceiling

The eight newly solved, and they are the ones the mechanism predicts:

    110 scipy  return distance.minkowski(u,v,p=p,w=w)
    119 scipy  return dist.moment(order=n)
    120 scipy  return dist.moment(n=n)
    125 scipy  return windows.lanczos(window_size)
    127 scipy  return gaussian_filter1d(x, radius=radius, sigma=sigma)
    129 scipy  return rank_filter(A,rank,size=size,axes=[1,2])
    131 scipy  return percentile_filter(A,percentile=percentile,size=size,axes=[1,2])
    136 scipy  output = np.zeros(A.shape); for i in range(...)

scipy: **0/34 → 6/34.** It was never version drift. Measured earlier: all 22 reference-solvable
scipy items have their truth name in the installed corpus.

## A benchmark defect this surfaced

Item 127's stub is `def apply_gaussian_filter1d(x, radius, sigma):` with **no trailing newline**.
The benchmark splices `starting_code + solution`, so the reference solution's `return` lands on
the same physical line as the `def` — which is why `return ` matters and why a body without it
returns `None`. Our grammar now reads that line ending rather than assuming a layout.

## Not claimed

* 26.4% is the score on the **193 no-dependency items**, in the environment as installed. It is
  not a score on the full 328, and not on "the benchmark" as a whole.
* `truth.achieved` remains **false**. Authority remains **NONE**.
* No model was called. Every answer came from the artifact's own text and signature plus the
  item's own hidden test as the arbiter.
