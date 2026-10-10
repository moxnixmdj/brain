# Executable Refinement + Terminal Closure Design

Date: 2026-10-09  
Repository: `moxnixmdj/brain`  
Status: DESIGN_APPROVED_IN_CHAT__WRITTEN_SPEC_PENDING_USER_REVIEW  
Objective: preserve the current mission objective while closing the highest-dominance proof gap between abstract verified semantics and the executable runtime.

## 1. Mission lock

The authoritative mission remains:

`BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`.

This design does not award checkpoint, benchmark, acceptance, capability-family, or terminal credit by itself. It introduces a fail-closed bridge required before an abstract/controller theorem can be treated as verified-live executable authority.

## 2. Problem

Current Brain governance already binds many runtime artifacts by exact Git blob SHA and independently verifies bounded behavior. That proves important properties of selected source/runtime artifacts and exact test surfaces.

The remaining terminal gap is the unsupported implication:

`ABSTRACT_OR_MODEL_LEVEL_THEOREM_CORRECT => CONCRETE_EXECUTABLE_BEHAVIOR_CORRECT`.

Artifact identity, source tests, isolated replay, build provenance, and runtime attestation answer different questions. In particular:

- a proof that an abstract controller/specification is correct does not prove a concrete implementation refines that specification;
- a hash proves artifact identity, not semantic refinement;
- attestation proves which approved artifact is loaded/executing, not why that artifact inherits the abstract theorem;
- regression tests sample behaviors but do not prove absence of additional goal-relevant concrete behavior.

The terminal system therefore needs an explicit proof-carrying refinement relation from the abstract semantics actually used by a theorem to the executable behavior actually admitted by the runtime.

## 3. Design principle

Do not create a second planner, second router, second promotion authority, or general-purpose formal-methods tower.

Add one compositional obligation:

`EXECUTABLE_REFINEMENT_CERTIFICATE`

and one fail-closed verifier/kernel that answers only:

> For this declared subject, do all goal-relevant concrete behaviors remain within the behaviors allowed by the bound abstract specification, under the declared representation, parsing, nondeterminism, liveness, compiler/build, and binary-identity assumptions?

Existing proof, authority, routing, verification, and terminal layers remain authoritative for their existing claims.

## 4. Terminal theorem integration

The current terminal proof should expose a small dependency graph rather than infer deployment correctness from source/runtime binding alone.

For a verified-live capability path:

`GOAL_CONTRACT -> ABSTRACT_THEOREM -> EXECUTABLE_REFINEMENT -> BUILD/BINARY_IDENTITY -> DEPLOYED_RUNTIME_IDENTITY -> ACTUAL_EFFECT_BOUNDARY`.

Every edge must be separately typed.

A route may be:

- `SPECIFIED`: semantic contract exists;
- `IMPLEMENTED`: concrete implementation exists;
- `REFINEMENT_VERIFIED`: implementation refines the bound abstract contract;
- `VERIFIED_LIVE`: refinement-verified implementation is the current admitted runtime under the existing deployment/authority rules.

No terminal or capability claim may promote directly from `IMPLEMENTED` to `VERIFIED_LIVE`.

## 5. Refinement model

For a subject capability define:

- abstract state set `A`;
- concrete state set `C`;
- relation `R(c, a)`;
- concrete transition relation `c --tau_c--> c'`;
- abstract transition relation `a ==tau_a*==> a'`;
- goal-relevant observation projection `Obs_G`.

A certificate establishes, for every reachable concrete transition covered by the certificate:

1. an abstract state `a` exists with `R(c,a)`;
2. an admissible abstract transition sequence exists;
3. `R(c',a')` holds after the transition;
4. the concrete goal-relevant observation equals or safely refines the abstract observation;
5. extra concrete behavior outside the abstract allowance is rejected;
6. concrete internal stuttering does not violate declared liveness/progress obligations.

The core safety condition is a goal-relative trace refinement:

`Behaviors_G(concrete) subseteq Behaviors_G(abstract)`.

The liveness condition is separate. Safety refinement alone cannot certify a concrete implementation that can stutter forever while the abstract machine must progress.

## 6. Certificate schema

Introduce a versioned governance/verification object with fields equivalent to:

- `schema`
- `date`
- `subject_id`
- `abstract_spec`
  - canonical path
  - exact Git blob SHA
  - semantic/version identifier
- `concrete_implementation`
  - canonical path(s)
  - exact Git blob SHA(s)
  - implementation/version identifier
- `state_mapping`
  - abstract state schema
  - concrete state schema
  - relation/verifier identity
