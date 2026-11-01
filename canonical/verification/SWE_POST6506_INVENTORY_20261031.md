# Remaining hardcore software-engineering problems — post-PR6506 audit

**Measured tree:** `c4c74d74d5718299418b511c3a4feef9aff21ff5` (merged PR6506).  
**Date:** 2026-10-31. **Purpose:** assess correctness, reachability, engineering breadth, speed and production readiness—not PDF/document features.  
**Status:** producer observations, not independent certification. No implementation, commit, push or merge was performed for this audit. This is a prioritized inventory of what was found and what remains unproven, not an exhaustive proof that every other behavior is correct.

## Executive finding

The strongest remaining problem is **not merely that advanced requests are refused**. Some directly callable adapters report verification after introducing real semantic regressions or allowing source-tree data mutation. Those failures deserve attention before making more requests reach those adapters.

There are five distinct layers to the remaining work:

1. Semantic correctness and transaction/isolation boundaries.
2. Correct routing, input binding and answer acceptance for existing mechanisms.
3. Reliable restoration and identification of the actual execution substrate.
4. End-to-end advanced engineering coverage beyond bounded Python transformations.
5. Representative evidence of speed, scale, autonomy and production reliability.

Existing machinery is substantial. The evidence does **not** justify rebuilding everything, declaring everything absent, or claiming that all missing behavior is merely hidden routing.

## 1. Fresh measurements and their limits

| Instrument | Current observation | What it does not establish |
|---|---|---|
| Fixed 28-case SWE surface probe | **28/28** | Arbitrary task completion or semantic equivalence outside these fixtures |
| Advanced 49-request census | **4 served, 45 refused** | Four independently proven correct solutions; this instrument has no per-request semantic oracle |
| 54-case capability matrix | **21 REAL, 33 refused, 0 FALSE, 0 DAMAGE-labelled cases** | General soundness, complete filesystem isolation or exhaustive correctness |
| Nine selected test modules | **152 passed, 3 failed; 9.16 s** | Full-repository suite health |
| Additional process-mediation test | **1 failed; 10.29 s** | Exploitability or universal process-policy failure |
| New disposable-fixture semantic audit | **5 counterexamples observed** | Frequency in real projects or behavior of every higher-level route |

The advanced census's four served requests selected acceptance measurement, rename-symbol, extract-function and security-review adapters. Do not translate its `served` flag into a semantic proof. Several census prompts are underdetermined by their fixtures, so the 49 requests are a route/execution census rather than 49 validated ground-truth tasks.

The matrix has case-specific oracles, but its scopes are finite. Its damage logic does not provide a comprehensive deletion/new-file/external-write monitor. The advanced census likewise compares modifications to pre-existing fixture files, not every possible effect. Both probes also produced tracked runtime-state litter outside their task fixtures; that audit-produced litter was restored.

### Advanced census by class

| Class | Served / requests |
|---|---:|
| Polyglot | 0/7 |
| Build/dependencies | 0/5 |
| CI | 0/4 |
| Performance | 0/4 |
| Systems/concurrency | 0/3 |
| Tests | 1/6 |
| Debugging/explanations | 0/3 |
| Refactoring | 2/6 |
| Review | 1/3 |
| Git | 0/5 |
| Design/architecture | 0/3 |

These are outcomes for the chosen requests, not proofs of zero capability in those domains. For example, ordinary git-diff, mutation-score and performance-review matrix cases did succeed, and the fixed surface includes race repair and git bisect.

## 2. Highest priority: reproduced semantic and mutation failures

These observations were made through **public `run` entry points against the current tree**, in temporary projects. No runtime files, loaders, tool responses or test infrastructure were mocked or patched.

### P0-A. Optimization can change behavior and still report `verified: true`

Adapter: `software_repair_crossfile_choreograph_v1.py`. Mode: `quadratic_to_linear_set`.

**Counterexample 1 — supported input types are narrowed without a precondition:**

- Original nested duplicate comparison accepts `[[1], [1]]` and returns `True`.
- Accepted replacement uses set membership.
- The same input now raises `TypeError: unhashable type: 'list'`.
- Existing integer tests pass; the adapter returns `verified: true`.

