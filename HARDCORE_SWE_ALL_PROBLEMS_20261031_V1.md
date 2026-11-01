# Every hardcore software-engineering problem, measured

Measured 2026-10-31 on main `5ad1222` with the substrate restored (`scripts/restore_substrate_v1.py`).
Supersedes the first edition of this same document (`43676be`); `HARDCORE_SWE_PROBLEM_INVENTORY_20261031_V19.md`
records one round of repairs; this document is the whole problem list, ordered so that the next
hour of work buys the most capability. Nothing here is a wish — every number is a measurement
taken by this run (`execution_guard/swe_advanced_probe_v1.py`, `execution_guard/swe_capability_matrix_v1.py`,
the live verified registry, and a probe of the substrate).

---

## §0 The answer in one paragraph

The brain answers **4 of 49** advanced software-engineering sentences and **23 of 54** capability cases for real (no FALSE rows, no DAMAGED). That gap is not a shortage of theory and it is
not a shortage of verification machinery — the tree has 440 registry rows and the strongest
fail-closed answer gate it has ever had. The gap is three separate things, in this order:

1. **Plumbing defects stop a sentence from reaching a row that already exists** (45 refusals split across 8 failure classes below). One row alone absorbs **8** of the 49 sentences and fails on every one.
2. **The substrate evaporates, and the machine is single-language.** It is Python-only by
   construction, and this image currently holds **17 of the 36 tools** an advanced
   engineer works with. Restoring it is one command and it buys real capability — measured
   this round: `python3 scripts/restore_substrate_v1.py` took the matrix from 22 to 23 REAL
   and the census from 3 to 4 served, with no row changed — so part of what looked like a
   capability gap was an install step nobody ran.
3. **Whole capability classes have no row at all** — build systems, CI, design/architecture, git
   operations, concurrency. Those are not defects; they are absences, and no amount of routing work
   makes them answer.

---

## §1 The measured surface

| instrument | result |
|---|---|
| advanced census (49 hardcore sentences) | **4 served / 45 refused** |
| capability matrix (54 cases) | **23 REAL / 0 FALSE / 0 DAMAGED** (false: `-`, damaged: `-`) |
| matrix latency | median 64 ms  p90 427 ms  max 2790 ms |
| live verified registry | 440 rows, 88 of them software-engineering rows |
| rows sourced from a PyPI package (unrunnable when absent) | 12 |
| rows whose own limitations admit they degrade silently | 23 |

The 23 rows that work for real, by name:

`fix_verb_first`, `fix_target_first`, `bug_report`, `repair_with_report`, `repair_two_modules`, `repair_test_file`, `repair_no_test_named`, `rename_param`, `rename_symbol`, `extract_stated_statement`, `dead_code`, `complexity`, `change_impact`, `count_functions`, `run_suite`, `lint`, `typecheck`, `git_diff`, `add_parameter`, `measure_coverage`, `security_review`, `mutation_score`, `perf_review`

That list is the honest capability of the machine today: **single-file Python edits** (repair,
rename, rename-parameter, add-parameter, extract, add-function), **static Python analysis**
(callers, dead code, complexity, change impact, definition count, taint), **three gates**
(security, mutation, perf review), and **running a suite**. Everything else in the inventory below
is either refused, misrouted, or absent.

---

## §2 The eleven hardcore capability classes that refuse

Ordered by how much of a real engineer's day the class covers, not by how hard it is.

| class | what it is | requests | served | why it fails |
|---|---|---|---|---|
| **refactor** | move, split module, rename across the repo, replace all uses, add type hints, extract | 6 | 2 | extract and cross-repo rename work; move, split, replace-all and type hints refuse |
| **tests** | unit, property-based, regression-from-bug, mutation-score raising, fuzzing | 6 | 1 | only running a suite and explaining failures works |
| **debug** | failing test to cause, 'why does this return None', bisect | 3 | 0 | the rows exist but are chosen wrongly or fail inside the controller |
| **perf** | profiling, optimisation, benchmark against a parent commit, memoisation | 4 | 0 | no profiler is installed, and no row answers 'which function is the hot spot' |
| **systems** | race detection, thread pools, GIL release | 3 | 0 | the only row claiming these declares them as effects it does not implement |
| **polyglot** | C++, Rust, Go, Java, TypeScript, SQL | 7 | 0 | the machine is Python-only: there is no row that edits any other language |
| **git** | commit, branch, diff, cherry-pick, changelog | 5 | 0 | no row performs a git operation; the history row is chosen for all five |
| **build** | pyproject, Makefile, dependency pinning, vendoring | 5 | 0 | no row owns the build file layer |
| **ci** | workflow repair, matrices, caching, flake quarantine | 4 | 0 | no row owns CI configuration |
| **review** | API design review, security review, dependency CVE audit | 3 | 1 | security review works; the other two have no row and no advisory data |
| **design** | ADR, migration plan, package split | 3 | 0 | no row, and no planning surface that produces a document |

