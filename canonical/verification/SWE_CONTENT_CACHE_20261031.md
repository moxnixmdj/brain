# SWE derivation content cache — local engineering evidence

Date: 2026-10-31. Baseline: `2e9b6427a1d5d7e22610810efd71e052fc343c4d`
(main including PR6485). Scope: shared source evidence in
`canonical/runtime/declared_input_derivation_v1.py` only, plus regressions,
admission metadata and the official regenerated model projection.

## Reuse and mechanism

The existing `python_source_symbol_index.py` validates the SHA-256 of current
source bytes; its freshness tests already reject equal-size edits with restored
mtime. Reuse that rule with the existing stdlib `hashlib` and AST parser, not a
new analyzer, cache service or parser package. The existing default detector and
all callers remain in place.

* Read current bytes before every lookup; a digest and AST always describe the
  same byte buffer. Metadata cannot validate source evidence.
* Share a content-bound AST between adapter-default and source-symbol derivation.
* Keep the latest revision per path/context. Bound each cache to 512 entries;
  this is an entry-count bound, not a byte-budget guarantee.
* Retain root-specific evidence locations and defensive dictionary copies.
* Return no evidence for deleted, unreadable, malformed or invalid-UTF-8 source.
  Strict UTF-8 now also rejects invalid bytes in comments instead of silently
  manufacturing replacement characters for adapter-default evidence.
* Remove the default walk's unused parent map and intermediate node list.

The detector's semantics for valid source are unchanged, checked against the
existing full-tree differential oracle and real repair adapters. ASTs are shared
internal read-only data as before; this does not introduce write confinement or
promise an atomic snapshot across filesystem edits concurrent with a later run.

## Failure-first verification

Tests execute real current-tree code and real temporary files; no pins, test
rewrites, module injection, source-loader interception or weakened assertions.
New tests restore size and nanosecond mtime after edits, replace files, remove
files, invalidate UTF-8/syntax, change roots, mutate returned dictionaries, churn
revisions/paths, and profile actual `ast.parse` calls without replacing it.

* Initial 11 controls on the unchanged runtime: **9 failed, 2 passed**.
* Added a constant-size, constant-mtime revision-churn control: **12 controls**.
* Broader same-tree comparison (13 modules): unchanged runtime **35 failed,
  187 passed, 1 xfailed, 24 subtests passed** in 74.66 s; patched runtime
  **25 failed, 197 passed, 1 xfailed, 24 subtests passed** in 79.93 s.
  For the baseline comparison, openly restored only our runtime-file patch to
  the current base and ran the unchanged tests, then reapplied it. No harness
  remapping was used. **10 failure identities removed; none introduced.**
* Final directly affected eight-module run: **93 passed, 24 subtests passed**
  in 5.49 s. Includes all 12 new controls, existing AST differential/default,
  derivation, stated-input, typed-plan, Wave1, source-index and index-freshness
  tests. This is a focused regression result, not an all-repository pass.

## Bounded microbenchmark and cost trade-off

Real adapter: `python_provenance_guided_coupled_repair_v1.py`, 12,433 bytes.
Pair = `adapter_defaulted_keys(entry, root)` then `_tree_of(root, rel)`.
Nine rounds of 100 pairs per mode, `perf_counter_ns`, median per-call time;
cold clears both derivation caches before every pair, warm reuses unchanged
bytes. CPython 3.11 in this sandbox; before/after runs, not randomized production
measurements, confidence intervals or a frontier-agent comparison.

| Measurement | Before | After |
|---|---:|---:|
| Cold pair | 7.286 ms | 4.503 ms |
| Warm pair | 40.29 us | 80.55 us |
| Cold AST parses | 2 | 1 |
| Warm AST parses (profiled regression) | 0 | 0 |

Cold pairs were approximately **1.62x faster**; warm validation costs about
**40 us more** per pair because every request reads/hashes actual bytes. This
is deliberately not claimed as a warm-path speedup. The before/after defaults
are identical and the `ast.dump` SHA-256 is identical:
`4c4ee17ee9cf9142460d5fbff1c18860d4ce11503b2f21d20c2cdb057eb16047`.
Deleting caches would provide freshness but lose warm parse reuse; adding more
metadata would not supply byte evidence. No new production dependency.

## Discovery boundaries

Fresh main was fetched and its Wave1 changes reused rather than duplicated.
Read Brain's current symbol-index implementation and freshness controls.
Inspected the CPython `Lib/linecache.py` source excerpt through the GitHub API;
its metadata-based route does not address this counterexample. Public GitHub
repository search `python ast cache sha256` returned no results. This bounded
search is not a literature survey or a claim that no better implementation exists.

## Residual failures (same identities on baseline and patched runtime)

The broad suite is **not green**. The following 25 existing failures were not
suppressed or claimed fixed; source-index report-location, compiler/routing
expectations, type totality and Git operation-contract compatibility remain
outside this cache patch:

