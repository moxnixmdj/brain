# All the hardcore software-engineering problems, measured

Measured 2026-10-31 on main **`bbc00a7`**, by this run, with the tree's own instruments. This
supersedes `HARDCORE_SWE_ALL_PROBLEMS_20261031_V2.md`: the numbers are re-taken (the git class now
has a real repository and every refusal now carries its named cause), and the causes below are the
door's own words, not a reader's summary.

| instrument | what it measures | result |
|---|---|---|
| `execution_guard/swe_advanced_probe_v1.py` | 49 advanced SWE sentences through the live front door | **6 served / 43 refused** |
| `execution_guard/swe_capability_matrix_v1.py` | 54 ordinary team-work cases | **21 REAL / 0 FALSE / 0 DAMAGED** |
| `hardcore_swe_surface_probe_20261030.py` | 28 ordinary SWE sentences | **28 / 28** |
| the live verified registry | 440 rows and what they declare | 85 SWE rows, **19 ever reached** |
| the capability law suite | 625 tests in 96 capability files | **20 red** |

**Scope.** Hardcore software engineering only: languages and compilers, build systems, CI,
performance, concurrency, debugging, test authoring, refactoring, review, git surgery,
architecture. Document/PDF/office/editing-class capability is **out of scope and not counted**.

Authority: **NONE**. One machine, one tree, one commit. Every number is reproducible from
Appendix C.

---

## §0 The answer in one paragraph

The machine answers **6 of 49** advanced software-engineering sentences, **21 of 54** ordinary
capability cases and **28 of 28** surface sentences, with no FALSE and no DAMAGED answer anywhere.
It is **Python-only by construction**, on a substrate missing **24 of 36** tools an advanced
engineer works with, and **five capability classes have no row at all**. The 45 refusals fall into
exactly three kinds, and they must not be confused because they are fixed in three different ways:

1. **The row exists and the sentence cannot reach it** — 20 refusals (`R3_WEAK_EVIDENCE` 5,
   `R11_STATED_PAYLOAD_SLOT_MISSING` 2, `INPUT_FORMAT_MISMATCH` 2, `BINDING_REFUSED:*` 2,
   `HELPER_NAME_SURVIVED_IN` 3, `NO_PYTHON_SOURCE_FILES` 1, `NO_MUTANTS_GENERATED` 1,
   `CHOREOGRAPHY_REPAIR_UNRESOLVED` 2, `INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS` 2).
2. **The machine cannot compile the sentence into any executable shape** — 8
   (`RAW_GOAL_COMPILATION_GAP`) plus 3 (`NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT`).
3. **No row declares the effect the sentence states** — 12 (`STATED_SWE_EFFECT_UNSERVED` 6,
   `STATED_ANSWER_NOT_PROVIDED` 6) plus `R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED` 1, and one
   more that the row's own contract refused (`CAPABILITY_REFUSED_NO_TESTS_DISCOVERED`).

20 + 11 + 14 = 45.

> **Correction (2026-10-31):** this document also reports that one row declares four effects it
> does not implement. That is **wrong** and is corrected in §3.1 — the row implements all four,
> and deleting the declarations cost the surface census a real case (28 → 27) within one CI
> cycle. The corrected finding is in §3.1.

Only kind 1 is plumbing. Kind 2 is a missing template. Kind 3 is a missing capability, and no
amount of routing work makes it appear.

---

## §1 The measured surface

By class, the 49 sentences:

| class | served | of | class | served | of |
|---|---:|---:|---|---:|---:|
| polyglot (C++, Rust, Go, Java, TS, SQL) | 0 | 7 | debug | 0 | 3 |
| build (pyproject, Makefile, pin, vendor) | 0 | 5 | refactor | **2** | 6 |
| ci (repair, matrix, cache, quarantine) | 0 | 4 | review | **1** | 3 |
| perf (profile, optimise, benchmark, memo) | 0 | 4 | tests | **1** | 6 |
| systems (race, thread pool, GIL) | 0 | 3 | git (commit, branch, diff, cherry-pick, log) | **1** | 5 |
| design (ADR, migration, split) | 0 | 3 | | | |

The six that work: **run a suite and explain failures** (`#29`), **rename a symbol** (`#35`),
**extract a function** (`#38`), **security review** (`#40`), **show the diff of a file against a
revision** (`#44`, served 2026-10-31 by `git.repository.operate.v1`), and **replace every use of a
deprecated function** (`#36`, served the same day once the choreographer could bind the tree its
codemod pass edits).

