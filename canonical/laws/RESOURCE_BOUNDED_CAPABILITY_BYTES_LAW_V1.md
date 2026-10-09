# RESOURCE-BOUNDED CAPABILITY BYTES LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Authority:
- canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V9.md
- canonical/laws/CAPABILITY_ACQUISITION_ENGINE_LAW_V8.md
- canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V2.md
- canonical/capabilities/opus55/ATOMIC_CAUSAL_INTELLIGENCE_MAP_V1.json

## Purpose

Minimize the persistent executable information required to own the required capability set after knowledge, deterministic computation, tools, memory, verification, and already-owned mechanisms have been subtracted.

The target is not "compress a model." The target is the smallest resource-feasible executable description of the required capability set conditional on the Brain substrate already owned.

## Objective

For required capability set C and already-owned substrate S, optimize a resource-bounded joint description:

B*_R(C | S) = min [ L(K,Q,D) + sum_i L(delta_i) ]

where K is genuinely necessary shared cognition, Q is routing/control information, D is decoder/loader machinery, and delta_i are capability-specific residuals.

A candidate is admissible only when:
- every claimed capability remains at or above its required frontier bar;
- donor deletion and ownership requirements pass;
- held-out qualification remains clean;
- non-interference and control regressions are acceptable;
- runtime, RAM, compute, reliability, and hard incremental-spend bounds pass.

Fewest bytes alone is not sufficient.

## Exact accounting

Every retained persistent dependency counts. At minimum account for:
- parameter or code values;
- sparsity masks and indices;
- routers and dispatch tables;
- decoder/loader machinery;
- unavoidable base substrate bytes not already counted in S;
- configuration, prompts, policies, and persistent control state;
- capability-specific residual artifacts.

A small adapter does not make an undisclosed required base disappear.

Report these separately:
- B_exec: persistent bytes required to execute the capability;
- B_verify: persistent online verification machinery required for autonomous correctness;
- B_proof: receipts, logs, historical evidence, and governance records;
- B_JIT: transient task knowledge.

B_proof is necessary for governance but is not cognition.
B_JIT is not persistent capability storage.
Their storage/runtime costs must still be reported where operationally relevant.

## Joint rather than independent minimization

Minimize the complete capability set jointly.

Count shared artifacts once.

For an acquisition order C_1...C_n:
- marginal byte cost is Delta B_i = B(C_1:i) - B(C_1:i-1);
- terminal byte cost is B(C_1...C_n).

A capability may therefore have near-zero marginal bytes while depending on a nonzero shared substrate. Do not confuse marginal cost with terminal substrate size.

## Elicit-before-teach law

For every surviving residual, search in increasing durable-information budget:

1. zero new bytes: existing Brain composition;
2. deterministic configuration/router/policy;
3. tiny elicitation key, prompt, mask, or activation/control direction;
4. sparse or low-rank residual;
5. compact learned module;
6. larger learned machinery only when smaller classes are falsified.

Latent-vs-taught diagnostics may guide this search. They are search signals, not proof of the final byte requirement.

## First-irreducible-failure teaching

When new learned information is necessary, do not default to full donor imitation.

Run the Brain-owned attempt, localize the earliest irreducible missing transformation, teach or harvest only that transformation, rerun, and repeat only if a later irreducible failure remains.

Each added residual must independently survive ownership, held-out, dependency, and minimization gates.

## Bidirectional search

Search from both directions:
- bottom-up: grow from zero bytes through increasingly expressive candidate mechanism classes;
- top-down: shrink a donor or existing implementation by causal replaceability, dependency deletion, structured pruning, rank/precision reduction, specialization, and distillation.

Both searches use the same verifier and accounting law.

## Dependency obsolescence

The donor's historical packaging has no authority over the retained byte count.

For models, libraries, frameworks, prompt packs, adapters, skills, or software packages:

donor -> capability contract -> causal dependency closure -> delete everything outside that closure -> repair incidental coupling without widening the contract -> verify -> remove original donor dependency.

Dynamic reachability alone is insufficient for promotion because unexercised capability branches can be missed.

## Global verified mechanism cover

Represent each verified mechanism as:

mechanism = (covered atomic behaviors, dependencies, unique persistent bytes, runtime properties, reliability properties, evidence state)

Then choose the minimum-byte verified composition whose dependency closure covers every required atomic behavior and satisfies all non-byte constraints.

For a finite enumerated mechanism library, an exact optimizer may truthfully claim:

"minimum-byte verified composition over the enumerated eligible mechanism library."

It may not claim the unrestricted universal information-theoretic minimum.

## Computability boundary

The unrestricted shortest executable description is not computable in general.

Therefore:
- continuously tighten verified upper bounds;
- establish lower bounds within explicit representation classes where possible;
- exhaust finite candidate classes when feasible;
- state the remaining gap;
- never relabel a finite-library optimum as a universal Kolmogorov optimum.

## Promotion boundary

Byte reduction alone grants zero capability, ownership, family, benchmark, or terminal credit.

Promotion still requires the governing capability law, donor-deletion law where applicable, untouched qualification, and exact Brain-route verification.

## Stop rule

Stop minimization when further byte reduction is dominated by increased wall-clock, memory, compute, reliability risk, verification burden, or total mission cost, or when a smaller already-owned route satisfies the same contract.
