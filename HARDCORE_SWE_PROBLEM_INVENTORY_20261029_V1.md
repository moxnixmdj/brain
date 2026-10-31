# Every problem between this machine and being the most advanced software engineer

Measured 2026-10-29 on `arena/47739ce8-brain`, branched from `main` `e2d7981`.
Authority: **NONE**. This is a measurement, not an independent verification. Credit: **0**.
Producer cognition model dependency: **0**. Incremental spend: **$0**.
Scope: hardcore software engineering only. PDF/DOCX/XLSX/chart/archive capabilities are
excluded except where they are the *wrong-domain destination* of an SWE request.

Nothing below is inferred from reading code alone. Every claim carries the probe that
produced it, run against a fresh tree, judged by the filesystem / the real test runner /
the real adapter as the independent oracle.

---

## 0. The one-paragraph answer

The machine owns several genuinely advanced software capabilities — a cross-file symbol
rename proved on disk, byte-exact extract-function, five measured Python repair families,
a real AST symbol index. Almost none of them is reachable from a sentence a human would
type. On **22 fresh human SWE sentences it answers 4, and 2 of those 4 are false** (the
requested change did not happen). On **10 realistic "build/change this software" requests
it answers 0, and one hangs forever**. Meanwhile **20 of its 64 SWE registry rows are
stubs that certify themselves by reading the registry**, 27 composition edges are carried
only by those stubs, 294 of the 419 advertised "capabilities" are historical receipts that
cannot run today, the cost model is the constant `1`, and the toolchain its "advanced review
gates" shell out to (mypy, ruff, coverage, bandit, z3, crosshair, pytest) is installed by
no workflow and absent from the machine. So the frontier is not "more capabilities". It is:
**make PASS mean the effect happened, make the owned capabilities reachable, and delete the
rows that only claim.**

**Updated later the same day (§1.5).** The `fix`/`repair` half of item 1 below, the
stated-bug-report sibling, and the routing rule of §2.1c are now fixed and measured. On a
12-sentence fresh probe the machine answers 4 and **none of the 4 is false** — it was 4 with
two false. A verbless bug report now really repairs the file and greens the test, 3/3 cold
processes, using a table that already existed and one new entry in it.

---

## 1. What is genuinely good (build on this, do not rebuild it)

| capability | evidence |
|---|---|
| `python.refactor.rename_symbol.v1` | renamed `old_name`→`new_name` in `models.py` **and** the import and call site in `service.py`; byte-exact spans, `output_verified: true` |
| `python.refactor.extract_function.v1` | 15 tests, byte-deterministic region move (2 errors on its own tests — §4.2) |
| five Python repair families | 150/150 across seeds 7, 11, 99, 1234, 424242 (prior session, unchanged) |
| `python.source.symbols.index.ast` | real AST index: `symbol_count 3, reference_count 4, call_edge_count 2` on a fresh file |
| fail-closed discipline | out-of-scope refusal is 1.0; 23/23 stub capabilities cannot be driven to a PASS from a sentence — the *execution* gates are honest even where the registry is not |
| 37-family end-to-end suite | 0.8241 in scope / 1.00 out-of-scope — but measured on **machine-authored** sentences (§3.2) |

The honest summary: the mechanisms that exist are real. The wiring, the acceptance layer,
and the self-description are what is broken.

---

## 1.5 Status of this document's own P0s (measured later the same day)

Five commits on `arena/47739ce8-brain` (`3671140`, `2b70c6d`, `4340001`, `7593910`, `1f5f86d`, base `main` `e2d7981`) fix
§2.1 and one instance of §2.11's sibling class, and are the reason the numbers below carry
a date. Nothing else in this document has changed status.

