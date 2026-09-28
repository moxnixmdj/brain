# CAPABILITY OBSOLESCENCE ARBITRAGE STRATEGY V2

Status: CANONICAL / MANDATORY / EXECUTION STRATEGY

Authority:
- canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_OBSOLESCENCE_MISSION_LOCK_V4.md

Supersedes:
- canonical/laws/CAPABILITY_ARBITRAGE_RUNTIME_STRATEGY_V1.md as the active capability strategy
- canonical/laws/ASTRA_CLOSURE_RACE_STRATEGY_V1.md as the active closure strategy

## Mission

For each frontier capability, find the fastest and cheapest realizable route that provides at least the same useful capability, preferably more.

Then verify it, inherit it, and treat the frontier implementation as obsolete for Project Brain.

## Core loop

**OBSERVE FRONTIER CAPABILITY
-> DEFINE REAL EFFECT
-> ESTABLISH FRONTIER BAR
-> DISCOVER ROUTES
-> RACE ROUTES
-> EXECUTE REAL WORK
-> VERIFY >= FRONTIER
-> OBSOLETE
-> INHERIT
-> RECOMPUTE**

## Route race

For each capability, race only useful independent approaches:

A. DIRECT REUSE
- existing software/system already has the capability.

B. COMPOSITION
- combine multiple weaker/specialized components into a stronger capability.

C. JIT ACQUISITION
- discover and bind the necessary capability at runtime.

D. DETERMINISTIC/SPECIALIZED SUBSTITUTE
- solver, algorithm, database, compiler, theorem prover, CV system, search engine, etc.

E. MODEL SUPPLIER
- use the smallest/cheapest adequate model, including frontier models when they actually win.

F. ADAPTATION
- modify a close existing solution.

G. INVENTION
- only after better existing routes are absent, falsified, or slower.

Stop losing routes as soon as sufficient evidence establishes they cannot win under the target constraints.

## Candidate ranking

Rank by this order:

1. correctness / capability strength;
2. wall-clock time to useful result;
3. incremental cost;
4. reliability;
5. generalization;
6. integration time;
7. provider replaceability;
8. compute;
9. verification quality;
10. maintenance burden.

A route that is cheap but weaker does not obsolete the frontier capability.

A route that is stronger but unusably slow may be useful evidence, but does not automatically win the operational race.

## Knowledge precedent

Knowledge is not a capability deficit to reconstruct inside model parameters.

Use JIT/external knowledge acquisition as the default precedent:
- authoritative retrieval;
- durable memory;
- provenance;
- verification;
- currentness.

Only treat a knowledge-side issue as reopened if real tasks falsify the current knowledge architecture.

## Inheritance

Each verified obsolescence win must store:
- capability ID;
- real target behavior;
- frontier bar/evidence;
- winning route;
- losing/falsified routes worth preserving;
- exact supplier/version;
- adapter;
- cost;
- latency;
- compute;
- limitations;
- verification method;
- regression tasks;
- fallback suppliers.

## Multi-capability leverage

Prefer substitutes that obsolete several apparent frontier capabilities at once.

Example:
a strong generic solver/retrieval/composition mechanism that removes separate requirements for multiple model-internal skills has higher leverage than one narrow one-off adapter, assuming real capability remains equal or better.

## Worker allocation

Use workers as search, integration, execution, falsification, and verification capacity.

Do not optimize worker count.

Allocate effort to minimize time until the highest-leverage capability is genuinely obsoleted.

Parallelize route races only when they are independent and the expected reduction in wall-clock exceeds coordination overhead.

## Terminal condition

The program is not complete at "parity."

It continues until the useful frontier capability set has been systematically processed and:
- each target capability has a verified equal-or-better route under the project constraints; or
- the exact remaining irreducible frontier capability deficit is known and actively bounded by evidence.

The ideal limiting case is that the frontier model is no longer uniquely necessary for any target useful behavior, but this is a discovered result, not an assumption.
