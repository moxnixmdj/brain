# What it takes, and what is in the way — the hardcore software-engineering matrix

Measured 2026-10-29 on `arena/47739ce8-brain` (`5b58fe0`, base `main` `e2d7981`).
Authority: **NONE**. This is a sandbox measurement, not an independent verification. Credit: **0**.
Producer cognition model dependency: **0**. Incremental spend: **$0**.

Every number below comes from running the front door on a **fresh tree per case** and then judging
it by something that is not the machine's own report: the file's bytes, a real `python -m unittest`
exit code, a real command's output, or the artifact the run wrote. Nothing is inferred from reading
code. The matrix is reproducible: 45 requests, one door call each.

---

## 0. The answer in one paragraph

On **45 fresh hardcore software-engineering requests** the door gives **8 real answers, 3 false
answers, and 34 honest refusals**. The 8 real ones are a verb-first repair, a stated bug report,
caller-finding, dead-code finding, change-impact, function counting, running a suite, and `git
blame`. The 3 false ones are a repair report that says a patch was found while the test stays red, a
"security audit" that is a symbol count, and a "coverage measurement" that never measures coverage.
The 34 refusals cover **every** refactor, every test-authoring request, every git request except
blame, the whole build/dependency/packaging lane, and every request to add a feature. So the
blocking problem is no longer lying (that is down to 3, from 2 false passes in a 12-request probe a
few hours earlier); it is **reach**: the machine owns real machinery and cannot be asked for it in
ordinary English. Median door latency is **86 ms**, but the two worst refusals take **33 s and 51 s**,
because the composer route spends that time running **5,046 subprocesses** discovering the
environment before deciding it cannot do the job.

---

## 1. The matrix

`REAL` = `pass=True` **and** the world shows the requested effect. `FALSE` = `pass=True` and it does
not. `refused` = `pass=False` (honest, unless the effect was trivially available).

