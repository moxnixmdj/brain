# Hardcore Software-Engineering Problem Inventory — 2026-10-30 V8

**Scope (the founder's frame, applied literally).** One subject: the machine that writes, changes,
verifies and reasons about *software*. Document editing, PDFs, images, archives, spreadsheets and
every other non-code registry row are **out of scope except as misroute destinations** — when one of
them answers a code question, that is a defect recorded here, not a capability to improve. The
target is a software engineer that is *more advanced, faster and smarter* than the alternative, so
every problem below is judged by exactly three questions: **does it stop the machine from doing hard
engineering work, from doing it fast, or from telling the truth about what it did?**

Every number is measured in this repository on this tree, today. Nothing here is a projection.

---

## 1. Scoreboard

| measurement | value | how |
|---|---|---|
| capability matrix — 53 designed SWE requests | **REAL 16 / FALSE 0 / REFUSED 37 / DAMAGED 0** | `execution_guard/swe_capability_matrix_v1.py` |
| fresh probe — 60 advanced SWE sentences, one ordinary tree | **13 answered (21.7 %) / 47 refused** | §5 harness |
| probe: requests whose selected row was a **non-SWE domain** | **2** (`math.numeric_expression.sympy`, `finance.saccr.credit.addon.v1`) | same |
| probe: requests that bound **no capability at all** | **14 of 60** | same |
| probe latency | **p50 72 ms · p90 618 ms · max 1666 ms** | same |
| "find every caller of `build_plan` in `canonical/runtime`" | **18.1 s / 18.6 s**, uncached, two runs | direct |
| registry rows / software-engineering rows | **419 / 62** (`python.*` 46, `software.*` 12, `code.*` 4) | `load_verified_registry()` |
| rows for any non-Python language | **≈0** (Rust 1, Java 3, C/C++ 0–1, Go 0, Ruby 0; JS/TS = one `typescript` keyword) | keyword census |
| sampled test modules red on the base commit (`efe0877`) | **4 of 40 (10 %)** | clean worktree, every 6th module |
| standing test batch on this branch | **84 tests green** (8 modules) | `unittest` |
| unified model verifier | **33/33 PASS** | `verify_brain_unified_model_v1.py` |

Matrix by family: `repair 4/7 · refactor 1/7 · tests 0/3 · analysis 7/12 · toolchain 3/7 · git 0/5 · feature 0/7 · honesty 1/5`.

**Read it as a spec:** a Python code *reader* with four real measurement gates, one verified repair,
one verified rename, and no write lane for anything else. The `FALSE 0` is new today and it is the
most important number here: every remaining PASS is now backed by the effect the sentence stated.

---

## 2. Where the 47 probe refusals actually come from

| refusal class | n | what it means | is it honest? |
|---|---|---|---|
| `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | 16 | a row was selected and could not bind the sentence's inputs | yes, but **it names nothing** |
| `FAIL__RAW_GOAL_COMPILATION_GAP` | 11 | nothing in the registry could be compiled at all | yes, but undiagnosable |
| `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` | 6 | the row cannot supply the stated effect | yes, and it is now specific |
| `FAIL_CLOSED__NO_OBSERVED_EFFECT` | 4 | it ran and changed nothing | yes |
| `FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED` | 3 | a change was promised, none observed | yes |
| `FAIL__LIVE_CONTROLLER_EXECUTION` | 3 | the second executor failed | partially — see P5 |
| `FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT` | 2 | a measurement ran, the threshold failed | yes, but the number is buried (P6) |
| `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` | 1 | a composed step raised; nobody knows the world | **no** (P4) |
| `FAIL_CLOSED__CAPABILITY_RETURNED_A_VERDICT` | 1 | ran, did not certify | yes |

The two largest buckets (27 of 47) are the two that tell the user **nothing**. That is itself the
first problem: the machine is honest and silent at the same time.

---

## 3. The problems, ranked

**P1 — The router cannot say "I do not have this".** 419 rows, 62 of them SWE; charts, docx, images,
finance, sqlite and maths compete on keyword overlap and sometimes win: `Extract the expression a + b
into a new function` → `math.numeric_expression.sympy`; `Find the definition of `add`` →
`finance.saccr.credit.addon.v1`; `Add logging/retries` → `python.software.request.semantic_behavior.compile.v1`
(a meta-row that compiles requests, not code). *Fix:* effect-first shortlisting (partly in place),
plus a named `MISSING_CAPABILITY:<effect>` refusal and an acquisition queue fed by it. **Size: small–medium.**

**P2 — 16 of 60 requests die at the binder, silently.** `ROUTE_ADMISSION_REJECTED` is the single
largest failure mode: the family was right, the sentence's inputs did not bind, and the record says
nothing about which slot was missing. *Fix:* `UNSTATED_INPUT:<slot>` with the fragment it needed
(this is P1's twin; one change closes both). **Size: small.**

**P3 — 14 of 60 requests bind no capability at all.** Whole families: git (6/6 refused: diff, blame,
bisect, commit, branch, history), feature work (cli flag, logging, retries, new parameter, issue,
cross-file), test authoring, formatting, complexity, TODO scan, API surface. For most of them the tool
is already installed (`git`, `ruff`, `mypy`, `coverage`, `pytest`) — the missing thing is a
declaration and a binder, not an implementation. **Size: small per row, large in aggregate.**

**P4 — The write lane is one-and-a-half capabilities wide.** 6/24 write requests answered (repair 4/7,
refactor 1/7, tests 0/3, feature 0/7). Today's probe adds detail: rename-symbol and rename-parameter
pass with verification; extract-function, move-symbol, type hints, format, dedupe, cli flag, logging,
retries, new parameter and test authoring all refuse. There is no generic "compute an AST edit →
verify → roll back on red" lane driven by intent. **Size: large — the single biggest capability gain.**

**P5 — Composition is a fallback that swallows the failure.** `STEP_RAISED_OUTCOME_UNKNOWN` is neither
an answer nor a diagnosis; measured today for "write a unit test for the function `mul`".
**Size: small (extend the supersession rule that already exists), high diagnostic value.**

**P6 — A second executor can overwrite the first one's answer.** Fixed at the single-capability path
today (mutation gate's `BASE_WORLD_RED` is now reported in its own words); the controller and composed
paths can still do it. **Size: small.**

**P7 — Measurement is reported as a refusal.** Coverage (745 ms) and mutation (1666 ms) both ran and
produced numbers; both ended `REVIEW_RAN_AND_RETURNED_A_VERDICT` with `pass: False`, because
`expect: gate == PASS` conflates "did it measure" with "does the code meet the bar". *Fix:* two
expectations — `measured` and `certified` — in the registry contract. **Size: small–medium.**

**P8 — Python-only.** 62 SWE rows, non-Python languages effectively absent. A JS lint request is now
honestly refused (it used to PASS on a parse — see §4); a JS rename, test run or impact analysis has
nowhere to go. *Fix:* one tree-sitter layer behind callers / definitions / impact / rename, bound by a
declared `language` slot; the repo already vendors tree-sitter. **Size: large.**

**P9 — Nothing is cached, so "insanely fast" is false at repository scale.** 18.1 s and 18.6 s for one
directory-scale caller question, twice in the same process; the change-impact row already builds an
index and deletes it after every call. *Fix:* one content-addressed index (file sha → symbols, imports,
call edges), delta-updated. **Size: medium; the difference between a tool and an engineer.**

**P10 — The referee is sick.** 4 of 40 sampled modules are red at the base commit (10 %);
`test_swe_typed_plan_v1` was 5/17 red at HEAD and is green now. A suite that is 10 % red cannot
certify anything. **Size: small to wire a whole-suite gate, medium to burn down.**

**P11 — Refusals are not diagnosable** (see §2): 27 of 47 failures say "rejected" or "compilation
gap". Fixing this is the cheapest improvement on the board and it makes every other fix measurable.
**Size: small.**

**P12 — A reflection answered as if it were a parse.** `Lint the javascript file <f>` was certified
PASS by `code.multilanguage.parse.tree_sitter.v1` — a syntax tree was written, nothing was linted.
Fixed today: lint / format / type-check are now stated effects with their own declaration surface.
The generalisation is the real problem: **an accepted artifact was verified as a file write, not as
an answer to the question.** Every fixed case in §4 is an instance. **Size: ongoing — one row per
effect.**

**P13 — No long-horizon work.** Every measurement is a single request; there is no capability for
"make the build green", "port this module", "upgrade this dependency across the repo", "cut a
release" — the multi-hour work that is most of an advanced engineer's day. Controller checkpoints
exist as execution internals, not as resumable tasks with a plan, evidence and a stop condition.
**Size: large; the natural sequel to P4.**

**P14 — Nothing learns from a refusal.** `solve_or_learn` exists and memory files are written, but the
same families refuse round after round (git 0/5, tests 0/3, feature 0/7). A refusal that does not
become an acquisition entry is a refusal the machine will repeat. **Size: small (P1 + P11 + a writer).**

---

## 4. What changed today (all measured, all with tests)

| # | defect measured before | now |
|---|---|---|
| 1 | "which tests must I run after changing `<f>`" → `python.repository.acceptance.measure.v1`, PASS over a repository run that never looked at the change | routed to `python.source.change_impact.testselect.v1`; PASS only with a non-empty `selected_tests` |
| 2 | same question, test file beside the module → `selected_tests: []` **and PASS** (a green light to skip the tests that cover a change) | the anchor directory is a test root; an empty selection is `FAIL_CLOSED__ANSWER_EMPTY__NO_TESTS_SELECTED`, final |
| 3 | ``Rename the symbol `mul` to `multiply` `` → read-only symbol index, refusal read as a verdict | quotes are identifiers; a refusal that measured the tree **unchanged** may be superseded by a decisive plan; the rename runs and verifies |
| 4 | a rename with no test to verify it rewrote the file **and then** refused | `PASS_BLIND_DRY_RUN`: patch computed and syntax-checked, **nothing written** |
| 5 | refactors handed any test beside the source, including a test of a different module (correct rename rolled back as "red") | `run_tests` only from a test that mentions the module, relative to the directory the capability runs in |
| 6 | mutation gate refused `BASE_WORLD_RED`; caller told `BOUND_CAPABILITY_SOURCE_UNSUPPORTED:runtime` | structured refusals parsed on the single-capability path, final, quoted verbatim |
| 7 | "rerun 3× … is it flaky" and "attach a debugger … show the frame" → PASS via a test-selection **index** | `STATED_FLAKY_VERDICT_NOT_PROVIDED_BY_CAPABILITY`, `STATED_DEBUGGER_FRAME_NOT_PROVIDED_BY_CAPABILITY` |
| 8 | "run the test suite for `<T>`" → PASS via the same index, nothing executed | `STATED_TEST_RUN_NOT_EXECUTED_BY_CAPABILITY`; now reaches `python.repository.acceptance.measure.v1`, which runs |
| 9 | "lint the javascript file" → PASS via a **parser** | lint/format/type-check are stated effects; a language with no linter row refuses by name |
| 10 | `Repair <X> so that <T> passes, and save the report to <R>` → **PASS with X byte-identical and its own test red** (the last FALSE row) | the stated report no longer licenses an unrepaired source: `promised_source_change_errors` refuses any file that is the object of the repair verb (`PROMISED_SOURCE_UNCHANGED:<X>`) |
| 11 | "repair X so its tests pass" on a tree where they already pass → `FAIL__LIVE_CONTROLLER_EXECUTION` (`RepairLoopError:BASELINE_ALREADY_PASSES`) | `PASS__REQUESTED_STATE_ALREADY_HOLDS`: `already_satisfied: true`, `edited: false`, baseline evidence carried; exempt from the byte-change and observation gates (the baseline run *is* the observation) |
| 12 | `test_swe_typed_plan_v1` red at HEAD (5/17) | green (17/17): the repair family's effect token is `repair`, so a no-op diff row cannot bind a repair sentence |

Evidence: `canonical/tests/test_the_answer_must_be_the_effect_that_was_stated_v1.py` (13 tests),
`canonical/tests/test_swe_typed_plan_v1.py` (17), `canonical/tests/test_a_refused_request_leaves_the_tree_alone_v1.py` (5),
plus the standing batch: **84 tests green**. Matrix `FALSE 1 → 0`. Model **33/33**. `DRIFT_GUARD_PASS`.
`LOAD_BEARING_ADMISSION_PASS`.

---

## 5. The probe (reproducible)

Sixty sentences over one ordinary tree (`canonical/astra_runtime/tmp/probe8`: a Python package with a
green suite, a benchmark file, a JS package, a broken-module fixture) covering repair, refactor,
analysis, measurement, tests, git, feature work, polyglot and honesty. Each case records the status,
the selected capability, the latency, whether the destination was a non-SWE domain, and whether the
request was answered. Every case is a `door.solve({...})` call; nothing is mocked.

Answering today (13): `repair/verb_first`, `refactor/rename_sym`, `refactor/rename_par`,
`analysis/callers`, `analysis/impact`, `analysis/count`, `analysis/imports`, `measure/security`,
`measure/perf`, `measure/lint`, `measure/typecheck`, `tests/run_suite`, `tests/run_file`.

Refusing today, by family: repair (bare / bug-report / no-test / two-modules / unparseable / test-file),
refactor (extract, move, hints, format, dedupe), analysis (defs, dead code, complexity, explain,
explain-code, API surface, coupling, TODO scan, hotspots), measurement (coverage, mutation,
complexity gate), tests (write unit, add case, flaky, debugger, from docstrings), git (6 of 6),
feature (6 of 6), polyglot (3 of 4), honesty (3 of 3).

---

## 6. Order to fix (each step makes the next cheaper)

1. **P11 + P1 + P2 + P14** — named refusals (`MISSING_CAPABILITY`, `UNSTATED_INPUT`) feeding the
   acquisition queue. Converts 27 of today's 47 refusals into work items and shrinks this document by
   itself.
2. **P7** — measurement vs certification (three refusals per tree become answers; pure contract work).
3. **P5 + P6** — no executor may swallow another's answer.
4. **P3** — the cheap families over tools already installed (git writes, format, type hints, test
   authoring, lockfile), one declaration and one binder each.
5. **P4** — the generic intent → AST edit → verify → roll-back lane (the biggest gain).
6. **P9** — one shared, cached index (makes the speed claim true at repository scale).
7. **P8** — tree-sitter behind callers / definitions / impact / rename, bound by language.
8. **P10 + P13** — a green referee and multi-hour resumable tasks: the two that turn a tool into an
   engineer.

---

## 7. Reproduction

```bash
cd /home/user/brain
python3 execution_guard/swe_capability_matrix_v1.py                # 53 cases: 16 / 0 / 37 / 0
python3 -m unittest canonical.tests.test_the_answer_must_be_the_effect_that_was_stated_v1   # 13
python3 -m unittest canonical.tests.test_swe_typed_plan_v1                                  # 17
python3 -m unittest canonical.tests.test_a_refused_request_leaves_the_tree_alone_v1          # 5
python3 canonical/runtime/verify_brain_unified_model_v1.py                                  # 33/33
python3 canonical/runtime/enforce_goal_hierarchy.py --base e2d7981d15809e130759a621687ee77e91c1236b
python3 execution_guard/enforce_load_bearing_primary_pr.py --base e2d7981d15809e130759a621687ee77e91c1236b --head HEAD
```

---

## 8. One sentence

The machine is now an **honest** Python reader — zero fabricated PASSes across 53 designed cases and
60 fresh sentences — with four real measurement gates and two verified write paths; **the hard part of
software engineering, changing code it did not write across files and languages, quickly, and knowing
when it is already done, is still out of reach**, and for the first time the distance is measured per
capability instead of guessed.

*Authority: NONE — sandbox measurement, not independent verification.*