- `input_binding`
  - parser/serialization/canonical-encoding contract
- `transition_refinement`
  - supported concrete transition classes
  - allowed abstract correspondence
  - explicitly rejected/unsupported classes
- `observation_refinement`
  - goal-relevant observable fields
  - equality/refinement rules
- `nondeterminism_contract`
- `stuttering_and_liveness_contract`
- `build_chain`
  - source identity
  - compiler/interpreter assumptions when load-bearing
  - resulting executable/blob identity when applicable
- `proof_dependencies`
- `verification_receipt`
- `nonclaims`
- `terminal_credit_delta: 0` until all required terminal dependencies close.

The certificate must be content-bound. Mutable current pointers may bind by canonical path where existing governance already defines that rule; immutable versioned subjects bind by exact Git blob SHA.

## 7. Minimal verifier

Add a small fail-closed verifier rather than trusting a generator.

The verifier must:

1. reject unknown schema versions;
2. reject missing or mismatched subject/blob identities;
3. reject unrecognized transition classes;
4. reject unproved parser/representation mappings;
5. reject concrete behavior outside the declared abstract behavior set;
6. reject a safety-only certificate when the calling theorem requires liveness preservation;
7. reject stale refinement certificates when either abstract or concrete subject changes;
8. emit a typed receipt with exact dependency hashes;
9. never infer completeness from passing tests alone.

The verifier is promotion authority only for the refinement relation it checks. It does not grant benchmark, task-family, user-authority, or terminal credit.

## 8. First integration target

Do not attempt to verify the entire repository.

The first implementation target is the narrow current live/runtime promotion cone already used by the terminal authority, especially the certificate-gated selected-route/runtime path and one representative bounded current route.

Candidate existing integration surfaces observed on current main include:

- `canonical/runtime/certificate_gated_selected_route_runtime_entrypoint_v2.py`
- `canonical/runtime/general_adequate_decision_fixed_point_v2.py`
- current R2 bounded direct-route modules
- `canonical/governance/CURRENT_TERMINAL_AUTHORITY.json`
- current terminal reconciliation tests.

The exact first subject must be selected during implementation from the smallest live path whose abstract contract and executable transition surface are already explicit enough to make refinement mechanically checkable.

The design explicitly forbids claiming repository-wide executable refinement from that bounded first subject.

## 9. Existing machinery to reuse

Reuse rather than duplicate:

- exact Git blob binding already used throughout canonical governance;
- proof-carrying verification receipts;
- fail-closed unknown/unsupported semantics;
- current pointer versus immutable blob precedence;
- independent replay conventions;
- terminal `terminal_credit_delta: 0` accounting;
- current anti-self-certification rules;
- existing source/semantic proof kernels;
- current test/verification receipt style.

The refinement certificate becomes another typed dependency consumed by terminal truth, not a replacement for these mechanisms.

## 10. Parser and representation boundary

If an abstract theorem reasons about typed values while concrete code consumes bytes/text/JSON, the binding from concrete representation to abstract value is part of refinement.

A refinement certificate must not silently assume:

`"$599.00" == 59900 cents`.

It must either:

- prove/check the parser and canonical encoding contract; or
- treat the parser as an explicit trusted dependency and expose that trust in the certificate.

Ambiguous/noncanonical encodings must fail closed where they can change goal-relevant behavior.

## 11. Nondeterminism and liveness

Concrete restriction of abstract nondeterminism may preserve safety while breaking liveness.

Therefore certificates declare separately:

- `safety_refinement`
- `liveness_refinement`.

Internal concrete steps may map to abstract stutter only if they preserve protected observables and the relation `R`. If liveness is load-bearing, a well-founded progress argument, bounded stutter condition, or equivalent explicit theorem is required.

## 12. Generated artifacts

Models/workers remain untrusted proposal generators.

For generated code, policies, solver encodings, or workflow artifacts:

`GENERATE -> VERIFY_REFINEMENT -> PROMOTE`.

The generator is not part of the proof root merely because it created a passing candidate.

This preserves fast model-assisted construction while keeping semantic promotion deterministic and checkable.

## 13. Terminal closure graph

Add a machine-readable terminal dependency graph whose leaves are classified only as:

- `ENFORCED`
- `PROVED`
- `USER_AUTHORIZED`
- `ROOT`
- `UNRESOLVED`.

The graph must make the executable-refinement edge explicit for every route claiming `VERIFIED_LIVE`.

Unknown/unclassified leaves fail closed.

