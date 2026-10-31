# SWE mechanism reuse and current-main integration — 2026-10-31

Local sandbox measurement; authority NONE. This report is not a terminal-goal
claim or an independent runtime-verification receipt. The signed referee judges
repository integrity separately; it does not turn a failing test into a pass.

## Changes

Reused existing Brain implementations discovered at `cd44f98`, then integrated
rather than restoring old modules wholesale. Merged current main through
`04b6cbb8329507cbd139b7df2038c0eb2c56c237`; preserved its bisect materialization
limits, request-role rules and guarded retry behavior. Runtime and tests import
only current-tree source, never the discovery copies.

* Restored interprocedural taint summaries and helper-to-sink propagation.
  Restricted shell quoting to shell contexts; HTML/URL/shell escaping cannot
  erase taint headed for Python execution. Defined functions named `int` do not
  receive the built-in coercion exemption.
* Combined interprocedural structural cost estimates with the current
  cyclomatic metric. Reports explicitly say the estimates are **not asymptotic
  proofs**: two recursive call sites alone do not establish an exponential
  recurrence. Taint reports likewise say they are not security proofs.
* Restored pure, request-local `build_index` by sharing the current index engine.
  Retained content/row-hash validation, incremental reuse, file-only scope and
  ignored generated directories. No historical pickle/stat-only/worker cache.
* Integrated typed-family routing, quoted Git-message roles, explicit destination
  preservation, local report allocation, structured contract checks and staged
  cross-file binding into the current gate chain. Plans never execute adapters.
  Parameter renames cannot silently select a function/symbol rename.
* Removed recovered extraction defaults that invented a helper name or zero
  line bounds. Stated spans remain the binder's evidence.
* Tightened native in-place cross-file verification: zero tests, all-skipped
  tests and malformed verification evidence cannot certify a repair. Its actual
  source-writing behavior is now declared in both registry views. A missing
  execution-row list cannot erase `tool_executed` or possible-side-effect facts
  and buy a second execution.
* Synchronized existing result contracts and the existing Git message slot.
  No capability IDs, terminal authority, protected policy or verifier was added.

## Measurements

The original 10-module cohort on main `b0784a5d` measured **65 failed, 101 passed**
(39.45 s). The same 166 case identities now measure **166 passed, zero failed**
inside the final current-tree run. One stale parent-directory scope expectation
was corrected to the stricter exact-file contract. Another test now requires
pre-execution parameter-route correction and explicitly forbids a fictitious
retry; its original refusal/supersession controls remain in place.

Final expanded run: **571 passed, 6 failed, 947 subtests passed**, 12 deprecation
warnings, 163.87 s; 41 modules, 577 ordinary cases. All **19 new joint-contract
controls** pass. This is not a whole-repository green result. The six unresolved
compatibility failures are listed below rather than weakened or hidden.

| Index measurement, five 200-file trials | Median |
|---|---:|
| Cold | 32.511 ms |
| Warm, identical output digest | 7.360 ms |
| Warm modules parsed / reused | 0 / 200 |

This demonstrates preservation of the existing warm cache (about 4.42x on this
fixture), not a universal speedup or a new cache invention. Timings are local,
not an independent benchmark. A broader 1,723-case attempt was stopped
during a registry-wide controller exercise; it has no completed-suite verdict.

## Unresolved compatibility checks

* `canonical.tests.test_a_question_about_one_source_file_is_answered_about_that_file_v1.AQuestionAboutOneFileIsAnsweredAboutThatFileTests::test_the_audit_reports_that_file_and_not_its_siblings`
* `canonical.tests.test_capability_selection_retrieval_v1.GoalDrivenSelectionTests::test_a_plain_sentence_is_planned_executed_and_reverified_with_a_real_result`
* `canonical.tests.test_live_brain_route_admission_v1::test_single_word_evidence_is_rejected`
* `canonical.tests.test_live_brain_route_admission_v1::test_both_live_doors_give_the_same_verdict_on_one_sentence`
* `canonical.tests.test_live_brain_route_admission_v1::test_r9_does_not_move_the_compile_or_selection_rates`
* `canonical.tests.test_live_brain_route_admission_v1::test_a_no_op_goal_is_refused_at_the_door_and_a_real_repair_is_not`

These cover an audit-vs-definition-count identity expectation, module-call
routing, a compiler-count census and pinned refusal classifications. Some are
interface drift; no blanket pre-existing-failure claim is made without a
matched baseline. Exact file-scope/caller, review non-mutation, cache freshness,
structured acceptance, staged rollback and retry boundaries are exercised by
the passing controls. Four older audit-identity assertions also remain failing
in `test_the_write_lane_runs_the_capability_the_sentence_asked_for_v1.py`;
the extraction end-to-end case in that module was separately repaired and passes.

