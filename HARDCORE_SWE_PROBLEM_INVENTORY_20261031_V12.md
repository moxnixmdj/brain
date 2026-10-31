# Every hardcore-SWE problem, measured on `f333567` (V12)

Everything below is a measurement on this tree at commit `f333567`, made by two instruments:
the 54-case capability matrix (`execution_guard/swe_capability_matrix_v1.py`) and a new 49-request
advanced census (`execution_guard/swe_advanced_probe_v1.py`, added with this document). Where a
number comes from somewhere else it says so. Nothing here is a projection.

---

## 0. The answer in one paragraph

**The machine is now an honest, fast Python repair-and-audit tool, and it is not yet an advanced
software engineer.** The 54 ordinary-team-work cases are `17 REAL / 0 FALSE / 0 DAMAGED` at a 172 ms
median — that is genuinely good, and it no longer lies. The 49 advanced requests — systems languages,
build systems, CI, performance, concurrency, test authoring, git surgery, design — are `2 served /
47 refused`, and one of those two is a **wrong answer in the right shape** (`Review <f> for API design
problems` answered by a secret scanner). Of 440 registry rows, **20 distinct rows** were ever selected
across those 49 requests, five of them swallowed 24 requests and then refused their own inputs, and
**whole domains have zero rows**: C/C++, Rust, Go, Java, build/packaging, CI, concurrency, profiling,
design. The document-format wing (chart 6 + docx 4 + pdf 2 + xlsx 2 + archive 2 rows) is larger than
the systems-language wing, which is empty. So the problems are, in the order that matters: **(1) five
selection magnets and the missing effect families behind them, (2) six input-derivation holes,
(3) seven adapters that break or abort on the rows that do exist, (4) eight absent domains that are
the actual product, (5) a refusal vocabulary that cannot say what went wrong, (6) four of ten
verification tools missing so a whole lane is unmeasurable.**

---

## 1. What was measured

### 1.1 The 54-case matrix — ordinary team work

```
TOTAL 54   REAL 17   FALSE 0   REFUSED 37   DAMAGED 0
LATENCY    median 172 ms   p90 685 ms   max 1266 ms
PRECONDITIONS tools_present 6/10   tools_missing: ruff, mypy, bandit, coverage
  repair    5/7    refactor 3/8    tests 0/3    analysis 7/12
  toolchain 1/7    git      0/5    feature 1/7   honesty 0/5
```

`REAL` = the door returned `pass: true` **and** the tree shows the effect the sentence named.
`FALSE` = a pass over an unmet oracle (zero, for the first time). `DAMAGED` = a file changed that the
request did not name (zero, after the `rename_symbol` allow-list correction in this PR: the oracle
required the caller to change while the damage rule forbade it — the two could not both be right).

### 1.2 The 49-request advanced census — the actual product question

```
REQUESTS 49   SERVED 2   REFUSED 47
  polyglot 0/7   build 0/5   ci 0/4   perf 0/4   systems 0/3
  tests    1/6   debug 0/3   refactor 0/6   review 1/3   git 0/5   design 0/3
```

`SERVED` here means only "came back `pass: true` and edited nothing unnamed" — the census has no
per-request oracle, so the selected row is printed for the reader to judge. Two of the two served
requests are: `Run the test suite in <tests> and tell me which tests fail and why`
(`python.repository.acceptance.measure.v1`, correct) and `Review <f> for API design problems`
(`python.source.secret_scan.v1`, **wrong**: a secret scan is not an API-design review).

The full census is §3; the failure histogram is:

| bucket | count | what it means |
|---|---|---|
| `LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE` | 18 | a row was reached, an adapter crashed or refused, and the door's status says only that |
| `RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP` (no row at all) | 8 | nothing in the registry declares the requested effect |
| `ROUTE_ADMISSION_REJECTED:*` | 7 | the row was refused before running (right call, but see §2 S6) |
| `STATED_ANSWER_NOT_PROVIDED:*` | 5 | the row cannot supply what the sentence asked to be told |
| `NO_OBSERVED_EFFECT` | 2 | the row ran and changed nothing |
| `REVIEW_EXECUTED__VERDICT_IS_THE_ANSWER` | 1 | a review gate ran and its verdict is the finding (correct shape) |
| `TOOL_REPORTED_NON_SUCCESS` / `CAPABILITY_EXITED_PROCESS` / `CAPABILITY_REFUSED:*` | 4 | adapter-level failures with a name, no remedy |

