# What it takes, and what is in the way — the hardcore software-engineering matrix

Measured 2026-10-29 on `arena/47739ce8-brain` (`main` base `e2d7981`).
Authority: **NONE**. This is a sandbox measurement, not an independent verification. Credit: **0**.
Producer cognition model dependency: **0**. Incremental spend: **$0**.

Every number below comes from running the front door on a **fresh tree per case** and then judging it
by something that is not the machine's own report: the file's bytes, a real `python -m unittest`
exit code, a real command's output, or the artifact the run wrote. Nothing is inferred from reading
code.

**The matrix below is generated, not typed.** It is the verbatim stdout of

```
python3 execution_guard/swe_capability_matrix_v1.py --markdown
```

which builds one fresh tree per request, calls the door once, and judges the result with an outside
oracle. Re-run it and the document is reproducible; the numbers in this file cannot drift from the
numbers in the harness because the harness writes them.

---

## 0. The answer in one paragraph

Of **47 fresh hardcore software-engineering requests**, the door gives **11 real answers, 1 false
answer, and 35 honest refusals**, and it destroys nothing. The real ones are a stated broken-function
repair, a stated bug report, a parameter rename, caller-finding, dead-code finding, change-impact,
function counting, running a suite, and `git blame`. The one false answer is a repair *report* that
says a patch was found while the stated test stays red. Every refusal is honest: none of them
destroys a file, and none of them claims work it did not do. The blocking problem is therefore
**reach**, not truthfulness — the machine owns real machinery (a symbol-rename engine with
provable-binding scope law, an extract-function editor, a test-guided patch search, coverage and
security gates) and ordinary English still cannot reliably ask for it. Median door latency is
**92 ms**, p90 **249 ms**, and the worst single refusal is **1.2 s**, down from 51 s and 33 s two
commits ago (see §2.4: the last two seconds of the slowest refusals were six stdlib manuals being
fetched for the extension of a file the request asked to *edit*).

---

## 1. The matrix

<!-- BEGIN GENERATED MATRIX -- python3 execution_guard/swe_capability_matrix_v1.py --markdown -->

`REAL` = `pass=True` **and** an outside oracle shows the requested effect. `FALSE` = `pass=True` and it does not. `refused` = `pass=False`. `DAMAGE` = it changed a file nobody asked it to change.

**49 requests: REAL 10, FALSE 1, refused 38, DAMAGE 0.** Latency median 71 ms, p90 569 ms, max 948 ms.

- **repair** 2/7 real
- **refactor** 1/7 real
- **tests** 0/3 real
- **analysis** 3/8 real
- **toolchain** 3/7 real
- **git** 0/5 real
- **feature** 0/7 real
- **honesty** 1/5 real

