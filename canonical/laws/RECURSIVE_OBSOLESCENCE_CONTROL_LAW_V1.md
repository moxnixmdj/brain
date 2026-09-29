# RECURSIVE OBSOLESCENCE CONTROL LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

## Purpose

Obsolescence analysis (OBS) is the default outer control loop for every consequential Project Brain action.

OBS exists to prevent local optimization of a path, component, blocker, verifier, or architecture that can instead be deleted, bypassed, substituted, reused, composed, or made irrelevant.

Remembering OBS is insufficient. A current OBS decision must exist before consequential implementation begins.

## Core invariant

**NO CONSEQUENTIAL IMPLEMENTATION WORK UNTIL A CURRENT CAPABILITY-LEVEL OBS PASS PROVES THAT THE IMPLEMENTATION IS STILL THE FASTEST SUFFICIENT SURVIVING ROUTE.**

The burden of proof is on keeping machinery, not deleting it.

## Seven recursive OBS layers

Every consequential action MUST evaluate all seven layers in order.

### OBS-1 — Goal

Ask:
- What real useful output is required?
- Is the stated local goal merely a proxy for a higher useful outcome?
- Can the local goal itself be deleted or replaced by a simpler sufficient outcome?

Output:
- exact real outcome;
- proxy goals deleted;
- surviving necessity.

### OBS-2 — Capability

Ask:
- What capability is actually required to produce the real outcome?
- Does Brain already inherit it?
- Does an existing connected tool, library, CLI, API, application, solver, database, model, service, or composition already provide it?
- Can multiple apparent capability gaps collapse into one stronger reusable mechanism?

Output:
- required capability;
- reusable routes found;
- capability work that becomes unnecessary.

### OBS-3 — Blocker

Ask:
- Is the blocker intrinsic to the required capability, or only to the chosen path?
- Can the blocker be bypassed, deleted, substituted, routed around, or made irrelevant by changing the architecture?
- Does fixing the blocker actually change parent-level capability output?

Output:
- blocker necessity classification;
- bypass/delete/substitute alternatives;
- exact blocker, if one survives.

### OBS-4 — Proposed solution

Before building or repairing anything, race:
1. inherited Brain capability;
2. direct reuse;
3. connected tool/system;
4. existing software/library/CLI/API/database/solver;
5. composition;
6. JIT acquisition;
7. deterministic/specialized substitute;
8. smallest adequate model supplier;
9. adaptation;
10. invention.

Output:
- surviving route;
- losing routes and why they lost;
- proof that implementation is still necessary.

### OBS-5 — Verification

Ask:
- Can the real effect be verified directly?
- Can an existing independent oracle verify it?
- Can a simpler observable consequence replace a synthetic benchmark, bespoke gate, or new evaluator?
- Does the proposed verification test the useful outcome rather than internal ceremony?

Output:
- cheapest independent sufficient verifier;
- verification machinery deleted;
- residual uncertainty.

### OBS-6 — Inherited system

After acquiring a capability, immediately ask:
- What queued tasks, adapters, probes, dependencies, or capability targets are now obsolete?
- Can the new capability absorb adjacent mechanisms?
- Can future tasks reuse the capability without rediscovery?

Output:
- inherited capability package;
- downstream deletions;
- frontier recomputation.

### OBS-7 — OBS itself

OBS is not exempt from OBS.

Ask:
- Is the current search/acquisition/verification process the fastest sufficient process?
- Are repeated searches, receipts, gates, or reviews consuming more time than the capability they protect?
- Can OBS be cached, inherited, compiled, automated, or shortened without reducing truthfulness?
- Is another OBS pass useful, or has an adequate route already been established?

Output:
- process improvements;
- redundant analysis deleted;
- stop decision.

## OBS receipt

Every consequential frontier action MUST carry a generation-bound recursive OBS receipt containing:

- canonical_generation_or_commit;
- real_outcome;
- required_capability;
- obs_goal;
- obs_capability;
- obs_blocker;
- obs_solution;
- obs_verification;
- obs_inherited_system;
- obs_obs;
- routes_considered;
- deleted_or_bypassed_paths;
- selected_surviving_route;
- why_selected_route_is_fastest_sufficient;
- expected_parent_level_state_change;
- stop_condition.

The receipt MAY live inside the action intent. A separate document is not required.

The receipt is invalid if the canonical frontier, relevant capability state, available route set, or real task materially changes before execution.

## Deletion-first rule

For every blocker or component, evaluate in this order:

**DELETE -> BYPASS -> REUSE -> SUBSTITUTE -> COMPOSE -> REPAIR -> BUILD**

Repairing the currently visible mechanism is never the default.

## Search sufficiency and stop rule

Search is not infinite.

Stop searching when:
- one route is verified adequate for the real capability;
- remaining plausible routes cannot beat it on correctness first, then wall-clock, then incremental cost enough to justify delay;
- additional search would not change the execution decision.

At that point, execute.

## Recursive invalidation rule

A selected route has no permanent authority.

After any material new fact:
- refresh canonical state;
- invalidate stale OBS assumptions;
- rerun only affected OBS layers;
- delete the selected route if a faster sufficient route now exists.

Do not blindly rerun all seven layers when only one layer changed.

## Blocker treatment

A blocker may receive implementation work only if current OBS proves:
1. the parent real outcome still matters;
2. the capability remains required;
3. no adequate existing route bypasses it;
4. the blocker is causal on the fastest surviving route;
5. removing it is faster than switching routes.

Otherwise the blocker is obsolete.

## Verification treatment

A benchmark, held-out test, or synthetic gate is admissible only if direct verification of the real effect is unavailable or insufficient and the synthetic mechanism is the fastest reliable substitute.

Verification infrastructure receives zero progress credit by itself.

## Infrastructure treatment

A new carrier, provider, bridge, scheduler, runtime, account, database, queue, or orchestration layer is forbidden until recursive OBS proves existing routes cannot produce the real output faster.

## Inheritance treatment

Every verified capability gain triggers OBS-6 immediately.

The default reaction to a new capability is not "what should we add next?" but:

> "What can we now delete?"

## Progress treatment

OBS passes are not progress.

Progress remains VERIFIED REUSABLE CAPABILITY OUTPUT.

OBS is a decision-quality mechanism whose success is measured by:
- avoided unnecessary work;
- shorter wall-clock to real output;
- deleted components;
- reused inherited capability;
- fewer synthetic support actions;
- faster frontier recomputation.

## Priority

1. correctness and real capability;
2. minimum wall-clock to verified reusable output;
3. minimum incremental cost;
4. deletion/reuse over construction;
5. verification strength;
6. minimum machinery.

The best part is no part, including parts of the OBS process itself.
