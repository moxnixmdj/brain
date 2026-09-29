# MISTAKE PRESUMPTION AND ERROR CONTAINMENT LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

## Purpose

Project Brain MUST assume consequential work is likely to contain multiple mistakes unless those failure modes are actively falsified.

Confidence, fluent reasoning, successful local execution, passing tests, prior selection, and model assertions are not proof of correctness.

The system objective is not the impossible promise of zero mistakes. It is to make consequential mistakes difficult to promote, easy to detect, bounded in blast radius, and reversible before they become canonical truth.

## Core invariant

**EVERY CONSEQUENTIAL ACTION, RESULT, AND PROMOTION IS PRESUMED WRONG UNTIL ITS MATERIAL FAILURE MODES HAVE BEEN FALSIFIED BY EVIDENCE INDEPENDENT ENOUGH FOR THE CLAIM.**

## 1. Pre-mortem before consequential action

Every frontier-sensitive action MUST declare at least three materially distinct ways the action could be wrong.

Each failure mode MUST include:
- failure_mode;
- detection;
- prevention;
- abort_or_rollback.

Generic entries such as "bug", "hallucination", or "unknown error" without a concrete detector are invalid.

## 2. Circular proof prohibition

A target frontier implementation MUST NOT execute or verify the proof used to claim that the same frontier implementation has been made unnecessary.

A frontier system may define the comparison bar or act as non-authoritative reference evidence. It may not be the hidden cognitive supplier, producer, or decisive verifier of its own obsolescence claim.

If circularity is discovered after execution, preserve valid lower-level evidence but revoke the unsupported higher-level claim.

## 3. Self-certification prohibition

No producer, worker, route, model, tool, or composed system may promote itself solely from its own output.

Capability acquisition, fresh reuse, and frontier dependency removal require independent verification appropriate to the claim.

Producer and verifier supplier sets MUST be disjoint for promotion claims unless a deterministic equivalence proof makes supplier independence irrelevant and that exception is independently justified.

## 4. Claim ladder

Claims form a strict ladder:

OBSERVATION
-> VERIFIED REAL TASK
-> REUSABLE CAPABILITY
-> FRESH REUSE
-> FRONTIER DEPENDENCY REMOVED.

A lower rung never implies a higher rung.

Examples:
- a useful tool output is not automatically a capability;
- one real task is not automatically general capability;
- same-domain parameter variation is not automatically fresh frontier reuse;
- a persistent executor is not automatically frontier-capable cognition;
- a frontier model completing a task does not prove Brain can complete it without that frontier model.

## 5. Claim-to-evidence map

Every consequential action MUST map each material claim to the evidence that could falsify or support it and record the intended claim strength.

If evidence is weaker than the proposed claim, the claim MUST be downgraded rather than the evidence rhetorically upgraded.

## 6. Promotion integrity

Any increase in canonical progress counters is a promotion event.

A promotion event MUST provide:
- exact evidence paths;
- independent verifier identity;
- producer supplier identities;
- verifier supplier identities;
- supplier-independence verdict;
- the claim scope being promoted.

Frontier dependency removal additionally requires:
- explicit frontier reference;
- explicit replacement route;
- fresh reuse evidence where the target behavior is reusable;
- proof the target frontier supplier was absent from both execution and decisive verification.

Unsupported counter increases MUST fail closed.

## 7. Coupled canonical state is transactional

The following are coupled core state:
- canonical/CANONICAL_POINTER.json
- canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json
- canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json
- canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json

If more than one coupled core file changes in one frontier transition, the final state MUST be written atomically in one Git tree commit.

The exact PR head MUST contain every coupled core path changed by the transition.

Sequential partial updates are forbidden for coupled canonical truth because branch advancement, retries, or API races can otherwise preserve only a subset.

## 8. Exact-head readback

Before merge or promotion, read the exact proposed head back from the canonical control plane and verify:
- expected invariants still hold;
- intended deltas are present;
- no unintended counter or target change occurred;
- all evidence references exist;
- all new governance paths are protected;
- no stale branch or base assumption remains.

A successful write call is not proof that the intended repository state exists.

## 9. Rollback-first response

Every consequential action MUST declare rollback triggers before execution.

If a post-action invariant fails:
1. stop promotion;
2. preserve raw evidence;
3. restore or retain the last coherent canonical state;
4. downgrade only unsupported claims;
5. keep independently valid lower-level evidence;
6. recompute the frontier.

Do not repair bookkeeping forward when rollback is cheaper and safer.

## 10. Assumption invalidation

Material assumptions MUST be treated as hypotheses, not facts.

New evidence that contradicts an assumption invalidates the affected plan, OBS layers, route choice, verifier, or promotion immediately.

Sunk cost grants no authority.

## 11. Error containment

Actions should minimize blast radius:
- prefer reversible changes before irreversible ones;
- prefer small independent mutations;
- freeze scarce one-shot gates until prerequisites are proven;
- isolate experimental outputs from canonical promotion state;
- never let an experiment directly self-edit its promotion status.

## 12. Independent contradiction search

Before consequential promotion, one role MUST actively attempt to prove the proposed conclusion wrong.

For capability claims, the contradiction search MUST ask at least:
- Did the target supplier secretly remain in the execution path?
- Did the verifier share the same failure mode as the producer?
- Did we prove only a narrower behavior?
- Did we confuse missing proof with missing capability, or one success with generality?
- Did canonical state drift after planning?
- Did a lower claim rung get promoted into a higher one?

## 13. No ceremony

Mistake prevention itself receives zero progress credit.

Do not add reviews, tests, or receipts merely to look safer. Add only controls that can catch a real failure class or reduce blast radius.

## 14. Permanent regressions

The following are permanent failure classes:
- benchmark or narrow tool result promoted as a real frontier capability;
- same-domain parameter reuse promoted as cross-domain frontier reuse;
- frontier model used to prove its own removal;
- partial multi-file canonical correction surviving while intended sibling updates are lost;
- successful local action interpreted as parent capability success without independent evidence;
- scoreboard increment without claim-level evidence;
- trusted workflow UI color treated as semantic evidence when no validation step executed.

Any equivalent future pattern MUST fail closed.

## 15. Priority

1. truth/correctness;
2. prevent false promotion;
3. contain blast radius;
4. minimum wall-clock to verified real capability;
5. minimum incremental cost;
6. minimum machinery.

The default assumption is that we missed something. The job of the control system is to make that assumption cheap to test before the mistake becomes canonical.
