# CAPABILITY ACQUISITION ENGINE LAW V5

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Authority:
- canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_OWNERSHIP_MISSION_LOCK_V5.md
- canonical/laws/RECURSIVE_OBSOLESCENCE_CONTROL_LAW_V3.md
- canonical/laws/REASONING_DURABILITY_AND_DECISION_RECEIPT_LAW_V1.md

Supersedes:
- canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V4.md

## Purpose

Project Brain permanently acquires useful capabilities equal to or better than Opus 5.5. Knowledge remains external and is retrieved JIT.

## Unit of progress

Progress is credited when:
1. a target Opus 5.5 useful capability is defined;
2. an already-existing realization is found;
3. the realization is configured into Brain;
4. the configured Brain capability is verified at or above the Opus 5.5 bar;
5. the capability package is saved durably;
6. future work can invoke it without capability rediscovery.

PRs, probes, benchmarks, runtime repairs, route searches, and task executions receive zero capability credit by themselves.

## Default capability loop

DEFINE OPUS 5.5 USEFUL CAPABILITY
-> SEARCH EXISTING REALIZATIONS
-> RACE SUFFICIENT CANDIDATES
-> CONFIGURE/INTEGRATE WINNER
-> VERIFY >= OPUS 5.5
-> SAVE PERMANENT CAPABILITY PACKAGE
-> INHERIT GLOBALLY
-> RECOMPUTE ENVELOPE

Real tasks are evidence for verification and regression. They are not the default mechanism for discovering a new capability after normal task execution has already begun.

## Knowledge boundary

Knowledge needed during acquisition or operation must be retrieved externally/JIT.

Do not create a permanent knowledge-replication project.

Preserved evidence, provenance, compact decision state, and caches are allowed, but are not counted as capability ownership.

## No invention

Underlying useful capability invention is forbidden under this program.

Allowed creation is limited to integration glue:
- configuration;
- adapters;
- packaging;
- routing;
- persistence;
- verification;
- regression protection;
- recovery.

If no existing equal-or-better realization is found after adequate search, mark the capability unresolved and record a theory-falsification candidate.

## Search law

Search order is broad and parallel where safe:
1. already-owned Brain capabilities;
2. existing installed/configurable software and tools;
3. libraries, CLIs, solvers, runtimes, local models/artifacts already legitimately available;
4. connected systems and existing agent/model capabilities that can be durably configured as part of Brain;
5. compositions of existing capabilities.

Do not add "invent capability" as a final search step.

Stop when a candidate can be configured into Brain and is sufficiently evidenced to meet/exceed the Opus 5.5 bar, unless a plausible dominator can be resolved cheaply enough to reduce total wall-clock.

## Ownership test

A candidate is not acquired if normal future use still requires rediscovering what capability to use, how to configure it, or how to verify it.

Ownership requires a durable capability package under the V5 mission lock.

## Repair rule

After a failure, first ask whether a different already-existing capability realization can replace the failing route.

Repair only integration/configuration around the chosen existing realization when that is faster than switching.

Do not recursively build a new cognitive capability from micro-repairs merely because the current implementation exposes another gap.

## Reasoning durability

Every consequential acquisition decision must persist a compact reasoning/decision receipt containing:
- objective;
- governing theory invariants;
- material facts/evidence;
- conclusion;
- selected route;
- rejected material alternatives and decisive reasons;
- uncertainties;
- supersession conditions;
- next action.

No silent reasoning drift is authoritative.

## Priority

1. real capability >= Opus 5.5;
2. permanent Brain ownership;
3. minimum wall-clock;
4. $0 incremental spend;
5. minimum machinery and complexity.