| lane | request | verdict | ms | status |
|---|---|---|---|---|
| repair | `fix <calc.py>` | refused | 186 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| repair | `the add function in <calc.py> is broken, fix it so its tests pass` | **REAL** | 813 | `PASS__…ADAPTER_EXECUTED_AND_VERIFIED` |
| repair | `Bug: <calc.py> add() returns the wrong value. Failing test: <test_calc.py>.` | **REAL** | 905 | `PASS__…ADAPTER_EXECUTED_AND_VERIFIED` |
| repair | `Repair <calc.py> so <test_calc.py> passes, save the repair report to <out.json>` | **FALSE** | 512 | `PASS__…` (`PASS__VERIFIED_MULTI_EDIT_PATCH_FOUND`, test still red) |
| repair | `the add function in <calc.py> and the total function in <util.py> are both broken, fix them` | refused | 180 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| repair | `the test in <test_calc.py> is failing, make the suite pass` | refused | 78 | `FAIL_CLOSED__NO_OBSERVED_EFFECT` |
| repair | `fix the bug in <calc.py>` | refused | 89 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| refactor | `Rename the parameter old_price to price in the python module <util.py> and save the report to <out.json>` | refused | 696 | `FAIL__LIVE_CONTROLLER_EXECUTION` |
| refactor | `Rename the function add to plus in <mod.py> and update every caller` | refused | 74 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| refactor | `Extract the body of add in <mod.py> into a helper function` | refused | 63 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| refactor | `Move the function mul from <calc.py> to <mathx.py>` | refused | 75 | `FAIL_CLOSED__NAMED_INPUT_REMOVED` |
| refactor | `Add type hints to every function in <calc.py>` | refused | 60 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| refactor | `Replace the magic number 3 in <calc.py> with a named constant` | refused | **33,396** | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| refactor | `Format <calc.py>` | refused | **51,548** | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| tests | `Write a unit test for <calc.py> and save it to <test_new.py>` | refused | 208 | `FAIL_CLOSED__PROMISED_ARTIFACT_MISSING` |
| tests | `Add a test for the case where qty is zero in <util.py>` | refused | 83 | `FAIL_CLOSED__NO_OBSERVED_EFFECT` |
| tests | `Generate tests from the docstrings in <mod.py>` | refused | 142 | `FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED` |
| analysis | `Find every caller of the function add in <mod.py>` | **REAL** | 119 | `PASS__…` (artifact names the two real callers) |
| analysis | `Where is the function mul defined?` | refused | 86 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| analysis | `Find the dead code in <pkg>` | **REAL** | 40 | `PASS__…` (`unused_helper` named) |
| analysis | `Report the cyclomatic complexity of <mod.py>` | refused | 116 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| analysis | `Which tests are affected if I change <mod.py>?` | **REAL** | 36 | `PASS__…` |
| analysis | `Count the functions in <calc.py>` | **REAL** | 47 | `PASS__…` (`function_count: 2`) |
| analysis | `Explain the bug in <calc.py>` | refused | 74 | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` |
| analysis | `Run a security audit on <pkg>` | **FALSE** | 34 | `PASS__…EXACT_SEMANTIC_ACCEPTANCE` (`python.source.audit.ast`, `function_count: 6`) |
| toolchain | `Run the test suite in <pkg>` | **REAL** | 98 | `PASS__…` |
| toolchain | `Lint <calc.py> with ruff` | refused | 86 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| toolchain | `Type-check <calc.py> with mypy` | refused | 82 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| toolchain | `Create a pyproject.toml for the project in <pkg>` | refused | 69 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| toolchain | `Measure the test coverage of <pkg>` | **FALSE** | 95 | `PASS__…` (`python.repository.acceptance.measure.v1`, no coverage) |
| toolchain | `Add the dependency requests to the project in <pkg>` | refused | 76 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| git | `Commit the current changes in <pkg> with the message 'fix calc'` | refused | 114 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| git | `Show the diff of <calc.py>` | refused | 47 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| git | `Create a branch named feature/x` | refused | 218 | `FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS` |
| git | `Who last changed line 2 of <calc.py>?` | **REAL** | 52 | `PASS__…EXACT_SEMANTIC_ACCEPTANCE` |
| feature | `Add a --verbose flag to the CLI in <cli.py>` | refused | 77 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| feature | `Add logging to every function in <mod.py>` | refused | 53 | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` |
| feature | `Add retry with backoff to the network call in <http.py>` | refused | 32 | `FAIL_CLOSED__NO_OBSERVED_EFFECT` |
| feature | `Implement this issue: add a subtract function to <calc.py> with a unit test` | refused | 56 | `FAIL__LIVE_CONTROLLER_EXECUTION` |
| feature | `Add a divide function to <calc.py> and use it in <service.py>` | refused | 99 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| feature | `The CI is failing because <test_calc.py> fails. Fix the build` | refused | 206 | `FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED` |
| honesty | `fix <pkg/missing.py>` | refused | 181 | `FAIL_CLOSED__PROMISED_ARTIFACT_MISSING` (nothing created) |
| honesty | `Explain the bug in <calc.py>` | refused | 70 | source left byte-identical |
| honesty | `fix it` | refused | 89 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| honesty | `Delete <legacy.py>` | refused | 48 | `FAIL_CLOSED__NO_OBSERVED_EFFECT` (the deletion itself is not counted as an effect) |

**Totals: REAL 8 · FALSE 3 · REFUSED 34 · destroyed files 0.**
Latency: median **86 ms**, p90 **696 ms**, max **51,548 ms**.

---

## 2. What changed today, so the numbers above are not stale

Four commits, all on `arena/47739ce8-brain`, each a reuse of machinery that was already in the tree:

| commit | defect it removed | measured before → after |
|---|---|---|
| `3671140` | a repair sentence that names its target **before** the verb promised nothing | `PASS` over a byte-identical file, test red → real in-place repair, test green |
| `4340001` | a **bug report** has no imperative, so it promised nothing either | `PASS` over an unchanged file → the promise is read from the statement |
| `1f5f86d` | the planner answered "fix this Python bug" with a **DOCX writer** | one entry in `swe_typed_plan_v1._FAMILIES` → `repair.apply.verified` lands the patch |
| `f3f69c5`, `5b58fe0` | a **report capability wrote its JSON over the file it was asked about** | 7 files destroyed across the matrix → **0**, with the answer still produced |

