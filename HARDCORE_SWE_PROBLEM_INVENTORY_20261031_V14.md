# Every hardcore-SWE problem, measured on `ecfc9fb` (V14)

Every number below was produced on **this tree at `ecfc9fb`** by instruments that already exist in the
repository, and every one of them is reproducible from §6. Where a claim is carried over from an
earlier inventory it says so and names what was re-measured instead. Nothing here is a projection.

Supersedes `HARDCORE_SWE_PROBLEM_INVENTORY_20261031_V12.md` (measured on `f333567`) and
`HARDCORE_SWE_PROBLEM_INVENTORY_20261031_V13.md` (merged in #6468, measured on `9f80823`). Both stay in
the tree; §3 reconciles the three and corrects two V13 inferences.

---

## 0. The answer in one paragraph

**The machine is a fast, honest Python repair-and-audit tool that lies about nothing and cannot yet do
most of what an advanced software engineer is asked to do.** Three instruments agree. Ordinary team
work: **20 of 54 real, 0 false, 0 damaged**, median **306 ms** — the improvements since V12 are real
(`17 → 20`, toolchain `1/7 → 3/7` once the analysers exist). Hardcore sentences: **25 of 28**. Advanced
work: **4 of 49 served**, and one of those four is a *wrong answer in the right shape* ("Review X for
API design problems" answered by a secret scanner). The registry says 440 capabilities; **293 of them
are `.auto.v1` projections of runtime modules, not capabilities**, and of the 147 real rows only **30
were ever selected** by the 77 measured requests — **118 real rows were never selected at all**. Whole
product domains are empty: C/C++/Rust/Go/Java **0 rows**, build & packaging **0**, CI **0**, profiling
**0**, concurrency **0**, design/ADR **0**, git surgery **0 usable**. Inside Python — the home turf —
the repair engine now finds a dropped operand, but still cannot express a lock, a parameterised query,
or a change that spans files. And the machine's own laws are not green: **24 of 625** capability tests
fail on clean `main`, and the required CI job has been red on a test that fails on `main` for longer
than this inventory has existed.

---

## 1. The seven numbers

### 1.1 Surface census — 28 hardcore sentences, 25 real

`hardcore_swe_surface_probe_20261030.py --jobs 4 --floor 25`

```
SURFACE REACHED 25/28        median 930 ms
FAIL fix_race                 1682 ms  python.software.repair.apply.verified.v1   FAIL__LIVE_CONTROLLER_EXECUTION
FAIL sql_injection             521 ms  (no capability)                           FAIL__CAPABILITY_DAG_RESULT_INVALID
FAIL fix_then_regression_test 6457 ms  python.software.repair.apply.verified.v1   suite green, no regression test written
```

The three failures are one class each: a **repair the grammar cannot express** (adding a lock), a
**composed plan whose steps cannot bind their inputs** (parameterise a query: a 2-step DAG of the
crossfile choreographer, both steps `MISSING_REQUIRED_ARGUMENTS`), and a **two-effect sentence that
delivers one effect** (fix + leave a regression test behind → the fix lands and verifies, the test is
never written).

### 1.2 Ordinary matrix — 54 cases of team work

`execution_guard/swe_capability_matrix_v1.py`

```
TOTAL 54   REAL 20   FALSE 0   DAMAGED 0   REFUSED 34
LATENCY median 306 ms   p90 1030 ms   max 2274 ms
repair 5/7   analysis 8/12   refactor 3/8   toolchain 3/7   tests 0/3   git 0/5   feature 1/7   honesty 0/5
```

`FALSE 0` and `DAMAGED 0` are the two numbers that matter most and they are good: on these 54 requests
the machine never claimed an effect it did not produce and never touched a file it was not asked to
touch. `honesty 0/5` is **not** a problem — all five are destructive or ambiguous requests that were
correctly refused; the metric counts "served", not "right".

The 34 refusals by cause: 10 `ROUTE_ADMISSION_REJECTED`, 7 `RAW_GOAL_COMPILATION_GAP` (nothing even
compiles), 7 `STATED_ANSWER_NOT_PROVIDED`, 4 `LIVE_CONTROLLER_EXECUTION` (opaque), 2
`PROMISED_SOURCE_CHANGE_NOT_APPLIED`, and one each of `REGION_INVALID`,
`CAPABILITY_RETURNED_A_VERDICT`, `SUITE_RED`, `STEP_RAISED_OUTCOME_UNKNOWN`.

### 1.3 Advanced census — 49 requests of the actual product

`execution_guard/swe_advanced_probe_v1.py` (a census: no per-request oracle, `SERVED` means
`pass: true` and nothing unauthorised changed — the `selected` column is the finding)

```
REQUESTS 49   SERVED 4   REFUSED 45
polyglot 0/7   build 0/5   ci 0/4   perf 0/4   systems 0/3   tests 1/6
debug 1/3      refactor 0/6   review 2/3   git 0/5   design 0/3
```

The four served, verbatim:

| # | request | answered by | verdict |
|---|---|---|---|
| 29 | Run the test suite and tell me which tests fail and why | `python.repository.acceptance.measure.v1` | right |
| 32 | Find the commit that broke the test | `python.source.change_impact.testselect.v1` | right shape, 1 of 3 git-history asks |
| 39 | **Review `pkg/service.py` for API design problems** | `python.source.secret_scan.v1` | **wrong answer, served** |
| 40 | Review `pkg/calc.py` for security issues | `python.review.diff_security_gate.v1` | right |

Refusals by cause: **17 opaque** `LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE` (a free-text
reason is the only diagnosis), 8 `STATED_ANSWER_NOT_PROVIDED` (named — the good shape), 8
`RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP`, 6 `ROUTE_ADMISSION_REJECTED` (R10/R3/R11), 2
`CAPABILITY_REFUSED` (`WORKTREE_NOT_DIRECTORY`, `REGION_INVALID`), 2 `NO_OBSERVED_EFFECT`, 1
`TOOL_REPORTED_NON_SUCCESS`, 1 `CAPABILITY_EXITED_PROCESS`.

### 1.4 Registry composition — the capability budget is 3× smaller than it reads

Measured through `load_verified_registry()`:

| measure | count |
|---|---|
| rows in the live verified registry | **440** |
| `.auto.v1` projections (one per runtime module — not capabilities) | **293 (67 %)** |
| real rows | **147** |
| SWE-prefixed rows (`python.`/`code.`/`software.`/`test.`/`orchestration.`/`git.`) | **84** |
| distinct capabilities that answered one of the 77 measured requests | **30** |
| real rows never selected by any of those 77 requests | **118** |
| SWE rows exercised | **27 / 84** |

And by domain, counting rows that can actually be selected for work:

| domain | rows | evidence |
|---|---|---|
| **C / C++ / CMake / clang** | **0** | request 1, 7 both refused; no row matches `cpp`, `cmake`, `clang` |
| **Rust / cargo** | **0** | request 2 refused (`dead_code` selected); only a *tree-sitter parser* mentions Rust |
| **Go** | **0** | request 3 compiles to nothing |
| **Java / Gradle / Maven** | **0** | request 4 compiles to nothing |
| **build / packaging / deps / lockfile / wheel** | **0** | requests 8–12 all refused; "Install the pytest package" routes to `archive.tar_gz.create_from_manifest` |
| **CI authoring / repair** | **0** | requests 13–16 all refused |
| **profilers / benchmark-with-baseline** | **0** | requests 17–20 all refused |
| **concurrency / race / async** | **0** | requests 21–23 all refused; and `fix_race` fails the surface census |
| **design / planning / ADR / migration plan** | **0** | requests 47–49 compile to nothing or exit the process |
| git | **2** (`operate`, `bisect`) | 0/5 git asks served; "Show the last three git commits" *does* pass (read path) |
| SQL / schema | **2** (`sqlite.table.*`) | no migration authoring; a `schema.sql` request routes to `decision.synthesis.typed.stdlib` |

### 1.5 Integrity of the word "verified"

| measure | count |
|---|---|
| adapters that write `"output_verified": True` as a literal | **40** |
| adapters that write `"verified": True` as a literal | **15** |
| rows with **no** verification block in the registry | **14** |
| SWE rows that declare **no** `proposal_bindings` (no input contract) | **73 / 84** |
| rows overall that declare no `proposal_bindings` | **413 / 440** |

This is the class the standing laws call the worst defect: a claim of verification that is a constant
in the adapter rather than an observation of the world. It is not hypothetical — §1.3 shows a request
served by an adapter that answered a different question.

### 1.6 The machine's own laws are not green

* Focused capability suite at `ecfc9fb` (clean tree, no local change): **625 tests, 21 failures,
  3 errors** in 117 s. Names include `test_capability_type_surface_v1::test_no_unknown_types`,
  `test_extended_capability_registry_v1::test_merge_opt_out_and_canonical_precedence`,
  `test_hardcore_swe_capabilities_20261031_v1::test_live_front_door_end_to_end_move_addparam_spec_choreograph_and_refusals`,
  two in `test_hardcore_swe_capabilities_and_speed_v1`, `test_bound_capabilities`,
  three `test_a_question_about_the_file_is_still_answered_by_the_census`, and an **error** in
  `test_capability_dag_live_wiring_v1`.
* CI's `verify-brain-unified-model-v1` job is **red** on
  `test_goal_compiler::test_compound_goal_compiles_full_verified_audit_pipeline`, which also fails on a
  clean `main` worktree. It does not block: a pull request with that job red still merges (measured —
  the merge state reads `UNSTABLE`, not `BLOCKED`), so the repository's own test job is a red light
  nobody acts on.
* The last full honest baseline (`canonical/verification/HONEST_SUITE_BASELINE_20261017_V1.json`) is
  **11,754 cases, 380 failed, 223 files with failures**, from 2026-10-17. Nothing has re-measured it.

### 1.7 Speed — selection is fast in the common lanes; execution and misfires are not

| what | measured |
|---|---|
| cold front-door call (`Show the last three git commits`) | **240 ms** |
| selection only (`typed.build_plan`, no execution) | **84–313 ms** typical, **3.36 s** on `Review <f> for security issues`, 0.1 ms on a non-SWE goal |
| census median | **930 ms** |
| `index_whole_runtime` (index all of `canonical/runtime`) | **28.5 s** |
| `fix_failing_test` (repair + verify) | **6.8 s** |
| a *mis-selected* rename (`inline_helper` on a directory rename) | **16.0 s wasted**, then failed |

Selection is not the bottleneck; execution and **misfires** are. There is no cache of a repeated
request: six near-identical failure modes in the census were each re-derived from scratch.

### 1.8 Nothing measures the product in CI

| instrument | workflows that run it |
|---|---|
| `hardcore_swe_surface_probe_20261030.py` | **1** (added 2026-10-31, floor 25) |
| `swe_capability_matrix_v1.py` (54 cases) | **0** |
| `swe_advanced_probe_v1.py` (49 requests) | **0** |

322 workflows exist. The two instruments that measure *whether the machine can do the work* are not
among them; the one that is covers 28 sentences out of 131 measured requests.

### 1.9 The declared dependency graph cannot be walked

Every row may declare `requires` (effect tokens it consumes) and `provides` (effect tokens it
publishes). Measured over `load_verified_registry()`:

| measure | count |
|---|---|
| SWE rows that declare `requires` | **47 / 84** |
| ... whose *every* requirement another real row provides | **40** |
| ... with at least one requirement **no row provides at all** | **7** |
| ... declaring nothing | **37** |
| `requires` edges in the whole registry naming a token no row provides | **45 edges / 26 tokens** |
| of those, edges whose "token" is actually a **capability id** | **6**, all on `python.source.symbols.index.ast` |
| adapter modules on disk | **166**, of which **136** are named by a registry row → **30 orphans** |

The seven rows that cannot start **even in principle**: `software.repair.choreograph.crossfile.v1` —
the **most-selected row in the advanced census (8 of 49 requests)** — plus
`python.refactor.move_function.v1`, `python.software.issue_to_pr.orchestrate.v1`,
`python.tests.generate.scaffold.v1`, `python.symbol.resolve.standalone.v1`,
`python.issue.natural_language.parse_edit_intent.v1` and `git.repository.operate.v1`.

Six of the seven require the string `python.source.symbols.index.ast`. That is not an effect token; it
is **the id of a row in the same registry**, and that row publishes `python.source.symbol_index`. The
producer exists, is verified, is indexed — and the requirement cannot see it, because
`plain_goal_bound_grounding._bindability_context` keys provider slots by published effect token. (That
binder, `grounded_executable_composition.py` and `bridge_enumeration_v1.py` all already walk
`requires`; the front door does not call them on the ordinary path.) `git.repository.operate.v1` is the
genuinely missing producer: nothing publishes `git.repository.available`.

So this is two defects, not one. A **data** defect of six strings, and a **wiring** defect: the graph
is declared, the binder that could walk it is written, and the route that needs it does not call it —
composition still only fires after a raw-goal compilation failure, which a decisive typed plan forbids.

---

## 2. The problems

Ranked by capability gained per hour of work. Every row names its evidence in this document and what
already exists to reuse, so none of this requires a new primitive.

### P1 — Selection: five magnets, and a composer that answers as if it were the work

| ID | problem | evidence |
|---|---|---|
| **P1.1** | `python.source.dead_code.v1` absorbs change requests | advanced 2, 17, 18, 20, 23, 28 (6) |
| **P1.2** | `git.history.bisect_regression.v1` absorbs commit / branch / diff / changelog / benchmark | advanced 19, 26, 42, 43, 44 (5) |
| **P1.3** | `software.repair.choreograph.crossfile.v1` absorbs vendor / pin-deps / fix-CI / find-race / plan-migration | advanced 11, 13, 21, 36 (4) + 4 surface |
| **P1.4** | `python.refactor.inline_helper.v1` absorbs move / split / type-hints / vendor / **rename** | advanced 12, 33, 34, 37; and a live rename on a directory cost **16 s** |
| **P1.5** | `python.tests.mutation_score.v1` absorbs CI edits and test authoring, and is handed YAML | advanced 1, 14, 16, 27 |
| **P1.6** | planners/composers are chosen as *answers* rather than as steps | advanced 13, 36, 48; `python.source.crossfile_edit.choreograph.v1` **exits the process** on 48 |
| **P1.7** | a wrong answer is served as a pass | advanced 39: API-design review answered by a secret scanner |
| **P1.8** | unserved-language requests get a Python row and a dead end | advanced 1, 5, 7 (`STATED_LANGUAGE_NOT_SERVED_BY_CAPABILITY:cpp/ts`) |

Reuse: the family table in `swe_typed_plan_v1._FAMILIES` and the effect-keyed
`_resolve_family` route; the door's existing `_STATED_EFFECTS`; the existing
"composition rows are steps, not answers" distinction. **22 of 49 advanced requests** are absorbed by
these five rows; the tarball-creator-on-"install" case shows the same defect one row deeper.

### P2 — The product domains that are empty

| ID | problem | evidence | what exists to build on |
|---|---|---|---|
| **P2.1** | **no systems language**: C, C++, Rust, Go, Java — 0 rows | advanced 1–7: 0/7 | `code.multilanguage.parse.tree_sitter.v1` already parses these grammars; the verified command runner already runs `cmake`/`cargo`/`go`/`javac`; `python_repo_diff_apply_full_testgate` is language-agnostic |
| **P2.2** | **no build/packaging**: pyproject, dependency add/pin, lockfile, vendoring, Makefile target, wheel, SBOM | advanced 8–12: 0/5 | the same test-gated patch engine + TOML/YAML edit + postconditions |
| **P2.3** | **no CI**: author a workflow, fix a failing job, add caching, quarantine a flake | advanced 13–16: 0/4 | YAML edit + `python.test.pipeline.verifier.v1`-class row + the command runner |
| **P2.4** | **no performance work**: profile, benchmark against a baseline, optimise a hot path | advanced 17–20: 0/4 | `cProfile`/`timeit` in a child; the diff-perf gate already compares two sides |
| **P2.5** | **no concurrency**: find a race, bound a pool, make async safe | advanced 21–23: 0/3; surface `fix_race` fails | the localizer's trace + a synchronisation-idiom family (see P3.1) |
| **P2.6** | **no design/planning**: ADR, design doc, migration plan | advanced 47–49: 0/3 | the composer + the document writers that already exist |
| **P2.7** | **git surgery**: commit, branch, cherry-pick, changelog, rebase | matrix git 0/5; advanced 42–46: 0/5 | `git.repository.operate.v1` exists and reads; it has no write postcondition |
| **P2.8** | **SQL/schema**: no migration authoring, no schema change | advanced 6 | two sqlite rows, no DDL planner |
| **P2.9** | **tool acquisition**: the machine cannot install what its own rows need | "Install the pytest package" → a tarball creator; `pynguin`, `hypothesis`, `z3`, `semgrep` absent | `auto.pypi.library.acquisition`, `auto.apt.*` rows exist |

P2.9 is why §1.2's toolchain lane reads `3/7` today: it reads that **only because** `ruff`, `mypy`,
`bandit` and `coverage` were installed by hand before the run. On a clean machine that lane is 1/7 and
three refusals are an *environment* fact masquerading as a capability fact.

### P3 — Depth inside Python: what the machine's home turf still cannot do

| ID | problem | evidence |
|---|---|---|
| **P3.1** | the repair grammar cannot express a **synchronisation idiom** (introduce a lock around a read-modify-write, take a re-entrant lock in `__init__`, guard the critical section) | surface `fix_race`: 0/10 green, `lock_present: false` after a full ladder |
| **P3.2** | the repair grammar cannot express a **parameterised query** (`"%s" % x` → `?` + args tuple) | surface `sql_injection`: payload still spliced |
| **P3.3** | a sentence with **two effects** delivers one: repair lands, regression test is never written | surface `fix_then_regression_test`: suite green, `fixed_value 5`, `new_test_files: []` |
| **P3.4** | `extract_function` refuses `REGION_INVALID` on "extract the **loop** in `fn` into a helper" | matrix `extract_function`; advanced 38 |
| **P3.5** | `move_function` fails end-to-end (`FAIL__LIVE_CONTROLLER_EXECUTION`) | matrix `move_function`; advanced 33 (routed to `inline_helper`) |
| **P3.6** | `add_type_hints` and `extract_constant` are rejected at admission | matrix `add_type_hints`, `extract_constant` (`ROUTE_ADMISSION_REJECTED`) |
| **P3.7** | **feature implementation** across files: 1/7 | matrix `feature` lane: `add_cli_flag` (no compile), `add_logging`, `add_retries`, `implement_issue`, `crossfile_feature` (admission), `fix_failing_ci` |
| **P3.8** | **test authoring** is not reachable although rows exist (`python.tests.synthesize.pynguin.v1`, `evidence.oracle.hypothesis_property.v1`) | matrix tests 0/3; advanced 24–28 → 1/6; both backends uninstalled |

P3.1 and P3.2 are the same shape as the `DROPPED_OPERAND` family added on 2026-10-31: the search space,
not the search, is the ceiling. Each is one structural family in `_candidate_specs`, verified by the
suite that already runs.

### P4 — Capability that exists and cannot be reached

| ID | problem | evidence |
|---|---|---|
| **P4.1** | **118 of 147 real rows were never selected** by 77 representative requests | §1.4 |
| **P4.2** | rows whose backend is not installed are still offered, then fail at run time | `pynguin`, `hypothesis`, `z3`, `semgrep` absent; §1.2 toolchain caveat |
| **P4.3** | "Write a unit test for `mul`" is rejected at admission on a **payload slot** the row itself never derives | advanced 24 `R11_STATED_PAYLOAD_SLOT_MISSING` |
| **P4.4** | 8 of 49 advanced requests compile to **nothing at all** | `RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP` |
| **P4.5** | 6 registry rows spell a requirement as another capability's **id** instead of its published token, so the producer exists and the consumer cannot bind it — including the top magnet, `software.repair.choreograph.crossfile.v1` | §1.9; `python.source.symbols.index.ast` publishes `python.source.symbol_index` |
| **P4.6** | the front door never walks `requires`; `plain_goal_bound_grounding` and `grounded_executable_composition` already do, and are not called on the ordinary path | §1.9; composition only after `RAW_GOAL_COMPILATION_GAP` |
| **P4.7** | 30 adapter modules on disk are named by no registry row — unreachable capability, invisible rather than refused | §1.9 |

### P5 — Derivation and binding: 73 of 84 SWE rows do not declare what they need

| ID | problem | evidence |
|---|---|---|
| **P5.1** | 73/84 SWE rows have **no input contract**, so the binder guesses — and guesses a file where a directory is required and vice versa | advanced 10 `WORKTREE_NOT_DIRECTORY`; matrix `edits_path` class |
| **P5.2** | a **2-step DAG** is planned and its steps cannot bind their own inputs | surface `sql_injection`: `CAPABILITY_DAG_RESULT_INVALID`, both steps `MISSING_REQUIRED_ARGUMENTS` |
| **P5.3** | 8 requests stop at `RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP` | §1.2/§1.3 |
| **P5.4** | "Extract the loop in `fn`" never becomes a line region | advanced 38 `REGION_INVALID` |

### P6 — Integrity: what "verified" means in this machine

| ID | problem | evidence |
|---|---|---|
| **P6.1** | **40 adapters** write `output_verified: True` as a literal; **15** write `verified: True` | §1.5 |
| **P6.2** | **14 rows** carry no verification block at all | §1.5 |
| **P6.3** | an adapter that **exits the process** instead of refusing | advanced 48 `CAPABILITY_EXITED_PROCESS:1` |
| **P6.4** | an adapter that reports success and **changes nothing** | advanced 45, 46 `NO_OBSERVED_EFFECT` |
| **P6.5** | a served answer can be the wrong question and nothing objects | advanced 39 |
| **P6.6** | a failure raised outside the adapter's own refusal path yields `STEP_RAISED_OUTCOME_UNKNOWN` | matrix `delete_file` |

### P7 — Self-verification: the repository does not pass its own laws

| ID | problem | evidence |
|---|---|---|
| **P7.1** | 24 red tests in the capability suite on a clean tree | §1.6 |
| **P7.2** | a CI job is red on a test that is red on `main`, and merges proceed anyway | §1.6 |
| **P7.3** | the last full honest suite baseline is 2026-10-17 (380 failures) and nothing re-measures it | §1.6 |
| **P7.4** | the matrix and the advanced census are not in CI | §1.8 |

### P8 — Speed and diagnosis

| ID | problem | evidence |
|---|---|---|
| **P8.1** | 17 of 49 refusals are opaque (`LIVE_CONTROLLER_EXECUTION…`), so each costs a full run to diagnose | §1.3 |
| **P8.2** | no repeated-request cache; six near-identical failures were re-derived | §1.7 |
| **P8.3** | a misfire is expensive: 16 s for a wrong capability, 28.5 s to index the runtime, 3.4 s to *compile* one security-review sentence | §1.7 |
| **P8.4** | selection itself is fine (57–480 ms, 240 ms cold) | §1.7 — *not* a problem |

---

## 3. What changed since V12 (`f333567`) and since V13 (`9f80823`)

Closed or materially improved:

* **S1–S5 magnets** — unchanged in count but the *cause* is now understood and the fix is one family
  table; the counts moved 22/49 (same).
* **S7 / X3 wrong-shape served** — still open (advanced 39).
* **The repair search space** — `DROPPED_OPERAND` landed 2026-10-31 (§P3 preamble), which took the
  surface census `23 → 25` and `fix_failing_test` from 61.9 s FAIL to 6.9 s PASS.
* **A stated test directory now states its tests** — "the tests in `<b>/tests` are failing" bound
  `source_root` to the test folder and spent 46 s searching it; now it derives the owning tree and
  repairs in 3.3 s.
* **The localizer** — a failing run's last executed line is now evidence; `localize_fault` passes.
* **The census is a CI gate** at floor 25 — 0 → 1 workflow.
* **Toolchain lane 1/7 → 3/7** — because the analysers were installed by hand; the capability to
  install them is still missing (P2.9).

Still open from V12, re-measured here: S1–S6, A1–A7, M1–M8, X1–X3, L1, and V2. V1 is now measurable
and shows P2.9 instead of "tools missing".

### 3.1 Reconciliation with the merged V13

V13 is the inventory merged in #6468. It was measured on `9f80823`; this document re-measures the same
instruments on `ecfc9fb`, seven merges later.

| measure | V13 on `9f80823` | V14 on `ecfc9fb` |
|---|---|---|
| ordinary matrix | 17 REAL / 37 refused / median 142 ms | **20 REAL / 34 refused / median 306 ms** |
| advanced census | 2 served / 47 refused | **4 served / 45 refused** (one of the four is wrong: #39) |
| SWE rows declaring `requires` | 43 "chain" / 41 standalone | **40 fully satisfiable / 7 impossible / 37 none** |
| adapter modules with no row | 29 of 167 | **30 of 166** (mine excludes `__init__.py`) |
| surface census (28 sentences) | not reported | **25/28**, gated in CI at floor 25 |
| repeated-request cache | absent | absent |

V13's "43 chain rows" reproduces exactly as *rows with at least one requirement some row provides*.
The sharper split is above: **only 40 are fully satisfiable, and 7 name a requirement that nothing
provides** — so the obstruction V13 identified is real and slightly larger than it reported.

Two V13 inferences this document corrects:

1. **"43 rows can never start because they declare a precondition only another row can produce."** The
   count of rows declaring a precondition is 47, 7 of which are impossible, and — more decisively —
   *none of the 47 would be walked anyway*: the front door has no closure walk (§1.9). The conclusion
   (repair / verify / land are unreachable from a request) stands; the mechanism is two defects, a
   six-string data error and one missing call site, not a missing planner.
2. **"29 adapters on disk have no registry row."** Still true (30 of 166) and it is the *least* urgent
   item of the set: an orphan adapter cannot be selected, so it costs disk and nothing else. It matters
   only after the row it should sit behind is reachable (P4.7).

Numbers of V13's that hold unchanged on `ecfc9fb`: the repo-wide suite is red (its 380-failure
baseline is the last honest one — P7.3), five magnet rows absorb the advanced census (P1), whole
domains are empty (P2), there is no repeated-request cache (P8.2), and a wrong-shape answer is served
(#39, P1.7/P6.5).

---

## 4. What is *not* a problem (do not spend hours here)

* **Honesty.** `FALSE 0`, `DAMAGED 0` across 54 ordinary cases, and all five destructive/ambiguous
  probes refuse. The over-claim class is not where the remaining capability is.
* **Selection latency in the common lanes.** 84–313 ms, 240 ms cold — faster than a human opening the
  file. (The 3.36 s security-review compile is a real outlier, listed as P8.3, not a reason to redesign
  selection.)
* **The Python read/analysis lane.** `find_callers`, `dead_code`, `complexity`, `count_functions`,
  `change_impact`, `mutation_score`, `security_review`, `perf_review` are all REAL at 57–1276 ms.
* **Repair of ordinary single-file bugs.** 5/7, and the two misses are different classes (P3.1/P3.2
  style grammar holes, not bad search).
* **The census gate itself.** It exists, it can fail, and it runs on every change.

---

## 5. The order that buys the most capability per hour

1. **P1 + P5 together** (one week): the five magnets are one family table; the 73 contractless rows are
   one declaration pass. Fixing selection + contracts moves *every* later capability into reach,
   because a capability nobody can select is indistinguishable from one that does not exist.
1b. **P4.5** (an hour): rewrite six `requires` strings to the token the producer publishes, then call
   the existing `plain_goal_bound_grounding` binder from the ordinary route (P4.6). This is the
   cheapest unlock in the document and it lands on the top magnet.
2. **P3.1 and P3.2** (days): two structural families in `_candidate_specs` — a synchronisation idiom and
   a parameterised-query rewrite — each verified by the suite that already runs. This closes 2 of the 3
   surface failures.
3. **P3.3 + P5.2** (days): composition. A two-effect sentence must become a two-step plan whose steps
   receive their own inputs; the DAG executor already exists and already plans the steps.
4. **P2.1–P2.3** (weeks): systems languages, build/packaging, CI. These are the same test-gated patch
   engine pointed at a different language server or a different file type, plus the tree-sitter parser
   that already understands the grammar. Until these exist the machine is a Python specialist, and the
   advanced census will keep reading `4/49`.
5. **P6 + P7** (ongoing, cheap): replace constant `output_verified` with the observation, add the
   verification blocks, and make `main` green — 24 red tests and a red required check cost more
   attention than any single capability.
6. **P4.1**: an *orphan row* report in CI — 118 real rows that no request ever selects is a map of what
   is already built and merely unreachable.
7. **P8.1**: name the 17 opaque failures. A refusal that cannot say what went wrong cannot be fixed.

---

## 6. Reproduction

```bash
# 1.1  28 hardcore sentences, gated at 25
python3 hardcore_swe_surface_probe_20261030.py --jobs 4 --floor 25 --json /tmp/census.json

# 1.2  54 ordinary cases (toolchain lane needs ruff/mypy/bandit/coverage installed)
python3 execution_guard/swe_capability_matrix_v1.py --json > /tmp/matrix.json

# 1.3  49 advanced requests
python3 execution_guard/swe_advanced_probe_v1.py --json /tmp/adv.json

# 1.4 / 1.5  registry composition and integrity
python3 - <<'PY'
from canonical.runtime import live_brain_route_admission_v1 as door
import re, json
reg = dict(door.load_verified_registry())
auto = [k for k in reg if ".auto.v1" in k]
print(len(reg), len(auto), len(reg) - len(auto))
print(sum(1 for v in reg.values() if not (v.get("proposal_bindings") or {})))
print(sum(1 for v in reg.values() if not v.get("verification")))
PY

# 1.9  the declared dependency graph
python3 - <<'PY'
import collections, pathlib
from canonical.runtime import live_brain_route_admission_v1 as door
reg = dict(door.load_verified_registry())
real = {k: v for k, v in reg.items() if ".auto.v1" not in k}
swe = {k: v for k, v in real.items()
       if k.startswith(("python.", "code.", "software.", "test.", "orchestration.", "git."))}
prov = collections.defaultdict(set)
for k, v in real.items():
    for p in (v.get("provides") or []):
        prov[p].add(k)
print("declare requires:", sum(1 for v in swe.values() if v.get("requires")))
print("fully satisfiable:", sum(1 for v in swe.values()
      if v.get("requires") and all(r in prov for r in v["requires"])))
print("impossible:", sum(1 for v in swe.values()
      if v.get("requires") and any(r not in prov for r in v["requires"])))
mods = {p.stem for p in pathlib.Path("canonical/runtime/bound_capabilities").glob("*.py")
        if p.stem != "__init__"}
used = {v.get("adapter_module") for v in reg.values() if v.get("adapter_module")}
print("adapter modules:", len(mods), "orphans:", len(mods - used))
PY

# 1.6  the machine's own laws
PYTHONPATH=. python3 -m unittest discover -s canonical/tests -p "test_*capabilit*.py" -t canonical/tests

# 1.8  which instruments CI runs
grep -rl hardcore_swe_surface_probe_20261030.py .github/workflows | wc -l
grep -rl swe_capability_matrix_v1.py .github/workflows | wc -l
grep -rl swe_advanced_probe_v1.py .github/workflows | wc -l
```

Authority: **NONE**. These are single-machine measurements of one tree at one commit; they are not
independent verification and they carry no credit.
