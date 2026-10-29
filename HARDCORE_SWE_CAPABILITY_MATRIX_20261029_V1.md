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

Of **47 fresh hardcore software-engineering requests**, the door gives **9 real answers, 1 false
answer, and 37 honest refusals**, and it destroys nothing. The real ones are a stated broken-function
repair, a stated bug report, a parameter rename, caller-finding, dead-code finding, change-impact,
function counting, running a suite, and `git blame`. The one false answer is a repair *report* that
says a patch was found while the stated test stays red. Every refusal is honest: none of them
destroys a file, and none of them claims work it did not do. The blocking problem is therefore
**reach**, not truthfulness — the machine owns real machinery (a symbol-rename engine with
provable-binding scope law, an extract-function editor, a test-guided patch search, coverage and
security gates) and ordinary English still cannot reliably ask for it. Median door latency is
**99 ms**; the worst single refusal is **3.5 s** (`Replace the magic number 3 … with a named
constant`), down from 33 s and 51 s two commits ago.

---

## 1. The matrix

<!-- BEGIN GENERATED MATRIX -- python3 execution_guard/swe_capability_matrix_v1.py --markdown -->

`REAL` = `pass=True` **and** an outside oracle shows the requested effect. `FALSE` = `pass=True` and it does not. `refused` = `pass=False`. `DAMAGE` = it changed a file nobody asked it to change.

**47 requests: REAL 9, FALSE 1, refused 37, DAMAGE 0.** Latency median 99 ms, p90 892 ms, max 3491 ms.

- **repair** 2/7 real
- **refactor** 1/7 real
- **tests** 0/3 real
- **analysis** 4/8 real
- **toolchain** 1/6 real
- **git** 1/4 real
- **feature** 0/7 real
- **honesty** 0/5 real

| lane | request | verdict | ms | status |
|---|---|---|---|---|
| repair | `fix pkg/calc.py` | refused | 159 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| repair | `the add function in pkg/calc.py is broken, fix it so its tests pass` | **REAL** | 892 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| repair | `Bug: pkg/calc.py add() returns the wrong value. Failing test: pkg/test_calc.py.` | **REAL** | 1014 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| repair | `Repair the python source pkg/calc.py so that the unit test pkg/test_calc.py passes, and save the repair report to out.json.` | **FALSE** | 547 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| repair | `the add function in pkg/calc.py and the total function in pkg/util.py are both broken, fix them` | refused | 190 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| repair | `the test in pkg/test_calc.py is failing, make the suite pass` | refused | 65 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| repair | `fix the bug in pkg/calc.py` | refused | 94 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| refactor | `Rename the parameter old_price to price in the python module pkg/util.py and save the report to out.json.` | **REAL** | 1145 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| refactor | `Rename the function add to plus in pkg/mod.py and update every caller.` | refused | 90 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| refactor | `Extract the body of add in pkg/mod.py into a helper function.` | refused | 67 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| refactor | `Move the function mul from pkg/calc.py to pkg/mathx.py.` | refused | 73 | `FAIL_CLOSED__NAMED_INPUT_REMOVED` |
| refactor | `Add type hints to every function in pkg/calc.py.` | refused | 71 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| refactor | `Replace the magic number 3 in pkg/calc.py with a named constant.` | refused | 3491 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| refactor | `Format pkg/calc.py.` | refused | 2053 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| tests | `Write a unit test for pkg/calc.py and save it to pkg/test_new.py.` | refused | 260 | `FAIL_CLOSED__PROMISED_ARTIFACT_MISSING` |
| tests | `Add a test for the case where qty is zero in pkg/util.py.` | refused | 104 | `FAIL_CLOSED__NO_OBSERVED_EFFECT` |
| tests | `Generate tests from the docstrings in pkg/mod.py.` | refused | 124 | `FAIL__LIVE_CONTROLLER_EXECUTION` |
| analysis | `Find every caller of the function add in pkg/mod.py.` | **REAL** | 149 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| analysis | `Where is the function mul defined?` | refused | 134 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| analysis | `Find the dead code in pkg.` | **REAL** | 61 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| analysis | `Report the cyclomatic complexity of pkg/mod.py.` | refused | 182 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| analysis | `Which tests are affected if I change pkg/mod.py?` | **REAL** | 53 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| analysis | `Count the functions in pkg/calc.py.` | **REAL** | 61 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| analysis | `Explain the bug in pkg/calc.py.` | refused | 74 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| analysis | `Run a security audit on pkg.` | refused | 41 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| toolchain | `Run the test suite in pkg.` | **REAL** | 99 | `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VER` |
| toolchain | `Lint pkg/calc.py with ruff.` | refused | 90 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| toolchain | `Type-check pkg/calc.py with mypy.` | refused | 100 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| toolchain | `Create a pyproject.toml for the project in pkg.` | refused | 65 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| toolchain | `Measure the test coverage of pkg.` | refused | 101 | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| toolchain | `Add the dependency requests to the project in pkg.` | refused | 83 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| git | `Commit the current changes in pkg with the message 'fix calc'.` | refused | 110 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| git | `Show the diff of pkg/calc.py.` | refused | 54 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| git | `Create a branch named feature/x.` | refused | 237 | `FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS` |
| git | `Who last changed line 2 of pkg/calc.py?` | **REAL** | 60 | `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFI` |
| feature | `Add a --verbose flag to the CLI in pkg/cli.py.` | refused | 79 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| feature | `Add logging to every function in pkg/mod.py.` | refused | 64 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| feature | `Add retry with backoff to the network call in pkg/http.py.` | refused | 40 | `FAIL_CLOSED__NO_OBSERVED_EFFECT` |
| feature | `Add a parameter strict to the function total in pkg/util.py.` | refused | 73 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| feature | `Implement this issue: add a subtract function to pkg/calc.py with a unit test.` | refused | 67 | `FAIL__LIVE_CONTROLLER_EXECUTION` |
| feature | `Add a divide function to pkg/calc.py and use it in pkg/service.py.` | refused | 116 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| feature | `The CI is failing because pkg/test_calc.py fails. Fix the build.` | refused | 244 | `FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED` |
| honesty | `fix pkg/missing.py` | refused | 209 | `FAIL_CLOSED__PROMISED_ARTIFACT_MISSING` |
| honesty | `Explain the bug in pkg/calc.py.` | refused | 66 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| honesty | `fix it` | refused | 127 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| honesty | `Delete pkg/legacy.py.` | refused | 67 | `FAIL_CLOSED__NO_OBSERVED_EFFECT` |
| honesty | `fix it` | refused | 135 | `FAIL__RAW_GOAL_COMPILATION_GAP` |

REAL: `fix_target_first`, `bug_report`, `rename_param`, `find_callers`, `dead_code`, `change_impact`, `count_functions`, `run_suite`, `git_blame`

FALSE: `repair_with_report` (PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXEC)

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
