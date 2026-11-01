# Current hardcore software-engineering problems — 2026-11-01

## Scope and delivery status

This is a **producer audit**, not independent qualification, a full-repository test run or proof that every other behavior is correct. It focuses on building software correctly, efficiently and safely—not document/PDF features.

Measurements are against **`c4c74d74d5718299418b511c3a4feef9aff21ff5` plus the current unmerged working-tree changes**, on `arena/9acd8a8c-brain`. The tree includes locally preserved upstream and repair changes. Do not attribute these results to the committed base alone. The repair bundle has **not been merged**, and this reply does not claim it is ready to merge.

Exact observations and SHA-256 identities of the principal measured runtime files are in `canonical/verification/SWE_CURRENT_AUDIT_20261101.json`.

## Fresh measurements

| Instrument | Observation | Interpretation |
|---|---|---|
| Fixed SWE surface | **28/28** | Bounded fixture coverage, not arbitrary engineering competence |
| Advanced request census | **4 served / 49** | Route/execution census; no independent semantic oracle per request |
| Ordinary capability matrix | **21 REAL, 33 refused; no FALSE/DAMAGE-labelled cases** | Finite case-specific oracles; not proof of general soundness or full effect containment |
| Six selected test modules | **105 passed, 4 failed, 5 subtests passed; 7.94 s** | The four failures expose file-versus-tree counting scope; not the whole suite |
| Compiled-model verifier | **31/33** | Artifact recompilation and source-hash integrity fail in the unmerged tree |
| Native module-invocation evidence checker | **24 drift errors** | Some owned mechanisms are not callable through their stale evidence pins |
| Runtime process universe | **No unmediated process sites reported** | Earlier ProcessPoolExecutor inventory defect no longer reproduces locally |
| Default Python substrate at final check | **2/10 required modules present** | Environment gap; separate test venv has pytest/pytest-subtests only |

Advanced classes: polyglot **0/7**, build **0/5**, CI **0/4**, performance **0/4**, systems **0/3**, tests **1/6**, debugging **0/3**, refactoring **2/6**, review **1/3**, Git **0/5**, design **0/3**. These are outcomes for the chosen sentences, not claims of zero machinery in those domains.

## P0 — Reproduced correctness and security problems

### 1. Definition counting loads executable cache data

`canonical/runtime/bound_capabilities/python_source_definition_count.py` loads a predictable temporary `.pkl` cache with `pickle.loads`.

**Fresh observation:** an audit-owned cache payload executed a harmless marker write while the public counter was asked only to count source definitions. The counter still returned its normal report with `output_verified: true`.

This establishes unsafe deserialization at this cache boundary. It does not establish that a remote attacker can populate the cache: practical exposure depends on who can write that filesystem location. Nevertheless, treating such cache data as code is unnecessary for a definition counter and is a serious trust-boundary defect.

### 2. The definition counter's cache can return stale semantic results

This is a **different cache** from the symbol index whose exact-byte provenance controls were repaired.

**Fresh observation:** after replacing one function with a plain assignment while preserving file size and mtime, the public counter still reported **one function**, although the file contained **zero**. It returned an integrity-verified artifact containing that stale result.

The key is path/mtime/size, not source content. This affects correctness under timestamp-preserving updates and shows why one repaired cache does not establish correctness of every cache.

### 3. A file-scoped request counts the surrounding tree

Four strengthened end-to-end tests ask to count functions in one named Python file, with its source-root directory also stated as context. The current binding counts sibling files/test functions as well:

| Reported functions | Functions in the requested file |
|---:|---:|
| 4 | 2 |
| 4 | 1 |
| 3 | 2 |
| 2 | 1 |

This is a real answer-scope bug, not merely an obsolete capability-name assertion. Selecting the definition counter is reasonable; supplying the wrong search scope is not. The stronger tests intentionally retain exact AST-derived expected values and currently fail.

### 4. Pruning still removes implicitly exported public APIs

Explicit `__all__` preservation is fixed locally. Python modules also export non-underscore names without an `__all__` declaration.

**Fresh observation:** in a module without `__all__`, `public_api(4)` initially returns `8`. Local tests exercise a different function. The public repair adapter deletes `public_api`, passes those tests, and returns **`verified: true`** in `dead_code_and_import_pruning` mode.

No in-repository reference is not proof of deadness for a library API, external consumer, plugin, reflection or entry point. The current repair remains narrower than safe whole-program pruning.

### 5. Passing tests remain weaker than the claimed edit correctness

The first four issues show a general acceptance problem: an intact report and green selected tests do not establish that the requested behavior, API surface, source scope or trust boundary is correct.

Verification should distinguish artifact integrity, smoke execution, named regression tests, independent differential/property checks and proof under explicit assumptions. Existing formal/property tooling is a reuse candidate, not proof that every mutator invokes the right oracle.

