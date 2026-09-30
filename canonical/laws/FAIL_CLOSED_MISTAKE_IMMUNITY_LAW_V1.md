# FAIL-CLOSED MISTAKE IMMUNITY LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

## Purpose

Project Brain assumes consequential plans, classifications, route selections, promotion claims, and remembered state are fallible by default.

The objective is not to pretend mistakes can be eliminated from cognition. The objective is to make an unverified mistake unable to silently acquire authority, consume duplicate scarce work, inflate capability progress, or substitute a proxy for the terminal objective.

## Core invariant

**EVERY CONSEQUENTIAL CLAIM IS NON-AUTHORITATIVE UNTIL ITS EXACT SCOPE, PRODUCER PATH, EVIDENCE, AND INDEPENDENT VERIFICATION MAKE THAT CLAIM ADMISSIBLE.**

Absence of a detected error is not proof of correctness.

## Deterministic lease ownership

Accidental duplicate blocker leases MUST have exactly one deterministic owner.

Blocker lease identity is exactly **canonical generation + active capability target + causal blocker**. `action_kind`, route wording, implementation label, branch name, and PR title are NOT part of blocker identity and MUST NOT permit duplicate ownership.

- The lowest open PR number holding a valid identical lease is the owner.
- Any later accidental duplicate MUST fail closed.
- The owner MUST NOT fail merely because a later duplicate exists.
- Intentional route races are allowed only when every participant declares the same nonempty route_race_id and intentional_route_race=true.
- Losing duplicate routes receive zero progress credit and are closed rather than ceremonially completed.

## No proxy substitution

An ordinary capability, task, repair, support, or reuse action MUST NOT silently change the active capability target.

Changing the active target requires an explicit frontier reconciliation or user-authorized governance action that states:
- previous target;
- new target;
- relationship between them;
- evidence that the change advances the terminal objective.

A subcapability is evidence toward its parent, not a replacement for its parent.

## No circular frontier proof

When claiming model-independent acquisition or frontier-model obsolescence of a cognitive capability:
- the target frontier model or equivalent target supplier MUST NOT be execution-critical in the producer path;
- a child/subcapability inherits the model-independence requirements of its frontier parent;
- the independent verifier MUST NOT be the same target supplier whose dependency is claimed removed;
- tool use by a verifier does not authorize the producer to depend on the target supplier.

If supplier independence cannot be demonstrated, the result may be useful task evidence but MUST NOT receive frontier-dependency-removal credit.

## No evidence laundering

The following equivalences are forbidden:
- benchmark completion == real capability acquisition;
- narrow deterministic tool == broad frontier capability;
- same-domain parameter variation == cross-domain fresh reuse;
- self-certification == independent verification;
- old success == current route readiness;
- model-assisted execution == model-independent capability proof;
- missing proof == missing capability;
- activity == progress.

Claims may only be promoted at the strongest scope directly supported by evidence.

## Promotion truth

Any scoreboard increase or frontier promotion MUST be traceable to evidence appropriate to that exact counter/claim.

Especially:
- reusable capability credit requires a capability package, real-task evidence, provenance, invocation contract, failure modes, and independent verification;
- fresh-reuse credit requires a distinct fresh task and no rediscovery of the operating method;
- cross-domain credit requires materially different domains;
- frontier-dependency-removal credit requires the removed supplier to be absent from the producer path and an independent verifier not equal to that supplier;
- broad capability promotion requires all minimum acquisition evidence declared by the frontier capability record.

If evidence is weaker than the claim, reduce the claim. Never stretch the evidence.

## Adversarial pre-mortem

Recursive OBS is required to search not only for a better route but also for the most plausible way the selected route or claim is wrong.

For consequential promotions, at least one falsification attempt or explicit impossibility of a cheap falsification route must be recorded before promotion.

The purpose is to kill false confidence cheaply before it reaches canonical state.

## Unknown-error containment

Unknown mistakes cannot be enumerated in advance. Therefore:
- state changes are exact-base-bound;
- route decisions expire;
- producer and verifier roles are separated for consequential claims;
- scope only expands after fresh evidence;
- contradictions invalidate affected authority immediately;
- rollback/correction is progress-neutral but mandatory;
- no sunk-cost authority exists.

## Progress

This law, its checks, regressions, PRs, and tests receive zero progress credit.

Progress remains verified reusable frontier capability output.

## Priority

1. exact truth and scope correctness;
2. real frontier capability acquisition;
3. minimum wall-clock to verified output;
4. zero incremental spend;
5. deletion/reuse/composition before construction;
6. minimum machinery.

The best part remains no part. The best mistake is the one that never gains authority.