**Counterexample 2 — the recognized loop shape is insufficient:**

```python
for i in range(len(xs) - 1):
    for j in [i + 1]:
        if xs[i] == xs[j]:
            return True
return False
```

This compares **adjacent** items only. The matcher accepts it as a general duplicate scan without proving the iteration domains/index relationships. On `[1, 2, 1]`, the original returns `False`; the accepted rewrite returns `True`, again with `verified: true`.

**Required boundary:** prove applicability, hash/equality/type assumptions and intended semantics, or refuse. A passing existing suite is not enough to label an arbitrary algorithm substitution behavior-preserving.

### P0-B. Dead-code pruning can delete an explicitly exported API

Same public adapter. Mode: `dead_code_and_import_pruning`.

- Fixture declares `__all__ = ["kept", "public_api"]`.
- `public_api(4)` returns `8` before the edit.
- Local tests exercise `kept`, not `public_api`.
- Pruning deletes `public_api` while leaving it named in `__all__`.
- The adapter returns `verified: true`.

The pruning pass collects syntactic references but does not use the export declaration to protect the function before deleting it. More generally, absence of in-repository references is not proof of deadness for libraries, plugins, entry points, reflection or downstream clients.

### P0-C. Test generation does not enforce a source-tree read-only transaction

Adapter: `python_tests_generate_scaffold.py`.

**Counterexample 4 — non-Python source data mutation is invisible:**

- A benign fixture function writes its sibling `state.txt` when called.
- Generated smoke test passes.
- The adapter returns `verified: true`, with one test passed.
- `state.txt` has changed. The source manifest hashes only `*.py` files.

**Counterexample 5 — Python-source mutation is detected but not undone:**

- The function instead overwrites sibling `state.py`.
- The adapter raises `SOURCE_TREE_MUTATED`.
- The overwritten file remains changed after refusal.

The repaired output/source ancestry checks correctly prevent overlapping generation directories; they do not sandbox executed subject code or roll back its effects. Detection after a write is not prevention or transactional restoration. Source-data, external filesystem, process, network and credential boundaries need explicit enforcement before unattended execution on untrusted projects.

## 3. Four existing failing test identities freshly reproduced

### P1-D. Fault-localizer ranking can prefer shared code over the fail-only suspect

`test_python_dynamic_fault_localizer_v1.py::T::test_shared_code_is_penalized_relative_to_fail_only`

The fail-only `buggy` function scores **1.0**; the shared function exercised by passing and failing tests scores **2.707106781187**. The promised ordering fails. This can direct repair effort to the wrong function even though application/test source scoping is now correct. The source-scope repair is not an explanation of this remaining scoring failure.

### P1-E. Caller artifacts still fail answer-scope acceptance

`test_swe_typed_plan_v1.py::EffectFamilyEnumerationTests::test_caller_family_passes_with_a_real_callers_of_artifact`

Observed refusal: `FAIL_CLOSED__ANSWER_SCOPE_UNPROVEN`. An existing callers artifact does not satisfy the typed answer-family acceptance contract. The matrix also refuses its find-callers case. This is a reachability/acceptance problem, not evidence that symbol indexing must be invented again.

### P1-F. Registry and test effect contracts disagree

`test_python_crossfile_edit_choreograph_v1.py::CrossfileEditRegistryContractTests::test_the_entry_is_a_verified_bound_capability`

The registry exposes the extra effect `python.source.crossfile_edit.choreograph.v1` beyond the test's expected `python.source.crossfile_edit.choreography`. Reconcile the intended vocabulary and its consumers. This is measured contract drift; the assertion alone does not demonstrate a broken edit at runtime.

### P1-G. One index-worker process site remains outside the mediation inventory

`test_hardcore_swe_capabilities_20261031_v1.py::HardcoreSWECapabilitiesTests::test_root3_process_universe_has_zero_unmediated_sites`

Inventory reports `concurrent.futures.ProcessPoolExecutor` in `_collect_index_parts`, `python_source_symbol_index.py:475`. Parallel indexing exists, but the process-policy/inventory closure is incomplete. The observation is a policy/inventory gap, not proof of arbitrary-command exploitation.

