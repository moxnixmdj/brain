# Every problem between this machine and a hardcore software engineer — V4

**Tree:** `main @ 9e6a366` (current at the time of writing, 20,913 commits of history),
measured in a detached worktree (`/tmp/bt2`) so the measurement could not contaminate the tree it
read. This tree contains the two fixes I landed earlier today (PR #6465: answer shape + stated
operation), main's own stated-effect gate, and five effect rules that landed in between (see §12).

A first pass was measured on `2e9b642`; **60 of 61 rows behaved identically**. The one that
differed (`Which commit broke the tests`) differs because `2e9b642` is the shallow boundary of
this clone — see §11, which is where that caveat belongs and nowhere else.

**Method:** the 62 sentences of V3, minus #16, which named `app/utils.py` — a path that does not
exist in this repository, so it measured nothing. **61 sentences**, each run through the real door
(`live_brain_route_admission_v1.solve`) in its own process, 6 at a time, 70 s cap each, with the
capability each one actually invoked recorded by instrumenting `run_adapter_locally`, and the
artifacts it wrote read back from disk. Every number below was produced by running this tree
today. Wall clock for the whole corpus: **118 s**.

**Scope ruling honoured:** PDF/DOCX/XLSX and document formats are not counted. One sentence in 61
touches that surface (`Extract the helper …`, which V3 measured being routed to
`pdf.extract.ocr.tesseract`) and it now fails closed, so it is not a wrong answer either.

---

## The headline

```
61 hardcore software-engineering sentences, main @ 9e6a366 (20,913 commits of history)
  17  PASS                                       28%
   4  of those deliver a correct answer           6.6%   ← the only number a user feels
   6  are correct artifacts with NO answer delivered         (status / diff / blame / log / bisect)
   1  is a correct artifact contaminated by the machine's own writes
   6  are WRONG and certified                   35% of all passes
   1  times out (70 s, cause measured)
  43  refuse and name what was missing          70%

  14  ask the machine to CHANGE code
   0  change code correctly
```

V3 measured 5 correct and 7 wrong passes out of 12. The fix landed today moved exactly two of
those: `List the functions` and `Show the imports` now deliver the real list, and
`Find every caller` is now *delivered* — as one of seven call sites, certified complete. **A
correct-delivery rate of 4/61 with a 35 % wrong-pass rate is not a software engineer.** It is a
repository question-answerer whose wrong answers have become more confident.

The whole report is one claim: **every one of the six wrong passes is admitted on a verb it does
not implement, and seven of the eleven other correct passes computed the right thing and then
threw it away.** Both are one predicate wide.

---

## §1. The measurement

Legend: **✔** correct and delivered · **◐** correct artifact, not delivered ·
**◐\*** correct but contaminated · **✘** wrong answer returned as PASS · **!** timeout ·
**·** honest refusal.

### A — navigate and understand (10)

| # | sentence | | what happened | time |
|---|---|---|---|---|
| 0 | `Find every caller of build_plan in canonical/runtime/swe_typed_plan_v1.py` | ✘ | index built over **the one file**; delivered `{"build_plan": ["plan_report"]}`, `count: 1`, `truncated: false` | 2.3 s |
| 1 | `Who calls _resolve_family` | · | `STATED_SWE_EFFECT_UNSERVED` | 0.3 s |
| 2 | `Show the definition of _family_terms in …` | · | `STATED_ANSWER_NOT_PROVIDED` | 0.8 s |
| 3 | `List the functions in …/swe_typed_plan_v1.py` | ✔ | 16 module-scope functions, delivered (verified correct by `ast`) | 1.2 s |
| 4 | `Show the imports of …/swe_typed_plan_v1.py` | ✔ | 5 imports, delivered (verified correct) | 1.2 s |
| 5 | `What is the complexity of build_plan` | · | `ROUTE_ADMISSION_REJECTED` | 0.7 s |
| 6 | `Are there any import cycles in canonical/runtime` | · | `ROUTE_ADMISSION_REJECTED` | 1.3 s |
| 7 | `Find duplicated code in canonical/runtime` | · | `STATED_ANSWER_NOT_PROVIDED` | 0.5 s |
| 8 | `Show me the class hierarchy of goal_compiler.py` | · | `ROUTE_ADMISSION_REJECTED` | 0.6 s |
| 9 | `Which modules import …/swe_typed_plan_v1.py` | · | `ROUTE_ADMISSION_REJECTED` | 0.7 s |

### B — change code (14, 0 correct)

