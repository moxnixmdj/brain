# Capability fabric: what is connected to what, derived

digest `5318717a8b80a71d` · authority `NONE__DERIVED_FROM_IMPORT_GRAPH_AND_COMMITTED_RECEIPTS` · 0 model calls, $0.00

| measure | value | what it decides |
|---|---|---|
| modules under `canonical/` | 6449 | the surface any unification has to cover |
| internal import edges | 3806 | what is actually composed today |
| connected components | 3911 (largest 1572, singletons 3380) | **the fragmentation, measured** — 'not one model' is this number |
| distinct `SCHEMA = "…"` constants | 2238 | bespoke envelopes; the cost a shared envelope removes; the number to drive to 1 |
| modules declaring an `AUTHORITY` | 238 | self-limiting claims — the good part of the culture |
| runnable modules (`if __name__ == "__main__"`) | 2990 | **ways in**; a system has one root and N adapters. Of these, 764 expose a `main()` at all |
| modules nothing in `canonical/` imports | 5067 | nothing in the tree imports them; they are reached only by hand or not at all |
| widest importer fan-out | 19 | the ceiling on 'just write an orchestrator that imports everything' |
| certified capabilities | 18 (0.527 % of non-test modules) | what may be wired into the root with a receipt behind it |

## Reachability classes (every module, one label each)

- `ENTRY_POINT`: 748
- `IN_USE`: 605
- `ISLAND`: 1512
- `TEST`: 3033
- `TEST_ONLY`: 551

## What is composed most, and what is certified most

- most imported: `canonical.swe_kernel.verified_skill_crystallizer_v1` (72), `canonical.runtime.lossless_raw_task_contract_v1` (65), `canonical.runtime.effect_broker_receipt_resolver_v2` (63), `canonical.runtime.brain_unified_model_v1` (45), `canonical.runtime.live_integrated_brain_v1` (41), `canonical.runtime.live_brain_route_admission_v1` (32), `canonical.runtime.semantic_relation_entailment_dag_v1` (31), `canonical.swe_kernel.concept_library_v1` (28)
- widest importers: `canonical.swe_kernel.closed_loop_autonomous_controller_v1` (19), `canonical.runtime.universal_verified_adaptive_solver_v1` (17), `canonical.runtime.brain_unified_model_v1` (16), `canonical.swe_kernel.perfect_algorithm_unified_v8` (16), `canonical.runtime.live_brain_route_admission_v1` (15), `canonical.swe_kernel.autonomous_awake_loop_v1` (14), `canonical.tests.test_unified_awake_cognitive_fabric_v1` (13), `canonical.tests.test_optimal_unified_creature_and_prc2_v1` (12)

## The manifest a composition root is allowed to dispatch to

| capability | class | entry | receipt present |
|---|---|---|---|
| `AUTHENTICATED_PARETO_SCHEDULE_V1` | TRUE_CAPABILITY | `canonical/runtime/scheduler_true_capability_adapters_v1.py``::solve_schedule` | True |
| `CAPABILITY_FIRST_RANKING_V1` | TRUE_CAPABILITY | `canonical/runtime/scheduler_true_capability_adapters_v1.py``::solve_ranking` | True |
| `DOCX_EXACT_TEXT_EDIT_V1` | TRUE_CAPABILITY | `canonical/runtime/docx_exact_text_edit.py``::solve_instance` | True |
| `DOCX_RUN_SPAN_REPLACE_V1` | TRUE_CAPABILITY | `canonical/runtime/docx_true_capability_adapters_v1.py``::solve_span` | True |
| `DOCX_STORY_PART_REPLACE_V1` | TRUE_CAPABILITY | `canonical/runtime/docx_true_capability_adapters_v1.py``::solve_story` | True |
| `DOCX_TEXT_EDIT_TRANSACTION_V1` | TRUE_CAPABILITY | `canonical/runtime/docx_true_capability_adapters_v1.py``::solve_transaction` | True |
| `FAMILY:COMPLEX_MULTI_TOOL_AGENCY` | FRONTIER_FAMILY | `canonical/runtime/matched_agency_stateful_case_v2.py` | True |
| `FAMILY:EXACT_SYMBOLIC_COMPUTATION` | FRONTIER_FAMILY | `-` | False |
| `FAMILY:INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT` | FRONTIER_FAMILY | `-` | True |
| `FAMILY:LONG_HORIZON_MEMORY_AND_CONTINUITY` | FRONTIER_FAMILY | `-` | False |
| `FAMILY:SELF_VERIFICATION_DEBUGGING_AND_RECOVERY` | FRONTIER_FAMILY | `-` | True |
| `FAMILY:SUBAGENT_DELEGATION_AND_COORDINATION` | FRONTIER_FAMILY | `-` | True |
| `FAMILY:TOOL_DISCOVERY_SELECTION_AND_LEARNING` | FRONTIER_FAMILY | `-` | True |
| `FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1` | TRUE_CAPABILITY | `canonical/runtime/file_change_true_capability_adapter_v1.py``::solve_through_the_front_door` | True |
| `FILE_QUESTION_TAUGHT_WORDS_V1` | TRUE_CAPABILITY | `canonical/runtime/taught_words_true_capability_adapter_v1.py``::solve_through_the_front_door` | True |
| `PARETO_FRONTIER_UPDATE_V1` | TRUE_CAPABILITY | `canonical/runtime/scheduler_true_capability_adapters_v1.py``::solve_frontier` | True |
| `SACCR_CREDIT_ADDON_V1` | TRUE_CAPABILITY | `canonical/runtime/saccr_credit_kernel.py``::solve_instance` | True |
| `SAME_IDENTITY_SUPERVISOR_V1` | TRUE_CAPABILITY | `canonical/runtime/same_identity_supervisor.py``::solve_instance` | True |
