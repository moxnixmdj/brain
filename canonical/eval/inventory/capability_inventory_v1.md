# Capability inventory, derived from the tree (no hand-typed numbers)

- head `5a626875`, 18054 tracked files, inventory digest `330ac8dbc1c8ea1d`
- authority: `NONE__DERIVED_FROM_COMMITTED_RECEIPTS_AND_CI_REPORTS`; model calls 0, cost $0.00

## What is measured against the bytes we ship
law on file: True | ledger authority: `NONE` | 9/9 PASS | stale measurements: 0

| capability | verdict | fresh instances | pass rate | oracle classes | canary | binding |
|---|---|---|---|---|---|---|
| `AUTHENTICATED_PARETO_SCHEDULE_V1` | PASS | 2000 | 1.0 | ANALYTIC_CLOSED_FORM+METAMORPHIC+PROPERTY | 0/0 | MEASURED_BYTES_STILL_IN_HEAD (1/1 kernels) |
| `CAPABILITY_FIRST_RANKING_V1` | PASS | 2000 | 1.0 | ANALYTIC_CLOSED_FORM+METAMORPHIC+PROPERTY | 0/0 | MEASURED_BYTES_STILL_IN_HEAD (1/1 kernels) |
| `DOCX_EXACT_TEXT_EDIT_V1` | PASS | 3000 | 1.0 | ANALYTIC_CLOSED_FORM+METAMORPHIC+PROPERTY | 0/0 | MEASURED_BYTES_STILL_IN_HEAD (0/0 kernels) |
| `DOCX_RUN_SPAN_REPLACE_V1` | PASS | 2000 | 1.0 | ANALYTIC_CLOSED_FORM+METAMORPHIC+PROPERTY | 0/0 | MEASURED_BYTES_STILL_IN_HEAD (1/1 kernels) |
| `DOCX_STORY_PART_REPLACE_V1` | PASS | 2000 | 1.0 | ANALYTIC_CLOSED_FORM+METAMORPHIC+PROPERTY | 0/0 | MEASURED_BYTES_STILL_IN_HEAD (1/1 kernels) |
| `DOCX_TEXT_EDIT_TRANSACTION_V1` | PASS | 2000 | 1.0 | ANALYTIC_CLOSED_FORM+METAMORPHIC+PROPERTY | 0/0 | MEASURED_BYTES_STILL_IN_HEAD (1/1 kernels) |
| `PARETO_FRONTIER_UPDATE_V1` | PASS | 2000 | 1.0 | ANALYTIC_CLOSED_FORM+METAMORPHIC+PROPERTY | 0/0 | MEASURED_BYTES_STILL_IN_HEAD (1/1 kernels) |
| `SACCR_CREDIT_ADDON_V1` | PASS | 2000 | 1.0 | ANALYTIC_CLOSED_FORM+DIFFERENTIAL_EXTERNAL+METAMORPHIC+PROPERTY | 1/1 | MEASURED_BYTES_STILL_IN_HEAD (0/0 kernels) |
| `SAME_IDENTITY_SUPERVISOR_V1` | PASS | 2000 | 1.0 | ANALYTIC_CLOSED_FORM+METAMORPHIC+PROPERTY | 0/0 | MEASURED_BYTES_STILL_IN_HEAD (0/0 kernels) |

## Frontier ownership, per family (the repo's own comparison, dated 2026-10-03)
19 families | verified-owned-or-better: 7 | behavioral PASS: 19 | quarantined scope: 5 | broken evidence pointers: 0

