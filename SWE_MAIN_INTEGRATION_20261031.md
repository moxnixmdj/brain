# SWE integration — 2026-10-31

## Status

All accumulated work is preserved on `arena/4b31f8b6-brain`, with main integrated through `270dad3e0a5f169d8da0fc2ee86fdd90ef139ccb`. This is **not a claim that PR #6341 has landed**. Required admission checks reject the missing action intent and the broad accumulated scope. No policy bypass, protected-file edit, or relabeling as governance was performed.

## Reuse and integration

- Preserve the explicit report-destination and effect-first caller-selection fixes.
- Restore exactly three existing registry declarations removed from current main: `python.source.symbols.index.ast`, `python.refactor.inline_helper.v1`, and `python.source.change_impact.testselect.v1`. These reuse existing adapters, not new engines.
- Combine upstream parallel symbol indexing with the pure `build_index` interface used by request-local caching.
- Preserve upstream evidence-first mutation ranking and separate neighborhood budgets while reusing the parse-once candidate renderer.
- Preserve first-success guided-search termination, wall limits, and two fresh winner replays.
- Retain both isolated task-bound cross-file choreography and upstream in-place repair algorithms. Explicit staged arguments never fall back to in-place repair.
- Retain structured-contract repair acceptance and upstream source/test fixture CEGIS as distinct protocols. Budget-only invocation still refuses; structured checks cannot silently downgrade to fixture mode.
- Retain upstream trace inspectors alongside task-bound report inspection.
- Keep default namespace confinement and optional null-only exposure. Additional runtime devices/private proc require an explicit boolean policy, change its digest/authority, and do not silently widen null-only authority. Reuse fixed-system-path binary resolution and syscall chroot portability.

The source/test-only legacy workflows can modify the stated source tree. The isolated structured workflows retain their original source-preservation guarantees. They are not interchangeable verification claims.

## Fresh measurements

Tests ran directly against this working tree, without historical-file substitution or test-result caching.

- Final 16-module regression run: **288 passed, 4 failed**, 96.02 seconds, one tree-sitter deprecation warning; 292 cases total.
- The ten new integration cases passed within that run: a real 70-file parallel index, real conflict repair, malformed staged-request refusal, real fixture CEGIS repair, strict device-policy typing/digests, and an actual namespace with opted-in devices/private proc.
- Existing renderer tests now independently check upstream metadata and exact legacy/neighborhood reserve counts. Exact process counts are retained; no acceptance assertion was weakened to tolerate either outcome.
- Integrity guard against integrated main: **17 rules, 0 violations, PASS**. Exactly three registry restorations are within the registration limit.
- Python syntax/diff-whitespace checks passed for the changed runtime/tests. Upstream's unrelated tracked patch artifacts contain existing whitespace findings relative to the old branch; they were not rewritten.

Four unresolved regression cases:

1. `test_python_provenance_guided_coupled_repair_v1.py::T::test_provenance_present`: zero interprocedural hypotheses where the test requires a positive count.
2. `test_task_bound_crossfile_workflow_v1.py::test_registry_presence_cannot_credit_fullstack_delivery`: current registry does not resolve all producer declarations expected by the test. Delivery remains unverified.
3. `test_front_door_task_bound_contracts_v1.py::test_normal_public_request_executes_real_repair_and_requested_checks`: successful repair lacks expected `typed_swe_selection` metadata.
4. `test_front_door_task_bound_contracts_v1.py::test_unknown_requirement_in_goal_is_not_removed_by_structured_checks`: refusal occurs after execution rather than before it.

The first pre-restoration run was **225 passed, 28 failed**, 97.95 seconds. It exposed missing registry declarations and obsolete pre-neighborhood test expectations; it is not an equal-configuration performance baseline. No overall speedup is claimed.

## Compiled artifact

Regenerated using `canonical/runtime/compile_brain_unified_model_v1.py`:

- Digest: `2038c534aa5a086667c823173ce052a3c266ebcccf8602dd698b3298647abf06`
- 364 capabilities: 69 bound, 295 receipt-backed.
- Compiler serialization/reload digest check passed.
- Full model verification **did not complete**: the negative-control driver requests `python.source.audit.ast`, absent from the current registry/model, and raises `CAPABILITY_NOT_IN_MODEL`. No fresh 33/33 claim is made. Restoring a fourth declaration in this PR would violate the registration limit.

## Landing blockers

Local goal admission reports `ACTION_INTENT_MISSING`, associated intent/parent/probe requirements, and `FRONTIER_PR_SCOPE_TOO_BROAD_RECONCILE_AND_SPLIT`. Load-bearing admission reports `EXACTLY_ONE_ACTION_INTENT_REQUIRED`.

Adding an intent alone does not resolve the >15-sensitive-file scope restriction. The accumulated SWE batch is not a governance change and must not be labeled as one to evade the restriction. The work remains preserved for legitimate scope reconciliation; no protected-check bypass or main-branch force push is authorized.

These are sandbox measurements by the producer, not independent verification or evidence of universal software-repair capability.
