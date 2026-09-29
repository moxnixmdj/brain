# CAPABILITY ACQUISITION ENGINE LAW V5

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Authority:
- canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V3.md
- canonical/laws/MISTAKE_PRESUMPTION_AND_ERROR_CONTAINMENT_LAW_V1.md

Supersedes:
- canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V4.md

All V4 requirements remain mandatory unless V5 is stricter.

## Error-presumed acquisition

Every consequential acquisition action MUST carry both:
1. a current Recursive OBS V4 receipt; and
2. a current Mistake Prevention V1 receipt.

The selected route, local success, verifier, and promotion claim are all presumed fallible until material failure modes are falsified.

## Claim ladder

Progress may advance only through evidence-supported levels:

OBSERVATION
-> VERIFIED REAL TASK
-> REUSABLE CAPABILITY
-> FRESH REUSE
-> FRONTIER DEPENDENCY REMOVED.

No level implies the next.

## Frontier independence

A frontier implementation may define the bar but MUST NOT execute or decisively verify the proof used to claim its own replacement.

If the target frontier supplier remains in execution or decisive verification, frontier dependency removal is unproven.

## Transactional canonical truth

When more than one coupled core canonical file changes, the final head MUST update all changed coupled paths atomically in one Git tree commit.

Exact-head readback is mandatory before merge or promotion.

## Promotion accounting

Every scoreboard counter increase is a promotion event and requires explicit evidence paths plus an independent-verification contract.

Unsupported promotion fails closed.

## Falsification reaction

When a mistake is found:
- preserve valid raw/lower-level evidence;
- revoke only unsupported higher claims;
- rollback promotion state before forward repair when rollback is cheaper;
- rerun only affected OBS layers;
- recompute the frontier.

## Progress

Mistake-prevention receipts, reviews, guards, and regressions receive zero progress credit.

Progress remains verified reusable capability output and verified removal of frontier dependence.