| family | status | ownership credit | behavioral | pointers | broken |
|---|---|---|---|---|---|
| ADVANCED_AGENTIC_CODING | BRAIN_CONFIGURED_VERIFICATION_PENDING | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 5 | 0 |
| COMPLEX_MULTI_TOOL_AGENCY | VERIFIED_OWNED_EQUAL_OR_BETTER | VERIFIED_OWNED_EQUAL_OR_BETTER | PASS | 4 | 0 |
| PROFESSIONAL_KNOWLEDGE_WORK | BRAIN_CONFIGURED_VERIFICATION_PENDING | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 6 | 0 |
| BUSINESS_WORKFLOW_AUTOMATION | EXTERNAL_CAPABILITY_SPECIMEN_FOUND | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 2 | 0 |
| MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING | EXTERNAL_CAPABILITY_SPECIMEN_FOUND | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 1 | 0 |
| AGENTIC_SCIENTIFIC_RESEARCH | EXTERNAL_CAPABILITY_SPECIMEN_FOUND | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 2 | 0 |
| VISION_AND_DENSE_DOCUMENT_UNDERSTANDING | EXTERNAL_CAPABILITY_SPECIMEN_FOUND | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 1 | 0 |
| COMPUTER_AND_BROWSER_USE | EXTERNAL_CAPABILITY_SPECIMEN_FOUND | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 2 | 0 |
| FINANCIAL_ANALYSIS | EXTERNAL_CAPABILITY_SPECIMEN_FOUND | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 1 | 0 |
| INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT | VERIFIED_OWNED_EQUAL_OR_BETTER | VERIFIED_OWNED_EQUAL_OR_BETTER | PASS | 3 | 0 |
| LONG_HORIZON_MEMORY_AND_CONTINUITY | VERIFIED_OWNED_EQUAL_OR_BETTER | VERIFIED_OWNED_EQUAL_OR_BETTER | PASS | 4 | 0 |
| SUBAGENT_DELEGATION_AND_COORDINATION | VERIFIED_OWNED_EQUAL_OR_BETTER | VERIFIED_OWNED_EQUAL_OR_BETTER | PASS | 6 | 0 |
| SELF_VERIFICATION_DEBUGGING_AND_RECOVERY | VERIFIED_OWNED_EQUAL_OR_BETTER | VERIFIED_OWNED_EQUAL_OR_BETTER | PASS | 6 | 0 |
| ARTIFACT_CREATION | OWNED_COMPONENT_NOT_FULL_FAMILY | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 4 | 0 |
| COMMUNICATION_AND_SYNTHESIS | EXTERNAL_CAPABILITY_SPECIMEN_FOUND | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 1 | 0 |
| TOOL_DISCOVERY_SELECTION_AND_LEARNING | VERIFIED_OWNED_EQUAL_OR_BETTER | VERIFIED_OWNED_EQUAL_OR_BETTER | PASS | 4 | 0 |
| UNKNOWN_DOMAIN_ADAPTATION | EXTERNAL_CAPABILITY_SPECIMEN_FOUND | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 1 | 0 |
| MULTI_CAPABILITY_COMPOSITION | OWNED_COMPONENT_NOT_FULL_FAMILY | ZERO_UNTIL_FROZEN_PROTOCOL_RESULT_PASS | PASS | 2 | 0 |
| EXACT_SYMBOLIC_COMPUTATION | VERIFIED_OWNED_EQUAL_OR_BETTER | VERIFIED_OWNED_EQUAL_OR_BETTER | PASS | 1 | 0 |

## Self-reported counts vs the fields they summarize
**Disagree** — the prose status and the numeric fields cannot both be true:

- status says 5 of 19 accepted; acceptance_truth says 7 of 19
- acceptance_truth.verified_owned_families=7 but ownership_truth.verified_owned_families=5

status string: `ACTIVE_FAIL_CLOSED__5_OF_19_ACCEPTED__5_OF_19_VERIFIED_OWNED__14_OF_19_OPEN__TERMINAL_FALSE`

## The capability law (imported, pinned receipts)
authority `NONE__PRODUCER_RUN_SANDBOX_COMPOSITION_OF_PUBLISHED_RECEIPTS`; terms: p_correct=0.2978, p_correct_value_bearing=0.1167