## 4. Request-to-execution reachability remains weak

### P1-H. Selection, admission and binding still lose advanced requests

The fresh 45 advanced refusals split into:

| Count | Failure family |
|---:|---|
| 10 | Route admission rejected |
| 10 | Live-controller execution/verification failure |
| 9 | Stated SWE effect unserved |
| 7 | Raw-goal compilation gap |
| 6 | Stated answer not provided |
| 1 | Worktree not a directory |
| 1 | No tests discovered |
| 1 | Invalid edit-plan input |

Do not add keyword aliases indiscriminately. Correct selection needs the language, project, requested effect, actual payload, source/test roles and output/answer obligations bound together. A row advertising a related word is not enough.

### P1-I. Failure explanations do not expose enough actionable inner cause

Ten advanced cases collapse to live-controller failure. The census does not distinguish their inner tool, input, subprocess, semantic-acceptance or rollback causes. Fail-closed behavior is preferable to false success, but it is not efficient recovery. Preserve stage-level structured diagnostics and artifact provenance without exposing secrets.

### P1-J. Executing an adapter and answering the question are different obligations

Six advanced requests end in `STATED_ANSWER_NOT_PROVIDED`. Diagnosis artifacts, taint reports, dead-code lists or bisect output are not automatically an explanation of the requested failure, performance result, race or regression. Answer acceptance needs task-specific evidence, not just an artifact hash or a completed call.

## 5. Advanced engineering breadth is not established end to end

The following are failed routes in these instruments or unestablished whole-task abilities—not declarations that no related module exists anywhere.

### P1-K. Polyglot parsing is not polyglot engineering

There is an existing shared tree-sitter SWE kernel, including non-Python language support. The advanced polyglot requests still serve **0/7**. Compiler/runtime availability, language-aware edits, project/build models and language-specific semantic tests must join the parsing substrate. C/C++ compilers exist here; Rust/Go/Java/TypeScript toolchains do not. Do not call the whole repository Python-only because the measured successful workflows are Python-heavy.

### P1-L. General feature implementation remains unestablished

The ordinary matrix refuses implement-issue, cross-file feature, CLI-flag, logging and retry requests. The advanced census refuses package/module splits and other architectural changes. Narrow AST rewrites and fixture-bound repairs do not establish open-ended requirement decomposition, multi-file API evolution, coordinated call-site changes, migration and end-to-end acceptance.

### P1-M. Build, package, dependency and CI workflows are not reliably connected

Advanced build **0/5**, CI **0/4**. Current requests include pyproject/Makefile work, dependency pinning/vendoring, CI workflow repair, cache/matrix configuration and flaky-test handling. These require actual file-format support, resolver/build execution, environment identity and validation of the resulting workflow—not sending YAML, SQL or native code to an unrelated Python adapter.

### P1-N. Systems and concurrency reasoning has only bounded evidence

Advanced systems **0/3**, despite the fixed surface's passing race-repair fixture. A successful lock-synthesis pattern does not establish deadlock freedom, lock ordering, cancellation safety, deterministic interleaving coverage, thread-pool behavior, native memory safety or distributed correctness. No current evidence here establishes those broader guarantees.

### P1-O. Git support is uneven across exact tasks and phrasings

Advanced git **0/5**, while an ordinary diff case and fixed-surface bisect succeed. Commit, branch, cherry-pick, history explanations and related workflows must not be substituted with history-search/bisect artifacts. Safe operation also needs dirty-worktree handling, explicit destructive-operation boundaries and task-specific final-state checks. The census is not a reason to claim git itself is unavailable.

### P1-P. Design and migration quality are not measured

Advanced design **0/3**. No current benchmark establishes architecture trade-off quality, compatibility-preserving migration, data/schema rollout, service-boundary design or the ability to implement and validate such plans. An ADR written to disk would not itself establish engineering correctness; the user's priority is working software.

## 6. Test, verification and security limitations

### P1-Q. Smoke generation is not a semantic test oracle

