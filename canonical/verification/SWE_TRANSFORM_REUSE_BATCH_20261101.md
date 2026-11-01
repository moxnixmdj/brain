# SWE transformation and retained-plan reuse: bounded implementation batch

Date: 2026-11-01. Base: `05762527e13e2d3345032f9b365df17b661c781f`.
Authority: NONE. These are agent-produced sandbox measurements, not independent capability receipts, terminal credit, or evidence of universal mastery.

## Implemented

- Reused the existing parser, subprocess reaper, route acceptance, project tests, learner and evidence/model compiler rather than adding a parallel learning architecture.
- Added shared transformation contracts and staged multi-file edits. Split destinations are checked before writing; failed split tests restore applied files. Public/decorated functions and explicit exports are protected from dead-code pruning; unresolved dynamic exports are handled conservatively.
- Optimizations retain the original body for unsupported domains. Integer/native reductions preserve arbitrary-precision behavior through checked overflow and Python fallback. Thread pooling is an additive reduction, not an approximation of arbitrary function chunking. A requested speed improvement must pass the speedup gate.
- Memoization refuses effects, mutable/default result hazards and unproved global dependencies. Closed arithmetic helpers have code/default guards, with fallback after changes. TypeScript rename edits supported identifier bindings, not literal/comment data, and rejects unsupported shadowing.
- The caller captures source preimages before execution, checks actual output and restores captured source after exceptions. Raw trace acceptance recomputes bounded structural checks rather than accepting only producer flags.
- Compiler stdout/stderr are separate and bounded, drained concurrently without a shell. Deadline handling reuses the existing reaper; the new single-command path cleans POSIX process groups after timeout, including descendant pipe holders.
- Existing transfer learning now reports interface action/reset calls (including fingerprint probes), persistence failures, the actual recalled-candidate count and its bounded 500-record retention policy. Chunked learning uses accumulated model state before the original prior.

## Measurements before current-main integration

The durable machine-readable summary is `SWE_TRANSFORM_REUSE_BATCH_20261101.json` in this directory.

- Focused transformation, restart-learning and ordered-abstraction run: **62 passed in 5.88 seconds**.
- Broader runnable run across 25 test modules: **398 passed, 6 failed, 1 skipped, 14 subtests passed**, pytest time **77.15 seconds**. This is not an all-green suite.
- The six failures are in `test_live_brain_route_admission_v1.py`. All six also fail when run against a separate, fresh `git archive` of the base tree, without loader patches or historical files supplied to the working-tree tests. That comparison does not constitute a full baseline suite run. The archive lacks Git metadata.
- Including `test_root3_subprocess_mediator_v2.py` stops collection: six legacy callsite mappings are stale in untouched `astra_runtime.py` and `python_test_audit.py`. Compiling the registry against a separate base-tree runtime archive reproduces the identical six missing sites. No mappings were re-stamped to hide this failure.
- POSIX child resource accounting for the 25-module run: elapsed **77.75 s**, child user **66.17 s**, child system **6.92 s**, maximum child RSS **213,268 KiB**. This is not an aggregate simultaneous process-tree peak or a per-task optimization comparison.
- Current 49-request advanced engineering census: **34 served, 15 refused**. There were no census-detected unauthorized edits. The guarded optimization request failed its speedup gate; the previous census reported 35 served. A census has no general behavioral oracle: “served” is not proof of correctness.

Separate-interpreter learning measurement using the same simple toggle environment:

| Run | Goal reached | Legacy trial count | Actual interface actions | Actual resets |
| --- | --- | ---: | ---: | ---: |
| Cold learning | yes | 8 | 23 | 17 |
| Restart with retained plan | yes | 1 | 15 | 8 |
| Transfer-disabled baseline | yes | 8 | 23 | 17 |
| Changed transition semantics | no | 8 | 23 | 17 |

The restart saving is real for this fixture; fingerprinting still costs work. Changed-environment rejection is not proof of applicability detection for every environment. This is not a different-repository or changed-dependency-version qualification.

## Evidence and governance

Used `module_invocation_evidence_v1.py --remeasure` with the actual broad-run JUnit, targeting only `live_brain_route_admission_v1.py` and the two evidence rows invalidated by the ordered-abstraction test edit. Failed `observed_effect_errors`, `route_admission` and `solve` evidence functions were refused, not promoted. Other inherited drift remains fail-closed. Model/module-invocation/integrity tests returned **85 passed, 1 failed, 913 subtests passed in 75.94 s**. The failed `test_check_mode_finds_no_drift` observes 21 stale evidence rows; calling the official checker against the separate base archive returns the identical 21 errors. No unrelated rows were re-pinned. Regenerated `BRAIN_UNIFIED_MODEL_V1.json` with the official compiler; no hand-edited evidence hashes, registry promotions, terminal claims or protected-path changes.

