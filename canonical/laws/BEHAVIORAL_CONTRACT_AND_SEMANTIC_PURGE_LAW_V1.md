# Behavioral Contract and Semantic Purge Law V1

## Purpose

Project Brain MUST NOT treat a name, family, primitive, blocker, capability label, or abstract noun as an implementation target unless it denotes an explicit observable behavior.

The implementation unit is behavior, not terminology.

## Core law

**NO TERM WITHOUT A BEHAVIORAL CONTRACT.**

Any term that materially affects mechanism search, acquisition, training, verification, promotion, or terminal-distance reasoning MUST be classified as exactly one of:

1. **BEHAVIOR** — an observable transformation with an explicit contract.
2. **ACCOUNTING_LABEL** — an evaluation/reporting grouping only; it MUST NOT imply one internal module or mechanism.
3. **UNDEFINED** — insufficiently specified for causal reasoning; mechanism search and capability credit are forbidden until contracted.

## Minimum behavioral contract

A BEHAVIOR contract MUST state:

- `inputs`: observable inputs.
- `environment_state`: state the transformation may depend on.
- `allowed_information`: information the mechanism may legally/causally use.
- `required_output_or_action`: observable result.
- `success_condition`: measurable acceptance condition.
- `failure_condition`: measurable failure condition.
- `terminal_consequence`: why this behavior is necessary for the terminal objective.
- `verification_route`: an independent route capable of falsifying the behavior.
- `dependency_boundary`: required donor/runtime/tool dependencies.
- `scope`: population/domain over which the claim is made.

A name without these fields is not an implementation primitive.

## Semantic purge procedure

For every active term:

1. Ask whether the term denotes one measurable transformation.
2. If no, classify it as ACCOUNTING_LABEL or UNDEFINED.
3. If it clusters multiple behaviors, split it until each leaf is independently testable.
4. Prove each leaf is necessary to terminal behavior before acquiring a mechanism.
5. Search for the minimum sufficient mechanism only after the behavior is explicit.

## Minimum mechanism search order

For each unresolved behavioral leaf, search in this order:

1. DELETE — prove the behavior unnecessary.
2. DETERMINISTIC — exact rules, state machines, invariants, parsers.
3. EXACT_COMPUTE — symbolic/numeric algorithms with deterministic acceptance.
4. RETRIEVE — external/JIT knowledge or state lookup.
5. SEARCH — executable planning/search over known state transitions.
6. TOOL_RUNTIME — existing Brain-owned runtime/tool mechanics.
7. OPEN_REUSE — permissive reusable mechanism.
8. COMPOSE — existing owned mechanisms.
9. WHITE_BOX_HARVEST — extract only the surviving causal residual from a donor.
10. TRAIN_RESIDUAL — only after cheaper behaviorally equivalent routes are falsified.

The selected mechanism MUST be the smallest/cheapest route that preserves the required behavior under the claimed scope.

## Verification independence law

Builder self-consistency is not independent evidence.

A terminal candidate MUST NOT be authorized solely because tests, interpretations, or recomputations derived from the builder's own assumptions pass.

Where the specification admits multiple plausible interpretations, verification MUST include an independent acceptance-model/adversarial route that attempts to produce:

- alternative interpretations,
- boundary cases,
- metamorphic cases,
- counterexamples,
- independently derived expected consequences.

Deterministic oracles remain preferred wherever possible.

## Causal ownership gate

A learned or donor-derived mechanism may survive only if all applicable checks pass:

- fresh held-out behavioral transfer,
- direct terminal-task improvement,
- ablation causes measurable degradation,
- rescue restores the behavior,
- smaller substitute fails or is weaker,
- cross-domain transfer where claimed,
- donor deletion preserves the behavior,
- full dependency accounting is explicit.

If donor removal destroys the behavior, Brain does not own it.
If mechanism removal changes nothing, delete the mechanism.

## Evaluation-family interpretation

The 19 Opus 5.5 capability families are acceptance/evaluation surfaces only.
They MUST NOT be assumed to correspond to 19 internal modules.

Likewise, C1-C10 names are provisional bookkeeping clusters. Their names carry zero ontological authority. Only contracted behavioral leaves may drive implementation or promotion.

## Fail-closed rule

Any consequential action that cites an uncontracted abstract term as its causal blocker, required mechanism, or acquisition target MUST fail closed.

Fresh clean benchmark evidence MUST NOT be spent merely to clarify an undefined term that can first be decomposed using already-spent evidence, open mechanisms, deterministic analysis, or noncontaminating general evidence.

## Terminal condition

Semantic closure requires:

- every required terminal behavior has a behavioral contract,
- every required behavior has a causally sufficient Brain-owned mechanism,
- donor-dependent required behavior is zero,
- unexplained required behavior is zero,
- all claimed compositions survive independent verification,
- all 19 external evaluation surfaces meet or exceed the Opus 5.5 bar under the owned route.
