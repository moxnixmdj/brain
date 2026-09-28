# Capability Arbitrage Runtime Strategy V1

> Superseded on 2026-09-28. V1 correctly introduced capability arbitrage but still framed the terminal program as acquiring Astra capabilities. V2 keeps the arbitrage machinery and changes the terminal objective to capability obsolescence.

Status: SUPERSEDED AS ACTIVE STRATEGY BY CAPABILITY_OBSOLESCENCE_ARBITRAGE_STRATEGY_V2 / RETAINED AS HISTORICAL PRECURSOR

## Mission

Make the actual useful capabilities demonstrated by Astra real in Project Brain, our way.

Our way is **capability arbitrage**:

> discover the strongest existing capability available anywhere -> bind it into the shared runtime -> replay real work -> independently verify the gain -> make the verified capability permanently inherited by the Brain and every future worker.

The loop is:

**DISCOVER -> BIND -> REPLAY -> VERIFY -> INHERIT**

Then recompute the largest remaining capability deficit and repeat.

## Optimization target

Maximize:

**verified target-capability gain / wall-clock time**

subject to:
- correct route only;
- $0 incremental spend;
- no fake capability credit;
- no provider lock-in where avoidable;
- no rebuilding an adequate existing capability;
- no predicate, benchmark, worker-count, or infrastructure proxy replacing the real capability goal.

If several deficits are tied and independent, acquire them in parallel.
Otherwise attack the single highest-leverage deficit first.

## Architecture

User goal / interface
-> persistent shared Project Brain runtime
-> capability graph + router
-> interchangeable cognition/models
-> external/JIT knowledge
-> tools, apps, APIs, browsers, computer-use systems
-> deterministic programs / solvers
-> verifiers
-> durable state/evidence

No model, tool, worker, provider, benchmark, or predicate is the architecture.
All are replaceable capability suppliers.

## Knowledge law

Do not use model parameters as the warehouse for knowledge that can be acquired externally.
Prefer authoritative, current, on-demand knowledge and durable external memory.
Models provide cognition; the Brain owns durable knowledge/state/provenance.

## Acquisition procedure for each capability deficit

1. Define the missing real-world ability operationally from target behavior, not from an internal predicate.
2. Search Project Brain and already-connected tools for an existing solution.
3. Search the Plugin/tool ecosystem and available services.
4. Search GitHub/OSS and technical ecosystems.
5. Search current web, papers, demos, communities/social sources where relevant.
6. Search available strong models/providers and model-composition routes.
7. Rank candidates by:
   - capability strength on the needed behavior;
   - integration time;
   - reliability;
   - $0 feasibility;
   - provider independence / replaceability;
   - evidence quality.
8. Bind the strongest adequate candidate with the thinnest adapter possible.
9. Replay one or more real consequential missions that require the capability.
10. Inspect actual results and classify residual failure.
11. If capability gain is real, independently verify and inherit it permanently into the runtime/Brain.
12. If it fails, preserve passing parts and repeat discovery only for the residual deficit.
13. Invent only after the relevant existing-solution search space has been exhausted or falsified.

## Inheritance rule

A verified capability gain must become reusable by later work without rediscovery.

Inheritance includes:
- capability description;
- exact provider/tool/model/program route;
- invocation contract;
- prerequisites;
- failure modes;
- evidence;
- fallback route;
- cost constraint;
- provenance;
- version/currentness;
- integration code or skill.

Future workers consume inherited capabilities rather than reconstructing them.

## Real mission rule

Real missions are used to expose and integrate capability.
They are not the roadmap themselves.

Choose missions because they maximally exercise the largest unresolved capability deficit and expose whether the integrated runtime can actually do useful work.

## Anti-reconstruction law

Do not rebuild a capability internally merely because Project Brain can.
If an adequate existing capability can be acquired and bound faster, acquire it.

Internal invention is justified only when:
- no adequate existing capability exists;
- existing routes violate hard constraints;
- integration would be slower or less reliable than invention;
- provider dependence would destroy the mission;
- or a residual capability must be invented after external routes are falsified.

## Worker law

Workers are deployment containers for inherited capability.
They are not the product and they are not the development unit.

Do not block capability acquisition on proving one perfect worker.
Do not scale weak capability.
Once the shared runtime is strong, package it into persistent workers and reproduce it.

## Verification law

Verification answers: "Did the newly bound capability actually work?"
Verification must never become the thing being optimized.

No self-certification.
No cross-executor evidence stitching for claims about one executor.
No internal suite may establish external parity by definition.

## Current execution priority

1. Reconcile the target Astra capability graph against capabilities already inherited by Project Brain.
2. Rank remaining deficits by capability gain / wall-clock time.
3. For the top deficit, perform a bounded but broad existing-solution discovery sweep.
4. Bind the strongest adequate $0 route.
5. Replay consequential real work.
6. Verify and inherit the gain.
7. Immediately recompute the frontier and continue.

## Terminal condition

The mission is not complete because a benchmark, suite, or worker definition passes.

It is complete only when the target capabilities are genuinely available through the shared Project Brain runtime at useful strength, reliability, breadth, and autonomy, with durable inheritance and no known higher-leverage unresolved deficit under the declared constraints.
