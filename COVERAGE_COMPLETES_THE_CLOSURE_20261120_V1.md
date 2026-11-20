# Coverage completes the closure — 2026-11-20

Authority: `NONE__PRODUCER_RUN_SANDBOX`. No acceptance, capability credit, terminal credit,
independent verification, benchmark score or operating model is claimed. Parameters stored: 0.
Runtime model calls: 0. Transitions predicted: 0; every edge is a real copy-and-execute of git.

## Requirements restated and resolved

1. Build our own weights, architecture and agent. Weights are calculated mechanisms only;
   no world fact or skill is retrieved from them at runtime. There are no runtime calls to any
   other model. Instant knowledge lives outside the model in an inspectable, editable, deletable
   store. A single judged experience may add a skill/closure to that store.
2. Research the project exhaustively (including non-obvious names) and the frontier before building;
   never rebuild an existing mechanism; never treat a paper as evidence of our own capability.
3. Report §3 as true/false/unproven/missing with evidence and name the actual bottleneck.
4. Give one minimal ultimate plan, with rejected ideas and the reason each was rejected.
5. Build, test honestly, repeat the bottleneck loop; §6 "done" only when the system runs on its own
   calculated weights plus the external store with zero model calls and solves the hardest open
   computer-use and software-engineering tasks, including unseen environments and one-shot learning.
   That state has **not** been reached.

§2 contradiction resolution: the forbidden thing is a weight matrix used as a world-fact lookup or a
runtime dependency on another model; the permitted thing is a mechanism that computes over an
external, inspectable/editable knowledge store, with learned skills written by a single judged
experience. This round stores three law names and zero parameters; deleting the store deletes the
knowledge and leaves the mechanism unchanged.

## Project and frontier research

Project routes already present and inspected: `the_branch_is_the_model_v1.py` (execute the branch,
do not predict it), `the_goal_is_a_discriminator_v1.py`, `the_experiment_that_identifies_v1.py`,
`the_counterexample_is_the_next_experiment_v1.py`, `coverage_is_the_bottleneck_not_hypotheses_v1.py`,
and `goal_closure_v1.py` (execute a goal hole, select the smallest preservation-law closure from
judgments). The last receipt reported 0 false accepts on a held-out repository but explicitly
recorded 16 accepted holes in an unjudged rescue class. Therefore closure was sound only within
judged classes: the bottleneck was **coverage**, not a larger law vocabulary or a better planner.

Frontier search (2026): coverage-driven CEGIS/CEGAR assertion generation (NeuroAssertion,
arXiv:2608.18482), compact counterexample clusters (arXiv:2606.11521), SMT/AST abstraction
refinement (NeuroAbs, arXiv:2608.17304), and AutoSpec/PreAct-style guardrail synthesis and
compile-extend-replace loops. All are model-based or model-dependent; they informed the shape of
the audit/refine loop but are not runtime dependencies and contribute no capability evidence.

## §3 verdict

- Replaying an executed action in a fresh copy as the exact successor: **true** (earlier receipts).
- Inferring a permanent goal from one unjudged experience: **false** (earlier and this receipt).
- A hand-written literal goal being equivalent to the judge: **false** (16 accepted holes).
- A law closure transferring to classes that supplied judgments, with zero parameters and zero
  model calls: **true**, bounded to those classes.
- Closure transfer to an unjudged class: **false**, measured before repair (52 accepted held holes).
- A coverage audit finding applicable laws with zero witnessing holes and a minimal one-clause
  goal repair making the class learnable, after refit transferring with 0 false accepts and
  0 false rejects: **true** in this producer run.
- General computer use, GUI/browser competence, hidden benchmark performance, one-shot learning
  in arbitrary environments, understanding/sentience: **unproven/missing**.

## One plan; rejected ideas

Plan: (1) audit each law against judged rows and name applicable laws with no violating row;
(2) construct the missing class by reusing the real git setup algebra, checking whether the literal
goal is contradictory (no satisfying state exists); (3) minimally repair the literal goal by
removing the fewest clauses until holes and legitimate states both appear; (4) refit the smallest
closure over the union of judged and constructed rows; (5) re-test on a different repository and on
planner execution. Stop when every constructed class contributes a discriminating judgment and
both error counts are zero. Store only the resulting law names externally.

Rejected: a larger action vocabulary (the successor is already given by real execution); learned
transition models (the copy is the successor); statistical edge pruning (it previously lost a real
task); hand-writing more clauses (they failed transfer); a model judge or model-generated
demonstrations (forbidden at runtime); claiming benchmark scores from web snippets (not our run).

## Measured result

Tool: `canonical/tools/coverage_completes_the_closure_v1.py`; tests:
`canonical/tests/test_coverage_completes_the_closure_v1.py`; full receipt:
`canonical/verification/COVERAGE_COMPLETES_THE_CLOSURE_20261120_V1.json`; external store:
`canonical/state/COVERAGE_CLOSURE_STORE_20261120_V1.json`.

- Training audit before repair: `target_content_preserve`, `tracking_preserve` and
  `reference_ancestor` UNCONSTRAINED (0 holes); `stash_restore` INAPPLICABLE (0 applicable origins).
- Contradictory classes on the held repo: `stashed_wrong_branch` and `conflict_and_stash`; each was
  repaired by dropping the single `head` clause. `side_untracked` and `side_dirty` were already
  satisfiable and were not changed.
- Held-out before refit: 19 legitimate states, 52 accepted holes, 0 rejected legit states.
- Refit closure: `ref_preserve`, `tracking_preserve`, `stash_restore` (the law already existed in
  the algebra; no new law or parameter was added). After refit: 0 accepted holes, 0 rejected
  legitimate states on the same held repo; 0/0 on the refit training rows.
- Planner: with the old closure and literal goal the planner finds a three-action destructive plan
  (`git_checkout_main`, `git_stash_drop`, `git_clean_fd`); with the refit closure and literal goal
  it finds none; with the refit closure and the one-clause repair it finds a legitimate five-action
  plan (`git_checkout_main`, `git_stash_pop`, `git_clean_fd`, `git_add_all`, `git_commit`).
- Criteria C1–C6 are true in the producer receipt; 12/12 tests pass including the earlier closure
  suite. Run time 390.5s; 0 model calls; 0 stored parameters.

## What is still missing

The judge is supplied, not learned from an unlabelled single experience; setup sequences are
reused; five git classes and two repositories are not an open computer-use benchmark. No GUI,
browser, unseen-tool, multi-application, or real SWE-bench/OSWorld-style evaluation was run; no
independent verifier exists. The next bottleneck is to remove the supplied judge: derive the
judgment from a single observed repair plus the repository's own checks, and then test a class
whose setup sequence and law combination were not present in the construction set. §6 is not met.
