# Benchmark Measurement vs Capability Proof Law V2

Status: **CANONICAL ACTIVE CONTROLLER LAW / FAIL-CLOSED**

Supersedes the scheduling semantics of
`canonical/laws/BENCHMARK_MEASUREMENT_VS_CAPABILITY_PROOF_LAW_V1.md`.
The V1 file remains immutable historical evidence.

## 1. Mission rule

A benchmark is a measurement instrument, not the capability and not the
architecture. Planning begins from the proposition that must become true or
proved, never from the benchmark procedure merely because that procedure
exists.

For every benchmark-linked claim Brain MUST preserve three distinct
propositions:

- **B**: the exact branded benchmark statistic under the owner's frozen
  protocol.
- **C**: a precisely scoped capability relation, such as
  `Brain capability >= reference capability`.
- **O**: Brain ownership of the credited capability under the
  capability-transfer versus cognition-outsourcing law.

B, C, and O are independent unless an explicit admissible entailment edge
proves otherwise.

## 2. Proposition-first compilation

Before benchmark execution or benchmark-specific engineering:

1. freeze the exact required proposition;
2. classify it as B, C, or O;
3. saturate existing evidence and deductive closure;
4. enumerate admissible certificates that could force that proposition;
5. bind every proposed implication with scope and evidence;
6. compile the resulting graph into the minimum proof cover;
7. execute only a nondominated runnable member of that cover.

A benchmark-native run receives no scheduling privilege.

## 3. Typed implication edges

Only proved edges may close propositions.

For C, creditable relations are:

- `EXACT_EQUIVALENCE`
- `CONSERVATIVE_DOMINANCE`
- `OWNER_ACCEPTED_RELATION`

For B, admissible closure requires either:

- `NATIVE_OWNER_RECEIPT`, or
- `EXACT_STATISTIC_BRIDGE` with the frozen scorer state bound.

For O, admissible closure requires a
`BRAIN_OWNERSHIP_CERTIFICATE`, a Brain-owned operative configuration, and
zero load-bearing external/general-purpose runtime cognition on the credited
task.

`SCHEDULING_HEURISTIC_ONLY` may prioritize investigation but has zero
proposition-closure authority.

## 4. Minimum proof cover

The controller MUST minimize the complete evidence set needed to force the
required propositions. Existing
`canonical/runtime/proof_coverage_compiler.py` is the canonical exact
finite-cover primitive.

When a complete admissible cover exists, work outside that cover is dominated
unless required for a separately active terminal objective.

When no complete cover exists, select the runnable action with the greatest
**proved marginal proposition closure**, then prefer broader reusable
capability coverage and lower wall-clock/new-reality/resource cost.

Projected benchmark-family incidence by itself is never closure evidence.

## 5. Information-value execution

A fresh reality query, private benchmark run, owner authorization request, or
new clean case is justified only when its possible outcomes can change a live
terminal decision and no cheaper deduction/certificate already decides it.

Same-information retries against wake-gated benchmark rows are forbidden.

External waiting is dominated by an immediately executable proof or capability
route whenever the latter can establish the same required proposition.

## 6. Benchmark-independent evaluation

For capability proposition C, a novel hidden/adversarial evaluation may replace
a branded benchmark only when a proved scope relation makes its result a
sufficient statistic or stronger certificate for C.

Novel-task quantity is not an objective. Experiments should maximize
decision-relevant information subject to contamination, independence,
ownership, and statistical-validity requirements.

No locally generated evaluation creates an official branded score without an
exact statistic bridge.

## 7. Cross-benchmark proof compression

A single certificate may discharge multiple benchmark-derived capability
obligations only when every downstream implication edge is independently
scope-bound and proved.

Shared wording, shared family labels, correlation, graph centrality, or model
performance similarity are insufficient.

This converts repeated benchmark chasing into a minimum-proof-cover problem
without laundering weak evidence into broad credit.

## 8. Anti-outsourcing and anti-leakage

All existing capability-ownership laws remain mandatory. The proof lattice may
not:

- use external runtime cognition and call it Brain capability;
- reconstruct private answers or hidden task identities;
- train or route on target outputs that are later used as proof;
- infer exact benchmark statistics from generic capability;
- promote heuristic benchmark projections as capability truth.

## 9. Scheduling objective

Subject to correctness, ownership, provenance, contamination control, and
fail-closed requirements, optimize in this order:

1. minimum wall-clock time to the required proposition set;
2. minimum new external-reality dependence;
3. maximum reusable capability/proposition coverage;
4. minimum clean-case consumption;
5. minimum compute, context, memory, energy, and incremental spend.

Hard incremental spend remains $0 unless the mission owner explicitly changes
it.

## 10. Runtime authority and nonclaims

Canonical V2 scheduler:

`canonical/runtime/benchmark_capability_dominance_scheduler_v2.py`

The scheduler grants no benchmark, capability, ownership, acceptance, or
promotion credit merely by selecting a route. Credit comes only from the
underlying admissible evidence and its proved implication edges.
