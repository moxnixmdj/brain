# Hardcore Software-Engineering Problem Inventory — 2026-10-29 V7

**Scope rule (the founder's frame, applied literally).** This document is about one thing: the
machine that writes, changes, verifies and reasons about *software*. Document editing, PDFs,
images, archives, spreadsheets and the rest of the non-code registry are **out of scope except as
misroute destinations** — when one of them answers a code question, that is a bug recorded here, not
a capability to improve. The target is a software engineer that is *more advanced, faster and
smarter* than the alternative, so every problem below is scored by one question: **does it stop the
machine from doing hard engineering work, or from doing it fast, or from telling the truth about
what it did?**

Everything below is measured in this repository on this tree, on 2026-10-29. Nothing is a wish.

---

## 1. The scoreboard (measured today)

| measurement | value | command |
|---|---|---|
| capability matrix (53 realistic SWE requests, designed fixtures) | **REAL 16 / FALSE 1 / REFUSED 36 / DAMAGED 0** | `python3 execution_guard/swe_capability_matrix_v1.py` |
| fresh probe (36 advanced SWE sentences, one ordinary tree, no per-case fixture tuning) | **9 answered / 27 refused** | §7 |
| registry rows that exist | **419** (after verification/word requirements) | `load_verified_registry()` |
| registry rows that are software-engineering rows | **62** — `python.*` 46, `software.*` 12, `code.*` 4 | id prefix census |
| rows for any language other than Python | **≈0** (JS/TS: 1 `typescript` keyword; Rust 1; Java 3; C/C++ 0–1; Go 0; Ruby 0) | keyword census |
| latency: "find every caller of `build_plan` in `canonical/runtime`" | **18.1 s / 18.6 s** (two runs, uncached) | §7 |
| latency: matrix median / p90 / max | **94 ms / 797 ms / 1145 ms** | matrix output |
| sampled test modules that are red **on the base commit** | **4 of 40 (10 %)** — see §6 | `git worktree` at `efe0877`, every 6th module |
| fabricated PASSes in the matrix | **1** (`repair_with_report`) | matrix `FALSE` row |

Family breakdown of the 53-case matrix:

```
repair     real 4/7      refactor   real 1/7      tests      real 0/3
analysis   real 7/12     toolchain  real 3/7      git        real 0/5
feature    real 0/7      honesty    real 1/5
```

Read that table as a spec of what the machine is: **a Python code *reader* with four measurement
gates, one verified repair, one rename, and no write-lane for anything else.** That is the problem,
stated once. The rest of this document decomposes it.

---

## 2. Problems, ranked by leverage

Each entry: **what happens**, **why (mechanism)**, **what fixed looks like**, **size**.

### P1 — The router cannot say "I do not have this".
The registry holds 419 rows and only 62 are software-engineering rows; the rest are charts, docx,
images, finance, sqlite, maths. The lexical matcher must still return *something*, so a missing
capability becomes a wrong one:

* `Rename the parameter old_price to price in <util.py>` → `python.refactor.rename_parameter.v1` (correct, once) and, on a re-run, `docx.document.create_from_json_record` (measured, §7 R4);
* `Extract the expression a + b into a new function named sum2` → `math.numeric_expression.sympy`;
* `Find the definition of `add` in <file>` → `finance.saccr.credit.addon.v1`;
* `Measure the cyclomatic complexity of <file>` → `python.repository.acceptance.measure.v1`;
* `Measure the test coverage of <file>` → (before V6/V7) `python.repository.acceptance.measure.v1`.

**Mechanism.** Routing is "which row contains the most of the sentence's words", and every row is a
candidate. Refusal statuses name the row that refused, not the capability that is missing, so the
failure is indistinguishable from a bad sentence.

**Fixed looks like.** Effect first, declaration second, and a *named* missing capability:
`MISSING_CAPABILITY:<effect>` in the refusal, with the cell that would satisfy it. The machinery for
the first half exists and is now used for security / coverage / callers / dead code / flaky /
debugger / test-run / change-impact; it is not yet used for extract, move, type hints, formatting,
git, feature work, test authoring. The second half (named-missing + acquisition queue) does not exist yet.

**Size.** Table + binders: medium. Named-missing: small (one status, one field).

### P2 — The same sentence gives different answers over time.
Measured twice in one process, on one tree: first call **PASS** via `python.refactor.rename_parameter.v1`;
second call **FAIL__LIVE_CONTROLLER_EXECUTION** via `docx.document.create_from_json_record`.

**Mechanism.** The derivation binds slots from *evidence in the tree* (the parameter exists, the
file parses). After the first request the evidence is gone — the rename is done — so the plan is no
longer decisive, the primary route is free to pick anything, and there is no answer for "this is
already true". The same mechanism makes the 53-case matrix and the 36-sentence probe disagree on
near-identical sentences.

**Fixed looks like.** An `ALREADY_SATISFIED` answer: prove the requested post-state holds *now* and
report it, with the evidence that proves it. Idempotency is not a nicety for an engineer who runs
the same command twice; today the second run is a coin flip.

**Size.** Small–medium. One derivation-side state check + one status. No new subsystem.

### P3 — The write lane is one-and-a-half capabilities wide.
`repair 4/7`, `refactor 1/7`, `tests 0/3`, `feature 0/7` → **6/24** write requests answered.

What actually writes code today: the test-guided repair loop (with a stated or discoverable test) and
parameter rename. Everything else that changes source — extract function, move symbol, add type
hints, format, add a CLI flag, add logging, add retries, add a parameter and update every caller,
write a unit test — has either no row or no bindable contract.

**Mechanism.** There is no generic "compute an AST edit, verify it, roll back on failure" lane driven
by *intent*. Where a row exists (`python.refactor.extract_function.v1`, the cross-file edit
choreographer) it is unreachable because its declared inputs (the expression span, the target file)
are never derived from the sentence. Where a row does not exist (logging, flags, retries) nothing was
ever declared.

**Fixed looks like.** One lane, effects as data: (statement of the edit → AST transform → render →
verify by tests/type-check → roll back on red), with per-effect templates. The adapters that do this
already exist for three transforms; the gap is the intent→edit-spec binder and the missing effect
templates.

**Size.** Large, and the single highest-value item on this list.

### P4 — Composition is a fallback that swallows the failure.
When nothing binds, the door composes steps from lexical matches. If a composed step raises, the
request ends as `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` — measured for "write a unit test
for `mul`" (R/T2), "explain the bug in <file>" (A7), "read the request and keep the file intact"
(honesty family).

**Mechanism.** A raised step leaves `side_effect_landed: UNKNOWN`, so the chain cannot be retried and
the refusal cannot name a missing capability. It is the only status in the system that is neither an
answer nor a diagnosis.

**Fixed looks like.** A composed chain that wrote only scratch may be superseded by a decisive typed
plan (the rule now exists for the primary path); and a chain that cannot be completed must end in
`MISSING_CAPABILITY`, never in "outcome unknown".

**Size.** Small (extends an existing predicate), high diagnostic value.

### P5 — A second executor can overwrite the first one's answer.
Measured: the mutation gate refused with its own JSON reason (`BASE_WORLD_RED:no tests ran`); the
caller was told `Blocker:BOUND_CAPABILITY_SOURCE_UNSUPPORTED:runtime` — a statement about the
registry's `source.type`, emitted by the other executor, about a gate that had already answered.

**Mechanism.** Two execution paths (local adapter runner and the astra controller) can run the same
action; only one of them parsed structured refusals.

**Fixed looks like.** One rule everywhere: a structured refusal from a capability is *the* answer and
ends the request. Fixed this round at the single-capability path; the controller and composed paths
must carry the same rule, and a test must assert no `BOUND_CAPABILITY_*` blocker can ever be the
reported reason for a capability that answered in JSON.

**Size.** Small.

### P6 — Measurement requests are reported as refusals.
`Measure the test coverage of <file>` where the file is not fully covered ends
`FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT` with `gate: FAIL`; same for mutation score and
performance. The *number* was measured — but it is delivered inside a refusal, and `pass` is False.

**Mechanism.** Four gates declare `expect: {gate: PASS}`, which conflates two different questions:
"did the measurement run?" (the answer to a measurement request) and "does this code meet the bar?"
(a judgement about the code). The row cannot express the difference.

**Fixed looks like.** Two expectations: `measured` (the artifact carries the metric) and `certified`
(the metric meets the threshold). A measurement request PASSes with the number and carries the
finding; a certification request (`make sure coverage is ≥ 90`) keeps the hard gate. This is a
contract change in the registry, not a code change in the adapters.

**Size.** Small–medium, and it converts three "refusals" per tree into real answers.

### P7 — The machine is Python-only, and SWE is polyglot.
62 SWE rows, of which the languages other than Python are effectively absent (JS/TS 1, Rust 1,
Java 3, C/C++ 0–1, Go 0, Ruby 0). A JS `rename` request is answered by a Python tool or refused.

**Mechanism.** Every adapter is `ast`-based (CPython's `ast`), not tree-sitter-based, and the
registry declares no `language` slot the binder can use.

**Fixed looks like.** One tree-sitter layer behind the four analyses that matter most (find callers,
find definition, change impact, symbol rename) plus the linters that already exist per language
(`tsc`, `eslint`, `cargo`, `gofmt`), bound by a declared `language` slot. The repo already has
tree-sitter in-tree (`code.impact.tree_sitter.testselect.v1`).

**Size.** Large, but the reuse is real: the hard part is the binder, not the parser.

### P8 — Whole hardcore families have zero rows.
Measured by keyword census over all 419 rows:

| family | rows | note |
|---|---|---|
| git write ops (commit, branch, bisect, blame, cherry-pick, rebase) | **0** | `git` binary present; matrix `git 0/5` |
| dependency / lockfile resolution (pyproject, requirements, lock) | **0** | matrix `add_dependency` refused |
| build systems (make, bazel, cmake, gradle, cargo) | **0** | — |
| API / contract (OpenAPI, protobuf, schema) | **0** | — |
| DB migrations | 0 (2 unrelated sqlite rows) | — |
| type-hint inference / annotation | **0** | `add_type_hints` refused |
| formatter / autofix | **0** | `format_file` refused |
| test authoring | 1 (property-based oracle) | `write_unit_test`, `add_case_test` refused |
| debugging (breakpoints, frames, tracebacks) | **0** | refuses now, loudly (V7) |
| flaky detection / stability | **0** | refuses now, loudly (V7) |
| release / semver / changelog | **0** | — |
| CI workflow authoring | 0 (matches are unrelated pipelines) | `setup_ci` refused |

Every one of these is a *declaration + binder* problem, not a research problem: `git`, `ruff`,
`mypy`, `bandit`, `coverage`, `pytest` are all in the environment and several are already wrapped.
The most expensive item in the list (cargo/bazel) is still a wrapper.

**Size.** Medium per family, small per row. This is the cheapest real capability on the board.

### P9 — Nothing is cached, so "insanely fast" is false at repository scale.
18.1 s and 18.6 s for one directory-scale caller question, twice in the same process. The matrix
median is 94 ms because its trees are tiny.

**Mechanism.** Every request re-parses the tree it needs. The repository already contains an
incremental index (`code.index.tree_sitter.incremental.v1`) and the change-impact row already builds
and deletes an index per call (`.change_impact_work`), so the index is thrown away after every run.

**Fixed looks like.** One content-addressed index (file sha → symbols, imports, call edges) reused
across requests and updated by delta; a request that touches one file costs the delta, not the tree.

**Size.** Medium. It is the difference between "a tool" and "an engineer you can talk to".

### P10 — The referee is sick.
On the base commit (`efe0877`), 4 of 40 sampled test modules are red (10 %) — e.g.
`test_a_binder_that_consumed_nothing_does_not_outrank_one_that_did_v1`,
`test_a_provisional_pass_says_why_it_is_provisional_v1`,
`test_archive_create_reinspection_and_learning_reachability`,
`test_bound_capability_evidence_and_kernel_native_dispatch_v1`. Separately,
`test_swe_typed_plan_v1` was fully red at HEAD (17 tests, 5 failures) and is green on this branch
(the cause was a family token that let two rows bind one repair sentence, so the plan went ambiguous:
P3/P1 in miniature).

**Mechanism.** Tests were added faster than they were kept green; nothing forbids a red module at
merge time.

**Fixed looks like.** A pre-merge gate on the whole `canonical/tests` suite (not a sample), and
"red module" as a first-class blocker. A machine that cannot certify itself cannot be trusted to
certify code.

**Size.** Small to wire, medium to burn down.

### P11 — Refusals are not diagnosable.
`FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` tells the user nothing. `R3_WEAK_EVIDENCE` tells them less.
Neither distinguishes "no capability provides this" from "your sentence did not state the input".

**Fixed looks like.** Every refusal carries one of: `MISSING_CAPABILITY:<effect>`,
`UNSTATED_INPUT:<slot>` (with the sentence fragment it needed), `CAPABILITY_REFUSED:<reason>`.
The acquisition queue (`canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json`) is
fed from the first class automatically.

**Size.** Small, and it makes every future round cheaper.

### P12 — One fabricated PASS survives in the matrix.
`repair_with_report` — "Repair <src> so that <test> passes, and save the repair report to <report>" —
returns PASS while the matrix's own acceptance check says the effect is not there. One is one too
many: the whole point of the door is that PASS means the work exists.

**Size.** Small (a promised-artifact check for the report path), and it should be closed before any
of the big items, because it corrupts the scoreboard used to rank them.

### P13 — No long-horizon work.
Every measurement above is a single request. There is no capability for "make this build green",
"upgrade this dependency across the repo", "implement this issue", "port this module", "cut a
release" — the multi-hour, many-step work that is most of an advanced engineer's day. Controller
checkpoints exist (`canonical/astra_runtime/state/*CONTROLLER_CHECKPOINT.json`) but they are
execution internals, not resumable tasks with a plan, evidence and a stop condition.

**Fixed looks like.** A task object: goal → sub-goals → steps (each a capability call) → evidence →
stop condition, persisted and resumable, with the same honesty gates at every step. The substrate is
there (composer, controller trace, checkpoints); the *capability* is not.

**Size.** Large; the natural sequel to P3.

### P14 — Nothing learns from a refusal.
`solve_or_learn` exists; memory files are written; the same families refuse forever (git 0/5 in every
round, `tests 0/3`, `feature 0/7`). A refusal that cannot be turned into an acquisition entry is a
refusal the machine will repeat.

**Fixed looks like.** Refusal → `MISSING_CAPABILITY` → queue row with the measured sentence and the
evidence it needed → next round binds it → the matrix case flips from REFUSED to REAL. That loop is
the only mechanism that makes this document shrink.

**Size.** Small to wire; it is P1 + P11 with a writer.

---

## 3. What changed in this round (all measured, all with tests)

| # | defect (measured before) | now |
|---|---|---|
| 1 | "which tests must I run after changing <f>" → `python.repository.acceptance.measure.v1`, PASS over a repository run that never looked at the change | routed to `python.source.change_impact.testselect.v1`; PASS only with a non-empty `selected_tests` |
| 2 | the same question, on a tree whose test file sat beside the module → `selected_tests: []`, PASS (green light to skip the tests) | the anchor directory is a test root; an empty selection is `FAIL_CLOSED__ANSWER_EMPTY__NO_TESTS_SELECTED` and is final |
| 3 | `Rename the symbol `mul` to `multiply`` (quoted identifiers) → read-only symbol index, refusal read as a verdict | quotes are identifiers; the typed retry may supersede a refusal that measured the tree **unchanged**; rename runs and verifies |
| 4 | a rename with no test to verify it rewrote the file **and then** refused | `PASS_BLIND_DRY_RUN`: the patch is computed and syntax-checked, nothing is written |
| 5 | refactor adapters were handed any test file beside the source, including one for a different module (a correct rename rolled back as "red") | `run_tests` only from a test that mentions the module; relative to the directory the capability runs in |
| 6 | mutation gate refused `BASE_WORLD_RED:no tests ran`; the caller was told `BOUND_CAPABILITY_SOURCE_UNSUPPORTED:runtime` | refusal parsed in the local path; a structured refusal is final and reported in its own words |
| 7 | "rerun the failing test 3× … is it flaky" and "attach a debugger … show the frame" → PASS via a test-selection **index** | `STATED_FLAKY_VERDICT_NOT_PROVIDED_BY_CAPABILITY`, `STATED_DEBUGGER_FRAME_NOT_PROVIDED_BY_CAPABILITY` (nothing in the registry declares stability or frames) |
| 8 | "run the test suite for <T>" → PASS via the same index, nothing executed | `STATED_TEST_RUN_NOT_EXECUTED_BY_CAPABILITY`; now routed to `python.repository.acceptance.measure.v1`, which really runs |
| 9 | `test_swe_typed_plan_v1` red at HEAD (5/17) | green (17/17): the repair family's effect token is `repair`, not `apply`, so a no-op diff row can no longer bind a repair sentence |

Test evidence: `canonical/tests/test_the_answer_must_be_the_effect_that_was_stated_v1.py` (10 tests),
`canonical/tests/test_swe_typed_plan_v1.py` (17), and the standing eight-module batch (81 tests, green).
Unified model verifier: **33/33**. Drift guard: **PASS**. Load-bearing admission: **PASS**.

Matrix moved `REAL 13 → 16`, `FALSE 1 → 1`, `REFUSED 39 → 36`, `DAMAGED 0 → 0` — and, more
importantly, three of those REALs are real *for the right reason*, and three former PASSes are now
honest refusals.

---

## 4. The order to fix them in (each step makes the next cheaper)

1. **P12** (one fabricated PASS) — because it corrupts the instrument.
2. **P1 + P11 + P14** (named-missing capability → acquisition queue) — turns every future refusal
   into a work item; shrinks this document automatically.
3. **P6** (measurement vs certification) — three refusals per tree become answers; pure contract work.
4. **P4 + P5** (composed chains and second executors must not swallow answers).
5. **P2** (`ALREADY_SATISFIED`) — the machine stops being a coin flip on a re-run.
6. **P8** (the cheap families: git write ops, formatting, type hints, test authoring, lockfile) —
   declarations and binders over tools that are already installed.
7. **P3** (the generic intent→edit→verify lane) — the largest single capability gain.
8. **P9** (one shared, cached index) — makes the fast claim true at repository scale.
9. **P7** (tree-sitter behind the four core analyses, bound by language).
10. **P10** (green referee) and **P13** (multi-hour tasks) — the two that turn a tool into an engineer.

---

## 5. Reproduction

```bash
cd /home/user/brain
python3 execution_guard/swe_capability_matrix_v1.py            # 53 cases, 16/1/36/0
python3 -m unittest canonical.tests.test_the_answer_must_be_the_effect_that_was_stated_v1
python3 -m unittest canonical.tests.test_swe_typed_plan_v1      # 17
python3 canonical/runtime/verify_brain_unified_model_v1.py      # 33/33
python3 canonical/runtime/enforce_goal_hierarchy.py --base e2d7981d15809e130759a621687ee77e91c1236b
python3 execution_guard/enforce_load_bearing_primary_pr.py --base e2d7981d15809e130759a621687ee77e91c1236b --head HEAD
```

Base-commit test health (sample of 40 modules, every 6th, in a clean worktree of `efe0877`):
4 red — the list is in P10.

Probe fixture (§1, §7): `canonical/astra_runtime/tmp/probe7/pkg/{calc.py,util.py,use.py,test_calc.py,bench.py}`;
36 sentences covering repair, refactor, analysis, tests, git, feature work and honesty.

---

## 6. The one-sentence summary

The machine is an honest Python *reader* with four real measurement gates and a single verified
write path; **the hard part of software engineering — changing code that it did not write, across
files and languages, quickly, and knowing when it is already done — is still out of reach**, and the
distance is now measured per capability rather than guessed at.

*Every number above is measurable again with the commands in §5; nothing in this document is a
projection. Authority: NONE — sandbox measurement, not independent verification.*
