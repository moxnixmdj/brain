# What is actually missing — the complete problem list for a hardcore software engineer

**2026-10-30 · V10 · every claim below was measured on this tree today unless marked STRUCTURAL.**

Scope, as instructed: the machine that writes, changes, verifies and reasons about *software*.
PDFs, docx, spreadsheets, charts, finance and the other 350-odd non-code rows appear here only as
**wrong destinations that must be refused**, never as capability targets.

How each claim was obtained, so it can be re-run or refuted:

| instrument | what it measures | today |
|---|---|---|
| `execution_guard/swe_capability_matrix_v1.py` | 54 designed SWE requests, fresh tree each, judged only by the filesystem / a real runner / the gate's own artifact | **REAL 17 · FALSE 0 · REFUSED 37 · DAMAGED 0**, median 111 ms |
| open-phrasing probes (61 sentences + 27 advanced requests, §8) | ordinary engineer sentences over a normal tree, no curation | **14 of 61 answered**; **3 fabricated PASSes found and all 3 closed in this round** (§2) |
| registry census (`load_verified_registry()`) | what rows exist and what they can bind | **419 rows · 63 SWE** (python 46, software 12, code 4, shell 1) |
| direct timings | cost of the right answer at repository scale | caller map **19.3 s** cold, **261 ms** when the *wrong* row answers (§2.3) |

---

## 1. The honest headline

The machine is a **Python code reader with three verified write operations** (repair a red test,
rename a symbol/parameter, extract one stated statement), four real measurement gates (coverage,
mutation, security, perf) and two static gates (lint, type-check). Outside that box it is either
silent or — in three shapes measured today — **wrong in the most damaging way: it says PASS**.

The distance to "most advanced, fastest, smartest software engineer" is therefore not one problem.
It is **24 problems in six families**. The first of them was not a missing feature but three
**fabricated PASSes** that the designed matrix never asked for — because the matrix only asks
questions the machine can already answer. **Those three are closed as of this round** (§2.4); the
other 23 are open, and they are ordered below by what they cost.

---

## 2. Three fabricated PASSes, measured today — and closed

All three are `door.solve({...})` on ordinary sentences. Each returned `pass=True`. Each is
reproducible in under a second. Each is a different *shape*, and all three come from one root cause.

### 2.1 A refactoring request "answered" by a reader

```
goal   "Split the function mul in <pkg>/calc.py into smaller functions."
bound  python.source.audit.ast          (an inventory of imports/functions/classes, read-only)
world  calc.py byte-identical (md5 before == after)
answer pass=True, PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED…
```
`"Split the function add …"` behaves the same. Nothing was split; nothing was even attempted.

### 2.2 A JavaScript test suite that does not exist

```
goal   "Run the javascript test suite in <dir>."      (dir contains pkg/, no JS at all)
bound  python.repository.acceptance.measure.v1        (a PYTHON acceptance measurement)
answer pass=True
```
With a real `web/` directory containing `package.json` and `app.test.js` the same sentence dies at
`NO_TEST_FILES_UNDER_SOURCE_ROOT` — i.e. the machine answers the *absent* case and fails the
*present* one. A Python row must never certify a JavaScript request.

### 2.3 The fastest answer is the wrong one

```
goal   "Find every caller of the function build_plan in canonical/runtime."
   -> 19 259 ms, python.source.symbols.index.ast, PASS          (the right row, real caller map)

goal   "Find every caller of the function load_verified_registry in canonical/runtime."
   ->    261 ms, software.repair.choreograph.crossfile.v1, PASS  (a REPAIR row, no caller map)
```
Same question, 74× faster, certified — by a row that has nothing to do with the question. For a
machine whose first requirement is speed, this is the worst possible failure: **the wrong answer is
the fast answer.**

**Root cause of all three (one sentence):** certification is only as strong as the
`_STATED_EFFECTS` table in `live_brain_route_admission_v1`, and any effect that is not in that table
can be "answered" by any row whose own `expect` field (usually `output_verified == true`) is
satisfied. Reading a file, writing a report or repairing something else all satisfy it. The table's
own docstring already admits two of these holes ("dead code, bisect, CI today").

What the table could not express is subtler than a missing effect: each failure was **the wrong KIND
of row** for the sentence, and a wrong kind of row satisfies its own expectation perfectly.