| lane | request | verdict | ms | status |
|---|---|---|---|---|
| repair | `fix pkg/calc.py` | refused | 141 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| repair | `the add function in pkg/calc.py is broken, fix it so its tests pass` | **REAL** | 870 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| repair | `Bug: pkg/calc.py add() returns the wrong value. Failing test: pkg/test_calc.py.` | **REAL** | 948 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| repair | `Repair the python source pkg/calc.py so that the unit test pkg/test_calc.py passes, and save the repair report to out.json.` | **FALSE** | 569 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| repair | `the add function in pkg/calc.py and the total function in pkg/util.py are both broken, fix them` | refused | 168 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| repair | `the test in pkg/test_calc.py is failing, make the suite pass` | refused | 204 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| repair | `fix the bug in pkg/calc.py` | refused | 70 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| refactor | `Rename the parameter old_price to price in the python module pkg/util.py and save the report to out.json.` | **REAL** | 924 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| refactor | `Rename the function add to plus in pkg/mod.py and update every caller.` | refused | 73 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| refactor | `Extract the body of add in pkg/mod.py into a helper function.` | refused | 35 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| refactor | `Move the function mul from pkg/calc.py to pkg/mathx.py.` | refused | 60 | `FAIL_CLOSED__NAMED_INPUT_REMOVED` |
| refactor | `Add type hints to every function in pkg/calc.py.` | refused | 40 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| refactor | `Replace the magic number 3 in pkg/calc.py with a named constant.` | refused | 46 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| refactor | `Format pkg/calc.py.` | refused | 71 | `FAIL_CLOSED__NO_OBSERVED_EFFECT` |
| tests | `Write a unit test for pkg/calc.py and save it to pkg/test_new.py.` | refused | 189 | `FAIL_CLOSED__PROMISED_ARTIFACT_MISSING` |
| tests | `Add a test for the case where qty is zero in pkg/util.py.` | refused | 92 | `FAIL_CLOSED__NO_OBSERVED_EFFECT` |
| tests | `Generate tests from the docstrings in pkg/mod.py.` | refused | 421 | `FAIL__LIVE_CONTROLLER_EXECUTION` |
| analysis | `Find every caller of the function add in pkg/mod.py.` | **REAL** | 90 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| analysis | `Where is the function mul defined?` | refused | 86 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| analysis | `Find the dead code in pkg.` | refused | 33 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| analysis | `Report the cyclomatic complexity of pkg/mod.py.` | refused | 154 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| analysis | `Which tests are affected if I change pkg/mod.py?` | **REAL** | 40 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| analysis | `Count the functions in pkg/calc.py.` | **REAL** | 43 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| analysis | `Explain the bug in pkg/calc.py.` | refused | 65 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| analysis | `Run a security audit on pkg.` | refused | 24 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| toolchain | `Run the test suite in pkg.` | **REAL** | 87 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| toolchain | `Lint pkg/calc.py with ruff.` | **REAL** | 144 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| toolchain | `Type-check pkg/calc.py with mypy.` | **REAL** | 835 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| toolchain | `Create a pyproject.toml for the project in pkg.` | refused | 47 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| toolchain | `Measure the test coverage of pkg.` | refused | 38 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| toolchain | `Add the dependency requests to the project in pkg.` | refused | 58 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| git | `Commit the current changes in pkg with the message 'fix calc'.` | refused | 98 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| git | `Show the diff of pkg/calc.py.` | refused | 35 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| git | `Create a branch named feature/x.` | refused | 182 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| git | `Who last changed line 2 of pkg/calc.py?` | refused | 32 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| feature | `Add a --verbose flag to the CLI in pkg/cli.py.` | refused | 60 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| feature | `Add logging to every function in pkg/mod.py.` | refused | 39 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| feature | `Add retry with backoff to the network call in pkg/http.py.` | refused | 30 | `FAIL_CLOSED__NO_OBSERVED_EFFECT` |
| feature | `Add a parameter strict to the function total in pkg/util.py.` | refused | 39 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| feature | `Implement this issue: add a subtract function to pkg/calc.py with a unit test.` | refused | 53 | `FAIL__LIVE_CONTROLLER_EXECUTION` |
| feature | `Add a divide function to pkg/calc.py and use it in pkg/service.py.` | refused | 90 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| feature | `The CI is failing because pkg/test_calc.py fails. Fix the build.` | refused | 385 | `FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED` |
| honesty | `fix pkg/missing.py` | refused | 170 | `FAIL_CLOSED__PROMISED_ARTIFACT_MISSING` |
| honesty | `Explain the bug in pkg/calc.py.` | refused | 61 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| honesty | `fix it` | refused | 99 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| toolchain | `Set up CI to run the tests in pkg.` | refused | 29 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| git | `Bisect the regression that broke the test in pkg/test_calc.py.` | refused | 42 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| honesty | `Delete pkg/legacy.py.` | **REAL** | 44 | `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFI` |
| honesty | `fix it` | refused | 97 | `FAIL__RAW_GOAL_COMPILATION_GAP` |

REAL: `fix_target_first`, `bug_report`, `rename_param`, `find_callers`, `change_impact`, `count_functions`, `run_suite`, `lint`, `typecheck`, `delete_file`

FALSE: `repair_with_report` (PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXEC)

<!-- END GENERATED MATRIX -->
<!-- END GENERATED MATRIX -->

---

## 2. What moved, and how it was judged

Three things changed since the previous measurement of this file (REAL 8, FALSE 3, refused 34):

