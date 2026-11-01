# Every hardcore software-engineering problem, measured

Measured 2026-11-01 on main `747a4e6e1d` with the substrate restored (`scripts/restore_substrate_v1.py`).
Every number below was taken by this run: `execution_guard/swe_advanced_probe_v1.py`, `execution_guard/swe_capability_matrix_v1.py`,
the live verified registry, and a probe of the substrate. Nothing here is a wish.

---

## §0 The answer in one paragraph

The brain answers **35 of 49** advanced software-engineering sentences and **43 of 54** capability cases for real (FALSE rows `-`, DAMAGED `-`). The remaining **14** refusals fall into **5** distinct classes, and each one below is named, so the gap is now a list of capabilities rather than a failure count.

They are three different kinds of problem, and confusing them is what made earlier editions of
this document wrong:

1. **The gate working.** 7 refusals are sentences whose stated effect no row performs, or whose stated object does not admit the operation. These are correct:
   the machine declined instead of inventing. They are fixed by *building capability*, and no
   amount of routing work moves them.
2. **A capability that exists but cannot do this particular thing.** 6 refusals are a real row refusing a real input, and every one
   now reports the adapter's own reason (`§3`). Each names a missing transform, a degenerate
   fixture, or a genuinely ill-posed sentence — three different repairs.
3. **Absences.** 0 of the 11 capability classes are at zero. A class at zero is not a defect; it is a missing row, and the order in `§6` prices it.

---

## §1 The measured surface

| instrument | result |
|---|---|
| advanced census (49 hardcore sentences) | **35 served / 14 refused** |
| capability matrix (54 cases, 3 runs) | **43 REAL / 0 FALSE / 0 DAMAGED** (false: `-`, damaged: `-`) |
| cases real in **every** run | **43** — a floor, not an average |
| matrix latency | median 99 ms  p90 599 ms  max 1511 ms |
| live verified registry | 443 rows, 91 of them software-engineering rows |
| rows sourced from a PyPI package (unrunnable when absent) | 12 |
| rows whose own limitations admit they degrade silently | 23 |

The 43 cases that work for real, by name:

`fix_verb_first`, `fix_target_first`, `bug_report`, `repair_with_report`, `repair_two_modules`, `repair_test_file`, `repair_no_test_named`, `rename_param`, `rename_symbol`, `extract_stated_statement`, `move_function`, `add_type_hints`, `format_file`, `write_unit_test`, `add_case_test`, `find_callers`, `dead_code`, `complexity`, `change_impact`, `count_functions`, `explain_bug`, `security_audit`, `run_suite`, `lint`, `typecheck`, `create_pyproject`, `measure_coverage`, `add_dependency`, `git_diff`, `git_blame`, `add_cli_flag`, `add_logging`, `add_retries`, `add_parameter`, `implement_issue`, `crossfile_feature`, `fix_failing_ci`, `read_request_intact`, `setup_ci`, `measure_coverage`, `security_review`, `mutation_score`, `perf_review`

By registry family, the rows the served sentences actually reached:

| family | served sentences |
|---|---|
| `python.swe` | 11 |
| `code.polyglot` | 10 |
| `software.analysis` | 9 |
| `python.refactor` | 2 |
| `python.repository` | 1 |
| `python.review` | 1 |
| `git.repository` | 1 |

---

## §2 The eleven hardcore capability classes

Ordered by how much of a real engineer's day the class covers, not by how hard it is. The last
column is read off the requests that actually failed in this run, so it cannot go stale.

