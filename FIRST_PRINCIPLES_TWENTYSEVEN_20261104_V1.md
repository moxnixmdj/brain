# First principles, pass 27: search that expands after refutation

**Date:** 2026-11-04. **Status:** bounded, locally evaluated program search and evidence-handling improvements; not sentience, independent verification, or a general measure of intelligence.

## Why this pass

In pass 26, a creature could reuse an observed `Add` operator, but the learned grammar was fixed at two binary nodes. After a genuine reviewed `Add` repair, the task `ref(z)=4*z`, `target(a,b)=a*b`, with a fixture specification `2*a+2*b`, still returned `no_candidates`: the required composition has three additions. This was a representational limit, not evidence that the task was impossible.

The new search first checks the complete, bounded shallow grammar. Only if every explored shallow candidate is refuted by the current observations does it try a deeper grammar. It stops at the first depth with survivors and reports the depth, coverage and remaining unexamined complexity. An incomplete shallow search is **not** a refutation and does not trigger deeper search.

To avoid enumerating many syntactically different expressions, deeper search groups expressions by their exact, typed outputs on the finite primary grid, stress grid, and all supplied example inputs. It retains a minimum-size representative for each observed behavior and composes those representatives. Integer/float types, signed zero and undefined results remain distinct. This is a finite-domain equivalence, not a claim that the expressions are equivalent elsewhere.

## What actually changed in behavior

The end-to-end tests use the same creature root and code before and after experience:

1. The cold creature reviews an unresolved two-input task and receives one fixture answer; it returns `no_candidates` and authors no test.
2. On a different task, the board locally checks and publishes `pair(x,y)=x+y`, recording the observed `Add` operator.
3. The original task is reopened with its existing review and answer unchanged. The creature deepens the search, asks for a second answer, and only then authors and screens a test. The board publishes a single-file candidate and reports `verified=False`, `correct=None`.

The real board path does this for both `2*a+2*b` (three additions) and `3*a+2*b` (four additions). For the latter, it produced `a + (a + (a + (b + b)))`; the fixture checked `(8,3)`, `(-2,7)`, `(0,10)` and `(101,-47)` after publication. These are fixture-authored holdouts, not an independent verifier or a representative accuracy benchmark. A separate planner test exercises a five-addition composition; the existing end-to-end subtraction-experience control also still passes.

For the four-addition example, the learned search reached depth 4 with 20 finite-behavior representatives and 85 operator-pair combinations on 45 domain points. The unrestricted syntactic enumeration for `Add` and two parameters contains 548 trees at depths 1–4, exceeding the old 256-candidate cap. Those are different counts, not a wall-clock speed comparison. Small exhaustive checks compare the resulting finite-domain behaviors against syntax enumeration for `Add`, `Sub`, `Mult`, and `FloorDiv` combinations through depth 3.

## Limits and falsifiers

- The ceiling is six learned binary nodes, 256 candidate behaviors, 4,096 semantic combinations and 256 domain points. The grammar contains no newly invented constants or branches. A seven-addition fixture still returns `no_candidates`, meaning only that no explored model fit. A partial level is reported as `truncated_search` and cannot justify bounded agreement.
- More remembered operators can hurt search under the cap: on the same two-input task, `Add` alone reaches bounded agreement, while `Add`, `Div` and `Pow` together exhaust the behavioral budget and abstain. The system does not yet learn which subgrammar to trust or allocate resources optimally.
- A fixture whose behavior changes only at inputs of 100 or more still agrees on the finite grid and defeats a surviving candidate at `(101,2)`. Compressed representations can also differ outside their common finite domain. Search agreement does not establish intent.
- Expansion changes hypotheses, not authority. Each later task still needs its own review and distinct answers. Review and attribution strings are caller-supplied and unauthenticated; the broker and sensitivity probe are not independently qualified.

## Evidence-boundary defects found and addressed

**Duplicated answers.** Corrupting a store to contain the same answer twice previously produced `bounded_agreement` and authored a test despite only one distinct input. The planner now rejects duplicate, malformed, non-finite or out-of-budget examples. Authorship and publication also revalidate distinct inputs and nonempty attribution, even if a plan record is forged. Attribution is still not authentication.

**Unpublished candidate.** Previously, calling `record_checked_repair` with a fitting candidate could record an operator while the workspace still contained the broken source. It now requires the current workspace bytes to match the candidate, and rechecks the recorded test, feedback and a fingerprint of all source bytes outside the target expression. Old authored-test origins lacking that fingerprint cannot create new structural experience through this path; previously stored experiences are not retroactively requalified.

This is still a local consistency check, not proof of publication. A direct workspace write followed by an explicit store call can satisfy it without going through the board or a sensitivity check. The metadata and lock are unauthenticated, noncooperating writes can race, and no independent reviewer is established. The board itself calls the method after its local publication checks, but the public store API cannot prove that provenance.

## Validation and workspace state

- Focused notion, board, experience and adaptive-search suites: **107 passed**.
- Eight broker/operator/board/self-model files in a pytest/pytest-subtests virtual environment: **79 passed, 17 subtests passed**.
- The same selected nine-file regression as pass 26: **22 failed, 47 passed**, with the same 22 failure names. This is not a full-suite result.
- The local repository integrity guard reported **0 violations** against pass-26 commit `971770f1`; this is not a PR referee result.
- The sandbox was reinitialized during this pass. In the new sandbox, the confined runner's system Python initially lacked pytest, and a targeted board test failed for that dependency. After installing the actual pytest dependencies in the sandbox and rerunning, both end-to-end cases and the counts above passed as reported.
- Three runtime state JSON files were already dirty. Validation can update them, and their pre-pass external backups did not survive the sandbox reinitialization; the exact earlier contents cannot be reconstructed. They remain uncommitted. Subsequent validation changes were restored to the values present immediately after reinitialization.

Focused command:

```sh
PYTHONPATH=. python -m pytest -q -p no:randomly \
  canonical/tests/test_reviewed_notions_and_active_queries_v1.py \
  canonical/tests/test_repair_board_heldout_v1.py \
  canonical/tests/test_experience_composition_v1.py \
  canonical/tests/test_adaptive_counterexample_search_v1.py
```

The other test selections are listed in the pass-26 report. All tests above ran on the current working tree, not on historical source copies.
