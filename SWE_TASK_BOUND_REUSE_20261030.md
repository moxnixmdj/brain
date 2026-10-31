# Task-bound SWE reuse: implemented and measured

**Latest status:** the follow-up at the end adds normal-entry measured repair, public structured checks, and planning-stage latency measurements. Earlier API-only results below are the initial implementation snapshot.

## What was reused, not reinvented

| Existing implementation | Connection made |
|---|---|
| `concrete_execution_oracle.py` | Its actual docstring contract parser/evaluator now checks caller-supplied source in both sample adapters; no substitute demo. |
| `python_provenance_guided_coupled_repair_v1.py` | Remains the bounded real candidate search used by the measured controller. No new patch synthesizer. |
| `python_repair_measured_acceptance_controller_v1.py` | Now optionally checks contracts against the **realized repaired candidate**, before authorizing acceptance. |
| Existing candidate realization, repository measurement, objective acceptance | Retained and required; property results cannot override unresolved task acceptance. |
| Hypothesis 6.170.12, already pinned in the SWE kernel requirements | Now generates/shrinks real integer examples for the existing contract language, instead of a hardcoded nonnegative-result property or fake fallback. |

No runtime model service, new capability registration, ownership promotion, changed terminal truth, weakened test infrastructure, or protected-path edit was introduced. No paper search was needed for this slice: the reusable code was already in the repository.

## Runtime changes

### Concrete and Hypothesis adapters

- Require actual source or a repository-confined source path. Missing source no longer executes a built-in example.
- Honor actual `post:` expressions for a standalone unary function named `f`.
- Report the number of function calls actually completed. A single-value domain completes one generated check, not a fictional 50.
- Missing Hypothesis reports `UNAVAILABLE__HYPOTHESIS`, zero checks, and no successful verification.
- Invalid Python, missing/unevaluable contracts, exceptions, and observed violations cannot satisfy the caller's property.
- Separate check completion from satisfaction; a valid counterexample is reported but is not a passing contract.
- Execute candidate source in a child with a wall timeout; on POSIX, timeout cancellation targets its process group. The worker has bounded memory/output-file size where supported. Python stdout/stderr from the candidate is redirected away from the result protocol.
- Never overwrite an existing report or the named source. Hash the exact source and report bytes.

These child processes are **not an OS security sandbox**. This change does not authorize hostile code or claim to close the broader execution-security findings.

### Measured repair controller

An optional `contract_checks` list connects both adapters to the repaired candidate. Each check specifies a source file relative to `source_root`, plus optional integer bounds, example count, and timeout. Invalid paths/options fail before repair search.

The two input enumerators run concurrently. Acceptance requires both checks to complete, pass, use the candidate's exact source hash, and leave that source unchanged. The existing measured tests and objective acceptance must also pass. Requested checks that fail block acceptance even if the unit tests pass. Omitted checks are explicitly reported as **not executed**, not as successful property verification.

Accepted results now include the actual candidate diffs as well as realization/measurement data. Property observations are embedded in the final report; temporary report paths are not presented as persistent evidence files.

### Legacy CEGIS/Hypothesis repair wrapper

Replaced the unrelated demo calls with one dispatch to the real measured controller above. Positive bounded integer budget, explicit source root, task text, and candidate contract checks are required. Zero iterations cannot be successful. A budget is an upper bound on dispatches, not a request to repeat an identical bounded search unnecessarily.

The legacy identifiers remain for compatibility; they are not evidence of Z3 source synthesis or universal repair. The budget-only registry template now fails closed. **Natural-language routing or registry input binding for this richer wrapper has not been implemented or claimed.** At this initial stage, the new optional configuration and wrapper were exercised through their Python interfaces. The follow-up below connects optional checks to the measured controller through the normal public entry, but does not add registry binding for this wrapper.

## Minimal interface example

```python
from canonical.runtime.bound_capabilities import (
    software_repair_loop_cegis_hypothesis_v1 as repair,
)

result = repair.run({
    "source_root": "pkg",
    "test_paths": ["pkg/trace_fail.py", "pkg/trace_pass.py"],
    "test_argv": ["/path/to/python", "pkg/test_all.py"],
    "task_text": "tests_pass must be true.\npython_parse_ok must be true.",
    "contract_checks": [{
        "source_path": "m.py",
        "min_value": -100,
        "max_value": 100,
        "max_examples": 50,
    }],
    "budget": 1,
    "output_path": "new_repair_report.json",
}, "/path/to/repository")
```

