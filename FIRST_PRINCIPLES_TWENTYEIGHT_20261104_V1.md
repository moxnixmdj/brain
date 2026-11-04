# First principles, pass 28: reason about what happens when an expression fails

**Date:** 2026-11-04. **Status:** bounded, locally evaluated adaptation and evidence-handling changes; not sentience, independent verification, or a general intelligence measurement.

## The defect

The previous search compared candidate expressions only where all returned numbers. That silently discarded precisely the inputs at which one expression returned a value and another raised an exception. We reproduced a consequential failure in the real reviewed-repair board path:

```python
def unit(x):
    return x * x / x

def combine(a, b):
    return a + b
```

A fixture specified `combine(a,b) = a*b/b`, reviewed `unit` as the reference, and provided the two nonzero answers `(2,3) -> 2.0` and `(-3,11) -> -3.0`. The old planner declared bounded agreement among three expressions and the board locally published `a*a/a`. This was wrong on two fixture holdouts: at `(0,3)` it raised `ZeroDivisionError` instead of returning `0.0`; at `(3,0)` it returned `3.0` instead of raising. The board's own report was `verified=False`, `correct=None`.

The root issue is not a division-specific repair. A model of an action's consequences must distinguish a known value, a known exception, and *not knowing*. Otherwise absence of a modeled value can be mistaken for agreement or for a refutation.

## Observed behavior after the change

With the **same source, review, and initial two answers**, the outcome-aware planner now asks about `(0,11)`. Its surviving hypotheses predict `0.0` versus `ZeroDivisionError`. Two separate fixture runs give different external answers, without changing the code between them:

| Supplied answer | Locally published expression | Four fresh fixture holdouts |
| --- | --- | --- |
| `0.0` | `a*b/b` | matched the fixture's values and exceptions |
| `{"raises":"ZeroDivisionError"}` | `a*a/a` | matched the other fixture's values and exceptions |

The holdouts were `(0,3)`, `(3,0)`, `(-4,3)`, and `(7,-2)`, separate from the supplied answers. The fixtures authored both the feedback and expectations; this is not blinded or independent verification and is not an accuracy estimate. With no additional answer, the real board neither authors the reviewed test nor publishes a repair. The committed end-to-end tests reproduce both branches.

The bounded interpreter now distinguishes primitive numeric outcomes, modeled built-in `ZeroDivisionError` or `OverflowError`, and unknown outcomes from unsupported operations or model limits. Unknown is neither an exception prediction nor a false contradiction. Known contradictions may refute a hypothesis; an unresolved unknown or truncated search cannot authorize bounded agreement or deeper search as if refutation were complete. Queries may expose exception predictions or identify model-unknown inputs, but the caller must supply the answer. Authored exception tests use standard-library syntax and check the exact exception type. Numeric root comparisons remain approximate; return type and signed-zero distinctions are not established by the agreement gate.

## Experience can also make search worse

The previous pass showed that a reviewed `Add` repair could expand a later search. This pass tests the opposite direction with actual stored experience, without changing code. A pending four-addition task initially reached bounded agreement with learned `Add`: 20 finite-behavior representatives and 85 combinations. The creature then locally repaired a different multiplication task and recorded `Mult`. Rechecking the pending task with the current `Add` and `Mult` experience hit the 256-signature cap after 464 combinations; the new plan was `truncated_search`. The previously authored test's cached agreement was refused at publication and the original module remained unchanged.

This is negative transfer under a fixed search budget, not a claim that remembering multiplication is intrinsically harmful. The planner still lacks a learned resource allocation or reliable way to choose a useful subgrammar. More experience is not monotonically beneficial. Six binary nodes, 256 signatures, 4,096 combinations and 256 semantic-compression domain points remain the relevant ceilings; deeper-than-first-surviving models can be unexamined.

## Evidence and publication boundaries

**Stale and forged plans.** An old plan could previously authorize authoring and publication even though its agreement ignored exception behavior; simply adding a current version marker could also forge that authorization. The board and authoring path now recompute the plan from the current original workspace bytes, observations, feedback and learned operators under a cooperative store lock. A marker by itself is not sufficient. The tested stale and forged cases now refuse. This is local consistency checking, not authenticated reviewer identity, evidence independence, hostile-writer safety, or a qualified sandbox.

