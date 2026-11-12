# Inputs must be kept before the action

2026-11-12 · authority NONE · no terminal or benchmark credit

## Answer to the owner's claim

One experience can be retained and can sometimes identify a reusable skill **within an existing
hypothesis space**. It does not establish perfect learning in arbitrary environments. The missing
implication is: stored experience → uniquely correct rule → applicable in a new situation → correct
execution. Each arrow can fail. Persistence is not identification, transfer, or correctness.

There is substantive machinery here, not merely plans under unfamiliar names:

- `canonical/runtime/edit_kind_learning_v1.py`: derives edit operators from a before/after example,
  retains multiple abstraction levels, proposes candidates elsewhere. The caller's tests select them.
- `canonical/runtime/environment_learning_v1.py`: observes transitions and finds shortest paths in
  the learned model, bounded by trials and observable states. Shortest in that model does not mean
  shortest in the unknown real environment, nor that hidden state was learned.
- `canonical/runtime/macro_v1.py` and `experience_v1.py`: retain reusable plans and contextual failure
  information. Retention still needs an applicability boundary and current dependencies.
- `canonical/runtime/capability_receipt_lane_v1.py`: records an execution, not its correctness; a
  distinct verifier/run reference is still required for independent verification.

Executed on this checkout: the edit-kind and environment-learning suites have **83 passing tests**.
That supports their tested contracts, not every conceivable task. The existing
`one_example_is_a_point_a_test_is_a_quantifier_probe_20261112.py` also ran: **34** generated candidate
programs, **33** consistent with one demonstration, **6** consistent with three assertions, **27**
matching the demonstration but failing the suite. Even three assertions do not uniquely identify the
program here. This is a finite measured example, not a universal impossibility of one-shot learning:
one example can be sufficient when prior constraints already select the right rule.

No experiment here establishes sentience. Durable memory, self-monitoring, and reusable actions are
engineering properties; none is evidence on its own of subjective experience. 'Most advanced coding
agent on the planet' needs a controlled comparative evaluation, which this round does not perform.

## A real defect, not another exposure campaign

Previous work established that a separate fixture runner can snapshot before editing. Inspection
this round found that the **standard receipt executor still called `snapshot_inputs` after the
adapter returned**. That is causally too late for a mutating action.

New tests invoke `execute_and_receipt` through an actual imported temporary adapter and a declared
registry entry, without mocking the invocation. Before the runtime patch: **6 failed, 1 passed**.

| Case | Before | After |
|---|---|---|
| Adapter overwrites input | Stores changed bytes | Stores consumed pre-edit bytes |
| Adapter deletes input | Input digest missing | Pre-edit bytes retained |
| Adapter creates output | Calls new output an input | Newly created output excluded |
| Adapter fails after deleting input | No saved input | Input retained; still no success receipt |
| Empty probe mutates then fails, declared call deletes | Declared call's input lost | Captures state immediately before declared call |
| Empty-argument success | No input field | Unchanged |

The runtime change wraps each attempted invocation with the existing snapshot helper, rather than
changing the probe signature, inventing a store, or editing old receipts. It captures the declared
fallback's own pre-state, not a state preceding a failed empty probe. The empty-probe side effects
are not rolled back by this patch. Existing files in output-valued arguments are still captured as
file arguments: the helper does not infer semantic input/output roles from names.

After the patch: **71 tests pass** across receipt lane, pre-execution capture, input snapshots,
instance index, and fixture replay. Tests inspect stored bytes and result hashes; observing an
`EXECUTED` flag alone would not catch this bug. No tests were loosened. These are local results,
not a claim that a third-party verifier ran these focused tests.

## What is not fixed

This small fix does not supply an arbitrary environment snapshot, dependency lock, directory
capture, privacy/secret filtering, protection from concurrent file mutation, or automatic restore in
the independent-verification lane. The helper still captures only small, direct string-valued file
arguments. CLI argv and nested/directory inputs remain outside this change. A failed execution may
leave an unreferenced stored blob. Storage is not learning; no learner was updated here.

## Recent research checked, not assumed to be proof

Sources accessed 2026-11-12 (the session date):

- [Continual-ARC, submitted November 10](https://arxiv.org/abs/2611.14505), with
  [code/run records](https://github.com/unifyai/continual-arc). Its abstract distinguishes retained
  seen-task performance from unseen-task generalization, reporting no unseen-task gains from its
  tested harness methods. That is evidence about those methods and tasks, not a ban on memory-based
  learning or an evaluation of Brain.
- [KEEL, October 25](https://arxiv.org/abs/2610.34043): verifier evidence supports, contradicts,
  replaces, or retires skill claims; it reports task-success improvements, not universal mastery.
  The design lesson is to retain the scope and counterevidence with a skill, not merely successes.
- [SWE-bench Pro official repository](https://github.com/scaleapi/SWE-bench_Pro-os), including its
  V2 task directories and fresh-sandbox grading tools. This is a candidate evaluation infrastructure,
  not something we ran or a score we earned. Importing a benchmark scaffold does not supply a solver.

## Fastest defensible route

1. Reuse the current operators, memory, and execution tools; do not rebuild a universal learner.
2. Select a real backlog task with an independently written acceptance test and isolated environment.
3. Preserve the relevant pre-state; execute, then let the acceptance test reject wrong candidates.
4. Retain only supported reusable structure, its applicability conditions, and contrary evidence.
5. Measure **frozen vs learned** on held-out tasks, with equal test/tool/time budgets and restart
   persistence checks. Count accepted successes, regressions, unsafe actions, and time—not files or
   skills stored. Increase coverage only when this comparison shows a gain.

We can start that process now. We cannot honestly conclude that a single successful exposure yields
permanent, perfect advanced SWE or all computer use. This round fixes one concrete prerequisite in
that process; it is not offered as a solution to the entire goal.