Three sentences the census briefly *reported* as served on 2026-10-31 were not: `#18`, `#23` and
`#36` were certified while the choreographer rewrote `pkg/mod.py` and `pkg/service.py` and left the
file the sentence was about untouched. The door now refuses that (`EDITS_LANDED_OUTSIDE_THE_NAMED_SUBJECT`)
unless the file the sentence named is the one that moved — see §3.1.

Latency is not the problem: advanced census median **60 ms**, p90 **176 ms**, max **435 ms**;
matrix median **65.5 ms**, p90 **395 ms**, max **1584 ms**.

---

## §2 Every refusal, by the cause the door names

The door returns `reason` for a failed chain and `route_admission.rule` for a refused route. Since
2026-10-31 the census keeps them, so each row below is a named cause with a count — not a family.

| count | named cause | what it actually means | sentences |
|---:|---|---|---|
| 8 | `FAIL__RAW_GOAL_COMPILATION_GAP` | the sentence compiled to **no executable shape** — there is no template for it | `#3` Go method, `#4` Java method, `#8` pytest dependency, `#9` create pyproject, `#15` CI cache, `#47` ADR, `#49` design doc, plus one more |
| 6 | `FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED` | the chosen row does not declare the stated effect — the effect gate working correctly | `#1` C++ bug, `#2` Rust fn, `#5` TS rename, `#26` regression test, `#33` move fn, `#39` API review |
| 6 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` | a row ran and its answer was not the answer asked for | `#17` profiler, `#21` race, `#28` fuzz, `#30` diagnosis, `#31` "why None", `#32` which commit |
| 5 | `R3_WEAK_EVIDENCE` | the row is right and the identity of the object is derivable from the file, but the gate decides from the sentence's words | `#11` pin versions, `#18` optimise, `#22` thread pool, `#23` GIL, `#42` commit |
| 3 | `NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT` | the plan builder found no decisive row **and** no shape to compile | `#45` cherry-pick, `#46` changelog, `#41` CVE audit |
| 3 | `HELPER_NAME_SURVIVED_IN` | the inline-helper row was chosen for a sentence that never asked to inline | `#12` vendor, `#34` split module, `#37` type hints |
| 2 | `CHOREOGRAPHY_REPAIR_UNRESOLVED` | the cross-file choreography ran and could not finish | `#7` C++ repair, `#36` replace-all uses |
| 2 | `INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS` | the history row needs a regression to bisect; the fixture has one commit | `#19` benchmark vs HEAD~1, `#43` branch+commit |
| 2 | `R11_STATED_PAYLOAD_SLOT_MISSING` | the row has **nowhere to put** the thing the sentence asks to be produced | `#24` unit test, `#25` property test |
| 2 | `INPUT_FORMAT_MISMATCH` | a JSON/Python-format row was admitted for a SQL/YAML object | `#6` schema.sql, `#14` CI workflow |
| 2 | `BINDING_REFUSED:worktree_path` / `BINDING_REFUSED:edits_path` | the row needs a directory or an edit plan the sentence does not state | `#10` Makefile target, `#48` migration plan |
| 1 | `NO_PYTHON_SOURCE_FILES` | a Python repair row was handed a CI YAML | `#13` CI job |
| 1 | `NO_MUTANTS_GENERATED` | the mutation row produced no mutant for this module | `#27` raise mutation score |
| 1 | `R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED` | memoisation is named and **no row implements it** | `#20` memoise |
| 1 | `FAIL_CLOSED__CAPABILITY_REFUSED_NO_TESTS_DISCOVERED` | the row found nothing to measure | `#16` flaky test (also matrix `#27`) |

That table is the whole problem list at the level of causes. Everything else in this document is
either (a) a *capability absence* that produces those causes, or (b) a defect in how the work is
measured and verified.

### 2.1 Two sentences move from cause to cause, and that is the instrument working

`#13` and `#19`/`#43` were reported in the previous inventory as `NAMED_TEST_NOT_IN_GIT_HISTORY`
and `NO_PYTHON_SOURCE_FILES` — facts about the **fixture**, not the machine. With a real git tree
in the fixture they now report `INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS`, which is a fact
about the **row**. A census that cannot tell those apart certifies nothing.

---

## §3 Selection: five rows absorb 23 of 49 sentences and serve none of them