### 2.4 Closed — the same three sentences, after the fix

The rule is drawn from each row's **own declaration**, so the day a capability that really splits a
function or really runs a JavaScript suite is bound, the same declaration admits it and nothing has
to change:

* a **transform** request (`split`, `inline`, `decompose`, `extract the method`) requires a row that
  declares a transform;
* a **read-only question** may not be certified by a row whose `provides` declare a patch, a repair
  or an applied write — a question is answered by a reader;
* a request naming a **non-Python** language may not be certified by a Python-only row (a row that
  runs an arbitrary stated command line is exempt: `npm test` *is* how a JS suite is run).

```
"Split the function mul in <pkg>/calc.py into smaller functions."
   before  pass=True   python.source.audit.ast            (calc.py byte-identical)
   after   pass=False  FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED:python.source.audit.ast

"Run the javascript test suite in <dir-with-no-js>."
   before  pass=True   python.repository.acceptance.measure.v1
   after   pass=False  FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED

"Find every caller of the function load_verified_registry in canonical/runtime."
   before  pass=True   software.repair.choreograph.crossfile.v1   261 ms   (no caller map)
   after   pass=True   python.source.symbols.index.ast         19 259 ms   (the correct row)
```

The four answers that must survive, survive: a real caller map, a real statement extraction, a real
coverage measurement and a real repair are all still certified (the matrix stayed
`REAL 17 / FALSE 0 / DAMAGED 0`, the batch went to **88 tests green over 11 modules**), and
`canonical/tests/test_a_wrong_kind_of_row_cannot_certify_the_work_v1.py` pins both halves.

---

## 3. The capability ladder — what a top-decile engineer does, and what this machine does

Each rung is scored from the probes and the matrix, not from opinion.

| # | the work | today | evidence |
|---|---|---|---|
| 1 | **Locate** — callers, definitions, impact, imports, counts | ✅ works, **Python only**, 19 s cold | `analysis/callers·defs·impact·count·imports`; matrix `find_callers`, `change_impact`, `count_functions` |
| 2 | **Explain** — "what does this do", dead code, complexity, coupling | ❌ misroutes (`explain` → a provenance tracer; `dead code` → a test selector) | §8 probes |
| 3 | **Measure** — coverage, mutation, security, perf, lint, type-check | ✅ six gates, on a *green* tree | matrix `measure_coverage`, `mutation_score`, `security_review`, `perf_review`, `lint`, `typecheck` |
| 4 | **Repair** a red test | ✅ one bounded family (whole-number/operator search) | `fix_verb_first`, `fix_target_first`, `bug_report`, `repair_no_test_named` |
| 5 | **Rename / extract** | ✅ rename param, rename symbol, extract one stated statement | §V9 round; matrix `rename_param`, `extract_stated_statement` |
| 6 | **Other refactors** — split, inline, move, dedupe, annotate, docstrings, validation | ❌ 0 of 7; two of them *pass* falsely | §2.1, §8 |
| 7 | **Author tests** — write, add a case, find flaky, reproduce a bug | ❌ 0 of 4 (`write_test` raises a composed step; `flaky` answered by a selector) | matrix `tests 0/3`, §8 |
| 8 | **Add a feature / multi-file change** | ❌ 0 of 7 | matrix `feature 0/7` |
| 9 | **Git and repo work** — commit, branch, bisect, history, PR | ❌ 0 of 6; not even a compile gap with a name | §8 (`git_commit`, `git_branch`, `git_bisect` → `RAW_GOAL_COMPILATION_GAP`) |
| 10 | **Polyglot** — JS/TS/Rust/Go/Java/C | ❌ nothing; a Python row even answers a JS suite request | §2.2; registry has Rust 1, Java 3, C/C++ 0–1, Go 0, Ruby 0 |
| 11 | **Debug** — breakpoints, stack frames, dynamic fault localisation | ❌ rows exist (`python.fault.localize.dynamic.dataflow`), **unreachable** | probe `tests/debugger` |
| 12 | **Optimise** — "make it faster" | ❌ measurement only; the request refuses | §8 (`perf_fix`) |
| 13 | **Review** — design, API, change safety, "what is wrong with my patch" | ⚠️ one static-triage gate; no judgement | §8 (`review`) |
| 14 | **Long-horizon** — plan, decompose, resume, hours of work | ❌ nothing | P13 |