| # | sentence | | what happened | time |
|---|---|---|---|---|
| 10 | `Rename the function build_plan to construct_plan in …` | · | `CAPABILITY_REFUSED_SYNTAX_ERROR_IN_FILE` — after doing work | 25.2 s |
| 11 | `Extract the helper from … into a new function` | · | `STATED_SWE_EFFECT_UNSERVED` | 1.0 s |
| 12 | `Inline the helper _request_goal in …` | · | `FAIL__LIVE_CONTROLLER_EXECUTION` | 53.9 s |
| 13 | `Add a parameter to the function build_plan in …` | · | `FAIL__LIVE_CONTROLLER_EXECUTION` | 1.2 s |
| 14 | `Move the function _family_terms to a new module` | · | `FAIL__RAW_GOAL_COMPILATION_GAP` | 1.3 s |
| 15 | `Remove the unused import from …/git_repository_operate.py` | · | `FAIL__LIVE_CONTROLLER_EXECUTION` | 0.7 s |
| 17 | `Repair …/swe_typed_plan_v1.py so the unit test … passes` | ◐ | `BASELINE_ALREADY_PASSES` — correct: `python3 -m unittest` runs 17 tests OK in 4.2 s | 30.7 s |
| 54 | `Write a test for build_plan` | · | `FAIL__RAW_GOAL_COMPILATION_GAP` | 1.1 s |
| 55 | `Generate tests for …/swe_typed_plan_v1.py` | ! | 70 s timeout — see §10; the named file has 16 functions, the run expanded **14,243** | 70.2 s |
| 56 | `Fix the failing tests and report which ones you fixed` | · | `STATED_SWE_EFFECT_UNSERVED` | 1.2 s |
| 57 | `Implement a function that parses git log output` | · | `STATED_SWE_EFFECT_UNSERVED` | 1.2 s |
| 58 | `Refactor …/goal_compiler.py into smaller modules` | · | `FAIL__LIVE_CONTROLLER_EXECUTION` | 61.9 s |
| 59 | `Make the test suite pass` | · | `STATED_ANSWER_NOT_PROVIDED` | 1.0 s |

### C — verify (10)

| # | sentence | | what happened | time |
|---|---|---|---|---|
| 18 | `Run the tests in canonical/tests/test_swe_typed_plan_v1.py` | ✘ | `repository.acceptance.measure.v1`: `test_count 0`, `test_returncode 1`, `tests_pass false` → PASS | 36.8 s |
| 19 | `Tell me which tests fail` | · | `ROUTE_ADMISSION_REJECTED` | 1.0 s |
| 20 | `Lint …/swe_typed_plan_v1.py` | · | ran; `ruff UNAVAILABLE` → `PASS_SYNTAX_ONLY`; door calls a verdict a failure | 24.4 s |
| 21 | `Type-check …/swe_typed_plan_v1.py` | · | ran; `mypy UNAVAILABLE` → `PASS_BASELINE_ONLY`; same refusal | 24.6 s |
| 22 | `Measure the test coverage of …/swe_typed_plan_v1.py` | · | `CAPABILITY_REFUSED_SUITE_RED` (correct: the suite **is** red) | 3.4 s |
| 23 | `Run a mutation test on …/swe_typed_plan_v1.py` | · | `STATED_ANSWER_NOT_PROVIDED` | 1.2 s |
| 24 | `Scan canonical/runtime for SQL injection` | · | `STATED_ANSWER_NOT_PROVIDED` | 1.2 s |
| 25 | `Check for security vulnerabilities in …` | ◐ | security gate on a stated-file diff: 0 blocking, 0 advisory — but the scanner is a stub (§6) | 1.8 s |
| 26 | `Measure the performance of build_plan` | · | `ROUTE_ADMISSION_REJECTED` | 1.0 s |
| 27 | `Which tests does …/swe_typed_plan_v1.py break` | ✘ | audit of the 14 stray `test_*.py` **inside** `canonical/runtime` (6 failed, 7 errored, 1 crashed); delivered value = the integer **0** | 32.6 s |

### D — history (10)

| # | sentence | | what happened | time |
|---|---|---|---|---|
| 28 | `Show the last three git commits` | ✔ | `op=log limit=3`; 3 rows, delivered | 0.9 s |
| 29 | `Who wrote line 3 of …/swe_typed_plan_v1.py` | ◐ | `op=blame`, 200 rows, `history_depth 20913`; no answer delivered | 3.2 s |
| 30 | `Show me the diff` | ◐\* | `op=diff` — and the only changed file is **the machine's own state file** (§7) | 0.9 s |
| 31 | `Show the diff of the last commit` | · | `STATED_SWE_EFFECT_UNSERVED` | 0.2 s |
| 32 | `List the branches` | ✔ | `op=branch`, 2 rows, delivered | 1.8 s |
| 33 | `Which commit broke the tests` | ◐ | real bisect: 15 probed commits over 20,913, names `93b1892` ("Add deterministic independent acceptance gate (#633)"); **SHA not delivered** | 8.5 s |
| 34 | `Revert the last commit` | · | `STATED_SWE_EFFECT_UNSERVED` — **fixed** (V3 §3) | 0.2 s |
| 35 | `Show the status of the working tree` | ◐ | `op=status`, 3 rows — all three are the machine's own writes (§7) | 0.8 s |
| 36 | `What changed in the last 5 commits` | ◐ | `op=log limit=5`, 5 rows; no answer delivered | 0.7 s |
| 37 | `Show me the staged changes` | · | `STATED_SWE_EFFECT_UNSERVED` | 0.3 s |

### E — debug and profile (8)