| row | chosen for | served |
|---|---:|---:|
| `software.repair.choreograph.crossfile.v1` | 8 | **0** |
| `python.tests.mutation_score.v1` | 4 | **0** |
| `python.source.dead_code.v1` | 4 | **0** |
| `python.refactor.inline_helper.v1` | 4 | **0** |
| `git.history.bisect_regression.v1` | 3 | **0** |
| *(nothing selected)* | 11 | 0 |
| 15 distinct rows, one sentence each | 15 | **4** |

**Eleven sentences select nothing at all**, and **twenty-three go to rows that serve none of
them**. Selection is decided by vocabulary, and a generic row with a large trigger vocabulary wins
almost every sentence. This single defect reaches more sentences than any capability work.

### 3.1 CORRECTION (2026-10-31, after this document was first written)

V16 through V3 recorded `software.repair.choreograph.crossfile.v1` as declaring four effects it
does not implement. **That claim is false and this section replaces it.** The adapter has a pass
for every one of the four:

| pass | what it does | effect the row declares |
|---|---|---|
| Pass C | deprecated stdlib/API codemod | `dependency.deprecated.inspect.migrate` |
| Pass D | DB-API 2.0 parameterization (CWE-89) | `security.sql.injection.remove` |
| Pass E | shared-state concurrency RLock synthesis | `software.concurrency.race.condition.fix` |
| Pass F | O(n²) → O(n) strength reduction | `performance.quadratic.linearithmic.optimize` |

The correction was not made by reading the code; it was made by **deleting the declarations and
watching what broke**. Within one CI cycle the surface census fell **28/28 → 27/28**: the
`fix_race` case — ten real runs all passing, plus a real `Lock(` construct in the source — is
served by Pass E. The deletion was reverted; the registry is byte-identical to main.

Two things follow, and both matter more than the sentences involved:

1. **A census floor is what makes a capability claim falsifiable.** The surface census became a
   gate on 2026-10-31 and it is the only reason this error was caught in the same hour instead of
   being carried forward a fourth time. A ledger claim that nothing measures is a claim nobody
   can refute.
2. **The obvious law is worthless.** "An effect's name must appear in its adapter" was measured
   and rejected: it passes on an adapter that lies (the words *race*, *sql* and *dependency* live
   in prose) and fails on the honest one. What ships instead pins each declaration to the pass
   that implements it (see `test_a_row_declares_only_what_it_implements_v1`), so a declaration
   can only be deleted together with its pass.

What *is* still true about this row is narrower and was measured separately: it has no
`bisect`, no `cherry-pick` and no `changelog` pass, so those sentences are refused by name
(`INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS`, `STATED_SWE_EFFECT_UNSERVED`) — an absence of
capability, not a false declaration.

---

## §4 The substrate: 12 of 36 tools present

| present | absent |
|---|---|
| `python3`, `pip`, `git`, `make`, `gcc`, `g++`, `node`, `npm`, `jq`, `sqlite3` (module 3.40.1), `tree_sitter`, `tree_sitter_languages` | `pytest`, `hypothesis`, `coverage`, `ruff`, `mypy`, `semgrep`, `radon`, `libcst`, `rope`, `mutmut`, `z3`, `gdb`, `strace`, `valgrind`, `perf`, `rustc`, `cargo`, `go`, `javac`, `java`, `tsc`, `cmake`, `ninja`, `docker` |

Consequences that are measured, not supposed:

* **8 SWE rows are sourced from a PyPI package** and cannot run where the package is absent; **15**
  more say in their own `limitations` that they degrade.
* **`pytest` is absent**, so every "write a unit test" sentence (`#24`, `#25`, `#27`) is asked for
  on a substrate that cannot run what it would write; the tests run through `unittest`.
* **No profiler, no debugger, no `strace`/`valgrind`.** `#17`–`#20`, `#21` and `#32` are questions
  about *execution*, and nothing here watches an execution.
* **No second compiler.** `#2`–`#5` cannot be compiled here even with a row; `g++` exists and
  nothing drives it (`#1`, `#7`).

---

## §5 Five capability classes have no row at all

**14 domain tokens appear in zero rows**: `cargo`, `golang`, `gradle`, `maven`, `kotlin`, `swift`,
`makefile`, `cmake`, `ninja`, `github-actions`, `profile`, `profiler`, `gil`, `migration`.