## Benchmark runs published by CI
2 committed report(s).

### `swe-pro-v2-hard51-latest.json`
- produced a number: True | run_failed: None | inputs: `null`
- gates: `{"nop_gate_pass": true, "oracle_gate_pass": false}` | incomplete shards: null
- receipt: `SWE_PRO_V2_HARD51_20261125_V1.json` claimable=False authority=`OFFICIAL_TASK_VERDICTS__GATES_NOT_PASSED`
  - `causal`: 0/51 (missing 0, calls None, $None) conditions=`null`
  - `nop`: 0/51 (missing 0, calls None, $None) conditions=`null`
  - `oracle`: 50/51 (missing 0, calls None, $None) conditions=`null`
  - why not quotable: ORACLE_GATE: the reference patch resolved 50/51, not N/N, in this job configuration — a task's own test is then not the constraint it claims to be, and no causa

### `swe-pro-v2-smoke3-latest.json`
- produced a number: False | run_failed: True | inputs: `{"agent_timeout_s": "600", "arms": "all", "benchmark": "swe-pro-v2-smoke3", "commit_results": "true", "n_shard_reports_found": 0, "n_shards": "1", "run_failed": ""}`
- gates: `null` | incomplete shards: null
- receipt: `swe-pro-v2-smoke3-receipt.json` claimable=False authority=`NO_MEASUREMENT__HARNESS_ONLY`
  - why not quotable: NO_TRIAL_DATA: no trial row was read for any expected task, so this run produced no benchmark number. The 0 columns in the raw report are a harness failure, not; RUN_FAILED: the eval job reported failure; no shard report was committed.

## Claim surface: 368 dated ledgers at the repo root (20261015..20261201) and 2927 verification receipts
Newest 15:
- `BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201_V1.md`
- `THE_GOAL_IS_NOT_IN_THE_ENVIRONMENT_20261130_V1.md`
- `THE_REPERTOIRE_IS_A_QUERY_20261129_V1.md`
- `THE_COUNTEREXAMPLE_IS_THE_NEXT_EXPERIMENT_20261129_V1.md`
- `THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE_20261128_V1.md`
- `THE_BRANCH_IS_THE_MODEL_20261128_V1.md`
- `THE_PRICE_OF_A_CORRECT_DECISION_20261127_V1.md`
- `THE_GOAL_IS_A_RELATION_OVER_THE_RUN_20261127_V1.md`
- `THE_GOAL_IS_A_DISCRIMINATOR_20261126_V1.md`
- `THE_DEMONSTRATION_CARRIES_THE_ACTION_20261126_V1.md`
- `THE_VOCABULARY_IS_THE_ARTIFACT_20261125_V1.md`
- `THE_DEMAND_IS_A_RELATION_20261125_V1.md`
- `SWE_BENCH_PRO_V2_FIRST_MEASURED_RUN_20261125_V1.md`
- `MOST_ADVANCED_CAPABILITIES_VS_FRONTIER_20261125_V1.md`
- `A_SITE_IS_NOT_A_PRODUCTION_20261124_V1.md`

**Date hygiene:** 10 ledgers carry an as-of date after the date this inventory was built (20261125), e.g. `BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201_V1.md`, `THE_GOAL_IS_NOT_IN_THE_ENVIRONMENT_20261130_V1.md`, `THE_REPERTOIRE_IS_A_QUERY_20261129_V1.md`, `THE_COUNTEREXAMPLE_IS_THE_NEXT_EXPERIMENT_20261129_V1.md`, `THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE_20261128_V1.md`, `THE_BRANCH_IS_THE_MODEL_20261128_V1.md`, `THE_PRICE_OF_A_CORRECT_DECISION_20261127_V1.md`, `THE_GOAL_IS_A_RELATION_OVER_THE_RUN_20261127_V1.md`. A ledger date is a label, not a measurement; nothing here treats it as one.