## P1 — Safety and integration boundaries

### 6. Read-only execution is not a hostile-repository sandbox

Local scaffold execution now reuses Brain's existing CPython audit policy. Fresh controls deny ordinary writes and subprocesses before their effects, including writes to absolute source paths. A complete source-content manifest is checked as well.

That policy lives in the subject interpreter. It is not an OS/container/VM boundary, general native-code confinement, transactional filesystem or concurrent-writer isolation guarantee. Credential access, host resources, network/process isolation and malicious in-process policy tampering still require an explicit threat model and stronger enforcement before unattended adversarial execution.

### 7. Evidence and runtime are not consistently synchronized

The current compiled model passes **31/33**, failing byte-identical recompilation and capability-source hashes. The module-invocation checker reports **24 module drift errors**.

These are concrete delivery/reachability blockers in an unmerged working tree, not proof that the underlying algorithms are all broken. Refreshing hashes without testing the mechanisms would not solve the trust problem. The previous required checks cannot certify current unmerged edits.

### 8. Restored tools do not remain a dependable execution precondition

The earlier repair work restored ten required modules in its venv. The fresh workspace did not retain that environment. Default Python started this audit at **0/10** and ended at **2/10** (the tree-sitter packages); pytest, Hypothesis, coverage, mypy, Ruff, Bandit, CrossHair and Z3 are absent there. The newly created test venv contains pytest/pytest-subtests, not a full runtime restore.

The sequential, pinned restore/check mechanism already exists. The unresolved integration problem is making restoration, interpreter selection, version checks and capability measurements describe the same actual machine. Do not relabel environment loss as an algorithm regression.

### 9. Existing capability discovery and task binding remain unreliable

The 49-request census still serves only **four**. Current refusals include ten route-admission failures, nine controller execution/verification failures, nine unserved effects, eight compilation gaps, six missing requested answers and three capability/input refusals.

Language, project, requested effect, payload, source/test roles, explicit scope and acceptance obligations need to agree before executing a related tool. Adding keywords indiscriminately can make an unsupported request reach an unsafe writer rather than solve it.

### 10. Executing a tool does not necessarily answer the question

Six advanced requests lack the requested answer. A dead-code list is not a measured profile; a taint artifact is not automatically a causal bug explanation; running a bisector does not establish a bracketed breaking commit.

Diagnostics have improved in the preserved upstream changes, so the old blanket claim that every refusal has no useful reason is too strong. Nine cases still end in the broad controller-failure family; cause exposure and recovery remain incomplete.

### 11. Cross-file semantic understanding is bounded

Existing AST and tree-sitter indices are valuable and reusable. They do not establish complete resolution of dynamic dispatch, runtime import construction, reflection, monkey-patching, downstream API consumers, mixed-language boundaries or generated code. A complete enumeration needs an explicit searched scope and a truthful unknown/ambiguous boundary.

The corrected caller test now states a directory search scope. A single defining file still correctly fails a global-completeness claim. This is not a reason to weaken that guard.

## P1 — Advanced engineering coverage

### 12. Polyglot parsing is not complete polyglot engineering

Tree-sitter and C/C++ compilers exist, but the advanced polyglot requests serve **0/7**. Compiler/type-aware transformations, language-specific tests and real project/build models are not reliably joined into complete workflows.

Rust/Cargo, Go, javac and tsc are absent in this environment. This does not mean the entire Brain repository is Python-only or lacks acquisition mechanisms.

### 13. General feature implementation is not established

Bounded AST repairs do not demonstrate open-ended requirement interpretation, task decomposition, new abstractions, multi-file features, coordinated API/call-site evolution or compatibility-preserving migrations. The ordinary matrix still refuses representative issue implementation, cross-file feature, CLI, logging and retry requests.

### 14. Build, dependency and CI loops are not reliably served

Advanced build **0/5**, CI **0/4**. Required work includes parsing and editing actual configuration formats, resolving dependencies, executing builds, validating lockfiles and proving the resulting CI workflow works. A Python repair row is not a substitute for a YAML/build-system mechanism.

CMake, Ninja and Docker are unavailable here; plain Make/C/C++ and Node/npm are available. Tool acquisition and restored environments should be reused where appropriate rather than assuming a new primitive is necessary.

### 15. Debugging and causal diagnosis remain incomplete

Locally, the prior fail-only-versus-shared ranking failure no longer reproduces in the selected tests. That is a bounded ranking repair, not proof of general causal localization, value provenance, cross-process debugging, nondeterministic failure diagnosis or native debugging.

The advanced debug requests still serve **0/3**. gdb is unavailable here.

### 16. Systems/concurrency correctness has only bounded evidence

A fixed race-repair fixture passes, while advanced systems requests serve **0/3**. No current evidence establishes deadlock freedom, lock ordering, cancellation safety, correct scheduling under adverse interleavings, native memory safety or distributed consistency.