| item | before | after |
|---|---|---|
| §2.1 `fix_broken` | PASS, source byte-identical, stated test **red** | PASS, source `return a - b` → `return a + b`, stated test **green**, 3/3 cold processes |
| §2.1b `bug_report` (new, below) | PASS, source byte-identical, named test **red**, 3/3 cold | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED:DAG_STEP_WEAK_EVIDENCE` — honest, and a routing gap, not a lie |
| §2.1c `bug_report` routing (`1f5f86d`) | planned a DOCX writer, then refused | **PASS from `python.software.repair.apply.verified.v1`, source repaired, named test green, 3/3 cold** |
| 12-sentence oracle probe | 4 PASS, **2 of them false** | 4 PASS, **0 false** |
| drift guard on `main..HEAD` | `DRIFT_GUARD_FAIL`, 6 codes | `DRIFT_GUARD_PASS` |
| new regression suite | — | 12/12; 4/12 with both sources reverted; 1 reader test red with the new rule disabled |
| model verifier | 33/33 | 33/33 after recompile, `MODEL 1842bdf1…` |

Two edits, both reuse, no new subsystem, `model_dependency_count: 0`, `incremental_spend_usd: 0`:
`live_brain_route_admission_v1._promised_source_files` reads the target before the verb
(`_nearest_source_before`, excluding witnesses via the repository's own
`python_test_corpus_discovery_v1.is_test_file_name`) and reads a stated defect
(`_DEFECT_STATEMENT_RE`) as the promise it is; `declared_input_derivation_v1` builds
`test_argv` from `python_test_guided_patch_search_v1.suite_argv` instead of running the test
file as a script (`[python, -B, file]` exits 0 having run nothing when the file has no
`__main__` guard — 695 of the 2019 unittest files here have none).

---

## 2. P0 — the truth layer lies, so every number above it is unfounded

### 2.1 A repair reports PASS while its own stated test is still red — **FIXED in `3671140`**

```
request : "the add function in <T>/pkg/calc.py is broken, fix it so its tests pass"
source  : def add(a, b): return a - b            (the bug)
verdict : PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED
adapter : python.software.repair.apply.verified.v1
payload : applied=false, files_written=[], status=PASS__STATED_TEST_ALREADY_PASSES_NOTHING_TO_REPAIR
oracle  : $ python3 -m unittest test_calc   ->   FAILED (failures=1)   (-1 != 5)
```

The source was not touched and the test the sentence names still fails. Root cause is one
branch: `python_repair_apply_verified_v1.py:181-193` treats `pre_apply_test_returncode == 0`
as "the stated test already passes". The argv can collect **zero tests** and still return 0.
The sibling "discovered corpus" branch at the same file, lines 144-170, already carries the
exact guard for the exact lie and documents it. The *stated* branch does not.

**Measured again after the fix** (`3671140`, cold processes, the filesystem and the real
runner as oracles): the same sentence now repairs the file and greens the test, and the
promise it makes is read from the sentence wherever the target sits — before the verb as
well as after it. The two mechanisms that were silently missing:

* `_promised_source_files` only looked for a `.py` **after** the repair verb, so ordinary
  English ("the add function in X is broken, fix it") promised nothing and the
  source-change gate had nothing to check;
* the derived test command was `[python, -B, <test>]`, which exits 0 having run **zero**
  tests when the file has no `__main__` guard. That 0 *is* the lie GATE 1 reads as "already
  passes". `python_test_guided_patch_search_v1.suite_argv` already documented the trap.

### 2.1b A bug report has no verb, so it promised nothing — and a no-op was a PASS — **FIXED in `4340001`**

```
request : "Bug: <T>/pkg/calc.py add() returns the wrong value. Failing test: <T>/pkg/test_calc.py."
before  : PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED
          capability python.software.repair.loop.test_guided.ast.v1, source byte-identical,
          named test RED, 3/3 cold processes
after   : FAIL_CLOSED__ROUTE_ADMISSION_REJECTED:DAG_STEP_WEAK_EVIDENCE, 3/3 cold processes
```

There is no `fix`/`repair` verb in a bug report, so the promise reader returned `[]`, no
digest was taken, and the source-change gate had nothing to check. The promise is in the
statement: a named source *reported broken* with a named failing witness is a source
promised to change. `_DEFECT_STATEMENT_RE` reads that. The residual problem is the next one.

### 2.1c The route planner answers "fix this Python bug" with a **DOCX writer** — **FIXED in `1f5f86d`**

With the source now read as a promise, the same sentence reaches the DAG planner, which
produces:

```
route_admission.compiler_mode : FRONT_CAPABILITY_DAG_PLANNED
dag_steps[0] : docx.document.create_from_json_record
               matched_tokens ["value"]   score 4   clause "…add() returns the wrong value"