**Read the ladder as the specification:** rungs 1–5 exist and are honest; rungs 6–14 do not exist,
and the two that look like they might work (6, 10) are where the false PASSes are.

---

## 4. The six structural reasons — why most of the ladder is missing

These are worth more than the symptom list, because every rung above fails for one of them.

**S1 — A contract that no sentence can satisfy.** 23 of the 63 SWE rows declare **≥6 inputs**
(`extract_function` needed 10). Each needs a *derivation* — a rule that reads the value out of the
sentence or the tree — and until it has one, the row is dead code wearing a registry entry. V9 added
one such rule (extract) and it turned a dead row into a `REAL` answer in a day. **There are 22 more
rows in the 6+ band.** This is the single highest-leverage structural fact in the machine.

**S2 — Rows that cannot be addressed at all.** **18 of 63** SWE rows declare only `capability_id`:
`software.hardcore.swe.supercomposer`, `python.pr.land.composer`, `python.patch.review.supercomposer`,
`python.test.pipeline.verifier`, `software.review.gate.composer` and friends. They can only be called
by *discovery*, never by a sentence. They are the "advanced" machinery — PR landing, patch review,
test pipelines — and none of it is on a path a human can reach.

**S3 — Certification weaker than the request.** §2. One table (`_STATED_EFFECTS`) decides whether a
capability can supply the stated effect; everything outside it can be certified by any write.

**S4 — Language is not declared.** No row says which language it serves, and no gate compares the
language of the sentence to the language of the row — so a Python acceptance measurement can pass a
JavaScript test request. The registry's own non-Python coverage is ~0 (Rust 1, Java 3, C/C++ 0–1,
Go 0, Ruby 0; JS/TS = a single `typescript` keyword). Tree-sitter is installed and one
`code.patch.tree_sitter.verify.v1` row exists with 6 inputs and no derivation.

**S5 — Nothing accumulates.** No index cache (19 s per caller question), no learning from refusals
(27 of 61 refusals are anonymous and none feeds an acquisition queue), no reuse across a session.

**S6 — No plan.** There is a compiler and a composer, but nothing that takes "implement this issue"
and produces an ordered, resumable plan with checkpoints. Every capability is one shot.

---

## 5. The complete problem list (ranked by what it costs)

Format: **what is broken · evidence · why it blocks advanced work · the cheapest existing mechanism to reuse.**

**P-01 · Three fabricated PASSes (S3/S4) — CLOSED this round.** §2.4. Three *kind* rules now refuse
a transform request to a reader, a question to a mutator, and a non-Python request to a Python-only
row, each read from the row's own declaration; no verdict on a servable sentence changed. What
remains open in this family is the general case: certification still rests on one table, and any
future effect not in it is one permissive `expect` away from the same failure. *Next:* make the
declaration-versus-sentence check mandatory for **every** certification (not only the listed
effects), and extend the effect table with the explain/dead-code/optimise families (P-10, P-12).

**P-02 · 22 dead rows in the 6+ input band (S1).** `python.patch.search.test_guided.ast.v1`,
`python.fault.localize.dynamic.dataflow.v1`, `python.software.issue_to_pr.orchestrate.v1`,
`python.repo.pr_realize.v1`, `code.patch.tree_sitter.verify.v1`, `python.software.repair.loop.*` …
Every one is a real capability nobody can ask for. *Fix:* derivation rules, one at a time, each
measured by making a matrix case REAL — the extract round is the template (3 links: verb set, family
row, slot guard).

**P-03 · 18 zero-argument rows (S2).** The advanced machinery — PR landing, patch review, test
pipeline, evidence synthesis — is unreachable by sentence. *Fix:* give the top five a declared
contract (they already know their inputs) and a derivation; or reach them from a **plan** (P-06).

**P-04 · No feature work (0/7 in the matrix).** "Add `--verbose`", "add retries with backoff",
"thread an argument through three files", "implement this issue". *Fix:* the crossfile choreographer
and `issue_to_pr` already exist; they need a change-set derivation (the stated paths → `edits_path`)
and an authoring lane. This is the biggest capability gain per line of code.

