# First principles, pass 26: experience changes a later search

**Date:** 2026-11-04. **Status:** a bounded, locally tested adaptation; not a claim of sentience, independently verified correctness, or general intelligence.

## The question

The previous pass could ask for a review and discriminate among expressions already represented by the current source. It could not, in general, use a locally checked repair to enlarge the expression space on a later task. This pass tests that capability in the actual board path: does an experience alter what a later creature can propose, without a code change or a new hard-coded repair for that case?

A question, a remembered operator, and a score remain proposals. The creature still needs a review, a chosen reference and separately supplied examples for the later task. These are caller claims, not authenticated independent verification.

## Measured transfer

The reproducible end-to-end assertions are in `canonical/tests/test_experience_composition_v1.py`. In one run:

1. A fresh creature saw `diagonal(q) = 3*q` and `bundle(a,b,c) = a*b*c`. A fixture confirmed the relation, chose `diagonal` as reference, and answered the creature's two queries using a sum specification. The cold planner returned `no_candidates`; no notion test was authored and the module stayed unchanged.
2. Another creature, with a fresh store, reviewed a different task, `narrow(t) = t+t` and `pair(x,y) = x*y`. After its fixture supplied two answers, the real board locally checked and published `pair(x,y) = x+y`. Only then did it record the observed `Add` primitive, alongside source, candidate and feedback hashes.
3. Without changing the code, that creature encountered the first three-input task. Before its own review it still authored no test. After its own review and two fixture answers, the enlarged search reached bounded agreement among 12 sums, and the board locally published `a + (b + c)`. The plan evaluated 211 new primary-grid and 26 stress-grid points where all surviving models were defined. The resulting function also matched the fixture on three inputs not used as answers: `(8,3,5)`, `(-2,7,4)`, and `(0,10,-4)`.

The cold and warm planners chose different questions, so that comparison alone is not a controlled same-evidence experiment. A separate end-to-end test first leaves the three-input task unresolved, then obtains the training experience elsewhere, and reopens the original task using its **unchanged review and answers**; it then reaches bounded agreement and publishes a locally checked candidate. That is the stronger demonstration that experience changed the search.

Other controls cover a new weighted two-`Add` expression, a separately trained `Sub` primitive transferring to a three-input subtraction task, and an unrelated product specification after `Add` experience. The product example is not forced to become addition. Five hand-selected held-out planner compositions went from cold `no_candidates` to warm bounded agreement; their displayed candidate expressions were checked against two held-out inputs each. These are curated fixture cases, not an estimate of general accuracy. The fixture author supplied both the review answers and the held-out expectations; there was no independent verifier.

## What changed

- The restricted numeric AST search can compose supported binary operators actually observed in a locally checked, reviewed, published repair. It enumerates expressions rather than mapping particular error classes to a repair. The current learned-composition budget is two binary nodes, with a 256-candidate cap and bounded attempts.
- Future tasks still need their own current review and examples. Source hashes, review and example hashes, and candidate hashes scope the stored observation. Retracting or changing the source feedback causes its operators to stop contributing to proposals; the historical record is not necessarily deleted.
- The planner asks discriminating questions, then also challenges agreement on a small negative/zero/out-of-range stress grid. It reports explored coverage, incomplete search and `no_candidates` rather than treating absence of a model as proof.
- The board checks a candidate in a private stage and publishes only a single target file after source, test and feedback checks. Multi-file proposals are refused; this is not a general multi-file transaction.
- The repair board's self-model now uses `strong_verifier=False` and `grounding_complete=False` for these repairs. Its reported probability and surprise are heuristic local telemetry, not calibrated correctness. It neither enters nor settles these repair predictions in the independent calibration ledger. Older ledger entries are not retroactively corrected.

## Falsifiers and remaining boundaries

**Finite evidence is not a specification.** The primary grid uses values 2 through 7; the stress grid uses -3, 0 and 11. Only jointly defined points are compared. A fixture specification that differs from ordinary addition above 10 is caught by a stress query, but another that differs only at 100 or above still produces bounded agreement and fails at `(101,2,3)`. A three-addition specification exceeds the two-node budget and returns `no_candidates`. A truncated learned grammar cannot claim bounded agreement. These are expected limitations, not proofs of generalization.

