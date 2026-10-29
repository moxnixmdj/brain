# Hardcore Software-Engineering Problem Inventory — 2026-10-30 V9

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

| measurement | V8 | **V9 (now)** | how |
|---|---|---|---|
| capability matrix — designed SWE requests | 53 cases · REAL 16 / FALSE 0 / REFUSED 37 / DAMAGED 0 | **54 cases · REAL 17 / FALSE 0 / REFUSED 37 / DAMAGED 0** | `execution_guard/swe_capability_matrix_v1.py` |
| fresh probe — advanced SWE sentences, one ordinary tree | 60 sentences · 13 answered (21.7 %) | **61 sentences · 14 answered (23.0 %)** | §5 harness |
| probe: selected row was a **non-SWE domain** | 2 | **2** (`math.numeric_expression.sympy`, `finance.saccr.credit.addon.v1`) | same |
| probe: bound **no capability at all** | 14 | **14** | same |
| probe latency | p50 72 · p90 618 · max 1666 ms | **p50 72 · p90 470 · max 1182 ms** | same |
| registry rows that exist but **no sentence can bind** | unknown, ≥1 | **1 measured and closed** (`python.refactor.extract_function.v1`); audit method in §3 | direct |
| standing test batch | 84 green (8 modules) | **82 green (10 modules)** — different modules, includes the two new ones | `pytest` |
| unified model verifier | 33/33 PASS | **33/33 PASS** | `verify_brain_unified_model_v1.py` |
| fabricated PASSes found this round | — | **1** (report written over its own subject), closed | direct |

Matrix by family: `repair 4/7 · refactor 2/8 · tests 0/3 · analysis 7/12 · toolchain 3/7 · git 0/5 ·
feature 0/7 · honesty 1/5`.

**Read it as a spec:** a Python code *reader* with four real measurement gates, one verified repair,
one verified rename and — new — one verified statement extraction, and still no write lane for
anything else. `FALSE 0` and `DAMAGED 0` hold after the round that found a pass whose file had been
replaced by the report about it.

---

## 2. Where the refusals come from (61-sentence probe, fresh tree)

| refusal class | n | what it means | is it honest? |
|---|---|---|---|
| `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | 17 | a row was selected and could not bind the sentence's inputs | yes, and it now names the slot when its binder named one |
| `FAIL__RAW_GOAL_COMPILATION_GAP` | 11 | nothing in the registry could be compiled at all | yes, but undiagnosable (P1) |
| `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` | 5 | the row cannot supply the stated effect | yes |
| `FAIL_CLOSED__NO_OBSERVED_EFFECT` | 4 | it ran and changed nothing | yes |
| `FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED` | 3 | a change was promised, none observed — **this now includes the unparseable-source repair that used to "pass"** | yes |
| `FAIL__LIVE_CONTROLLER_EXECUTION` | 3 | the second executor failed | partially (P5) |
| `FAIL_CLOSED__CAPABILITY_REFUSED_SYNTAX_ERROR_IN_FILE` | 2 | the capability refused on a real syntax error | yes |
| `PASS__REQUESTED_STATE_ALREADY_HOLDS` | 1 | the request was already satisfied | yes |
| `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED` | 1 | one composed request verified end to end | yes |
| `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` | 1 | a composed step raised; nobody knows the world | **no** (P5) |
| `FAIL_CLOSED__CAPABILITY_RETURNED_A_VERDICT` | 1 | ran, did not certify | yes |

Answered (14): `repair/verb_first`, `repair/bare`, `refactor/rename_sym`, `refactor/rename_par`,
`analysis/callers`, `analysis/impact`, `analysis/count`, `analysis/imports`, `measure/security`,
`measure/coverage`, `measure/mutation`, `measure/perf`, `measure/lint`, `measure/typecheck`,
`tests/run_suite`, `tests/run_file`. The first run of this round answered 17 of 61 — and one of those
17 was the fabricated PASS closed in §3.3, which is why the probe is re-run after every fix and why
P15 matters.

---

## 3. What changed this round — three defects, each one hidden by the other

### 3.1 A registry row nobody could reach (P2, closed for one row)

`python.refactor.extract_function.v1` has been in the registry since the refactor round. Its adapter
lifts a **statement block** and it declares nine inputs, four of which describe one region of one file:

```
module, qualname, start_line, end_line, new_name, source_root, run_tests, output_path, timeout_s
```

No sentence could bind it. Every attempt ended `BINDING_REFUSED:end_line:not_stated` — correct,
permanent, and silent. Three separate links were broken, and each one alone looked like an ordinary
refusal:

1. `extract` was not in the SWE verb set, so the derivation **never ran** and the binder kept asking
   for a slot the sentence had already stated in a different shape;
2. the typed plan had **no extract family**, so the door answered `NO_DECISIVE_TYPED_PLAN` before
   admission was ever consulted;
3. the derivation guard required the **full** contracted slot set, so a shadow contract that still
   carried one of the slots derived nothing at all.

Now one rule reads the statement the sentence quotes out of the stated file's **own AST** (normalized
`ast.get_source_segment` match) and binds `module`, `qualname`, `start_line`, `end_line`, `new_name`,
plus the derived `source_root` and `run_tests`:

```
"Extract the statement `total = a + b` into a new function named sum2 in <pkg>/calc.py."
   -> qualname add · start_line 2 · end_line 2 · new_name sum2 · module calc.py
   -> PASS in 169 ms; calc.py gains `def sum2(a, b)` and `add` now calls it; `mul` survives
