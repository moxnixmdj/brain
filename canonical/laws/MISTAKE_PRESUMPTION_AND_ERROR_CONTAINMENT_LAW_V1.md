# MISTAKE PRESUMPTION AND ERROR CONTAINMENT LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

## Purpose

Project Brain MUST assume consequential work is likely to contain multiple mistakes unless those failure modes are actively falsified.

Confidence, fluent reasoning, successful local execution, passing tests, prior selection, and model assertions are not proof of correctness.

The system objective is not the impossible promise of zero mistakes. It is to make consequential mistakes difficult to promote, easy to detect, bounded in blast radius, and reversible before they become canonical truth.

## Core invariant

**EVERY CONSEQUENTIAL ACTION, RESULT, AND PROMOTION IS PRESUMED WRONG UNTIL ITS MATERIAL FAILURE MODES HAVE BEEN FALSIFIED BY EVIDENCE INDEPENDENT ENOUGH FOR THE CLAIM.**

## Pre-mortem before action

Every frontier-sensitive action MUST declare at least three materially distinct ways the action could be wrong. Each must contain:
- failure_mode;
- detection;
- prevention;
- abort_or_rollback.

Generic filler is invalid. A failure mode without a concrete detector does not count.

## Circular proof prohibition

A target frontier implementation MUST NOT execute or decisively verify the proof used to claim that the same frontier implementation has been made unnecessary.

The frontier implementation may define the comparison bar or provide non-authoritative reference evidence. It may not be the hidden producer, cognitive supplier, or decisive verifier of its own obsolescence.

If circularity is discovered later, preserve valid lower-level evidence and revoke the unsupported higher-level claim.

## Self-certification prohibition

No producer, worker, model, tool, route, or composed system may promote itself solely from its own output.

Capability acquisition, fresh reuse, and frontier dependency removal require verification independent enough for the claim.

For promotion claims, producer and verifier supplier sets MUST be disjoint unless a separately justified deterministic-equivalence exception is independently established.

## Strict claim ladder

OBSERVATION
-> VERIFIED REAL TASK
-> REUSABLE CAPABILITY
-> FRESH REUSE
-> FRONTIER DEPENDENCY REMOVED.

A lower rung never implies a higher rung.

A useful tool output is not automatically a capability.
One real task is not automatically general capability.
Same-domain parameter variation is not automatically frontier fresh reuse.
A persistent executor is not automatically frontier-capable cognition.
A frontier model completing a task does not prove Brain can complete it without that frontier model.

## Claim-to-evidence map

Every consequential action MUST map each material claim to evidence and declare the intended claim strength.

If evidence is weaker than the proposed claim, downgrade the claim. Never rhetorically upgrade the evidence.

## Promotion integrity

Any increase in canonical progress counters is a promotion event.

A promotion event MUST provide:
- exact evidence paths;
- independent verifier identity;
- producer supplier identities;
- verifier supplier identities;
- supplier-independence verdict;
- claim scope.

Frontier dependency removal additionally requires:
- explicit frontier reference;
- explicit replacement route;
- fresh reuse evidence when reusable behavior is claimed;
- proof the target frontier supplier was absent from both execution and decisive verification.

Unsupported counter increases MUST fail closed.

## Coupled canonical state is transactional

The coupled core state is:
- canonical/CANONICAL_POINTER.json
- canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json
- canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json
- canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json

If more than one coupled core file changes in one frontier transition, the final proposed head MUST update every changed coupled path in one atomic Git tree commit.

Sequential partial updates are forbidden for coupled canonical truth.

## Exact-head readback

Before merge or promotion, reread the exact proposed head and verify:
- expected invariants;
- intended deltas;
- no unintended target/counter drift;
- evidence references exist;
- new governance paths are protected;
- no stale base assumption remains.

A successful mutation call is not proof the intended repository state exists.

## Rollback-first response

Every consequential action MUST declare rollback triggers before execution.

On post-action contradiction:
1. stop promotion;
2. preserve raw evidence;
3. keep or restore the last coherent canonical state;
4. downgrade only unsupported claims;
5. preserve independently valid lower-level evidence;
6. recompute the frontier.

Prefer rollback over forward bookkeeping repair when rollback is cheaper and safer.

## Assumptions are hypotheses

Material assumptions have no permanent authority.

Contradictory evidence invalidates affected plan, OBS layers, route, verifier, or promotion immediately.

Sunk cost grants no authority.

## Error containment

Prefer reversible changes before irreversible ones.
Keep experiments isolated from promotion state.
Never let an experiment self-edit its promotion status.
Freeze scarce one-shot gates until prerequisites are proven.
Minimize mutation blast radius.

## Independent contradiction search

Before consequential promotion, actively try to prove the conclusion wrong.

At minimum ask:
- Did the target supplier secretly remain in execution?
- Did the verifier share the producer's failure mode?
- Did we prove only a narrower behavior?
- Did a lower claim rung become a higher one without evidence?
- Did canonical state drift after planning?
- Did we confuse missing proof with missing capability?

## No ceremony

Mistake prevention receives zero progress credit.

Add only controls that catch a real failure class or reduce blast radius.

## Permanent regressions

These future-equivalent patterns MUST fail closed:
- benchmark or narrow domain result promoted as frontier capability;
- same-domain parameter reuse promoted as cross-domain frontier reuse;
- frontier model used to prove its own removal;
- partial multi-file canonical state update;
- local success promoted as parent capability success without independent evidence;
- scoreboard increment without claim-level evidence;
- workflow UI status treated as semantic validator evidence when no validation step executed.

## Priority

1. truth/correctness;
2. prevent false promotion;
3. contain blast radius;
4. minimum wall-clock to verified real capability;
5. minimum incremental cost;
6. minimum machinery.

The default assumption is that we missed something. The control system exists to make that assumption cheap to test before the mistake becomes canonical.