`m.py` must contain a supported `f(x)` with a real docstring contract, for example `post: _ == (x <= 3)`. This interface does not infer arbitrary contracts or solve arbitrary issue semantics.

## Measurements

Environment: local Python 3.11, isolated `.venv`, pytest plus the already-pinned `hypothesis==6.170.12`. Packages were installed outside the tests. Tests execute the working tree without test-harness monkeypatches, historical files, fake tools, or assertion weakening.

### Changed-path and existing repair tests

```sh
.venv/bin/python -m pytest -q \
  canonical/tests/test_task_bound_repair_contracts_v1.py \
  canonical/tests/test_python_repair_measured_acceptance_controller_v1.py \
  canonical/tests/test_python_repair_semantic_acceptance_v9.py \
  canonical/tests/test_swe_typed_plan_v1.py --tb=short
```

**86 passed in 26.50 seconds**, including **45 new cases**.

Positive evidence: a fresh broken comparison function is repaired; actual measured tests pass; concrete and Hypothesis checks use the repaired candidate hash; the emitted diff, applied by the test, satisfies a separately written exhaustive predicate over 401 integers; original source/test bytes remain unchanged after the call.

Negative cases cover zero/invalid budget, missing task input, fake-demo avoidance, missing backend, missing/invalid/unevaluable contracts, real violations/exceptions, finite-domain counts, timeouts, path escape, existing-file preservation, invalid contract configuration, passing tests with a failing property, and semantic residuals that must continue to block acceptance.

### Pre-existing front-door failures retained

The four front-door/parity/consult/naming suites from the prior audit were rerun separately: **76 passed, 10 failed**. The ten failing test identities are unchanged from the prior audit. They were not weakened or declared fixed.

Across these disjoint selections: **162 passed, 10 failed**. This is not a full-repository suite measurement.

### Speed, honestly compared

Three fresh small-fixture runs per route, all accepted and source-restoring:

| Route | Runs (ms) | Median (ms) |
|---|---|---:|
| Existing measured controller, without added property checks | 812.93, 807.51, 853.61 | 812.93 |
| Task-bound wrapper, with concrete + Hypothesis candidate checks | 1025.67, 1086.36, 1126.96 | 1086.36 |

The additional checks cost about **273 ms** at the median on this fixture. This is added validation, **not a claimed speedup** over doing less work. Parallel sample checks and avoiding repeated unchanged searches reduce redundant work. No general latency or throughput conclusion follows from this small fixture.

## Limits and next connections

- These are local sandbox measurements, not independently produced capability credit.
- The two sample adapters share a contract evaluator. They do not count as two independent semantic implementations; `independent_semantic_oracle_credit` remains false.
- Finite samples do not prove absence of bugs. Supported scope is standalone unary integer functions and the existing docstring contract language.
- A failed property currently blocks the candidate; this change does not turn its witness into a new search constraint or implement general CEGIS feedback.
- Repository-wide routing, typed artifact composition, hardened confinement, calibrated costs, real-repository breadth, and the other audit findings remain separate work.
- Existing dynamic repair temporarily trials edits and restores source. This work does not claim concurrent same-tree searches are transactionally isolated from each other.

The engineering gain is a real connection from existing repair machinery to task-bound candidate verification, with observable outputs and explicit unsupported scope—not another declaration-only solver.

---

## Follow-up: normal-entry wiring and measured planning speed

The initial implementation above exposed task-bound checks through the controller's Python API. The follow-up now connects them to **`live_brain_route_admission_v1.solve`**, without adding a new capability or modifying the registry's verification claims.

### Root cause actually reproduced

The pre-existing `test_acceptance_clause_front_door_v1.py` ran **1 passed / 3 failed** before this follow-up. The plain request for a measured acceptance **repair** report selected `python.repository.acceptance.measure.v1`. That tool successfully measured the still-broken source and the front door reported success—even for cases where it should have performed repair and rejected an unmet objective.

The existing typed selector already chose `python.software.repair.measured_acceptance.v1` and the existing declared-input derivation already supplied its test argv/path. The selector was consulted only after primary execution failed. A measurement-only tool's successful execution therefore prevented correction.

### Changes made