## Reproduce the expanded current-tree run

```bash
python3 -m pytest -q \
  canonical/tests/test_a_bisect_without_a_known_good_commit_is_not_certified_v1.py \
  canonical/tests/test_a_failed_attempt_is_not_a_verdict_v1.py \
  canonical/tests/test_a_mutation_score_is_measured_not_asserted_v1.py \
  canonical/tests/test_a_question_about_one_source_file_is_answered_about_that_file_v1.py \
  canonical/tests/test_a_refusal_is_not_answered_by_a_substitute_v1.py \
  canonical/tests/test_a_refused_request_leaves_the_tree_alone_v1.py \
  canonical/tests/test_a_rename_question_is_answered_by_a_plan_v1.py \
  canonical/tests/test_a_repair_is_an_edit_and_a_referee_v1.py \
  canonical/tests/test_a_report_is_never_written_over_its_subject_v1.py \
  canonical/tests/test_a_report_never_replaces_a_source_file_v1.py \
  canonical/tests/test_a_review_is_not_answered_by_a_mutator_v1.py \
  canonical/tests/test_a_search_never_runs_when_the_target_is_already_there_v1.py \
  canonical/tests/test_a_sentence_reaches_the_repair_it_names_v1.py \
  canonical/tests/test_a_stated_defect_is_a_request_to_repair_v1.py \
  canonical/tests/test_a_stated_effect_is_answered_by_a_capability_that_declares_it_v1.py \
  canonical/tests/test_a_stated_function_is_written_wired_and_tested_v1.py \
  canonical/tests/test_adapter_default_ast_walk_v1.py \
  canonical/tests/test_capability_selection_retrieval_v1.py \
  canonical/tests/test_declared_input_derivation_v1.py \
  canonical/tests/test_hardcore_swe_capabilities_20261031_v1.py \
  canonical/tests/test_hardcore_swe_capabilities_and_speed_v1.py \
  canonical/tests/test_live_brain_route_admission_v1.py \
  canonical/tests/test_python_source_symbol_index_v1.py \
  canonical/tests/test_python_symbol_index_cache_freshness_v1.py \
  canonical/tests/test_software_implementation_effect_admission_v1.py \
  canonical/tests/test_swe_acceptance_boundaries_20261031_v1.py \
  canonical/tests/test_swe_family_effect_filter_v1.py \
  canonical/tests/test_swe_git_intent_reuse_v1.py \
  canonical/tests/test_swe_main_integration_v1.py \
  canonical/tests/test_swe_reuse_joint_contracts_v1.py \
  canonical/tests/test_swe_stated_report_destination_v1.py \
  canonical/tests/test_swe_typed_plan_v1.py \
  canonical/tests/test_task_bound_crossfile_workflow_v1.py \
  canonical/tests/test_the_index_remembers_what_it_already_read_v1.py \
  canonical/tests/test_the_stated_swe_surface_stays_reached_v1.py \
  canonical/tests/test_a_bisect_materialises_only_the_named_tree_v1.py \
  canonical/tests/test_the_answer_must_be_the_effect_that_was_stated_v1.py \
  canonical/tests/test_the_rename_answers_the_object_the_sentence_names_v1.py \
  canonical/tests/test_brain_unified_model_v1.py \
  canonical/tests/test_goal_compiler.py \
  canonical/tests/test_goal_compiler_world_binding_v1.py --tb=short
```

The original cohort comprises `test_swe_acceptance_boundaries_20261031_v1`,
`test_hardcore_swe_capabilities_20261031_v1`, `test_task_bound_crossfile_workflow_v1`,
`test_swe_git_intent_reuse_v1`, `test_swe_family_effect_filter_v1`,
`test_swe_stated_report_destination_v1`, `test_swe_typed_plan_v1`,
`test_declared_input_derivation_v1`, `test_a_report_never_replaces_a_source_file_v1`
and `test_the_stated_swe_surface_stays_reached_v1` under `canonical/tests/`.

## Limits

Static summaries are bounded/name-based, not full Python dispatch analysis.
Structural complexity assumes a unit-cost loop model and does not solve arbitrary
recurrences. Native in-place repair is not a full filesystem transaction or a
sandbox. The passing fixtures do not prove general semantic correctness, global
optimality, universal speed, or completion of the project's terminal goal.