The last one is the important one for an agent: `Explain the bug in <S>`, `Count the functions in
<S>`, `fix <S>`, `add a test for …`, `add retry … to <S>`, `generate tests from <S>`, `the CI is
failing because <T> fails` all used to end with a 32-byte source replaced by a 545-byte JSON report.
The rule now lives where it already lived — `repair_output_collisions` — and is decided by the
**capability's own declaration** (`capability_edits_source`), not by the sentence's grammar; the
composer calls that function instead of carrying a copy.

---

## 3. The problem list, in the order that blocks "most advanced software engineer"

### P0-1 · Three false passes remain, all one mechanism: the capability's own `expect` is read as the sentence's goal

```
"Run a security audit on <pkg>"
  → PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE
  → python.source.audit.ast, function_count: 6      ← a symbol audit, not a security audit

"Measure the test coverage of <pkg>"
  → PASS   python.repository.acceptance.measure.v1  ← measurement metadata, no coverage number

"Repair <calc.py> … save the repair report to <out.json>"
  → PASS   PASS__VERIFIED_MULTI_EDIT_PATCH_FOUND    ← a patch was found; the source was restored
                                                     and the stated test is still red
```

The door now knows how to refuse this shape when the sentence asks a **question**
(`FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED`, added in `f3f69c5`) but it does not do it for the whole
class. The fix is the same one, generalised: a stated **effect family** (audit, coverage, security,
performance, complexity) must be present in the capability's own declared surface, exactly as the
explanation case already is. That is one function, and its refusal already exists.

### P0-2 · The two slowest refusals take 33 s and 51 s on a five-line file

```
"Format <calc.py>"                      → 51,548 ms to refuse
"Replace the magic number 3 in <calc.py>" → 33,396 ms to refuse
median door call                          →     86 ms
```

Profile of the 51 s refusal:

```
48.97 s  solve
48.75 s   └ _try_composed
48.75 s      └ composer_route.route
46.39 s         └ computer_env_v1.discover
39.32 s            └ computer_env_v1.act ×442 → 5,046 subprocess.run calls
33.88 s         └ transfer_learning_v1.drive → environment_learning_v1.learn_model ×15
```

**5,046 subprocesses and 34 s of "learning the environment"** before answering "I cannot format this
file". The requirement is that everything is insanely fast; 18 ms of work and 51 s of discovery is
the single largest violation in the system, and it is a plain caching/ordering defect: discovery is
run synchronously inside routing, on the failure path, with no memoisation.

### P0-3 · The three refactor capabilities are owned, real, and unreachable

`rename_param`, `rename_symbol`, `extract_function` are refused at the door with four different
statuses. The adapters exist and are exercised by their own suites (which are themselves red — see
the earlier inventory §4.2). This is the cheapest capability win available: the code that renames a
symbol across two files already works when driven directly.

### P0-4 · There is no git lane

`commit`, `diff`, `branch` are all refused; `blame` passes. A software engineer who cannot commit,
diff or branch is not one, whatever the analysis depth.

### P0-5 · There is no build / dependency / packaging lane

`pyproject.toml`, dependency addition, ruff, mypy, coverage are all refused — and ruff/mypy are not
even installed (earlier inventory §4.1), so a refusal here is at least honest.

### P0-6 · Test authoring is 0/3

`Write a unit test for <S>` fails `PROMISED_ARTIFACT_MISSING` (a report capability was selected for a
file-writing request — the §2.2/§2.3 seam again), `Add a test for the case …` fails
`NO_OBSERVED_EFFECT`, `Generate tests from the docstrings in <S>` fails `COMPOSED_CHAIN_NOT_VERIFIED`.

### P0-7 · Feature work is 0/6

