# All the hardcore software-engineering problems, measured

Measured 2026-10-31 on main **`34124aa`**, by this run, with the tree's own instruments:

| instrument | what it measures | command |
|---|---|---|
| `execution_guard/swe_advanced_probe_v1.py` | 49 advanced SWE sentences through the live front door | `--floor 0 --json /tmp/q_adv.json` |
| `execution_guard/swe_capability_matrix_v1.py` | 54 ordinary team-work cases | `--json` |
| `hardcore_swe_surface_probe_20261030.py` | 28 ordinary SWE sentences | `--jobs 4 --json /tmp/q_surf.json` |
| the live verified registry | 440 rows and what they declare | `live_integrated_brain_v1.load_verified_registry()` |
| the capability law suite | 625 tests in 96 files | `unittest discover -p "test_*capabilit*.py"` |

**Scope.** Hardcore software engineering only: languages and compilers, build systems, CI,
performance, concurrency, debugging, test authoring, refactoring, code review, git surgery,
architecture. Document/PDF/office/editing-class capability is **out of scope and not counted** —
those rows exist and are not the subject of this document.

Authority: **NONE**. One machine, one tree, one commit. Every number below is reproducible with
the command next to it.

---

## §0 The answer in one paragraph

The machine answers **4 of 49** advanced software-engineering sentences for real, **21 of 54**
ordinary capability cases, and **28 of 28** ordinary surface sentences, with **no FALSE and no
DAMAGED** answer anywhere. It is **Python-only by construction**, on a substrate that is missing
**26 of the 37 tools** an advanced engineer works with (no profiler, no debugger, no `rustc`/`go`/
`javac`/`tsc`, no `pytest`, no `ruff`, no `mypy`), and **five capability classes have no row at
all** (build files, CI configuration, design/architecture, git operations, concurrency). The gap is
therefore three separate things and they must not be confused:

