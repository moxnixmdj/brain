# Hardcore software engineering — the complete problem census (2026-10-30, V9)

**Scope.** One subject: the machine that understands, changes, verifies and ships software.
Documents, PDFs, images, spreadsheets and charts appear here in exactly one role — **wrong
destinations** the router must refuse. The target is the most advanced, fastest and smartest
software engineer available, so every problem is judged by three questions only: does it stop the
machine from doing hard engineering work, from doing it fast, or from telling the truth about what
it did?

**Every number below was measured at HEAD `e8738e9`**, by instruments in the repository:

| instrument | what it answers |
|---|---|
| `execution_guard/swe_request_probe_v1.py` | 28 ordinary advanced sentences |
| `execution_guard/swe_request_probe_v1.py --suite hardcore` | 48 advanced requests, a **fresh tree per case** (git history, `pyproject.toml`, Makefile, JS package) |
| `execution_guard/swe_capability_matrix_v1.py` | 54 designed requests, REAL / FALSE / REFUSED / DAMAGED |
| registry census | what the machine claims, and whether a sentence can reach it |

The matrix now prints its own **preconditions** (HEAD, toolchain, leftover scratch) before its
score, because the same code scored 17 with `ruff`/`mypy`/`bandit`/`coverage` present and 12
without them, and those two numbers are not comparable.

---

## 1. Scoreboard

| measurement | value |
|---|---|
| registry rows / **routable** | 419 / **125** |
| software-engineering rows | **63** (`python` 46, `software` 12, `code` 4, `shell` 1) |
| SWE rows that declare **no inputs** (unreachable by any sentence) | **18** |
| SWE rows needing 6–9 inputs | **8** |
| rows that structurally edit code | **4** (rename symbol, rename parameter, extract function, cross-file choreograph) |
| rows for build / dependency / CI / language-server work | **0** |
| 54-case matrix | **17 REAL · 0 FALSE · 37 REFUSED · 0 DAMAGED**, median ~100 ms |
| 28-sentence probe | **6 of 28 (21 %)**, p50 60 ms, 0 trees damaged |
| 48-request hardcore probe | **9 of 48 (19 %)**, p50 87 ms, **0 refusals that dirtied a tree** |
| what is left after 9 answered | 12 compilation gaps · 8 wrong-row refusals · 6 wrong-destination raises · 6 capability refusals · rest composed/verifier refusals |

**What it actually does, measured:** reads a Python tree (symbols, callers, change impact), runs a
suite or a Makefile, typechecks with mypy, reviews security with bandit, renames a symbol inside one
file, extracts one stated statement, repairs one bug when the failing test is named, and — since
`e8738e9` — answers **three git questions** (`status`, `log`, `diff`) through the verifier that
already existed.

---

## 2. The four wrong destinations (measured this round)

These are worth more than any summary, because each one is a *capability from another domain*
answering a software request:

| request | what answered it | what it said |
|---|---|---|
| `Add the dependency requests to pyproject.toml.` | **`finance.saccr.credit.addon.v1`** | `SACCR_INPUT_JSON_INVALID` |
| `Build the package into a wheel.` | **`archive.tar_gz.create_from_manifest`** | `MANIFEST_INPUT_REQUIRED` |
| `Write a unit test for the function mul.` | **`python.tests.audit.unittest`** (an auditor) | `TEST_AUDIT_EMPTY` |
| `Profile the function total and tell me where the time goes.` | **`chart.raster.axis_title_unit_binding.v1`** | live-controller failure |

Four domains — finance, archives, test auditing, chart reading — each matched on a word ("add",
"build", "test", "profile"). The correct rows for the first three **exist**; the fourth does not
exist at all.

---

## 3. Reach — the sentence does not arrive at the capability

**A1 · Lexical ranking sends requests to another domain** (§2, 4 measured). Existing mechanism:
`capability_selection_retrieval_v1` with its decisive-margin rule. Missing wire: the margin rule
admits only when one row dominates; nothing encodes **the verb–object family** ("add a dependency"
is package management, not "add"). Cost: 4 hardcore requests, 6 more in the matrix.

**A2 · Selection does not follow the stated command line** — *closed for read commands* (`e8738e9`:
a settled argv now re-selects `shell.command.run` before the gate). Still open for **write**
commands: `git commit`, `git branch`, `ruff format` run but their promise is unverified.

