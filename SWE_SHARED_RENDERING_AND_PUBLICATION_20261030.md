# Shared repair rendering and safe report publication

2026-10-30. Local development measurements on the current working tree. No capability admission, independent-verifier credit, promotion, commit or push.

## Reuse decisions

Inspected existing specialist search, exact-tree/input checks, report publication, write authority, dependency-cone cache and receipt-bound Pareto scheduler. Two directly applicable mechanisms were already implemented:

1. The coupled repair engine already rendered mutations from parsed source spans and deep-copied target subtrees.
2. `swe_task_artifacts_v1.py` already provided atomic no-replace report publication using a same-directory temporary file, fsync and hard-link publication.

Reused these mechanisms rather than creating another repair engine, cache or publisher. The proof cache requires dependency completeness, and the scheduler requires receipt-bound metrics. This work does not fabricate those prerequisites or automatically treat their existence as qualified repair scheduling.

No external library or paper was necessary for these particular fixes. This is not a claim that all remaining engineering problems are solved or optimally scheduled.

## Implementation

### Shared request-local renderer

Extracted the coupled engine's existing replacement-span primitive into `python_test_guided_patch_search_v1.py` and connected a request-local `_CandidateRenderer` to:

- standalone test-guided search;
- each iterative file/round search;
- coupled pools, and therefore their provenance-guided callers.

Each file version is parsed/indexed once for its search batch. UTF-8 byte offsets use a prefix-offset table instead of resumming preceding lines for every edit. Replacers receive deep-copied subtrees so they cannot mutate the shared AST. Candidate bytes, descriptors, order, no-op behavior and limits are preserved. One-off compatibility rendering still avoids constructing a complete index unnecessarily.

Only immutable syntax-derived work is reused. There is **no test-result cache**, baseline cache, skipped candidate execution, or removed fresh acceptance/replay step. A changed file/round constructs a new index; there is no persistent cross-request syntax cache.

### Measured-controller output safety

Before this change, direct measured repair wrote its final report using `Path.write_text`, even when the destination contained caller-owned bytes. Two new real-execution tests reproduced that behavior before the fix: both guided and iterative→guided calls completed without the expected refusal.

The measured controller now:

- checks for a fresh report destination before any oracle execution;
- uses the existing atomic no-replace publisher at the end;
- refuses when another process creates the destination after preflight;
- preserves source restoration and scratch cleanup if publication refuses;
- keeps output hashes tied to the exact published bytes;
- reports artifact integrity separately from task acceptance, preserving the controller's legacy `output_verified` meaning without turning an intact failed report into a successful task.

The shared `fresh_output()` also rejects a pre-existing dangling destination symlink instead of resolving it into a different report filename.

**API behavior change:** measured repair now requires a fresh output path. Callers that intentionally overwrote a previous report must choose a new destination. The apply-verified adapter and all other legacy writers have not been universally converted by this change.

This is report publication safety, not a filesystem sandbox, arbitrary workspace transaction, or protection against a malicious process changing parent directories. The original intermittent public-entry report-preservation failure's root cause remains unresolved; this deterministic direct-controller defect is not presented as proof of that root cause.

## Before/after measurements

Python 3.11.2, local venv. Before measurements ran the then-current source **before editing**; after measurements ran the updated source. Three repetitions each, sequential benchmark, no historical module substitution or test-harness patching.

Fixture: an authored 600-function Python file, not a held-out upstream project. Render stage generates the first 128 mutations using the same literals. Real search runs one bounded iterative round with sixteen candidate trials and an actual unittest subprocess oracle. Its deliberately late target is not repaired in that bound; both versions truthfully report ordinary no-progress exhaustion and restore the original bytes.

| Measurement | Before samples (ms) | After samples (ms) | Before median | After median | Reduction |
|---|---|---|---:|---:|---:|
| 128-candidate rendering stage | 914.957, 922.286, 916.162 | 17.870, 19.528, 18.510 | 916.162 ms | 18.510 ms | 97.98% |
| Real bounded iterative search | 996.282, 918.062, 908.780 | 786.839, 795.265, 767.152 | 918.062 ms | 786.839 ms | 14.29% |

Every render sequence has the same combined descriptor/candidate hash:

`06d4ffffdd441390793c2f3f77cb75f61e7d418f0198783fbb11315fd50139d5`

Every real search executes **17 test commands**: one baseline and sixteen trials. Trial counts, status and source restoration are unchanged. The 97.98% number is **render-stage only**; it is not overall software-engineering speed or successful repair throughput. The 14.29% result is for this bounded unsuccessful search, not a successful large-repository repair benchmark.

Reproducer for the current implementation:

```sh
.venv/bin/python -m canonical.experiments.benchmark_candidate_rendering_reuse_v1
```

It prints JSON and removes its temporary projects. A separate rerun of this checked-in reproducer gave 17.450 ms render median and 748.377 ms bounded-search median, the same sequence hash, and 17 real test executions in each repetition. Those later values are not substituted into the paired before/after table.

## Tests

Added 18 current-tree cases:

- `test_shared_candidate_renderer_v1.py`: 12 cases covering independent parse-per-edit differential comparison, UTF-8/emoji, CRLF, multiline expressions, async/nested code, absent spans, no-ops, mutating-replacer isolation, source-version changes, and real source-parse/test-execution counts for standalone and iterative search.
- `test_measured_repair_publication_v1.py`: 6 cases covering both strategies' pre-existing report refusal, both strategies' post-preflight collision refusal, dangling symlink refusal and successful exact-hash publication with fresh winner replays.

Validation:

- early existing renderer/search/reuse regressions: **43 passed in 10.55 s**;
- new and existing focused renderer/publication/search selection: **61 passed in 12.63 s**;
- final 12-module core selection, including real namespace qualification and fresh repair replays: **150 passed in 98.73 s**;
- adjacent 11-module selection: **175 passed, 1 failed in 56.71 s**. Persistent failure: `test_python_repair_apply_verified_v1.py::RepairApplyVerifiedTests::test_missing_test_paths_is_refused_rather_than_guessed`, which expects refusal while the unchanged apply adapter intentionally discovers tests. No assertion was weakened to hide this conflict;
- the earlier intermittent public-entry preservation test passed in this adjacent selection. Its root cause is not claimed fixed.

The core and adjacent selections were run concurrently in separate pytest processes; their timings are regression-run observations, not the sequential performance benchmark above.

Integrity guard against base `c79a8f544fe47b1d7250b1c64889b958237db4f3`: **17 rules, 0 violations, PASS**. `git diff --check`: clean. No full-suite or CI-green claim.

Prior integration: [measured iterative→guided portfolio](SWE_MEASURED_REPAIR_PORTFOLIO_20261030.md). Its timings are separate historical measurements, not reruns of this cycle.