**Revocation and provenance.** A reproduced defect allowed a previously authored test to publish a repair after its review was retracted. The publication path now rechecks the current feedback hash and reconstructed test content, holding a cooperative read lock through publication. Removing the generated-test header was a second reproduced bypass. Newly authored tests now have both a local origin registry entry and a workspace `.<test-name>.brain-origin` sidecar; header removal is refused with memory both on and `OFF`. A symlink alias is resolved before checking the sidecar. Malformed registered origins, a missing feedback store, or a missing read-only lock fail closed. Ordinary user tests can still be considered without a notion store in `READ_WRITE`, `READ_ONLY`, and `OFF` modes.

These safeguards are not authentication. Removing or copying around the available metadata, including making a separate unmarked copy under `OFF`, can defeat provenance; legacy unregistered tests lack the new protections. The lock is advisory and assumes cooperating writers and a stable lock file. It does not protect against hostile or noncooperating writers. An interrupted authoring operation may leave an orphan origin/sidecar requiring attention. A successful `READ_ONLY` repair does not record new structural experience.

**Trial learning.** A rejected reviewed candidate previously still wrote `* -> +` into old habit memory and updated other legacy repair stores before the board refused publication. The board now seeds a disposable repair-memory snapshot from prior JSON/SQLite memory, uses private learner instances, and discards those trial writes whether the candidate is accepted or rejected. A regression checks that the real legacy files and the five process-wide learner instance references do not change on that rejection. This trades away legacy trial learning on successful board repairs too; the new reviewed structural observation is recorded separately after publication. Direct uses of the older daemon outside this board path are not covered by that isolation claim.

**Probe integrity and coverage.** The input-sensitivity probe now accepts only a conservative syntax subset and binds the inspected source bytes into the confined stage. It declines frame introspection, unsafe builtin laundering and definition-time hooks rather than executing them in its own verifier namespace. It also declines benign programs outside the subset, such as one importing `math`; this is a coverage loss. A constant boolean result previously reported `generalizes=True` while also saying its sensitivity was unprobed. It now abstains when the two perturbed boolean outputs are equal, and accepts sensitivity only when they differ. Even a responsive result is not a correctness proof. The namespace broker remains `carrier_qualified=False`; neither this syntax gate nor a local test is a certified hostile-code sandbox.

The broader, older autonomous paths may have their own evidence and learning semantics. This pass establishes the behavior of the measured reviewed-repair board path, not a blanket guarantee about every path in the repository.

## Validation on the current tree

- Focused reviewed-notion, held-out board and experience suites: **83 passed**.
- Eight broker, operator, board and self-model qualification files in a separate Python virtual environment with `pytest-subtests`: **79 passed, 17 subtests passed**.
- The same selected nine-file regression used in pass 25: **22 failed, 47 passed**. The 22 failing test names are identical to pass 25; this is not a full-suite result.
- Five trials of 16 concurrent cooperative notion-store writers retained **16/16** findings in each trial, versus **3, 4, 5, 1, 3** before serialization in the earlier measurement. This does not establish behavior under noncooperating writers or all filesystems.
- The local repository integrity guard reported **0 violations** with `--base fa90dd5f` (the previous pass), not a PR referee result.

Focused command:

```sh
PYTHONPATH=. python3 -m pytest -q \
  canonical/tests/test_reviewed_notions_and_active_queries_v1.py \
  canonical/tests/test_repair_board_heldout_v1.py \
  canonical/tests/test_experience_composition_v1.py
```

The nine-file regression command was:

```sh
PYTHONPATH=. python3 -m pytest -q -p no:randomly \
  canonical/tests/test_four_wave_optimal_plan_v1.py \
  canonical/tests/test_optimal_four_phase_awake_mastery_v1.py \
  canonical/tests/test_optimal_unified_creature_and_prc2_v1.py \
  canonical/tests/test_post_066e8df_workspace_speed_and_r2_scientific_fabric_v1.py \
  canonical/tests/test_self_expanding_awake_organism_v1.py \
  canonical/tests/test_sentient_cognitive_core_v1.py \
  canonical/tests/test_unattended_inspector_investigation_v1.py \
  canonical/tests/test_unified_awake_cognitive_fabric_v1.py \
  canonical/tests/test_zero_llm_awake_mastery_upgrades_v1.py
```

The eight qualification files are listed in the preceding pass report; the new tests run against the current tree. `python -m canonical.swe_kernel.notion_feedback_cli_v1 --help` describes the feedback interface. Reviewers must assess their own evidence; their labels are not authenticated by the tool.
