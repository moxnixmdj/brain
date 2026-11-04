# First principles, pass 29: spend the search budget on unresolved behavior

**Date:** 2026-11-04. **Status:** a bounded search improvement measured through local, fixture-supplied experience; not sentience, independent verification, or a general intelligence result.

## The question and the previous failure

A capable adaptive system should not automatically become less useful whenever it remembers something. Pass 28 demonstrated a concrete counterexample: a creature that had learned `Add` reached bounded agreement on a four-addition task, but after a separate locally reviewed multiplication repair it also remembered `Mult`, hit the 256-signature cap, and refused the pending task. The second experience enlarged the space the creature had to consider; discarding `Mult` or pretending that the truncated search was complete would conceal the problem.

The pending fixture had `ref(z) = 5*z`, `target(a,b) = a*b`, and a caller-supplied target of `3*a + 2*b`. Its unchanged external answers were `(2,3) -> 12` and `(-3,11) -> 13`. On pass-28 code, the real `Add`-then-`Mult` experience changed this plan from bounded agreement to `truncated_search` after 464 semantic combinations and 256 retained signatures. Publication was correctly refused.

## What changed and why

When it reports a depth complete, the search has considered the full supplied learned-operator grammar at that depth, not a favored subset. For a possible **first surviving depth**, it streams all child combinations. When the signature store fills, it retains every fitting or unresolved root behavior but can discard root behaviors already contradicted by the current constraints. Once streaming, a known contradiction can be checked on the constraints before computing a whole finite-domain vector. Unknown outcomes are never discarded as contradictions.

This optimization is valid only for a level at which the search stops: refuted root expressions might still be needed as **children** of a deeper expression. If the search discards them and finds no survivor at that depth, it reports `intermediate_signature_budget` and cannot deepen or authorize agreement. If fitting or unknown behaviors exceed the signature budget, or the combination budget runs out, it also reports incomplete search. Counts now identify the retained-signature peak, full-domain combinations, constraint-first refutations, and whether the reported candidate count is only a lower bound.

## Actual experience, unchanged feedback

The end-to-end test uses real locally reviewed board repairs rather than injecting operators into memory. With no code changes during the experiment:

1. A reviewed repair on one task records `Add`. The pending four-addition task receives its own review and the two answers above; it reaches bounded agreement and authors a test.
2. A reviewed repair on another task records `Mult`. The pending source, review, test and answers remain unchanged. The stored old plan is not trusted: locked revalidation recomputes using both operators.
3. Unlike the previous implementation, the new search completes that first surviving depth and the board locally publishes `a + (a + (a + (b + b)))`. Its report remains `verified=False`, `correct=None`. Fixture holdouts `(8,3)`, `(-2,7)`, `(0,10)`, and `(101,-47)` produced `30`, `8`, `20`, and `209`, respectively.

For the `Add`/`Mult` search, production retained at most **256** unique signatures, and finished with **96** retained, across **45** domain points. It processed **1,280** combinations: **472** needed full-domain vectors and **808** were refuted from constraints first. A diagnostic call with a larger, nonproduction limit retained **344** distinct signatures, evaluated all 1,280 combinations over the whole domain, and found the same finite survivor. These are operation counts and bounded representations, not a wall-clock speedup or an estimate of accuracy.

## Falsifiers and safety controls

**Negative transfer remains.** A five-addition fixture, `4*a + 2*b` with `ref(z) = 6*z`, still reaches bounded agreement after real `Add` experience but becomes `truncated_search` after real `Mult` experience. At depth four the search has discarded refuted intermediates that could be needed at depth five; revalidation returns false, the candidate publication gate returns `NOTION_FEEDBACK_STALE`, and the source stays unchanged. The former pass-28 regression was updated to this harder fixture so the stale-plan refusal remains tested while the original four-addition case is separately tested as newly solvable. More experience is still not monotonically helpful under fixed budgets.

**Survivors, exceptions, and unknowns.** Separate syntax enumeration for the specified small grammars matches the streamed survivor vectors: `Add`/`Mult` through four binary nodes, and `Add`/`Div` and `Mod`/`Sub` through three, including exception and signed-zero inputs. In one lower-cap diagnostic, six divergent survivors are retained at a cap of 101; a cap of 100 retains only five and correctly reports truncation rather than agreement. A modeled-unknown candidate remains unresolved; a separate test hits the 4,096-combination budget and also reports incomplete search.

A deterministic 100-case generated-grammar differential compared a 128-signature run with a larger-cap diagnostic: both completed in 93 cases, 45 of those used streaming, and their finite survivor sets and first surviving depths matched. The remaining seven were not compared as complete results. The exhaustive and differential checks share the same arithmetic model, so they cannot reveal every common-mode interpreter error or prove equivalence outside their finite domains.

**The evidence boundary has not moved.** The primary and stress grids are finite; more complex models beyond the first surviving depth remain unexamined. The pass-28 polynomial still agrees on those grids but fails at `(8,3)`. Root numeric comparison is approximate; reviewers, feedback, and local metadata are unauthenticated. A matching direct workspace write followed by the public store call can still create proposal experience without authenticated board publication. Locks remain advisory, the sensitivity probe is not a correctness verifier, and the broker remains `carrier_qualified=False`. These limitations and the legacy retry limitation from the prior report remain.

## Validation on the current tree

- Six focused budget, outcome, reviewed-notion, board, experience and adaptive-search files: **150 passed**.
- Eight broker/operator/board/self-model qualification files in a virtual environment: **79 passed, 17 subtests passed**.
- The same selected nine-file regression as passes 25–28: **22 failed, 47 passed**, with the same 22 failure names. This is not a full-suite result.
- The local repository integrity guard reported **0 violations** against pass-28 commit `a8f4f5e3`; this is not a PR referee result.
- The three already-dirty runtime state JSONs were restored byte-for-byte to their pass-29-entry backups and remain uncommitted. The earlier lost-backup limitation is described in the pass-27 and pass-28 reports.

Focused command:

```sh
PYTHONPATH=. python -m pytest -q -p no:randomly \
  canonical/tests/test_budget_aware_semantic_search_v1.py \
  canonical/tests/test_outcome_aware_notions_v1.py \
  canonical/tests/test_reviewed_notions_and_active_queries_v1.py \
  canonical/tests/test_repair_board_heldout_v1.py \
  canonical/tests/test_experience_composition_v1.py \
  canonical/tests/test_adaptive_counterexample_search_v1.py
```

Fixture authors supplied both the review answers and held-out expectations. `truth.achieved` remains false.