**A3 · A stated answer is refused because the row is the wrong KIND of row** — 8 of 48
(`STATED_ANSWER_NOT_PROVIDED`, `ROUTE_ADMISSION_REJECTED`). Example: `Add type hints to every
function and make mypy pass` selects `software.review.gate.composer.v1` and is refused
`R3_WEAK_EVIDENCE` — the right refusal for the wrong reason.

**A4 · 18 routable SWE rows take no inputs** — every `*supercomposer*`, `python.pr.land.composer.v1`,
`python.test.pipeline.verifier.v1`, `python.patch.review.supercomposer.v1`,
`software.hardcore.swe.supercomposer`. They are verified, advertised, unreachable.

**A5 · 8 rows want 6–9 inputs and nothing derives them** (`pr_realize`, `issue_to_pr.orchestrate`,
`fault.localize.dynamic.dataflow`, `patch.search.test_guided`).

**A6 · 2 routable rows point at a module that does not exist** (`knowledge.consistency.assess`,
`knowledge.json.fetch.external`).

**A7 · A raw adapter error can still reach stdout** — the hardcore probe captured
`{"error": "EDIT_PLAN_INPUT_INVALID", "message": "edits_path unreadable JSON"}` before its table:
a stale spool artifact bound as this request's input.

---

## 4. The capability ladder, rung by rung

| rung | state | what is missing | what already exists |
|---|---|---|---|
| **R1 Read** | ◐ | explain a module (compilation gap); dataflow trace (step raised); "who changed this line" (refused by design) | symbol index, callers, change impact, mypy, bandit, **git status/log/diff/shown/blame verifiers** |
| **R2 Change one thing** | ◐ | inline, move, split, dedupe, constants, docstrings, repo-wide rename (`PROMISED_SOURCE_CHANGE_NOT_APPLIED`) | rename symbol, rename parameter, extract function, one-bug repair (2 measured source edits today) |
| **R3 Change many things** | ✗ | `edits_path` derivation — measured: the correct 4-step chain is *found* for `issue to PR` and dies on `SystemExit:1` at `crossfile_edit.choreograph` because nothing produces its edit plan | `python.source.crossfile_edit.choreograph.v1` (3 slots), `software.repair.choreograph.crossfile.v1` |
| **R4 Write tests** | ✗ | the writer request routes to an **auditor** (`tests.audit.unittest`); the generator row `python.tests.generate.scaffold.v1` is never selected; regression-test search dies in the live controller | 2 scaffold rows, `patch.search.test_guided.ast.v1`, mutation and coverage gates |
| **R5 Build & depend** | ✗ | wheel → a **tarball** row; dependency add → a **finance** row; upgrade → composed raise; CI → `kernel.orchestrate` | `make`/`python -m build` installed; `execution.pipeline.8stage.v1` exists with no inputs |
| **R6 Version control** | ◐ | commit, branch, bisect, revert, changelog (5 of 8) | read commands (3 of 8, closed today), `_post_git` postconditions written and tested |
| **R7 Debug** | ✗ | why-did-this-fail (gap), trace (raised), debugger frames, bisect | `fault.localize.dynamic.dataflow.v1` (8 inputs), `fault.provenance.*`, root-cause refusal now honest |
| **R8 Review & ship** | ◐ | review needs a green tree; no PR, changelog, release | security/type/static review, `pr.land.composer`, `repo.pr_realize` (unreachable) |
| **R9 Performance** | ✗ | profile → **chart row**; optimise → gap | `review.diff_perf_gate.v1` (9 inputs), `cProfile`/`timeit` installed |
| **R10 Polyglot** | ✗ | JS suite refused, JS lint → a *Python* triage row, port → gap | tree-sitter multi-language parser (0 inputs), `node --test` installed |

---

## 5. Truth — the machine must not certify what it did not do

- **T1** A content request deleted the file it was asked to clean — **closed** (deletion is not the
  object of "remove … from X").
