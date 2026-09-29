# CAPABILITY ACQUISITION ENGINE LAW V2

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Authority:
- canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V1.md

Supersedes:
- canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V1.md

## Purpose

Project Brain is a capability acquisition engine, not a benchmark factory.

The terminal objective remains unchanged: systematically obsolete useful frontier-model capabilities by finding verified equal-or-better capability routes with minimum wall-clock time and incremental cost.

## Mandatory outer loop

Recursive OBS controls every consequential action.

Before implementation, the action must survive:
1. OBS the goal;
2. OBS the capability;
3. OBS the blocker;
4. OBS the proposed solution;
5. OBS the verification method;
6. OBS the inherited system;
7. OBS the OBS process itself.

No consequential implementation work may begin without a current generation-bound OBS receipt.

## Unit of progress

Progress is credited only when at least one parent-level state changes:

1. a reusable capability is acquired and bound;
2. a real consequential task is completed using that capability;
3. the result is independently verified;
4. the capability is inherited for reuse without rediscovery;
5. a previously required frontier-model contribution is removed;
6. an irreducible residual capability gap is localized with enough evidence to change the frontier.

PRs, commits, tests, benchmarks, probes, gates, carrier qualifications, infrastructure, package discovery, OBS receipts, and workflow runs receive ZERO progress credit by themselves.

## Default operating loop

REAL TASK
-> RECURSIVE OBS
-> IDENTIFY SURVIVING MISSING CAPABILITY
-> SEARCH / REUSE BEFORE INVENTION
-> ACQUIRE OR COMPOSE FASTEST SUFFICIENT ROUTE
-> EXECUTE REAL WORK
-> INDEPENDENTLY VERIFY REAL EFFECT
-> INHERIT WINNER
-> OBS INHERITED SYSTEM FOR DELETIONS
-> REUSE ON FRESH WORK
-> RECOMPUTE FRONTIER

## Real-task-first rule

The default next action MUST be a real task that exercises useful capability.

Synthetic work is allowed only when one exact unresolved predicate blocks the selected real task and recursive OBS proves the synthetic action is the fastest sufficient blocker-removal route.

## Support budget

For each real capability acquisition mission:
- at most one synthetic/support action may run without a parent-level output change;
- a second requires documented falsification of the first support route;
- after two support actions without real output, recompute the capability target;
- another gate, carrier, or infrastructure branch is never an automatic continuation.

## Pre-freeze realizability

No held-out or hidden gate may be frozen until, without using its hidden payload:
- every carrier surface requirement is satisfied;
- the runtime can represent the required invocation contract;
- the independent verifier is available and generically qualified;
- exact runtime/import closure is available;
- required orthogonality dimensions are realizable;
- recursive OBS proves a synthetic gate is necessary versus direct real-effect verification.

## Search and reuse

Before creating infrastructure, adapters, benchmarks, probes, or code:
1. search inherited Brain capabilities;
2. search connected tools and systems;
3. search existing software, APIs, libraries, CLIs, databases, solvers and models;
4. compose existing routes;
5. adapt only when reuse/composition is insufficient;
6. invent last.

Stop search once recursive OBS establishes an adequate route whose plausible competitors cannot justify delaying execution.

## Capability package definition

A capability counts as acquired only when inheritance records:
- capability ID and useful behavior;
- invocation contract;
- supplier/version or deterministic implementation;
- prerequisites;
- independent verification method;
- provenance;
- latency and incremental cost;
- known failure modes;
- at least one successful real task;
- fresh reuse evidence when practical.

## Hard scoreboard

Canonical scoreboard:
- canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json

Progress counters:
- reusable_capabilities_inherited;
- verified_real_tasks_completed;
- fresh_reuse_passes;
- frontier_dependencies_removed;
- residual_gaps_localized.

Compliance/efficiency may track OBS-related avoided work, but OBS activity itself is never progress.

## Infrastructure law

Reuse existing qualified infrastructure by default.

New infrastructure is forbidden unless a current real task plus recursive OBS proves:
- existing routes are insufficient;
- the infrastructure blocker is causal;
- bypass/substitution is inferior;
- building the infrastructure is the fastest sufficient route to real output.

## Automatic deletion after inheritance

Every acquired capability triggers OBS-6 immediately.

Queued work made unnecessary by the new capability must be marked obsolete/superseded rather than completed ceremonially.

## Stop rule

If work can succeed while leaving reusable capability, verified real-task completion, inheritance, frontier dependency, and residual-gap state unchanged, it is supporting work and receives no progress credit.

If recursive OBS shows the entire path can be deleted or bypassed, stop the path immediately.

## Priority

1. correctness and real useful capability;
2. minimum wall-clock time to verified reusable output;
3. minimum incremental cost;
4. reuse/deletion/generalization;
5. verification strength;
6. minimum infrastructure, probes, context, compute and complexity.