```

It is refused (`DAG_STEP_WEAK_EVIDENCE`), which is the only reason this is not a §2.3-class
false credit. A single token (`value`) is enough to nominate a document writer for a Python
repair; the repair capability that can actually do it is never a candidate. This is the
general shape behind §3.1: the front door's planning is token overlap, not intent.

**Fixed the same day, in `1f5f86d`, by adding a third entry to a table that already
existed.** `swe_typed_plan_v1._FAMILIES` is the repository's own §9 lever — enumerate
candidates from the registry's *declared keywords*, let `selection.admit` be the oracle,
take the single admitted capability whose name carries the effect token. One tuple for
stated defects, and the selector's own effect vocabulary
(`capability_selection_retrieval_v1._EFFECT_WORDS`) already listed `bug`/`broken`/`failing`
as repair words:

```
"Bug: <S> add() returns the wrong value. Failing test: <T>."
  before : PASS from python.software.repair.loop.test_guided.ast.v1
           source byte-identical, named test RED          (3/3 cold)
  after  : PASS from python.software.repair.apply.verified.v1
           source 'return a - b' -> 'return a + b', named test exit 0   (3/3 cold)
```

The enumeration is the evidence that nothing is hardcoded: four rows declare a surface
about landing a fix (`python.pr.land.composer`, `python.repo.diff_apply_full_testgate`,
`python.software.issue_to_pr.orchestrate`, `python.software.repair.apply.verified`);
exactly one admits every input the sentence states. An analysis-only guard keeps
"Explain the bug in X" out of the family route, because a question is not a request to
change the file. Measured: 373 SWE/front-door test files are 56 red with the change and
56 red without — zero newly red; the new suite is 4/4 and 2 of its 4 fail with the family
removed; 12-sentence oracle probe is 4 PASS with **0 false** (it was 4 with 2 false).

### 2.2 A search capability's "patch found" is accepted as "the repair was applied"

```
request : "Repair the python source <T>/pkg/calc.py so that the unit test ... passes"
verdict : PASS      capability: python.patch.search.test_guided.ast.v1
adapter : PASS__VERIFIED_MULTI_EDIT_PATCH_FOUND     source changed: no     test: still red
```

`python.patch.search.test_guided.ast.v1` is a *search*; its registry `expect` is
`output_verified == true`, i.e. "a patch was found". The door accepts the capability's own
definition of done as proof of the sentence's goal. The seam is the same in §2.3.

### 2.3 A report capability's "report written" is accepted as "a test was written"

```
request : "Write a unit test for <T>/pkg/calc.py and save it to <T>/pkg/test_new.py"
verdict : PASS      capability: python.tests.audit.unittest
artifact: <T>/pkg/test_new.py  ==  a JSON audit report: {"tests":1,"failed":1,"pass_rate":0.0}
```

The "test file" contains the machine's own red audit of an unrelated test. The request was
not satisfied in any sense.

### 2.4 The effect gate is a substring test, and only runs on the retry path

`canonical/runtime/swe_typed_plan_v1.py:119` `_effect_consistent` returns true when any
effect word appears anywhere in the capability id. Measured:

```
"Write a unit test for <file> and save it to <out>"
      python.tests.audit.unittest          -> consistent == True  (the AUDIT is admitted for a WRITE request)
      python.tests.generate.scaffold.v1    -> consistent == True
"Rename the parameter old_price to price in <file> and save the report to <out>"
      python.refactor.rename_parameter.v1  -> consistent == True
      document.convert.markdown_pdf.pandoc -> consistent == False
