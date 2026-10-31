# Complete stated-file binding before SWE selection — 2026-10-31

Authority: NONE. Local sandbox regressions, not independent capability
qualification, benchmark/family promotion, or terminal progress certification.
Base: `fabf28c4ba5c947ad0341c083a2ae64db11aaaab` (merged PR6463).

## Observed defect and bounded repair

A function-call request names a Python module, a JSON payload and a destination.
The pinned compiler selected a source indexer using only the module and the
destination. The existing typed selector already proposed and completely bound
the existing module invoker; the front compiler never consulted it because a
specific lexical winner had bound *some* inputs.

The front compiler now checks whether its single-capability binding drops a
named file. It reuses the compiler's path parser and existing bounded typed
selector, admission, ambiguity and receipt/derived-evidence rules. A complete
specific binding remains unchanged and does not invoke retrieval. A replacement
must cover the stated files; otherwise compilation refuses rather than running
an incomplete tool. No tool-ID override, new capability or runtime dependency.

Directory scopes retain ownership of contained files and existing test paths
stated relative to a bound repository. Lists and whole-goal arguments retain
their file evidence; absolute/relative spellings normalize through the existing
parser. URLs and directory/context tokens are not additional input files.
This is a necessary completeness check, **not a semantic correctness proof** or
a new path parser: bare names without a slash remain outside that parser's
coverage, and a complete binding still needs all existing admission gates.

## Important promotion boundary retained

The live registry marks the invoker `RECEIPT_BACKED_PENDING_PROMOTION`.
`is_verified_entry` deliberately excludes that population from unnamed routing.
This change does not alter that policy, registry, evidence or promotion state.
Consequently, structured compilation over the declared registry can select the
existing invoker, and its existing adapter produces the expected result against
a direct-call oracle. The public doors refuse when their admitted registry has
no complete alternative. They do **not** execute an indexer while discarding the
payload. The old tests requiring successful unnamed live invocation remain
unresolved; they were not weakened to make this change appear complete.

## Measurements

Before changes, the existing selection module plus both-live-door parity case
measured **10 passed, 3 failed in 2.54 s**. After the first repair it measured
**11 passed, 2 failed in 1.40 s**: structured selection repaired; public invocation
still gated as described above.

An initial 45-module expanded run measured **598 passed, 12 failed, 949 subtests
passed in 169.63 s**. It exposed one new relative-test-scope regression in Git
bisect, which was repaired by recognizing files within the already-bound
repository scope. Two failures were generated-model staleness before official
regeneration. The remaining failures were retained, not skipped or loosened.
Final focused, expanded and official-model results are recorded below after
validation. No whole-repository green or universal speedup claim.

## Regression controls

`canonical/tests/test_stated_input_coverage_v1.py` checks complete invocation,
a real adapter result against `classify_support`, incomplete/missing input
refusal, a renamed invoker ID, ambiguous complete alternatives, unchanged
specific source analysis, absolute/relative equivalence, list/whole-goal
bindings, relative repository test scope, out-of-scope files and URL/context
handling. Selection-only controls assert that no result artifact is written.
Original tests and their exact result expectations are unchanged.

## Reproduce

```sh
python -m pytest -q canonical/tests/test_stated_input_coverage_v1.py \
  canonical/tests/test_capability_selection_retrieval_v1.py \
  canonical/tests/test_hardcore_swe_capabilities_and_speed_v1.py
python -m canonical.runtime.compile_brain_unified_model_v1
python -m canonical.runtime.verify_brain_unified_model_v1 --output <local-report.json>
```

The expanded cohort is the 41-module command in
`SWE_REUSE_INTEGRATION_20261031.md`, plus stated-input coverage, exact SWE intent
scope, path-does-not-choose-capability, and output-destination binding controls.
Generated test/controller state and local logs are not part of the patch.

## Completed local validation before incoming-main integration

* Focused stated-input coverage plus existing advanced SWE/speed module:
  **17 passed, 2.11 s**, including all **12 new controls** and real adapter output.
* Expanded 45-module cohort after the relative-test-scope repair and official
  model regeneration: **604 passed, 9 failed, 949 subtests passed, 162.12 s**,
  12 deprecation warnings. All original **166** cohort identities passed.
* Official model verifier: **33/33 passed**. This is the existing sandbox verifier,
  not an independent capability-promotion receipt.
* Warm completeness helper: median **25.672 microseconds/call**, nine trials of
  200 calls over a three-path module/payload/output request. This measures only
  local helper overhead, not end-to-end latency or improvement over a baseline.

Remaining exact failed IDs (unchanged assertions; not a whole-suite pass):

- `test_a_question_about_one_source_file_is_answered_about_that_file_v1.AQuestionAboutOneFileIsAnsweredAboutThatFileTests::test_the_audit_reports_that_file_and_not_its_siblings`
- `test_capability_selection_retrieval_v1.GoalDrivenSelectionTests::test_a_plain_sentence_is_planned_executed_and_reverified_with_a_real_result`
- `test_live_brain_route_admission_v1::test_path_token_only_match_is_rejected_before_execution`
- `test_live_brain_route_admission_v1::test_single_word_evidence_is_rejected`
- `test_live_brain_route_admission_v1::test_a_source_root_key_binds_from_the_goal`
- `test_live_brain_route_admission_v1::test_both_live_doors_give_the_same_verdict_on_one_sentence`
- `test_live_brain_route_admission_v1::test_r9_does_not_move_the_compile_or_selection_rates`
- `test_live_brain_route_admission_v1::test_a_no_op_goal_is_refused_at_the_door_and_a_real_repair_is_not`
- `test_output_destination_is_not_an_input_candidate_v1.SelectionSuiteIsOrderIndependentTests::test_the_selection_module_passes_as_a_whole`

The last failure re-runs the existing selection module and inherits its unresolved
public invocation expectation. The two public invocation expectations remain red
rather than bypass the live admission policy. The other failures concern exact
capability identities, scope, compiler counts and refusal classifications; this
change makes no blanket claim about their causes or baseline status.

## Incoming-main integration validation

Retained main `8679d55` unchanged, including PR6479's empty-diff semantics and
PR6481's inventory V16. Rebuilt the combined model through the official compiler.

- Original 166-case SWE cohort + model/compiler suites + all 12 new controls:
  **315 passed, 905 subtests passed, 68.82 s**, 8 deprecation warnings.
- Focused coverage/intent/Git/joint-contract/advanced-speed integration:
  **88 passed, 5.94 s**. These overlap the preceding cohort; do not sum them.
- Fresh official model verification: **33/33 passed**; model digest
  `899178d7ccf8c5d1542178d21245b9b9120c20c77191b1303de78fd658bb9bba`.
- Local current-base hierarchy/prewrite admission: `DRIFT_GUARD_PASS`.

These post-integration measurements do not constitute a rerun of the entire
45-module expanded cohort. Its nine residual failures above remain explicitly
open. Signed remote repository-integrity admission is required separately before
landing; no local run can manufacture that signature.
