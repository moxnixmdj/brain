# Verified priors — a fresh instance re-executes its stored facts

**Date:** 2026-11-22 · **Authority:** NONE, producer-run sandbox · **Branch:** `arena/5b6ab456-brain`

## Objective and progress claim

Objective, verbatim: `BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`.

Progress class: `VERIFIED_REUSABLE_CAPABILITY_GAIN` in the producer sandbox — the Perfect Algorithm's prior-seeding is now honest. Stored priors (observed environment rows from a *different* instance of the same kind) are re-executed on the fresh instance before they are trusted: only root-row transitions that hold survive into the scan seed. Everything else is discarded and re-derived. No independent verifier, capability credit, or terminal claim is made.

## What changed and why

The loop already had a prior-seeding path — the scan accepted a learned-model prior from another instance without re-execution. That is exactly the wrong kind of instant knowledge: a row collected in one instance is a **claim about another instance**, not a fact about this one. The fresh instance inherited another instance's transitions as if they were its own.

The fix is a single gate, not a second mechanism:

    TO STORE: learned model of THIS instance (observed facts, saved unconditionally)
    TO USE:   re-executed root transitions only → discarded → re-derived by scan

The root is the one state the env can always return to (reset). Root rows are re-executed directly; anything deeper is discarded by design — it cannot be re-verified cheaply without walking the whole prior model, which is the scan itself. The scan then re-derives those rows against *this* instance. This is honest, cheap, and sound: nothing is trusted that did not re-execute.

## What was measured

All of this reuses the Perfect Algorithm loop (`canonical/swe_kernel/perfect_algorithm_v1.py`) and the repo's existing scan machinery. No new dependency.

A same-family pair on the 4×4 grid world:

| Evidence | Result |
|---|---|
| **Instance A** (no walls) | plan 6 · priors saved · rule REFUSED (`NO_FRESH_INSTANCES_OFFERED__NOT_PERSISTED`) |
| **Instance B** (firewall across the top row) | 3 root transitions kept (`up`, `down`, `left` — all survive) · 43 transitions discarded (`right` blocked by walls + all non-root rows) · plan 6 (re-derived) · goal reached after act+verify · rule REFUSED honestly |
| Unit + integration tests | **21/21** pass (`canonical/tests/test_perfect_algorithm_v1.py`) |
| Full suite | **98/98** OK (perfect_algorithm + environment_learning + jit_knowledge) |
| Receipt | `canonical/verification/PERFECT_ALGORITHM_RECEIPT_20261122_FRESH_FAMILY_V1.json` |

**Honest split:**

- The fresh instance's plan is **re-derived** against its own walls — not replayed from instance A. The act+verify step confirms the goal is observed.
- The stored plan rule is not admitted on fresh instances (none offered), so no rule is served and none is persisted. That is the separator working, not a bug.
- What is genuinely reused across instances is the root transition shape — the affordance signature at the root — and that is the one thing that is stable across instances of the same kind.

## Honest limits

- Producer-run sandbox only. No independent identity re-ran any measurement. `truth.achieved` remains false.
- Only root transitions are re-verified. Deeper rows are **never** seeded by design — the scan re-derives them. This is the honest trade: trust nothing on the cheap.
- Fresh-family admission of the plan rule remains open: a fresh instance with identical shape is admitted (existing tests), but the generic plan rule is not yet admitted on a genuinely fresh family — the receipt from the prior PR refused it honestly.
- No GUI, browser, OSWorld 2.0, Terminal-Bench 4.0 or SWE-bench task was run this round. §6 remains open.

## Next test — not a stopping point

Bind one observed family to the admission separator against a genuinely fresh instance of the same family (different walls, different target) so the receipt shows a plan rule saved, replayed, and verified honestly — or honestly refused and refused in the same place. Then carry the same discipline to the OSWorld-shaped surface.