The scaffold explicitly promises smoke tests, not expected functional answers. An additional async-only fixture returned `verified: false` and zero passed tests; it did **not** reproduce a false async success and is retained as a separate control, not counted among the five counterexamples. Its fixture table is narrow; arbitrary state, complex inputs, async behavior and rich contracts are not established. Coverage and mutation tools already exist, but increasing either score alone is not proof that requirements are tested. Generated tests must not merely bless a candidate's behavior.

### P1-R. Verification labels need evidence levels

The new optimization/API counterexamples show that `verified: true` can mean a named test suite passed while important behavior regressed. Distinguish:

- artifact integrity;
- compile/import success;
- smoke execution;
- named regression-suite success;
- independent differential/property/contract checks;
- bounded proof under declared assumptions.

Existing CrossHair, Hypothesis, SMT and task-bound acceptance mechanisms are reuse candidates. Their presence does not establish that every mutating adapter invokes an appropriate independent oracle, that contracts exist, or that an inconclusive analysis is a proof. This audit did not execute CrossHair or claim a newly reproduced CrossHair defect.

### P1-S. Security scanning remains bounded

The integrated scope-aware qualified import aliases pass the selected controls. Remaining limits include assignment aliases, reflection, dynamic imports and function-local import inference. Diff-only findings are not whole-system assurance; no current audit establishes general taint, dependency CVE, secrets or business-logic security coverage.

The current review gate explicitly records an AST substitute and `complete: false` when Bandit is absent. Do **not** revive the old claim that this path still reports a complete Bandit scan. A local PASS is still not evidence that the unavailable external checker ran.

## 7. Substrate and performance

### P1-T. The substrate is not restored as a reliable execution precondition

At audit end, `python scripts/restore_substrate_v1.py --check` reports **2/10 required modules present**, all six declared binaries present, and `SUBSTRATE_INCOMPLETE`. The two installed modules are `tree_sitter` and `tree_sitter_languages`; pytest, Hypothesis, coverage, mypy, Ruff, Bandit, CrossHair and Z3 are missing from the default interpreter. `jsonschema` is also absent.

The separate test `.venv` was installed with pytest and pytest-subtests only. Do not confuse that with restoring runtime tools. Native tool gaps include rustc/cargo, Go, javac, tsc, Docker, gdb, perf, CMake and Ninja.

**Reuse:** `scripts/restore_substrate_v1.py` already installs the hashed kernel and unhashed review tools sequentially and checks the parser generation. The old mixed-hash installation defect is fixed. This audit ran `--check`, not a full restore. Counts such as 21 versus a historical 22 accepted matrix cases are environment-specific and not proof of regression.

### P1-U. Fast refusals and small warm-cache benchmarks do not prove fast engineering

- This advanced census: median **82 ms**, p90 **232 ms**, max **592 ms**; most requests refused.
- The matrix's producer measurement was median **98 ms**, p90 **616 ms**, max **1,529 ms**.
- A single fixed-surface whole-runtime index request took **21,410.7 ms**. This is an observed end-to-end sample, not a stable regression benchmark or an attribution of all time to parsing.
- Prior small synthetic warm-index results are not remeasured here and are not whole-project speed evidence.

Needed measurements: successful task latency and correctness together, cold/warm costs, repository-size scaling, dependency installation, subprocess startup, invalidation, multi-worker memory, p95/p99, and cost per correct end-to-end task.

### P2-V. Safe cache reuse still has deliberate limits

The new cache controls passed: unknown/forged persisted rows are rederived; trusted reuse depends on a bounded process-local exact-byte attestation cache. That protects correctness but does not provide durable cross-process trust, concurrent snapshot isolation or protection against malicious code already running in-process. These are future design/performance boundaries, not reasons to weaken the current provenance checks.

## 8. Repository and production evidence

### P2-W. Checked-in merge-conflict markers remain in `.gitignore`

The measured commit contains `<<<<<<< HEAD`, `=======`, and `>>>>>>> origin/main` at lines 39, 46 and 48. This is existing repository hygiene debt, not an audit-created conflict. It does not by itself invalidate Python execution or establish that other files are conflicted.

### P2-X. CI green is narrower than all laws green

