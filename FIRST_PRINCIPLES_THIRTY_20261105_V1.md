# First principles, pass 30: remember where to ask, not what to believe

**Date:** 2026-11-05. **Status:** bounded, local behavioral adaptation; not sentience, independent verification, or a general-intelligence result.

## The question

A system that has encountered an unusual input elsewhere should be able to reconsider whether that input matters on a new task. But the old task's answer is not the new task's answer. This pass transfers a few *questions*, never labels or permission to change code.

On pass-29 code, a pending fixture had `ref(z) = 4*z`, a broken `target(a,b) = a*b`, and a caller-defined target of `2*a + 2*b`, plus one when the largest argument is at least 100 and the arguments differ. Its own review and two answers, `(2,3) -> 10` and `(-3,11) -> 16`, produced bounded agreement. A separate, successfully published reviewed repair had previously received `(101,2) -> 103` as an extra example. The pending task's source, review, examples, and learned operator set stayed unchanged; the old planner nevertheless asked nothing and the board published a candidate returning **206** at `(101,2)`, where the fixture expected **207**. For that old-code baseline only, the extra prior example was inserted into the fixture store because the earlier API accepted only active-query answers. The prior repair itself went through the local board.

## What changed

- A feedback-bound repair experience from *different source bytes* may contribute up to four same-arity input locations outside the fixed typed query grids. Frequency across distinct source hashes and then magnitude prioritize this small pool. This is a scheduling heuristic, not learned proof of relevance; copies of the same source do not increase frequency. Retracted or feedback-mismatched experiences stop contributing.
- Selected inputs join the finite semantic domain **before** model behaviors are compressed. After the fixed-grid disagreement checks, an unanswered transferred location requires a fresh caller answer, even if all surviving models predict the same value. Old numeric results and old exception labels are never copied. Unknown outcomes remain unknown. A changed experience is rechecked under the cooperative store lock before test authorship and publication, and new unanswered locations block later recording of repair experience.
- The feedback API and CLI now accept an explicitly attributed additional `example`, not only an answer to the current query. Both routes validate arity, supported outcomes, duplicate typed locations, and a 256-example cap; adding an example invalidates the cached plan. If another answer is needed after the cap, the plan reports `example_budget_exhausted` rather than agreement. Attribution strings do not authenticate the caller, the oracle, or independence.

For example, with a store and finding ID supplied by the board:

```sh
python -m canonical.swe_kernel.notion_feedback_cli_v1 --store STORE example FINDING \
  --args '[101,2]' --expected '103' --reviewer 'reviewer' --basis 'external basis'
```

Run the workspace sensor again after feedback. Predictions are visible to the caller, so the answers are not blinded.

## Measured adaptation without changing code during the experiment

The committed end-to-end tests actually publish a separate reviewed `Add` repair using the new example API. Before and after that experience, the pending task still has the same source, review, two answers, and `Add` operator set. Afterward it asks about `(101,2)`, predicts `206`, and does not copy the old task's `103`. The caller supplies **207** for the pending threshold fixture. Search returns `no_candidates`; no test or repair is published and the source remains unchanged. This is one locally authored fixture, not an accuracy estimate.

In a separate linear fixture with the same old pending test, the old publication gate first refuses `NOTION_FEEDBACK_STALE`. A fresh answer of **206** yields bounded agreement. The ordinary unscoped board then refreshes the unchanged generated test and locally publishes `a + (a + (b + b))`; held-outs `(8,3)`, `(-2,7)`, and `(0,10)` produce `22`, `10`, and `20`. The board reports **`verified=False`, `correct=None`**. Fixture authors supplied the feedback and expected outcomes.

## Typed inputs and evidence diversity

During implementation, the experimental planner treated `(10000000000000000, 1)` and `(1e16, 1.0)` as the same input. It declared agreement without asking about the latter, although on those floats `(a+b)-a` returns `0.0` and `(b+b)-b` returns `1.0`. Input identity now preserves integer versus float and the sign of float zero throughout selection, query matching, plan persistence, and learning checks. The planner now asks the float question and reports both predictions.

