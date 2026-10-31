# Source-scoped Python fault localization — local integration evidence

Date: 2026-10-31. Base: `43676be3a788257eb70edfe36b27f470d6b33edf`.
Scope: existing dynamic localizer, regressions, action intent and officially
regenerated model projection. No new capability or runtime dependency.

## Failure and reused mechanisms

The real adapter ranked `.venv/.../_distutils_hack` as the application fault for
an assertion-only test that executes no declared application code. Its existing
`_app_paths` was used for one scoring heuristic, not to constrain collection or
ranking. Repository-local dependencies also consumed the trace-event cap.

Reuse:

* `python_source_symbol_index._py_files`: existing source enumeration with the
  shared tree-sitter substrate's generated/environment directory exclusions.
  The enumeration is stdlib-only; no parser wheel is imported for this work.
* `python_test_corpus_discovery_v1.is_test_file_name`: shared prefix/suffix test
  classification; explicitly stated tests are excluded even with arbitrary names.
* Existing `_brain_project_file` cached frame-path resolution and suite runner.
* Existing localizer application membership, spectrum scoring and repair callers.

The adapter computes canonical application membership once per run. Each child
receives the allowlist through stdin, avoiding command-line argument-size limits.
Only application files and the current stated test are collected. Irrelevant
frames cannot consume the cap. Synthetic nonpositive line numbers are ignored.
Ranking requires application membership, failing-run coverage, and a still-present
canonical file. Passing-only evidence stays diagnostic in the test traces, not
fault guidance. The existing score formula and ranking heuristic are unchanged.

This is evidence isolation, NOT a subprocess sandbox, general causal-debugging
proof, content-snapshot guarantee or write-confinement change. Dependencies outside
the declared source root are intentionally not application repair candidates.

## Failure-first controls and comparison

Tests execute actual fixture code in real child interpreters, without replacing
subprocess results, file loaders, tracing callbacks or test assertions.

The eleven new controls cover source/sibling-prefix separation, ignored environment
files, arbitrary stated-test names, suffix-named tests, application-free failure,
passing-only evidence, shared passing/failing coverage, noise exhausting the cap,
deleted application files, and deterministic positive guidance.

Same seven-module suite on the unchanged runtime: **10 failed, 42 passed** in
11.14 s. Patched runtime: **1 failed, 51 passed** in 10.75 s. For the baseline,
openly restored only our localizer-file patch in the working tree, executed the
unchanged tests, then reapplied it. No historical test loader or pin mechanism.
**Nine failure identities removed; none introduced.**

New controls plus the existing package-root/empty-localization suite:
**15 passed** in 1.79 s. The previously failing empty-localization control now
passes without modifying it. Neighbors include existing localizer, coupled repair,
provenance-guided repair, value-provenance and incoming placeholder-proof tests.

## Honest residual

`test_python_dynamic_fault_localizer_v1.py::T::test_shared_code_is_penalized_relative_to_fail_only`
fails on both baseline and patched runtime: the heuristic assigns `buggy` a score
of 1.0 and shared code 2.707106781187. This patch does not modify those weights,
weaken the assertion, or claim that source-scoped guidance proves root causality.
The neighboring suite is not all green. The wider advanced-SWE audit is not solved.

## Measured cost and footprint

Nine adapter calls per case, separate real subprocesses, median `perf_counter_ns`
duration. Parent module import is outside the timed region; source selection,
child tracing, scoring and report writing are inside. Synthetic project has a
small failing application and, for the noisy case, an unrelated dependency loop
of 10,000 iterations. Both versions retain the executed `buggy` body line.

| Case/measurement | Baseline | Patched |
|---|---:|---:|
| Noisy call median | 161.064 ms | 39.770 ms |
| Recorded noisy line events | 20,011 | 6 |
| Noisy report bytes | 1,466,354 | 3,224 |
| Clean call median | 36.847 ms | 41.368 ms |
| Clean line events | 5 | 4 |
| Clean report bytes | 3,225 | 2,874 |

Approximately **4.05x faster** on the noisy fixture and **99.78% smaller** report.
The clean control was approximately 4.52 ms slower in these sequential runs.
These are bounded sandbox observations, not randomized production comparisons,
confidence intervals, a global optimum or an unconditional speedup claim.

## Discovery and boundaries

Read CPython `Lib/trace.py` `_Ignore.names` through GitHub's contents API: cached
module/directory exclusion before collection is established standard machinery.
GitHub repository discovery surfaced `edwingl10/fault-localization` and
`sunbugs/coverage-sbfl`; these were metadata-only discovery hits, not qualified
replacements or imported code. Brain already owns the necessary pieces, so no
external analyzer is needed. No research-paper survey or exhaustive frontier claim.

No registry addition, ownership promotion, benchmark qualification, frozen-target
discharge or terminal credit. This is producer-run local engineering evidence,
not independent capability certification. Final model/goal-compiler and integrity
checks are recorded separately after this indexed report is finalized, so it does
not recursively invalidate its own model digest.
