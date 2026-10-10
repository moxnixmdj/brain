# Coverage Completeness Root Theorem Law V1

Status: CANONICAL_PROOF_ARCHITECTURE_CANDIDATE__FAIL_CLOSED__ZERO_TERMINAL_CREDIT

## Purpose

Collapse coverage-completeness reasoning into the smallest load-bearing root theorem and stop unbounded peer-level category growth.

This law does not prove that the current Project Brain terminal objective is complete. It defines the proof architecture under which such a claim may be made.

## Four roots

Let:

- `B_real` = the real mission-relevant behavior set of the deployed system in the authorized scope.
- `B_plus` = a conservative upper envelope of possible mission-relevant behavior.
- `G_minus` = the behavior set definitely accepted by the authorized mission semantics.
- `G_real` = the behavior set actually accepted by the authorized mission.

The load-bearing set roots are:

```
R1 REALITY_CONTAINMENT: B_real subseteq B_plus
R2 MISSION_SOUNDNESS:   G_minus subseteq G_real
R3 TERMINAL_CLOSURE:    B_plus subseteq G_minus
```

The meta root is:

```
R4 PROOF_AND_REALIZATION_TRUST:
the certificates, semantic bindings, provenance, versions, realization path,
and trusted checking needed to assert R1-R3 are trustworthy under explicit
trust atoms and current authority.
```

R4 is not an additional set inclusion in the pure mathematical theorem. It is the operational condition that makes the asserted set inclusions authoritative.

## Terminal theorem

By transitivity:

```
R1 and R3 and R2
=> B_real subseteq B_plus subseteq G_minus subseteq G_real
=> B_real subseteq G_real
```

Therefore false terminal success cannot coexist with true R1, R2, and R3 under consistent semantic bindings.

If an alleged false-success witness appears while all three set roots are reported true, the controller MUST NOT invent an R5 by default. It MUST reopen R4 and the exact semantic bindings used to establish R1-R3.

## Root polarity

Unknown never strengthens authority.

- uncertainty about reality keeps or widens `B_plus`;
- uncertainty about mission acceptance keeps or shrinks `G_minus`;
- UNKNOWN is never PROVED;
- NOT_PROVED is never FALSE;
- timeout is never UNSAT;
- absence of a discovered counterexample is never completeness.

## Derived obligations under R1

The following are not peer roots. They are strategies or proof obligations for establishing reality containment:

- mission-sufficient boundary realization;
- generalized behavioral carrier and conservative observation semantics;
- implementation-to-contract refinement or mediated containment;
- sound abstraction and outward approximation;
- unknown-to-TOP behavior;
- effect-frame completeness;
- resource identity, alias, lifetime, persistence, and storage integrity where load-bearing;
- physical/reality anchoring where load-bearing;
- complete mediation when used as a containment construction;
- runtime containment falsification and semantic-diff invalidation.

A defect in any such mechanism is a defect in R1 unless it instead invalidates the proof/realization chain, in which case it is R4.

## Derived obligations under R2

The following are subordinate to mission soundness:

- authenticated mission authority and delegation;
- mission interpretation envelopes;
- modality preservation;
- scope and assumption discipline;
- evaluator/proxy-to-mission binding;
- qualitative acceptance semantics;
- authorized mission revisions and epoch fencing;
- evidence-selection rules insofar as they establish mission acceptance.

A newly named intent/evaluator failure is not automatically a new root. If it causes definitely-good behavior to be unacceptable under the real authorized mission, it falsifies R2 or its R4 evidence.

## Derived obligations under R3

Terminal closure is the direct success relation:

```
B_plus subseteq G_minus
```

Viability, winning, liveness, finality, quantitative risk, recovery, and similar mechanisms are included only when required by the mission semantics represented in `G_minus` or the behavior semantics represented in `B_plus`.

R3 is not proved by output quality, benchmark resemblance, or lack of known failures. It requires a sound inclusion proof or an equivalent proof-producing reduction.

## Derived obligations under R4

The following are proof-authority machinery, not additional semantic roots:

- typed claims and no implicit quantifier/modality coercion;
- well-founded proof dependencies, with explicitly checked least/greatest fixed points where recursion is legitimate;
- premise consistency or a proven non-explosive reasoning context;
- semantic soundness of the proof calculus and theory translations;
- proof-obligation coverage and fail-closed UNKNOWN handling;
- bytes-to-semantics canonicalization;
- proof-to-use continuity;
- implementation/execution realization binding;
- current revision and epoch binding;
- append-only/non-equivocating authority history;
- explicit trust atoms and trust-root provenance.

## New-E admission test

A proposed new failure class, root, gate, ontology, checker, or semantic subsystem MUST NOT enter the canonical peer architecture merely because it has a new name.