PR6506's required checks passed before merge, but the selected current tests still reproduce four failure identities, and the new semantic audit exposes five counterexamples not guarded by those checks. Existing CI is evidence about its selected obligations, not a blanket capability certificate. Add targeted regressions for genuine failures without weakening floors or replacing the actual tree with historical copies.

### Unmeasured ambitions—not proven missing implementations

This audit does not establish the following claims either positively or negatively:

- sustained success on independent, held-out large-repository tasks;
- requirements clarification and stopping at the right uncertainty boundary;
- long-horizon plans that revise after real tool feedback without losing intent;
- safe restart/resume, cancellation and recovery across crashes;
- multi-agent coordination, conflict resolution and shared-worktree consistency;
- deployment, data migration, monitoring and rollback under production load;
- operating on adversarial repositories without credential, network or host exposure;
- cross-platform/Python-version behavior beyond this environment;
- universally optimal, fastest or smartest engineering.

These need representative external evaluation and explicit operational tests. It would be inaccurate to call them all solved by the existence of tools, or all absent because this census does not exercise them.

## 9. Reuse-first repair order

1. **Contain verified-but-wrong edits and uncontrolled source writes.** Tighten matcher applicability/export preservation, run risk-appropriate differential/property checks, and enforce real execution/rollback boundaries.
2. **Repair the four reproduced contract failures.** Localizer ranking, callers answer scope, registry vocabulary, process mediation. Preserve the passing scoped-source/cache/security controls.
3. **Restore and pin the execution substrate before capability judgments.** Use the existing restore path; record interpreter/tool versions and separate unavailable from failed.
4. **Connect existing mechanisms by task, not lexical similarity.** Reuse source indices, tree-sitter, typed plans, declared input roles, task-bound repair loops and acceptance artifacts. Preserve stage diagnostics and refuse unsupported effects honestly.
5. **Deliver representative full engineering loops.** Build/CI, polyglot, multi-file features, concurrency and migrations need real projects, executable acceptance and compatibility checks.
6. **Optimize measured successful work.** Profile cold indexing, tool starts, repeated parsing and scheduling; keep semantic correctness and provenance requirements intact.
7. **Evaluate production and autonomy claims independently.** Held-out tasks, representative scale, adverse conditions and independent execution—not self-authored success labels.

## 10. Evidence and reproduction

Persisted observations: `canonical/verification/SWE_POSTMERGE_AUDIT_20261031.json` contains the complete 49-request, 54-case and 28-case rows, selected-test outcomes, five semantic observations and final environment check. It is a producer audit record, not a signed receipt or independent verification.

Reproduce the new semantic observations from repository root:

```sh
PYTHONPATH=. .venv/bin/python canonical/verification/swe_postmerge_semantic_audit_20261031.py
```

This script creates and removes its own disposable projects under `.arena`, calls the actual public adapters, and prints observations. Its minimal fixture tests deliberately omit the independent witness inputs, demonstrating the acceptance gap. It never edits this checkout's application source.

Re-run the existing instruments:

```sh
python execution_guard/swe_advanced_probe_v1.py --floor 0 --json .arena/postmerge_advanced.json
python execution_guard/swe_capability_matrix_v1.py --json
python hardcore_swe_surface_probe_20261030.py --jobs 4 --floor 28 --json .arena/postmerge_surface.json
python scripts/restore_substrate_v1.py --check
```

The nine selected modules were `test_swe_safe_reuse_integration_v1.py`, `test_diagnosis_source_and_test_roles_v1.py`, `test_fault_localization_source_scope_v1.py`, `test_security_import_aliases_v1.py`, `test_python_dynamic_fault_localizer_v1.py`, `test_python_crossfile_edit_choreograph_v1.py`, `test_swe_typed_plan_v1.py`, `test_derivation_content_cache_v1.py`, and `test_the_index_cache_key_is_the_tree_not_the_request_v1.py`, all under `canonical/tests/`. The process test was run separately by its node ID above.

**Preserved repairs:** source-scoped localization, explicit application/test roles, resolved bidirectional scaffold ancestry, positional-only call rendering, exact-byte process-attested cache trust, and qualified security aliases passed the selected controls. They are not repeated as unresolved defects in this inventory.