## Latest-main integration and report provenance

Retained main's premise-versus-request and question-versus-repair distinctions,
including indirect questions. Applied the premise distinction consistently to
both effect shortlisting and the answer gate. Test selection now requires a
selection effect: a generic impact index alone is not an answer naming tests.

Two neighboring change-impact tests were reading an old shared
`spool_0_output.json` even though the current request produced its own report.
They now require the actual test-selector execution, read the returned path and
check its SHA-256 before checking selected/candidate tests. The assertions still
require the module's test to be found. Both pass, along with the 19 joint controls.

During the in-progress main merge, the existing Git diff verifier refused the
staged action-intent rename (`INDEPENDENT_CHECK_DISAGREES` on brace-form rename
output). This is a remaining adapter limitation; no refusal was overridden.
Completing the merge removed that transient tree state; the final 577-case run
includes both public Git reads passing and all 166 original case identities passing.

## Compiled-model and admission checks

Regenerated the unified model with the official compiler and ran the existing
verifier on fresh instances: **33/33 passed**, including six execution cases and
five negative controls. This local result is not an independent capability receipt.
The action intent requests zero credit and distinguishes its subjective scheduling
assumptions from measured confidence bounds. Current-base load-bearing/orientation
and hierarchy/OBS/blocker-lease checks pass locally; the final signed referee
must still judge the exact pushed head before landing.

The final 577-case engineering run exercised commit `cb21400a`, including main
`9f808230`. Retained its new object-role checks at typed admission and at the
execution exit; preserved our independent generic-path admission restriction.
All seven incoming object-role cases pass. Also retained the inventory/probe
additions and corrected caller-damage allowance from main `57edfa44`.
Model and admission checks were refreshed for the resulting current base.

## Existing-output source-role regression

The CI model verifier itself passed 33/33, but its subsequent 137-test
model/compiler suite exposed a shared binding bug: an existing report destination
could fill a `source_root` input and make an audit row steal a compound transform.
The raw binder now reuses its output-role/claimed-path machinery to exclude a
stated destination from scope candidates, and rejects a scope equal to a bound
output regardless of slot order. No document-specific route was added.
Two fresh file/directory controls require refusal and pair it with a real-source
positive case. All **137 model/compiler tests now pass** inside the final expanded
run, with the original six SWE compatibility failures still reported above.

Latest-main carry: subsequently merged `5029bf7d`'s Git-question/composer rule.
The new Git-question suite plus the existing Git-intent and joint-boundary suites
measure **46 passed** on the merged source. The 577-case measurement above is
explicitly the earlier `cb21400a` run; the new main tests supplement it rather
than being silently included in that count. Model/admission records were rebound.

Retained main `95e70a31`'s repair-search/localizer improvements and integrated its
three derivation rules without restoring its older duplicate module body.
Directory-test discovery and the test-owning code root are retained; an extraction
span can also come from the new unique self-contained data-flow block heuristic.
That heuristic is not a proof of arbitrary prose meaning. Zero line sentinels and
invented helper names stay removed. Derivation/joint/Git-question controls:
**32 passed**. This supplements the earlier 577-case measurement.

## Final current-main controls and census

Retained main `04b6cbb8`'s new census gate unchanged. The incoming test-owner
inference initially displaced explicit source roots and broke five original
stated-report cases. Fixed the integration at the evidence boundary: inference
is confined to test-consuming rows, preserves an explicit source role, and
starts with the test-owning directory itself before trying ancestors. A new
read-only test-file control forbids widening to the source tree.

On merged commit `6f187586`: **205 passed**, 38.15 s, including all original
166 cases, **20 joint controls**, and coupled/test-guided repair tests.
The live surface census then measured **27/28 reached** with `--jobs 4 --floor 25`;
only `fix_then_regression_test` remains unreached. The floor was not lowered.
These current-main checks supplement the earlier 577-case run, not replace or
retroactively change its six failures or its count of 19 joint controls.

CI on the earlier head also passed the signed referee, admission and structural
checks. Its non-required same-identity UBJSON mission failed in the worker/relay
step after its relay/compiler unit checks passed; the cause is not attributed
without a diagnostic trace. The long heartbeat is not represented as completed.
The final head must obtain its own signed verdict and model/compiler CI result.

Final landing integration also retains main `ecfc9fb0`'s V13 inventory.
Its incoming diff adds the inventory Markdown and its generated model index;
no runtime source changed. The combined model was regenerated and subjected to
the fresh 33-case verifier; the 205-case/census measurements above retain their
original measured-source attribution.