The graph is not itself a proof of closure. It is the canonical inventory consumed by systematic falsification and terminal reconciliation.

## 14. Systematic falsifier

After the first refinement verifier exists, attack each terminal dependency node with reusable failure families:

- negation;
- quantifier swap;
- composition mismatch;
- hidden state;
- timing;
- concurrency;
- crash/restart;
- rollback/fork;
- Byzantine input/component;
- finite-resource failure;
- version drift;
- revocation;
- adaptive selection;
- proxy/measurement failure where relevant;
- causal-confounding where relevant;
- novel/unmodeled dimension;
- implementation/refinement mismatch.

A family applies only where semantically meaningful. Passing the falsifier does not imply open-world completeness; the generator coverage and residual `OTHER/NOVEL` assumptions remain explicit.

## 15. Architecture minimization

The terminal dependency graph is also used to reduce machinery.

Each primitive/component is classified:

- `KEEP`: load-bearing unique obligation;
- `MERGE`: duplicate obligation with another primitive;
- `DERIVE`: can be produced mechanically from stronger existing state;
- `DEMOTE`: useful evidence/optimization but not terminal authority;
- `DELETE`: no terminal or recovery role and no declared future-option value.

Deletion remains subordinate to the current option-preserving optimization rule and proof-preserving history/retention semantics. Current dominance alone is not deletion authority.

## 16. Tests

Implementation must be TDD and include at minimum:

1. **identity mismatch RED**: concrete blob changes while old certificate remains -> verifier rejects;
2. **abstract mismatch RED**: abstract spec changes -> verifier rejects;
3. **extra concrete transition RED**: implementation exposes an undeclared goal-relevant branch -> verifier rejects;
4. **parser mismatch RED**: concrete representation maps to a different abstract value -> verifier rejects;
5. **safety-only/liveness-required RED** -> verifier rejects;
6. **unsupported transition class RED** -> fail closed;
7. **valid bounded refinement GREEN** -> typed receipt produced;
8. **terminal projection RED/GREEN**: a route cannot be labeled `VERIFIED_LIVE` without required refinement, then succeeds only when a valid certificate is bound;
9. existing affected regression suites remain green;
10. independent replay receipt records exact tested blobs and grants zero unrelated credit.

Where an exhaustive finite transition surface exists, use complete enumeration/differential comparison rather than examples alone.

## 17. Verification and promotion

Promotion sequence:

1. create candidate refinement verifier and certificate schema;
2. run focused RED/GREEN tests;
3. run affected runtime/terminal regression cone;
4. independent clean replay on an isolated carrier;
5. create immutable verification receipt with exact blobs;
6. activate bounded refinement authority with zero unrelated credit;
7. update current terminal truth to show the bounded executable-refinement edge as closed only for the exact certified subject;
8. leave repository-wide/general executable refinement explicitly open;
9. re-run the terminal dependency/falsifier pass.

Passing tests never directly grant terminal credit.

## 18. Nonclaims

This design makes no claim that:

- all Brain code is formally verified;
- source-level unit tests prove executable refinement;
- attestation implies semantic correctness;
- one bounded refinement proof generalizes to other routes;
- compiler correctness is established unless explicitly included;
- parser semantics are trusted unless explicitly declared/proved;
- safety refinement automatically preserves liveness;
- a machine-readable dependency graph proves its own completeness;
- the terminal mission is closed by implementing this design.

## 19. Success criteria

The design is implemented successfully when:

1. at least one live bounded route has an exact abstract-to-concrete refinement certificate;
2. the verifier fails closed on all enumerated mismatch classes;
3. terminal truth distinguishes `IMPLEMENTED`, `REFINEMENT_VERIFIED`, and `VERIFIED_LIVE`;
4. current terminal/runtime promotion cannot silently bypass the refinement obligation for the selected subject;
5. exact artifact identities and proof dependencies are replayable independently;
6. no unrelated acceptance or terminal credit is granted;
7. the terminal dependency graph identifies the next highest-dominance `UNRESOLVED` leaf after this bridge is closed.

## 20. Recommended implementation order

After this written spec is reviewed:

1. create the machine-readable certificate schema + fail-closed verifier;
2. bind one smallest representative current route;
3. add RED/GREEN refinement tests;
4. add terminal dependency projection and anti-bypass test;
5. independently replay the exact bounded cone;
6. promote zero-credit bounded authority;
7. run systematic terminal-graph falsification;
8. only then decide whether the next step is broader refinement coverage or a different higher-dominance unresolved leaf.
