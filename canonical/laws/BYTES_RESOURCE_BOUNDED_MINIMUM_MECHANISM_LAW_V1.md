# BYTES RESOURCE-BOUNDED MINIMUM MECHANISM LAW V1

Status: CANONICAL / MANDATORY FOR BYTES MINIMIZATION / FAIL-CLOSED

Authority and composition:
- canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V1.md
- canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V7.md
- canonical/capabilities/opus55/ATOMIC_CAUSAL_INTELLIGENCE_MAP_V1.json

This law supplements the white-box harvesting law. It does not weaken donor deletion, causal sufficiency, held-out qualification, provenance, licensing, dependency accounting, or fail-closed behavior.

## Mission

For the complete required capability set C and already-owned Brain substrate S, minimize the persistent executable description required to meet the capability bar under real runtime constraints.

The target is not "compress a model" and not "minimize parameter count."

The target is the minimum verified composition of mechanisms conditional on what Brain already owns.

## Resource-bounded objective

Define a candidate composition R by its complete unavoidable persistent representation:

B(R) =
  B_values
+ B_masks_and_indices
+ B_router
+ B_decoder_loader
+ B_unavoidable_base
+ B_configuration
+ B_other_persistent_dependencies.

A candidate is admissible only if all required constraints hold:

- capability(C, S + R) >= required bar;
- donor runtime dependency = zero after promotion;
- held-out generalization passes;
- latency <= declared bound;
- peak memory <= declared bound;
- compute <= declared bound;
- reliability >= declared minimum;
- non-interference and compatibility constraints hold;
- all operative dependencies are explicitly counted.

Minimize B(R) over admissible discovered mechanisms.

A tiny adapter that requires a giant base does not have a tiny total footprint. Hidden dependencies count.

## Accounting partitions

Track separately:

- B_exec: persistent bytes required to execute the capability;
- B_verify: persistent online verification machinery required for autonomous correctness;
- B_proof: receipts, experiment logs, qualification evidence, and governance history;
- B_JIT: transient task knowledge acquired just in time.

Only B_exec and unavoidable online B_verify belong in the executable capability footprint.
B_proof remains mandatory governance evidence but is not cognition.
B_JIT is not persistent capability storage.

Never erase these partitions by reporting one undifferentiated directory size.

## Marginal versus terminal bytes

For ordered acquisition of capabilities C_1...C_n:

delta_B_i = B(C_1...C_i) - B(C_1...C_{i-1})

is marginal byte cost.

B_terminal = B(C_1...C_n)

is the final complete substrate cost.

A capability may have near-zero marginal bytes because required machinery is already shared. The shared substrate is still counted exactly once in B_terminal.

## Elicit-before-teach law

For every residual behavior, search in increasing persistent-information budget:

1. ZERO NEW BYTES
   - existing Brain composition;
   - deterministic route;
   - already-owned mechanism.

2. TINY KEY
   - configuration;
   - routing rule;
   - prompt/control state;
   - mask/index selection;
   - activation/control direction where operatively sufficient.

3. SMALL DELTA
   - sparse delta;
   - low-rank delta;
   - expert/module selection;
   - compact donor-derived residual.

4. TAUGHT RESIDUAL
   - smallest learned module that supplies the missing transformation.

5. LARGER MODULE
   - only when smaller classes have been falsified under the declared scope.

Evidence suggesting latent capability is a search signal, not proof of required byte count.

## Atomic residual teaching

Do not imitate a donor trajectory merely because it exists.

Run the Brain-owned route first.
Locate the earliest irreducible causal failure.
Acquire only the missing transformation.
Retry.
Repeat only if a later irreducible failure remains.

This is counterexample-guided capability distillation.

Whole-trajectory or whole-model distillation requires evidence that the smaller residual route is insufficient.

## Bidirectional minimization

Search simultaneously:

Bottom-up:
zero-byte reuse -> tiny key -> sparse/low-rank residual -> compact module -> larger module only if required.

Top-down:
donor -> causal dependency closure -> remove replaceable machinery -> structured deletion -> rank/precision reduction -> specialized branch retention -> donor deletion.

Both searches use the same target contract and verifier.

## Joint global factoring

Independent per-capability minimization is not the terminal objective.

Represent each discovered mechanism m_j with:
- atomic behaviors covered;
- dependencies;
- persistent bytes;
- latency;
- RAM;
- compute;
- reliability;
- compatibility/interference constraints;
- evidence.

Find the minimum-weight verified composition whose dependency closure covers every required atomic behavior.

Shared cognition is counted once.

This may be implemented as a constrained minimum-weight set/hypergraph cover over the finite discovered mechanism library.

The exact optimum over a finite known mechanism library may be claimed when exhaustively solved.
The unrestricted universal shortest executable description may not be claimed.

## Dependency obsolescence

Treat neural models, libraries, frameworks, prompt packs, adapters, skill repositories, and software packages under the same causal rule:

donor
-> define capability contract
-> identify causal dependency closure
-> delete everything outside that closure
-> repair incidental coupling without widening scope
-> verify
-> delete original donor.

Historical packaging has zero authority over the final retained byte count.

## Promotion gates

No candidate receives promoted capability credit unless all applicable gates pass:

- target contract frozen;
- donor positive control;
- ablation;
- rescue;
- specificity;
- untouched held-out qualification;
- complete dependency accounting;
- runtime resource bounds;
- donor deletion;
- exact future Brain route verification;
- cross-capability regression/non-interference checks;
- byte accounting partitions recorded;
- smaller discovered admissible compositions ruled out by the optimizer.

## Research-state truth boundary

Research checkpoints may record promising reductions before promotion.

A checkpoint must distinguish:
- measured result;
- derived inference;
- hypothesis;
- rejected branch;
- promoted capability.

Calibration success is not untouched qualification.
Untouched qualification is not universal scope proof.
A small constructed mechanism is not donor-harvest credit unless the governing acquisition rules permit that origin.

## Stop rule

Stop reducing a candidate when no discovered smaller admissible composition beats it under the resource-bounded objective, or when further acquisition/minimization has negative expected mission value.

Resume when a new mechanism, stronger verifier, lower-cost dependency closure, or newly exposed capability obligation changes that result.