### 17. Performance engineering is not closed-loop and general

Advanced performance **0/4**, despite passing bounded performance fixtures. A correct duplicate-scan specialization is not arbitrary optimization. Exact builtin scalar inputs get a fast path; other types retain the original algorithm for correctness.

A mature loop needs actual profiles, a representative workload, bottleneck attribution, a valid cost model, correctness checks, memory/tail-latency measurements and measured before/after behavior. Python stdlib profiling exists; missing `perf` does not mean no profiling is possible.

### 18. Git lifecycle support is uneven

Some diff/bisect cases work, but advanced Git **0/5**. Correct operation and argument transport, dirty-worktree boundaries, safe commits, history interpretation, conflicts and task-specific final-state checks are not established by executing a vaguely related history tool.

### 19. Design, architecture and migration quality remain unmeasured

Advanced design **0/3**. There is no current held-out evidence for high-quality architecture decisions followed by correct implementation, compatibility validation, data/schema migration, staged rollout and rollback. Producing an ADR alone would not satisfy the user's objective of working software.

## P1/P2 — Quality, speed and autonomy evidence

### 20. Generated tests are still smoke tests

The scaffold correctly states that it does not invent semantic expected values. Its fixture table is narrow; arbitrary state, complex inputs, async execution and rich contracts are not established. The fresh async-only control refuses verification rather than falsely passing.

Coverage, mutation and property/formal tools are available as mechanisms, but score increases alone do not establish requirement coverage or independent semantic acceptance.

### 21. Security analysis remains bounded

The repaired qualified import aliases are not complete dataflow, reflection, assignment-alias or dependency-vulnerability analysis. Diff-only checks are not a whole-system audit. The new pickle-cache observation demonstrates why checking the subject application is insufficient if the engineering toolchain itself trusts unsafe data.

The Bandit substitute is recorded as incomplete; do not repeat the obsolete claim that it still asserts a complete external Bandit scan.

### 22. End-to-end speed is not demonstrated by fast refusals

Current advanced-census latency is median **52 ms**, p90 **217 ms**, max **413 ms**—mostly refusals. Matrix median **62 ms**, p90 **427 ms**, max **2,183 ms**. One successful whole-runtime index request took **14,216.5 ms**.

Those are samples, not stable scaling benchmarks. They do not prove a speedup relative to a different environment or the fastest implementation. Measure cost and time per correctly completed task, cold/warm behavior, invalidation, repository scaling, CPU/RAM, retries and p95/p99.

### 23. Representative independent evaluation is missing

Fixed surfaces, self-authored regression tests and finite matrices are valuable falsifiers. They do not establish best-in-class engineering performance on held-out real repositories. The probes also do not monitor every possible filesystem deletion, new file or external effect.

No full-repository suite was run in this audit. There is no basis for claiming that all software-engineering problems are enumerated or solved.

### 24. Production autonomy and recovery are unproven here

Current evidence does not establish long-horizon planning that revises correctly after feedback, correct uncertainty handling, minimal-action tool choice, durable checkpoints, safe crash/cancellation recovery, concurrent-agent coordination, adversarial-repository containment, deployment under load, operational observability or rollback.

These are unmeasured claims, not declarations that no related module exists. Existing tools and papers are candidate mechanisms; only tested integration establishes the actual capability.

## What is no longer an open reproduction locally

Fresh execution of the original counterexample script shows:

- lists-of-lists duplicate scanning preserves its original answer;
- adjacent-only comparisons are not rewritten as all-pairs scans;
- explicit `__all__` APIs remain present;
- ordinary generated-test writes to Python and non-Python source files are refused without changing them;
- the async-only control remains unverified;
- the process-universe compiler reports no unmediated sites.

Selected localizer, scaffold and registry contract controls also pass. None of this is a merged delivery, general sandbox proof, safe pruning of implicit APIs or universal correctness claim.

## Priority order for the most capable, efficient engineer

1. Remove executable/untrusted cache boundaries and stale semantic answers.
2. Bind the exact requested file/project/effect and enforce compatibility and source/API preservation.
3. Make verification evidence levels explicit and execution safe for the actual threat model.
4. Finish and verify the unmerged integration, including source/evidence/model consistency and all required checks.
5. Restore and identify the real substrate before judging capability.
6. Reuse existing indices, compilers, planners, tests, solvers and build tools in representative complete engineering loops.
7. Optimize successful, correct work—not refusal latency or artifact counts.
8. Qualify generalization, autonomy and production reliability independently.

**Bottom line:** the bottleneck is trustworthy integration of existing mechanisms into correct, safely executed, task-complete engineering—not the sheer number of tools, papers or registered capabilities. Universal optimality, speed leadership and software-engineering intelligence remain claims to measure, not statuses to declare.