It is admissible only if at least one is true:

1. **Demonstrated root repair:** there is a concrete or formally constructed witness showing an unresolved failure of R1, R2, R3, or R4 that existing subordinate machinery does not close.
2. **Material proof-cost reduction:** it materially reduces the cost or wall-clock of establishing a root while preserving soundness. If it increases the trusted core, a dominance proof over the added trust cost is required.

Otherwise the proposal remains research material or is deleted as redundant.

## Anti-overengineering invariant

A canonical mechanism must do at least one of:

- soundly shrink `B_plus`;
- soundly expand `B_minus`;
- soundly expand `G_minus`;
- soundly shrink `G_plus`;
- close a demonstrated R1/R2/R3/R4 defect;
- materially reduce the proof cost of those operations without weakening truth.

Descriptive machinery that changes none of these is not load-bearing architecture.

## Falsification-first phase

After this root theorem is adopted, architecture invention is no longer the default response to uncertainty.

The default loop is:

1. freeze the current root claim and exact semantic bindings;
2. try to construct a counterexample to R1;
3. try to construct a counterexample to R2;
4. search directly for a witness in `B_plus - G_minus` against R3;
5. mutate the R4 proof/realization chain;
6. refine only the root actually falsified;
7. rerun the root theorem;
8. add no peer mechanism unless the New-E admission test passes.

## Permanent mutation classes

The falsifier MUST include at minimum:

- real behavior omitted from the upper behavior envelope -> R1;
- definitely-good behavior rejected by real mission semantics -> R2;
- possible behavior outside definitely-good -> R3;
- stale, inconsistent, circular, unsound, mistranslated, or unrealized proof chain -> R4;
- UNKNOWN promoted to PROVED -> hard fail;
- false success not localized to a root or semantic-binding inconsistency -> hard fail;
- redundant new meta category with no root delta and no proof-cost advantage -> reject.

Mutation score is diagnostic evidence only. A score of 1 is not a universal completeness proof.

## Safety completeness versus proof capability

Two dashboards remain separate:

```
SEMANTIC_SOUNDNESS_CLOSURE
PROOF_CAPABILITY_CLOSURE
```

The first asks whether false success can be authorized.
The second asks whether the Brain can efficiently establish or construct a true result when one exists.

Failure to find a proof changes epistemic state, not theorem truth.

## Relationship to prior work

This law subsumes rather than erases prior mechanisms.

- `ACTION_INTENT_TERMINAL_FOUR_INVARIANT_COLLAPSE_20261007_V1.json` is a domain-specific ancestor.
- Historical PR #2206's typed coverage-dominance sandwich is preserved as prior specialized proof work, but it is not current authority and was closed as a stale integration vehicle.
- Existing behavioral-contract, terminal-proof-tree, truth-first, authority, verification, and regression machinery remains valid where it establishes or accelerates one of R1-R4.

\n## Semantic carrier precondition\n\nThe set theorem is sound only over a carrier that preserves every mission-relevant distinction. Let full concrete worlds be W, let the theorem carrier be Omega, and let pi: W -> Omega be the projection used to form B_real, B_plus, G_minus, and G_real.\n\nRequired factorization:\n\n    forall w1,w2: pi(w1)=pi(w2) => M(w1)=M(w2)\n\nEquivalently, the mission must factor through the carrier:\n\n    exists M_hat such that M = M_hat o pi\n\nTherefore the element type of Omega is not fixed to a single execution trace. It MUST be lifted when the mission depends on richer objects, including trace sets or hypertraces, probability laws or ambiguity sets, policy-environment interaction objects, infinite temporal behaviors, or causal/resource/authority histories.\n\nA carrier-aliasing witness consists of two concrete worlds that project to the same carrier value but have different mission verdicts. Such a witness is an R4 semantic-binding failure and an R1 scope/carrier defect, not a new fifth semantic root.\n\nCarrier factorization is indexed by the same frozen certification claim C used by the root theorem. A factorization certificate for one claim_id, scope digest, or semantics digest MUST NOT be transported to another claim without an explicit preservation proof. The open-ended global mission is not a finite claim and is not closed by any finite carrier certificate.\n\nNo finite sample without a separate scope-completeness proof may establish universal factorization. In particular:\n\n- equal support does not imply equal stochastic risk;\n- one equal trace does not imply equal hyperproperty truth;\n- one equal finite prefix does not imply equal liveness truth;\n- UNKNOWN mission truth cannot be erased by projection.\n\nCanonical guard:\n- canonical/governance/MISSION_SUFFICIENT_SEMANTIC_CARRIER_V1.json\n- canonical/runtime/mission_carrier_factorization_v1.py\n- canonical/tests/test_mission_carrier_factorization_v1.py\n
## R4 exact root-binding coherence