**P-05 · No test authoring (0/4).** `python.tests.generate.scaffold.v1` exists with 3 inputs and
answers nothing; `write_test` currently raises inside a composed chain. For an engineer, writing the
failing test *is* how work starts. *Fix:* bind scaffold from "write a test for <fn> in <f>" (source
root + symbol are derivable), then verify by running it.

**P-06 · No plan, no resume, no long-horizon (S6).** Everything is one capability, one shot. A real
task is 10–50 steps with checkpoints. *Fix:* `software.issue_to_pr.orchestrate` and
`python.pr.land.composer` already describe the pipeline; a checkpointed plan executor is the one place
where new code is justified.

**P-07 · No git (0/6).** commit, branch, bisect, history, revert, PR. `git` is installed;
`shell.command.run` exists. *Fix:* a stated command line is already extracted by the composer
(`extract_argv`), and "commit with message X" is a stated argv; the missing piece is a declared git
row family and a refusal-free binding for it.

**P-08 · Polyglot is absent (S4).** JS/TS/Rust/Go/Java: no editing, no tests, no lint, and the one
JS request that "passed" was a Python row. *Fix:* language declarations + tree-sitter symbol rows
(the binary is installed; one verify row exists) + a JS test runner row (`node --test` is on disk).
Start with JS/TS: it is the second language of every web codebase.

**P-09 · Six refactors missing (0/7)** — split, inline, move, dedupe, annotate, docstrings, plus
"add validation". *Fix:* each is an AST transform of the kind the repo already contains
(`python_refactor_rename_symbol.py` synthesises and syntax-checks a whole patch); the blocker is the
contract, not the transform.

**P-10 · Explain and dead code misroute.** "Explain <f>" → a provenance tracer; "find dead code" → a
test selector. The symbol index already holds definitions and references; dead code is "no
references", explain is "signature + references + docstring". *Fix:* one reader row with a stated
effect.

**P-11 · Debugging unreachable.** `fault.localize.dynamic.dataflow` (8 inputs) and
`fault.provenance.interprocedural.value` (7 inputs) are dynamic-analysis capabilities no sentence can
bind. *Fix:* derive the test command + source root the way the repair row does; "why does X fail" is
the sentence.

**P-12 · No optimisation.** The perf gate *measures*; nothing improves. *Fix:* "make X faster" needs
a transform lane, not a measurement — start by having the machine *report the hotspot with a
number* instead of refusing (cheap, honest, useful).

**P-13 · No design/API/change-safety review.** `review.diff_static_triage` is one gate.
*Fix:* the diff-coverage/mutation/security/perf gates already take a diff; a "change set" review that
runs all four and reports them together is composition, not new capability.

**P-14 · 19 s per caller question, no index cache (S5).** Measured twice today. A repository-scale
question re-parses everything every time. *Fix:* one content-addressed index keyed by
(path, mtime, size) — the repo already writes content-addressed artifacts.

**P-15 · 27 of 61 refusals are anonymous; nothing learns from one (S5).** The refusal names a class,
not the capability that would have served it, and no queue records it. *Fix:* refusals already carry
`compiled_capability_id` and, since V9, the binder's own slot; emit `MISSING_CAPABILITY:<family>` and
`UNSTATED_INPUT:<slot>` rows into an acquisition file.

**P-16 · Composition swallows failures.** `write_test` → `COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN`;
three `LIVE_CONTROLLER_EXECUTION`. *Fix:* a failed step must be reported, not replaced by the other
executor's verdict.

**P-17 · Measurement reported as refusal.** Coverage/mutation refuse on a red tree (they must), but
the answer says "review ran, verdict FAIL" without the number or the next action. *Fix:* separate
`measured` from `certified` in the artifact.

**P-18 · A 10 %-red referee.** 4 of 40 sampled base modules fail; 3 CLI subprocess tests are flaky at
module scope. An engineer cannot trust a suite that is red at rest. *Fix:* quarantine + fix, tracked.

**P-19 · Two pre-existing failures in the binder-fallthrough test** (verified identical at the base
commit). The write lane they describe still loses the file. Same family as P-04.

