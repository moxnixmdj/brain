# Benchmark Measurement vs Capability Proof Law V1

Status: **CANONICAL CANDIDATE / FAIL-CLOSED**

## 1. Scope

This law governs every benchmark, leaderboard, private test, public test, or owner evaluation used as a Project Brain checkpoint or capability comparison.

## 2. Three propositions must remain separate

For any benchmark target, Brain MUST track three distinct propositions:

1. **Branded benchmark predicate (B)** — the exact score/result under the benchmark owner's protocol.
2. **Capability comparison predicate (C)** — Brain is at least as capable as the target/reference on a precisely bound capability scope.
3. **Ownership predicate (O)** — the credited capability is Brain-owned and satisfies the capability-transfer vs cognition-outsourcing law.

None of B, C, or O implies either of the others unless an explicit admissible entailment is bound.

In particular:

- capability evidence does **not** create a branded score;
- a branded score does **not** prove general capability outside the benchmark's bound scope;
- either result gets zero Brain ownership credit if external/general-purpose runtime cognition remains load-bearing.

## 3. Benchmark role

The mission objective is capability-first. A benchmark is a measurement instrument, not the architecture.

Benchmark-specific work is primary only when it is the cheapest sound route to the proposition actually required. If a stronger or scope-equivalent Brain-owned certificate proves the same capability comparison faster, use the stronger certificate and keep the branded score predicate separately open.

If the user explicitly requires the literal benchmark score/result, B remains an independent obligation. Closing C never silently substitutes for B.

## 4. Typed benchmark-to-capability relations

Every benchmark-to-capability projection MUST declare one of:

- `EXACT_EQUIVALENCE`
- `CONSERVATIVE_DOMINANCE`
- `OWNER_ACCEPTED_RELATION`
- `SCHEDULING_HEURISTIC_ONLY`

Only the first three may participate in capability-comparison credit, and only with their stated scope. `SCHEDULING_HEURISTIC_ONLY` can rank research but grants zero benchmark, capability, acceptance, ownership, or terminal credit.

## 5. Minimum sufficient evidence

For a required capability proposition, choose the minimum-wall-clock admissible evidence set that logically forces the proposition.

A benchmark receipt is one admissible evidence type. It is not privileged over a stronger certificate merely because it has a brand name.

Proof compression across benchmarks is encouraged only when the shared certificate is causally load-bearing and its scope relation is explicit.

## 6. Scheduling

Benchmark rows that are wake-gated on new authority, new private scope, new authenticated result, or a stronger certificate MUST NOT receive same-information retries.

A latent capability family inferred from a benchmark MUST NOT create capability work by itself. New capability work requires at least one of:

- a real task-local counterexample;
- an independently verified live capability defect;
- an already-authorized capability experiment whose result discriminates a live hypothesis;
- a proof-preserving resource Pareto improvement already admitted by the current capability-first frontier.

Global shared-mechanism work is forbidden when an existing falsifier proves that mechanism is not globally necessary. Route-local necessity wins over graph centrality.

## 7. Two ledgers

Canonical state MUST maintain:

- **CAPABILITY_COMPARISON_LEDGER** — capability propositions and admissible supporting certificates;
- **BRANDED_BENCHMARK_RECEIPT_LEDGER** — exact benchmark results and owner-comparable receipts.

The ledgers may cross-reference each other only through an explicit typed entailment.

## 8. Optimization order

Subject to correctness, ownership, provenance, contamination, and fail-closed requirements:

1. minimize wall-clock time to the required proposition;
2. maximize reusable capability coverage;
3. minimize external wait/authorization dependence;
4. minimize compute, context, memory, energy, and incremental spend.

Hard incremental spend remains $0 unless the mission owner explicitly changes it.

## 9. Anti-outsourcing inheritance

`canonical/laws/CAPABILITY_TRANSFER_VS_COGNITION_OUTSOURCING_LAW_V1.md` remains mandatory. No benchmark or capability certificate can launder external runtime cognition into Brain credit.

## 10. Hard nonclaims

This law does not close any benchmark, does not infer any private score, does not prove any benchmark fully represents a capability family, and does not authorize access to gated/private evaluation content.
