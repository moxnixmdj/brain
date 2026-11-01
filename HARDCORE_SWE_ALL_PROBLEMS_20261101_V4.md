# The complete problem inventory — hardcore software engineering

**Measured 2026-11-01 on `6aa5dab`** (this branch's base = `origin/main`). Every number below comes from a run in
this checkout, not from a plan. Re-measure with the commands in Appendix A.

Scope: the machine as a software engineer — compilers, build, CI, performance, systems, testing, debugging,
refactoring, review, git, design. Document / PDF / office work is excluded by standing instruction and is counted
nowhere below, neither as a case nor as a gap.

---

## 0. The scoreboard

| instrument | what it asks | result | median |
|---|---|---|---:|
| `execution_guard/swe_advanced_probe_v1.py` | 49 advanced SWE sentences, 10 axes, through the live front door | **36 served / 13 refused** — of which **1 served answer is false** (#44) | 38 ms |
| `execution_guard/swe_capability_matrix_v1.py` | 54 ordinary cases, each with a world oracle | **44 REAL / 0 FALSE / 0 DAMAGED / 10 refused** | 92 ms |
| `hardcore_swe_surface_probe_20261030.py` | 28 capability surfaces, by real execution | **28 / 28** | — |
| registry | rows the door can rank | **443 rows, 566 declared effects, 11 reached by the 49 sentences** | — |
| substrate | kernel modules the manifest pins | **10 / 10 after `scripts/restore_substrate_v1.py`** (8 of 10 were absent, measured directly) | 15 s |
| laws | `canonical/tests` | **2,248 test modules**; full discovery exceeds a 28-minute budget (§7) | — |

**35 genuinely answered, 13 refused, 1 answered with the wrong question** (`#44`: asked for the diff against
`HEAD~1`, given the diff against `HEAD` and stamped VERIFIED).

The fourth row is the one to read twice. **Three rows serve 31 of the 36 served sentences**, and **11 of 443
rows are ever reached.** The machine is not short of capability; it is short of *declaration* and *routing* —
and both are cheap to fix, because the capability is already written.

---

## 1. The ten axes, sentence by sentence

| axis | served | total | verdict |
|---|---:|---:|---|
| polyglot | 4 | 7 | Rust, Go, Java, TypeScript, TOML, YAML and Make are edited and verified; **C++ and SQL go through a pattern table**, and both of their fixtures hold already-correct code |
| build | 3 | 5 | pyproject create/add/pin, Makefile targets, vendoring all work; the **pin/vendor fixtures declare no dependency to act on** |
| ci | 3 | 4 | workflow create / matrix / cache / fix all work; **flaky-test quarantine** cannot answer because the test is not flaky |
| perf | 3 | 4 | hot-spot profiling, memoisation and O(n²)→O(n) all work; **benchmark against a revision** is unreachable and needs two commits |
| systems | 2 | 3 | thread pool and GIL release are written and verified; **race *detection*** runs when invoked directly and is unreachable by sentence |
| tests | 5 | 6 | unit, property, mutation and suite diagnosis all work; **regression tests** cannot be routed |
| debug | 2 | 3 | root cause and behaviour explanation work; **bisect / provenance** is blocked by binding and declaration |
| refactor | 5 | 6 | rename, move, extract, split, inline, type hints all work; **a symbol move with a name collision** is an honest refusal |
| review | 3 | 3 | 3 of 3 — security, API design, dependency audit |
| git | 3 | 5 | commit and branch+commit work; **cherry-pick and changelog** are implemented but undeclared; **diff against a revision** silently drops the revision |
| design | 3 | 3 | 3 of 3 — ADR, migration plan, package split |

### 1.1 All 49 sentences

| # | axis | R | sentence | row reached | cause |
|---:|---|:-:|---|---|---|
| 1 | polyglot | ❌ | Fix the off-by-one bug in canonical/astra_runtime/tmp/swe_advanced_probe/01_polyglot/src/main.cpp so th… | code.polyglot.transform_and_verify.v1 | POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM |
| 2 | polyglot | ✅ | Add a function sub to canonical/astra_runtime/tmp/swe_advanced_probe/02_polyglot/src/lib.rs that subtra… | code.polyglot.transform_and_verify.v1 |  |
| 3 | polyglot | ✅ | Add a method Mul to canonical/astra_runtime/tmp/swe_advanced_probe/03_polyglot/src/main.go that multipl… | code.polyglot.transform_and_verify.v1 |  |
| 4 | polyglot | ✅ | Add a second method to canonical/astra_runtime/tmp/swe_advanced_probe/04_polyglot/src/Main.java and mak… | code.polyglot.transform_and_verify.v1 |  |
| 5 | polyglot | ✅ | Rename the exported function add to plus in canonical/astra_runtime/tmp/swe_advanced_probe/05_polyglot/… | code.polyglot.transform_and_verify.v1 |  |
| 6 | polyglot | ❌ | Add a NOT NULL constraint on users.email in canonical/astra_runtime/tmp/swe_advanced_probe/06_polyglot/… | code.polyglot.transform_and_verify.v1 | POLYGLOT_REFUSED:SQL_UNSUPPORTED_DDL_EDIT |
| 7 | polyglot | ❌ | Repair the C++ source file canonical/astra_runtime/tmp/swe_advanced_probe/07_polyglot/src/main.cpp so t… | code.polyglot.transform_and_verify.v1 | POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM |
| 8 | build | ✅ | Add pytest as a development dependency in canonical/astra_runtime/tmp/swe_advanced_probe/08_build/pypro… | code.polyglot.transform_and_verify.v1 |  |
| 9 | build | ✅ | Create a pyproject.toml for the project in canonical/astra_runtime/tmp/swe_advanced_probe/09_build/pkg … | code.polyglot.transform_and_verify.v1 |  |
| 10 | build | ✅ | Add a target `lint` to canonical/astra_runtime/tmp/swe_advanced_probe/10_build/Makefile that runs ruff … | code.polyglot.transform_and_verify.v1 |  |
| 11 | build | ❌ | Pin the dependency versions in canonical/astra_runtime/tmp/swe_advanced_probe/11_build/pyproject.toml. | code.polyglot.transform_and_verify.v1 | POLYGLOT_REFUSED:PYPROJECT_ALREADY_PINNED_OR_EMPTY |
| 12 | build | ❌ | Vendor the single dependency of the project in canonical/astra_runtime/tmp/swe_advanced_probe/12_build/… | code.polyglot.transform_and_verify.v1 | POLYGLOT_REFUSED:NO_DECLARED_DEPENDENCY_TO_VENDOR |
| 13 | ci | ✅ | Fix the failing CI job in canonical/astra_runtime/tmp/swe_advanced_probe/13_ci/.github/workflows/ci.yml. | code.polyglot.transform_and_verify.v1 |  |
| 14 | ci | ✅ | Make the CI workflow in canonical/astra_runtime/tmp/swe_advanced_probe/14_ci/.github/workflows/ci.yml r… | code.polyglot.transform_and_verify.v1 |  |
| 15 | ci | ✅ | Add caching of pip downloads to canonical/astra_runtime/tmp/swe_advanced_probe/15_ci/.github/workflows/… | code.polyglot.transform_and_verify.v1 |  |
| 16 | ci | ❌ | Quarantine the flaky test in canonical/astra_runtime/tmp/swe_advanced_probe/16_ci/tests/test_calc.py so… | code.polyglot.transform_and_verify.v1 | POLYGLOT_REFUSED:NO_FLAKY_TEST_DETECTED |
| 17 | perf | ✅ | Profile canonical/astra_runtime/tmp/swe_advanced_probe/17_perf/pkg/util.py and tell me which function i… | software.analysis.diagnose_and_architect.v1 |  |
| 18 | perf | ✅ | Optimise the function total in canonical/astra_runtime/tmp/swe_advanced_probe/18_perf/pkg/util.py; it i… | python.swe.transform_and_synthesize.v1 |  |
| 19 | perf | ❌ | Benchmark canonical/astra_runtime/tmp/swe_advanced_probe/19_perf/pkg/calc.py against the version in git… | — | NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT |
| 20 | perf | ✅ | Add memoisation to the function twice in canonical/astra_runtime/tmp/swe_advanced_probe/20_perf/pkg/mod… | python.swe.transform_and_synthesize.v1 |  |
| 21 | systems | ❌ | Find the race condition in canonical/astra_runtime/tmp/swe_advanced_probe/21_systems/pkg/service.py. | software.repair.choreograph.crossfile.v1 | STATED_ANSWER_NOT_PROVIDED:STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER:software.repair.choreo |
| 22 | systems | ✅ | Add a thread pool to canonical/astra_runtime/tmp/swe_advanced_probe/22_systems/pkg/util.py that totals … | python.swe.transform_and_synthesize.v1 |  |
| 23 | systems | ✅ | Make the function total in canonical/astra_runtime/tmp/swe_advanced_probe/23_systems/pkg/util.py releas… | python.swe.transform_and_synthesize.v1 |  |
| 24 | tests | ✅ | Write a unit test for the function mul in canonical/astra_runtime/tmp/swe_advanced_probe/24_tests/pkg/c… | python.swe.transform_and_synthesize.v1 |  |
| 25 | tests | ✅ | Write a property-based test for the function add in canonical/astra_runtime/tmp/swe_advanced_probe/25_t… | python.swe.transform_and_synthesize.v1 |  |
| 26 | tests | ❌ | Add a regression test that reproduces the bug in canonical/astra_runtime/tmp/swe_advanced_probe/26_test… | — | STATED_SWE_EFFECT_UNSERVED |
| 27 | tests | ✅ | Increase the mutation score of canonical/astra_runtime/tmp/swe_advanced_probe/27_tests/pkg/calc.py abov… | python.swe.transform_and_synthesize.v1 |  |
| 28 | tests | ✅ | Fuzz the function add in canonical/astra_runtime/tmp/swe_advanced_probe/28_tests/pkg/calc.py for intege… | software.analysis.diagnose_and_architect.v1 |  |
| 29 | tests | ✅ | Run the test suite in canonical/astra_runtime/tmp/swe_advanced_probe/29_tests/tests and tell me which t… | python.repository.acceptance.measure.v1 |  |
| 30 | debug | ✅ | The test in canonical/astra_runtime/tmp/swe_advanced_probe/30_debug/tests/test_calc.py fails; find the … | software.analysis.diagnose_and_architect.v1 |  |
| 31 | debug | ✅ | Explain why the function total in canonical/astra_runtime/tmp/swe_advanced_probe/31_debug/pkg/util.py r… | software.analysis.diagnose_and_architect.v1 |  |
| 32 | debug | ❌ | Find the commit that broke the test in canonical/astra_runtime/tmp/swe_advanced_probe/32_debug/tests/te… | git.history.bisect_regression.v1 | STATED_ANSWER_NOT_PROVIDED:STATED_PROVENANCE_NOT_ANSWERED_BY_CAPABILITY:git.history.bisect_regre |
| 33 | refactor | ❌ | Move the function add from canonical/astra_runtime/tmp/swe_advanced_probe/33_refactor/pkg/mod.py into c… | python.refactor.move_symbol.v1 | TARGET_SYMBOL_COLLISION:add |
| 34 | refactor | ✅ | Split canonical/astra_runtime/tmp/swe_advanced_probe/34_refactor/pkg/calc.py into one module per functi… | python.swe.transform_and_synthesize.v1 |  |
| 35 | refactor | ✅ | Rename the public function total in canonical/astra_runtime/tmp/swe_advanced_probe/35_refactor/pkg/util… | python.refactor.rename_symbol.v1 |  |
| 36 | refactor | ✅ | Replace every use of the deprecated function mul in canonical/astra_runtime/tmp/swe_advanced_probe/36_r… | python.swe.transform_and_synthesize.v1 |  |
| 37 | refactor | ✅ | Add type hints to every function in canonical/astra_runtime/tmp/swe_advanced_probe/37_refactor/pkg/calc… | python.swe.transform_and_synthesize.v1 |  |
| 38 | refactor | ✅ | Extract the loop in the function total in canonical/astra_runtime/tmp/swe_advanced_probe/38_refactor/pk… | python.refactor.extract_function.v1 |  |
| 39 | review | ✅ | Review canonical/astra_runtime/tmp/swe_advanced_probe/39_review/pkg/service.py for API design problems. | software.analysis.diagnose_and_architect.v1 |  |
| 40 | review | ✅ | Review canonical/astra_runtime/tmp/swe_advanced_probe/40_review/pkg/calc.py for security issues. | python.review.diff_security_gate.v1 |  |
| 41 | review | ✅ | Audit the dependency list in canonical/astra_runtime/tmp/swe_advanced_probe/41_review/pyproject.toml fo… | software.analysis.diagnose_and_architect.v1 |  |
| 42 | git | ✅ | Commit the changes in canonical/astra_runtime/tmp/swe_advanced_probe/42_git/pkg with a clear message. | python.swe.transform_and_synthesize.v1 |  |
| 43 | git | ✅ | Create a branch named feature/x and commit canonical/astra_runtime/tmp/swe_advanced_probe/43_git/pkg/ca… | python.swe.transform_and_synthesize.v1 |  |
| 44 | git | ⚠️ | Show me the diff of canonical/astra_runtime/tmp/swe_advanced_probe/44_git/pkg/calc.py against HEAD~1. | git.repository.operate.v1 | **FALSE PASS** — the stated revision was dropped, see §4/D2 |
| 45 | git | ❌ | Cherry-pick the last commit onto a new branch. | — | NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT |
| 46 | git | ❌ | Write the changelog entry for the last three commits. | — | NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT |
| 47 | design | ✅ | Design the API for a rate limiter and write an ADR. | software.analysis.diagnose_and_architect.v1 |  |
| 48 | design | ✅ | Plan the migration of the package in canonical/astra_runtime/tmp/swe_advanced_probe/48_design/pkg from … | software.analysis.diagnose_and_architect.v1 |  |
| 49 | design | ✅ | Write a design document for splitting canonical/astra_runtime/tmp/swe_advanced_probe/49_design/pkg into… | software.analysis.diagnose_and_architect.v1 |  |

---

## 2. The 13 refusals, and what each one really is

| # | sentence | what happened | the real problem | class |
|---:|---|---|---|---|
| 1 | Fix the off-by-one bug in canonical/astra_runtime/tmp/swe_advanced_probe/01_p… | POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM | `code.polyglot.transform_and_verify.v1` refused `CPP_NO_APPLICABLE_TRANSFORM`. The fixture's `sum` is already correct, so there is no bug to fix — the honest answer is a verified *diagnosis* ('sum already returns the right total'), and the machine has no C++ defect localiser to say it with. | already-satisfied + no localiser |
| 6 | Add a NOT NULL constraint on users.email in canonical/astra_runtime/tmp/swe_a… | POLYGLOT_REFUSED:SQL_UNSUPPORTED_DDL_EDIT | `SQL_UNSUPPORTED_DDL_EDIT`. The fixture's `users.email` is **already** `TEXT NOT NULL`. The request is already satisfied; the row cannot certify that, so it refuses. | already-satisfied |
| 7 | Repair the C++ source file canonical/astra_runtime/tmp/swe_advanced_probe/07_… | POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM | Same row, same cause, same fixture: the file already compiles cleanly. The machine refuses instead of certifying the end state, because no C++ localiser exists to say 'nothing to repair'. | already-satisfied + no localiser |
| 11 | Pin the dependency versions in canonical/astra_runtime/tmp/swe_advanced_probe… | POLYGLOT_REFUSED:PYPROJECT_ALREADY_PINNED_O… | `PYPROJECT_ALREADY_PINNED_OR_EMPTY`. The fixture declares no `[project.dependencies]`, so the fixture cannot decide this sentence at all. Fixture, not capability. | fixture |
| 12 | Vendor the single dependency of the project in canonical/astra_runtime/tmp/sw… | POLYGLOT_REFUSED:NO_DECLARED_DEPENDENCY_TO_… | `NO_DECLARED_DEPENDENCY_TO_VENDOR` — the same fixture defect. | fixture |
| 16 | Quarantine the flaky test in canonical/astra_runtime/tmp/swe_advanced_probe/1… | POLYGLOT_REFUSED:NO_FLAKY_TEST_DETECTED | `NO_FLAKY_TEST_DETECTED`. The test is deterministic, so the premise is false; the right answer is the measurement ('not flaky in N runs'), which nothing in the registry can produce today. | verdict-as-refusal |
| 19 | Benchmark canonical/astra_runtime/tmp/swe_advanced_probe/19_perf/pkg/calc.py … | NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT | No plan was decisive. The operation **exists** (`benchmark_git_ref`) and the fixture has one commit, so the comparison target `HEAD~1` does not exist. Declaration gap + fixture gap. | declaration + fixture |
| 21 | Find the race condition in canonical/astra_runtime/tmp/swe_advanced_probe/21_… | STATED_ANSWER_NOT_PROVIDED:STATED_READ_ONLY… | Routed to a *writer* and refused `STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER`. `find_race_condition` is implemented in the same registry and **runs today** (measured in §2.1); no `provides` entry names it, so the door never sees it. | declaration |
| 26 | Add a regression test that reproduces the bug in canonical/astra_runtime/tmp/… | STATED_SWE_EFFECT_UNSERVED | `STATED_SWE_EFFECT_UNSERVED`, nothing selected. `write_regression_test` is implemented as an `op` of `python.swe.transform_and_synthesize.v1`; no declared effect stands for it. | declaration |
| 32 | Find the commit that broke the test in canonical/astra_runtime/tmp/swe_advanc… | STATED_ANSWER_NOT_PROVIDED:STATED_PROVENANC… | `git.history.bisect_regression.v1` was selected, its `source_root` refused to bind on a *test* path, and the provenance gate then refused the answer because the row declares no blame/changelog effect. Three defects stacked: binding, fixture (one commit), declaration. | binding + fixture + declaration |
| 33 | Move the function add from canonical/astra_runtime/tmp/swe_advanced_probe/33_… | TARGET_SYMBOL_COLLISION:add | `TARGET_SYMBOL_COLLISION:add` — both modules already define `add`, so the move is genuinely ambiguous. This is an **honest** refusal; what is missing is merge-on-collision, not routing. | honest refusal |
| 45 | Cherry-pick the last commit onto a new branch. | NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT | No row. `git_cherry_pick` is implemented and refuses only because the fixture has one commit (`GIT_CHERRY_PICK_REQUIRES_AT_LEAST_TWO_COMMITS`, measured below). Declaration gap + fixture gap. | declaration + fixture |
| 46 | Write the changelog entry for the last three commits. | NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT | No row. `git_changelog` is implemented and **runs today** (measured below, produced entries). A pure declaration gap: the door ranks on `provides`, and no row declares a changelog effect. | declaration |

### 2.1 What is already written behind those refusals — measured, not inferred

Each operation below was called **directly** on a throw-away repository to separate 'the machine cannot' from
'the door cannot see it':

| operation | implemented in | direct call result |
|---|---|---|
| `git_changelog` | `software.analysis.diagnose_and_architect_v1` | **PASS** — produced `- 34b18dd baseline (b)` |
| `find_race_condition` | same | **PASS** |
| `git_cherry_pick` | `python_swe_transform_and_synthesize_v1` | refused `GIT_CHERRY_PICK_REQUIRES_AT_LEAST_TWO_COMMITS` — the **fixture** has one commit |
| `benchmark_git_ref` | `software.analysis.diagnose_and_architect_v1` | refused `GIT_REF_NOT_AVAILABLE:HEAD~1` — the **fixture** has one commit |
| `git_branch_and_commit` | `python_swe_transform_and_synthesize_v1` | refused `GIT_NOTHING_CHANGED_TO_COMMIT` — the **fixture** is clean |

So of the 13 refusals: **2 are pure declaration gaps over working code**, **3 need a two-commit fixture**, **2 need
a declaration**, **2 are fixture-only**, **2 are 'the stated end state already holds'**, and **1 is an honest
refusal** (`#33`, a real symbol collision).

---

## 3. The capability matrix: 44 of 54 ordinary cases

| case | status | what it really is |
|---|---|---|
| `extract_function` | `FAIL_CLOSED__CAPABILITY_REFUSED_REGION_INVALID` | `python.refactor.extract_function.v1` exists and serves other sentences; for this sentence no plan was decisive (no capability selected). Routing. |
| `extract_constant` | `FAIL__LIVE_CONTROLLER_EXECUTION` | `extract_constant` is an implemented `op` of the SWE row and no declared effect names it. Declaration gap. |
| `tests_from_docstrings` | `FAIL_CLOSED__CAPABILITY_RETURNED_A_VERDICT` | `tests_from_docstrings` is implemented; the door refuses to bind the row's `source_root` (`BINDING_REFUSED:source_root:0_existing_directories_named`, measured directly) because the scope is not declared `path_file_or_dir`. Binding gap. |
| `find_definition` | `FAIL__RAW_GOAL_COMPILATION_GAP` | Nothing declares 'where is a symbol defined'. The AST index rows provide an index and references, not a lookup by name. No row. |
| `git_branch` | `FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED` | `git_branch_and_commit` is implemented. 'Create a branch named feature/x' states no operation the grammar reads, so no plan is built. Stated-operation gap. |
| `missing_source` | `FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED` | The named file does not exist. The refusal is **honest**; only its cause (`STATED_SWE_EFFECT_UNSERVED`) fails to say so. |
| `ambiguous_fix_it` | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | 'fix it' with no antecedent. **Honest** refusal, correctly fail-closed. |
| `bisect_regression` | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` | `git.history.bisect_regression.v1` is reached, then refuses twice: the row's `source_root` will not bind on a *test* path (measured directly: `BINDING_REFUSED:source_root:0_existing_directories_named`) and the answer gate refuses the provenance claim because the row declares no blame/changelog effect. Binding + declaration + a one-commit fixture. |
| `delete_file` | `FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN` | No row and no `op` deletes a file anywhere in the registry. Genuine missing capability. |
| `idempotent_refusal` | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | 'fix it', a second spelling of the same sentence. **Honest** refusal. |

Zero damaged, zero false. `lint` and `typecheck` were two of these refusals an hour before this measurement;
**restoring the substrate closed both without touching a line of runtime code** (§5).

---

## 4. The six defect classes behind all 23 refusals

### D1 — Declaration blindness (≈8 cases). The biggest problem in the machine.

Five platform adapters dispatch **101 distinct operations** and together declare **36 effects**:

| adapter | operations implemented | effects declared |
|---|---:|---:|
| `python_swe_transform_and_synthesize_v1` | 39 | 8 |
| `code_polyglot_transform_and_verify_v1` | 29 | 6 |
| `software_analysis_diagnose_and_architect_v1` | 27 | 13 |
| `python_review_diff_mutation_gate` | 4 | 1 |
| `software_repair_crossfile_choreograph_v1` | 2 | 8 |

The door ranks, admits and refuses **only on `provides`** (plus id and keywords). An operation the adapter
dispatches but no effect names is **invisible**: the machine owns it and cannot be asked for it. `git_changelog`,
`find_race_condition`, `git_cherry_pick`, `benchmark_git_ref`, `write_regression_test`, `extract_constant` and
`tests_from_docstrings` are all in that state today.

This is the exact inverse of the defect the previous inventory chased (a row *declaring* effects it does not
implement). Both are declaration errors; the second one is invisible to every test that only reads the registry.
The fix reuses what is already here: each adapter already enumerates its operations in its dispatch table, and the
registry is already *derived* from adapters for 293 of its 443 rows.

### D2 — A dropped stated argument (1 case, and it is a **false pass**).

Measured on a two-commit repository (`canonical/astra_runtime/tmp/probe_rev2`) where the two answers differ:

```
sentence : Show me the diff of <pkg>/f.py against HEAD~1.
truth    : git diff HEAD~1  ->  one hunk,  -A = 1  +A = 2
machine  : git diff HEAD    ->  (empty)
artifact : rows: []                      output_verified: True
status   : PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED
```

`git.repository.operate.v1` declares `op`, `target`, `repo_root`, `limit` and `message` — and **no `rev`**. The
sentence's `HEAD~1` has nowhere to bind, is dropped, and the row answers the question it *can* answer. This is the
`output_verified: True` without an observed effect class, the worst one this repository names, and the census scores
it as a pass because its oracle only asks whether the run was verified and the tree was untouched.

Two fixes exist in the repo and compose: declare `rev` on the row (`OPS` already carries `diff`/`show`/`log`), and
let `declared_input_derivation_v1` — which already reads `HEAD~1` — bind it. The door's `R11_STATED_PAYLOAD_SLOT_MISSING`
rule is exactly the guard for the unbound case, and it fires today for other payloads.

### D3 — Silent verification degradation (3 adapters).

`rust_transform_and_verify`, `go_transform_and_verify` and `java_transform_and_verify` return
`compiler_verified: <bool>` and set it to `False` when the compiler is absent — then write the file and return
`gate: PASS`. On this image `rustc`, `go` and `javac` are absent, so three 'compiler-verified' languages are
pattern-verified and reported as passing. The flag is honest; the gate it feeds is not.

### D4 — A row exists and the sentence never reaches it (≈7 cases).

`find_race_condition` (#21), `git_changelog` (#46), `git_cherry_pick` (#45), `write_regression_test` (#26),
`extract_constant`, `tests_from_docstrings` and `extract_function` all live behind rows the door selected or could
have selected, and no sentence reached the operation. Two of those are binding defects rather than ranking ones:
`source_root` is refused for a *test* path (`tests_from_docstrings`, `bisect_regression`) because the row does not
declare its scope as `path_file_or_dir`, and `git_branch_and_commit` is never reached because
`stated_git_operations` does not read 'Create a branch named X'.

### D5 — The fixture cannot decide the sentence (5 cases).

`#11`/`#12` name a dependency the fixture does not declare; `#1`/`#6`/`#7` name a defect the fixture does not have;
`#19`/`#32`/`#45`/`#46` need a history and `seed_repository` commits exactly once. A census whose fixture cannot
separate 'the machine cannot' from 'the fixture gave it nothing' certifies nothing — the same law this harness
already applies to its oracles.

### D6 — The stated end state already holds and the machine refuses instead of saying so (2–6 cases).

`sum` is already correct; `users.email` is already `NOT NULL`; the dependency list is already empty. A senior
engineer answers 'already true, here is the proof'. The door already has that concept for repairs
(`already_satisfied`) and the polyglot and analysis rows do not use it, so they refuse work that is already done —
which reads to a caller exactly like a missing capability.

---

## 5. The substrate: one command, and it is measured

| | before | after `python3 scripts/restore_substrate_v1.py` |
|---|---|---|
| kernel modules importable | **8 of 10 absent** by direct import | **10 / 10** (`pytest`, `hypothesis`, `z3`, `crosshair`, `coverage`, `mypy`, `ruff`, `bandit`, `tree_sitter`, `tree_sitter_languages`) |
| binaries | 6 / 6 | 6 / 6 (`git gcc g++ make node npm`; **absent**: `rustc go javac tsc cargo cmake ninja docker gdb strace valgrind`) |
| capability matrix | 42 REAL | **44 REAL** — `lint` and `typecheck` closed |
| advanced census | 36 / 49 | 36 / 49 — unchanged; the advanced refusals are structural, not substrate |
| wall clock | — | **15 s** |

The script exists, verifies itself (`SUBSTRATE_READY`, parser version match) and pins the kernel by SHA-256. No
gate runs it, so an image without the substrate silently measures a smaller machine — which is exactly what had
happened: `lint` and `typecheck` were recorded as capability gaps and were a missing `pip install`.

Absent and load-bearing for the *advanced* bar, cheapest first:

| absent | what it unlocks | cost |
|---|---|---|
| `rustc` + `cargo` | real compile-verification for Rust (today: pattern match, `rustc` if present) | toolchain install |
| `go` + `gofmt` | the same for Go | toolchain install |
| `javac` + `java` | the same for Java | toolchain install |
| `tsc` | real type-verification for TypeScript (`node` only strips types) | `npm i -g typescript` |
| `gdb`, `strace`, `valgrind`, `perf` | the debug axis: frames, syscalls, leaks, real sampling | apt + privileges |
| `cmake`, `ninja`, `docker` | build-system editing beyond Make and pyproject | toolchain install |

---

## 6. Speed

| instrument | median | p90 | slowest observed |
|---|---:|---:|---|
| advanced census (49) | **38 ms** | 191 ms | `#25` mutation score 451 ms, `#40` security review 285 ms |
| capability matrix (54) | **92 ms** | — | fixture rebuild dominates (each case re-creates a tree) |

Speed is **not** the current limit on capability: the door answers in tens of milliseconds, end to end. The two
places where time is real are the composed chain and re-parsing large artifacts, and both already carry named fixes
in this repository (the section-read gate and the tree-keyed cache from earlier work). The one cost that is a
*defect* by the standing law is the double pass over the sentence grammar (front compiler, then route admission);
at ~38 ms per sentence it is acceptable, and it becomes a defect the moment it grows.

---

## 7. Verification debt

| | count | state |
|---|---|---|
| test modules in `canonical/tests` | 2,248 | **full discovery did not finish inside a 28-minute budget** on this image |
| laws recorded by the last complete run (V3, `bbc00a7`) | 625 | 20 red |
| GitHub workflows | 323 | 1 gates the advanced census (`swe-advanced-census.yml`, floor 5/49) |
| workflows gating the 54-case matrix | **0** | the matrix has world oracles and no gate |
| workflows gating the surface census | 1 | 28/28 |

Three consequences worth stating plainly:

1. **A suite that cannot finish in one sitting cannot gate anything.** 2,248 modules at this image's speed is a
   multi-hour run; in practice the law layer is sampled, never checked.
2. **The strongest instrument has no floor.** The matrix has 54 cases with *world oracles* and nothing fails a
   build when it regresses. The advanced census got its floor two changes ago and immediately caught a real
   deletion that three inventories had argued for.
3. **The matrix is deterministic only when it rebuilds its trees.** Two full runs on the same tree differ in exactly
   the two cases the substrate restore changed (`lint`, `typecheck`) and nowhere else; re-running a single goal
   against a fixture a previous run left behind can return a different status, which is why every cause in §3 is
   quoted from a fresh direct run against a fresh tree.

---

## 8. What 'the most advanced software engineer' still requires, axis by axis

Each line names the bar, what the machine already has, and the specific thing it lacks. The bar is the state of the
art in that axis, not a wish list.

| axis | the bar | what exists | the specific gap |
|---|---|---|---|
| **compilers / polyglot** | Edit and *prove* by compiling, in every language the repository already reads. | gcc/g++/node drive C++ and TypeScript verification; `rustc`/`go`/`javac` are wired and degrade silently; SQL, TOML and YAML have real validators. | A C/C++ **defect localiser**. `cpp_repair` is a pattern table (`cpp_fix_off_by_one`) with no notion of 'off-by-one' in a new file; tree-sitter already parses C++, so the index exists and only the localiser is missing. |
| **build systems** | Read and write any build definition, and prove it still builds. | pyproject create/add/pin/vendor, Makefile targets, wheel build, requirements lock, SBOM. | CMake / Ninja / Bazel / Cargo manifest editing, and 'did the build still succeed' for non-Python trees (`make` is the only real runner). |
| **CI** | Author, diff and *simulate* a workflow; know which jobs would fail. | create / fix / matrix / cache on a workflow file with YAML validation, and 323 real workflows in-repo to learn shapes from. | No local execution model of a workflow, and no flakiness measurement (the `quarantine` op cannot say 'not flaky'). |
| **performance** | Measure, attribute, transform, and *prove the improvement*. | cProfile hot-spot ranking, memoisation, O(n²)→O(n) strength reduction, benchmark-vs-revision (implemented). | Wall-clock *differential* proof: every transform is verified for behaviour, never for speed. `perf`/`py-spy` are absent; the benchmark op is unreachable and its fixture has one commit. |
| **systems / concurrency** | Find races, prove the fix, measure parallel speedup. | RLock synthesis (Pass E) proved by ten real runs; thread-pool and GIL-release transforms verified by syntax and suite. | Race *detection* is `find_race_condition` (unreachable). No ThreadSanitizer, no GIL-holding measurement, no deterministic scheduler. |
| **testing** | Generate, mutate, fuzz, and *know* the suite's strength. | unittest/pytest runners, mutation score, property tests (hypothesis installed), coverage, regression-test authoring (implemented). | No run-time test *impact* selection (the index exists), and no flaky detection across N runs. |
| **debugging** | From symptom to fault, with evidence. | Root-cause and behaviour explanation, suite diagnosis, data-flow tracing, bisect (needs a real history). | No frame-level debugger and no traceback capture from a live run; `gdb`/`strace` absent; fault localisation is Python-dataflow only. |
| **refactoring** | Any structural change, proved safe across the call graph. | rename, move symbol, move module, extract function, inline, split, type hints, dead-code removal — all AST-verified with dual oracles. | Collision-aware merge (two modules defining the same symbol) and cross-language refactoring. |
| **review** | Verdicts that are measurements, not opinions. | Security, API design, dependency audit, and diff-scoped lint / type / coverage / mutation gates (ruff, mypy, bandit and coverage are installed). | No behavioural-risk ranking (complexity, regression risk), and no PR-level synthesis of the gates into one verdict. |
| **git** | Any history question or operation, against a stated revision. | commit, branch+commit, diff, show, log, blame, status, bisect (row), changelog and cherry-pick (ops). | `rev` is not in the contract — a **false pass** today; cherry-pick and changelog are undeclared; conflict resolution stops at the merge-conflict pass. |
| **design** | Produce the artefact, not a description of it. | ADR, migration plan, package-split document, PR description, design review. | Nothing verifies a design against the code it constrains (for example, whether a split plan's target graph would still import). |

---

## 9. The queue, ordered by cases gained per hour of work

Every item reuses a mechanism that is already in this repository. No new primitive is proposed anywhere.

| # | change | cases | mechanism already present | cost |
|---:|---|---:|---|---|
| 1 | Run `scripts/restore_substrate_v1.py` in CI and in the dev boot | **+2 measured** (lint, typecheck); unlocks the hypothesis / z3 / crosshair rows | the script, the hashed manifest and the review-tool file all exist | 15 s, one workflow step |
| 2 | Derive each adapter's `provides` from its own dispatch table instead of hand-listing 8, 6 and 13 effects for 39, 29 and 27 operations | **+6 candidates**: #21, #26, #45, #46, matrix `extract_constant`, `tests_from_docstrings` | the adapters already enumerate every `op`; the registry is already generated from adapters for 293 of 443 rows | one generator pass + recompile |
| 3 | Seed a three-commit fixture with a planted regression | arms #19, #32, #45, #46 — four cases that cannot be decided today | `execution_guard/swe_git_fixture_v1.py`, one function, already the single owner of the fixture | ~20 lines |
| 4 | Add `rev` to `git.repository.operate.v1`'s contract and honour it in `_op_diff` / `_op_show` / `_op_log` | removes the only **false pass**; enables #19 | `OPS` already includes diff/show/log; `declared_input_derivation_v1` already reads `HEAD~1` | ~15 lines + 1 test |
| 5 | Declare `source_root` / `worktree_path` as `path_file_or_dir` on the rows that provably accept one file | **+2** (matrix `tests_from_docstrings`, #32) | `goal_front_compiler_v1.bind_typed_key` already honours exactly this declaration | registry edit only |
| 6 | Read 'Create a branch named X' as a stated git operation | **+1** (matrix `git_branch`) | `declared_input_derivation_v1.stated_git_operations` already owns that grammar | one clause |
| 7 | Let the polyglot and analysis rows certify 'the stated end state already holds' instead of refusing | +2 … +6 depending on how the census scores them (#1, #6, #7, #11, #12, #16) | the door already has `already_satisfied` and uses it for repairs | one flag + one test |
| 8 | One `provides` entry and one `op` for 'where is symbol X defined' | **+1** (matrix `find_definition`) | the AST index row already parses and indexes every definition | ~5 lines |
| 9 | Give the debug axis a real debugger (`pdb` is in the stdlib; `gdb` is not installed) | raises the ceiling on 3 debug sentences; no single case flips | the `python.fault.*` rows already exist | one adapter |
| 10 | Gate the 54-case matrix at its measured floor | protects every item above from silent regression | `swe-advanced-census.yml` is the exact template | one workflow |

If items 1–8 land, the advanced census reaches **≈47 / 49** and the matrix **≈51 / 54**; the residue is #33 (a
genuine symbol collision) and a C++ defect localiser. Those are projections, not measurements — each item must be
re-measured by the instrument it claims to move, which is the rule this repository already follows.

---

## 10. Three things that are true and uncomfortable

1. **The machine's capability is larger than its declaration.** 101 operations, 36 declared effects, 11 rows
   reached. Almost every refusal on this page is a sentence the machine could have answered if the door could
   see the operation. That is a bookkeeping problem whose fix is a generator, not a research problem.
2. **There is exactly one false pass, and it is a dropped argument.** Measured: a sentence that states `HEAD~1`
   against a repository whose `HEAD~1` diff is one hunk returns **an empty row set** and
   `PASS__..._EXECUTED_AND_VERIFIED`. The census scores it as served. It is cheap to fix (§9 item 4) and it is
   the most dangerous line on this page, because a false pass is worth less than a refusal.
3. **The instrument that could catch all of this has no floor.** The 54-case matrix has world oracles and no gate;
   the suite has 2,248 modules and no sitting long enough to finish it. Every improvement in §9 without item 10
   will regress silently within a week.

---

## Appendix A — the exact commands

```
python3 execution_guard/swe_advanced_probe_v1.py --floor 5 --json /tmp/adv.json
python3 execution_guard/swe_capability_matrix_v1.py --json > /tmp/mat.json
python3 hardcore_swe_surface_probe_20261030.py --jobs 6 --json /tmp/surf.json
python3 scripts/restore_substrate_v1.py --check       # substrate verdict, no install
```

## Appendix B — the ten matrix refusals, verbatim

| case | goal |
|---|---|
| `extract_function` | Extract the body of add in canonical/astra_runtime/tmp/frontier_matrix/extract_function/pkg/mod.py into a helper functi… |
| `extract_constant` | Replace the magic number 3 in canonical/astra_runtime/tmp/frontier_matrix/extract_constant/pkg/calc.py with a named con… |
| `tests_from_docstrings` | Generate tests from the docstrings in canonical/astra_runtime/tmp/frontier_matrix/tests_from_docstrings/pkg/mod.py. |
| `find_definition` | Where is the function mul defined? |
| `git_branch` | Create a branch named feature/x. |
| `missing_source` | fix canonical/astra_runtime/tmp/frontier_matrix/missing_source/pkg/missing.py |
| `ambiguous_fix_it` | fix it |
| `bisect_regression` | Bisect the regression that broke the test in canonical/astra_runtime/tmp/frontier_matrix/bisect_regression/pkg/test_cal… |
| `delete_file` | Delete canonical/astra_runtime/tmp/frontier_matrix/delete_file/pkg/legacy.py. |
| `idempotent_refusal` | fix it |

## Appendix C — how every number in this document was produced

| number | source |
|---|---|
| 36 / 49, 13 refusals, per-axis counts, median | `execution_guard/swe_advanced_probe_v1.py --json` on this tree |
| 44 / 54, 0 false, 0 damaged | `execution_guard/swe_capability_matrix_v1.py --json`, substrate restored |
| 42 / 54 before the restore | the same command before `restore_substrate_v1.py`, same tree |
| 28 / 28 | `hardcore_swe_surface_probe_20261030.py` |
| 443 rows, 566 effects, 11 reached | `load_verified_registry()` plus the census `selected` column |
| 101 operations / 36 effects | static scan of the five adapters' `op ==` / `op in` dispatch tables |
| direct-call results | the five `run(...)` calls recorded in §2.1 |
| 2,248 test modules | `len(glob('canonical/tests/test_*.py'))` |
| 323 workflows | `len(glob('.github/workflows/*.yml'))` |

