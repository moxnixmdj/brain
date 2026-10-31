# Reuse the existing destination-role boundary; stop state-dependent SWE report routing

2026-10-31. Local development evidence, not independent capability admission or a full-suite verdict.

## Result

Reused Brain's existing destination-role detector, typed SWE plan, structured-contract preflight, and no-overwrite report mechanism. No new capability, registry edit, dependency requirement, policy change, test weakening, import hook, or successful-result cache was introduced by this correction. No internet implementation was needed: the relevant mechanisms already existed in Brain.

The change prevents an explicitly requested SWE report destination from being replaced by a shared spool path when the destination already exists. It also fixes two existing source/destination regression tests by making destination exclusion apply to successful pinned bindings and joint-role elimination, not only type fallback.

This is a correctness and avoided-work improvement. It is not a demonstrated whole-system speedup, general repair qualification, or claim that all previously inventoried problems are solved.

## Actual root cause, not another intermittent-rerun explanation

A fresh run of the existing public-contract/refusal modules produced **33 passed, 1 failed in 11.72 s**. The failure was `test_existing_report_is_preserved_before_execution`: the request unexpectedly returned `pass: true`.

Directly inspected real compilation/typed-plan results showed the user's existing `.../front-contract-.../report.json` binding to **`canonical/astra_runtime/tmp/spool_0_output.json`** instead. The structured-contract preflight therefore inspected the wrong path.

- If that spool was absent, repair could execute and report success for a request that should have refused its occupied destination.
- If it already existed, the same request refused because the spool existed, not because the correct destination had been bound.
- This provides a concrete shared-state mechanism consistent with the earlier report-preservation and repair-success inconsistencies. It does not establish that every historical public-entry failure had this cause.

The destination-role machinery already existed in `goal_front_compiler_v1._named_output_destinations`. It was used only to exclude some type-fallback input candidates, not to preserve a destination in the typed SWE plan.

Connecting that mechanism exposed another defect: the directory `src` in `report to src/report.json for the source root src` was judged at its first substring occurrence inside `src/report.json`. A path prefix is not a complete occurrence of the separately named directory. The existing detector could consequently classify both the report and its source directory as destinations.

## Changes

### `canonical/runtime/swe_typed_plan_v1.py`

After existing selection and input derivation, reuse the front compiler's declared-role detector for `output_path`:

- exactly one explicit destination remains the destination regardless of existence;
- multiple explicit destinations refuse rather than arbitrarily selecting/spooling one;
- incidental bindings onto source code can still be relocated when no destination was stated;
- an explicitly stated destination on an existing source/test file is not silently relocated; preserve its identity so existing write/repair preflight can refuse it.

This does not grant overwrite authority. Existing guards still judge the bound destination.

### `canonical/runtime/goal_front_compiler_v1.py`

- Reject path-prefix occurrences in `_role_anchored`; `/child`, `_suffix`, `-suffix`, an alphanumeric continuation, and `.extension` continue a path. A final sentence period does not.
- Compute stated destinations once per `bind_all_inputs` call.
- Reject a successful pinned input binding that points to a stated destination.
- Reserve those destinations before joint-role elimination as well as type fallback.
- Reuse the computed destination set in both fallback branches instead of repeating its derivation there.

The shared role vocabulary, declared templates, execution adapters, expectations and acceptance rules remain in use. No new prose parser or hardcoded tool table was built.

### Regression tests

`canonical/tests/test_swe_stated_report_destination_v1.py`: **13 cases**, exercising actual compiler/selection paths without registry/filesystem/compiler mocks:

- new/existing report paths, with and without reusing the compiled request context;
- context and project-byte preservation;
- repeated public refusals for an existing report, source file and test file;
- refusal of two explicit destinations;
- five path-prefix continuations, repeated mentions and final sentence punctuation.

The owned test script writes an execution marker if actually run. Occupied-destination tests compare all project files before/after, as well as requiring `executed: false`; preservation is not inferred solely from a result flag.

## Tests and measurements

Environment: Python 3.11, locally recreated `.venv`, pytest 9.2.0, Hypothesis 6.170.12, tree-sitter 0.20.4 and tree-sitter-languages 1.10.2. Installation ran outside tests; test infrastructure was not changed.

| Selection | Result |
|---|---|
| Initial new eight-case regression module, before runtime correction | **3 failed, 5 passed in 2.38 s** |
| Final new module + public contract/refusal + destination-role + selection/declaration tests | **69 passed in 14.73 s** |
| Final repair reuse, confined repair, portfolio, shared rendering/execution, publication, index-context and cross-file qualification selection | **152 passed in 117.47 s** |
| Compiled-model verifier after regeneration | **33/33 PASS** |