| # | sentence | | what happened | time |
|---|---|---|---|---|
| 38 | `Profile the function build_plan in …` | · | `FAIL__LIVE_CONTROLLER_EXECUTION` | 0.9 s |
| 39 | `Debug the failing test test_breaking_the_derivation_breaks_the_selection` | · | `STATED_SWE_EFFECT_UNSERVED` | 0.8 s |
| 40 | `Find the fault in …/swe_typed_plan_v1.py that makes the test fail` | ✘ | `code.impact.tree_sitter.testselect.v1` — test *selection*: `selected_test_count 1`, `affected_file_count 173`. No fault localized. | 51.6 s |
| 41 | `Trace the value of limit through build_plan` | · | `ROUTE_ADMISSION_REJECTED` | 0.8 s |
| 42 | `Set a breakpoint in build_plan` | · | `ROUTE_ADMISSION_REJECTED` | 0.4 s |
| 43 | `Show me the stack trace of the last failure` | · | `FAIL__RAW_GOAL_COMPILATION_GAP` | 0.6 s |
| 44 | `Which line raises the ZeroDivisionError` | · | `FAIL__RAW_GOAL_COMPILATION_GAP` | 0.8 s |
| 45 | `Find the slow function in …/goal_compiler.py` | · | `FAIL__LIVE_CONTROLLER_EXECUTION` | 1.6 s |

### F/G/H — build, review, compose (9)

| # | sentence | | what happened | time |
|---|---|---|---|---|
| 46 | `Build the project` | · | `FAIL__RAW_GOAL_COMPILATION_GAP` | 1.5 s |
| 47 | `Run the script canonical/runtime/goal_compilation_benchmark_v1.py` | ✘ | `repository.acceptance.measure.v1` — hashed 2,309 files; **the script never ran** → PASS | 21.3 s |
| 48 | `Install the dependencies` | · | `FAIL__RAW_GOAL_COMPILATION_GAP` | 0.7 s |
| 49 | `Package the project` | · | `ROUTE_ADMISSION_REJECTED` | 0.7 s |
| 50 | `Run a static analysis pass on canonical/runtime` | ✘ | `repository.acceptance.measure.v1` — hashes + `python_parse_ok`; **no analysis of any kind** → PASS | 19.2 s |
| 51 | `Review the diff` | · | `FAIL__RAW_GOAL_COMPILATION_GAP` | 1.7 s |
| 52 | `Review …/git_repository_operate.py for bugs` | · | `CAPABILITY_REFUSED_SUITE_RED` | 5.3 s |
| 53 | `Check the type safety of the diff` | · | `FAIL__RAW_GOAL_COMPILATION_GAP` | 1.6 s |
| 60 | `Find every place that reads the registry` | · | `ROUTE_ADMISSION_REJECTED` | 0.9 s |
| 61 | `Design a cache for the capability registry` | · | `GROUNDING_ARTIFACT_REPORTED_UNGROUNDED` — **fixed** (V3 §1 row 61) | 0.8 s |

---

## §2. P0 — the six wrong passes are all one defect: **the verb is not checked against what the tool provides**

Every wrong pass names the token that admitted it. Read the admission record of the wall clock:

```
"Run the script canonical/runtime/goal_compilation_benchmark_v1.py"
  selected_capability : python.repository.acceptance.measure.v1
  matched_tokens      : ["run"]                    score 4
  admission_basis     : DECLARED_INPUT_CONTRACT_FULLY_STATED_IN_GOAL
  admitted            : true

"Run a static analysis pass on canonical/runtime"
  matched_tokens      : ["run"]                    score 4     admitted: true

"Run the tests in canonical/tests/test_swe_typed_plan_v1.py"
  matched_tokens      : ["run", "tests"]           score 8
  typed_binding_refused : true
  typed_binding_reason  : BINDING_REFUSED:source_root:0_existing_directories_named
  admitted              : true                     ← refused by the binder, admitted anyway
```

Three different requests — *execute a script*, *analyse a directory*, *run one test file* — became
one row because that row's keyword list contains the phrase **"run the tests"**, whose first word
is `run`. `run` is in *every* imperative execution request in software engineering. One generic
token in one row's keyword phrase is enough to win, because admission asks only:

* are the declared input keys derivable from the sentence? (`source_root`, `output_path` — yes,
  a path was named and a spool path is auto-assigned), and
* did the adapter write and verify an artifact?

It asks the effect question only for the fourteen classes `_STATED_EFFECTS` enumerates — and for
those it asks the wrong side. The clearest case is the rule whose entire purpose is this defect:

```python
# live_brain_route_admission_v1.py:1958  STATED_TEST_RUN_NOT_EXECUTED_BY_CAPABILITY
asked    = re.compile(r"^\s*(?:please\s+|now\s+|can you\s+)*(?:re)?run\b[^.\n]{0,40}"
                      r"\b(?:tests?|suite|pytest)\b | ... | ^\s*(?:run|rerun)\s+the\s+tests?\b")
supplied = re.compile(r"\brun\w*|\bsuite\b|\bpytest\b|\bunittest\b|\bacceptance\b"
                      r"|\bexecut\w*|\bharness\b|\bdriver\b")
```

`Run the tests in canonical/tests/test_swe_typed_plan_v1.py` matches the ASKED side exactly. The
SUPPLIED side is a regex run over the whole row, and `python.repository.acceptance.measure.v1`
contains `acceptance` in its **capability id and its `provides`**, and `run the tests` / `run tests`
/ `test suite` in its **keywords**. So the gate concludes that a row whose artifact reports
`test_count: 0, test_returncode: 1` *executes tests*, and admits it. The row's real `provides` is
`python.test.measurement.objective` — **the declaration already draws the line; the regex ignores
it.**