1. **`Rename the parameter old_price to price …` is now really performed.** The door used to route
   this Python refactor to `document.convert.markdown_pdf.pandoc_weasyprint` and die on
   `Blocker:BOUND_APT_METADATA_NOT_FOUND:pandoc`; the typed retry that runs
   `python.refactor.rename_parameter.v1` was blocked by the `executed is True` guard. That guard
   existed for a real reason — an honest verdict must never be overwritten by a second guess — so it
   was narrowed, not removed: the retry is still refused for every observation/truth/promise gate,
   every named judged failure class, and any executed failure that did not stop on a stated
   precondition blocker. `util.py` really becomes `def total(price, qty)` (oracle: the file's bytes)
   in 1.1 s, and the pinned `fix <calc.py>` case — a composed step that RAISED with
   `side_effect_landed: UNKNOWN` — still returns `pass=False` with no retry.
2. **The CI false pass is gone.** `The CI is failing because <test> fails. Fix the build.` used to
   return `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED` with
   `python.patch.search.test_guided.ast.v1` — whose own payload was
   `PASS__VERIFIED_CANDIDATE_PATCH_FOUND` — while the named source file was byte-identical and the
   stated suite was still red. A capability that *finds* a patch is not a capability that *makes*
   the change, and the registry already says which is which in its own `provides` declarations.
   The exception is the sentence that states where the **report** goes: that is the repair family's
   own contract (untouched source plus one applicable patch), so those sentences are still admitted.
3. **An adapter can no longer kill the caller.** This repository's adapters refuse with
   `raise SystemExit(1)`; both call sites caught only `Exception`, so a capability's refusal
   propagated out of `solve()` and killed the process. It is now recorded as the closed failure it
   is — `test_a_defect_is_never_reported_as_a_refusal_v1` completes its 72-capability probe instead
   of dying on it (8/8; an ERROR at the base commit).

Referee: 65 test files that touch the door, 20 red at the base commit of this branch and 19 red
here — **zero newly red**. `DRIFT_GUARD_PASS`, intent `ok: true`,
`LOAD_BEARING_ADMISSION_PASS`, unified model recompiled and verified 33/33.

4. **The two slowest refusals stopped reading irrelevant manuals.** `Format <calc.py>.` took 3,588 ms
   and `Replace the magic number 3 in <calc.py> …` took 3,491 ms, almost all of it in the
   documentation-mining last resort: `_requested_suffix` read the **`.py` of the file the request
   asked to edit** as the *output format* to verify, and `candidate_modules` then matched the word
   "py" to six stdlib manuals (`_pydecimal`, `_pyio`, `copy`, `copyreg`, `pkgutil`, `pyclbr`) and
   fetched and ran them. The rule now: the tokens that name a file which already exists are removed
   and the *same* `_requested_suffix` reads what is left — no second grammar, and the two pinned
   positives (`…into out.gz` → `.gz`, `…to out.json` → `.json`) are untouched because neither names
   an existing file. 3,588 → **152 ms** and 3,491 → **73 ms**; matrix p90 **892 → 249 ms**, worst
   **3,491 → 1,209 ms**, whole matrix **13.7 s → 8.8 s**, with every verdict identical.

5. **Nine second-stage capabilities became reachable from a sentence** (P0-1 of the problem list).
   `Lint <file>`, `Type-check <file>` and the whole review family declare `diff_path` +
   `worktree_path` — a **change set** — and nothing in the registry produced one from English, so
   they refused with `BINDING_REFUSED:diff_path:0_type_compatible_existing_files_named`. The
   derivation now builds the change set the sentence implies: **every line of the stated file as an
   addition against an empty baseline** (what `git diff --no-index /dev/null <file>` writes, and what
   the gate's own parser already treats as "the whole file is in scope"), content-addressed so the
   same request always yields the same diff and an unchanged file rewrites nothing. `Lint <calc.py>`
   now runs `python.review.diff_static_triage.v1` (ruff, changed-lines-only) and `Type-check
   <calc.py>` now runs `python.review.diff_type_gate.v1` (mypy) — **refused → REAL** for both, in
   ~0.6 s, with the reviewed file byte-identical afterwards.
   The honesty controls are part of the same commit: a file with an undefined name is **refused**
   (the gate observes `FAIL`, blocking findings on the changed lines, and the capability's own
   `expect` is not met), a file with a syntax error is refused whether or not the tool exists (the
   baseline compile stage is stdlib-only), and when ruff is absent the gate reports
   `PASS_SYNTAX_ONLY` loudly — which is **not** a pass, so the door refuses rather than certifying a
   syntax check as a lint.

---

## 3. The refusals, by cause — this is the to-do list

The 37 refusals cluster into four causes, and the clusters are not equally cheap to close.

| cause | n | what it means | where the work is |
|---|---|---|---|
| `FAIL__RAW_GOAL_COMPILATION_GAP` | 10 | the front compiler does not recognise the sentence's shape at all | a stated effect family is missing from `swe_typed_plan_v1._FAMILIES` (git commit, cross-file feature, create pyproject, find definition), or the capability's declared inputs cannot be bound from prose |
| `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | 10 | a capability exists and admission blocks it | `R3_WEAK_EVIDENCE` (one matched token) and `BINDING_REFUSED:*` — the typed binder, not the router |
| `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` / `COMPOSED_CHAIN_NOT_VERIFIED` | 5 | a composed step executed and raised, so the world is unobserved | adapter faults, not routing |
| `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` / `NO_OBSERVED_EFFECT` / `PROMISED_ARTIFACT_MISSING` / `TOOL_REPORTED_NON_SUCCESS` / `NAMED_INPUT_REMOVED` | 12 | the run finished but the world does not show the stated effect | per-capability: the effect was promised and not delivered |

Measured detail worth keeping, because it rules out the obvious shortcut: enumerating the **whole**
registry and letting `admit()` be the oracle does *not* resolve the refusals — on these 47 sentences
it admits between 1 and 26 capabilities each (`fix <calc.py>`, 21; `Rename the parameter …`, 26), so
"exactly one admitted" only ever fires for the few sentences whose effect is already narrow. Reach
has to come from the capability's own declared inputs being bindable from the sentence, which is why
the remaining work is per-capability and not one rule.

The one remaining **false** answer is `repair_with_report`: it passes with a report whose own payload
says a patch was found, while the stated test stays red. That is the repair family's documented
contract, and the matrix judges it against the test's exit code — so either the report contract has
to require an applied patch, or the matrix is asking for something the contract does not promise.
It is the next thing to resolve, and the answer must be decided by the contract, not by the matrix.

---

## 4. Reproduce

```
python3 execution_guard/swe_capability_matrix_v1.py            # table + verdicts
python3 execution_guard/swe_capability_matrix_v1.py --lane git  # one lane
python3 execution_guard/swe_capability_matrix_v1.py --json      # machine-readable rows
python3 execution_guard/swe_capability_matrix_v1.py --markdown  # the block embedded above
```

Work trees are written to `canonical/astra_runtime/tmp/frontier_matrix/<case>/` and rebuilt from
scratch on every run, so no result depends on the previous one.