1. For explicit SWE requests, compare the lexical route with the existing stated-effect vocabulary **before execution**. If they contradict, use the existing decisive typed plan; refuse if no decisive plan exists. Never replace an executed adapter's verdict with a different tool's result.
2. Reuse the primary compiled context within the same request. The corrected plan now receives its selected capability's own effects, prerequisites, capability list, and match evidence—not stale metadata from the measurement-only plan. No cross-request evidence cache was added.
3. Accept optional public `contract_checks` only on the measured-repair controller. Bind validated per-request literals into a copied executable template, leaving the shared registry unchanged. Unsupported routes and malformed checks fail before tool execution; fallback composition cannot discard them.
4. Bind normalized check specifications by SHA-256 in the emitted report. Re-open the report, verify its artifact hash and exact requested checks, and inspect completed checks, source hashes, and requested Hypothesis bounds. Omitted, substituted, or tampered checks cannot produce success.
5. Count preflight compilation/selection and final inspection in public `elapsed_ns`. Moving work earlier must not make reported latency artificially smaller.
6. Replace default-input detection's repeated full-tree AST searches with a parent map and ancestor traversal. Eleven differential tests compare exact evidence against the original detector, including actual repair adapters. The source is still re-read; no stale AST cache was introduced.

### Public interface

```python
from canonical.runtime.live_brain_route_admission_v1 import solve

result = solve({
    "task_id": "my-repair-task",
    "goal": (
        "Write a measured acceptance repair report to work/report.json "
        "for the source root work using the test path work/test_all.py "
        "where `tests_pass` must be true and `python_parse_ok` must be true"
    ),
    "contract_checks": [{
        "source_path": "m.py",  # relative to the bound source root
        "max_examples": 50,
        "min_value": -100,
        "max_value": 100,
    }],
})
```

The source/test tree must already exist under the repository and contain a supported contract. No caller-supplied private execution plan or pre-authored patch is needed. This is a bounded sentence/API corridor, not arbitrary natural-language or multi-language engineering.

The legacy budget-only CEGIS wrapper's registry binding remains unsupported. This public connection uses the **existing measured-repair capability**, not a new registration or an invented capability promotion.

### Focused validation

**215 passed, 10 failed, 4 warnings in 85.89 seconds** across 13 selected test files, including the final malformed-evidence hardening. The follow-up adds 35 cases (24 public-entry and 11 AST differential), including report-corruption cases for missing hashes and invalid (zero/boolean) check counts. Combined with the initial 45 cases, this session has added 80 tests; all 80 pass.

- The three reproduced acceptance-front-door failures now pass; that existing file is **4/4 passing** without edits to its assertions.
- The ten failures are the same previously reported route/parity/consult/naming tests; they were not weakened or declared fixed.
- Repository integrity guard: **17 rules, zero violations, PASS** against the session's starting commit.
- `git diff --check`: clean.
- Not a full-suite or independent-verifier measurement; no ownership, benchmark, or terminal credit is granted.

### Planning-stage timing

Ten warmed runs per mode on the same small fixture, after the AST traversal optimization:

| Typed plan construction | Median |
|---|---:|
| Recompiles the already-available primary context | 145.728 ms |
| Reuses that context within the request | 68.458 ms |

That is about **53% less time for this plan-construction stage**, not a 53% whole-agent speedup. Context creation is excluded from both stage timings because it has already happened in the primary path. Before the AST traversal change, a separate ten-run measurement gave 183.456 ms for the context-reusing stage; that sequential observation is not a controlled whole-system benchmark.

Remaining limits are unchanged: sampled unary integer contracts are not proofs; the two samplers share their semantic evaluator; the worker is not a hardened OS sandbox; property failures currently block rather than guide new synthesis constraints; and general routing still has the reported backlog.

---

## Follow-up: reuse the existing cross-file issue pipeline

### Discovery and implementation

The repository already contains a strict, symbol-bound natural-language edit parser (`python_issue_nl_parse_edit_intent`), an actual staged rename/move executor (`python_issue_to_pr_orchestrate`), and content-hashed tree manifests (`canonical_tree_attestation_v1`). The new connection reuses these implementations, not a new refactoring engine or external dependency.

`software_repair_crossfile_choreograph_v1.run` no longer credits imports as repair. It now requires exactly one explicit issue/task input and:

1. Binds supported rename/move issue text against a fresh symbol index, refusing ambiguity and unconsumed prose.
2. Executes the existing choreography in a fresh task-private copied workspace.
3. Checks actual summary/diff artifacts and the existing fixed-point result.
4. Checks the emitted diff against **all relevant staged file changes**, not just the adapter's changed-file claim. Selected tests cannot introduce unreported candidate edits.
5. Runs the full fixture pytest suite in addition to the underlying impact-selected tests. Completed, non-skipped tests are required; failure elsewhere in the suite blocks acceptance.
6. Checks that regression execution did not change the candidate, that original source content remains unchanged, and that the original issue/task input remains unchanged.
7. Embeds the diff, requested operations, test results, and source/candidate hashes in the final report. Scratch paths are not presented as persistent deliverables.