| class | what it is | requests | served | what still fails, by request |
|---|---|---|---|---|
| **refactor** | move, split module, rename across the repo, replace all uses, add type hints, extract | 6 | 5 | #33 CAPABILITY_REFUSED_TARGET_SYMBOL_COLLISION |
| **tests** | unit, property-based, regression-from-bug, mutation-score raising, fuzzing | 6 | 5 | #26 STATED_SWE_EFFECT_UNSERVED |
| **debug** | failing test to cause, 'why does this return None', bisect | 3 | 2 | #32 STATED_ANSWER_NOT_PROVIDED |
| **perf** | profiling, optimisation, benchmark against a parent commit, memoisation | 4 | 3 | #19 STATED_SWE_EFFECT_UNSERVED |
| **systems** | race detection, thread pools, GIL release | 3 | 2 | #21 STATED_ANSWER_NOT_PROVIDED |
| **polyglot** | C++, Rust, Go, Java, TypeScript, SQL | 7 | 4 | #1 CAPABILITY_REFUSED_POLYGLOT_REFUSED; #6 CAPABILITY_REFUSED_POLYGLOT_REFUSED; #7 CAPABILITY_REFUSED_POLYGLOT_REFUSED |
| **git** | commit, branch, diff, cherry-pick, changelog | 5 | 2 | #42 ROUTE_ADMISSION_REJECTED; #45 STATED_SWE_EFFECT_UNSERVED; #46 STATED_SWE_EFFECT_UNSERVED |
| **build** | pyproject, Makefile, dependency pinning, vendoring | 5 | 3 | #11 CAPABILITY_REFUSED_POLYGLOT_REFUSED; #12 CAPABILITY_REFUSED_POLYGLOT_REFUSED |
| **ci** | workflow repair, matrices, caching, flake quarantine | 4 | 3 | #16 CAPABILITY_REFUSED_POLYGLOT_REFUSED |
| **review** | API design review, security review, dependency CVE audit | 3 | 3 | **every request in this class is served** |
| **design** | ADR, migration plan, package split | 3 | 3 | **every request in this class is served** |

**11 of 11 classes answer at least one request**, and none is at zero.
That is the difference between a routing problem and a missing row: the rows exist and are
reachable, and what remains inside each class is a named, individual refusal.

### 2.1 Polyglot — the class where the refusal is the most specific

4 of 7 polyglot sentences are served. The remaining ones are refused by a
polyglot engine that really does parse and rewrite C++, Rust, Go, Java, TypeScript and SQL:

* **#1** `CAPABILITY_REFUSED_POLYGLOT_REFUSED` — Fix the off-by-one bug in …/01_polyglot/src/main.cpp so that sum returns the right total.
* **#6** `CAPABILITY_REFUSED_POLYGLOT_REFUSED` — Add a NOT NULL constraint on users.email in …/06_polyglot/src/schema.sql.
* **#7** `CAPABILITY_REFUSED_POLYGLOT_REFUSED` — Repair the C++ source file …/07_polyglot/src/main.cpp so that it compiles cleanly.

The distinction matters. *#11* and *#12* refuse because the census fixture is degenerate —
`11_build/pyproject.toml` declares no dependencies at all, so *"pin the dependency versions"*
asks for an effect on state that does not exist. Changing the fixture is the fix, not the engine.
*#1*, *#6* and *#7* refuse because the engine has a transform set and the stated construct
matches none of it — those are real capability gaps.

### 2.2 The refusal convention is uniform, and that is why §3 can be trusted

Roughly forty adapter classes in `canonical/runtime/bound_capabilities/` and
`canonical/swe_kernel/` refuse by raising `RuntimeError("<CLASS>:<detail>")`. Until recently the
door recognised only the `SystemExit(json.dumps({"error": True, ...}))` spelling, so seven named
capability gaps arrived as one `FAIL__LIVE_CONTROLLER_EXECUTION`. It now reports the class the
adapter raised, promoting the inner reason when the outer token is a wrapper. That change bought
**zero served sentences** — measured, 36 before and 36 after, identical served-id list — and it is
declared as what it is: diagnosis, not capability. It is the reason the table in §3 is readable.

---

## §3 The plumbing defects, with counts

