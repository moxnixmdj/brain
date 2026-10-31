# Hardcore software-engineering audit — 2026-10-29

## Executive judgment

Brain is not yet demonstrated to be an advanced autonomous software engineer. The main obstacles are **task-grounded correctness, real synthesis depth, safe execution, reliable routing, connected composition, and honest measurement** — not PDF/document features or the number of capability IDs.

There are real mechanisms worth retaining: test-guided AST repair, source indexing, cross-file edit machinery, typed admission, and independent filesystem checks. But some impressive capability descriptions advertise substantially more than their adapters implement. Connecting declarations cannot substitute for implementing those missing behaviors.

This is a bounded source audit plus focused execution, not a claim to have discovered every defect in the repository. Findings below distinguish **reproduced**, **source-confirmed**, and **qualification gaps**. Existing October 27–28 audit documents were retrieval hints, not assumed current facts. No production source or governance policy was changed.

## Scope and measurements

Checkout: `c79a8f544fe47b1d7250b1c64889b958237db4f3`, session branch `arena/4b31f8b6-brain`.

Current bound registry (`canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json`):

| Measurement | Observed |
|---|---:|
| Bound capability rows | 125 |
| Rows with `python.`, `code.`, or `software.` prefixes | 62 |
| Distinct provided tokens | 187 |
| Provided tokens consumed by no declared requirement | 86 |
| Required tokens without a declared provider | 24 |
| Rows with empty requirements | 41 |
| SWE-prefix rows with `channel_schema` | 0 |
| Declared costs | 107 rows cost 1; 18 rows cost 2 |
| True-capability ledger rows | 9; none qualifies an end-to-end coding capability |
| Workflow files referencing the pinned SWE kernel requirements filename | 0 |

These graph counts concern declarations. An unused token is not inherently a bug: some outputs are terminal, and some missing inputs are supplied by the environment. The defect is assuming that a large registry demonstrates a connected, executable engineering workflow.

### Focused tests

Installed pytest into an isolated `.venv`; no test infrastructure was patched.

```sh
.venv/bin/python -m pytest -q \
  canonical/tests/test_swe_typed_plan_v1.py \
  canonical/tests/test_live_brain_route_admission_v1.py \
  canonical/tests/test_front_door_selection_parity_v1.py \
  canonical/tests/test_live_route_memory_consult_v1.py \
  canonical/tests/test_capability_naming_rule_v1.py --tb=short
```

**Result: 93 passed, 10 failed, 4 warnings, 52.92 seconds.** All 17 typed-SWE tests passed. This is not a full-suite result. An earlier unittest invocation ran only the unittest-style cases; it did not discover the pytest-style functions, so it is not the combined suite verdict.

Failures include selection-count drift, cross-entry disagreement, changed failure/status contracts, failure to attempt learning for a real executable, and selecting a repository acceptance capability for a request naming no capability. Some are stale assertions or environment-sensitive; they must be triaged rather than all described as runtime regressions.

## P0 — correctness and trust defects

### 1. Zero-work repair reports success — reproduced

`canonical/runtime/bound_capabilities/software_repair_loop_cegis_hypothesis_v1.py:20–36`

Calling `run({"budget": 0, ...}, temporary_root)` returns `verified: true`, `output_verified: true`, and `iterations: 0`. The artifact is also verified because `all(...)` over an empty list is true. The return object unconditionally reports success even independently of the artifact predicate.

**Needed:** reject invalid/nonpositive budgets; use an explicit task-success predicate requiring actual work and independently observed acceptance.

### 2. The repair loop does not operate on the user's repair task — source-confirmed

The same loop calls four adapters with only fixed output paths. It passes no user source, failing tests, repair specification, or candidate patch. No discovered counterexample is fed into the next iteration. Its per-round predicate accepts *any* boolean success in a round, not all required obligations. The break condition ignores choreography.

**Needed:** a real loop over the same task and candidate state: reproduce → localize → synthesize → apply in isolation → verify → feed counterexample back → retry or stop with an explicit unresolved result.

### 3. Hypothesis fallback fabricates the measurement count — reproduced

`canonical/runtime/bound_capabilities/evidence_oracle_hypothesis_v1.py:49–111`

With Hypothesis absent, even syntactically invalid source produced `checked: 13`, no violations, and `verified: true`. The fallback does not execute 13 samples; it inspects whether the source contains `return x -`.

**Needed:** missing dependency/error must report unavailable/error and zero completed checks, never a successful substitute measurement.

### 4. Property checking does not implement the stated contract — source-confirmed

The same adapter only looks for a function named `f`, a docstring containing `post`, and tests `r >= 0` over integers from -100 to 100. It does not compile arbitrary postconditions. A no-postcondition path assigns 13 checks without executing them. Source is executed with `exec` in the orchestrator process when Hypothesis is available.

