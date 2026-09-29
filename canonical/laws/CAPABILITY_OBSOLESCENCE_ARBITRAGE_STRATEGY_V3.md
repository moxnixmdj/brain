# CAPABILITY OBSOLESCENCE ARBITRAGE STRATEGY V3

Status: CANONICAL / MANDATORY / EXECUTION STRATEGY

Authority:
- canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_OBSOLESCENCE_MISSION_LOCK_V4.md
- canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V1.md

Supersedes:
- canonical/laws/CAPABILITY_OBSOLESCENCE_ARBITRAGE_STRATEGY_V2.md

## Mission

Acquire, verify, inherit, and reuse the fastest realizable equal-or-better routes for useful frontier-model capabilities until the frontier implementation is no longer uniquely necessary.

The engine optimizes for VERIFIED REUSABLE CAPABILITY OUTPUT, not activity.

## Core loop

**SELECT REAL CONSEQUENTIAL TASK
-> IDENTIFY MISSING USEFUL CAPABILITY
-> SEARCH HIDDEN WAREHOUSE
-> REUSE / COMPOSE / ACQUIRE
-> EXECUTE THE REAL TASK
-> INDEPENDENTLY VERIFY
-> INHERIT THE WINNING ROUTE
-> REUSE ON FRESH WORK
-> OBSOLETE OR LOCALIZE RESIDUAL GAP
-> RECOMPUTE**

A benchmark or held-out gate may support this loop. It may not replace it.

## Real-output gate

Before any consequential action, require a direct path to one of:
- reusable capability inherited;
- verified real task completed;
- fresh reuse demonstrated;
- frontier dependency removed;
- residual capability gap localized enough to change the frontier.

If no direct path exists, the action is supporting work and is subject to the strict support budget in CAPABILITY_ACQUISITION_ENGINE_LAW_V1.

## Route order

Search and race in this order unless evidence justifies otherwise:
1. existing inherited Brain capability;
2. existing connected tool/plugin/system;
3. existing software/library/CLI/API/database/solver;
4. composition of existing components;
5. JIT capability acquisition;
6. adaptation;
7. smallest adequate model supplier;
8. invention.

Search before invention is mandatory.

## Synthetic support policy

Synthetic work is allowed only to unblock the current real-task capability acquisition.

Do not create H(N+1) merely because H(N) terminated.

No hidden gate may be frozen before generic carrier/runtime/verifier realizability has already passed without the hidden payload.

## Capability inheritance

Every winning route must be stored as a reusable capability package:
- useful behavior;
- invocation contract;
- supplier/version or implementation;
- prerequisites;
- verifier;
- provenance;
- latency/cost;
- failure modes;
- real-task evidence;
- fresh-reuse evidence where practical.

The package is the product. The experiment is disposable.

## Multi-capability leverage

Prefer mechanisms that unlock many future tasks:
- generic retrieval;
- generic tool discovery/acquisition;
- deterministic execution;
- composition/orchestration;
- verification;
- durable memory/reuse.

A narrow adapter wins only when it is the fastest route to real output.

## Frontier target tenure

A capability target retains frontier priority only while it has the highest expected:

**verified reusable capability gain / wall-clock**

Sunk cost has zero authority.

If two supporting actions occur without a real-output state change, recompute the target before further work.

## Infrastructure

Reuse existing qualified execution surfaces by default.

No new carrier, provider, account, bridge, or orchestration layer may be introduced unless a live real task proves the existing surface cannot produce the needed capability output.

## Scoreboard

Canonical scoreboard:
- canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json

Primary counters:
- reusable_capabilities_inherited;
- verified_real_tasks_completed;
- fresh_reuse_passes;
- frontier_dependencies_removed;
- residual_gaps_localized.

Secondary efficiency metrics:
- median_capability_acquisition_wall_s;
- incremental_spend_usd;
- synthetic_support_actions_since_last_real_output.

PR count, benchmark count, workflow count, gate count, and worker count are not progress metrics.

## Immediate operating mode

Project Brain now operates in REAL_CAPABILITY_ACQUISITION mode.

The next frontier action is not another synthetic gate by default.

Select one high-leverage real task that requires a currently missing or uncertain capability, run the full search->acquire->execute->verify->inherit cycle, and score only the reusable output.

Existing synthetic work may continue only if it is the shortest proven blocker-removal path for that real mission.

## Terminal condition

The program ends only when the useful frontier capability surface has been systematically processed and every target has either:
- a verified reusable equal-or-better route that is inherited and usable on real work; or
- a precise evidence-backed irreducible residual gap.

The goal is not to own more tests.

The goal is to need frontier models less because Brain actually does the work.
