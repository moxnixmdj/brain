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