`declared_effect_ids` in this repository states the law ("what it produces outranks what it is
tagged with") and the router has not adopted it.

The same one-liner explains rows 0, 27 and 40: `find every caller` → `symbols.index.ast`
(a counter), `which tests does X break` → `tests.audit.unittest` (a corpus audit), `find the fault`
→ `code.impact.tree_sitter.testselect` (a test selector). Four rows, four nouns in common
(`caller`, `test`, `fault`), zero verbs in common. **Selection is a noun matcher; the request is a
verb.**

---

## §3. P0 — the door certifies a *measurement* as *the work*, over an artifact that says it failed

Rows 18, 47 and 50 are one row, and that row is unusually honest about itself. Its artifact, read
back from disk:

```json
{"schema": "PROJECT_BRAIN_PYTHON_REPOSITORY_ACCEPTANCE_MEASUREMENT_V1",
 "status": "PASS__CONTENT_ADDRESSED_REPOSITORY_MEASUREMENT",
 "measurements": {"python_file_count": 2232, "python_parse_ok": true,
                  "repository_source_unchanged": true,
                  "test_count": 0, "test_returncode": 1, "tests_pass": false},
 "test_evidence": {"returncode": 1, "test_count": 0, "timed_out": false},
 "terminal_authority": false,
 "hard_nonclaims": ["MEASUREMENT_SUCCESS_IS_NOT_TASK_ACCEPTANCE",
                    "TEST_PASS_IS_NOT_COMPLETE_REQUEST_SEMANTICS",
                    "MEASURES_ONLY_THE_DECLARED_SOURCE_ROOT_AND_TEST_COMMAND",
                    "NO_BENCHMARK_SCORE_OR_TERMINAL_AUTHORITY"]}
```

`tests_pass: false`. `test_returncode: 1`. `test_count: 0`. The artifact's own first non-claim is
literally **`MEASUREMENT_SUCCESS_IS_NOT_TASK_ACCEPTANCE`**. And the door's verdict for that exact
run:

```
status                    PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
raw_goal_acceptance.status RAW_GOAL_ACCEPTANCE_VERIFIED
semantic_acceptance_complete  true
terminal_authority            false
accepted_obligation_ids       [RAWREQ:ca0563…, RAWREQ:7f5e78…]
reinspection_ledger           {subject_files_rehashed: 2239, suite_re_run_returncode: 1,
                               tests_recounted: 0}
```

Note `EXACT_SEMANTIC_ACCEPTANCE_VERIFIED` next to `suite_re_run_returncode: 1`. The verification
loop **re-ran the suite, saw it red, counted zero tests, and kept the word EXACT** — because the
obligations it accepted (`RAWREQ:…`) were derived from the capability's declared inputs and
outputs, not from the sentence's stated effect. The artifact being written *is* the obligation.

This is strictly worse than V3 §11.4, which measured `pass: true` alongside
`semantic_acceptance_complete: false`. Today the field reads `true` over an artifact that reports
its own failure.

**The fix is data that is already in the artifact**, and it is four lines:

1. if the artifact carries `terminal_authority: false` and a `hard_nonclaims` entry that names the
   request class (`MEASUREMENT_SUCCESS_IS_NOT_TASK_ACCEPTANCE`,
   `TEST_PASS_IS_NOT_COMPLETE_REQUEST_SEMANTICS`), the row may not satisfy that class;
2. if the sentence names a test file or a script, the artifact must name that same path in its
   `subject`/`command`, or the request is unanswered;
3. `tests_pass: false` may never be rendered as `pass: true` for a request whose verb is `run`;
4. `semantic_acceptance_complete` may not be `true` while `terminal_authority` is `false`.

The row is not the villain. It says, in its own bytes, that it is only a measurement. **The
admission and acceptance layers decline to read it.**

---

## §4. P0 — "every caller" is answered from inside the calling file, and `truncated: false` certifies the scope

Row 0's artifact is a `PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1` whose `source_root` is
**`canonical/runtime/swe_typed_plan_v1.py`** — the file the sentence asked *about*, not the codebase
that could *contain* callers. So `callers_of["build_plan"] = ["plan_report"]` is not a partial
answer, it is the right answer to the wrong question: *who calls `build_plan` inside
`build_plan`'s own file*.

The truth, measured with `grep -rn "build_plan("`:

```
canonical/runtime/astra_runtime.py:90
canonical/runtime/bound_capabilities/python_crossfile_edit_choreograph.py:451
canonical/runtime/live_brain_route_admission_v1.py:4011, 4984, 5037, 5076
canonical/runtime/root3_declared_artifact_finalizer_v1.py:157
canonical/runtime/swe_typed_plan_v1.py:683
```

**7 call sites in 5 modules. The answer returned 1, and said `truncated: false`.**

Two independent rules are missing and both are one line:

* a *reference* verb (`every caller / who calls / which modules import / every place that reads`)
  requires `source_root` ⊇ the package that can contain a call site — never the defining file;
* `truncated` must be a **computed** claim (scope size vs. what was searched), not a literal.

This is the row where my own fix made things worse: V3 measured a count of an unrelated index and
called it a wrong pass; today the same wrong scope is *delivered* as a confident one-item list with
an exactness certificate. §12 retracts my claim that this class was closed.

---

## §5. P0 — the projection delivers scalars for enumerating nouns, and nothing at all for two thirds of the passes

Two failures, measured on the 16 passes:

**(a) A scalar is delivered where a collection was asked for.** Row 27 asks *which tests does this
file break*. The audit artifact holds 14 file records, 6 red. The delivered answer is:

```json
{"noun": "test", "field": "records.0.tests", "count": 1, "value": 0, "truncated": false}
```

`records[0]` is `canonical/runtime/test_cognitive_tool_router.py`, which ran **0 tests**. The
projection walked into the first record, found a key named `tests`, and returned the integer. A
request for *which* tests was answered with *how many tests the first file in the list did not
run*, and certified.

**(b) Nothing is delivered for 10 of the 16 passes.** `answer: null` for rows 17, 18, 25, 29, 30,
35, 36, 40, 47, 50 — even where the artifact holds the right rows (`status` 3 rows, `blame` 200
rows, `diff` 1 row + patch, `log` 1 row). The projection only lifts nouns it has in its table
(`function`, `import`, `caller`, `commit`, `branch`, `test`), so `status`, `diff`, `blame`, `log`
and every diagnostic artifact fall through to `null`.

Net: **4 of 61 requests return a useful payload.** The machine computed an answer 11 times and
handed over 4.

The fix is in the same file as the working half: `_narrow` must prefer a collection-valued node of
the right noun over any scalar descendant, and the noun table needs the five read families it is
missing. Both are table entries plus one comparison, not a new subsystem.

---

## §6. P0 — the verification gates grade themselves on tools that are not installed, and say `complete: true`

`Lint`, `Type-check` and `Check for security` all ran today (V3 §6 said they could not — see §12).
They ran on a synthetic `--- /dev/null` diff of the named file (`stated_9dd1c402f76cb605.diff`,
36,132 bytes, `@@ -0,0 +1,693 @@`) — a clever reuse of the diff-scoped gates. What the artifacts
say:

```
PROJECT_BRAIN_DIFF_STATIC_TRIAGE_V1   ruff: "UNAVAILABLE"    gate: "PASS_SYNTAX_ONLY"     complete: true
PROJECT_BRAIN_DIFF_TYPE_GATE_V1       mypy: "UNAVAILABLE"    gate: "PASS_BASELINE_ONLY"   complete: true
PROJECT_BRAIN_DIFF_SECURITY_GATE_V1   bandit: "brain-ast-security-v1 (python 3.11)"
                                          blocking 0, advisory 0, gate: "PASS", complete: true
```

* `ruff` and `mypy` are **not installed**, and nothing in this repository installs them: there is
  no `pyproject.toml`, no `setup.py`, no requirements file, and not one of the workflows contains
  the strings `ruff` or `mypy` (they install `pytest`, `numpy`, `opencv-python-headless`,
  `pydantic`, `nltk`, `msgpack` and the document libraries). So **lint and type-check are
  structurally decorative on every run** — and they still emit a gate verdict and `complete: true`.
* `complete: true` next to `UNAVAILABLE` is a false statement, in the one field a consumer reads
  to decide whether a gate is meaningful.
* Security's `PASS` is produced by a hand-rolled AST scanner (`brain-ast-security-v1`), not by
  `bandit`. That may be a legitimate dependency-free choice; presenting it as a security gate with
  `complete: true` and 0 findings, for a 693-line file, is not something a caller can calibrate.
* The door then refuses rows 20/21 with `REVIEW_RAN_AND_RETURNED_A_VERDICT` — it treats *a verdict*
  as a failure of the request. A lint pass that finds 12 things is an **answer**, and the door
  throws it away — while a security pass that finds nothing is certified.

One predicate repairs the family: **`complete` must mean "every declared checker executed"; any
`UNAVAILABLE` checker makes the gate `INCOMPLETE`, and an incomplete gate may report findings but
may never report `gate: PASS`.** And a returned verdict is an answer, not a refusal.

---

## §7. P0 — the machine's own writes are inside every answer it gives about the repository

Two of the three git-read passes returned artifacts about the machine, not about the user's work:

```
Show me the diff
  op=diff, file_count 1 -> canonical/astra_runtime/state/ASSOCIATIVE_MEMORY_V1.json
                           (the agent's own associative memory, rewritten by the agent)

Show the status of the working tree
  op=status, 3 rows     -> M canonical/astra_runtime/state/ASSOCIATIVE_MEMORY_V1.json
                           ?? canonical/astra_runtime/state/B__live-raw-goal-controller__CONTROLLER_CHECKPOINT.json
                           ?? (one more state file)
```

The whole 61-sentence corpus left exactly those writes behind — no source file was touched (V3's
`typed_swe_report.json` in the source tree did **not** reproduce; the spool now goes to
`canonical/astra_runtime/tmp/`, which is git-ignored). But `solve()` still writes *inside the
repository it is asked about*, so **the agent's own bookkeeping is the top answer to "what
changed?"**. A user who asks for the diff after a solve gets a diff of the agent's memory.

This is V3 §4, confirmed and sharpened: the write is no longer destructive to source, it is now
*epistemically* destructive — it makes every repository read wrong. A scratch root for
`ASSOCIATIVE_MEMORY_V1.json` and the `*__CONTROLLER_CHECKPOINT.json` files, and `git` reads
restricted to paths the caller asked about, closes it.

---

## §8. P0 — 0 of 14 change-code sentences, grouped by cause

| cause | # | evidence |
|---|---|---|
| refused *after* doing the work | 10 (25 s), 12 (54 s), 58 (62 s) | `CAPABILITY_REFUSED_SYNTAX_ERROR_IN_FILE`, `HELPER_AMBIGUOUS`, `LIVE_CONTROLLER_EXECUTION` |
| the compiler never produced a plan | 14, 43, 44, 46, 48, 51, 53, 54 | `FAIL__RAW_GOAL_COMPILATION_GAP` |
| the stated effect has no row that provides it | 11, 56, 57 | `STATED_SWE_EFFECT_UNSERVED` |
| the controller failed on a stated file | 13, 15, 38, 45 | `LIVE_CONTROLLER_EXECUTION` |
| scope explosion | 55 | 1 file → 2,287 modules → **14,243** tests (§10) |
| answered "nothing to do" | 17 | `BASELINE_ALREADY_PASSES` (correct) |
| the answer is a count, not a change | 59 | `STATED_ANSWER_NOT_PROVIDED` |

Eight of fourteen never reached an adapter: the compiler had no plan for `write a test`, `build`,
`install`, `package`, `review the diff`, `check type safety`, `move function`, `stack trace`,
`which line raises`. That is the single largest block of dead sentences in the corpus, and it is
upstream of every capability.

---

## §9. P1 — there is still no wall clock, and the fast paths are fast by accident

```
subprocess.run(...) sites in canonical/runtime + bound_capabilities : 228
   of which carry a timeout=                                      :  32
   of which carry no timeout=                                      : 196
RLIMIT_* mentions in the whole runtime                             :   5
```

Twelve of 61 sentences took ≥ 20 s; **seven of those twelve then failed**. 25 s to refuse a rename,
54 s and 62 s to refuse an inline/refactor, 24 s each to refuse a lint and a type-check, 70 s to
time out on generated tests. The four correct answers took 0.8–1.8 s; every 20 s+ answer in the
corpus is either a refusal or a wrong pass.

The door has no `deadline` parameter and does not pass one to adapters, so the only bound in the
system is whatever individual adapters happen to declare.

---

## §10. P1 — cold start is 31.9 s and 312 MB, and the timeout is caused by *scope*, not by analysis

Measured directly, on this tree:

```
python_source_symbol_index.run(source_root=".")   : 31.91 s
artifact size                                     : 312,619,060 bytes  (298 MB)
json.loads of that artifact                       : 2.35 s
canonical/runtime: 2,289 .py files, 2,287 parse, 14,243 module-scope functions
```

Row 55 (`Generate tests for canonical/runtime/swe_typed_plan_v1.py`, one file, 16 functions) timed
out at 70 s because the derivation bound `source_root = canonical/runtime` (**the parent
directory**, a 2,287-module / 14,243-function scope), and
`python_tests_generate_scaffold._load_index` then builds the 298 MB index in-process
(`indexer.run({"source_root": "."}, source_abs)`) and expands **every module-scope function in the
tree** before running them under pytest.

So the most valuable verb in the corpus (`generate tests`) is lost to two lines: a `source_root`
that widened a file to its directory, and a target list derived from the index instead of from the
stated file. The scaffold already accepts `targets_path`; nothing passes it.

---

## §11. P1 — a shallow boundary thins history silently, and nothing in the answer says so

My first pass measured `2e9b642`, and **`2e9b642` is the shallow boundary of this clone**
(`.git/shallow` contains exactly that commit). On it, `git rev-list --count HEAD` is **1**, while
the very same object store holds **20,913** commits reachable from `main`. Three history answers
adapted silently instead of saying so:

```
Show the last three git commits     -> 1 row    PASS, no truncation flag
What changed in the last 5 commits  -> 1 row    PASS, no truncation flag
Who wrote line 3 of <file>          -> blame, history_depth 1, PASS
```

On a full checkout (`9e6a366`) all three are correct — 3 rows, 5 rows, `history_depth: 20913`.
So the *reads* are fine and this is **not** a wrong-answer defect; it is a **certificate** defect.
An answer holding fewer rows than the sentence asked for cannot distinguish "there are only
three" from "I can see only three", and `git.repository.operate.v1` already re-derives every
effect with a second plumbing command, so it knows the difference.

This matters because **GitHub Actions' default checkout is `fetch-depth: 1`**: the CI-visible
version of this machine is permanently in the first state, and every history answer it certifies
there is thinner than the question. `git rev-parse --is-shallow-repository` is one call,
`history_depth` is already in the blame artifact, and the fix is one flag —
`TRUNCATED_BY_SHALLOW_CLONE` — set whenever the repository is shallow and `commit_count < stated
limit`.

Two modules in `canonical/runtime` do not parse at all, and no guard reports them:

```
livebench_legacy_predecessor_compiler_audit_v1.py:139  unexpected character after line continuation
osworld_v21_app_policy_overlay_v1.py:152               closing parenthesis ']' does not match '('
```

Every index skips them (`unparseable: 2`), so even a correctly scoped `find every caller` has two
holes in this tree and no artifact says where.

## §12. What works, and what I must retract

**Works, measured this run:** seven of ten history sentences pass — `log`, `status`, `branch`,
`blame`, `diff` and a **real** bisect that probed 15 commits across a 20,913-commit history in
8.5 s and named the offending commit; all are fast (0.5–3.2 s);
`List the functions` and `Show the imports` deliver exact lists;
`Repair …` correctly reports that the suite is already green; the coverage gate correctly refuses
on a red suite; 44 of 61 refusals name exactly what was missing; the whole 61-sentence corpus now
leaves **no source file touched**; and the two classes I landed a fix for stayed fixed
(`Revert the last commit` → refusal, `Design a cache` → refusal).

**Explicit retractions of V3 (and of my own SWE_FIXES report):**

| claim | status |
|---|---|
| V3 §1-A: "show/list/imports are answered with counts" | **half false today.** `List the functions` and `Show the imports` deliver the real list; `Show the definition` refuses. `Find every caller` still wrong, now *delivered* — my fix made that one more convincing, not less. |
| V3 §3: "a revert is answered by a log" | **fixed**, by main's stated-effect gate plus the verb binding I landed. Re-verified. |
| V3 §5: "three sentences hang 180 s" | **false today.** Repair returns in 30.7 s, "make the suite pass" refuses in 1.0 s. One timeout remains (row 55) and its cause is different and named in §10. |
| V3 §6: "lint/type/security die on `diff_path`" | **false today.** They run, on a synthetic stated-file diff. They fail for a different reason: the checkers are absent and the door treats a verdict as a failure (§6). |
| V3 §1 row 61: `Design a cache` PASSes over an ungrounded artifact | **fixed** — `GROUNDING_ARTIFACT_REPORTED_UNGROUNDED`. |
| V3 §1: "5 of 62 correct, 7 of 12 passes wrong" | **superseded.** Today: 4 correct delivered, 6 of 17 passes wrong, 6 correct-but-undelivered, 1 contaminated. V3's column counted a correct *artifact* as correct; a user never sees it. |
| V3 §11.4: `pass: true` with `semantic_acceptance_complete: false` | **superseded and worse.** Today `semantic_acceptance_complete: true` over artifacts that report their own failure (§3). |
| SWE_FIXES: "the answer-shape gate closes the count-for-list class" | **partly false.** Two of five rows fixed, one now refuses, two still deliver wrong values (rows 0 and 27). §5 is the remaining hole. |
| my own first V4 pass: "three history answers are silently thin; this clone is one commit deep" | **reframed, not wrong.** The tree was shallow at that commit, not the machine. On a full checkout all three are correct; what survives is the missing `TRUNCATED_BY_SHALLOW_CLONE` certificate (§11). |

---

## §13. The fix order (damage per unit of work), each with the mechanism that already exists

1. **Make the supplied side of `_STATED_EFFECTS` read `provides` (§2, §3).** One edit to the
   table at `live_brain_route_admission_v1.py:1923`: replace each regex-over-`str(entry)` with a
   match against the row's `provides` + the artifact's own evidence. For the test-run rule that
   means `provides` must name test *execution*, which `python.test.measurement.objective` does
   not. Kills 3 of the 6 wrong passes with no new data. Then, in the same pass, read the
   artifact's own non-claims (`terminal_authority`, `tests_pass`, `hard_nonclaims`) before the
   door may emit `EXACT_SEMANTIC_ACCEPTANCE`, and require a named test file or script to appear in
   the artifact's `subject`.
2. **Admit on `provides`, not on `matched_tokens` (§2).** The row's `provides` / `target_effects`
   is the declared effect vocabulary; `declared_effect_ids` already states the law. Kills the
   `run`-token gravity that produced all three of §3's sentences, and the noun-routing behind
   rows 0, 27 and 40.
3. **Scope for reference verbs (§4).** `find every caller / who calls / which modules import`
   requires a `source_root` that contains call sites, and `truncated` must be computed from
   (scope searched vs. scope possible).
4. **Project the collection, not a scalar (§5).** Prefer collection-valued nodes; add the five
   missing read families (`status`, `diff`, `blame`, `log`, diagnostics). Turns 10 answer-less
   passes into delivered answers with no new capability.
5. **`complete` means every checker ran (§6).** `UNAVAILABLE` ⇒ `INCOMPLETE`, and an incomplete
   gate may never report `PASS`. Then install `ruff`/`mypy` in the environment (they are absent
   from the repo's own dependency story) or stop presenting those gates as available.
6. **A scratch root for the agent's own state (§7).** `ASSOCIATIVE_MEMORY_V1.json` and
   `*__CONTROLLER_CHECKPOINT.json` move out of the analysed tree; git reads filter to the paths
   the caller named.
7. **Targets from the stated file (§10).** `python_tests_generate_scaffold` gets `targets_path`
   derived from the single named file (16 functions), and the index is built over the scope it
   needs. Turns a 70 s timeout into a sub-second answer.
8. **A deadline in `run_adapter_locally` (§9).** One parameter, checked between files in
   `python_test_audit` and before each `subprocess.run`; 196 call sites become bounded.
9. **A persisted, checksummed index per root (§10).** 31.9 s and 298 MB become a 2.35 s load.
10. **Say `TRUNCATED_BY_SHALLOW_CLONE` (§11).** One `git rev-parse --is-shallow-repository`, plus
    a guard that reports the two unparseable modules.

**The ordering logic is the same as V3's and it has not changed:** items 1–2 stop the machine from
certifying work it did not do; items 3–5 make the answers it *does* compute reach the caller;
items 6–10 are speed and hygiene. Until 1 and 2 land, no number this project reports about itself
— including the numbers in this document — can be trusted as a measure of capability rather than
a measure of its own bookkeeping.


---

## Appendix — the raw run (61 sentences, `main @ 9e6a366`, 118 s wall, 6 workers)

`n | pass | elapsed | adapter the door actually invoked | verdict`

```
  0 | True  |   2.2s | python_source_symbol_index                 | PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERI
  1 | False |   0.2s | —                                          | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED
  2 | False |   0.8s | —                                          | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED
  3 | True  |   1.2s | python_source_audit_ast                    | PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERI
  4 | True  |   1.2s | python_source_audit_ast                    | PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERI
  5 | False |   0.7s | —                                          | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
  6 | False |   1.2s | —                                          | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
  7 | False |   0.5s | —                                          | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED
  8 | False |   0.6s | —                                          | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
  9 | False |   0.7s | —                                          | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
 10 | False |  22.6s | —                                          | FAIL_CLOSED__CAPABILITY_REFUSED_SYNTAX_ERROR_IN_FILE
 11 | False |   1.0s | —                                          | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED
 12 | False |  52.6s | —                                          | FAIL__LIVE_CONTROLLER_EXECUTION
 13 | False |   1.2s | —                                          | FAIL__LIVE_CONTROLLER_EXECUTION
 14 | False |   1.5s | —                                          | FAIL__RAW_GOAL_COMPILATION_GAP
 15 | False |   0.6s | —                                          | FAIL__LIVE_CONTROLLER_EXECUTION
 17 | True  |  29.4s | python_software_repair_apply_verified_v1   | PASS__REQUESTED_STATE_ALREADY_HOLDS
 18 | True  |  33.7s | python_repository_acceptance_measurement_v | PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERI
 19 | False |   1.1s | —                                          | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
 20 | False |  24.3s | —                                          | FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT
 21 | False |  25.0s | —                                          | FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT
 22 | False |   3.0s | —                                          | FAIL_CLOSED__CAPABILITY_REFUSED_SUITE_RED
 23 | False |   1.4s | —                                          | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED
 24 | False |   1.3s | —                                          | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED
 25 | True  |   1.9s | python_review_diff_security_gate           | PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_V
 26 | False |   1.2s | —                                          | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
 27 | True  |  35.5s | python_tests_audit_unittest                | PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_V
 28 | True  |   0.9s | git_repository_operate                     | PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_V
 29 | True  |   3.2s | git_repository_operate                     | PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_V
 30 | True  |   0.9s | git_repository_operate                     | PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_V
 31 | False |   0.2s | —                                          | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED
 32 | True  |   1.9s | git_repository_operate                     | PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_V
 33 | True  |   8.5s | git_bisect_regression                      | PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERI
 34 | False |   0.3s | —                                          | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED
 35 | True  |   0.8s | git_repository_operate                     | PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_V
 36 | True  |   0.7s | git_repository_operate                     | PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_V
 37 | False |   0.2s | —                                          | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED
 38 | False |   1.1s | —                                          | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED
 39 | False |   1.0s | —                                          | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED
 40 | True  |  53.0s | code_tree_sitter_impact_v1                 | PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_V
 41 | False |   0.8s | —                                          | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
 42 | False |   0.6s | —                                          | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
 43 | False |   0.5s | —                                          | FAIL__RAW_GOAL_COMPILATION_GAP
 44 | False |   0.7s | —                                          | FAIL__RAW_GOAL_COMPILATION_GAP
 45 | False |   2.4s | —                                          | FAIL__LIVE_CONTROLLER_EXECUTION
 46 | False |   2.0s | —                                          | FAIL__RAW_GOAL_COMPILATION_GAP
 47 | True  |  23.4s | python_repository_acceptance_measurement_v | PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERI
 48 | False |   1.2s | —                                          | FAIL__RAW_GOAL_COMPILATION_GAP
 49 | False |   0.8s | —                                          | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
 50 | True  |  20.2s | python_repository_acceptance_measurement_v | PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERI
 51 | False |   1.6s | —                                          | FAIL__RAW_GOAL_COMPILATION_GAP
 52 | False |   5.1s | —                                          | FAIL_CLOSED__CAPABILITY_REFUSED_SUITE_RED
 53 | False |   1.4s | —                                          | FAIL__RAW_GOAL_COMPILATION_GAP
 54 | False |   1.1s | —                                          | FAIL__RAW_GOAL_COMPILATION_GAP
 55 | False |  70.2s | —                                          | TIMEOUT_70S
 56 | False |   1.2s | —                                          | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED
 57 | False |   1.1s | —                                          | FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED
 58 | False |  60.2s | —                                          | FAIL__LIVE_CONTROLLER_EXECUTION
 59 | False |   1.1s | —                                          | FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED
 60 | False |   0.6s | —                                          | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
 61 | False |   0.8s | —                                          | FAIL_CLOSED__GROUNDING_ARTIFACT_REPORTED_UNGROUNDED
```

The adapter column is what `run_adapter_locally` was handed (recorded by wrapping it); `—` means the
request was refused before any adapter ran. Elapsed is wall clock inside `solve()`, so it includes
compilation, admission and verification, not the adapter alone.

Reproduce any single row on a clean checkout of this commit:

```bash
python3 -c 'import sys, json; sys.path.insert(0, ".")
from canonical.runtime.live_brain_route_admission_v1 import solve
print(json.dumps(solve({"task_id": "A", "goal": "<the sentence>"}), default=str)[:2000])'
```

The six wrong passes are reproduced by rows 0, 18, 27, 40, 47 and 50; the three §3 sentences are
18, 47 and 50.