The first attempt to connect the existing detector revealed the path-prefix defect and failed extensively. That intermediate implementation was corrected; its results were not represented as final success.

### Before/after discrimination of existing failures

Ran the same selected eleven initially failing adjacent nodes plus the thirteen new cases against the actual before and after runtime source trees in separate pytest processes. Source files on disk were changed openly between runs, then restored to the corrected version; there were no historical-file import substitutions or assertion changes.

- Before: **20 failed, 4 passed in 8.40 s**.
- After: **9 failed, 15 passed in 8.76 s**.
- The new cases and the two pre-existing `DestinationIsNotASourceTests` now pass.
- The nine remaining nodes fail on both runtime versions.

This is a deliberately failure-enriched selection, not an overall success-rate benchmark. The execution-marker strengthening was added afterwards and is covered by the final 69-case run.

External experiment details/source hashes: `/home/user/swe-destination-version-comparison.json`; source-version comparison driver: `/home/user/compare_swe_destination_versions.py`.

### Bounded extended run: incomplete and red

An expanded 15-module run was interrupted after **293.52 s**, with **258 passed, 11 failed, 18 subtests passed** and four warnings. It did not finish. The original bash wait timed out at 180 s; the existing process was not duplicated. It was later interrupted explicitly; no test process was left running.

Nine failures were reproduced on both before/after versions:

1. bare-fix retry test expects refusal but gets success;
2. caller-family execution refuses write authority;
3. caller-family plan is not decisive;
4. caller-family mutation control cannot establish its initial plan;
5. single-word admission chooses a different refusal rule;
6. registry proof test finds an inline-helper row without a verification block;
7. two live doors disagree on a sentence;
8. compile/selection counts are 21/19 rather than asserted 23/22;
9. no-op goal reports a composed-step exception rather than the expected observed-effect refusal.

The expansion adds two failures not yet before/after-triaged:

10. `test_f1_best_candidate_that_cannot_bind_fails_closed_instead_of_falling_through`;
11. `test_every_capability_is_reachable_from_one_sentence_by_prose_or_by_name`.

The long-running continuation was interrupted inside `goal_compiler.py`. This cycle does not diagnose that runtime cost or establish that the two additional failures are pre-existing. No claim of a green adjacent/full suite.

### Real preflight latency

21 actual repeated public requests on one owned project, one process, with an occupied requested report:

- first request **220.793 ms**;
- remaining 20 median **123.555 ms**, maximum **137.930 ms**;
- all refused before execution with `CONTRACT_REPORT_ALREADY_EXISTS`;
- all project bytes preserved; test-execution marker absent.

Data: `/home/user/swe-destination-preflight-latency.json`. These are refusal timings, not repair timings, fresh-process startup, a before/after latency comparison or proof of fastest execution.

## Generated model and integrity

Regenerated `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` using the existing compiler, not hand-edited hashes. Its verifier reports **33/33 PASS**; digest `3146d171248b82c146046a70e54fa5d504328e0c187406befde77960927082da`.

- Static integrity: **11 rules, zero violations, PASS**.
- Explicit diff integrity against local `HEAD` (`c79a8f5`): **17 rules, one violation, FAIL**: `CAPABILITY_REGISTRATION_FLOOD`, eight additions versus limit three in the already-present aggregate registry diff. This correction did not modify the registry or add capabilities.
- Diff check for changed runtime files and generated model: clean.
- No independent-verifier receipt, capability promotion, policy relaxation, merge, commit or push is claimed.

## Workspace and scope

The starting checkout already had a large working-tree delta, including main integration work, registry changes, runtime implementations and tests. Those were preserved. The local branch still reports `c79a8f5`, whereas the previously pushed PR head is `8121f434`; this source-control discrepancy was not repaired by resetting or discarding work.

This correction changes two runtime files, adds one test module and this report, and refreshes the generated model. Newly generated test state (eleven files, including checkpoints) was archived outside the repository under `/home/user/swe-destination-generated-state`, with hashes and original locations in `archive-index.json`. Pre-existing files were not removed.

The current PR admission/scope blockers are not solved by this local correction. The next engineering step is a bounded triage of the remaining route-selection/acceptance failures and the long-running compiler path, reusing the existing mechanisms rather than adding another wrapper or claiming general optimality.