**Needed:** typed function/argument/contract inputs; explicit supported contract language; real counts; isolated, bounded execution; distinguish finding a violation from proving a property.

### 5. The CEGIS/Z3 patch adapter is not a code-patch synthesizer — reproduced and source-confirmed

`canonical/runtime/bound_capabilities/software_patch_cegis_z3_v1.py:37–74`

Default execution returned `verified: true` while its embedded result said `pass: false`, `NEW_PRIMITIVE_REQUIRED`, and listed missing effects. It emits no repaired source or patch. It invokes a bounded component-architecture enumerator, not Z3-based source synthesis. Neither the adapter nor that enumerator performs the advertised CrossHair/concrete verification loop.

Exhausting a declared frontier can be a correct *diagnostic*. It is not evidence that a software patch was produced. These outcomes need different result types and effects.

### 6. Cross-file repair verifies imports, not a cross-file repair — reproduced

`canonical/runtime/bound_capabilities/software_repair_crossfile_choreograph_v1.py`

A nonexistent `source_root` still returns `choreography_verified: true`. The adapter imports three kernels and writes availability/verification booleans; it never invokes them to produce or validate edits.

**Needed:** bind actual edits, execute the real choreography, verify changed sites and imports, and test the resulting tree. Preserve the real underlying kernels rather than crediting this wrapper as their execution.

### 7. “Full-stack SWE” composition is registry introspection — reproduced

`canonical/runtime/bound_capabilities/software_hardcore_swe_supercomposer_v1.py`

In a temporary root containing only the registry JSON, this adapter returns `verified: true`. It checks whether tokens and capability IDs are declared. It does not run the producers, build software, repair code, run tests, or land a PR.

Twenty-two registered adapters are at most 34 lines, including many similar fusion/supercomposer wrappers. Short length alone is not a defect; the inspected implementations establish the problem, not their size.

**Needed:** separate `DECLARATIONS_RESOLVE` from `WORKFLOW_EXECUTED` and `TASK_ACCEPTED`. Audit each wrapper's claimed effect.

### 8. Generic verification flags have incompatible meanings — source-confirmed

Across these adapters, `verified` can mean a report was written, a violation was found, no contract was parsed, a component search exhausted its frontier, imports succeeded, or the requested task succeeded. Registry expectations frequently accept `output_verified == true`.

**Needed:** distinct fields/types for execution completion, artifact integrity, contract outcome, test outcome, unresolved scope, and task acceptance. Producer flags must not independently grant capability credit.

### 9. Patch acceptance checks applicability without executing the patched task — source-confirmed

`canonical/runtime/live_brain_route_admission_v1.py:1344–1412`, `_statement_patch_authority`.

A stated report can satisfy this local gate when its diff applies and changes the named source. This function does not run the promised tests on the patched copy. Other gates may reject a particular run; this is not proof that every bad patch reaches an overall PASS.

**Needed:** acceptance on the exact patched tree and exact intended test/specification, with immutable original tests and relevant regression coverage.

### 10. Write safety is not a uniform pre-execution transaction — source-confirmed; older destruction not reproduced

The live entry observes selected paths and applies post-execution checks. `_close_observations` changes a PASS into a refusal; it does not restore original bytes. There is composed-chain cleanup, but that is not a universal transaction for arbitrary adapter writes.

The October 27 audit reported deletion of a source file by a rename request. A fresh equivalent probe in this checkout **did not delete the source**; it incorrectly chose a document converter and failed execution. Do not present the older destructive example as freshly reproduced.

**Needed:** copy-on-write task workspace; explicit read/write/delete authority; validated diff; atomic promotion; recovery after crash or refusal; protection for pre-existing uncommitted work.

### 11. Subprocess cwd and output-path checks are not sandboxing — source-confirmed

`canonical/runtime/bound_capabilities/cli_command.py:10–29` confines the declared report path, but executes arbitrary supplied argv with the ambient process privileges/environment. Argument-list execution avoids shell interpolation, not filesystem access, credentials access, child-process escape, or resource exhaustion. It captures the entire output before truncating returned text.

**Needed:** enforceable process/filesystem/network isolation, secret stripping, process-group cancellation, memory/CPU/output quotas, and explicit authority for external side effects. Audit the actual launch path; do not assume a separate mediation module necessarily covers every adapter or in-process `exec`.

## P1 — understanding, planning, and capability depth

### 12. Natural requests still select unrelated tools — reproduced

A fresh parameter-rename sentence selected `document.convert.markdown_pdf.pandoc_weasyprint` and ended `FAIL__LIVE_CONTROLLER_EXECUTION`, leaving the source unchanged. The focused compile tests observed 21/23 compiled and 19/23 expected-first selections, not their asserted 23/23 and 22/23.