Adding a CLI flag, logging, retries, a cross-file feature, an issue implementation, or fixing a
failing CI build: six requests, six refusals. This is the lane that separates "a tool that repairs
one bug" from "an engineer", and it has no composition path today.

### P0-8 · Multi-file repair is refused

`fix the add in <calc.py> and the total in <util.py>` → `RAW_GOAL_COMPILATION_GAP`. Everything the
repair family does is single-file by construction.

### P1 · Analysis is real but narrow: 4/8

Working: caller-finding, dead code, change impact, function count. Refused: definition lookup,
cyclomatic complexity, explanation.

### P1 · Destructive requests are refused and a symbol move is a file operation

`Delete <legacy.py>` → `NO_OBSERVED_EFFECT` (a deletion is not counted as an effect).
`Move the function mul from <A> to <B>` used to **delete `<A>` and report a PASS**; it is now
`NAMED_INPUT_REMOVED`, which is honest but still not the operation that was asked for.

### P2 · Self-description

125 registry rows, all `VERIFIED_BOUND_CAPABILITY`; 63 are SWE-ish. The earlier inventory measured
that 20 of 64 certify themselves by reading the registry and that 294 of 419 advertised
"capabilities" are historical receipts. That number was not re-measured today and should be treated
as an upper bound on the truth of the registry.

---

## 4. What the most advanced SWE agent needs that is not here at all

Judged against the matrix, these have **no lane**:

1. **Multi-step planning on a real repository** — an issue in, a reviewable diff out, with the test
   suite as the gate. (`issue_to_pr.orchestrate` exists as a row; no sentence has ever reached it.)
2. **Honest incremental editing** — the whole "change this, keep that" class: add a parameter, add a
   flag, add logging, thread a value through three files.
3. **A debugger loop** — run, read the traceback, form a hypothesis, patch, re-run. Only the last
   step exists.
4. **A git lane** — commit, diff, branch, stash, revert, and eventually bisect.
5. **A real toolchain** — ruff, mypy, coverage, pytest installed and pinned, so "lint", "type-check",
   "coverage" are measurements rather than refusals.
6. **Cost/timing as a first-class quantity** — the registry's cost field is the constant `1`, so
   "fastest" cannot currently be chosen; and the one measured 51 s refusal shows what that costs.

---

## 5. What I would do next, in this order, all reuse

| # | action | why it is first | reuse |
|---|---|---|---|
| 1 | Cache + bound `computer_env_v1.discover` inside routing; never run it on the failure path | 51 s → milliseconds on the worst path; the "insanely fast" requirement | the discovery result is already a value; it needs a memo keyed by tree fingerprint |
| 2 | Generalise `stated_answer_errors` to every stated effect family (audit, coverage, security, complexity) | removes the last 3 false passes | the function exists; the effect vocabulary for audit/coverage is already in `_EFFECT_WORDS` |
| 3 | Route refactor requests to the adapters that already rename/extract | 0/7 → several real answers; the code works when driven | `swe_typed_plan_v1._FAMILIES` + `capability_selection_retrieval_v1.admit` |
| 4 | Add a git lane over the same family mechanism | commit/diff/branch are table stakes | `git` is available; the family table and `shell.command.run` already exist |
| 5 | Make the test-authoring request compile to a file-writing capability, not a report | 0/3 → 3/3 potential | the §2.3 seam plus `text.file.write` |
| 6 | Multi-file repair | 0/2 today; the repair loop is single-file by construction | two sequential repair runs over the same tree, which the composer can already chain |

---

## 6. Limits of this document

- 45 requests is a sample, not a census. Each case is one cold run on a fresh tree; no case was
  repeated three times here except where the earlier documents say so.
- The oracles are filesystem/exit-code/oracle-artifact checks, not human judgement of code quality.
  A case can be `REAL` and still be a poor piece of engineering.
- Requests that need the network, a package install, or a real git remote were not exercised.
- The registry census (P2) is carried over from the earlier inventory and was **not** re-measured
  today; it is quoted as an upper bound, not as a fresh fact.
