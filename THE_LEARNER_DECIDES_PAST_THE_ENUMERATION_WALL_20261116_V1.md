# The Learner Decides Past the Enumeration Wall

**Receipt, 2026-11-16. Authority: NONE (measurement + arithmetic only). $0, no models, no weights.**

## The wall, and what this round shipped

`THE_WALL_IS_IN_THE_VOCABULARY_AND_IT_CAN_NOW_BE_PROVED_20261113_V1.md` proved two things in
order: (1) with the fact vocabulary closed to kinds and absence emitted, the separation
obstruction disappears on the real corpus (certificate stops firing), and (2) the obstacle then
moves to combinatorics -- 2^23 = 8,388,608 hypotheses against `learn`'s cap of 12 -- and the
round stopped rather than ship "add negation" as the end of it. Section 4 named the repair:
**compute minimal hitting sets instead of enumerating.** This round ships that repair.

The learner (`canonical/runtime/applicability_v1.py`) now decides every case whose failure side
fits an inclusion-extraction budget, by counting survivors arithmetically instead of listing
them; the selector (`canonical/runtime/contrast_selection_v1.py`) ranks reachable states by
exact per-state counts on the same arithmetic. The enumeration path is untouched below the cap.

## Measured, this round

| Measurement | Value |
| --- | --- |
| Real corpus (4 historical repairs, kind-closed vocabulary) | vocab 31, A = 23, m = 2 failures, D_i = [20, 20] |
| Raw survivors | **8,388,600** = 2^23 − 8 (brute force over all 2^23 subsets: 1.37 s, agrees exactly) |
| Inclusion-extraction count (2^2 terms) | 0.000 s, same number |
| `learn` verdict (was BOUNDED) | **AMBIGUOUS**, `survivor_count = 8,388,600`, G = lex-first singleton (20 candidates), S = A (23), list = () (over `LIST_MAX = 100_000`) |
| Selector on the same evidence | `NO_INFORMATIVE_STATE` with `survivors_before = 8,388,600` — every state already observed gives every survivor the same answer (exact, not sampled) |
| Separable 21-fact case (was BOUNDED) | AMBIGUOUS, count 2^20, G = (x,) |
| Inseparable 20-fact case (was BOUNDED) | INCONSISTENT, count 0; certificate independently says separation-impossible — both instruments agree |
| Exhaustive IE vs brute force | every universe ≤ 4 and every exclusion family of size ≤ 3 (5,058 families): exact equality |
| Seeded learn vs brute force past the cap | 120 trials, |A| ∈ {13..16}: status, count, required, G, S, and full list all identical |
| Selector arithmetic vs list path | 120 forced small cases: identical status/state/counts/gain-terms/discriminating |
| Budget | IE_MAX_LOG2 = 18 (262,144 terms ≈ 0.3 s measured worst case); LIST_MAX = 100,000; SEARCH_MAX = 2^20 visits |
| Consumer battery this round | **272 passed** (13 applicability/contrast consumers + scope gate + ledger + settlement + world probe) + 82 passed (refusal/causal/compression/admission) |
| New suite | `test_the_learner_decides_past_the_enumeration_wall_v1.py`: 11 tests, all pass |

## The design in one paragraph

A survivor is a subset C of A (the facts every success shares) not contained in any failure;
writing D_i = A \ F_i, C survives iff C hits every D_i. Counting those by inclusion-extraction
over the D_i costs 2^m terms where m = failure rows -- and chosen questions keep m small. Under
the stated budgets the learner reports the exact status (`IDENTIFIED`/`AMBIGUOUS`/
`INCONSISTENT`) with exact `survivor_count`, the lex-first least-demanding G (size-ordered
search, no full listing), and S = A; the survivor list is materialised only when it fits
`LIST_MAX`, and when entailment makes raw survivors non-distinct the learner lists and reduces
within budget instead of trusting the raw count. `BOUNDED` remains only when neither axis fits
(m > 18, or canon-active with count > LIST_MAX, or search over budget) -- a refusal about
compute, never about a decidable case -- and a BOUNDED boundary still never withholds
(`explains_failure` guard pinned against the over-budget case).

## Honest boundaries

- `survivors` on a scale-bound AMBIGUOUS boundary is `()`; the count is exact. Query selection
  at scale reads the count and splits by arithmetic; the `skill_scope_ledger` guard treats an
  empty list as "nothing to split", which is truthful when no split exists and priced when one
  does (all `buy_scope` victims remain small-A, on the list path).
- `explains_failure` and licensing stay as they were: exactness here removes a compute refusal,
  never an epistemic one.
- The pinned certificate tests were rewritten, not weakened: where the certificate used to be
  the only decider past the cap, the learner now reaches the same verdict by a different
  method, and both directions (separable / inseparable) are asserted.

## Files

- `canonical/runtime/applicability_v1.py` — `count_survivors`, `_least_demanding_survivor`,
  `_list_survivors`, `_reduces_identically`, `_success_intersection`; exact branch in `learn`
  and `candidate_requirements`; module COST and `Boundary.survivors` docs updated.
- `canonical/runtime/contrast_selection_v1.py` — `_select_from_arithmetic` +
  `_discriminating_from_arithmetic`, routed when |A| > 12 and reduction is identity.
- `canonical/tests/test_the_learner_decides_past_the_enumeration_wall_v1.py` — new suite.
- `canonical/tests/test_insufficiency_witness_v1.py` — two wall tests re-pinned to the decided
  outcomes (with the wall round's authorization quoted in-test).
- `canonical/tests/test_a_failure_is_a_context_not_a_ban_v1.py` — guard split into
  decidable-beyond-cap (AMBIGUOUS 63, sound refusal) and genuine over-budget BOUNDED
  (never withholds).