```

Boundaries held, measured with the file's md5 before and after: a quoted **sub-expression**
(`Extract the expression \`a + b\` …`) binds nothing, a statement **absent** from the file binds
nothing, and a **nameless** function binds nothing. In all three the tree is byte-identical.

### 3.2 A refusal that had the answer and did not say it (P11, closed for one path)

`live_brain_route_admission_v1` has written `typed_binding_reason` since the fallthrough round —
`BINDING_REFUSED:edits_path:0_type_compatible_existing_files_named` — and **nothing ever read it**.
The caller got `:not_admitted:R3_WEAK_EVIDENCE`, a statement about evidence, when the machine knew the
capability wanted an edits file. Now:

```
"Refactor <pkg>/calc.py."
  before: crossfile_edit.choreograph.v1:not_admitted:R3_WEAK_EVIDENCE
  now   : crossfile_edit.choreograph.v1:contract_not_stated:edits_path:0_type_compatible_existing_files_named
```

The verdict is unchanged — still refused — and the slot is named by the capability's own binder.

### 3.3 A PASS whose file had been replaced by the report about it (new, closed)

This is the round's most important find, and it arrived from re-running the probe on a **rebuilt**
fixture:

```
goal   "Repair the python source <pkg>/broken.py so that its tests pass."   (broken.py is not valid Python)
bound  output_path = <pkg>/broken.py        (the only .py the sentence names)
world  broken.py replaced by the adapter's own JSON report
answer pass=True, status=PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED…
```

Two defects had to meet. The report destination was the file being repaired, on the **primary** path —
the typed retry path has relocated a report off a stated source since 2026-10-27
(`swe_typed_plan_v1._fresh_output_path`), so the same sentence was destructive or not depending on
which path answered it. And the source-change gate then saw a changed byte and was satisfied — by the
report. After the fix the report lands at `<dir>/typed_swe_report.json`, the source keeps its md5, and
the sentence refuses with `FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED`.

Residual (P16 below): the *adapter* still reports `PASS__STATED_TEST_ALREADY_PASSES_NOTHING_TO_REPAIR`
when the discovered corpus is green, because it never learns which file the sentence named. The door
catches it; the adapter called directly would still lie.

---

## 4. The problems, ranked (status after this round)

**P1 — The router cannot say "I do not have this".** 419 rows, 62 SWE; charts, docx, images and
finance are still reachable for code questions. Open. 11 of 61 probe requests bind nothing at all and
say nothing about what is missing.

**P2 — Silent binder refusals.** *Partly closed.* 17 of 61 refuse at admission; the extraction row
went from permanently unreachable to `REAL` in the matrix, and one path now names the slot. The 16
remaining are still anonymous in the sense that they do not name a capability that could serve them.

**P3 — Families that bind nothing.** *Partly closed.* git 0/5 and feature 0/7 are unchanged; refactor
moved 1/7 → 2/8.

**P4 — Write lane.** repair 4/7, refactor 2/8. Still the narrowest part of the machine.

**P5 — Composition swallows failure.** 1 `COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN`, 3
`LIVE_CONTROLLER_EXECUTION` in the probe. Open.

**P6 — A second executor overwrites the first.** Open (mitigated for the refusal-with-reason case).

**P7 — Measurement reported as refusal.** Improved downstream of a real repair: coverage 509 ms and
mutation 1182 ms now answer on a green tree. The refusal was never the gate's fault — it was the
tree's — which is exactly why the probe's order-dependence (P15) hid it.

