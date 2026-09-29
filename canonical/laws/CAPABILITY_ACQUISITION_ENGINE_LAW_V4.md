# CAPABILITY ACQUISITION ENGINE LAW V4

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Authority:
- canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V2.md
- canonical/laws/MISTAKE_PRESUMPTION_AND_ERROR_CONTAINMENT_LAW_V1.md

Supersedes:
- canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V3.md

All V3 requirements remain mandatory unless this V4 rule is stricter.

## New invariant: error-presumed acquisition

Every consequential acquisition action MUST carry both:
1. a current Recursive OBS V3 receipt; and
2. a current Mistake Prevention V1 receipt.

The system MUST presume the selected action, local success, verifier, and promotion claim may all be wrong until their material failure modes are falsified.

## Claim ladder

Progress may advance only one evidence-supported claim level at a time:

OBSERVATION
-> VERIFIED REAL TASK
-> REUSABLE CAPABILITY
-> FRESH REUSE
-> FRONTIER DEPENDENCY REMOVED.

No success at one level implies the next.

## Frontier independence

A frontier implementation may define the bar but MUST NOT execute or decisively verify the proof used to claim its own replacement.

A route remains unproven for frontier dependency removal if the target frontier supplier remains in the execution or decisive verification path.

## Transactional canonical truth

Coupled core canonical state MUST update atomically when more than one core file changes.

The exact head must be read back and checked before merge/promotion.

## Promotion accounting

Every scoreboard counter increase is a promotion event and MUST be supported by explicit evidence paths plus an independent-verification contract.

Unsupported promotion is worse than missing progress and MUST fail closed.

## Falsification reaction

When a mistake is discovered:
- preserve valid raw/lower-level evidence;
- revoke only unsupported higher claims;
- do not erase useful falsification evidence;
- rollback canonical promotion state before attempting forward repair when rollback is cheaper;
- rerun OBS only for affected layers.

## Progress

Mistake-prevention receipts, reviews, guards, and regressions receive zero progress credit.

Progress remains verified reusable capability output and verified removal of frontier dependence.
