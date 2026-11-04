# Parameters the data asks for, instead of a menu of twelve

Pre-registered 2026-11-04, **before** implementation. Branch `arena/0d9138ce-brain`, base `4db59c51`.

## The measurement that forced this

Merging main's Kleene arms fixed four defects and exposed a fifth, larger one. At the default
weight bound, `demand_evidence` reports `UNRESOLVED` for four ordinary affine functions, and the
reason it gives is **wrong advice**: it tells the caller to raise `max_weight`.

Measured on `x = 1..5`, `max_bank_size=5000`:

| function | truth | plain, w=3 | with the constant it needs | the constant |
|---|---|---|---|---|
| `3x+1` | 4, 7, 10, 13, 16 | UNRESOLVED | **DETERMINED, 1 explanation** | 3 |
| `2x+7` | 9, 11, 13, 15, 17 | UNRESOLVED | **DETERMINED, 1 explanation** | 7 |
| `x+5` | 6, 7, 8, 9, 10 | UNRESOLVED | PROVISIONAL, 35 | 5 |
| `5x-1` | 4, 9, 14, 19, 24 | UNRESOLVED | PROVISIONAL, 3 | 5 |

Raising the weight bound instead took `3x+1` to weight **5** and found 28 programs, not 1. The
hypothesis did not need a bigger grammar. It needed one number, and the search owned that number's
menu in advance.

This is the **seventh** appearance of the same defect class in this project: a frozen list standing
in for a computation. Round 11 found it in regime predicates, round 12 in vocabulary, round 14 in
rivals; here it is the constant alphabet —

```python
seed_consts = [0, 1, 2, -1, 100, True, False, None, "", [], {}]   # 12 entries, fixed
```

so the system can represent `2x` and `3x` (2 and 1 are on the menu) but not `3x+1`, `x+5`, `5x-1`
or `2x+7`. A creature that cannot name the coefficient the data is asking for will call a solvable
problem unsolvable, and be fluent about it.

Already in the tree and unused by this path: `hypothesis_classes_v1.Affine.fit`, which solves for
exact rational coefficients. The capability existed; nothing consulted it.

## Predictions

Each is a claim about what the *current* code will do, written before I change anything.

**P1 — the menu is the binding constraint, not the weight bound.** For all four functions above,
supplying the single constant `3, 7, 5, 5` respectively makes the answer reachable at `max_weight=3`
while raising `max_weight` to 5 does not reach `DETERMINED` for any of them. *Predicted: pass* — the
table above is the measurement.

**P2 — inventing the constant is at least as good as being handed it.** After the change,
`demand_evidence` with no `extra_constants` on those four functions must reach the same status and
explanation count as the hand-supplied runs (`DETERMINED/1` for `3x+1` and `2x+7`). *Predicted: pass
for the two that were DETERMINED when handed the constant; I predict `x+5` and `5x-1` stay
PROVISIONAL, because a solved coefficient does not by itself collapse the piecewise rivals.*

**P3 — invented parameters must be exact, not floating.** For `3x+1` the recovered coefficient must
compare equal to the exact rational `3`, and for a fit to `1.5x + 0.25` the recovered pair must equal
`(3/2, 1/4)` exactly. A float that is merely close is a different claim. *Predicted: pass.*

**P4 — an invented parameter is verifiable, not trusted.** A parameter is admissible only if the
resulting body reproduces **every** example at the same `_freeze_val` granularity the search uses. A
fit that misses one example must contribute nothing rather than contribute a near-miss. *Predicted:
pass.*

**P5 — this does not make the system overconfident.** On the four functions that were already
reachable (`2x`, `x*x`, `mod 2`, and `relu`), the status and explanation counts must be **unchanged**
by the addition. *Predicted: pass, but this is the one I would most expect to fail, because enlarging
the constant alphabet enlarges `seen_sigs` and can change the bank's composition.*

**P6 — the bad advice goes away.** The `UNRESOLVED` message must stop implying that a heavier body
would help when the true blocker is a nameable constant. When the exact fitter runs and still cannot
fit, the message must say the sweep covered exact affine fits too. *Predicted: pass.*

**P7 — it does not silently become a curve-fitter.** With more examples than an affine line can
carry, the parameter invention must **refuse** rather than add parameters until the data is absorbed.
Specifically `x*x` on 5 points must not be reported as affine-fitted, and the fitter must return a
non-fitting status. *Predicted: pass.*

## Falsifiers

This work is void if any of these hold:

- **F1.** An invented constant changes the status of a case that was already correct. `2x` must not
  move from PROVISIONAL/5 to something else.
- **F2.** A parameter is admitted that fails to reproduce an example under the search's own equality.
- **F3.** The fitter starts absorbing non-affine data by adding degrees of freedom — the round-11/12/14
  DOF failure, fourth time.
- **F4.** Any existing test in the twelve suites changes outcome for a reason other than P2's
  intended improvement. A merge-adjacent refactor that quietly moves other numbers is not a fix.
- **F5.** The recovered coefficient is a float approximation reported as if exact.

## What would count as a genuine gain

Not "more functions solved". The gain is narrower and has to be stated narrowly: **the system stops
reporting a solvable problem as an exhausted ontology, and stops prescribing the wrong remedy.**
`DETERMINED` here still means only that the budget contains one explanation over the observed domain;
it is not truth, and the domain-of-verification module is what says how far it was checked.

## Non-claims, fixed in advance

- Pure Python, small integer/rational tuples. No generalisation claim.
- $0 spend, no external model calls, no neural weights, no dynamic code execution in result-bearing
  modules. Fitted bodies are constructed as source text and compiled by the existing checked path.
- `truth.achieved` stays false. No sentience claim.
- If P5 fails I will record it as a failure rather than tune the suite until it agrees.
