# FRONTIER CAPABILITY OBSOLESCENCE MISSION LOCK V3

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Supersedes as top-level objective:
- canonical/laws/FRONTIER_CAPABILITY_SUPERWORKER_MISSION_LOCK_V2.md

## Terminal objective

Project Brain exists to make **frontier-model capability dependency obsolete**.

For every useful behavior currently associated with a frontier model or agent, determine what part of the outcome truly depends on frontier-model-internal capability, then replace that dependency with the cheapest sufficiently general combination of explicit algorithms, retrieval, software, tools, solvers, databases, search, experiments, external systems, smaller models, reusable state, or newly built mechanisms.

The useful real-world outcome must survive or improve.

The terminal direction is:

required frontier-model capability dependency -> 0

This does NOT mean useful functions disappear. It means the requirement that a frontier model permanently possess those functions internally disappears.

## Parameter analogy

The precedent is parameter obsolescence.

The project did not attempt to reproduce all knowledge inside another giant parameter store. It attacked the requirement that knowledge/capability be permanently encoded in model weights by externalizing knowledge and acquiring what is needed at runtime.

Apply the same method recursively to frontier capabilities themselves.

Do not ask only:
- how do we match frontier planning?
- how do we match frontier research?
- how do we match frontier coding?
- how do we match frontier memory?
- how do we match frontier computer use?

Ask first:

> Why must a frontier model possess this capability internally at all?

Then attempt to remove that dependency while preserving the useful effect.

## Obsolescence loop

For each frontier-dependent behavior:

1. define the real consequential outcome;
2. identify the exact frontier-model contribution currently believed necessary;
3. construct a causal test that can falsify that necessity;
4. search the hidden warehouse before invention;
5. substitute external/JIT/general mechanisms for the frontier-model contribution;
6. run the same real task under the reduced dependency;
7. independently verify outcome equivalence or improvement;
8. if the outcome survives, mark that frontier-model dependency obsolete;
9. compile the substitute path into canonical reusable machinery;
10. recurse on the remaining frontier-model dependency.

A successful substitute is not merely another capability added to the inventory. It removes a dependency from the irreducible model-capability set.

## Hidden warehouse law

Before adding model capability, search all legitimate existing sources of useful function:
- deterministic algorithms;
- libraries and applications;
- APIs and services;
- retrieval and databases;
- search and documentation;
- formal solvers;
- compilers/interpreters;
- browsers/computer-control systems;
- experiments and measurement;
- external models where useful;
- reusable prior Brain capabilities;
- newly discovered compositions.

Only invent when the existing solution space is inadequate.

## Irreducible frontier set

Maintain an explicit set R of frontier-model-internal functions that remain causally necessary after successful obsolescence experiments.

R is not a wishlist and not a capability map.

A function may remain in R only when:
- a real consequential task requires it;
- proposed substitutes have been tested;
- the substitutes fail for a specific causal reason;
- the evidence is preserved;
- no cheaper/general route is currently adequate.

The primary research objective is to shrink R.

## Progress metric

Primary pre-scaling metric:

verified reduction in required frontier-model capability dependency

Secondary metrics:
- outcome correctness;
- generalization;
- autonomy;
- wall-clock latency;
- incremental cost;
- robustness/recovery;
- reusable inheritance;
- independent verifiability.

Capability count, benchmark count, parameter count, worker count, infrastructure count, or internal predicate count are not primary progress measures.

## Frontier systems

Astra, Opus-class systems, and other frontier agents/models are:
- sources of observed useful behaviors;
- challenge generators;
- comparison references;
- suppliers when causally useful.

They are not:
- implementation blueprints;
- terminal architecture targets;
- required providers;
- sacred irreducible capability sets.

A frontier capability map is an **obsolescence queue**, not an acquisition checklist.

## Reproducibility

The Superworker architecture must remain reproducible, but reproduction is subordinate to the terminal objective.

A clean worker must be able to reconstruct the obsolescence machinery and inherited substitutes from canonical state without hidden mutable state.

## Anti-regression law

Never replace a frontier-model dependency with a weaker proxy and call it obsolete.

Obsolescence is valid only when the same relevant real-world effect is preserved or improved under comparable constraints.

Internal benchmarks may support evidence but cannot define success by themselves.

## Capability compilation

When a dependency is obsoleted, preserve:
- the task class;
- former frontier-model dependency;
- substitute mechanism;
- causal rationale;
- source/provenance;
- invocation contract;
- preconditions;
- failure modes;
- verification method;
- measured latency/cost;
- regression tasks.

The next worker should inherit the substitute without rediscovering it.

## Current phase

The existence question is closed: P_real = 1.

The active program is now:

1. RECOVER / NORMALIZE THE FRONTIER DEPENDENCY MAP
2. SELECT THE HIGHEST-LEVERAGE FRONTIER-MODEL DEPENDENCY
3. RUN AN OBSOLESCENCE EXPERIMENT
4. VERIFY SAME/BETTER REAL OUTCOME
5. REMOVE THAT DEPENDENCY FROM R
6. COMPILE THE SUBSTITUTE
7. REPEAT
8. CLEAN-ROOM REPRODUCE THE SHRINKING SYSTEM
9. SCALE ONLY AFTER THE CORE IS SUFFICIENTLY GENERAL AND STABLE

## Mandatory pre-action question

Before every consequential action ask:

> Does this action directly reduce a currently necessary frontier-model capability dependency, prove that a dependency is irreducible, preserve a verified substitute, or remove the current causal blocker to doing so?

If NO, abort unless required for safety, correctness, evidence preservation, or canonical consistency.

## Priority

Correctness first.
Then maximum verified frontier-dependency reduction per wall-clock time.
Then minimum compute/cost/context/energy consistent with the first two.