Two differently typed spellings of one numeric location can be useful *constraints*, but must not by themselves meet the minimum of two numerically distinct example locations. New tests enforce that rule even against a forged bounded plan or forged experience. The old duplicate-example test was updated to use an exact typed duplicate; separate tests preserve its original evidence-diversity concern. This count does not establish that the examples or their sources are independent. Returned numeric values are still compared approximately; type and signed-zero equality of returned values are not established.

## Guarded test refresh

When new feedback changes a binding, the unscoped sensor may replace an existing generated test only if its registry entry, old header and test hash, sidecar, original source, and non-target scope still match. It records the new origin under the advisory lock before an atomic file replacement. Edited or ordinary tests, missing/changed/symlinked sidecars, mismatched scope or header, contradictory feedback, and changed source are refused. A replacement interrupted after updating the origin leaves a mismatch that blocks publication and requires manual recovery; it is not an all-files durable transaction.

Refresh is limited to recognized registered tests in unscoped sensing. It does not cover arbitrary legacy or unregistered tests, a scoped scan, or the earlier case where unchanged feedback needed an automatic board retry. `READ_ONLY` and `OFF` do not refresh. Registry files, reviewer identity and sidecars are unauthenticated, locks are advisory, and noncooperating writers can race or tamper with metadata. A finite-reference-matching direct write can still be recorded as experience without authenticated board publication.

## Counterexamples and costs

- **A farther blind spot remains.** With an otherwise identical fixture whose threshold is 1000, the creature asks and receives the correct linear answer `206` at `(101,2)`, then publishes a repair reporting `verified=False`, `correct=None`. At the unsupplied holdout `(1001,2)` it returns **2006** while the fixture expects **2007**. Four selected locations cannot establish general correctness.
- **Experience can reduce availability.** A real reviewed subtraction repair can contribute `(1e20,1e20)`, where its answer is `0.0`. On an unchanged pending sum task, both candidate outcomes at that location become model-unknown; the correct external sum `2e20` exceeds the supported numeric outcome limit and cannot be recorded. Publication is refused as stale. Retracting the prior review removes the question and restores the pending bounded plan. Thus more experience is not monotonically useful.
- Extra inputs can consume the finite-domain budget, require unnecessary answers, or expose model unknowns. Search remains limited by the existing six learned binary nodes, 256 retained signatures, 4,096 combinations, and 256 domain points. The previous deeper-search, direct-write provenance, bounded-polynomial, and non-sandbox limitations still apply. The sensitivity probe is not a correctness verifier; the broker remains `carrier_qualified=False`.

## Validation on the current tree

- Seven focused transfer, budget, outcome, reviewed-notion, board, experience, and adaptive-search files: **182 passed** (including 32 new transfer/refresh test cases).
- Eight broker/operator/board/self-model qualification files in the pytest/pytest-subtests virtual environment: **79 passed, 17 subtests passed**.
- The same selected nine-file regression as the preceding passes: **22 failed, 47 passed**, with the same 22 failure names as pass 29. This is not a full-suite measurement.
- The local repository integrity guard reported **0 violations** against pass-29 commit `ae4f5b6a`; this is not a PR referee result.
- The three already-dirty runtime JSONs were restored byte-for-byte to their pass-30-entry backups and remain uncommitted. The older lost-backup limitation described in passes 27–29 remains.

Focused command:

```sh
PYTHONPATH=. python -m pytest -q -p no:randomly \
  canonical/tests/test_experience_challenge_transfer_v1.py \
  canonical/tests/test_budget_aware_semantic_search_v1.py \
  canonical/tests/test_outcome_aware_notions_v1.py \
  canonical/tests/test_reviewed_notions_and_active_queries_v1.py \
  canonical/tests/test_repair_board_heldout_v1.py \
  canonical/tests/test_experience_composition_v1.py \
  canonical/tests/test_adaptive_counterexample_search_v1.py
```

The qualification and regression selections are listed in the preceding reports. `truth.achieved` remains false.