```
The gate works on the word it was written for and admits an audit for a write because
"test" is a substring of both ids.

and the gate is never consulted on the PRIMARY route: a rename request without a report
path reached `document.convert.markdown_pdf.pandoc_weasyprint` by the primary
`DETERMINISTIC_VERIFIED_CAPABILITY_MATCH`, failed `FAIL__LIVE_CONTROLLER_EXECUTION`, and the
correct typed plan that *did* exist (`python.refactor.rename_parameter.v1`) was suppressed
because the wrong capability had already "executed" (`live_brain_route_admission_v1.py:1953`).

**Measured cost of that suppression rule: 3 more sentences.** Forcing the honest retry those
3 are denied produced 2 real fixes (rename verified on disk; `fix <path>` repaired) and **1
new false PASS** (§2.3). That is the whole argument for fixing acceptance *before* relaxing
the retry.

### 2.5 A user's source file is replaced by a JSON report, and nothing notices — **FIXED in `f3f69c5`**

```
request : "fix <T>/pkg/calc.py"
before  : def add(a, b):\n    return a - b\n        (32 bytes)
after   : {"capability_id":"code.multilanguage.parse.tree_sitter.v1", "symbol_count":1,...}   (545 bytes)
verdict : FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN     (a report, and no source)
```

A parse/report capability wrote its artifact over the named source file. The observation
gate catches a *deleted* file (`NAMED_INPUT_REMOVED`) but not a *replaced* one — the path
still exists. The redirect guard that prevents exactly this (`_dangerous_output_redirect`,
`swe_typed_plan_v1.py:100-116`) exists and is only applied inside the typed-plan path.

**Fixed by moving the rule to the one function that already owned it.** `F10`
(`goal_front_compiler_v1.repair_output_collisions`) has always said *"an output path is never
one of the action's own input files"*, and `F13` has always had the remedy for a sentence
that names no output at all — a deterministic spool artifact. Neither could see a sentence
whose only other slot is a **directory** (`source_root`), so nothing collided; and the
composer bound its own arguments with no version of the rule at all. `F10b` adds the missing
condition once, and the composer now *calls* that function instead of carrying a copy.

| request | before | after |
|---|---|---|
| `Explain the bug in <S>` | `<S>` replaced by the parse adapter's JSON (32 B → 545 B) | `<S>` byte-identical, result spooled, honest refusal |
| `Count the functions in <S>` | same destruction, **and no refusal** | `PASS`, `function_count: 2`, `output_path` in the spool, `<S>` untouched |
| `Explain why the test in <T> fails` | destruction, `NAMED_SOURCE_UNPARSEABLE` | `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` |
| `Show the first line of <S>` | `PASS` | `PASS` (unchanged) |
| `Write the text 'hello' to <O>` | `PASS` | `PASS` (unchanged: the sentence states a change, so the binding is byte-for-byte what it was) |

Removing the destruction uncovered the defect it had been hiding: with the file no longer
being destroyed, `Explain why the test in <T> fails` came back as `PASS` from
`code.impact.tree_sitter.testselect.v1` — a test *selection* capability whose own
`expect: output_verified` was treated as the sentence's goal (§2.3's seam). The door now
reads a stated explanation effect and refuses a capability whose own declaration neither
explains nor localizes (`FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED`).

### 2.6 20 of 64 SWE registry rows are stubs that certify themselves

```
row: python.symbol.resolve.standalone.v1     status: VERIFIED_BOUND_CAPABILITY
     verification.independently_verified_by: hardcore_verify   (+ a receipt path)
adapter: 28 lines. reads BOUND_CAPABILITY_REGISTRY_V1.json, checks that the tokens it
         declares are present in that same file, writes {"verified": true}
run      -> {"output_verified": true, "verified": true}
result   -> resolves zero symbols. It advertises "ast definitions + references + call_edges
            + inverted callers_of"; the artifact contains none of them.
```

23 rows overall (20 of them SWE), median 29 lines, providing 44 tokens. Those tokens carry
**27 `requires` edges between real capabilities** (supplied by 15 distinct stub rows), and
they hold up the whole
`software.hardcore.{swe,final,closing}.supercomposer` "advanced SWE engineer" tower — a
structure whose top node reports `verified: true` while the artifact's `composition` field is
prose: `"triad proven → test contract verified → ... → closing"`. The composer's own plan for
`software.hardcore.closing.verified` is **36 steps, 11 of them these stubs**.

Separately, `python.refactor.rename_symbol.v1` writes `"verified": false` in its artifact
while the door passes it, because the registry `expect` reads `output_verified` instead. Two
truth fields, opposite values, in one artifact, and the door reads whichever is convenient.

### 2.7 70% of the 419 "capabilities" are receipts, not capabilities

```
BRAIN_UNIFIED_MODEL_V1.json   entries: 419
  kind RECEIPT_BACKED_CAPABILITY : 294   (of which present in the live registry: 0)
  kind BOUND_CAPABILITY          : 125   (of which self-certifying stubs: 23)