R1, R2, and R3 are composable only when their proof receipts inhabit one exact current semantic binding. Before four-root closure, the checker MUST verify equality of:

- certification claim identity;
- scope digest;
- semantics digest;
- carrier schema identity;
- mission identity;
- mission/proof epoch;
- canonical generation.

The content-addressed claim, scope, and semantics fields MUST be valid digests. Missing root proof or missing expected binding is UNKNOWN and fails closed. A root receipt bound to a different carrier, scope, semantics, mission, epoch, or generation is an R4 failure.

Therefore a naked boolean such as `proof_chain_trustworthy = true` is never sufficient to close R4.

This is load-bearing. If R1 proves `r -> p1`, R3 proves `p2 -> g2`, and R2 proves `g3 -> a` under unrelated bindings, all three local implications can be true while `r -> a` is false. Set-inclusion transitivity is authorized only after exact binding coherence is established.


## R4 canonical certificate authority

Exact binding coherence is necessary but not sufficient. R1, R2, and R3 acquire proof authority only through the canonical coverage-completeness root certificate registry.

The authoritative registry is:

- `canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json`
- validated by `canonical/runtime/coverage_root_certificate_registry_guard_v1.py`.

Four-root closure therefore additionally requires:

1. the registry validates against the current authoritative mission source;
2. all three canonical root IDs are present exactly once;
3. every root slot is `PROVED_CURRENT`;
4. each proved slot binds a content-addressed certificate and independent verification object;
5. the referenced certificate and verification bytes match their claimed Git blob identities;
6. the registry reports `r4_proof_closure = true`.

Locally supplied objects containing `status = PROVED` have zero authority by themselves.

The registry binds the stable authoritative mission source, not incidental mutable fields in `CURRENT_MISSION_OBJECTIVE.json`. The current pointer must still identify the same authoritative mission source and real objective. Auxiliary pointer churn therefore cannot silently invalidate or silently redefine mission semantics.

If the canonical registry has any open root certificate obligation, R4 is not closed even when local test fixtures make R1, R2, and R3 individually true.


## R4 canonical-registry/local-claim alignment

Canonical registry authority and local root-binding coherence MUST refer to the same active frozen certification claim.

After the canonical root-certificate registry validates and reports R4 proof closure, the root theorem checker MUST additionally prove that the locally expected root binding matches the registry's active claim on at least:

- claim identity;
- scope digest;
- semantics digest;
- claim epoch;
- current canonical generation.

The root theorem checker MUST pass the current mission-pointer Git blob identity into the registry guard when validating an active claim. Otherwise a valid future active claim would fail closed for a plumbing defect rather than a semantic defect.

A registry that closes claim X cannot authorize locally coherent root proofs for claim Y. This is an R4 authority-splice failure, not a new root.

The canonical generation is not part of the registry's abstract claim identity, but local root proofs must still match the currently active generation before they may be composed into terminal authority.


## R4 executable semantic certificate verification

Content identity is necessary but not sufficient proof authority.

A `PROVED_CURRENT` canonical root slot MUST bind:

- the exact root certificate bytes;
- a content-addressed canonical semantic verifier;
- an independent verification receipt;
- the exact frozen claim.

Before R4 accepts the slot, the semantic verifier MUST be rerun over the exact certificate and active claim. The independent receipt MUST bind the same root ID, claim ID, certificate blob, verifier blob, and deterministic verifier-result digest, and MUST explicitly report successful semantic verification under an allowed proof mode.

A byte-perfect empty, foreign, self-contradictory, or unrelated verification receipt has zero proof authority.

A stored PASS receipt cannot override a verifier that rejects the certificate.

The semantic verifier itself becomes an explicit R4 trusted dependency and MUST be content-addressed by the live-binding currentness layer. Its tests and the registry claim-alignment tests are also load-bearing currentness dependencies.

This remains R4 proof-authority hardening, not a fifth semantic root.

## Nonclaims

This law:

- does not prove current R1;
- does not prove current R2;
- does not prove current R3;
- does not change current terminal, family, acceptance, atomic-predicate, or ownership counts;
- does not authorize fresh target reality;
- does not authorize benchmark or qualification execution;
- does not grant Opus 5.5 capability credit.

## Canonical stop rule

Do not continue adding architectural layers merely because another imaginable failure can be described.

Continue theory expansion only when a falsifier demonstrates a failure that cannot be represented as an R1/R2/R3/R4 defect under the exact semantic bindings, or when a new construction materially reduces proof cost without weakening the root theorem.

Until then: falsify, refine, and compress.