1. **Selection and binding defects** stop a sentence from reaching a row that already exists —
   19 of the 45 refusals (10 refused by an admission rule, 6 answered by the wrong row, 3 refused
   by the row's own contract).
2. **Opaque execution failures** — 10 sentences route to a row, the chain runs, and the controller
   fails without saying why.
3. **Real absences** — 9 sentences state an effect no row declares, 7 compile to nothing, and the
   substrate cannot run what several rows already claim.

---

## §1 The measured surface

| instrument | result |
|---|---|
| advanced census (49 hardcore sentences) | **4 served / 45 refused** |
| capability matrix (54 cases) | **21 REAL / 0 FALSE / 0 DAMAGED** |
| surface census (28 sentences) | **28 / 28** |
| live verified registry | 440 rows — 293 `.auto.v1`, **147 authored**, 85 SWE-prefixed |
| SWE rows actually reached by the 49 sentences | **19 of 85** |
| capability law suite | 625 tests, **20 red** (17 failures, 3 errors) |
| advanced latency | median **61 ms**, p90 **174 ms**, max **420 ms** |
| matrix latency | median **65 ms**, p90 **389 ms**, max **1504 ms** |

By class, the 49 sentences:

| class | served | of | class | served | of |
|---|---:|---:|---|---:|---:|
| polyglot (C++, Rust, Go, Java, TS, SQL) | 0 | 7 | debug | 0 | 3 |
| build (pyproject, Makefile, pin, vendor) | 0 | 5 | refactor | **2** | 6 |
| ci (workflow repair, matrix, cache, flake) | 0 | 4 | review | **1** | 3 |
| perf (profile, optimise, benchmark, memo) | 0 | 4 | tests | **1** | 6 |
| systems (race, thread pool, GIL) | 0 | 3 | git (commit, branch, diff, cherry-pick, log) | 0 | 5 |
| design (ADR, migration, split) | 0 | 3 | | | |

The four that work: **run a test suite and explain failures** (`#29`, 175 ms), **rename a symbol**
(`#35`, 68 ms), **extract a function** (`#38`, 44 ms), **security review** (`#40`, 44 ms).

---

## §2 The 45 refusals, by class

Counts are this run's, first token of the failure class:

| count | class | what it means | examples |
|---:|---|---|---|
| 10 | `ROUTE_ADMISSION_REJECTED` | a row was chosen and then refused the sentence at the gate | `#6` SQL schema → a JSON decision row; `#11` pin versions → repair choreography (`R3_WEAK_EVIDENCE`); `#14` CI matrix → mutation score (`INPUT_FORMAT_MISMATCH:python_required`); `#18`, `#22`, `#23` → choreography `R3_WEAK_EVIDENCE`; `#24`, `#25` → a capability with no slot for the stated payload (`R11_STATED_PAYLOAD_SLOT_MISSING`); `#42` git commit → `R3_WEAK_EVIDENCE`; `#20` memoise → `R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED` |
| 10 | `LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE` | the chain ran and failed, **and the failure does not say why** | `#7` repair C++ with the Python repair row; `#12` vendor a dependency; `#13` fix CI YAML; `#16` quarantine a flaky test; `#19`, `#43`, `#44` git operations routed to bisect; `#34` split a module via inline-helper; `#36` replace every use across a package; `#37` add type hints via inline-helper |
| 9 | `STATED_SWE_EFFECT_UNSERVED` | the chosen row does not declare the effect the sentence states — the honest gate | `#1` C++ off-by-one, `#2` Rust function, `#5` TS rename, `#26` regression test, `#33` move a function, `#39` API design review, `#41` dependency CVE audit, `#45` cherry-pick, `#46` changelog |
| 7 | `RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP` | the sentence compiled to no executable shape at all | `#3` Go method, `#4` Java method, `#8` pytest dependency, `#9` create pyproject, `#15` CI pip cache, `#47` ADR, `#49` split a package |
| 6 | `STATED_ANSWER_NOT_PROVIDED` | a row ran and its answer was not the answer asked for | `#17` profiler question answered by dead-code analysis; `#21` race condition answered by a writer; `#28` fuzz answered by dead-code; `#30` failing test → diagnosis; `#31` "why does this return None" → taint flow; `#32` which commit broke it → bisect |
| 3 | `CAPABILITY_REFUSED` | the row's own contract refused the object it was handed | `#10` Makefile edit → `WORKTREE_NOT_DIRECTORY`; `#27` raise mutation score → `NO_TESTS_DISCOVERED`; `#48` migration plan → `EDIT_PLAN_INPUT_INVALID` |

### 2.1 Route-admission rules that fire, by name

| rule | count | the defect it shows |
|---|---:|---|
| `R3_WEAK_EVIDENCE` | 5 | the sentence states the object, the row is right, but the lexical/derived evidence does not reach the row's own vocabulary (`#11` pin, `#18` optimise, `#22` thread pool, `#23` GIL, `#42` commit) |
| `R11_STATED_PAYLOAD_SLOT_MISSING` | 2 | the row has nowhere to put the thing the sentence asks to be produced (`#24` unit test, `#25` property test) |
| `INPUT_FORMAT_MISMATCH` | 2 | a JSON/native-format row was admitted for a text/YAML/SQL object (`#6` SQL, `#14` CI YAML) |
| `R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED` | 1 | `#20` memoisation: the effect is named and no row implements it |

Two of these (`R3`, `R10`) are the same shape as the defect that was fixed on 2026-10-31 for
`#35`: *the identity of the object is derivable from the file, and the gate is deciding it from
the sentence's word order instead.* `#35` went from refused to served by proving the function name
against the file's AST. The remaining five `R3` refusals are of exactly that shape and were not
attempted in this run.

### 2.2 The ten controller failures are opaque

`LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE` is one class for ten different failures, and
the census records no inner reason. From the sentence and the chosen row the disagreement is
visible — Python repair row for a C++ file (`#7`), git operations routed to history *search*
(`#19`, `#43`, `#44`), inline-helper for "add type hints" (`#37`) — but the machine reports one
string for all of them. **A failure a reader cannot name is a failure nobody can fix**; the
capability ledger's own rule (b) says a law that refuses work the machine can do is worse than a
false pass, and (f) says a harness that cannot distinguish "the answer is empty" from "no answer
was produced" certifies nothing. This class is (f) ten times over.

---

## §3 Selection: six rows absorb 25 of 49 sentences

| row | sentences it is chosen for | served |
|---|---:|---:|
| `software.repair.choreograph.crossfile.v1` | 8 | 0 |
| `python.tests.mutation_score.v1` | 4 | 0 |
| `python.source.dead_code.v1` | 4 | 0 |
| `python.refactor.inline_helper.v1` | 4 | 0 |
| `git.history.bisect_regression.v1` | 4 | 0 |
| *(nothing selected)* | 10 | 0 |
| every other row (14 rows) | 1 each | 4 |

The five magnet rows serve **zero** of the 25 sentences they absorb. One of them,
`software.repair.choreograph.crossfile.v1`, declares in its own row:

```
software.concurrency.race.condition.fix
security.sql.injection.remove
performance.quadratic.linearithmic.optimize
dependency.deprecated.inspect.migrate
```

It implements one choreography — patch, symbol graph, impact slice, dual-oracle verify, gate. It
therefore **passes the effect gate** that exists to catch exactly this, and the race-condition
(`#21`), SQL-injection and quadratic→linearithmic sentences are refused *late*, inside the
controller, instead of being refused early by name or answered. A declared-but-unimplemented
effect defeats the one gate built to detect it. It is one row and one edit to fix the declaration;
the sentences still need capability, but they would then refuse honestly and route elsewhere.

**Ten of the 49 sentences select nothing at all, and ten more select a row that refuses them on
its own contract.** Those twenty are the same defect one level up: the sentence's stated object is
not derived before the row is chosen, so the shortlist is decided by words in the sentence rather
than by the object it names.

---

## §4 The substrate: 11 of 37 tools present

| present | absent |
|---|---|
| `python3`, `pip`, `git`, `make`, `gcc`, `g++`, `node`, `npm`, `jq`, `tree_sitter` (+`tree_sitter_languages`), `sqlite3` (module 3.40.1) | `pytest`, `hypothesis`, `coverage`, `ruff`, `mypy`, `semgrep`, `radon`, `libcst`, `rope`, `mutmut`, `pynguin`, `crosshair`, `z3`, `sympy`, `numpy`, `profiler` (`cProfile` exists in-process; no external viewer), `gdb`, `strace`, `valgrind`, `perf`, `rustc`, `cargo`, `go`, `javac`, `java`, `tsc`, `cmake`, `ninja`, `docker`, `sqlite3` (CLI) |

Consequences that are measured, not supposed:

* **8 SWE rows are sourced from a PyPI package** and cannot run where the package is absent; 15
  more say in their own `limitations` that they degrade.
* **`pytest` is absent**, so every "write a unit test" sentence (`#24`, `#25`, `#27`) is asked for
  on a substrate that cannot run what it would write — the tests run through `unittest`.
* **No profiler, no debugger, no `strace`/`valgrind`.** Perf (`#17`–`#20`), race detection (`#21`)
  and "which commit broke this" (`#32`) are questions about *execution*, and nothing watches an
  execution.
* **No second compiler.** `#3` Go, `#4` Java, `#5` TS, `#2` Rust cannot be compiled here even if a
  row existed; `g++` exists and nothing drives it (`#1`, `#7`).

---

## §5 Five capability classes have no row at all

Measured over the live registry: **16 domain tokens appear in zero rows** — `cargo`, `golang`,
`gradle`, `maven`, `kotlin`, `swift`, `makefile`, `cmake`, `ninja`, `github-actions`, `profile`,
`profiler`, `thread`, `concurrency`, `gil`, `migration`.

| class | sentences | what exists to build on |
|---|---:|---|
| **polyglot editing** | 7 | tree-sitter parsing, indexing, impact and patch verification already exist and cover Python, JS, TS, Rust, Go, Java, C++, YAML; **no row edits a non-Python file** and **no row proves a non-Python edit compiles** |
| **build files** (pyproject, Makefile, pins, vendoring) | 5 | `make` and `g++` are installed; nothing reads or writes a build file |
| **CI configuration** | 4 | 323 workflows live in this repository; no row parses or edits one |
| **git operations** | 5 | `git` is installed and the tree already materialises diffs from a stated git tree; no row commits, branches, cherry-picks or writes a changelog |
| **design/architecture** | 3 | the machine produces edits and verdicts; nothing produces a document |
| **concurrency** | 3 | no row, no detector, and the only row that *claims* race fixing does not implement it (§3) |

This is the architectural line: every editing row is built on Python's `ast`. The machine can
*read* six languages and can *edit* one.

---

## §6 Verification: 20 red laws, and instruments nothing gates

### 6.1 The 20 red capability laws

625 tests in 96 capability test files: **17 failures, 3 errors, 13 skipped, 1 expected failure**.

| law | red as |
|---|---|
| `test_a_question_about_the_file_is_still_answered_by_the_census` | 3 failures |
| `test_capability_dag_live_wiring_v1` | error |
| `test_a_named_failure_does_not_share_a_class_with_an_unnamed_one` | error |
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

These are not cosmetic: `test_a_named_failure_does_not_share_a_class_with_an_unnamed_one` is
exactly the law that would have caught §2.2 (ten different failures sharing one name), and it is
**erroring**. A red law about naming failures means the naming rule itself is unverified.

### 6.2 Instruments nothing runs

| instrument | workflows that gate on it (of 323) |
|---|---:|
| `swe_capability_matrix_v1.py` | **0** |
| `swe_advanced_probe_v1.py` | 1 (added 2026-10-31) |
| `hardcore_swe_surface_probe_20261030.py` | 1 |
| `declared_input_derivation_v1` (the binding layer) | 0 |

The surface census became a gate on 2026-10-31 and went **25 → 28**; the advanced census became a
gate the same day and went **2 → 4**. The matrix — the only instrument that measures *ordinary*
work — still gates nothing.

### 6.3 Measurement breadth

49 sentences written by the same hand that writes the rows, over synthetic fixtures in
`canonical/astra_runtime/tmp/`. No real repository, no adversarial sentence, no sentence in a
language other than English. A corpus that small can be satisfied without being a good engineer;
the numbers above should be read as an upper bound on measured capability, not as a description.

---

## §7 What is *not* a problem (said plainly, to keep the list honest)

* **28/28** ordinary SWE sentences reached; the front door admits and executes ordinary work.
* **No FALSE and no DAMAGED answer** in 54 cases: when the machine says it verified something, the
  verification is real.
* Median **61–65 ms** per sentence, p90 under 400 ms: routing cost is not the bottleneck.
* The 2026-10-31 answer gate change means a correct answer is no longer refused for its file's
  size: a callers question over a 105.8 MB artifact answers in **5.7 s** with the 1.47 MB section
  read costing **101 ms**, and two questions about one tree now share the index (15.5 s → 3.5 s).

---

## §8 The order to fix, by reach per unit of work

Every item names the existing mechanism it reuses. Nothing here requires a new primitive.

| # | move | reaches | existing machinery to reuse |
|---|---|---:|---|
| 1 | **Selection keyed on the stated effect and object**, replacing the five trigger-word magnets | up to **25/49** | `capability_selection_retrieval_v1`, `declared_input_derivation_v1`, `swe_typed_plan_v1` — all present, all already wired to the door for some families |
| 2 | **Make the controller name its failure** (one class → one named cause) | **10/49** diagnosed | `test_a_named_failure_does_not_share_a_class_with_an_unnamed_one` already encodes the rule |
| 3 | **Fix the row that declares four effects it does not implement** | 3 sentences refuse honestly instead of dying late | the row's own `provides` field |
| 4 | **Derive the stated object for the remaining `R3_WEAK_EVIDENCE` families** (proven once for `#35`) | **5** | the derivation module's proof-against-AST pattern |
| 5 | **Install the work substrate** (`pytest`, `ruff`, `mypy`, `coverage`, `hypothesis`, a profiler) | unblocks tests/perf/review classes | rows already exist and are blocked on the binary |
| 6 | **Build the three absent classes** — build files, CI configuration, git operations | **14** | `make`, `git`, and 323 workflows are already here to be read |
| 7 | **Second language substrate** — a tree-sitter *edit* row plus a per-language compile gate | **7** | parsing/index/impact/patch-verify already exist for six languages |
| 8 | **Design/architecture output** | 3 | needs a planning surface that produces a document |
| 9 | **Gate the matrix** and repair the 20 red laws | protects everything above | the floor idiom already used by two censuses |

The order is by reach, not by taste: item 1 alone changes more sentences than items 4–8 combined.

---

## Appendix A — all 49 sentences, this run

| # | class | sentence (abridged) | chosen row | verdict | ms |
|---:|---|---|---|---|---:|
| 1 | polyglot | fix off-by-one in main.cpp | `python.tests.mutation_score.v1` | STATED_SWE_EFFECT_UNSERVED | 169 |
| 2 | polyglot | add `sub` to lib.rs | `python.source.dead_code.v1` | STATED_SWE_EFFECT_UNSERVED | 71 |
| 3 | polyglot | add method `Mul` to main.go | none | RAW_GOAL_COMPILATION_GAP | 160 |
| 4 | polyglot | add a method to Main.java and compile | none | RAW_GOAL_COMPILATION_GAP | 79 |
| 5 | polyglot | rename `add`→`plus` in app.ts | `python.source.symbols.index.ast` | STATED_SWE_EFFECT_UNSERVED | 118 |
| 6 | polyglot | NOT NULL constraint in schema.sql | `decision.synthesis.typed.stdlib` | INPUT_FORMAT_MISMATCH | 58 |
| 7 | polyglot | repair main.cpp so it compiles | `software.repair.choreograph.crossfile.v1` | LIVE_CONTROLLER_EXECUTION | 420 |
| 8 | build | add pytest dev dependency to pyproject | none | RAW_GOAL_COMPILATION_GAP | 72 |
| 9 | build | create pyproject with console script | none | RAW_GOAL_COMPILATION_GAP | 59 |
| 10 | build | add `lint` target to Makefile | `python.review.diff_static_triage.v1` | WORKTREE_NOT_DIRECTORY | 31 |
| 11 | build | pin dependency versions | `software.repair.choreograph.crossfile.v1` | R3_WEAK_EVIDENCE | 29 |
| 12 | build | vendor the dependency | `python.refactor.inline_helper.v1` | LIVE_CONTROLLER_EXECUTION | 33 |
| 13 | ci | fix the failing CI job | `software.repair.choreograph.crossfile.v1` | LIVE_CONTROLLER_EXECUTION | 35 |
| 14 | ci | run tests on 3.11 and 3.12 | `python.tests.mutation_score.v1` | INPUT_FORMAT_MISMATCH | 90 |
| 15 | ci | cache pip downloads | none | RAW_GOAL_COMPILATION_GAP | 319 |
| 16 | ci | quarantine the flaky test | `python.tests.mutation_score.v1` | LIVE_CONTROLLER_EXECUTION | 76 |
| 17 | perf | profile util.py, find the hot spot | `python.source.dead_code.v1` | STATED_PROFILE_NOT_TAKEN | 38 |
| 18 | perf | optimise `total` | `software.repair.choreograph.crossfile.v1` | R3_WEAK_EVIDENCE | 15 |
| 19 | perf | benchmark against HEAD~1 | `git.history.bisect_regression.v1` | LIVE_CONTROLLER_EXECUTION | 114 |
| 20 | perf | add memoisation | `python.source.dead_code.v1` | R10_EFFECT_UNSERVED | 24 |
| 21 | systems | find the race condition | `software.repair.choreograph.crossfile.v1` | READ_ONLY_QUESTION_ANSWERED_BY_WRITER | 35 |
| 22 | systems | add a thread pool | `software.repair.choreograph.crossfile.v1` | R3_WEAK_EVIDENCE | 13 |
| 23 | systems | release the GIL while summing | `software.repair.choreograph.crossfile.v1` | R3_WEAK_EVIDENCE | 13 |
| 24 | tests | write a unit test for `mul` | `python.tests.audit.unittest` | R11_STATED_PAYLOAD_SLOT_MISSING | 174 |
| 25 | tests | write a property-based test | `code.impact.tree_sitter.testselect.v1` | R11_STATED_PAYLOAD_SLOT_MISSING | 63 |
| 26 | tests | regression test from a bug | `python.patch.search.test_guided.ast.v1` | STATED_SWE_EFFECT_UNSERVED | 31 |
| 27 | tests | raise mutation score above 0.8 | `python.review.diff_mutation_gate.v1` | NO_TESTS_DISCOVERED | 61 |
| 28 | tests | fuzz `add` | `python.source.dead_code.v1` | STATED_FUZZ_NOT_PERFORMED | 34 |
| **29** | tests | run the suite, say what fails and why | `python.repository.acceptance.measure.v1` | **SERVED** | 175 |
| 30 | debug | find the root cause of a failing test | `python.tests.mutation_score.v1` | STATED_DIAGNOSIS_NOT_PROVIDED | 102 |
| 31 | debug | why does `total` return None | `python.source.taint_flow.v1` | STATED_ANSWER_NOT_PROVIDED | 86 |
| 32 | debug | which commit broke it | `git.history.bisect_regression.v1` | STATED_PROVENANCE_NOT_ANSWERED | 66 |
| 33 | refactor | move `add` to another module | `python.refactor.inline_helper.v1` | STATED_SWE_EFFECT_UNSERVED | 48 |
| 34 | refactor | split module into one file per function | `python.refactor.inline_helper.v1` | LIVE_CONTROLLER_EXECUTION | 85 |
| **35** | refactor | rename `total`→`sum_all` across the repo | `python.refactor.rename_symbol.v1` | **SERVED** | 68 |
| 36 | refactor | replace every use of `mul` | `software.repair.choreograph.crossfile.v1` | LIVE_CONTROLLER_EXECUTION | 400 |
| 37 | refactor | add type hints to every function | `python.refactor.inline_helper.v1` | LIVE_CONTROLLER_EXECUTION | 87 |
| **38** | refactor | extract the loop into a helper | `python.refactor.extract_function.v1` | **SERVED** | 44 |
| 39 | review | API design review | `python.source.secret_scan.v1` | STATED_SWE_EFFECT_UNSERVED | 41 |
| **40** | review | security review | `python.review.diff_security_gate.v1` | **SERVED** | 44 |
| 41 | review | dependency CVE audit | none | STATED_SWE_EFFECT_UNSERVED | 2 |
| 42 | git | commit with a clear message | `git.repository.operate.v1` | R3_WEAK_EVIDENCE | 47 |
| 43 | git | branch and commit there | `git.history.bisect_regression.v1` | LIVE_CONTROLLER_EXECUTION | 57 |
| 44 | git | diff against HEAD~1 | `git.history.bisect_regression.v1` | LIVE_CONTROLLER_EXECUTION | 91 |
| 45 | git | cherry-pick the last commit | none | STATED_SWE_EFFECT_UNSERVED | 1 |
| 46 | git | changelog for the last three commits | none | STATED_SWE_EFFECT_UNSERVED | 2 |
| 47 | design | ADR for a rate limiter | none | RAW_GOAL_COMPILATION_GAP | 65 |
| 48 | design | migration plan 3.9 → 3.12 | `python.source.crossfile_edit.choreograph.v1` | EDIT_PLAN_INPUT_INVALID | 38 |
| 49 | design | design doc for a package split | none | RAW_GOAL_COMPILATION_GAP | 417 |

## Appendix B — the 33 refused capability-matrix cases

`extract_function` (REGION_INVALID), `move_function` (EFFECT_UNSERVED), `add_type_hints`,
`extract_constant`, `write_unit_test`, `git_blame`, `add_logging`, `implement_issue`,
`ambiguous_fix_it`, `setup_ci`, `idempotent_refusal` (ROUTE_ADMISSION_REJECTED), `format_file`,
`find_definition`, `create_pyproject`, `git_branch`, `add_cli_flag`, `crossfile_feature`
(RAW_GOAL_COMPILATION_GAP), `security_audit`, `measure_coverage`, `missing_source`
(EFFECT_UNSERVED), `add_dependency`, `git_commit`, `fix_failing_ci` (LIVE_CONTROLLER_EXECUTION),
`add_case_test`, `add_retries` (PROMISED_SOURCE_CHANGE_NOT_APPLIED), `tests_from_docstrings`
(CAPABILITY_RETURNED_A_VERDICT), `find_callers` (ANSWER_SCOPE_UNPROVEN), `explain_bug`
(STATED_ANSWER_NOT_PROVIDED), `lint`, `typecheck` (REVIEW_RAN_AND_RETURNED_A_VERDICT),
`read_request_intact` (STATED_ANSWER_NOT_PROVIDED), `bisect_regression`
(STATED_ANSWER_NOT_PROVIDED), `delete_file` (STEP_RAISED_OUTCOME_UNKNOWN).

`find_callers` refusing `ANSWER_SCOPE_UNPROVEN` while the advanced census answers the callers of a
real tree is the same defect the answer gate fixed on 2026-10-31 — **the scope proof is the part
that has not caught up**, not the capability.

## Appendix C — reproduce

```bash
python3 execution_guard/swe_advanced_probe_v1.py --floor 0 --json /tmp/adv.json
python3 execution_guard/swe_capability_matrix_v1.py --json > /tmp/mat.json
python3 hardcore_swe_surface_probe_20261030.py --jobs 4 --json /tmp/surf.json
PYTHONPATH=. python3 -m unittest discover -s canonical/tests -t canonical/tests -p "test_*capabilit*.py"
python3 -c "from canonical.runtime.live_integrated_brain_v1 import load_verified_registry as L; r=dict(L()); print(len(r))"
```

## What this document is not

It is not a plan to make the machine *seem* more capable. Every line is a measured refusal, a
measured absence, or a measured red law. It also does not soften the headline: **4 of 49** advanced
sentences, **21 of 54** ordinary cases, **85** SWE rows of which **19** are ever reached, and a
substrate missing **26 of the 37** tools the work needs. The value of the list is that the next
hour can be spent where the reach is largest — §8, item 1 — instead of where the last refusal
happened to land.
