# Reuse engineering operation intent — 2026-10-31

## Scope

Base: `59a593ca9094ecd7c31b02f83b05c9d27636a181`. Upstream synthesis, static-soundness, polyglot and network-mediation work is integrated, not reimplemented. This change adds no registry rows, providers, terminal credit, policies or runtime model calls.

## Existing machinery reused

1. A shared `stated_git_operations` applies the existing operation grammar to the existing prose/value boundary. Quoted commit messages and paths cannot invent extra operations or repository authority. Actual values still bind from the original request.
2. Narrow unqualified repository reads (diff/status/history/current branch) reach the existing Git family. Deployment status, sorting history, branch metaphors and quoted payloads do not become repository requests.
3. A stated ordinary operation requires an operation-bearing declared contract before admission. A bisector's bindable source directory alone is not an authorship operation. Multiple eligible admissions still refuse. Explicit bisection is not silently downgraded to reading a log.
4. An undecidable stated Git plan returns the established fail-closed shape before primary execution. An executed verdict is never replaced.
5. Existing caller and source-change controls exposed three upstream regressions. A function named `rename` is data, not a rename imperative. The existing role-aware intent matcher already distinguishes `function add in file` from `make the function add a parameter`; removing a redundant broad exclusion restores that distinction. Existing strict assertions are unchanged.

## Actual results

- Initial 15 new controls on unchanged production code: **6 passed, 9 failed, 1.34 s**. Five additional negative/commit-message controls were added afterward; no baseline count is invented for those.
- Focused final routing, real Git adapter, caller and intent checks: **74 passed, 3.07 s**.
- Nine-module integrated run before repairing the three caller/source-obligation regressions: **174 passed, 3 failed, 43.31 s**.
- The same nine-module integrated run afterward: **177 passed, 6 warnings, 43.04 s**. Includes real public read operations, contract-bound repairs, caller lookup, cross-file workflows, and upstream synthesis/static/polyglot controls. No successful tool execution is substituted with a mock; spies wrap actual functions, including negative assertions that primary execution did not occur.

These timings are scoped test durations, not a controlled speedup benchmark. Avoiding primary execution after an authoritative refusal is asserted directly; no universal optimality follows.

## Adverse observations retained

`canonical/tests/test_declared_input_derivation_v1.py` cannot collect: its committed contents are JSON with `true` literals rather than Python test code. A four-module attempt reported **one collection error**. The file was neither hidden nor weakened nor replaced with a historical test loader; passing runs above explicitly have different scopes.

Correctly selecting the Git authorship operator does not complete missing target/line-range transport through the public contract. No authorship delivery claim is made. Broader compiler, production, resource and unfamiliar-repository qualifications remain open.

Model diagnostics, fresh signed referee, actual final head/base and merge outcome are recorded on this session's PR. The generated model is recompiled from the actual combined tree. This is producer-run sandbox evidence, not independent capability verification or terminal authority.


## Concurrent main integration

Main subsequently advanced to `09867fd76b3f658b3e19da81576e634b370aa912`, adding governing-clause and repair-flow improvements. These are retained. The short Git-read recognizer now feeds the upstream three-part family-hit contract; ordinary Git operation contracts cannot be bypassed by the upstream rival-phrase path. The newer governing-clause implementation supersedes this branch's interim narrow rename check.

Intermediate validation during the unresolved merge reported **70 passed, 8 failed, 7 subtests passed, 70.55 s**: seven caller-report checks exposed a widened source root, and a real Git diff could not execute against the unmerged index. An actual trace showed a single owned fixture's symbol query expanding to `canonical`, writing its report there and scanning unrelated code. This was not treated as passing caller qualification.

The root widening now applies only when the declared contract actually consumes test paths/argv; the existing src-layout repair discovery is retained, but an index-only query keeps the stated file's own directory. A new strict source-root regression is added. After completing the merge, focused validation passed **75/75 in 3.14 s** and public structured-contract validation passed **30/30 in 12.56 s**. The final integrated result and regenerated artifact are reported on PR #6446.