```

The unified model serves the receipt-backed ones through `unified_model.solve` as
`PASS__RECEIPT_BACKED_BOUND_CAPABILITY_EXECUTED` — "merely ran and reported success" is the
model's own wording for them. None of the 294 is in the live bound registry, so none is
re-executable today; they are history. The executable surface is therefore:

**419 claimed → 125 registry rows → 102 non-stub adapters → 44 SWE adapter files →
0 SWE rows with independent-oracle credit → 2/22 human sentences honestly answered.**

That chain is the honest size of the machine, and no document in the repository states it.

### 2.8 "Try it; if it cannot, learn how" does not learn

`solve_or_learn` on an unsupported goal, three runs: same verdict, same 0.1 s, and the
return payload carries `learned: None`. Nothing is recorded, nothing is retried differently.
The owner's active goal (`OWNER_ACTIVE_GOAL_20261018_V1.md`) is *instant learning*. There is
no measured instance of it.

### 2.9 Running the door mutates tracked repository state

`solve()` writes `canonical/runtime/state/experience_v1.json` (tracked) and drops
`*_CONTROLLER_CHECKPOINT.json` files into `canonical/astra_runtime/state/` on failure. A
measurement that changes the tree it is measuring is not reproducible, and 42 untracked
scratch files accumulated in one session.

### 2.10 Zero SWE credit exists

`TRUE_CAPABILITY_LEDGER_V1.json`: 9 specs, **0 SWE**, all `MEASURED_SANDBOX`, authority
NONE. All 30 `canonical/verification/HARDCORE_VERIFY_*` receipts are `verified: true`,
repeat the producer's own hash and name no separate verifier run.

---

## 3. P0 — reachability: the owned capabilities are behind a door nobody fits through

### 3.1 Ten realistic "be a software engineer" requests: 0 answered, 1 hangs forever

Each on a fresh tree; the oracle is the filesystem and the real test runner.

| request | verdict | capability chosen |
|---|---|---|
| create a CSV→JSON CLI with `--delimiter` + a passing unittest | **HUNG (>60 s, unbounded — §3.3)** | — |
| add a `--verbose` flag and cover it in tests | FAIL_CLOSED__NO_OBSERVED_EFFECT | — |
| make a tempfile-based test deterministic (flaky) | FAIL_CLOSED__NAMED_SOURCE_UNPARSEABLE | `code.impact.tree_sitter.testselect.v1` |
| fix a circular import between `a.py`/`b.py` | FAIL_CLOSED__NO_OBSERVED_EFFECT | `software.repair.choreograph.crossfile.v1` |
| annotate so `mypy` passes | FAIL__RAW_GOAL_COMPILATION_GAP | — |
| write a PR description for a diff | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED | `python.software.request.semantic_behavior.compile.v1` |
| make an O(n²) function O(n) and prove it | FAIL_CLOSED__NAMED_SOURCE_UNPARSEABLE | `code.impact.tree_sitter.testselect.v1` |
| split a module into reader/writer without breaking tests | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED | **`docx.document.create_from_json_record`** |
| replace a `requests` dependency with stdlib | FAIL__LIVE_CONTROLLER_EXECUTION | `decision.synthesis.typed.stdlib` |
| fix the source so a failing test passes | FAIL__LIVE_CONTROLLER_EXECUTION | **`chart.raster.axis_title_unit_binding.v1`** |

Truthful reading: **0/10 pass**, and 3 of 10 choose a different domain — Word documents for
a module split, chart axis titles for a failing test. This is the class the earlier reports
called "one word matched"; it is still live on the request shapes that matter most.

### 3.2 22 human sentences → 2 honest answers

12 repair/refactor/navigation sentences (`repair_full`, `fix_broken`, `bug_report`,
`rename_param`, `fix_short`, `rename_callsites`, `find_callers`, `write_unit_test`,
`explain_fail`, `refactor_extract`, `type_check`, `lint`): **4 PASS, 2 of them false**
(§2.1, §2.2). Plus §3.1: 0/10. Combined honest rate: **2/22 ≈ 9%**.

The sharpest single gap: `"Rename the function add to plus in <file> and update every
caller"` → `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED`, plan `None`, while §1 shows
`rename_symbol` performing exactly that, correctly, across two files. The capability is owned
and unreachable. That is integration debt, not a missing primitive.