### 2.1 Polyglot editing — the largest single absence

Seven of the 49 sentences name a C++, Rust, Go, Java, TypeScript or SQL file, and the machine
answers **none** of them. This is architectural, not accidental: every editing row is built on
Python's `ast`. The machine can already *read* other languages — tree-sitter is installed and four
rows use it (`code.multilanguage.parse.tree_sitter.v1`, `code.index.tree_sitter.incremental.v1`,
`code.impact.tree_sitter.testselect.v1`, `code.patch.tree_sitter.verify.v1`), covering Python,
JavaScript, TypeScript, Rust, Go, Java, C++ and YAML. So parsing, indexing, impact and patch
structure are not the gap. **The gap is that no row edits a non-Python file, and no row proves a
non-Python edit compiles** — `gcc`, `g++`, `node` and `npm` are installed but nothing drives them,
and `rustc`, `go`, `javac`, `tsc` are not installed at all. A second language substrate is therefore
two additions, not one: a tree-sitter rewrite row, and a per-language build/verify row.

### 2.2 The classes with no row at all

Build system work, CI configuration, and design/architecture have **zero** dedicated rows. A
sentence like *"Add a target `lint` to the Makefile that runs ruff"* has nothing to be routed to,
so it either compiles to nothing or is answered by the generic repair row, which then fails.

### 2.3 The class where the row claims what it does not do

`software.repair.choreograph.crossfile.v1` declares, in its own `provides`:
`software.concurrency.race.condition.fix`, `security.sql.injection.remove`,
`performance.quadratic.linearithmic.optimize`, `dependency.deprecated.inspect.migrate`,
`software.patch.crossfile.atomic`. It implements one choreography: patch, symbol graph, change
impact slice, dual-oracle verify, gate. Because it *declares* the effect, the effect gate lets it
through — so the race-condition sentence, the SQL-injection sentence and the quadratic→linearithmic
sentence are refused **late, inside the controller**, instead of early by name. Declared-but-
undeveloped effects are the most expensive class in the whole inventory: they defeat the one gate
built to catch them.

---

## §3 The plumbing defects, with counts