**Needed:** task-relevant input binding and typed effects before execution; route across paraphrases, repository locations, and realistic issue descriptions. Rejecting a wrong route is necessary but does not solve the request.

### 13. Typed recovery is real but narrow — source-confirmed and tested

`swe_typed_plan_v1.py` adds useful typed binding and the caller-finding route; its 17 tests pass. Its explicit hidden-effect-family table currently contains only caller-finding. `_effect_consistent` still compares lexical effect words with substrings of capability IDs.

**Needed:** semantic contracts independent of display names; resolve ambiguity by collecting evidence or asking a focused question rather than silently guessing. Do not infer general engineering competence from the tested corridor.

### 14. Composition lacks SWE artifact contracts — measured

None of the 62 SWE-prefix registry entries has `channel_schema`. Many tokens are disconnected, and the composer has only a small explicitly verified-emission bridge table, not universal automatic integration.

**Needed:** schemas for source snapshots, symbol graphs, diagnostics, candidate patches, test selections, test results, and acceptance; bind actual values and artifact provenance across edges. Graph reachability alone is insufficient.

### 15. The generic planner is not an adaptive engineering controller — source-confirmed

`capability_planner.py` performs shortest-path search over accumulating fact sets. This is useful for monotone precondition/effect composition but does not itself represent arbitrary edit/retest loops, invalidation after changes, conditional experiments, or concurrent conflicting writes. Specialist loops exist, so this is a limitation of the generic planner, not a claim that no loop exists anywhere.

**Needed:** hierarchical task state, explicit failure transitions, invalidation, bounded retries, evidence-driven replanning, and safe parallelism.

### 16. General code generation is not demonstrated by template selection — source-confirmed

`program_synthesis_v1.py` selects from fixed file-format program templates. `python.patch.search.test_guided.ast.v1` honestly declares deterministic single-node AST mutations/literal substitutions and its incompleteness. The component enumerator is a different, bounded synthesis problem.

**Needed:** task-to-specification mechanisms, richer typed code representations and synthesis grammars, multi-edit search, library/API grounding, and demonstrated transfer to unseen repository changes. Wiring existing modules cannot manufacture these capabilities.

### 17. Parsing multiple languages is not engineering multiple languages — qualification gap

Tree-sitter parsing/indexing capabilities are now registered; earlier claims of zero multi-language parsing are stale. That does not establish compiler/type-system integration, safe refactoring, debugging, or correct patch generation for TypeScript, Rust, Go, Java, or C++.

**Needed:** per-language parse → resolve/typecheck → edit → build → test workflows, qualified on unfamiliar repositories.

### 18. Issue-to-PR requires edits already specified — source-confirmed

`python_issue_to_pr_orchestrate.py` documents task JSON containing edit operations and supports specified rename/move operations. This is valuable choreography, not general issue understanding and solution design. Its worktree is a byte-copy, not automatically a complete Git worktree/environment abstraction.

**Needed:** derive and validate the change plan from requirements, then reuse the real choreography and PR machinery.

### 19. Advanced tool surfaces need end-to-end qualification — qualification gap

Generic shell execution is not a proven autonomous Git debugger, build engineer, or SRE. The bound registry does not demonstrate complete goal-driven workflows for history/blame/bisect, interactive debugger control, native profiling, dependency conflicts, or reproducible multi-service environments.

**Needed:** task-grounded workflows using existing tools, rather than adding impressive IDs. Test rollback, dirty trees, merge conflicts, flaky builds, missing dependencies, and interrupted runs.

## P2 — speed, consistency, and development infrastructure

### 20. The cost model cannot justify “fastest” — measured

All 125 registry costs are 1 or 2. This cannot represent measured wall time, setup cost, memory, success probability, or recovery cost.

**Needed:** per-stage traces and cold/warm distributions; optimize time to an independently accepted change, not planner speed or action count in isolation.

### 21. Duplicate work and broad invalidation — source-confirmed

The typed retry re-enters `_solve_body` after a failed primary route. The unified-model compiler indexes root Markdown and broad runtime/governance sources, coupling changes to artifact integrity and rebuilds.

**Needed:** cache pure plans and parsed/indexed inputs by relevant content hashes; incrementally invalidate only dependencies; retain all safety checks. Never cache a success without revalidating its source/test/environment provenance.

### 22. Fixed intermediate/report paths invite collisions — source-confirmed

The repair loop uses `canonical/tmp_loop_*_<round>.json`; typed output relocation uses `typed_swe_report.json` in the source directory. These are not fresh run identities and may collide across tasks or overwrite prior reports. No collision was stress-tested here.

**Needed:** per-task isolated namespaces, atomic writes, immutable artifact identities, and concurrency tests.

