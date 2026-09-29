# TRUTH-FIRST AND NO-DUPLICATE-EXECUTION LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Purpose: prevent stale summaries, missing-artifact confusion, duplicate experiments, and locally sensible but globally obsolete work from consuming wall-clock time or corrupting Project Brain state.

## 1. Primary-state refresh before planning
Before any consequential plan or action, the agent MUST refresh the highest-authority live canonical state directly from the control plane.

At minimum, read:
- canonical/CANONICAL_POINTER.json;
- the current frontier/task state relevant to the mission;
- the predicate/evidence record for any capability the plan intends to prove, repair, or rerun.

Memory, prior chat summaries, handoffs, and local cached state are advisory only. They MUST NOT define the current frontier when a fresher canonical source is available.

## 2. Canonical generation lock
Every consequential action MUST bind to the canonical generation or commit observed immediately before execution.

If the canonical generation, frontier, or relevant task/predicate state changes before the action commits:
- ABORT the stale action;
- refresh canonical state;
- recompute necessity;
- proceed only if the action is still required.

No agent may continue executing a plan merely because it was valid at the start of the chat.

## 3. Existing-work search before creation or rerun
Before creating a new experiment, benchmark, qualification mission, recovery path, infrastructure component, or proof artifact, the agent MUST search canonical state for:
- an already-completed task;
- an already-proven predicate;
- an existing exact artifact;
- an existing equivalent artifact;
- a newer superseding result;
- a distinct verifier receipt;
- preserved raw evidence sufficient for reconstruction.

If an adequate prior result exists, new execution is prohibited unless a concrete invalidation is documented.

## 4. Missing proof is not missing capability
A missing file, broken reference, unavailable mirror, lost receipt, or stale pointer MUST NOT be interpreted as evidence that the underlying capability is unproven.

When canonical state says a predicate was proven but referenced evidence is unavailable, classify the blocker as EVIDENCE_RECOVERY unless contradictory evidence shows the capability itself must be re-proved.

The agent MUST NOT rerun the capability experiment merely to replace a missing artifact.

## 5. Mandatory recovery ladder
For missing evidence or uncertain historical completion, use this exact order:
1. recover the exact original artifact;
2. recover an exact mirror/archive/copy;
3. reconstruct the proof from preserved primary evidence;
4. re-adjudicate preserved evidence with an independent verifier;
5. re-prove only the specific missing predicate;
6. rerun the full experiment only as a last resort.

Skipping to a lower step is NON-COMPLIANT unless every higher step has been falsified.

## 6. Frontier contradiction abort
If the planned action assumes a predicate/task is unproven, READY, blocked, or missing while canonical state marks it PROVEN, COMPLETE, SUPERSEDED, or otherwise closed, execution MUST ABORT and reconcile.

Similarly, if a summary says work remains but canonical state says it is complete, canonical state wins unless independently falsified.

## 7. Necessity proof for consequential actions
Every consequential action MUST have a short necessity record answering:
- What exact currently unproven predicate or causal blocker does this address?
- What canonical evidence proves this remains unresolved now?
- What prior work was checked to avoid duplication?
- Why is this the highest remaining step in the recovery ladder?

If these answers cannot be grounded in current canonical state, the action MUST NOT execute.

## 8. Evidence-presence classification
Before rerunning work, classify the situation as exactly one of:
- CAPABILITY_UNPROVEN;
- CAPABILITY_FAILED;
- CAPABILITY_PROVEN_EVIDENCE_PRESENT;
- CAPABILITY_PROVEN_EVIDENCE_MISSING;
- HISTORICAL_STATE_UNCERTAIN;
- SUPERSEDED_BY_NEWER_CANONICAL_STATE.

Only CAPABILITY_UNPROVEN or CAPABILITY_FAILED can directly justify a fresh capability experiment.

## 9. Summary non-authority
Conversation summaries, model memory, agent notes, cached status messages, and handoffs MUST NOT self-promote into canonical truth.

They may accelerate discovery, but every consequential claim they supply must be reconciled against the live canonical control plane before action.