### 3.3 A "create a new file" request audits the Brain's own test corpus for hours

Traced at the syscall boundary for `"Create a Python CLI at <T>/pkg/cli.py ... and add a
unittest at <T>/pkg/test_cli.py that passes"`:

```
1. git -C <T>/pkg/cli.py rev-parse HEAD                      (a file, not a repo; 10 s cap)
2. python -c <SUITE_RUNNER> canonical/tests/test_a_binder_...py   cwd=/home/user/brain, timeout=180
3. ... one process per file in canonical/tests (2,138 files)
```

`source_root` was never stated by the sentence and the derivation cannot derive it (the
named files do not exist yet), so `python_test_audit.run` falls back to its own default,
`canonical/tests` (`python_test_audit.py:114`). The machine then runs **its own 2,138-file
test suite** as "the unit test for your CLI", 180 s per file, with no global budget. The
request is the single most common thing a software engineer is asked to do: *create
something that does not exist yet*. There is no code path for it: every capability is shaped
around reading files that already exist.

### 3.4 Even naming the capability explicitly does not reach it

For 12 advanced SWE capabilities, the sentence `"Run the capability <id> on the python
source root <existing dir> and save the report to <out>"`:

```
python.refactor.rename_symbol.v1            FAIL__RAW_GOAL_COMPILATION_GAP
python.refactor.extract_function.v1         FAIL__RAW_GOAL_COMPILATION_GAP
python.source.symbols.index.ast             FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
python.source.audit.ast                     FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
python.review.diff_static_triage.v1         FAIL__RAW_GOAL_COMPILATION_GAP
python.review.diff_type_gate.v1             FAIL__RAW_GOAL_COMPILATION_GAP
python.tests.generate.scaffold.v1           FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
python.tests.audit.unittest                 FAIL__RAW_GOAL_COMPILATION_GAP
python.source.change_impact.testselect.v1   FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
python.repo.diff_apply_full_testgate.v1     FAIL__RAW_GOAL_COMPILATION_GAP
software.hardcore.kernel.orchestrate.v1     FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
python.software.issue_to_pr.orchestrate.v1  FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
```

**0/12.** So the reachability census figure (`411 REACHED_AND_BOUND / 419`) is not a
statement about advanced SWE capabilities under any sentence a user or an agent would write;
it is a statement about goals generated from the capability's own name in the compiler's
expected shape.

---

## 4. P1 — capability depth: what an advanced engineer does that this cannot

### 4.1 The toolchain the "advanced review gates" need is installed by no workflow

`requirements/software_engineering_kernel_v1.txt` pins `crosshair-tool`, `hypothesis`,
`z3-solver`, `tree_sitter*`, `typeshed-client`. `grep -rl software_engineering_kernel_v1
.github/` → **no match**. Absent on this machine: `mypy`, `ruff`, `coverage`, `bandit`,
`z3`, `crosshair`, `pytest`. Present: `git`, `node`, `npm`, `gcc`, `gh`.

Consequence: `python.review.diff_type_gate`, `..._coverage_gate`, `..._security_gate`,
`..._mutation_gate`, `python.contract.check.crosshair.v1`, and every z3-backed synthesis row
cannot check anything here, and each degrades to `UNAVAILABLE` / `PASS_BLIND` (the registry's
`gate == "PASS"` expectation then fails closed — correct, but the capability is inert). The
advertised capability "type-check a change" does not exist on the machine, and nothing in CI
makes it exist.

### 4.2 The three refactor capabilities are red on their own tests