### 1.3 Registry composition — where the capability budget actually went

440 rows in the live verified registry (`load_verified_registry()`), by measured domain scan of
ids + keywords + provides:

| domain | rows | note |
|---|---|---|
| Python source / refactor / review / tests / fault | **46** | the real capability of this machine |
| document & office formats (`chart.raster` 6, `docx.document` 4, `pdf.extract` 2, `xlsx.table` 2, archive 2) | **16** | out of scope for this product, larger than every systems domain combined |
| **C / C++ / CMake / clang** | **0** | — |
| **Rust / cargo** | **0** | — |
| **Go** | **0** | — |
| **Java / JVM / gradle / maven** | **0** | — |
| **CI authoring, build systems, packaging, lockfiles, SBOM** | **0** | — |
| **profilers / benchmark-with-baseline** | **1** (`python.review.diff_perf_gate.v1`) | a gate, not a profiler |
| **concurrency / race / async** | **0** real rows | 3 incidental `.auto.v1` rows match the words |
| git | **4** (`operate`, `bisect`, merge-conflict, one incidental) | no commit/branch/rebase/cherry-pick/changelog |
| SQL / schema | 2 real (`sqlite.table.create_from_json_records`, `...verify_against_json_records`) | no migration authoring |

### 1.4 The machine's own verification is not green

* Honest suite baseline (`canonical/verification/HONEST_SUITE_BASELINE_20261017_V1.json`, commit
  `370005ad`): **11,754 cases, 380 failed, 0 errors, 223 files with failures**, `authority: NONE`.
  That is the last full run on record; today only a focused subset was re-measured.
* Focused door subset today (8 modules, 70 tests): **8 red** — and all 8 are red on a clean
  `origin/main` worktree too, so they are inherited, not caused by this branch.