### 23. Observation coverage is bounded and metadata-based — source-confirmed

`observe_world` skips walking subtrees over its file-count limit and stores size/mtime snapshots. This is an observation aid, not an authoritative content-integrity proof. Parsing only Python also cannot establish general source validity.

**Needed:** content-addressed changed-file manifests and write mediation; reject missing required observations rather than treating unobserved state as safe. Measure large-repository overhead.

### 24. The focused regression suite is red — reproduced

Ten of 103 selected tests fail. Some pin historical counts/status strings instead of durable behavioral requirements. Fixing the number in a test is appropriate only after explaining the behavioral change and retaining independent acceptance checks.

**Needed:** classify each failure as environment, stale assertion, or runtime defect; keep a reproducible current baseline; block real regressions without hiding known failures.

### 25. The measured CI environment differs from the pinned SWE substrate — source-confirmed

No workflow references `requirements/software_engineering_kernel_v1.txt`. The heartbeat installs a generic, unpinned dependency set with `|| true`, and its path filters do not cover every runtime/adapter change. It uses `ubuntu-latest`. Its comments acknowledge previous timeouts; it currently uses `--jobs 4` and a 40-minute timeout.

**Needed:** reproducible SWE environments, required dependency failures made explicit, relevant change coverage, and bounded/sharded measurements. Current GitHub run outcomes and branch rules were not queried in this audit; older claims about required checks and latest failures are not new observations.

### 26. Persistent state and replay need a stronger contract — qualification gap

Tests/runtime create checkpoints and learning/source-value state. The audit cleaned the two newly untracked state files it generated. Historical verdict instability is documented, but was not freshly isolated here.

**Needed:** replay the same task in clean identical environments; make mutable experience an explicit versioned input; record nondeterminism and seeds; test interrupted/restarted execution and concurrent tasks.

## What “advanced software engineer” still needs to prove

These are **qualification requirements**, not blanket claims that no related file exists:

1. **Repository-scale understanding:** build graph, dependency graph, types, symbols, dataflow, ownership, tests, history; incremental updates after changes.
2. **Root-cause debugging:** reliable repro, ranked causal hypotheses, targeted experiments, debugger/traces, bisection, minimal fixes.
3. **New feature and architecture work:** derive contracts, choose interfaces, implement multi-file features, reason about compatibility, evolve APIs and schemas.
4. **Serious verification:** independently authored requirements/tests, property and differential testing, mutation/fuzzing, integration/E2E checks; explicit unsupported formal-proof scope.
5. **Systems engineering:** races, deadlocks, cancellation, transactions, consistency, retry/idempotency, backpressure, memory/resource lifetimes.
6. **Performance engineering:** profiles, complexity, allocations, tail latency, load testing, baseline/variance control, measured trade-offs.
7. **Production engineering:** secure builds/dependencies, migrations, observability, rollout/rollback, secrets, authentication/authorization, incident recovery.
8. **Efficient autonomy:** evidence retrieval, bounded search, tool discovery, context/state management, safe parallel task decomposition, escalation when requirements are underspecified.

A model-free owned runtime remains the repository's stated constraint. The compiled unified artifact explicitly contains descriptors/routes/indexes, not trained general-purpose weights. Having a “model” JSON, an SMT package, or a large toolbox does not establish general software reasoning. Learning/acquisition mechanisms must show successful transfer after acquisition-time donors are removed, on untouched tasks. No policy change or runtime model dependency is proposed here.

## Recommended order

1. **Restore trustworthy outcome semantics.** Separate diagnostics/artifact integrity from task success; eliminate fake checks and empty-work success; qualify actual source/test/candidate flow.
2. **Make execution safe.** Isolated task workspace, scoped permissions, quotas, crash recovery, validated atomic promotion.
3. **Prove one complete real-repository workflow.** Natural issue → reproduce → localize → patch → independent tests → regression gates → reviewable diff, without adapter IDs or pre-authored edit instructions in the request.
4. **Strengthen actual mechanisms.** Richer synthesis, semantic/type/build integration, debugger experiments, real cross-file changes; reuse real kernels but replace declaration-only wrappers.
5. **Make connected workflows composable and fast.** Typed artifacts, measured costs, sound incremental indexing/test selection, relevant caching, safe parallel experiments.
6. **Expand depth and languages on unfamiliar repositories.** Include architecture, security, performance, concurrency, migrations, and operational tasks.

Use success rate and time-to-correct-change on held-out real tasks as diagnostic instruments, with failure traces and scope limits. Keep broader product needs as development authority, not a benchmark-score chase. Optimize correctness, efficiency, and capability together; neither universal fastest execution nor globally optimal engineering on arbitrary programs can be established from this finite audit.