The source indexer's existing implementation was extracted into a no-write `build_index` helper; the existing `run` adapter serializes the same schema and retains its result fields. This avoids the natural-language parser's fixed probe filename in the original source. Tests compare the pure builder's full object with the original adapter output for identical roots.

Reports use same-directory temporary files and atomic no-replace hard-link publication. Existing reports survive, including a concurrent destination race. Concurrent cross-file tasks have separate index/candidate/report scratch paths.

### Explicit API

```python
from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1

result = software_repair_crossfile_choreograph_v1.run({
    "source_root": "work/src",
    "issue_path": "work/issue.json",
    "output_path": "work/reports/change.json",
    "timeout_s": 60,
}, repository_root)
```

Example `issue.json`:

```json
{"issue_id":"RENAME-1","title":"Rename helper to compute in pkg/core.py"}
```

Alternatively pass `task_path` containing explicitly specified `rename_symbol`/`move_symbol` operations, not both input modes. Paths in operations are relative to `source_root`. Original source is not promoted. An accepted diff can be reviewed and applied separately.

**Reachability limit:** the legacy registry template supplies only a source root/output and now refuses, rather than inventing a task. This richer cross-file API has not been wired into general normal-entry task binding. It is not arbitrary issue understanding, parameter refactoring, multi-language repair, or autonomous PR delivery.

### Two diagnostic false-success paths closed

- `software_patch_cegis_z3_v1` retains architecture-search results, but neither exact frontier exhaustion nor a successful component plan is now reported as an executed/proven source patch. `pass`, `verified`, and legacy `output_verified` remain false; artifact integrity and search completion have separate fields. **Z3 source-patch synthesis remains unimplemented in this adapter.**
- `software_hardcore_swe_supercomposer_v1` retains declaration-inspection results, but registry presence no longer reports successful software delivery. **A real full-stack workflow has not been implemented in this wrapper.**

No capability registrations, registry verification claims, governance receipts, or protected paths were changed. Other declaration-only wrappers were not silently credited or claimed fixed.

### Validation and timing

- **33 new tests pass in 7.32 seconds.** They execute the actual kernels and child pytest processes, including a separate application of the emitted diff with `git apply` and execution of the resulting tests. This is a local acceptance check, not independent capability qualification.
- Combined focused run over 20 files: **331 passed, 12 failed, 4 warnings in 101.24 seconds**. The previous ten route/parity/consult/naming failures remain. Two additionally exercised failures are exact registry-token assertions in the symbol-index and choreography suites: both assertion files and the registry are unchanged from the starting commit, and their expected token lists already disagree. No existing assertions were edited.
- Integrity guard: **17 rules, zero violations, PASS**. `git diff --check`: clean.
- Three complete rename-adapter runs: **715.201, 709.692, 755.738 ms**; median **715.201 ms**, each changing three fixture files and running both selected and full regression checks. This measures useful work on a tiny fixture; it is not a speedup comparison with the old import-only no-op or evidence of large-repository latency.

### Remaining execution limits

Content hashes detect source/input/candidate drift; they do not confine hostile tests or roll back arbitrary external writes. The existing subprocess execution and copied workspace are not a hardened sandbox. Timeouts are per subprocess, not one total-task deadline; output capture is not a streaming quota. Supported inputs are bounded rename/move tasks, and unsupported prose is refused rather than interpreted. No formal-proof or universal optimality claim is made.

---

## Follow-up: cross-file workflow connected to normal entry

The previous section's explicit-API reachability limitation is now resolved for a **bounded, losslessly parsed staged-report request**. This is not general issue understanding or source promotion.

### Normal request

```python
from canonical.runtime.live_brain_route_admission_v1 import solve

result = solve({
    "task_id": "cross-file-rename",
    "goal": (
        "Write a cross-file repair report to work/out/report.json "
        "for the source root work/src using the issue path work/issue.json"
    ),
})
```

The issue file contains an identifier and supported rename/move instructions, for example:

```json
{"issue_id":"RENAME-1","title":"Rename helper to compute in pkg/core.py"}
```

`Create` is also supported. The alternative `using the task path work/task.json` accepts explicit `{ "issue_id": ..., "edits": [...] }` tasks. Prose fields beside structured edit operations are refused in this normal-entry corridor rather than silently ignored; use issue mode for supported natural-language instructions. Unknown requirements appended to the routing sentence are refused before execution. An issue's unsupported prose also prevents acceptance.

### Existing mechanisms reused