## 10. Anti-duplication stop rule
The moment live canonical state shows that the intended goal predicate is already proven or the intended task is already complete, all planning/execution for reproving that property MUST STOP.

The next action becomes one of:
- evidence preservation;
- pointer reconciliation;
- next-frontier acquisition;
- contradiction investigation.

## 11. Regression cases
The following 2026-09-22 failure patterns are permanent regression failures:
- planning three new Astra global missions after canonical recovery state already marked all ten global predicates PROVEN;
- treating missing adjudication files as if the underlying Astra capabilities themselves needed rerunning;
- using stale chat/frontier context after canonical/CANONICAL_POINTER.json had advanced to a later generation;
- spending multiple actions on infrastructure or experiment design before checking the authoritative predicate/task tables.

Any future plan matching these patterns MUST fail closed before execution.

## 12. Enforcement consequence
This law is mandatory at boot and before every consequential frontier transition.

Violation invalidates any claim that the resulting work was optimal, fastest, or canonical, regardless of whether the local action technically succeeded.


## 13. Blocker lease and open-PR deduplication
Before any consequential frontier action is allowed to execute, it MUST possess a unique blocker lease derived from:
- canonical generation;
- capability target;
- causal blocker;
- action kind.

The canonical lease key is the exact tuple serialized as:
`canonical_generation::capability_target::causal_blocker::action_kind`.

Every frontier action intent MUST contain this `blocker_lease_key`.

Before expensive execution, the control plane MUST search open pull requests for other action intents with the same lease key. If one exists, the new action MUST:
- join/reuse the existing action;
- wait for its reconciliation; or
- prove that the actions are intentionally independent route-race competitors under a predeclared shared race.

Absent that explicit route-race declaration, equivalent concurrent execution is forbidden.

A frontier workflow MUST NOT begin expensive execution before its pull request exists and the trusted guard has checked the blocker lease. The sequence is:
1. create branch;
2. commit action intent only;
3. open PR;
4. pass trusted blocker-lease/drift guard;
5. only then add/trigger expensive experiment work.

The PR #72 / PR #73 duplicate executable-semantic repair incident is a permanent regression case. Any future equivalent duplicate MUST fail closed.



## 14. Atomic single-flight claim for one-shot validations
A frozen held-out or otherwise freshness-sensitive validation that forbids same-case replay MUST NOT rely on comments, process memory, deployment naming, or a mutable service configuration as its execution lock.

After every non-fresh preflight has passed, but BEFORE any carrier capable of exposing the fresh cases is triggered, the executor MUST acquire exactly one atomic execution claim in the canonical GitHub control plane.

Claim identity:
- key fields: `validation_id` and the frozen manifest Git blob SHA;
- serialization: `validation_id + "\n" + lowercase(manifest_git_blob)`;
- claim digest: SHA-256 of that UTF-8 serialization;
- immutable branch ref: `execution-claims/v1/<claim_digest>`;
- ref target: the exact protected candidate commit SHA to be executed.

The claim MUST be acquired with GitHub's create-reference operation. Creation success is the monotonic spend boundary. The claim ref MUST NEVER be deleted, moved, reused, or reset.

If creation returns "Reference already exists" or any result other than a verified first creation:
- ABORT before any fresh-case carrier trigger;
- treat the gate as already claimed/spent by another executor;
- refresh canonical evidence and join read-only reconciliation.

Only the worker that successfully creates the claim may trigger the fresh-case carrier, and that carrier MUST remain bound to the claim's validation ID, manifest blob, and protected candidate bytes.

A preflight failure before claim creation does not spend the gate. Any failure after successful claim creation leaves the gate permanently spent, possibly with NO_VERDICT; retrying the same validation ID + manifest is forbidden.

Any fresh-case execution that lacks the canonical claim, uses a different claim identity, or occurs after a conflicting claim is inadmissible evidence.

This rule is deliberately one primitive wide: use the existing atomic GitHub ref store. Do not add a database, lock server, queue, or metered coordination service unless this primitive is independently falsified.
