# GOAL HIERARCHY AND DRIFT IMMUNITY LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Purpose: make local task success, probe completion, infrastructure activity, and attractive subproblems structurally unable to replace Project Brain's terminal objective.

## 1. Immutable hierarchy

Every consequential action MUST be bound to this hierarchy:

L0 TERMINAL OBJECTIVE
-> L1 ACTIVE PROGRAM
-> L2 CAPABILITY TARGET
-> L3 PROBE / EXPERIMENT
-> L4 OBSERVED CAUSAL BLOCKER
-> L5 ACTION

A child level may produce evidence for its parent. It may never redefine, replace, or become its parent.

The terminal objective may change only through an explicit user-authorized canonical goal change.

## 2. Current terminal objective

Systematically obsolete useful frontier-model capabilities by finding verified equal-or-better capability routes with minimum wall-clock time and incremental cost.

A probe is never the goal.
A package, benchmark, tool, model, workflow, branch, PR, artifact, or test is never the goal.

## 3. Parent-progress rule

Before execution, every L5 action MUST state the exact expected state change at L2 or above.

"Make the probe pass", "fix the package", "finish the branch", or "improve the benchmark" are invalid parent-progress claims.

If an action can succeed while leaving the parent capability decision unchanged, it is diagnostic/supporting work only and receives no progress credit.

## 4. Probe budget

A single probe may expose a candidate generic blocker.

For one probe:
- at most ONE generic repair may be made from a blocker observed only in that probe;
- that repair may be replayed on the SAME frozen probe once;
- after that replay, the probe's diagnostic role is CLOSED regardless of success or failure.

A second repair motivated by the same probe is forbidden unless:
1. the same causal failure recurs in at least TWO orthogonal probes; or
2. the repair is required by an acceptance gate that was frozen BEFORE the first probe ran.

This rule exists specifically to prevent a diagnostic mission from turning into a local optimization rabbit hole.

## 5. Orthogonality requirement

Before promoting a blocker into a generic architectural problem after one repair/replay, test it on orthogonal work.

Orthogonal means materially different in at least two of:
- domain;
- supplier/tool ecosystem;
- input/output type;
- verification mechanism;
- execution surface;
- capability composition.

Two cosmetic variants of one task are not orthogonal.

## 6. Probe-contamination rule

Generic runtime/controller code MUST NOT gain task-specific literals, package names, benchmark names, data values, or one-probe special cases merely to make a probe pass.

Task-specific adapters may live in explicit capability bindings/registries when independently verified.

If a generic runtime change contains probe-specific literals, the action FAILS CLOSED unless cross-probe evidence proves those literals are actually generic protocol vocabulary.

## 7. Automatic frontier reconciliation

After each probe reaches any terminal result:
- PASS;
- FAIL;
- PARTIAL;
- BLOCKED;
- CANDIDATE_MATCH;

the next action MUST be RECONCILE_FRONTIER.

Reconciliation asks:
1. Did the parent capability status change?
2. Did a generic blocker recur across orthogonal evidence?
3. Is the probe now closed?
4. What is the highest-leverage next capability action?

Continuing the same probe without this reconciliation is prohibited.

## 8. Capability-target tenure

A capability target remains active only while it is the highest-leverage unresolved target under the canonical optimization law.

No capability target may remain active merely because substantial work has already been invested in it.

Sunk cost has zero authority.

## 9. Sensitive-change intent record

Every PR that changes frontier-sensitive paths MUST add an immutable action-intent record under:

canonical/action_intents/

The record MUST bind:
- canonical generation;
- terminal objective;
- active program;
- parent capability;
- probe;
- blocker;
- action;
- expected parent-level state change;
- evidence for highest leverage;
- probe budget usage;
- orthogonal recurrence count;
- stop condition.

Missing or inconsistent intent => FAIL CLOSED.

## 10. Merge gate

Frontier-sensitive PRs MUST pass the canonical anti-drift validator before merge.

A failed drift check invalidates merge authority even if all technical tests pass.

Green tests cannot promote an off-goal action.

## 11. Anti-self-modification

Changes to this law, the drift validator, the action gate, or the anti-drift workflow are GOVERNANCE_CHANGES.

They require:
- explicit governance-change intent;
- unchanged terminal objective unless explicit user authorization is recorded;
- no weakening of mandatory checks without explicit user authorization.

A normal capability PR may not weaken, bypass, delete, or scope out the drift guard.

## 12. Quarantine rule

When drift is detected:
- stop mutations on the drifting branch;
- preserve its evidence;
- mark it draft/evidence-only;
- recompute the parent frontier from canonical state;
- extract only independently useful generic improvements through a fresh compliant PR.

Do not finish the drifting branch "because we are close."

## 13. Progress accounting

Progress is credited only for:
- verified frontier capability obsolescence;
- verified increase in reusable equal-or-better capability;
- exact localization/removal of a generic blocker supported by the required evidence;
- inherited reusable capability that changes future parent-level decisions.

No progress credit:
- probe completion by itself;
- PR/commit count;
- test count;
- package discovery;
- infrastructure;
- retries;
- local benchmark improvement.

## 14. Enforcement priority

When this law conflicts with a local experiment plan, this law wins.

Priority:
1. terminal objective integrity;
2. correctness/truth;
3. maximum parent-level leverage per wall-clock time;
4. minimum incremental cost;
5. local probe completion.

Local completion is deliberately last.
