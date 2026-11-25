# PROVENANCE ROUGHLY DOUBLES COVERAGE — and the first version of this round was a leak that made it look solved
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts; every
> parameter derived and justified; knowledge external, inspectable, removable; project then web; name the
> real limiting factor; kill the idea before building it; verified / unverified / failed; hardest real
> tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. The claim I pre-registered, and what happened to it

Last round: shape-only vocabulary speaks about 7.6% of real code at best. The next lever would be
**provenance** — where values come from, not what the code around them looks like. Pre-registered claim:

> Branch-test provenance determines return behaviour better than structural shape does, at the same
> evidence cost.

Measured on 7,812 trained / 3,679 held-out functions (split by file), equal vocabulary budget of 4:

| arm | predictions | wrong | accuracy | coverage |
|---|---|---|---|---|
| `SHAPE_ONLY` | 211 | 4 | **0.9814** | 0.0574 |
| `PROVENANCE_ONLY` | 20 | 3 | 0.8696 | **0.0054** |
| `BOTH` | **395** | 22 | 0.9472 | **0.1074** |

**The pre-registered claim is refuted.** Provenance alone is the *worst* arm — 0.5% coverage, an order of
magnitude below shape. `provenance_beats_shape_at_equal_budget = false`,
`provenance_lifts_coverage_out_of_single_digits = false`.

What is true is weaker and more useful: **the union roughly doubles coverage** (0.0574 → 0.1074), wins at
every price point (1, 10, 100) under the cost objective, and pays for it with 18 more errors — which is
exactly what the dial from the previous round says should happen. Provenance and shape are not competing
hypotheses; they are complementary terms, and provenance alone is far too sparse to carry anything.

## 2. The leak, because I made it again

The first run of this file reported:

```
SHAPE_ONLY      174 pred, 0 wrong, coverage 0.047
PROVENANCE_ONLY 365 pred, 0 wrong, coverage 0.099
BOTH            692 pred, 0 wrong, coverage 0.188
best at price 1: 3621 pred, 4 wrong, accuracy 0.9989, coverage 0.9842
```

0.984 coverage at 0.9989 accuracy, a 13× jump, and I had it half-written as the breakthrough of the
project. It was the label handed to the predictor. `PROVENANCE_FEATURES` included features computed from
**`Return` nodes** — `RET_ORIGINS_COUNT`, `RET_ORIGINS_*`, `RET_ORIGIN_IS_CALL` — while the target class
*is* a classification of `Return` nodes:

```
RET_ORIGINS_COUNT_0  ≡  "no return statement carries a value"  ≡  NO_RETURN
```

**This is the V14 defect, committed again, four rounds later, by the same person who wrote the retraction.**
V14 was the condition vocabulary drawn from unvisited states. This is the feature vocabulary drawn from the
node type the label is defined on. Different mechanism, identical shape: *something the answer already knows
was handed to the model.*

How it was caught: asking the one question that catches the family — **does any feature read the same node
type the label is computed from?** Not a test, not a review, that question. A test now asks it mechanically:
a function whose only distinguishing feature is its return value must produce an identical provenance
feature set to one with no return at all.

The honest reading: I have now caught this class twice and both times only *after* a number looked too good.
The reflex that would fix it permanently is to distrust a near-perfect fit on principle — a predictor that
nearly equals the label is not good, it is suspicious.

## 3. Two more defects, caught by the tools rather than by me

* **`sweep` minimised errors while the price table minimised cost**, so the two tables could select
  different subsets while both claimed "equal budget". A test now asserts the price-1 winner and the arms
  table report the same prediction count, and that `cost == wrong + refused` exactly at price 1.
* **A tautological assertion**: I wrote `assert ... or True` in a test, which makes the test vacuous. The
  repo's own integrity guard flagged it (`[TAUTOLOGICAL_ASSERTION]`) and failed the commit. It was right;
  the assertion is now a real one.

## 4. Where this leaves the real-code work

| quantity | value |
|---|---|
| held-out real functions | 3,679 |
| best coverage, equal budget 4 | **0.1074** (union) |
| best accuracy at that coverage | 0.9472 |
| coverage before this round | 0.0574 |
| shape features | 9 |
| branch-provenance features | 8 |
| features that read a `Return` node | **0** (asserted) |

Coverage on real code went from 5.7% to 10.7%. That is a doubling and it is still single digits after two
rounds aimed specifically at it. The distance between this and anything resembling computer use is not a
tuning gap; it is the honest measurement of where the representation stands.

## 5. Verified / unverified / failed

**Verified by execution:** the three-arm table at equal budget; the union winning at all three prices; the
leak and its removal (before/after both recorded in the artifact); no feature reads a `Return` node; the two
tables agree on their objective.

**Failed, mine, this round:** the pre-registered provenance claim (alone it is worst); a leak that inflated
coverage to 0.984; two incompatible selection objectives; a tautological test.

**Unverified:** whether richer provenance (dataflow to assignment sites, not just branch-test shape) would
raise coverage further. The sparsity of branch-provenance alone is the reason to doubt it — 20 predictions
from 8 features suggests the relation is too coarse, not that it is the wrong idea.

**Not publishable:** any benchmark row — `docker: command not found`. Nothing here is comparable to the
vendor/SEAL figures the prompt quotes, which are for systems spending real inference compute.

**Audited (re-checked by tool this round):** 25 commits; 4 of 19 prompt identifiers exist as code; 0 of 9
prompt commit hashes resolve; 6 numeric figures unverified. Receipt:
`canonical/verification/AUDIT_THE_PROMPT_CLAIMS_20261124_V1.json`.

## 6. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 343.7 s · 1200 files
```

5 new tests, one of which exists solely to make the leak impossible to repeat in this file. Guard PASS after
the fix (17 rules, 0 violations).

## 7. Next

Two rounds of representation work have moved real-code coverage 5.7% → 10.7%. The measured obstacle is
sparsity: branch-test provenance fires for too few functions to carry coverage alone. The next instrument
should test whether **assignment-site provenance** — the dataflow origin of the values a function returns,
computed through the assignment graph rather than the return node — is dense enough to matter, and it must
be built with the anti-leak rule first: the feature set may not read the node type the label is defined on.
That rule is now a test rather than a resolution.