**A candidate outside the modeled consensus.** Even after re-planning, a manually supplied `a + 0*b` candidate passed the examples and the input-sensitivity probe while disagreeing with the consensus at `(3,0)`. Publication now also compares the candidate's modeled outcomes against a recomputed representative survivor on both finite grids and the supplied examples. The tested candidate is refused with `NOTION_CANDIDATE_DISAGREES`; a consensus-matching candidate passes. The probe still measures sensitivity, not correctness. A correct candidate can be refused when the incomplete model consensus is wrong.

**Learning without publication.** A direct workspace write followed by `record_checked_repair()` could record `Add` and `Mult` from that rejected candidate. A newly authored origin now retains the model's finite outcome reference; recording structural experience rechecks the candidate against it. The reproduced off-consensus write now returns `candidate_outcome_mismatch` and learns no operators. Old origin records without the new reference cannot create new experience through this path; earlier experiences are not retroactively requalified. Publication rechecks the current plan, whereas experience additionally checks the reference saved at authorship, so changed consensus can conservatively prevent learning even if publication succeeded.

This does **not** authenticate publication. A direct write of the matching `a*b/b`, followed by the same public store call, still records `Div` and `Mult` for proposals without the board or an independent verifier. Local metadata can be altered, locks are advisory, and noncooperating writes can race. A matching finite reference is consistency evidence, not provenance.

**Old authored tests and retry.** A legacy authored test that needs an additional answer becomes feedback-hash stale; it is not automatically replaced. In a separate case with enough unchanged feedback, recomputing a current bounded plan allowed the direct publication gate to pass, but the ordinary board did not automatically retry that previously blocked task. These are migration and availability limitations, not proof that legacy tasks are repaired automatically.

## A falsifier of bounded agreement

The two finite grids use first-argument values `2,3,4,5,6,7,-3,0,11`. A supported, nonbranching expression can add the product of `(a - n)` over those nine values to `a*b/b`. That polynomial is zero on both grids and on the supplied examples, so it passes the new candidate-consensus check. At `(8,3)` it returns `-190072` while the fixture expects `8`. Finite-grid consistency cannot establish a general specification, even when every modeled point is known. Reviewer and basis strings are caller-provided and unauthenticated, and model predictions are visible to the caller.

## Validation on the current tree

- Five focused outcome, reviewed-notion, board, experience and adaptive-search files: **139 passed**.
- Eight broker/operator/board/self-model qualification files in a virtual environment with real `pytest` and `pytest-subtests`: **79 passed, 17 subtests passed**.
- The same selected nine-file regression as passes 25–27: **22 failed, 47 passed**, with exactly the same 22 failure names as pass 25. This is not a full-suite result; the names and selection are listed in the preceding reports.
- The local repository integrity guard reported **0 violations** against pass-27 commit `119e2fe6`; this is not a PR referee result.
- The sandbox was reinitialized during this pass. The actual pytest dependencies were reinstalled both in the test venv and for the broker's system Python, and the tests above were rerun on the current tree.
- Three runtime state JSONs were already dirty at pass-28 entry. Validation changes were restored byte-for-byte to the pass-28-entry backups and those files remain uncommitted. Backups from before pass 27's earlier sandbox reset had already been lost, so the exact pre-validation contents from that earlier point cannot be reconstructed.

Focused command:

```sh
PYTHONPATH=. python -m pytest -q -p no:randomly \
  canonical/tests/test_outcome_aware_notions_v1.py \
  canonical/tests/test_reviewed_notions_and_active_queries_v1.py \
  canonical/tests/test_repair_board_heldout_v1.py \
  canonical/tests/test_experience_composition_v1.py \
  canonical/tests/test_adaptive_counterexample_search_v1.py
```

The other test selections are in the preceding reports. The broker remains `carrier_qualified=False`; no claim here covers arbitrary hostile workspaces, all autonomous paths, or general semantic correctness. `truth.achieved` remains false.
