# ADVERSARIAL ERROR CONTROL LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

## Purpose

Consequential Brain actions MUST assume their current plan may be wrong. This law converts that assumption into a compact machine-enforced contract at the existing trusted action gate.

It does not claim that every conceivable future mistake can be made impossible. It makes known high-impact error classes fail closed and requires explicit adversarial search for material unknown errors before authorization.

## Mandatory contract

Every frontier-sensitive action intent MUST contain `adversarial_error_control` and MUST:

1. assert `assume_action_wrong=true`;
2. state multiple strongest plausible disconfirming hypotheses;
3. check the canonical known-failure classes;
4. leave no unresolved material risk at authorization time;
5. preserve exact target fidelity and reject proxy substitution;
6. declare an exact execution-supplier manifest for any proof-bearing claim;
7. forbid unknown or opaque supplier identities in capability-promotion, fresh-reuse-proof, or frontier-dependency-removal evidence;
8. forbid the target frontier supplier from the producer or verifier path of any claim that says that supplier is no longer necessary;
9. require producer/verifier independence for promotion/removal claims;
10. declare the exact non-intent sensitive paths expected to change;
11. declare machine-checkable postconditions evaluated on the exact PR head.

## Canonical known-failure classes

At minimum:
- STALE_STATE
- TARGET_SUBSTITUTION
- PROXY_GOAL
- CIRCULAR_PROOF
- SELF_CERTIFICATION
- NARROW_CAPABILITY_INFLATION
- SAME_DOMAIN_REUSE_INFLATION
- ROUTE_READINESS
- DUPLICATE_EXECUTION
- ACTIVITY_AS_PROGRESS
- POST_STATE_MISMATCH
- HIDDEN_DEPENDENCY
- FALSIFIED_ROUTE_REPLAY

A newly observed generic failure class MUST be added to the canonical regression set rather than handled only by operator memory.

## Non-circular frontier proof

When a PR increases `reusable_capabilities_inherited`, `fresh_reuse_passes`, or `frontier_dependencies_removed`, or otherwise claims frontier capability promotion/removal:

- execution supplier inventory MUST be complete;
- unknown suppliers MUST be empty;
- opaque supplier aliases MUST be empty;
- the target frontier supplier MUST NOT be in the producer path;
- the target frontier supplier MUST NOT be in the verifier path;
- an independent verifier MUST be present;
- producer and verifier MUST be independent.

A frontier model may be a comparator/reference source, but it cannot perform or certify the capability whose independence is being claimed.

## Exact head contract

The action intent MUST enumerate exactly the non-intent frontier-sensitive paths changed by the PR.

The trusted guard MUST evaluate every declared postcondition against the exact PR head. Supported postconditions are deliberately small and deterministic:
- file exists;
- JSON field equals an exact value;
- text contains an exact required token.

Unexpected sensitive changes, missing expected changes, or failed postconditions abort authorization.

## Unknown-error discipline

The operator MUST actively try to falsify the chosen route. Empty `unresolved_material_risks` is an authorization assertion, not proof of omniscience. If a new material risk appears, the affected action loses authority immediately and OBS must refresh the affected layers.

## Progress

Adversarial analysis, guard changes, regressions and postcondition checks receive zero progress credit by themselves.

## Stop rule

Once this compact contract is machine-enforced, stop governance work. Return to the current real frontier capability blocker.