```
test_python_refactor_rename_parameter_v1   16 tests, 1 ERROR  (TESTS_RED_AFTER_EDIT:<no output>)
test_python_refactor_rename_symbol_v1      18 tests, 1 ERROR
test_python_refactor_extract_function_v1   15 tests, 2 ERRORS
test_python_repo_diff_apply_full_testgate  13 tests, 3 FAIL   (gate 'FAIL' != expected 'PASS')
```

Across 81 SWE-related test files on pristine `main`: **14 red (17%)**, and the reds are the
flagship rows — `rename_parameter`, `rename_symbol`, `extract_function`,
`diff_apply_full_testgate`, `review_diff_security_gate`, `review_diff_mutation_gate`,
`source_symbol_index`, `repair_apply_verified`. The honest baseline (344 failures) has not
moved down; the SWE core is inside it.

### 4.3 Cross-file editing: it plans, it does not apply — and the applier is broken

`python.source.crossfile_edit.choreograph.v1` (438 lines) *plans* an edit and states it
"Plans, does not apply". The only multi-file applier is
`python.repo.diff_apply_full_testgate.v1`, which needs a **human-supplied** `diff_path` and
is red on its own tests (§4.2). So the machine cannot author and apply a multi-file change
end to end. Verified directly: a valid two-file unified diff, applied to a fresh package,
aborted `DIFF_DOES_NOT_APPLY` before any test ran.

### 4.4 No capability for most of the job

Searched by the registry's own keywords over 125 rows:

| what an engineer must do | rows | note |
|---|---|---|
| version control (commit, branch, log, bisect, revert) | **0** | only `pr_realize` + `diff_apply`, both `gh`/network-shaped |
| debug a crash / step / breakpoint | **0** | no pdb, no traceback→cause reasoning |
| build, package, install (`setup.py`, `pyproject`, wheel, venv) | **0** | `pypi.provenance` is not a build |
| resolve dependencies / lockfiles | **0** | — |
| profile / find a bottleneck | 1 | `review.diff_perf_gate`, needs perf tooling |
| flaky-test diagnosis | **0** | measured request → wrong capability (§3.1) |
| concurrency/async/race correctness | 0 real | 4 rows merely mention the words |
| architecture/comprehension of an unfamiliar repo | 0 | `choreograph` plans edits, not designs |
| any language other than Python | **0 editable** | tree-sitter *parses* 8 languages; nothing edits, tests, builds or runs any non-Python language |
| semantic test authoring | 0 | `tests.generate.scaffold` is explicitly "smoke-class only: asserts the result is not an exception" |
| long-horizon task decomposition to a PR | 0 reachable | `issue_to_pr.orchestrate` (667 lines) exists, unreachable (§3.4) |

### 4.5 The composition graph is built on the stubs

`capability_composer_v1.plan(seed, "software.hardcore.closing.verified")` returns a
36-step chain whose members include 11 self-certifying stubs (§2.6). 187 distinct `provides`,
86 never consumed, 37 `requires` tokens with no producer at all, and the 27 edges that *are*
consumed from the stub set are exactly the ones that make the graph look connected.
`bridge_enumeration_v1` proves bridges **by execution** — and its output never reaches the
composer. The fix already exists in the repository and is unwired.

---

## 5. P1/P2 — the "fastest, most efficient" requirement is unmeasured

### 5.1 The cost model is fake, so "fastest" cannot be chosen

```
cost histogram over 125 rows:  1 -> 107 rows,  2 -> 18 rows
rows carrying latency/wall/bytes fields: 0
adapters exposing timing or byte cost: 0
```

Nothing in the machine can compare two correct capabilities by time, bytes or money, so the
scheduler law ("max capability gain per wall-clock × compute × memory × cost") cannot be
evaluated, and the owner's "fastest way with minimal actions" has no substrate underneath it.

### 5.2 No global budget; a bad binding runs for hours

§3.3 is the existence proof: an unbounded subprocess fan-out (2,138 × 180 s) inside a single
`solve()` call, with no wall-clock cap, no step budget and no cancellation. Observed cost of
one bad binding: >20 minutes, killed by my harness.

### 5.3 Double work on every failure

`solve()` re-enters the entire gate chain (compile → admit → execute → all honesty gates) for
the typed retry; the decisive typed plan is not cached across the two attempts. Measured
`PASS` runs: 127-770 ms; the typed selector alone is ~119 ms.