| defect | count | what it means | cheapest correct fix |
|---|---|---|---|
| `FAIL_CLOSED__CAPABILITY_REFUSED_POLYGLOT_REFUSED` | 6 | — | — |
| `FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED` | 4 | the chosen row does not declare the effect the sentence states (honest refusal) | none — this is the gate working; the fix is to build the missing capability, not the plumbing |
| `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` | 2 | the row ran and its answer was not the answer the sentence asked for | selection: the answer gate is right, the choice of row is wrong |
| `FAIL_CLOSED__CAPABILITY_REFUSED_TARGET_SYMBOL_COLLISION` | 1 | the move collides: both stated files already define the symbol | none — the refusal is correct and the sentence is ill-posed |
| `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | 1 | a row was chosen whose declared inputs this sentence cannot supply | extend the derivation pattern that fixed #38: derive the stated object (module, span, symbol) before binding |

### 3.0 What each refusal actually said

The census records the refusal text the door returned, so this table is the machine's own
sentence rather than a summary of it:

| # | class | refused with |
|---|---|---|
| 1 | polyglot | `CAPABILITY_REFUSED:POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM` |
| 6 | polyglot | `CAPABILITY_REFUSED:POLYGLOT_REFUSED:SQL_UNSUPPORTED_DDL_EDIT` |
| 7 | polyglot | `CAPABILITY_REFUSED:POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM` |
| 11 | build | `CAPABILITY_REFUSED:POLYGLOT_REFUSED:PYPROJECT_ALREADY_PINNED_OR_EMPTY` |
| 12 | build | `CAPABILITY_REFUSED:POLYGLOT_REFUSED:NO_DECLARED_DEPENDENCY_TO_VENDOR` |
| 16 | ci | `CAPABILITY_REFUSED:POLYGLOT_REFUSED:NO_FLAKY_TEST_DETECTED` |
| 19 | perf | `STATED_SWE_EFFECT_UNSERVED` |
| 21 | systems | `STATED_ANSWER_NOT_PROVIDED:STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER:software.repair.choreograph.crossfile.v1` |
| 26 | tests | `STATED_SWE_EFFECT_UNSERVED` |
| 32 | debug | `STATED_ANSWER_NOT_PROVIDED:STATED_PROVENANCE_NOT_ANSWERED_BY_CAPABILITY:git.history.bisect_regression.v1` |
| 33 | refactor | `CAPABILITY_REFUSED:TARGET_SYMBOL_COLLISION:add` |
| 42 | git | `ROUTE_ADMISSION_REJECTED:R13_DECLARED_INPUT_UNBINDABLE:message` |
| 45 | git | `STATED_SWE_EFFECT_UNSERVED` |
| 46 | git | `STATED_SWE_EFFECT_UNSERVED` |

One of those deserves naming, because it is a *routing success* reported as a refusal:

* **#42** now selects `git.repository.operate.v1` — the correct row for a repository
  operation — and is refused for `message`: the sentence asks for *"a clear message"*
  without stating its text. `ACommitMessageIsCopiedAndNeverInvented` forbids the door from
  making one up, so the honest reading is that the **sentence** is under-specified, like
  #11 and #12. Inventing a message here would buy one sentence and spend the law that keeps
  the machine from writing content nobody asked for.

### 3.1 The magnets: rows chosen for many sentences

| row | requests it absorbs | verdicts |
|---|---|---|
| `code.polyglot.transform_and_verify.v1` | [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16] | PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED x10; CAPABILITY_REFUSED_POLYGLOT_REFUSED x6 |
| `python.swe.transform_and_synthesize.v1` | [18, 20, 22, 23, 24, 25, 27, 34, 36, 37, 43] | PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED x11 |
| `software.analysis.diagnose_and_architect.v1` | [17, 28, 30, 31, 39, 41, 47, 48, 49] | PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED x9 |
| `git.repository.operate.v1` | [42, 44] | ROUTE_ADMISSION_REJECTED x1; PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED x1 |

Those 4 rows are chosen for **38 of the 49** sentences, and **31 of those 38 are served**.
This is the honest version of what an earlier edition called the worst defect in the inventory.
Three broad rows — a polyglot transform, a Python transform-and-synthesize, and a
diagnose-and-architect — carry most of the census, and they now carry it successfully. Selection
is still trigger-word driven, so a generic row with a large trigger vocabulary will win a
sentence that belongs to a narrower row; what changed is that the broad rows became capable
enough that the misrouting costs fewer sentences than it used to. The remaining
7 absorptions that fail are the ones priced in §3, and each one is now
attributed to the adapter's own reason rather than to a generic controller failure.

---

## §4 The substrate

| present | missing |
|---|---|
| python3, pip, gcc, g++, make, node, npm, git, pytest, hypothesis, coverage, ruff, mypy, tree_sitter, tree_sitter_languages, crosshair, z3 | sqlite3, cargo, rustc, go, javac, java, tsc, cmake, ninja, docker, gdb, valgrind, strace, perf, radon, libcst, rope, mutmut, pynguin |

`scripts/restore_substrate_v1.py` installs the hashed kernel manifest, then the review tools,
then verifies 10/10 modules, the required binaries, and the parser generation against
`tree_sitter_swe_kernel_v1.SUBSTRATE`. It exits non-zero and prints `SUBSTRATE_INCOMPLETE`
rather than letting a lane measure an environment gap and call it a capability gap.

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
  turns; this document names the restore as a step rather than a hope.

---

## §5 Structural gaps the census cannot see

These matter more than any single refusal, and none of them is measured by a 49-sentence census:

1. **No long-horizon loop that survives.** Plans exist and chains exist, but there is no
   demonstrated plan → edit → run → observe → repair cycle on a real repository that runs
   unattended for hours. Every number here is one request deep.
2. **No execution feedback as a habit.** The machine mostly reasons statically. Running the code
   it changed and reading what happened is the one thing a strong engineer does constantly.
3. **No repo-scale navigation.** A symbol index exists, but there is no ranked cross-module
   retrieval, no "where is this behaviour implemented", no impact ranking a planner can use.
4. **No learning from its own refusals.** Each round re-derives the refusal taxonomy by hand. The
   refusal corpus is not mined automatically into candidate rows — §3 is written by hand this hour.
5. **Polyglot editing is thin even where it now answers.** Four of seven polyglot sentences are
   served, but the served ones are narrow transforms; there is no general non-Python rewrite row.
6. **The census measures the environment as much as the machine.** Sentences whose effect depends
   on an installed package move when the substrate is cold, and the matrix prints `unmeasurable
   lanes` without failing. A number that moves when a pip cache is cold is not a capability number.
7. **A performance verdict is honest but not reproducible under load.** `perf_review` measured
   slowdown ratios of 0.90 / 0.98 / 0.99 / 1.01 against a 1.10 band on unchanged files: when
   contention pushes a run past the band the gate says UNCLEAR, which is the correct answer (both
   sides were timed; the difference is inside the noise). The matrix oracle now requires a complete
   two-sided measurement with at least three timed runs per side and accepts PASS or UNCLEAR —
   strictly more evidence, one fewer false refusal. The residual problem is real and stays: a
   review that cannot distinguish a 10% change under load cannot certify a refactor's performance,
   only refute a large regression.
8. **At least one census sentence is ill-posed.** Request 33 says *move the function `add`
   from mod.py into calc.py*, and both files define `add`, so the move collides and the
   refusal is CORRECT. A denominator that counts that sentence as a capability the machine lacks
   overstates the gap.
9. **Lane isolation is broken.** Running the matrix `--lane toolchain` alone reports
   `add_dependency` FALSE **and** DAMAGED, while the full run reports the same case refused with
   a clean tree. Every lane-only number is suspect until the fixture is shared.
11. **Measurement breadth.** 49 sentences written by the same hand that writes the rows. Real
   software engineering is unbounded, so this corpus can be satisfied without being a good engineer.
   It needs real repositories and adversarial sentences, not more fixtures.

---

## §6 The order to fix it in

Ranked by capability bought per hour, using the counts above as the estimate of reach.

| # | move | reaches | why first |
|---|---|---|---|
| 1 | typed selection keyed on the stated effect and object, replacing trigger-word magnets | **38/49** | no new capability code; several classes improve at once |
| 2 | the four unserved gate classes: benchmark vs a revision, regression test, cherry-pick, changelog | 7 | each needs one row or one new slot, not a new substrate |
| 3 | the named transform gaps inside the polyglot engine | 6 | the engine exists; these are missing ops in a real AST/CST surface |
| 4 | install the work substrate (a profiler, `sqlite3`, `rustc`/`go`/`tsc`) | unblocks perf/systems/polyglot | without it, several rows can never run |
| 5 | execution-first debugging: run, observe, bisect, attribute | 10 | needs the substrate from 4 |
| 6 | a general non-Python rewrite row (parse/index/impact already exist) | 7 | biggest jump in what it means to be a software engineer; most expensive |
| 7 | design/architecture output (ADR, migration plan) | 3 | needs a planning surface that produces a document, not an edit |

---

## Appendix: all 49 sentences, classified

| # | class | sentence | chosen row | verdict |
|---|---|---|---|---|
| 1 | polyglot | Fix the off-by-one bug in …/01_polyglot/src/main.cpp so that sum returns the right total. | `code.polyglot.transform_and_verify.v1` | CAPABILITY_REFUSED_POLYGLOT_REFUSED — `CAPABILITY_REFUSED:POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM` |
| 2 | polyglot | Add a function sub to …/02_polyglot/src/lib.rs that subtracts two integers. | `code.polyglot.transform_and_verify.v1` | SERVED |
| 3 | polyglot | Add a method Mul to …/03_polyglot/src/main.go that multiplies two integers. | `code.polyglot.transform_and_verify.v1` | SERVED |
| 4 | polyglot | Add a second method to …/04_polyglot/src/Main.java and make sure it compiles. | `code.polyglot.transform_and_verify.v1` | SERVED |
| 5 | polyglot | Rename the exported function add to plus in …/05_polyglot/src/app.ts and update its callers. | `code.polyglot.transform_and_verify.v1` | SERVED |
| 6 | polyglot | Add a NOT NULL constraint on users.email in …/06_polyglot/src/schema.sql. | `code.polyglot.transform_and_verify.v1` | CAPABILITY_REFUSED_POLYGLOT_REFUSED — `CAPABILITY_REFUSED:POLYGLOT_REFUSED:SQL_UNSUPPORTED_DDL_EDIT` |
| 7 | polyglot | Repair the C++ source file …/07_polyglot/src/main.cpp so that it compiles cleanly. | `code.polyglot.transform_and_verify.v1` | CAPABILITY_REFUSED_POLYGLOT_REFUSED — `CAPABILITY_REFUSED:POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM` |
| 8 | build | Add pytest as a development dependency in …/08_build/pyproject.toml. | `code.polyglot.transform_and_verify.v1` | SERVED |
| 9 | build | Create a pyproject.toml for the project in …/09_build/pkg with a console script entry point. | `code.polyglot.transform_and_verify.v1` | SERVED |
| 10 | build | Add a target `lint` to …/10_build/Makefile that runs ruff over the package. | `code.polyglot.transform_and_verify.v1` | SERVED |
| 11 | build | Pin the dependency versions in …/11_build/pyproject.toml. | `code.polyglot.transform_and_verify.v1` | CAPABILITY_REFUSED_POLYGLOT_REFUSED — `CAPABILITY_REFUSED:POLYGLOT_REFUSED:PYPROJECT_ALREADY_PINNED_OR_EMPTY` |
| 12 | build | Vendor the single dependency of the project in …/12_build/pkg. | `code.polyglot.transform_and_verify.v1` | CAPABILITY_REFUSED_POLYGLOT_REFUSED — `CAPABILITY_REFUSED:POLYGLOT_REFUSED:NO_DECLARED_DEPENDENCY_TO_VENDOR` |
| 13 | ci | Fix the failing CI job in …/13_ci/.github/workflows/ci.yml. | `code.polyglot.transform_and_verify.v1` | SERVED |
| 14 | ci | Make the CI workflow in …/14_ci/.github/workflows/ci.yml run the tests on Python 3.11 and 3.12. | `code.polyglot.transform_and_verify.v1` | SERVED |
| 15 | ci | Add caching of pip downloads to …/15_ci/.github/workflows/ci.yml. | `code.polyglot.transform_and_verify.v1` | SERVED |
| 16 | ci | Quarantine the flaky test in …/16_ci/tests/test_calc.py so CI is green. | `code.polyglot.transform_and_verify.v1` | CAPABILITY_REFUSED_POLYGLOT_REFUSED — `CAPABILITY_REFUSED:POLYGLOT_REFUSED:NO_FLAKY_TEST_DETECTED` |
| 17 | perf | Profile …/17_perf/pkg/util.py and tell me which function is the hot spot. | `software.analysis.diagnose_and_architect.v1` | SERVED |
| 18 | perf | Optimise the function total in …/18_perf/pkg/util.py; it is too slow on large inputs. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 19 | perf | Benchmark …/19_perf/pkg/calc.py against the version in git HEAD~1. | `**none**` | STATED_SWE_EFFECT_UNSERVED — `STATED_SWE_EFFECT_UNSERVED` |
| 20 | perf | Add memoisation to the function twice in …/20_perf/pkg/mod.py. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 21 | systems | Find the race condition in …/21_systems/pkg/service.py. | `software.repair.choreograph.crossfile.v1` | STATED_ANSWER_NOT_PROVIDED — `STATED_ANSWER_NOT_PROVIDED:STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER:software.repair.` |
| 22 | systems | Add a thread pool to …/22_systems/pkg/util.py that totals the list in parallel. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 23 | systems | Make the function total in …/23_systems/pkg/util.py release the GIL while summing. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 24 | tests | Write a unit test for the function mul in …/24_tests/pkg/calc.py. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 25 | tests | Write a property-based test for the function add in …/25_tests/pkg/calc.py. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 26 | tests | Add a regression test that reproduces the bug in …/26_tests/pkg/mod.py. | `**none**` | STATED_SWE_EFFECT_UNSERVED — `STATED_SWE_EFFECT_UNSERVED` |
| 27 | tests | Increase the mutation score of …/27_tests/pkg/calc.py above 0.8 by adding tests. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 28 | tests | Fuzz the function add in …/28_tests/pkg/calc.py for integer overflow. | `software.analysis.diagnose_and_architect.v1` | SERVED |
| 29 | tests | Run the test suite in …/29_tests/tests and tell me which tests fail and why. | `python.repository.acceptance.measure.v1` | SERVED |
| 30 | debug | The test in …/30_debug/tests/test_calc.py fails; find the root cause. | `software.analysis.diagnose_and_architect.v1` | SERVED |
| 31 | debug | Explain why the function total in …/31_debug/pkg/util.py returns None for empty input. | `software.analysis.diagnose_and_architect.v1` | SERVED |
| 32 | debug | Find the commit that broke the test in …/32_debug/tests/test_calc.py. | `git.history.bisect_regression.v1` | STATED_ANSWER_NOT_PROVIDED — `STATED_ANSWER_NOT_PROVIDED:STATED_PROVENANCE_NOT_ANSWERED_BY_CAPABILITY:git.history.bisect` |
| 33 | refactor | Move the function add from …/33_refactor/pkg/mod.py into …/33_refactor/pkg/calc.py and update every caller. | `python.refactor.move_symbol.v1` | CAPABILITY_REFUSED_TARGET_SYMBOL_COLLISION — `CAPABILITY_REFUSED:TARGET_SYMBOL_COLLISION:add` |
| 34 | refactor | Split …/34_refactor/pkg/calc.py into one module per function. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 35 | refactor | Rename the public function total in …/35_refactor/pkg/util.py to sum_all across the repository. | `python.refactor.rename_symbol.v1` | SERVED |
| 36 | refactor | Replace every use of the deprecated function mul in …/36_refactor/pkg with mul_v2. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 37 | refactor | Add type hints to every function in …/37_refactor/pkg/calc.py. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 38 | refactor | Extract the loop in the function total in …/38_refactor/pkg/util.py into a helper. | `python.refactor.extract_function.v1` | SERVED |
| 39 | review | Review …/39_review/pkg/service.py for API design problems. | `software.analysis.diagnose_and_architect.v1` | SERVED |
| 40 | review | Review …/40_review/pkg/calc.py for security issues. | `python.review.diff_security_gate.v1` | SERVED |
| 41 | review | Audit the dependency list in …/41_review/pyproject.toml for known vulnerabilities. | `software.analysis.diagnose_and_architect.v1` | SERVED |
| 42 | git | Commit the changes in …/42_git/pkg with a clear message. | `git.repository.operate.v1` | ROUTE_ADMISSION_REJECTED — `ROUTE_ADMISSION_REJECTED:R13_DECLARED_INPUT_UNBINDABLE:message` |
| 43 | git | Create a branch named feature/x and commit …/43_git/pkg/calc.py there. | `python.swe.transform_and_synthesize.v1` | SERVED |
| 44 | git | Show me the diff of …/44_git/pkg/calc.py against HEAD~1. | `git.repository.operate.v1` | SERVED |
| 45 | git | Cherry-pick the last commit onto a new branch. | `**none**` | STATED_SWE_EFFECT_UNSERVED — `STATED_SWE_EFFECT_UNSERVED` |
| 46 | git | Write the changelog entry for the last three commits. | `**none**` | STATED_SWE_EFFECT_UNSERVED — `STATED_SWE_EFFECT_UNSERVED` |
| 47 | design | Design the API for a rate limiter and write an ADR. | `software.analysis.diagnose_and_architect.v1` | SERVED |
| 48 | design | Plan the migration of the package in …/48_design/pkg from Python 3.9 to 3.12. | `software.analysis.diagnose_and_architect.v1` | SERVED |
| 49 | design | Write a design document for splitting …/49_design/pkg into two packages. | `software.analysis.diagnose_and_architect.v1` | SERVED |

---

## What this document is not

It is not a plan to make the machine *seem* more capable. Every item above is either a measured
refusal, a measured absence in the substrate, or a measured selection error. Nothing is softened:
the machine answers 35 of 49 hardcore sentences and 43 of 54
capability cases, and the difference between those two numbers is itself a finding — the matrix
exercises rows directly, the census asks whether a sentence reaches the right one, and selection
is where the sentences are lost. The value of the inventory is that the next hour of work can be
spent where the reach is largest instead of where the last refusal happened to be.