- **T2** A chain certified "done" with its only step `UNRESOLVED` — **closed** (the last step's
  verdict is the chain's verdict).
- **T3** Requests died on their own spool scratch — **closed** for writes, **open** for *reads* (A7).
- **T4** A "why" question is certified by a measurement (`why is the suite red` → `pass=True` from
  the acceptance measurer) — **open**.
- **T5** Measurement refuses on a red tree (`CAPABILITY_REFUSED_SUITE_RED`) — open, and it is
  exactly when a broken repo needs its coverage known.
- **T6** The referee is state- and toolchain-sensitive — **partially closed**: the matrix now prints
  HEAD, toolchain presence, unmeasurable lanes and leftover scratch before the score.
- **T7** 17 red test ids in the command-reading modules at HEAD (proved identical without this
  branch's changes), no CI gate.

---

## 6. Speed

| | |
|---|---|
| refusals and reads | p50 60–87 ms |
| answers that do work | 60 ms (suite) · 95 ms (impact) · 842 ms (typecheck) · 850–1 370 ms (repair) · **19 s → 2.4 s** (repo-wide caller map, cached) |
| reuse between requests | none — 419 rows reloaded, inputs re-derived, plans rebuilt |
| parallelism | none — independent steps are serial |
| long horizon | no plan, no checkpoint, no resume |

The bottleneck is capability, not speed: when the machine can do something it answers in
milliseconds.

---

## 7. Learning

39 of 48 hardcore requests refuse, identically, every time. Nothing records that a wheel builder, a
dependency manager, a test author, a debugger and a profiler are missing — and nothing ranks them.

---

## 8. The mapping the founder asked for: every problem already has a mechanism

| problem | mechanism that already exists (in this repo) | the missing wire |
|---|---|---|
| git read questions | `raw_goal_trace_acceptance_v1._READ_ONLY_SUBCOMMANDS` (verifies by re-running) | **done in `e8738e9`** |
| git write questions | `_post_git` (HEAD subject, clean tree, branch resolves, HEAD on branch) | a commit message the *world* supplies + acceptance allowance for derived tokens |
| file writes, moves, deletes | `_MUTATING_POSTCONDITIONS` (rm, mv, cp, tee, gzip, chmod, sort, `ruff format`, sed) | `git` rows; a formatter row that says "already formatted" instead of NO_OBSERVED_EFFECT |
| any stated command | `shell.command_run` + `_inspect_shell_command_run` (re-run and compare) | selection for write commands |
| multi-file editing | `crossfile_edit.choreograph` + `software.repair.choreograph.crossfile` | derive `edits_path` from the stated change (the typed planner already derives 8–9 slots for rename/extract) |
| test authoring | `tests.generate.scaffold.v1`, `refactor.test_scaffold.fusion.v1`, `patch.search.test_guided.ast.v1` | one derivation each; the writer must stop routing to the *auditor* |
| refactoring beyond rename | `python_refactor_*` adapters + tree-sitter kerns | inline / move / split rows over the same AST editor |
| build & deps | `make`, `python -m build`, `pip`, `npm` installed; `execution.pipeline.8stage.v1` exists | rows (no row declares a wheel or a dependency) |
| debugging | `fault.localize.dynamic.dataflow`, `fault.provenance.*`; `git bisect` is 4 argv | derivations + a bisect row; the controller fix for test-guided search |
| performance | `review.diff_perf_gate`, `cProfile`, `timeit`, the coverage runner | a profiling row (currently a **chart** row answers) |
| polyglot | `code.multilanguage.parse.tree_sitter.v1`, `node --test`, `npm` | language binding + rows; the parser needs inputs |
| long-horizon work | 18 no-input supercomposers, the DAG planner, F13 spooling | any declaration at all |
| ranking | `capability_selection_retrieval_v1` decisive margin, F15/F18 rules | verb–object family constraint |

**Read that table as the plan:** almost nothing in this list needs new machinery. It needs *wires* —
one derivation, one row, one binder rule, one ranking constraint at a time — and each wire is
measured the moment it is made.

---

## 9. Fastest correct order

1. **`edits_path` derivation** (R3) — the highest-value single wire: it turns the found-but-dead
   cross-file chain into multi-file editing, and it is what `issue to PR` is blocked on.
2. **Test authoring** (R4) — stop the writer routing to the auditor; one derivation each for the two
   scaffold rows; fix the test-guided controller.
3. **git commit/branch** (R6) — postconditions exist; supply the message from `git status` names and
   allow the derivation in the acceptance gate.
4. **Build & dependency rows** (R5) — wheel, add/upgrade dependency: installed binaries, zero new
   machinery.
5. **Refactor rows** (R2) — inline, move, split on the existing AST editor.
6. **Ranking by verb–object family** (A1) — kills the finance/tarball/chart destinations.
7. Derivations for the **18 no-input rows** (A4) — the highest ceiling.
8. **Debug + perf** (R7, R9) — bisect and profiling over installed binaries.
9. **Polyglot** (R10) — tree-sitter + `node --test`.
10. **Registry reuse, plans, checkpoints** (speed, long horizon).

---

## 10. Reproduction

```bash
cd /home/user/brain
python3 execution_guard/swe_request_probe_v1.py                     # 28 sentences -> 6 answered
python3 execution_guard/swe_request_probe_v1.py --suite hardcore    # 48 requests  -> 9 answered
python3 execution_guard/swe_capability_matrix_v1.py                 # 54 cases     -> 17/0/37/0
                                                                    # (prints its preconditions first)
python3 canonical/runtime/verify_brain_unified_model_v1.py          # 33/33
python3 -m pytest -q canonical/tests/test_a_question_about_the_repository_is_answered_by_the_repository_v1.py \
                    canonical/tests/test_a_content_request_never_deletes_the_file_v1.py \
                    canonical/tests/test_a_chain_that_came_back_unresolved_is_not_a_pass_v1.py \
                    canonical/tests/test_a_second_request_does_not_die_on_the_first_requests_scratch_v1.py
```

*Authority: NONE — sandbox measurement, not independent verification.*

---

## 11. Addendum, measured after the `edits_path` wire (branch `arena/47739ce8-brain`)

Item 1 of §9 is done.  `declared_input_derivation_v1` now proves the cross-file edit set — the stated
rename pair, the single stated directory as `source_root`, and the ONE module under it that really
defines the symbol (`ast`, module scope; zero or several defining modules derive nothing) — and writes
it content-addressed to `canonical/astra_runtime/tmp/derived/edits_<sha16>.json`.

Three defects had to be fixed before the sentence could be answered, each found by measuring, not by
reading:

1. **The op's `module` must be the repository-relative path**, not the path under `source_root`: the
   consumer compares it against the symbol index's own `path` column.  First derivation emitted
   `pkg/calc.py`, the plan refused its only op `MODULE_NOT_IN_INDEX:pkg/calc.py`.
2. **A question is not a writer's job — and not a promise.**  "Which files must change to rename…"
   was refused `STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER` for the planner whose own registry
   row says *"Plans, does not apply"*; the exemption is read from that declaration (exactly one row in
   the registry matches), never from an id.  The byte gate then refused `PROMISED_SOURCE_UNCHANGED`,
   demanding the tree move for a question about moving it.
3. **A plan that planned nothing and refused its only op is not an answer**, whatever
   `output_verified` says — `TOOL_PLANNED_NOTHING_AND_REFUSED` is now a truth-check error.  Before
   this, the refused plan certified PASS with `affected_file_count: 0`.

An IMPERATIVE rename keeps the old reading: "Rename the symbol `mul` to `multiply` in <dir>" still
fails `PROMISED_SOURCE_CHANGE_NOT_APPLIED` when only a plan came back, because the sentence demands
the change, not the plan.  Wiring that to `python.refactor.rename_symbol.v1` (which does write, and
whose `module`+`qualname`+`new_symbol` are derivable from the same evidence) is §9 item 5.

| instrument | before | after |
|---|---|---|
| `swe_request_probe_v1.py --suite hardcore` | 9 of 48 | **10 of 49** (`refactor/rename_plan` added and answered) |
| `swe_request_probe_v1.py` | 6 of 28 | 6 of 28 (no regression) |
| `swe_capability_matrix_v1.py` | 17/0/37/0 | 17/0/37/0 (no regression) |
| `verify_brain_unified_model_v1.py` | 33/33 | 33/33 |
| new pinning tests | — | 7, `canonical/tests/test_a_rename_question_is_answered_by_a_plan_v1.py` |

The answer is a real one, not a certificate: for the fixture tree the plan reports
`planned_op_count 1`, `refused_op_count 0`, `affected_file_count 2`, `ambiguous_site_count 0`, and its
sites are `DEFINITION pkg/calc.py:1`, `IMPORT_SITE pkg/util.py`, `REFERENCE pkg/util.py:5`.

*Authority: NONE — sandbox measurement, not independent verification.*