- The real registry/compiler still selects the capability. No caller-supplied capability ID or private execution plan is needed.
- The existing role-aware binder binds source, issue/task, and output paths. Only this request's copied action template gains the missing input and preflight binding; the shared registry remains unchanged.
- Source-tree, input-file, and exact-goal hashes bind execution to preflight. Changed inputs refuse before adapter side effects.
- The existing source index, issue parser, choreography planner/apply functions, and staged orchestrator still perform the edits.
- The existing raw-goal trace acceptance mechanism now has a scoped cross-file re-inspector. Fallback composition cannot discard this workflow's required inputs or replace its verdict.

### Acceptance is reconstructed, not taken from success flags

The producer now includes per-file patches/preimage/candidate hashes and a content-only candidate digest, excluding its named transient stage artifacts.

The re-inspector:

1. Checks the real report bytes and execution fingerprint, request binding, input/source preimages, patch ledger, and diff digest.
2. Re-binds actual issue contents, preserving refusals and checking the exact requested edit operations.
3. Applies the emitted diff with the existing `git apply` tool to a separate source copy and hashes its actual content.
4. Reconstructs the exact requested transformation with the existing edit kernels, without running their tests. This rejects a self-consistently hashed forged patch that also changes function behavior or weakens test assertions.
5. Rechecks the existing operation fixed point and runs the full pytest suite in another process. Nonzero completed tests and matching counts/outcomes are required.
6. Rejects candidate mutation during replay or original source/input drift.

On the positive fixture, normal entry reports both `crossfile_acceptance_complete: true` and `semantic_acceptance_complete: true`, with all three raw-goal obligations accounted for. These fields cover this bounded task only. Terminal credit remains zero and independent semantic-oracle credit remains false; the parser and transformation kernels are shared, and no independent capability qualification is claimed.

### Final validation

- **38 new normal-entry/reinspection cases** pass. Together with the earlier 33 cross-file cases, the cross-file test pair is **71 passing**.
- Normal cross-file entry + existing public contract checks + generic trace acceptance: **84 passed, 2 subtests passed in 45.65 seconds**.
- Final combined selection over 22 files: **391 passed, 12 failed, 4 warnings, 2 subtests passed in 129.98 seconds**. The twelve failures are the same ten original route/parity/consult/naming failures and two unchanged registry-token assertion mismatches reported above. This is not a full-suite run.
- A combined run exposed one additional route-dependent refusal-code mismatch in our earlier structured-contract test. Single-test execution passed, but another lexical selection path returned `STATED_SWE_EFFECT_UNSERVED`. Runtime error precedence was corrected to consistently report unbound structured obligations. The test was not weakened; the final combined run no longer has this extra failure.
- Integrity guard after the functional changes: **17 rules, zero violations, PASS**. Whitespace check: clean. Test-generated experience/JIT state was cleaned after execution, not substituted into the test harness.

Positive tests include normal issue/task requests, move-to-new-module, preserved original source, unchanged shared registry, request timing, and exact obligation accounting. Negative tests include unconsumed requirements, malformed/unsupported inputs, existing reports, preflight source/input drift, failed regressions, conflicting structured checks, substituted edits, forged patch/source/test evidence, and post-execution requirement changes. A replay-sensitive real test passes the producer's selected/full runs but fails the separate replay; normal entry correctly rejects despite producer success.

### End-to-end fixture timing

Three complete normal-entry runs: **1210.713, 1069.299, 1115.422 ms**; median **1115.422 ms**. Each includes compilation/binding, staged edits, selected/full tests, diff reconstruction, exact-transformation checking, and separate full-suite replay on a three-changed-file fixture. This is not a speedup over the earlier API-only measurement, which performed less verification, nor a claim about large-repository or whole-agent latency.

Remaining limits include narrow rename/move grammar, fixture rather than unfamiliar-repository qualification, shared semantic machinery, no hardened hostile-code sandbox, per-process rather than total-task deadlines, non-streaming output capture, and no automatic promotion of source changes.


## Follow-up: confined external-repository exercise

See `SWE_CONFINED_REPOSITORY_EXERCISE_20261030.md` for the subsequent opt-in namespace entry, syscall-chroot portability fix, multiline rename-import fix, and pinned Boltons run (621 baseline/full/replay tests, 58 selected tests, final 18,791.042 ms). Its expanded regression selection measured 437 passed / 13 failed; the additional failure is an unchanged impact-selector registry expectation newly included in that selection. Ordinary `solve()` remains unconfined unless invoked through the explicit confined entry. This adds local exercise evidence, not independent capability credit.