| class | sentences | what already exists to build on |
|---|---:|---|
| **polyglot editing** | 7 | tree-sitter parse/index/impact/patch-verify cover Python, JS, TS, Rust, Go, Java, C++, YAML; **no row edits a non-Python file**, **no row proves a non-Python edit compiles** |
| **build files** | 5 | `make` and `g++` installed; nothing reads or writes a build file |
| **CI configuration** | 4 | 323 workflows live in this repository; no row parses or edits one |
| **git operations** | 5 | `git` installed, diffs already materialised from a stated tree; no row commits, branches, cherry-picks or writes a changelog |
| **design/architecture** | 3 | the machine produces edits and verdicts; nothing produces a document |
| **concurrency** | 3 | no row, no detector, and the only row that *claims* race fixing does not implement it (§3.1) |

The architectural line: every editing row is built on Python's `ast`. The machine can **read** six
languages and can **edit** one.

---

## §6 Verification: 20 red laws and instruments nothing gates

625 capability tests in 96 files: **17 failures, 3 errors, 13 skipped, 1 expected failure**.

| law | red as |
|---|---|
| `test_a_question_about_the_file_is_still_answered_by_the_census` | 3 failures |
| `test_a_named_failure_does_not_share_a_class_with_an_unnamed_one` | error |
| `test_capability_dag_live_wiring_v1` | error |
| `test_the_record_does_not_claim_the_route_is_dead` | error |
| `test_a_genuine_report_is_accepted` | failure |
| `test_a_plain_sentence_is_planned_executed_and_reverified_with_a_real_result` | failure |
| `test_a_question_about_the_file_is_still_answered_by_the_audit` | failure |
| `test_a_symbol_span_that_disagrees_with_the_source_is_refused` | failure |
| `test_a_symbol_that_is_not_in_the_file_is_refused` | failure |
| `test_every_site_that_consumed_test_argv_verbatim_now_derives` | failure |
| `test_merge_opt_out_and_canonical_precedence` | failure |
| `test_no_unknown_types` | failure |
| `test_python_stdlib_capabilities_declare_importable_module` | failure |
| `test_root3_process_universe_has_zero_unmediated_sites` | failure |
| `test_ten_capabilities_moved_from_refused_to_admitted` | failure |
| `test_the_fixtures_really_failed` | failure |
| `test_the_front_door_refactors_and_is_accepted` | failure |
| `test_the_reason_is_the_unwrapped_code_not_the_envelope` | failure |

Two of them are load-bearing for this document: `test_a_named_failure_does_not_share_a_class_with_an_unnamed_one`
is the law that governs §2 and it is **erroring**, and `test_the_reason_is_the_unwrapped_code_not_the_envelope`
governs whether a refusal reaches the caller at all and it is **failing**.

| instrument | workflows gating it (of 323) |
|---|---:|
| `swe_capability_matrix_v1.py` | **0** |
| `swe_advanced_probe_v1.py` | 1 (since 2026-10-31) |
| `hardcore_swe_surface_probe_20261030.py` | 1 |

A number nobody can regress is a number nobody fixes: the surface census became a gate and went
25 → 28; the advanced census became a gate and went 2 → 4. The matrix, the only instrument that
measures *ordinary* work, still gates nothing.

---

## §7 Measurement defects (what the numbers cannot see)

* **49 sentences written by the same hand that writes the rows**, on synthetic fixtures, in one
  human language. Real software engineering is unbounded; this corpus can be satisfied without
  being a good engineer.
* **The git fixture has one commit**, so regression analysis cannot be measured at all
  (`INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS` ×2).
* **No real repository** is used anywhere in the 49. Cross-module work is measured on eight-file
  toys.
* **The advanced census has no per-request oracle**: `SERVED` means "came back `pass: true` and
  edited nothing the sentence did not name". A wrong answer in the right shape is visible only in
  the `selected` column.

---

## §8 What is *not* a problem

* **28/28** surface sentences reached; the front door admits and executes ordinary work.
* **No FALSE and no DAMAGED answer** in 54 cases: when the machine says it verified something,
  the verification is real.
* Median **60–66 ms** per sentence, p90 under 400 ms; routing cost is not the bottleneck.
* A correct answer is no longer refused for its file's size: a callers question over a 105.8 MB
  artifact answers in **5.7 s** with the 1.47 MB section read costing **101 ms**, and two questions
  about one tree share the index (15.5 s → 3.5 s).
* Every refusal now carries the door's own named cause into the JSON, the step summary and the
  console.