| defect | count | what it means | cheapest correct fix |
|---|---|---|---|
| `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | 10 | a row was chosen whose declared inputs this sentence cannot supply | extend the derivation pattern that fixed #38: derive the stated object (module, span, symbol) before binding |
| `FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED` | 9 | the chosen row does not declare the effect the sentence states (honest refusal) | none — this is the gate working; the fix is to build the missing capability, not the plumbing |
| `FAIL__LIVE_CONTROLLER_EXECUTION` | 9 | the composed chain ran and failed (missing substrate or a wrong sub-row) | make the declared dependency part of admission: a chain whose substrate is absent must refuse by name |
| `FAIL__RAW_GOAL_COMPILATION_GAP` | 8 | the sentence could not be compiled into any executable shape at all | one compiler shape per sentence family that has no template — or refuse it as NO_ROW instead of as a gap |
| `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` | 6 | the row ran and its answer was not the answer the sentence asked for | selection: the answer gate is right, the choice of row is wrong |
| `FAIL_CLOSED__CAPABILITY_REFUSED_WORKTREE_NOT_DIRECTORY` | 1 | the row's own contract refused the stated object | bind `worktree_path` from the stated file's parent, the same way #38's span was derived |
| `FAIL_CLOSED__CAPABILITY_REFUSED_NO_TESTS_DISCOVERED` | 1 | the row's own contract found nothing to measure | state the test root or refuse early; a census that finds nothing is not an answer |
| `FAIL_CLOSED__CAPABILITY_REFUSED_EDIT_PLAN_INPUT_INVALID` | 1 | the row's own contract refused the edit plan it was handed | validate the edit plan shape at admission, not inside the adapter |

### 3.1 The magnets: five rows absorb most of the traffic

| row | requests it absorbs | verdicts |
|---|---|---|
| `software.repair.choreograph.crossfile.v1` | [7, 11, 13, 18, 21, 22, 23, 36] | ROUTE_ADMISSION_REJECTED x4; LIVE_CONTROLLER_EXECUTION x3; STATED_ANSWER_NOT_PROVIDED x1 |
| `python.tests.mutation_score.v1` | [1, 14, 16, 30] | STATED_SWE_EFFECT_UNSERVED x1; ROUTE_ADMISSION_REJECTED x1; LIVE_CONTROLLER_EXECUTION x1; STATED_ANSWER_NOT_PROVIDED x1 |
| `python.source.dead_code.v1` | [2, 17, 20, 28] | STATED_ANSWER_NOT_PROVIDED x2; STATED_SWE_EFFECT_UNSERVED x1; ROUTE_ADMISSION_REJECTED x1 |
| `python.refactor.inline_helper.v1` | [12, 33, 34, 37] | LIVE_CONTROLLER_EXECUTION x3; STATED_SWE_EFFECT_UNSERVED x1 |
| `git.history.bisect_regression.v1` | [19, 32, 43] | LIVE_CONTROLLER_EXECUTION x2; STATED_ANSWER_NOT_PROVIDED x1 |

Those 5 rows are chosen for **23 of the 49** sentences. Selection here is
trigger-word driven, and a generic row with a large trigger vocabulary wins almost every sentence.
This is the single highest-leverage defect in the inventory: fix selection and several distinct
capability classes improve at once, with no new capability code.

---

## §4 The substrate: restorable in one command, still missing real tools

| present | missing |
|---|---|
| python3, pip, gcc, g++, make, node, npm, git, pytest, hypothesis, coverage, ruff, mypy, tree_sitter, tree_sitter_languages, crosshair, z3 | sqlite3, cargo, rustc, go, javac, java, tsc, cmake, ninja, docker, gdb, valgrind, strace, perf, radon, libcst, rope, mutmut, pynguin |

`scripts/restore_substrate_v1.py` installs the hashed kernel manifest, then the review tools,
then verifies 10/10 modules, the required binaries, and the parser generation against
`tree_sitter_swe_kernel_v1.SUBSTRATE`. It exits non-zero and prints `SUBSTRATE_INCOMPLETE`
rather than letting a lane measure an environment gap and call it a capability gap.

**What the restore bought, measured this round:**

| before restore | after restore |
|---|---|
| tools 6/10, matrix 22 REAL, census 3/49 | **tools 10/10, matrix 23 REAL, census 4/49** |

The census gained request 35 (*rename the public function `total` … across the repository*) —
it had been failing for want of a tool, not a capability. `crosshair` and `z3` also became
live: `python.contract.check.crosshair.v1` now refutes a real postcondition
(`halve(n)` declared `__return__ * 2 == n` returns `CONTRACT_VIOLATION_FOUND` on odd `n`),
so symbolic contract checking is no longer dead weight in the registry.

**12 registry rows are sourced from a PyPI package or a package-shaped adapter, and
4 of them cannot run in this image**:

| package-sourced row | needs | here |
|---|---|---|
| `auto.pypi.bson-modern` | `bson` | package absent |
| `auto.pypi.msgpack` | `msgpack` | package absent |
| `code.impact.tree_sitter.testselect.v1` | `tree_sitter` | **runnable** |
| `code.index.tree_sitter.incremental.v1` | `tree_sitter` | **runnable** |
| `code.multilanguage.parse.tree_sitter.v1` | `tree_sitter` | **runnable** |
| `code.patch.tree_sitter.verify.v1` | `tree_sitter` | **runnable** |
| `math.numeric_expression.sympy` | `sympy` | package absent |
| `pdf.extract.text.pypdf` | `pypdf` | package absent |
| `python.contract.check.crosshair.v1` | `crosshair` | **runnable** |
| `python.review.diff_static_triage.v1` | `ruff` | **runnable** |
| `python.review.diff_type_gate.v1` | `mypy` | **runnable** |
| `python.software.issue_to_pr.orchestrate.v1` | `in-tree` | **runnable** |

* **No profiler, no debugger, no `valgrind`, no `strace`, no `gdb`.** Profiling, race
  detection and "find the commit that broke this" are requests about *execution*, and nothing
  here watches an execution.
* **No `rustc`, `cargo`, `go`, `javac`, `tsc`, `sqlite3`.** Five of the six languages the census
  asks about cannot be compiled here even if a row existed. `gcc`, `g++`, `node`, `npm` and
  `make` are present but no row drives them.
* **The substrate does not persist.** pip installs outside `/home/user` evaporate between
  turns; this document is the first that names the restore as a step rather than a hope.

---

## §5 Structural gaps the census cannot see

These matter more than any single refusal, and none of them is measured by a 49-sentence census:

1. **No long-horizon loop that survives.** Plans exist, chains exist, and 10 of 10 executed chains
   fail. There is no demonstrated plan → edit → run → observe → repair cycle on a real repository.
2. **No execution feedback.** The machine mostly reasons statically. It does not routinely run the
   code it changed and read what happened — the one thing a strong engineer does constantly.
3. **No repo-scale navigation.** A symbol index exists, but there is no ranked cross-module
   retrieval, no "where is this behaviour implemented", no impact ranking that a planner can use.
4. **No learning from its own refusals.** Each round re-derives the refusal taxonomy by hand. The
   refusal corpus is not mined automatically into candidate rows.
5. **Single-language is architectural** (Python `ast` everywhere), so polyglot support is not a row
   addition, it is a second substrate.
6. **The census measures the environment as much as the machine.** 4 of the 49 sentences turn
   on which packages happen to be installed, and the matrix prints `unmeasurable lanes` but
   does not fail. A number that moves when a pip cache is cold is not a capability number.
7. **The matrix is not deterministic.** Seven consecutive runs on one unchanged tree gave
   22 REAL once and 23 REAL six times, with the printed REAL list identical every time. A
   number that moves on an unchanged tree cannot be regressed against, so the floor the
   census workflow enforces is measuring partly the machine's mood.
8. **At least one census sentence is ill-posed.** Request 33 says *move the function `add`
   from mod.py into calc.py*, and both files define `add`, so the move collides and the
   refusal is CORRECT. The ambiguity rule caught it (it declined to pick a symbol whose
   definition is not unique across the stated files). A denominator that counts that
   sentence as a capability the machine lacks overstates the gap.
9. **Lane isolation is broken.** Running the matrix `--lane toolchain` alone reports
   `add_dependency` FALSE **and** DAMAGED, while the full run reports the same case refused with
   a clean tree. The single-lane fixture lacks the shared setup the case depends on, so every
   lane-only number is suspect until the fixture is shared.
10. **Measurement breadth.** 49 sentences written by the same hand that writes the rows. Real
   software engineering is unbounded, so this corpus can be satisfied without being a good engineer.
   It needs real repositories and adversarial sentences, not more fixtures.

---

## §6 The order to fix it in

Ranked by capability bought per hour, using the counts above as the estimate of reach.

| # | move | reaches | why first |
|---|---|---|---|
| 1 | typed selection keyed on the stated effect and object, replacing trigger-word magnets | **23/49** | no new capability code; several classes improve at once |
| 2 | declare the substrate contract per row and refuse early when it is absent | 9 chains + 12 pypi rows | turns silent controller death into a named, actionable refusal |
| 3 | extend the #38 derivation pattern to the stated object of every family | 10 | proven once, cheap to repeat |
| 4 | install the work substrate (pytest, hypothesis, ruff, mypy, coverage, tree-sitter, a profiler) | unblocks tests/perf/review/impact | without it, several rows can never run |
| 5 | build the three absent classes: build files, CI configuration, git operations | 14 | whole classes with no row; each is mechanical and verifiable |
| 6 | execution-first debugging: run, observe, bisect, attribute | 10 | needs the substrate from 4 |
| 7 | second language substrate: a tree-sitter *edit* row and a per-language compile gate (parse/index/impact already exist) | 7 | biggest jump in what "software engineer" means; most expensive |
| 8 | design/architecture output (ADR, migration plan) | 3 | needs a planning surface that produces a document, not an edit |

---

## Appendix: all 49 sentences, classified

| # | class | sentence | chosen row | verdict |
|---|---|---|---|---|
| 1 | polyglot | Fix the off-by-one bug in …/01_polyglot/src/main.cpp so that sum returns the right total. | `python.tests.mutation_score.v1` | STATED_SWE_EFFECT_UNSERVED |
| 2 | polyglot | Add a function sub to …/02_polyglot/src/lib.rs that subtracts two integers. | `python.source.dead_code.v1` | STATED_SWE_EFFECT_UNSERVED |
| 3 | polyglot | Add a method Mul to …/03_polyglot/src/main.go that multiplies two integers. | `**none**` | RAW_GOAL_COMPILATION_GAP |
| 4 | polyglot | Add a second method to …/04_polyglot/src/Main.java and make sure it compiles. | `**none**` | RAW_GOAL_COMPILATION_GAP |
| 5 | polyglot | Rename the exported function add to plus in …/05_polyglot/src/app.ts and update its callers. | `python.source.symbols.index.ast` | STATED_SWE_EFFECT_UNSERVED |
| 6 | polyglot | Add a NOT NULL constraint on users.email in …/06_polyglot/src/schema.sql. | `decision.synthesis.typed.stdlib` | ROUTE_ADMISSION_REJECTED |
| 7 | polyglot | Repair the C++ source file …/07_polyglot/src/main.cpp so that it compiles cleanly. | `software.repair.choreograph.crossfile.v1` | LIVE_CONTROLLER_EXECUTION |
| 8 | build | Add pytest as a development dependency in …/08_build/pyproject.toml. | `**none**` | RAW_GOAL_COMPILATION_GAP |
| 9 | build | Create a pyproject.toml for the project in …/09_build/pkg with a console script entry point. | `**none**` | RAW_GOAL_COMPILATION_GAP |
| 10 | build | Add a target `lint` to …/10_build/Makefile that runs ruff over the package. | `python.review.diff_static_triage.v1` | CAPABILITY_REFUSED_WORKTREE_NOT_DIRECTORY |
| 11 | build | Pin the dependency versions in …/11_build/pyproject.toml. | `software.repair.choreograph.crossfile.v1` | ROUTE_ADMISSION_REJECTED |
| 12 | build | Vendor the single dependency of the project in …/12_build/pkg. | `python.refactor.inline_helper.v1` | LIVE_CONTROLLER_EXECUTION |
| 13 | ci | Fix the failing CI job in …/13_ci/.github/workflows/ci.yml. | `software.repair.choreograph.crossfile.v1` | LIVE_CONTROLLER_EXECUTION |
| 14 | ci | Make the CI workflow in …/14_ci/.github/workflows/ci.yml run the tests on Python 3.11 and 3.12. | `python.tests.mutation_score.v1` | ROUTE_ADMISSION_REJECTED |
| 15 | ci | Add caching of pip downloads to …/15_ci/.github/workflows/ci.yml. | `**none**` | RAW_GOAL_COMPILATION_GAP |
| 16 | ci | Quarantine the flaky test in …/16_ci/tests/test_calc.py so CI is green. | `python.tests.mutation_score.v1` | LIVE_CONTROLLER_EXECUTION |
| 17 | perf | Profile …/17_perf/pkg/util.py and tell me which function is the hot spot. | `python.source.dead_code.v1` | STATED_ANSWER_NOT_PROVIDED |
| 18 | perf | Optimise the function total in …/18_perf/pkg/util.py; it is too slow on large inputs. | `software.repair.choreograph.crossfile.v1` | ROUTE_ADMISSION_REJECTED |
| 19 | perf | Benchmark …/19_perf/pkg/calc.py against the version in git HEAD~1. | `git.history.bisect_regression.v1` | LIVE_CONTROLLER_EXECUTION |
| 20 | perf | Add memoisation to the function twice in …/20_perf/pkg/mod.py. | `python.source.dead_code.v1` | ROUTE_ADMISSION_REJECTED |
| 21 | systems | Find the race condition in …/21_systems/pkg/service.py. | `software.repair.choreograph.crossfile.v1` | STATED_ANSWER_NOT_PROVIDED |
| 22 | systems | Add a thread pool to …/22_systems/pkg/util.py that totals the list in parallel. | `software.repair.choreograph.crossfile.v1` | ROUTE_ADMISSION_REJECTED |
| 23 | systems | Make the function total in …/23_systems/pkg/util.py release the GIL while summing. | `software.repair.choreograph.crossfile.v1` | ROUTE_ADMISSION_REJECTED |
| 24 | tests | Write a unit test for the function mul in …/24_tests/pkg/calc.py. | `python.tests.audit.unittest` | ROUTE_ADMISSION_REJECTED |
| 25 | tests | Write a property-based test for the function add in …/25_tests/pkg/calc.py. | `code.impact.tree_sitter.testselect.v1` | ROUTE_ADMISSION_REJECTED |
| 26 | tests | Add a regression test that reproduces the bug in …/26_tests/pkg/mod.py. | `python.patch.search.test_guided.ast.v1` | STATED_SWE_EFFECT_UNSERVED |
| 27 | tests | Increase the mutation score of …/27_tests/pkg/calc.py above 0.8 by adding tests. | `python.review.diff_mutation_gate.v1` | CAPABILITY_REFUSED_NO_TESTS_DISCOVERED |
| 28 | tests | Fuzz the function add in …/28_tests/pkg/calc.py for integer overflow. | `python.source.dead_code.v1` | STATED_ANSWER_NOT_PROVIDED |
| 29 | tests | Run the test suite in …/29_tests/tests and tell me which tests fail and why. | `python.repository.acceptance.measure.v1` | SERVED |
| 30 | debug | The test in …/30_debug/tests/test_calc.py fails; find the root cause. | `python.tests.mutation_score.v1` | STATED_ANSWER_NOT_PROVIDED |
| 31 | debug | Explain why the function total in …/31_debug/pkg/util.py returns None for empty input. | `python.source.taint_flow.v1` | STATED_ANSWER_NOT_PROVIDED |
| 32 | debug | Find the commit that broke the test in …/32_debug/tests/test_calc.py. | `git.history.bisect_regression.v1` | STATED_ANSWER_NOT_PROVIDED |
| 33 | refactor | Move the function add from …/33_refactor/pkg/mod.py into …/33_refactor/pkg/calc.py and update every caller. | `python.refactor.inline_helper.v1` | STATED_SWE_EFFECT_UNSERVED |
| 34 | refactor | Split …/34_refactor/pkg/calc.py into one module per function. | `python.refactor.inline_helper.v1` | LIVE_CONTROLLER_EXECUTION |
| 35 | refactor | Rename the public function total in …/35_refactor/pkg/util.py to sum_all across the repository. | `python.refactor.rename_symbol.v1` | SERVED |
| 36 | refactor | Replace every use of the deprecated function mul in …/36_refactor/pkg with mul_v2. | `software.repair.choreograph.crossfile.v1` | LIVE_CONTROLLER_EXECUTION |
| 37 | refactor | Add type hints to every function in …/37_refactor/pkg/calc.py. | `python.refactor.inline_helper.v1` | LIVE_CONTROLLER_EXECUTION |
| 38 | refactor | Extract the loop in the function total in …/38_refactor/pkg/util.py into a helper. | `python.refactor.extract_function.v1` | SERVED |
| 39 | review | Review …/39_review/pkg/service.py for API design problems. | `python.source.secret_scan.v1` | STATED_SWE_EFFECT_UNSERVED |
| 40 | review | Review …/40_review/pkg/calc.py for security issues. | `python.review.diff_security_gate.v1` | SERVED |
| 41 | review | Audit the dependency list in …/41_review/pyproject.toml for known vulnerabilities. | `**none**` | STATED_SWE_EFFECT_UNSERVED |
| 42 | git | Commit the changes in …/42_git/pkg with a clear message. | `git.repository.operate.v1` | ROUTE_ADMISSION_REJECTED |
| 43 | git | Create a branch named feature/x and commit …/43_git/pkg/calc.py there. | `git.history.bisect_regression.v1` | LIVE_CONTROLLER_EXECUTION |
| 44 | git | Show me the diff of …/44_git/pkg/calc.py against HEAD~1. | `**none**` | RAW_GOAL_COMPILATION_GAP |
| 45 | git | Cherry-pick the last commit onto a new branch. | `**none**` | STATED_SWE_EFFECT_UNSERVED |
| 46 | git | Write the changelog entry for the last three commits. | `**none**` | STATED_SWE_EFFECT_UNSERVED |
| 47 | design | Design the API for a rate limiter and write an ADR. | `**none**` | RAW_GOAL_COMPILATION_GAP |
| 48 | design | Plan the migration of the package in …/48_design/pkg from Python 3.9 to 3.12. | `python.source.crossfile_edit.choreograph.v1` | CAPABILITY_REFUSED_EDIT_PLAN_INPUT_INVALID |
| 49 | design | Write a design document for splitting …/49_design/pkg into two packages. | `**none**` | RAW_GOAL_COMPILATION_GAP |

---

## What this document is not

It is not a plan to make the machine *seem* more capable. Every item above is either a measured
refusal, a measured absence in the substrate, or a measured selection error. Nothing in it is
softened: the machine answers 3 of 49 hardcore sentences, and 22 of 54 capability cases. The
value of the inventory is that the next hour of work can be spent where the reach is largest
instead of where the last refusal happened to be.
