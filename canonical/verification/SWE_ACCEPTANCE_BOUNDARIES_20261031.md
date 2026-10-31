# SWE acceptance-boundary repairs — 2026-10-31

## Scope and reuse

This is a focused repair, not a claim that all advanced engineering gaps are closed.
No capability rows, terminal predicates, protected policies, or workflows are changed.
The final integrated base is `4b1baa2a57c1eac48658c101342fe5d0636c25a5`.

Existing mechanisms were inspected and reused rather than adding new providers:

- `python_test_guided_patch_search_v1`: byte-exact restoration and source-bytecode invalidation.
- `swe_task_artifacts_v1`: fresh destinations, atomic non-replacing report publication, and separation of artifact integrity from effect verification.
- `software_hardcore_swe_supercomposer_v1`: declaration availability is not completed workflow delivery.
- `software_repair_crossfile_choreograph_v1`: the candidate must remain unchanged during acceptance.
- Existing AST annotation interpretation in `opus55_sdk_schema_closure_v1` informed structural handling of Union, Literal, and Annotated; task annotations are never evaluated.

No external dependency was vendored, and no new research or repository was needed for these bounded defects. The observational synthesis/STUN algorithms already exist in Brain and were retained.

## Changes

### Source CEGIS

Every candidate trial restores original source bytes, including CRLF files, failures, runner exceptions, and timeouts. Trial code invalidates timestamp-based bytecode, so an equal-sized edit cannot silently execute the baseline's pyc. A successful candidate is promoted only when requested; report-publication failure also restores source. Baseline timeout stops without trying a candidate. Acceptance that modifies the candidate is rejected. Source-file symlinks cannot promote edits outside the declared source root.

This is a single-source promotion boundary, not a general filesystem transaction, process sandbox, concurrent-writer lock, or isolation claim. In-process evaluation of extracted source classes remains a separate review item.

### Literal annotation checks

The analyzer now uses AST structure and three-valued matching: valid, invalid, or unsupported. It handles primitive unions, Optional, Literal, Annotated, quoted annotations, and supported qualified forms without evaluating annotation code. Unknown aliases do not count as validated. Unsupported literal checks, empty analysis, and file-budget truncation cannot certify the entire requested scope. Reports explicitly identify bounded AST checks and do not claim semantic correctness.

This is not a replacement for a language compiler or complete type checker. Unresolved names and aliases remain unknown rather than being guessed.

### Final composition wrapper

Registry tokens and producer presence are reported as declarations only. Neither complete declarations nor a clean static preflight establishes workflow delivery. The wrapper reports `workflow_executed=False`, `verified=False`, and `output_verified=False`, while independently reporting artifact byte integrity. Existing output destinations are preserved.

## Measurements

All tests read the current working tree. No historical source substitution or test-harness patch was introduced.

- Initial new regression module, before source repairs: **21 failed, 6 passed, 1.74 s**. This also exposed stale-pyc behavior on successful equal-sized candidates.
- Final expanded focused regression module: **33 passed, 3.27 s**. Includes real subprocess acceptance runs, apply/no-apply controls, exact-byte rollback, real baseline/candidate timeouts, candidate mutation, source symlink refusal, and declaration-only reporting. Runner and report-publication exception tests use explicitly labeled unit-level fault injection; other acceptance runs execute real suites.
- Literal-union microbenchmark, five samples of 10,000 checks each: 0.057751, 0.056408, 0.055169, 0.054918, 0.055128 seconds; median **0.055169 s**. No comparative or universal speed claim follows from this small measurement.
- Broader initial integration run: **94 passed, 65 failed, 4 warnings, 39.47 s**.
- Broader run after merging main `4b1baa2a57` and installing the parser's declared substrate (`tree-sitter==0.20.4`, `tree-sitter-languages==1.10.2`): **99 passed, 65 failed, 4 warnings, 42.07 s**. This run included the first 31 focused controls; two additional focused controls were added and run afterwards. It is not an all-green or full-repository result.

The broader command covered the acceptance-boundary controls, hardcore SWE capabilities, task-bound cross-file workflow, Git intent reuse, family-effect filtering, stated report destinations, typed planning, declared input derivation, source/report separation, and upstream's stated-surface reachability test.

## Integration failures that remain open

Incoming main changed runtime modules beyond this repair's three-module source scope. The broader run exposed missing interfaces and disconnected previously landed routes, including:

- `python_source_symbol_index.build_index` absent while the cross-file workflow calls it.
- `declared_input_derivation_v1.stated_git_operations` absent while Git-intent controls require it.
- `swe_typed_plan_v1.build_plan` no longer accepting `compiled_context`.
- Lost caller/value-boundary and stated-output-preservation behavior.
- Interprocedural taint and complexity results disagreeing with their existing controls.
- Loose-object diff derivation and feature-route reachability controls failing.

These failures are not hidden, tests are not weakened, and missing APIs are not shimmed in test infrastructure. No end-to-end Git blame transport, general adaptive engineering controller, broad systems qualification, universal optimality, or fastest-engineer claim is made. Further integration repair must preserve both upstream's newer rules and the already-landed mechanisms rather than replacing whole modules blindly.

## Final focused and model checks

- Combined acceptance-boundary and unified-model regression modules: **93 passed, 905 subtests passed, 41.95 s**.
- Separate compiled-model verifier, seed `acceptance-boundaries-20261031`: **33/33 PASS**, all eight verification categories passed. Its own authority remains NONE; this is a sandbox measurement, not independent capability promotion.
- Repository integrity guard against integrated main: **17 rules, zero violations**.
- The compiled model was regenerated after this report update so its knowledge/source hashes describe the final tree. No descriptor counts were increased by this repair.

## Reproduction

```sh
python -m pytest -q canonical/tests/test_swe_acceptance_boundaries_20261031_v1.py
python execution_guard/repo_integrity_guard_v1.py --base origin/main
```

Scoped checks and compiled-model verification are measurements, not an independent capability promotion. Merge is permitted only after the required signed repository referee check succeeds on the exact proposed head.