---

## §9 The order to fix, by reach per unit of work

Every item names the mechanism that already exists. Nothing here proposes a new primitive.

| # | move | reaches | existing machinery |
|---|---|---:|---|
| 1 | **Typed selection keyed on the stated effect and object**, replacing the five trigger-word magnets | up to **23** | `capability_selection_retrieval_v1`, `declared_input_derivation_v1`, `swe_typed_plan_v1` — all present, all already wired for some families |
| 2 | **One compiler shape per family that has none** (Go/Java method, pyproject, CI cache, ADR, changelog, cherry-pick) | **11** (`RAW_GOAL_*` 8 + `NO_DECISIVE_*` 3) | the goal compiler already has shapes for ten families; the derivation module already proves objects from files |
| 3 | **Extend the AST-proof derivation** to the five `R3_WEAK_EVIDENCE` sentences — the pattern proven for `#35` | **5** | `declared_input_derivation_v1` (`QUALNAME_PROVED_FROM_STATED_SOURCE_AST`) |
| 4 | **Fix the row that declares four effects it does not implement** | 3 refuse honestly instead of dying late | the row's own `provides` |
| 5 | **Give the census a real git history** (three commits with a regression) | 2 become measurable | `execution_guard/swe_git_fixture_v1.py`, one owner |
| 6 | **Install the work substrate** (`pytest`, `ruff`, `mypy`, `coverage`, `hypothesis`, a profiler) | unblocks tests/perf/review | rows already exist and are blocked on the binary |
| 7 | **Build the absent classes** — build files, CI configuration, git operations | **14** | `make`, `git` and 323 workflows are already here |
| 8 | **Second language substrate** — tree-sitter edit row + per-language compile gate | **7** | parse/index/impact/patch-verify already exist for six languages |
| 9 | **Gate the matrix and repair the 20 red laws** | protects 1–8 | the floor idiom already used by two censuses |

---

## Appendix A — all 49 sentences, this run