* CI's `verify-brain-unified-model-v1` job is red on `test_goal_compiler::
  test_compound_goal_compiles_full_verified_audit_pipeline`, which also fails on a clean main
  worktree (measured in `/tmp/wt-cur`).
* Tools absent here: **ruff, mypy, bandit, coverage** — 4 of 10. The entire `toolchain` lane
  (`lint`, `typecheck`, `measure_coverage`) is therefore unmeasurable, and those three refusals are an
  environment fact rather than a capability fact. A machine that cannot ship its own analysers cannot
  claim the capability they implement.

---

## 2. The problems

Master list first (ranked by capability gained per hour of work, §5 explains the ordering), then the
evidence for each class.

| ID | problem | class | evidence | reuse that already exists | size |
|---|---|---|---|---|---|
| **S1** | `python.source.dead_code.v1` swallows six unrelated change requests | selection | census 17,18,20,23,28,34 | `swe_typed_plan_v1._resolve_family` | 1 triple |
| **S2** | `python.tests.mutation_score.v1` swallows CI/test-authoring requests and parses YAML as Python | selection + adapter | census 1,14,16,27 | the same family table + a language guard the row already has | 1 triple + 1 guard |
| **S3** | `git.history.bisect_regression.v1` swallows commit/branch/diff/changelog/benchmark requests | selection + missing rows | census 19,26,32,42,43,44 | `git.repository.operate.v1` + postconditions | 1 triple + 1 binder |
| **S4** | `python.refactor.inline_helper.v1` swallows vendor/move/split/type-hint requests | selection | census 12,33,34,37 | family table | 1 triple |
| **S5** | `software.repair.choreograph.crossfile.v1` swallows deps/CI/race/replace-deprecated requests | selection | census 11,13,21,36 | family table + "composition rows are steps, not answers" mark | 1 triple + 1 flag |
| **S6** | a request in an unserved language gets a *Python* row and a dead-end refusal | selection + product | census 1,2,5,7 (`STATED_LANGUAGE_NOT_SERVED_BY_CAPABILITY:cpp/ts`) | the existing language rule; it needs a *named* refusal and a next step | small |
| **S7** | a wrong answer can be `SERVED`: API-design review answered by a secret scanner | honesty | census 39, `pass: true` | `_STATED_EFFECTS` table | 1 row |
| **D1** | `move_function` cannot derive `symbol` from "Move the function `<name>` …" | derivation | census 33 `python.refactor.move_function.v1:symbol:not_stated` (V11 §7) | `declared_input_derivation_v1` | 1 rule |
| **D2** | `source_root` is not derived when the sentence names a **file** | derivation | 6 requests: `SOURCE_ROOT_MISSING` (census 17,18,23,28,34, and 12 adjacent) | the existing `PATH_DIR_FROM_STATED_FILE_PARENT` rule | 1 rule |
| **D3** | `edits_path` receives a directory | derivation | `EDIT_PLAN_INPUT_INVALID: IsADirectoryError` (census 33/34 class) | binder refuses ambiguity already | 1 binding |
| **D4** | `worktree_path` receives a file | derivation | census 10 `CAPABILITY_REFUSED_WORKTREE_NOT_DIRECTORY` | same | 1 binding |
| **D5** | "Extract the loop in `<fn>` into a helper" never becomes a line region | derivation | census 38 `CAPABILITY_REFUSED_REGION_INVALID` | `start_line`/`end_line` derivations (V10 §3.1) | 1 rule |
| **D6** | a repository-wide rename is refused although a directory-wide rename works | derivation + scope | census 35 `ROUTE_ADMISSION_REJECTED`, matrix `rename_symbol` REAL | stated-scope derivation | small |
| **A1** | `mutation_score` raises `SyntaxError` on a YAML file | adapter | census 14 | row's own language precheck | small |
| **A2** | `mutation_score` says `NO_MUTANTS_GENERATED` / `BASELINE_TEST_SUITE_FAILED_OR_EMPTY` with no cause | adapter | census 16,27 | existing refusal vocabulary | small |
| **A3** | `inline_helper` fails with `HELPER_NAME_SURVIVED_IN` on inputs it was never meant for | adapter | census 12,37 | admission-time shape check | small |
| **A4** | the crossfile choreographer fails with `CHOREOGRAPHY_REPAIR_UNRESOLVED` **plus a traceback fragment in the reason** | adapter + diagnosis | census 36 | — | small |
| **A5** | a SQL request selects `decision.synthesis.typed.stdlib` → `DECISION_INPUT_JSON_INVALID`, while two sqlite rows exist unreached | selection | census 6 | family table | 1 triple |
| **A6** | `git.repository.operate.v1` runs and changes nothing (`NO_OBSERVED_EFFECT`) | adapter | census 45,46 | `_post_git` postconditions | small |
| **A7** | `python.source.crossfile_edit.choreograph.v1` exits the process (`SystemExit 1`) instead of refusing | adapter | census 48 | the `_systemic` convention | small |
| **M1** | **no systems-language capability at all**: C, C++, Rust, Go, Java (0 rows of 440) | product | census 1–7 | tree-sitter index already parses several; verified command runner runs `cargo`/`go`/`javac`/`cmake` | large |
| **M2** | **no build/packaging capability**: pyproject, dependency add/pin, lockfile, vendoring, Makefile target, wheel, SBOM | product | census 8–12 | command runner + YAML/TOML edit + postconditions | medium |
| **M3** | **no CI capability**: author a workflow, fix a failing job, add caching, quarantine a flaky test | product | census 13–16 | command runner, `git` rows, YAML edit | medium |
| **M4** | **no performance capability**: profile, benchmark against a recorded baseline, optimise a hot path | product | census 17–20 | `python.source.complexity`, perf gate, `cProfile` | medium |
| **M5** | **no concurrency capability**: find a race, bound a pool, make a function async, prove no deadlock | product | census 21–23 | tree-sitter + `py-spy`-class tooling | medium |
| **M6** | **no test-authoring capability reachable from a sentence**: unit, property, regression, coverage-driven, fuzz | product | census 24–28 all refused | `python.tests.generate.scaffold.v1`-class rows, `evidence.oracle.hypothesis_property.v1` | medium |
| **M7** | **git surgery missing**: commit, branch, rebase, cherry-pick, changelog, worktree | product | census 42–46, 4 rows total | `git.repository.operate.v1` + postconditions | medium |
| **M8** | **no design/planning capability**: ADR, design doc, migration plan | product | census 47–49 | the composer + document writers that already exist | medium |
| **X1** | 18 of 47 refusals say only `LIVE_CONTROLLER_EXECUTION…`; the cause lives in a free-text `reason` | diagnosis | census histogram | the refusal vocabulary already has better names | medium |
| **X2** | composition rows (choreographers, supercomposers, synthesis) are still chosen as *answers* | selection | census 5,36,48, V11 §3.2 | a "step, not an answer" flag | small |
| **X3** | a served answer can be the wrong question and nothing objects (§2 S7) | honesty | census 39 | `_STATED_EFFECTS` | medium |
| **V1** | 4 of 10 verification tools missing; the `toolchain` lane is unmeasurable | verification | matrix preconditions | declare and ship the tools | small |
| **V2** | the repository's own suite is 380/11,754 red (2026-10-17) and CI's model job is red on a test that fails on main | verification | §1.4 | the honest-baseline instrument already exists | large |
| **L1** | nothing caches a repeated request: six near-identical failure modes were each re-derived and re-run | cost | census 17,18,23,28,34 | memory/flywheel (`flywheel_v1`, `_recall_for`) is consulted but does not change selection | medium |

### 2.1 The five magnets are one problem, not five

`python.source.dead_code.v1` (6), `git.history.bisect_regression.v1` (6),
`python.tests.mutation_score.v1` (4), `software.repair.choreograph.crossfile.v1` (4),
`python.refactor.inline_helper.v1` (4) account for **24 of the 49 selections**. In every case the
sentence states an effect these rows do not have, the ranker matches on a shared word ("source",
"test", "git", "repair", "helper"), and the row then refuses its own inputs: `SOURCE_ROOT_MISSING`,
`NO_MUTANTS_GENERATED`, `NAMED_TEST_NOT_IN_GIT_HISTORY`, `HELPER_NAME_SURVIVED_IN`,
`CHOREOGRAPHY_REPAIR_UNRESOLVED`.

The mechanism that fixes this class is already in the tree and already decisive for eight families:
`canonical/runtime/swe_typed_plan_v1._resolve_family(trigger → registry terms → effect token)` — the
answering row's own id must carry the effect token, and ambiguity fails closed. The 24 wrong
destinations are **not 24 bugs**: they are the triples missing from `_FAMILIES` for
`profile / optimise / memoise / split / vendor / pin / ci / branch / commit / diff / changelog /
fuzz / property-test / type-hints / design`.

### 2.2 The derivation holes are one class too

Six of the eight no-row and eighteen of the execution failures are the same shape: **the sentence
states the datum and the binder does not read it.**

| sentence states | binder wants | measured |
|---|---|---|
| "the function `add`" | `symbol` | `symbol:not_stated` |
| a **file** to change | `source_root` (a directory) | `SOURCE_ROOT_MISSING` |
| a directory of edits | `edits_path` (a file) | `IsADirectoryError` |
| a file to edit | `worktree_path` (a directory) | `CAPABILITY_REFUSED_WORKTREE_NOT_DIRECTORY` |
| "the loop in `total`" | `start_line`/`end_line` | `REGION_INVALID` |
| "across the repository" | a scope | `ROUTE_ADMISSION_REJECTED` |

`declared_input_derivation_v1` already proves slots from stated evidence and refuses ambiguity; each
row above is one more `(stated pattern → slot → proven value)` rule in the table it keeps.

### 2.3 The absent domains are the product

The census does not say "these sentences fail"; it says **the machine has no way to do this work at
all**, and the registry scan says the same from the other side: zero rows. For the goal as stated —
the most advanced, fastest software engineer — the ordering of value is roughly:

1. **Build/packaging + CI (M2, M3)** — every real change ends in a build and a pipeline; this is the
   daily loop, and today a CI file cannot even be edited by a chosen row.
2. **Test authoring (M6)** — the machine can *measure* tests (mutation, coverage gate, acceptance)
   but cannot *write* one from a sentence; the rows that scaffold tests exist and are unreachable.
3. **Git surgery (M7)** — the machine can bisect but cannot commit; four rows total.
4. **Performance (M4) + concurrency (M5)** — the two things "fastest" is actually about, with one
   gate row and zero profilers between them.
5. **Second language (M1)** — C/C++/Rust/Go/Java are zero. The tree-sitter index and the verified
   command runner are language-agnostic already; what is missing is rows, not substrate.

---

## 3. The full advanced census (49 requests, verbatim)

| # | axis | request | verdict | selected row | cause |
|---|---|---|---|---|---|
|  1 | polyglot | Fix the off-by-one bug in `<tree>/src/main.cpp` so that sum returns the right total. | refused | `python.tests.mutation_score.v1` | STATED_ANSWER_NOT_PROVIDED |
|  2 | polyglot | Add a function sub to `<tree>/src/lib.rs` that subtracts two integers. | refused | `python.source.dead_code.v1` | ROUTE_ADMISSION_REJECTED |
|  3 | polyglot | Add a method Mul to `<tree>/src/main.go` that multiplies two integers. | refused | — no row — | RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP |
|  4 | polyglot | Add a second method to `<tree>/src/Main.java` and make sure it compiles. | refused | — no row — | RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP |
|  5 | polyglot | Rename the exported function add to plus in `<tree>/src/app.ts` and update its callers. | refused | `python.source.symbols.index.ast` | STATED_ANSWER_NOT_PROVIDED |
|  6 | polyglot | Add a NOT NULL constraint on users.email in `<tree>/src/schema.sql`. | refused | `decision.synthesis.typed.stdlib` | LIVE_CONTROLLER_EXECUTION |
|  7 | polyglot | Repair the C++ source file `<tree>/src/main.cpp` so that it compiles cleanly. | refused | `python.source.audit.ast` | STATED_ANSWER_NOT_PROVIDED |
|  8 | build | Add pytest as a development dependency in `<tree>/pyproject.toml`. | refused | — no row — | RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP |
|  9 | build | Create a pyproject.toml for the project in `<tree>/pkg` with a console script entry point. | refused | — no row — | RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP |
| 10 | build | Add a target `lint` to `<tree>/Makefile` that runs ruff over the package. | refused | `python.review.diff_static_triage.v1` | CAPABILITY_REFUSED (worktree) |
| 11 | build | Pin the dependency versions in `<tree>/pyproject.toml`. | refused | `software.repair.choreograph.crossfile.v1` | ROUTE_ADMISSION_REJECTED |
| 12 | build | Vendor the single dependency of the project in `<tree>/pkg`. | refused | `python.refactor.inline_helper.v1` | LIVE_CONTROLLER_EXECUTION |
| 13 | ci | Fix the failing CI job in `<tree>/.github/workflows/ci.yml`. | refused | `software.repair.choreograph.crossfile.v1` | STATED_ANSWER_NOT_PROVIDED |
| 14 | ci | Make the CI workflow run the tests on Python 3.11 and 3.12. | refused | `python.tests.mutation_score.v1` | LIVE_CONTROLLER_EXECUTION (`SyntaxError`) |
| 15 | ci | Add caching of pip downloads to the CI workflow. | refused | — no row — | RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP |
| 16 | ci | Quarantine the flaky test in `<tree>/tests/test_calc.py` so CI is green. | refused | `python.tests.mutation_score.v1` | LIVE_CONTROLLER_EXECUTION (`NO_MUTANTS`) |
| 17 | perf | Profile `<tree>/pkg/util.py` and tell me which function is the hot spot. | refused | `python.source.dead_code.v1` | LIVE_CONTROLLER_EXECUTION (`SOURCE_ROOT_MISSING`) |
| 18 | perf | Optimise the function total in `<tree>/pkg/util.py`; it is too slow on large inputs. | refused | `python.source.dead_code.v1` | LIVE_CONTROLLER_EXECUTION (`SOURCE_ROOT_MISSING`) |
| 19 | perf | Benchmark `<tree>/pkg/calc.py` against the version in git HEAD~1. | refused | `git.history.bisect_regression.v1` | LIVE_CONTROLLER_EXECUTION |
| 20 | perf | Add memoisation to the function twice in `<tree>/pkg/mod.py`. | refused | `python.source.dead_code.v1` | ROUTE_ADMISSION_REJECTED |
| 21 | systems | Find the race condition in `<tree>/pkg/service.py`. | refused | `software.repair.choreograph.crossfile.v1` | STATED_ANSWER_NOT_PROVIDED |
| 22 | systems | Add a thread pool to `<tree>/pkg/util.py` that totals the list in parallel. | refused | — no row — | RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP |
| 23 | systems | Make the function total release the GIL while summing. | refused | `python.source.dead_code.v1` | LIVE_CONTROLLER_EXECUTION (`SOURCE_ROOT_MISSING`) |
| 24 | tests | Write a unit test for the function mul in `<tree>/pkg/calc.py`. | refused | `python.tests.audit.unittest` | ROUTE_ADMISSION_REJECTED |
| 25 | tests | Write a property-based test for the function add in `<tree>/pkg/calc.py`. | refused | `code.impact.tree_sitter.testselect.v1` | ROUTE_ADMISSION_REJECTED |
| 26 | tests | Add a regression test that reproduces the bug in `<tree>/pkg/mod.py`. | refused | `git.history.bisect_regression.v1` | LIVE_CONTROLLER_EXECUTION |
| 27 | tests | Increase the mutation score of `<tree>/pkg/calc.py` above 0.8 by adding tests. | refused | `python.tests.mutation_score.v1` | LIVE_CONTROLLER_EXECUTION (baseline empty) |
| 28 | tests | Fuzz the function add in `<tree>/pkg/calc.py` for integer overflow. | refused | `python.source.dead_code.v1` | LIVE_CONTROLLER_EXECUTION (`SOURCE_ROOT_MISSING`) |
| 29 | tests | Run the test suite in `<tree>/tests` and tell me which tests fail and why. | **SERVED** | `python.repository.acceptance.measure.v1` | — |
| 30 | debug | The test in `<tree>/tests/test_calc.py` fails; find the root cause. | refused | `python.patch.search.test_guided.ast.v1` | TOOL_REPORTED_NON_SUCCESS |
| 31 | debug | Explain why the function total returns None for empty input. | refused | `python.fault.localize.dynamic.dataflow.v1` | ROUTE_ADMISSION_REJECTED |
| 32 | debug | Find the commit that broke the test in `<tree>/tests/test_calc.py`. | refused | `git.history.bisect_regression.v1` | STATED_ANSWER_NOT_PROVIDED |
| 33 | refactor | Move the function add from `<tree>/pkg/mod.py` into `<tree>/pkg/calc.py` and update every caller. | refused | `python.refactor.inline_helper.v1` | LIVE_CONTROLLER_EXECUTION |
| 34 | refactor | Split `<tree>/pkg/calc.py` into one module per function. | refused | `python.refactor.inline_helper.v1` | LIVE_CONTROLLER_EXECUTION |
| 35 | refactor | Rename the public function total to sum_all across the repository. | refused | `python.refactor.rename_symbol.v1` | ROUTE_ADMISSION_REJECTED |
| 36 | refactor | Replace every use of the deprecated function mul in `<tree>/pkg` with mul_v2. | refused | `software.repair.choreograph.crossfile.v1` | LIVE_CONTROLLER_EXECUTION |
| 37 | refactor | Add type hints to every function in `<tree>/pkg/calc.py`. | refused | `python.refactor.inline_helper.v1` | LIVE_CONTROLLER_EXECUTION |
| 38 | refactor | Extract the loop in the function total in `<tree>/pkg/util.py` into a helper. | refused | `python.refactor.extract_function.v1` | CAPABILITY_REFUSED (region) |
| 39 | review | Review `<tree>/pkg/service.py` for API design problems. | **SERVED (wrong answer)** | `python.source.secret_scan.v1` | — |
| 40 | review | Review `<tree>/pkg/calc.py` for security issues. | refused | `python.review.diff_security_gate.v1` | verdict is the answer (bandit absent) |
| 41 | review | Audit the dependency list in `<tree>/pyproject.toml` for known vulnerabilities. | refused | `python.source.audit.ast` | STATED_ANSWER_NOT_PROVIDED |
| 42 | git | Commit the changes in `<tree>/pkg` with a clear message. | refused | `git.history.bisect_regression.v1` | LIVE_CONTROLLER_EXECUTION |
| 43 | git | Create a branch named feature/x and commit `<tree>/pkg/calc.py` there. | refused | `git.history.bisect_regression.v1` | LIVE_CONTROLLER_EXECUTION |
| 44 | git | Show me the diff of `<tree>/pkg/calc.py` against HEAD~1. | refused | `git.history.bisect_regression.v1` | LIVE_CONTROLLER_EXECUTION |
| 45 | git | Cherry-pick the last commit onto a new branch. | refused | `git.repository.operate.v1` | NO_OBSERVED_EFFECT |
| 46 | git | Write the changelog entry for the last three commits. | refused | `git.repository.operate.v1` | NO_OBSERVED_EFFECT |
| 47 | design | Design the API for a rate limiter and write an ADR. | refused | — no row — | RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP |
| 48 | design | Plan the migration of the package in `<tree>/pkg` from Python 3.9 to 3.12. | refused | `python.source.crossfile_edit.choreograph.v1` | CAPABILITY_EXITED_PROCESS |
| 49 | design | Write a design document for splitting `<tree>/pkg` into two packages. | refused | — no row — | RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP |

---

## 4. What this means for "the most advanced software engineer"

Read as a product statement, the measurements imply four missing organs, in this order:

1. **A build/verify loop.** An engineer's unit of work is *change → build → test → fix*, and today
   the machine can do the first and the third in one language and none of the second or fourth for
   anything it did not write. M2 + M3 are that loop.
2. **Test authoring as an output, not a measurement.** The machine can score tests
   (mutation, coverage, acceptance) but cannot produce the artifact that makes the score true.
   M6 is the difference between a reviewer and an engineer.
3. **Repository operations.** The machine can bisect history but cannot commit, branch, or
   cherry-pick; M7 is the smallest, cheapest organ and it unblocks every multi-step task.
4. **A second language and a profiler.** Everything measured here is Python; "fastest" is measured by
   nothing.

Everything else on the list (S, D, A, X) is *quality of the organs it already has*, and is cheaper.

---

## 5. The order that buys the most capability per hour

1. **The five triples (S1–S5) = one edit to `swe_typed_plan_v1._FAMILIES`.** 24 of 49 advanced
   requests currently land on a magnet; the mechanism that stops it is decisive already for eight
   families. Expect: those 24 become honest *family refusals* ("no capability declares profile /
   ci / commit …") instead of wrong-row crashes — and the ones where a row does exist (type hints,
   memoise, split) reach it.
2. **The six derivation rules (D1–D6).** `symbol` from "the function `<name>`", `source_root` from a
   stated file, `edits_path` from a stated directory, `worktree_path` from a stated file, region from
   "the loop in `<fn>`", scope from "across the repository". Each is one rule in the table that
   already exists, each converts a crash into a run.
3. **The seven adapter failures (A1–A7).** Every one already has a better refusal name available;
   today the answer is a traceback in a `reason` string.
4. **Git surgery (M7) then CI (M3) then build/packaging (M2).** `git.repository.operate.v1` plus the
   `_post_git` postconditions already exist; CI and packaging are rows over the verified command
   runner and the YAML/TOML editors.
5. **Test authoring (M6).** The scaffold/property/oracle rows exist and are unreachable; making them
   the answer to "write a test for `<fn>`" is a family triple plus a promised-artifact check.
6. **Performance (M4) and concurrency (M5).** Profiler row over `cProfile`, benchmark row with a
   recorded baseline; race detection is the hardest item and should follow a working profiler.
7. **A second language (M1).** Start with the one whose toolchain is a single command (`cargo`,
   `go`, `javac`) and whose parser already exists in the tree-sitter index; do not start with C++.
8. **Diagnosis (X1–X3) and self-verification (V1–V2)** in parallel, because they make every later
   number trustworthy.

---

## 6. What is already *not* a problem (do not spend hours here)

* **Single-file Python repair** — five shapes, all REAL, all really editing, with the receipt saying
  `applied: true`.
* **Analysis** — callers, dead code, complexity, change impact, function count, and a measured
  mutation score: 7 of 12, all REAL.
* **Selection for the families that do have triples** — security, coverage, mutation, perf, extract,
  repair, type-check, callers. When a family exists, the wrong row does not win.
* **The honesty layer** — 0 FALSE and 0 DAMAGED on the matrix; the door refuses rather than lies.
* **Latency** — 172 ms median, 685 ms p90 on ordinary work; the 35 s clone class is gone.
* **Document/office formats** — they answer and they are correct; they are simply not the product.

---

## 7. Reproduction

```bash
python3 execution_guard/swe_capability_matrix_v1.py                    # 54 -> 17 / 0 / 37 / 0
python3 execution_guard/swe_advanced_probe_v1.py --json /tmp/census.json  # 49 -> 2 served
python3 canonical/runtime/verify_brain_unified_model_v1.py            # 33/33, AUTHORITY NONE
python3 -m unittest canonical.tests.test_a_review_is_not_answered_by_a_mutator_v1 \
    canonical.tests.test_a_bisect_without_a_known_good_commit_is_not_certified_v1 \
    canonical.tests.test_a_mutation_score_is_measured_not_asserted_v1 \
    canonical.tests.test_a_bisect_materialises_only_the_named_tree_v1  # 23 tests
```

*Authority: NONE — sandbox measurement on one tree at one commit, not independent verification.*
