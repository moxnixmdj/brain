# BENCHMARK OUTPUT INFORMATION EQUIVALENCE LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

## Objective

A benchmark is a measurement instrument, not an intrinsic goal.

For every benchmark-linked obligation, first identify the exact terminal decision output the benchmark is being used to determine. Then minimize the actions and genuinely new information required to determine that output truthfully.

The controller MUST NOT execute, imitate, reconstruct, or optimize around benchmark procedure merely because that procedure exists.

## Two terminal predicate classes

Every benchmark-linked terminal predicate MUST be classified before planning:

1. `CAPABILITY_RELATION`
   - Example semantic form: `BRAIN_CAPABILITY >= REFERENCE_CAPABILITY`.
   - The benchmark's prompts, private task set, judge implementation, aggregation method, and scalar score are measurement machinery.
   - A proof-carrying exact sufficient statistic or a strictly stronger certificate may replace native benchmark execution if it provably determines the same terminal decision.

2. `EXACT_BENCHMARK_STATISTIC`
   - Example semantic form: `OFFICIAL_AA_BRIEFCASE_ELO(BRAIN) >= 1822`.
   - A capability-superiority proof alone is insufficient.
   - A non-native route is admissible only when a formal exact-statistic bridge binds the frozen scorer state and proves that the substitute evidence entails the exact benchmark statistic.

Confusing these two classes is goal drift and MUST fail closed.

## Required planning order

Before any benchmark execution or new benchmark information acquisition:

1. Freeze the terminal predicate and its decision output.
2. Decompose the benchmark result into only the information that can change that decision.
3. Saturate existing evidence and deductions.
4. Search for an exact sufficient statistic or strictly stronger proof-carrying certificate.
5. Compute the minimum information/action cut over the declared candidate route universe.
6. Delete native benchmark execution when a cheaper sound route determines the same terminal decision.
7. Execute the benchmark only when it remains nondominated or when the exact realized statistic itself is the terminal predicate.

## Anti-cheating and anti-proxy rules

A substitute route is invalid if it:

- substitutes a correlated proxy metric without a proved entailment relation;
- infers or reconstructs private benchmark answers, hidden task identity, or target-specific hidden solutions;
- uses the target output as training, tuning, route-selection leakage, or circular proof;
- claims an exact realized benchmark statistic from latent capability without a proved scorer bridge;
- silently changes the terminal predicate from an exact score claim to a capability claim or vice versa.

## Dominance rule

If route A and route B determine the same terminal decision with equal or stronger proof strength, and A requires strictly less fresh information, wall-clock, compute, or spend without weakening correctness, B is dominated and MUST be deleted from the critical path.

Native benchmark execution has no special privilege.

## Credit rule

This law is scheduling and proof-structure authority only. Passing its gate grants zero benchmark, capability, ownership, family, acceptance, execution, or promotion credit by itself.

Canonical runtime gate:

`canonical/runtime/benchmark_output_information_equivalence_gate_v1.py`

The gate MUST fail closed whenever decision equivalence, stronger entailment, exact-statistic bridging, or the minimum-information cut is unproved.