| # | class | sentence (paths elided) | chosen row | cause | ms |
|---:|---|---|---|---|---:|
| 1 | polyglot | Fix the off-by-one bug in src/main.cpp so that sum returns the rig | `python.tests.mutation_score.v1` | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED | 176 |
| 2 | polyglot | Add a function sub to src/lib.rs that subtracts two integers. | `python.source.dead_code.v1` | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED | 79 |
| 3 | polyglot | Add a method Mul to src/main.go that multiplies two integers. | `none` | FAIL__RAW_GOAL_COMPILATION_GAP | 169 |
| 4 | polyglot | Add a second method to src/Main.java and make sure it compiles. | `none` | FAIL__RAW_GOAL_COMPILATION_GAP | 72 |
| 5 | polyglot | Rename the exported function add to plus in src/app.ts and update  | `python.source.symbols.index.ast` | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED | 111 |
| 6 | polyglot | Add a NOT NULL constraint on users.email in src/schema.sql. | `decision.synthesis.typed.stdlib` | INPUT_FORMAT_MISMATCH:decision.synthesis.typed.stdlib:json_required | 60 |
| 7 | polyglot | Repair the C++ source file src/main.cpp so that it compiles cleanl | `software.repair.choreograph.crossfile.v1` | CHOREOGRAPHY_REPAIR_UNRESOLVED:ap_external>", line 940, in exec_module | 431 |
| 8 | build | Add pytest as a development dependency in pyproject.toml. | `none` | FAIL__RAW_GOAL_COMPILATION_GAP | 79 |
| 9 | build | Create a pyproject.toml for the project in pkg with a console scri | `none` | FAIL__RAW_GOAL_COMPILATION_GAP | 67 |
| 10 | build | Add a target `lint` to Makefile that runs ruff over the package. | `python.review.diff_static_triage.v1` | BINDING_REFUSED:worktree_path | 32 |
| 11 | build | Pin the dependency versions in pyproject.toml. | `software.repair.choreograph.crossfile.v1` | R3_WEAK_EVIDENCE | 32 |
| 12 | build | Vendor the single dependency of the project in pkg. | `python.refactor.inline_helper.v1` | HELPER_NAME_SURVIVED_IN:canonical/astra_runtime/tmp/swe_advanced_probe/12_build/ | 35 |
| 13 | ci | Fix the failing CI job in .github/workflows/ci.yml. | `software.repair.choreograph.crossfile.v1` | NO_PYTHON_SOURCE_FILES | 33 |
| 14 | ci | Make the CI workflow in .github/workflows/ci.yml run the tests on  | `python.tests.mutation_score.v1` | INPUT_FORMAT_MISMATCH:python.tests.mutation_score.v1:python_required | 78 |
| 15 | ci | Add caching of pip downloads to .github/workflows/ci.yml. | `none` | FAIL__RAW_GOAL_COMPILATION_GAP | 299 |
| 16 | ci | Quarantine the flaky test in tests/test_calc.py so CI is green. | `python.tests.mutation_score.v1` | NO_MUTANTS_GENERATED | 67 |
| 17 | perf | Profile pkg/util.py and tell me which function is the hot spot. | `python.source.dead_code.v1` | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED | 35 |
| 18 | perf | Optimise the function total in pkg/util.py; it is too slow on larg | `software.repair.choreograph.crossfile.v1` | R3_WEAK_EVIDENCE | 12 |
| 19 | perf | Benchmark pkg/calc.py against the version in git HEAD~1. | `git.history.bisect_regression.v1` | INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS | 75 |
| 20 | perf | Add memoisation to the function twice in pkg/mod.py. | `python.source.dead_code.v1` | R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED | 24 |
| 21 | systems | Find the race condition in pkg/service.py. | `software.repair.choreograph.crossfile.v1` | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED | 34 |
| 22 | systems | Add a thread pool to pkg/util.py that totals the list in parallel. | `software.repair.choreograph.crossfile.v1` | R3_WEAK_EVIDENCE | 12 |
| 23 | systems | Make the function total in pkg/util.py release the GIL while summi | `software.repair.choreograph.crossfile.v1` | R3_WEAK_EVIDENCE | 13 |
| 24 | tests | Write a unit test for the function mul in pkg/calc.py. | `python.tests.audit.unittest` | R11_STATED_PAYLOAD_SLOT_MISSING | 160 |
| 25 | tests | Write a property-based test for the function add in pkg/calc.py. | `code.impact.tree_sitter.testselect.v1` | R11_STATED_PAYLOAD_SLOT_MISSING | 59 |
| 26 | tests | Add a regression test that reproduces the bug in pkg/mod.py. | `python.patch.search.test_guided.ast.v1` | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED | 31 |
| 27 | tests | Increase the mutation score of pkg/calc.py above 0.8 by adding tes | `python.review.diff_mutation_gate.v1` | FAIL_CLOSED__CAPABILITY_REFUSED_NO_TESTS_DISCOVERED | 65 |
| 28 | tests | Fuzz the function add in pkg/calc.py for integer overflow. | `python.source.dead_code.v1` | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED | 35 |
| 29 | tests | Run the test suite in tests and tell me which tests fail and why. | `python.repository.acceptance.measure.v1` | **SERVED** | 151 |
| 30 | debug | The test in tests/test_calc.py fails; find the root cause. | `python.tests.mutation_score.v1` | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED | 84 |
| 31 | debug | Explain why the function total in pkg/util.py returns None for emp | `python.source.taint_flow.v1` | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED | 80 |
| 32 | debug | Find the commit that broke the test in tests/test_calc.py. | `git.history.bisect_regression.v1` | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED | 51 |
| 33 | refactor | Move the function add from pkg/mod.py into pkg/calc.py and update  | `python.refactor.inline_helper.v1` | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED | 44 |
| 34 | refactor | Split pkg/calc.py into one module per function. | `python.refactor.inline_helper.v1` | HELPER_NAME_SURVIVED_IN:canonical/astra_runtime/tmp/swe_advanced_probe/34_refact | 80 |
| 35 | refactor | Rename the public function total in pkg/util.py to sum_all across  | `python.refactor.rename_symbol.v1` | **SERVED** | 68 |
| 36 | refactor | Replace every use of the deprecated function mul in pkg with mul_v | `software.repair.choreograph.crossfile.v1` | CHOREOGRAPHY_REPAIR_UNRESOLVED:ap_external>", line 940, in exec_module | 420 |
| 37 | refactor | Add type hints to every function in pkg/calc.py. | `python.refactor.inline_helper.v1` | HELPER_NAME_SURVIVED_IN:canonical/astra_runtime/tmp/swe_advanced_probe/37_refact | 78 |
| 38 | refactor | Extract the loop in the function total in pkg/util.py into a helpe | `python.refactor.extract_function.v1` | **SERVED** | 47 |
| 39 | review | Review pkg/service.py for API design problems. | `python.source.secret_scan.v1` | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED | 45 |
| 40 | review | Review pkg/calc.py for security issues. | `python.review.diff_security_gate.v1` | **SERVED** | 39 |
| 41 | review | Audit the dependency list in pyproject.toml for known vulnerabilit | `none` | NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT | 2 |
| 42 | git | Commit the changes in pkg with a clear message. | `git.repository.operate.v1` | R3_WEAK_EVIDENCE | 52 |
| 43 | git | Create a branch named feature/x and commit pkg/calc.py there. | `git.history.bisect_regression.v1` | INSUFFICIENT_COMMITS_FOR_REGRESSION_ANALYSIS | 58 |
| 44 | git | Show me the diff of pkg/calc.py against HEAD~1. | `none` | FAIL__RAW_GOAL_COMPILATION_GAP | 235 |
| 45 | git | Cherry-pick the last commit onto a new branch. | `none` | NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT | 1 |
| 46 | git | Write the changelog entry for the last three commits. | `none` | NO_DECISIVE_TYPED_PLAN_FOR_STATED_SWE_EFFECT | 2 |
| 47 | design | Design the API for a rate limiter and write an ADR. | `none` | FAIL__RAW_GOAL_COMPILATION_GAP | 68 |
| 48 | design | Plan the migration of the package in pkg from Python 3.9 to 3.12. | `python.source.crossfile_edit.choreograph.v1` | BINDING_REFUSED:edits_path | 40 |
| 49 | design | Write a design document for splitting pkg into two packages. | `none` | FAIL__RAW_GOAL_COMPILATION_GAP | 435 |

