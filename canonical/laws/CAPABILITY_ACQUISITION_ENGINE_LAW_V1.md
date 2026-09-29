# CAPABILITY ACQUISITION ENGINE LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

## Purpose

Project Brain is a capability acquisition engine, not a benchmark factory.

The terminal objective remains unchanged: systematically obsolete useful frontier-model capabilities by finding verified equal-or-better capability routes with minimum wall-clock time and incremental cost.

## Unit of progress

Progress is credited only when at least one parent-level state changes:

1. a reusable capability is acquired and bound;
2. a real consequential task is completed using that capability;
3. the result is independently verified;
4. the capability is inherited so future workers can reuse it without rediscovery;
5. a previously required frontier-model contribution is removed;
6. an irreducible residual capability gap is localized with evidence sufficient to change the next frontier decision.

PRs, commits, tests, benchmarks, probes, gates, carrier qualifications, infrastructure, package discovery, and workflow runs receive ZERO progress credit by themselves.

## Default operating loop

REAL TASK
-> IDENTIFY MISSING CAPABILITY
-> SEARCH / REUSE BEFORE INVENTION
-> ACQUIRE OR COMPOSE ROUTE
-> EXECUTE REAL WORK
-> INDEPENDENTLY VERIFY
-> INHERIT WINNER
-> REUSE ON FRESH WORK
-> RECOMPUTE FRONTIER

Synthetic probes are subordinate support tools only.

## Real-task-first rule

The default next action MUST be a real task that exercises a useful capability.

A synthetic probe is allowed only when:
- one exact unresolved predicate blocks execution of the current real task;
- the probe is the fastest reliable way to resolve that predicate;
- its result directly determines the next real-task action.

When the predicate is resolved, the system MUST return immediately to real work.

## Probe budget

For each real capability acquisition mission:
- at most one synthetic support probe may run without a parent-level output change;
- a second support action requires a documented falsification showing the first could not resolve the blocker;
- after two support actions without real capability output, the target MUST be recomputed rather than extended by default.

Creating another held-out gate is NOT an automatic next step.

## Pre-freeze realizability rule

No held-out or hidden gate may be frozen until, without using its hidden payload:
- the execution carrier satisfies every frozen surface requirement;
- the runtime can represent the required invocation contract;
- the independent verifier mechanism is available and generically qualified;
- exact runtime/import closure is available;
- the required orthogonality dimensions are realizable.

A gate that fails these checks must never become the active frontier.

## Search and reuse

Before creating infrastructure, adapters, benchmarks, or probes:
1. search inherited Brain capabilities;
2. search connected tools and existing software;
3. search public implementations and documentation;
4. compose existing routes;
5. adapt only when reuse/composition is insufficient;
6. invent last.

## Capability package definition

A capability counts as acquired only when the inheritance record contains:
- capability ID and real useful behavior;
- invocation contract;
- supplier/version or deterministic implementation;
- prerequisites;
- independent verification method;
- known failure modes;
- wall-clock and incremental cost;
- provenance;
- at least one successful real task;
- a fresh reuse result when practical.

## Hard scoreboard

The control plane MUST track:
- reusable_capabilities_inherited;
- verified_real_tasks_completed;
- fresh_reuse_passes;
- frontier_dependencies_removed;
- residual_gaps_localized;
- median_capability_acquisition_wall_s;
- incremental_spend_usd;
- synthetic_support_actions_since_last_real_output.

The last metric is a liability, not an achievement.

## Infrastructure law

Existing qualified infrastructure is reused by default.

New infrastructure is forbidden unless a current real task proves existing infrastructure inadequate and the new infrastructure is the fastest route to parent-level capability output.

## Stop rule

If work can succeed while leaving reusable capability, real-task completion, inheritance, frontier dependency, and residual-gap state unchanged, it is supporting work and receives no progress credit.

If supporting work begins to dominate the critical path, abort and recompute.

## Priority

1. correctness and real useful capability;
2. minimum wall-clock time to reusable capability output;
3. minimum incremental cost;
4. reuse and generality;
5. verification strength;
6. minimum infrastructure, probes, context, compute, and complexity.

The best part is no part. Delete machinery that does not increase verified reusable capability.
