# BENCHMARK MEASUREMENT AND CAPABILITY CAUSALITY LAW V1

Status: CANONICAL CANDIDATE
Date: 2026-10-11

## Purpose

Benchmarks are measurement surfaces. They are not the capability definition and
must not become the optimization target for Brain-owned capability credit.

The system must optimize the smallest reusable causal mechanism that produces
the measured behavior on fresh neighboring tasks. Benchmark scores are evidence
about that mechanism, not substitutes for it.

## Hard rules

1. **Capability first.** Development targets a behavioral transform that remains
   useful when benchmark task IDs, seeded values, entity names, app names,
   endpoint names, ordering, and wording change.

2. **Benchmark adapters are narrow.** Benchmark-specific code may handle
   transport, harness protocol, score parsing, task loading, evaluator receipts,
   or tool-schema conversion. It may not be the load-bearing reasoning,
   planning, judgment, or action-selection mechanism credited to Brain.

3. **No task-template credit.** Logic keyed by benchmark task IDs, exact seeded
   values, named public examples, hidden/private examples, or threshold-tuned
   special cases receives zero capability and ownership credit.

4. **Public tasks are failure generators.** Public benchmark tasks may expose
   causal failure classes. A repair is promotable only when it fixes the general
   cause and is validated on neighboring or adversarial cases that change
   surface literals while preserving the underlying capability requirement.

5. **Measurement is downstream.** Private/public benchmark execution occurs
   after a candidate is frozen. A score may close an acceptance predicate but
   cannot retroactively turn benchmark-specific scaffolding into a general
   capability.

6. **Ablation requirement.** If removing benchmark-specific literals/templates
   leaves the general mechanism intact, the mechanism may receive credit.
   If removing them destroys the claimed capability, the claim is benchmark
   overfitting and receives zero capability/ownership credit.

7. **No goal substitution.** This law does not weaken exact benchmark acceptance
   predicates. It changes development causality only: build the capability,
   then measure it on the benchmark.

## Preferred development loop

GOAL
-> DESIRED STATE / ACCEPTANCE PREDICATES
-> WORLD OBSERVATION
-> GENERIC TOOL EFFECT MODEL
-> MINIMUM-COST PLAN
-> EXECUTION
-> INDEPENDENT STATE VERIFICATION
-> CAUSAL FAILURE LOCALIZATION
-> GENERAL REPAIR
-> ADVERSARIAL / NEIGHBOR VALIDATION
-> FROZEN CANDIDATE
-> BENCHMARK MEASUREMENT

## AutomationBench application

For AUTOMATIONBENCH_GE_40, Zapier/Artificial Analysis remain the measurement
authorities for the private score. AutomationBench-specific Stirrup/API adapters
may remain as harness code. App/task-specific action compilers are transitional
zero-credit scaffolding unless their behavior is absorbed into a benchmark-
agnostic goal/state/tool-effect mechanism and survives literal-renaming and
neighboring-task tests.

## Accounting

This law grants no benchmark, family, capability, ownership, promotion, or
terminal credit by itself.