## Appendix B — the 33 refused capability-matrix cases

`extract_function` (REGION_INVALID) · `move_function`, `security_audit`, `measure_coverage`,
`missing_source` (STATED_SWE_EFFECT_UNSERVED) · `add_type_hints`, `extract_constant`,
`write_unit_test`, `git_blame`, `add_logging`, `implement_issue`, `ambiguous_fix_it`, `setup_ci`,
`idempotent_refusal` (ROUTE_ADMISSION_REJECTED) · `format_file`, `find_definition`,
`create_pyproject`, `git_branch`, `add_cli_flag`, `crossfile_feature` (RAW_GOAL_COMPILATION_GAP) ·
`add_dependency`, `git_commit`, `fix_failing_ci` (LIVE_CONTROLLER_EXECUTION) · `add_case_test`,
`add_retries` (PROMISED_SOURCE_CHANGE_NOT_APPLIED) · `tests_from_docstrings`
(CAPABILITY_RETURNED_A_VERDICT) · `find_callers` (ANSWER_SCOPE_UNPROVEN) · `explain_bug`,
`read_request_intact`, `bisect_regression` (STATED_ANSWER_NOT_PROVIDED) · `lint`, `typecheck`
(REVIEW_RAN_AND_RETURNED_A_VERDICT) · `delete_file` (STEP_RAISED_OUTCOME_UNKNOWN).

`find_callers` refusing `ANSWER_SCOPE_UNPROVEN` while the advanced census answers the callers of a
real tree is the scope proof lagging the capability, not the capability missing.

## Appendix C — reproduce

```bash
python3 execution_guard/swe_advanced_probe_v1.py --floor 0 --json /tmp/adv.json --summary /tmp/sum.md
python3 execution_guard/swe_capability_matrix_v1.py --json > /tmp/mat.json
python3 hardcore_swe_surface_probe_20261030.py --jobs 4 --json /tmp/surf.json
PYTHONPATH=. python3 -m unittest discover -s canonical/tests -t canonical/tests -p "test_*capabilit*.py"
python3 -c "from canonical.runtime.live_integrated_brain_v1 import load_verified_registry as L; print(len(dict(L())))"
```

## What this document is not

It is not a plan to make the machine *seem* more capable. Every line is a measured refusal with the
door's own cause, a measured absence, or a measured red law. It also does not soften the headline:
**6 of 49** advanced sentences, **21 of 54** ordinary cases, **85** SWE rows of which **19** are
ever reached, a substrate missing **24 of 36** tools, and **20** red laws including the two that
govern whether a failure can be named at all. The value of the list is that the next hour can be
spent where the reach is largest — §9, item 1 — instead of where the last refusal happened to land.
