# The twelve-entry menu was deciding which functions exist

Result note, 2026-11-04. Branch `arena/0d9138ce-brain`, base `4db59c51`.
Pre-registration: `PREREG_PARAMETERS_THE_DATA_ASKS_FOR_20261104_V1.md`.

## Score: 6 of 7 predictions, 1 falsified and kept

| prediction | claim | result |
|---|---|---|
| **P1** | the menu, not the weight bound, was binding | **PASS** |
| **P2** | inventing ≈ being handed the constant | **PASS** for `3x+1`, `2x+7`, `x+5`; `5x-1` stayed PROVISIONAL |
| **P3** | recovered parameters are exact rationals | **PASS** — `1.5x+0.25` → `(3/2, 1/4)` |
| **P4** | a parameter missing one example is not admitted | **PASS** |
| **P5** | already-correct cases are unchanged | **FAILED** — `2x` went 5 → 6 explanations |
| **P6** | the wrong advice stops being given | **PASS** |
| **P7** | non-affine data is refused, not absorbed | **PASS** |

### P5 failed, and the failure is the more useful result

I predicted this one was the likeliest to fail, and it did. `2x` moved from 5 explanations to 6. The
newcomer is

```
if ((x - 2) > 2):
    return ((100 / x) / 2)
```

which agrees with `2x` at x = 1..5 and differs at x = 10 (**5.0** vs **20.0**). It is a genuine rival,
not a duplicate — so the old count of 5 was an **undercount**. A larger constant alphabet enumerated
piecewise bodies the twelve-entry menu could not reach.

The consequence matters more than the number: *every* explanation count produced before this change
was computed over a space that excluded ordinary numbers like 3, 5 and 7. The counts were not wrong
by a rounding error; they were counts over a **subset of the representations**, and nothing in the
reports said so. That is the same structural mistake as the truncated bank fixed in the previous
round — a number that looks like a cardinality and is actually a property of the instrument.

## The gain, stated narrowly

`3x+1`, `2x+7` and `x+5` went from **UNRESOLVED** to **DETERMINED** with one explanation, at the same
weight bound. Before the change the system reported these as unrepresented and advised the caller to
search harder — the wrong axis entirely, since the missing item was a number and not an operation.

The affine solver already existed in `hypothesis_classes_v1.Affine.fit`. Nothing consulted it. The
capability was present and unreachable, which is the seventh instance of the same pattern in this
project: **a frozen list standing where a computation belongs.**

## Two instrument bugs found while building it

1. **`_freeze_val` vs behavioural equality.** `compile_body` emits `return 3 * x + 1`, which returns
   `int`. Compared against float targets under `_freeze_val` — which keeps `4` and `4.0` distinct —
   every integer-valued line was rejected. The coefficient was recovered and then discarded by a
   spelling difference. Fixed by comparing through this module's existing `_signature_token`.
2. **`DETERMINED` from a saturated bank, reintroduced.** A larger alphabet fills the bank sooner, so
   a truncated sweep could now terminate on a single explanation that a complete sweep would have
   contradicted. `bank=900` on `2x+1` returned `DETERMINED` with `complete=False`. This is the exact
   defect retracted last round, returning in miniature through a side effect. The certainty branch now
   requires `coverage.complete`, and returns `SEARCH_TRUNCATED` with the budget in `why` otherwise.

The second one is the reason to distrust any fix that enlarges a search space: it re-opens failure
modes that were already closed, and it does so *silently*, because the doors still work.

## Blame, sharpened

`accuse` compared `without_it_programs == prior_programs` to decide which observation broke the model.
That signal went from `[3]` to `[]` while the data was unchanged, because the cheapest admissible body
changed shape. Program counts are not cardinalities on this branch — one representative per behaviour
class — so the test was always weaker than it looked, and the previous `[3]` was luck.

Comparing the restored **commitment** (`prior_chosen`) gives exactly one restorer, and it is the
injected observation. Both signals are now reported, so a regression in the search cannot hide behind
the blame logic.

## Verification

- **273 passed, 178 subtests** across 18 suites, including 13 new tests in
  `test_parameters_the_data_asks_for_v1.py`.
- `repo_integrity_guard_v1`: mode `static+diff`, 17 rules, **0 violations**.
- Module findings: domain-of-verification **7/7**, hypothesis classes **14/14**, vocabulary induction
  **12/12**, discovered tests **10/10**, evidence demand **9/11**, observation refutation **8/9**.
- The three remaining failures are **pre-registered failures from earlier rounds**, kept in the code
  with `pass: False` and a `why`. None was rewritten to match its result.

## Non-claims

- DETERMINED means the budget contained one explanation over the observed domain. It is not truth,
  and `domain_of_verification_v1` is what says how far it was checked.
- Two parameters are spent to invent an affine fit, and the fitter refuses with fewer than two
  distinct inputs. That is a stated degree of freedom, not a discovered one.
- The recovered constants come from a **single-input** affine family. Nothing here claims parameter
  invention for multi-argument bodies.
- `truth.achieved` stays false. $0 spend, no external model calls, no neural weights. No sentience
  claim.