**P8 — Python-only.** Unchanged: Rust 1, Java 3, C/C++ 0–1, Go 0, Ruby 0, and no tree-sitter bindings
by language.

**P9 — Nothing is cached.** "find every caller of `build_plan` in `canonical/runtime`" still costs
18 s. Unchanged.

**P10 — A referee that is 10 % red.** Unchanged (4 of 40 base modules).

**P11 — Refusals undiagnosable.** *Partly closed*: a binder-named slot is now surfaced. The 27-of-47
anonymous-refusal analysis still applies to the compile-gap bucket.

**P12 — An artifact write certified as an answer.** *Closed for the destructive case* (§3.3). Still
open in the weaker form: a report is still the "answer" for requests whose effect is not a file.

**P13 — No multi-hour resumable work.** Unchanged.

**P14 — Nothing learns from a refusal.** Unchanged: no acquisition queue is fed.

**P15 — NEW: the census is stateful and the state is invisible.** Re-running the same 60 sentences on
a rebuilt fixture moved four cases, three of them **cascades**: the repair case earlier in the list
fixed `calc.py`, so coverage and mutation later measured a green tree and answered. A census that
mutates its own fixture cannot be compared run to run without also recording the tree digest per case.
This is a measurement defect in *this document*, not in the machine.

**P16 — NEW: "the stated test passes" is measured on a corpus nobody said was the subject.** The
repair adapter discovers tests under the stated root when the sentence names none; a discovered green
suite is then read as proof for a source it may never import. The door refuses, the adapter still
claims. Open.

---

## 5. The probe (reproducible)

One tree: `canonical/astra_runtime/tmp/probe8` — a Python package with a failing suite
(`add` returns `a - b`), a benchmark file, a JS package, an unparseable module. Sentences cover
repair, refactor, analysis, measurement, tests, git, feature work, polyglot and honesty. Each case is
a real `door.solve({...})`; nothing is mocked. The fixture is **rebuilt before every run** and each
case's row records status, capability, latency, non-SWE destination and whether the request was
answered.

Answered today (14 of 61) and refused honestly otherwise. Two cases still leave the SWE domain
(`extract_expr` → `math.numeric_expression.sympy`, `analysis/defs` →
`finance.saccr.credit.addon.v1`); 14 bind no capability at all; 17 refuse at admission.

---

## 6. Order to fix (each step makes the next cheaper)

1. **P1 + P14 + P15** — name the missing capability and the unstated input, feed the acquisition
   queue, and make the census per-case `tree_digest` so the document stops lying about its own
   measurements. This is the cheapest step and it shrinks the rest of this document.
2. **P16** — give the repair row the source the sentence named, so the adapter can stop believing a
   discovered corpus is about the file the user pointed at.
3. **P5 + P6** — no executor may swallow another's answer.
4. **P3** — the cheap families over installed tools (git writes, format, type hints, test authoring).
5. **P4** — the generic intent → AST edit → verify → roll-back lane (biggest single gain; extraction
   was the first instance and it took three links to reach).
6. **P9** — one shared cached index.
7. **P8** — tree-sitter behind callers/definitions/impact/rename, bound by language.
8. **P10 + P13** — a green referee and multi-hour resumable tasks.

---

## 7. Reproduction

```bash
cd /home/user/brain
python3 execution_guard/swe_capability_matrix_v1.py                # 54 cases: 17 / 0 / 37 / 0
python3 -m pytest -q canonical/tests/test_a_row_that_exists_must_be_a_row_a_sentence_can_bind_v1.py
python3 -m pytest -q canonical/tests/test_a_report_is_never_written_over_its_subject_v1.py
python3 -m pytest -q canonical/tests/test_swe_typed_plan_v1.py canonical/tests/test_the_answer_must_be_the_effect_that_was_stated_v1.py
python3 canonical/runtime/verify_brain_unified_model_v1.py                                  # 33/33
python3 canonical/runtime/enforce_goal_hierarchy.py --base e2d7981d15809e130759a621687ee77e91c1236b
python3 execution_guard/enforce_load_bearing_primary_pr.py --base e2d7981d15809e130759a621687ee77e91c1236b --head HEAD
```

---

## 8. One sentence

The machine is an **honest** Python reader — zero fabricated PASSes across 54 designed cases and 61
fresh sentences, two more verified write paths than yesterday, and a refusal that finally names the
slot it wanted; **the hard part of software engineering, changing code it did not write across files
and languages, quickly, and knowing when it is already done, is still out of reach**, and the distance
is now measured per capability, per refusal class, and per file digest.

*Authority: NONE — sandbox measurement, not independent verification.*