### 5.4 One-line doc edits force a 9.4 MB model rebuild

`BRAIN_UNIFIED_MODEL_V1.json` hashes root `*.md`, all intents and all runtime source, so any
governance or documentation change invalidates `ARTIFACT_INTEGRITY` and forces a full
deterministic recompile. The fastest correct edit is the most expensive one.

---

## 6. Owner-only / cannot be landed by an agent

- `heartbeat` is **not** in the ruleset's required checks and its last runs are red; the full
  suite exceeds its 40-minute timeout and has never finished on the public runner.
- The 30 `HARDCORE_VERIFY_*` receipts are tautological (repeat the producer's own hash).
- Adding the SWE kernel install to CI and sharding the heartbeat require touching protected
  workflow files / the ruleset.

---

## 7. The honest ranking of what to fix, and why in this order

Everything below is `INDEPENDENT_FALSIFICATION_OF_A_FALSE_GENERAL_CLAIM` or
`VERIFIED_REUSABLE_CAPABILITY_GAIN`, agent-landable, $0, zero model dependency.

1. **Acceptance from the sentence, not the capability's own `expect`.**
   *Landed for the `fix`/`repair` shapes in `3671140` and for stated bug reports in `4340001`.
   The remaining half is §2.1c: the machine already finds, verifies and applies the right
   patch when the sentence carries a verb, and refuses a bug report only because the planner
   cannot name the repair family for a sentence with no imperative.*
   (a) a test command that collects zero tests is a failure, on the stated branch as on the
   discovered one (`python_repair_apply_verified_v1.py:181`); (b) a request that names a
   source file and asks for a change may only be answered by a capability whose own effect is
   a source edit — not by a search, a report, or an audit; (c) the redirect guard
   (`_dangerous_output_redirect`) applies on the primary route, so a report can never overwrite
   a named source file. Oracle: the file's bytes + the real runner. This removes §2.1-2.5.
2. **Give "create software" a path.** An artifact contract: the named output file must exist,
   parse, and the named test must run and pass — with `source_root` derived from the stated
   output path, never defaulted to `canonical/tests` (§3.3), and a hard per-request wall-clock
   budget (§5.2). Oracle: the created file + its test result.
3. **Delete the 20 stub rows and repoint the 27 fabricated edges** at
   `bridge_enumeration_v1`'s execution-proved `BRIDGE_VERIFIED` rows (§2.6, §4.5). This costs
   nothing and removes the false self-model; it also removes 11 dead nodes from that plan.
4. **Install the pinned kernel in CI and on the machine** (§4.1), then fix the 14 red SWE test
   files (§4.2). Type-check, lint, coverage, mutation and security become real capabilities
   instead of inert rows — and the suite stops being a red signal.
5. **Wire the owned, working capabilities to human sentences** (§3.2, §3.4):
   `rename_symbol`, `extract_function`, `issue_to_pr.orchestrate`, `diff_apply_full_testgate`,
   `change_impact.testselect`. The template already exists and is measured — the effect-family
   resolver that took caller-finding from dark to PASS (#6306). This is the cheapest real
   capability gain available: the code already works.
6. **Real cost/timing on every row + plan caching** (§5.1, §5.3), so "fastest" becomes a
   computable quantity instead of a constant.
7. **Only then breadth**: a git lane (diff/commit/branch/log/bisect), a debugger lane
   (traceback → cause → patch), dependency/build resolution, non-Python editing, semantic
   test authoring.

---

## 8. What is not measured here (limits of this document)

- I did not run the full 11,525-case suite; the 344-failure baseline is the project's, and I
  measured 81 SWE-related files (14 red).
- Long-horizon behaviour (a real issue → PR) is not measured because no reachable composition
  exists to measure; that is a finding, not a gap in this measurement.
- Network-dependent rows (`gh`, `pip install`, chromedriver) were not exercised.
- The 37-family score (0.8241) is taken from the prior session's record and was not re-run;
  §3.1 is my measurement of the same machine on human-shaped requests, and the two are not
  comparable (machine-authored vs human sentences).