Existing test corrections are explicit: the dead-code fixture now uses private `_dead_fn`, because an unreferenced public function is not proven dead; ordered strategy abstraction expects a subsequence, not a sorted set, with an additional repeated-step regression.

## Boundaries and remaining plan

1. **Trustworthy/reversible execution: partial implementation.** `FileEdits` is exception rollback with staged replacement, not crash-atomic, concurrent-writer-isolated or an OS sandbox. Caller rollback covers captured source and known split destinations, not arbitrary external effects. The transition verifier checks selected structural invariants, not complete equivalence, arbitrary fast-path correctness or every public signature/effect.
2. **Retain/retrieve/reuse: existing mechanism instrumented and restart-tested.** Full integration of independently qualified SWE outcomes into parameterized executable skill records is still pending. The store has a bounded hot-record limit and no permanent archive/durability/concurrent-writer guarantee. Generic environment learning is not itself advanced software skill learning.
3. **Advanced mechanism curriculum: pending.** No claim that these repairs teach arbitrary cross-package feature work, systems programming, distributed concurrency, migrations or releases.
4. **Transfer qualification: partial tests only.** Restart, changed transition semantics, unsupported inputs, helper changes and generated-name variations are covered. Held-out repositories, dependency changes, compositions and separated teaching/evaluation remain required.
5. **End-to-end efficiency: measured, not optimized universally.** A safe but slower rewrite is refused. Broader compute/memory comparisons and dependency-aware proof reuse remain future work.
6. **Autonomy: unchanged.** No new capabilities, authority expansion, mastery or sentience claim.

## Reproduction

Focused tests:

```sh
.venv/bin/python -m pytest -q \
  canonical/tests/test_swe_transform_contracts_v1.py \
  canonical/tests/test_swe_learning_reuse_contracts_v1.py \
  canonical/tests/test_universal_learning_meta_policy_v9.py
```

The JSON summary records the complete broader test argv, failed case IDs, source hashes, observed census and learner counters. Use the repository's normal substrate restoration before running compiler/parser tests. Run the existing model/integrity checks against the current tree; do not conceal the disclosed baseline failures with historical fixtures or loader patches.

## Integrated current-main qualification

Integrated `073540db10dc8f56d5193281f24f2bd32f13550e` on the same working branch rather than replacing its maintained semantic graph, skill crystallizer, goal-DAG and cross-machine transfer changes. Kept action-availability checks before counting replay attempts; preserved staged/collision-checked split behavior for the supported self-contained functions, async functions and classes. Also fixed an integration regression: structured capability refusals must retain their top-level diagnostic `reason`, not only the nested payload.

- Merged SWE/learning/new-main targeted tests: **84 passed in 9.88 s**.
- Refusal-reason/transform/restart regressions: **102 passed, 15 subtests passed in 8.90 s**.
- Final 30-module integrated run: **445 passed, 6 failed, 1 skipped, 24 subtests passed in 81.54 s**. All six remaining failed cases also fail against an actual separate archive of `073540db` (2.25 s). This is not a full baseline comparison and the archive does not contain Git metadata.
- The additional missing-top-level-reason failure observed during integration was fixed and is no longer in the final six failures.
- Integrated census: **41 served, 8 refused of 49**, no census-detected unauthorized edits. The gain over the earlier 34 is primarily reuse of incoming main changes, not an isolated attribution to this patch. The optimization speedup request remains correctly refused. The census remains a shape/effect census, not a general semantic oracle.
- Final broader-run resource measurement: elapsed **82.14 s**, child user **71.58 s**, child system **7.69 s**, maximum child RSS **228,676 KiB**; not an aggregate process-tree peak. Learner fixture counts remain 23/15/23/23 actions and 17/8/17/17 resets.
- Targeted official evidence refresh leaves **21** stale rows fail-closed; incoming main had **22**. The Root3 V2 collection blocker is still present. Compilation alone or an alpha-renamed syntactic twin is not general behavioral qualification of the incoming skill store; no permanent-learning claim is adopted from its module name/docstring.

The initial measurements above remain historical measurements of the original repair commit. The JSON `integration` object records current-main qualification separately. The complete six-phase objective remains incomplete; no autonomy expansion is made.