**P-20 · No conversation-level memory of the tree.** Every request re-derives the same facts
(source root, tests, symbols). *Fix:* the same cache as P-14, scoped to the task.

**P-21 · Refusal granularity.** `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` (17 of 61) still does not
say "a capability that could serve this exists but needs X". V9 fixed one path; the compile-gap
bucket (11) is untouched.

**P-22 · No property-based / differential / fuzz verification.** `unittest`/`pytest` only. A repair
verified by one assertion is not verified. *Fix:* hypothesis is a pure-Python dependency and the
acquisition gate already probes before installing.

**P-23 · No performance regression gate on the machine itself.** Nothing measures the cost of the
door (except the matrix's median). "Insanely fast" is currently an aspiration with two numbers.

**P-24 · No cross-file semantic index.** `symbols.index.ast` is per-file; impact analysis re-walks
the tree; rename "across every caller" is a matrix refusal (`rename_symbol`). *Fix:* the same index
as P-14, with references.

---

## 6. Speed — the honest state

| request | today | what a top engineer's tool answers in |
|---|---|---|
| locate a symbol's callers (small tree) | 72–111 ms | ~50 ms |
| locate callers across `canonical/runtime` | **19.3 s** (cold), no cache | <1 s |
| full suite run + gate | 150–1100 ms per case | — |
| a wrong row answering a repo question | **261 ms** — faster than the right answer | — |

The machine is fast where the work is small and slow exactly where the repository is real, and the
one thing it does *fast* at scale is answer with the wrong row. Fixing P-14 and P-01 in that order
turns both halves of that sentence around.

---

## 7. What "done" looks like — acceptance tests, not adjectives

A claim of "most advanced software engineer" is only meaningful if each line below is a test:

1. **No false pass on open phrasing.** 200 uncurated engineer sentences; every `pass=True` backed by
   an independent filesystem/test-runner oracle; zero exceptions.
2. **Every SWE row reachable.** For each of the 63 rows, one sentence exists that binds it and one
   matrix case judges it. (Today: 17 judged, 22 need derivations, 18 need contracts.)
3. **A feature request lands.** "Add `--verbose` to X and a test for it" → diff + passing test +
   unchanged unrelated files, in one call.
4. **A repository-scale question is answered in under a second, twice** (the second one cached).
5. **Two languages.** The same five operations (locate, repair, rename, test, lint) on JS/TS as on
   Python, judged by the same oracles.
6. **A 10-step task resumes** after a kill and finishes.
7. **Every refusal names a capability and an input**, and the list of them is the queue that gets
   built next week.

---

## 8. Reproduction

```bash
cd /home/user/brain
python3 execution_guard/swe_capability_matrix_v1.py                 # 54: 17 REAL / 0 FALSE / 37 REFUSED / 0 DAMAGED
python3 -m pytest -q canonical/tests/test_a_row_that_exists_must_be_a_row_a_sentence_can_bind_v1.py
python3 -m pytest -q canonical/tests/test_a_report_is_never_written_over_its_subject_v1.py
# the three false passes in §2 (fresh trees are built by the snippet in the V9 doc):
#   "Split the function mul in <pkg>/calc.py into smaller functions."
#   "Run the javascript test suite in <dir-with-no-js>."
#   "Find every caller of the function load_verified_registry in canonical/runtime."
python3 canonical/runtime/verify_brain_unified_model_v1.py          # 33/33
```

---

## 9. Fix order (by measured leverage, not by taste)

1. ~~**P-01** (false passes)~~ — **done this round** for the three measured shapes; the residual is
   the general declaration check (see P-01).
2. **P-02 + P-03 + P-15** — derivations and contracts for the dead rows, and refusals that name
   them; this converts the census into a work queue.
3. **P-14 + P-20 + P-24** — one cached, content-addressed index; it makes "fast" true at scale and
   speeds up everything else.
4. **P-04 + P-05 + P-09** — feature work, test authoring and the six missing refactors: the actual
   engineering.
5. **P-07 + P-08** — git and the second language.
6. **P-06** — the plan executor, once there are enough steps worth planning.
7. **P-18 + P-22 + P-23** — a green referee, stronger verification, and a cost meter.

---

*Authority: NONE — sandbox measurement, not independent verification. Every number in this document
came from a command run on this tree today; §8 reproduces them.*