* `canonical/tests/test_swe_family_effect_filter_v1.py::test_real_caller_request_executes_index_without_modifying_source[add]`
* `canonical/tests/test_swe_family_effect_filter_v1.py::test_real_caller_request_executes_index_without_modifying_source[repair]`
* `canonical/tests/test_swe_family_effect_filter_v1.py::test_real_caller_request_executes_index_without_modifying_source[update]`
* `canonical/tests/test_swe_family_effect_filter_v1.py::test_real_caller_request_executes_index_without_modifying_source[rename]`
* `canonical/tests/test_swe_family_effect_filter_v1.py::test_real_caller_request_executes_index_without_modifying_source[remove]`
* `canonical/tests/test_swe_family_effect_filter_v1.py::test_real_caller_request_executes_index_without_modifying_source[fix]`
* `canonical/tests/test_swe_family_effect_filter_v1.py::test_actual_empty_caller_set_is_not_invented`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f1_best_candidate_that_cannot_bind_fails_closed_instead_of_falling_through`
* `canonical/tests/test_goal_front_compiler_v1.py::test_every_capability_is_reachable_from_one_sentence_by_prose_or_by_name`
* `canonical/tests/test_goal_front_compiler_v1.py::test_every_capability_is_reachable_BY_PROSE_alone`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f11_multi_step_capability_dag_planned_and_executed`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f11_multi_step_capability_dag_with_bm25_ranking`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f11_five_step_metabolic_dag_executed_and_verified`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f11_eight_step_metabolic_dag_executed_and_verified`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f11_ten_step_metabolic_dag_executed_and_verified`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f13_intermediate_spool_assigned_when_the_sentence_names_no_artifact`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f16_an_id_shaped_path_that_no_capability_answers_to_fails_closed`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f23_two_same_type_inputs_bind_by_the_roles_the_sentence_states`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f23_a_role_in_front_of_a_conjunction_stays_open`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f24_a_candidate_the_sentence_never_gave_its_input_is_not_the_route`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f24_a_runtime_native_capability_is_admitted_on_the_contract_the_sentence_states`
* `canonical/tests/test_goal_front_compiler_v1.py::test_f24_an_ambiguous_statement_still_keeps_the_request_open`
* `canonical/tests/test_capability_selection_retrieval_v1.py::GoalDrivenSelectionTests::test_a_plain_sentence_is_planned_executed_and_reverified_with_a_real_result`
* `canonical/tests/test_capability_type_surface_v1.py::SurfaceTotalityTests::test_no_unknown_types`
* `canonical/tests/test_git_sentence_routing_v1.py::TheCapabilityIsReal::test_the_registry_row_declares_the_operation_contract`

## Credit and delivery

No registry addition, ownership promotion, authority/scoreboard edits, benchmark
qualification or terminal credit. These are producer-run local engineering
regressions, not independent capability certification. The wider advanced-SWE
audit is not solved by this bounded change. Delivery requires the exact final
head's repository/referee/admission/model checks; no red-check bypass.

Official artifact regeneration and model/goal-compiler verification are run
with repository commands after this indexed report is finalized. Their final
results and GitHub run links belong in the PR so the report does not recursively
invalidate its own model digest.

Integration: main advanced to `6c6c5df48cd96802ace3e9e5266c9493cca92bfc`
(PR6489 undeclared-effect refusal guard). Retain that runtime and its negative
controls unchanged; regenerate the combined model through the official compiler.
The earlier baseline comparison above remains bound to its explicitly stated
`2e9b6427` tree, not relabeled as a measurement of the newer base.

Second integration: main advanced to `9e6a366b0d0f99b1974b9056e3798e09f2ef6a5c`
(PR6486 requirement-effect declarations and route-admission negative controls).
Retain those changes and the matrix guard unchanged, rebind the intent and
regenerate the combined model officially. No earlier baseline result is relabeled.

The second integration run measured **242 passed, 1 failed, 931 subtests**:
PR6486 renamed the index's provided effect but duplicated it in the live
registry, while the snapshot already had one canonical effect and the older
exact registry test still expected the intentionally removed row-id alias. A
new uniqueness/no-row-id control failed on the incoming duplicate (**2 != 1**).
Normalize the live duplicate to match the already-canonical snapshot and change
the existing exact assertion to the now-declared single canonical effect.
This is an explicit contract migration plus a stronger invariant, not restoring
the obsolete alias, loosening the test, changing runtime effects or promoting
a capability. The snapshot itself needs no change.

Third integration: retain main `34f867a9d0b057d2bd9fcef1167c31d251b13f75`
(PR6490 package-root and answer-artifact fixes, PR6492 audit) unchanged. Run
the new answer/suite controls with cache/index/model tests and officially
regenerate the combined model. Earlier timing and broad comparison numbers
remain measurements of the explicitly identified earlier source, not the
subsequently edited repair adapter or newly integrated answer projection.

Final expanded 15-module integration run on the combined `34f867a9` tree:
**250 passed, 1 failed, 931 subtests passed**, four deprecation warnings,
41.93 s. The incoming test
`test_the_suite_runs_where_the_imports_point_v1.py::TheSuiteRunsWhereTheImportsPointTests::test_an_empty_localization_is_not_a_pass`
expects a localizer refusal but receives no exception in this environment.
Openly restoring only the derivation runtime to unchanged main and rerunning
that control reproduced **1 failed in 0.28 s**, then the cache patch was
reapplied. This is a confirmed incoming failure, not claimed fixed or hidden,
and not justification to broaden this cache integration into a localizer rewrite.
The other incoming package-root/answer controls and all 12 cache controls passed.
