# Every hardcore-SWE problem that is still open — measured on the merged tree (V11)

Date: 2026-10-31 · branch `arena/47739ce8-brain` · tree `dd840c98` (merge of `main` `ba0924ea`)
· 138 live capability rows · instrument `execution_guard/swe_capability_matrix_v1.py`

This file answers one question: **what is still missing before this machine is the most advanced
software engineer we can build?** It is a census of *defects and gaps*, not of intentions. Every
number below was produced by a command in §9. Where a figure comes from the earlier 120-case census
(`HARDCORE_SWE_PROBLEM_INVENTORY_20261031_V10.md`) it says so.

---

## 0. The answer in one paragraph

Of 54 hardcore-SWE sentences run end to end, **13 are really performed, 38 are refused, 3 are a false
PASS and 1 of those damages the tree**. The same instrument on `main` before this branch: **5 really
performed, 9 false, 3 damaged** — so the honest frontier moved from 5/54 to 13/54 and false PASSes
fell from 9 to 3, but the machine still cannot do the thing a senior engineer is actually paid for:
*change code that is not a single-file Python repair*. It cannot add a CLI flag, add logging, add a
parameter, add retries, implement an issue, or touch a second module in one request (7/7 refused);
it cannot commit, branch, diff or blame a repository (4/5 refused, 1 false PASS); it cannot write a
unit test for a stated function (3/3 refused); it cannot write a file it invented
(`write_unit_test` → `PROMISED_ARTIFACT_MISSING`). The remaining gaps are **three kinds** and they
must be fixed in this order: **(1) honesty — 3 sentences still return PASS over a world that did not
change**, (2) **selection — 21 refusals are the *wrong row* chosen, not a missing capability**, and
(3) **reachability — rows that already exist and no sentence can reach**.

| class | count today | what it means |
|---|---|---|
| **FALSE** (a PASS that is not true) | **3** | `bisect_regression`, `security_review`, `mutation_score` |
| **DAMAGED** (the tree was changed while claiming PASS) | **1** | `security_review` wrote into `bench_calc.py` |
| **refused — wrong row reached** | 21 | `ROUTE_ADMISSION_REJECTED` 9, `STATED_ANSWER_NOT_PROVIDED` 8, `PROMISED_*` 4 |
| **refused — no lane at all** | 7 | `RAW_GOAL_COMPILATION_GAP` |
| **refused — the row ran and failed** | 10 | `LIVE_CONTROLLER_EXECUTION` 6, `REVIEW_RAN_AND_RETURNED_A_VERDICT` 3, `STEP_RAISED_OUTCOME_UNKNOWN` 1 |

---

## 1. Honesty problems — fix these first, they poison everything else

A refusal is a fact; a false PASS is a lie, and this repository exists to prevent exactly that.

### P1 · A PASS over a mutation-score request whose own gate said "not covered" (`mutation_score`, FALSE)
The sentence asks for a mutation score; the gate measured the change set and answered *insufficient*;
the terminal status was `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`. A verdict of
"no" is an **answer**, not an inability — and it is currently reported as a PASS. Fix: the
`REVIEW_VERDICT` class that already exists as a refusal (`REVIEW_RAN_AND_RETURNED_A_VERDICT`) must be
a *verdict* with a pass/fail polarity, and a failing verdict can never be a PASS.

### P2 · A security review that PASSes and writes into the file it reviewed (`security_review`, FALSE + DAMAGED)
Worst row in the census: false PASS **and** `DAMAGED:bench_calc.py`. The review row was handed a
source path as its output. The collision rule exists (`repair_output_collisions`) but is applied in
one lane only. Fix: one call site for both lanes (H6).

### P3 · A bisect that certifies a regression it did not find (`bisect_regression`, FALSE, 9.5 s)
Longest case in the matrix and it returns exact semantic acceptance. Either the postcondition does not
read the bisect exit code, or a row without the bisect result answered. Fix: the stated answer
(a blamed commit) must be present in the result, or it is `STATED_ANSWER_NOT_PROVIDED`.

### P4 · A stated *effect* is still ungated (H1, from V10)
"Make the suite run in parallel" passes because something ran the suite. Files unchanged, nothing
parallel. Fix: an effect gate over the row's own declaration, exactly like the write-authority gate
that closed the previous false PASS (§8.2 of V10.1).

### P5 · The worst diagnosis in the system (H2)
`FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN` (1 case left today, 9 in the 120-case census) names neither
the step nor the reason. Any composed request that raises is un-debuggable by the machine itself.

---

## 2. Refusals by domain — what a working engineer would do and this machine cannot

Status is the measured terminal status of the sentence. Counts in brackets.

### 2.1 Change code at feature level — **0 / 7** (the core gap)

| case | status | the missing wire |
|---|---|---|
| `add_cli_flag` | ROUTE_ADMISSION_REJECTED | no row whose *name* carries "add a flag"; the AST editor can already insert an argument |
| `add_parameter` | ROUTE_ADMISSION_REJECTED | same; `python.refactor.rename_parameter.v1` proves the parameter grammar but does not add one |
| `add_logging` | ROUTE_ADMISSION_REJECTED | no observability row at all (0 rows match logging/metrics/tracing) |
| `add_retries` | PROMISED_SOURCE_CHANGE_NOT_APPLIED | a plan came back, no bytes changed — the imperative-change gate works, nothing behind it writes |
| `implement_issue` | ROUTE_ADMISSION_REJECTED | `python.software.issue_to_pr.orchestrate.v1` exists but needs `task_path`/`pr_intent_path`/`index_path` and nothing derives them from an issue text |
| `crossfile_feature` | ROUTE_ADMISSION_REJECTED | `python.source.crossfile_edit.choreograph.v1` is registered; its edit set is not derived from a feature sentence |
| `fix_failing_ci` | LIVE_CONTROLLER_EXECUTION | the controller runs and fails without a capability-level cause |

**This is the single most valuable cluster in the repository.** "Build me this feature" is the request
the machine is for; today it answers it with a refusal 7 times out of 7.

### 2.2 Refactor beyond rename — **1 / 8**

| case | status | the missing wire |
|---|---|---|
| `rename_symbol` | CAPABILITY_REFUSED_PATH_MISSING | the row refuses its own `path`; `python.refactor.rename_symbol.v1` works when bound from a sentence with a directory |
| `extract_function`, `extract_stated_statement` | LIVE_CONTROLLER_EXECUTION | `start_line`/`end_line`/`new_name` are never derived from "extract the body of the loop in `<fn>` into `<name>`" |
| `move_function` | LIVE_CONTROLLER_EXECUTION | the row is now on `main` (H15 closed) but its adapter fails when reached — the next concrete debug |
| `add_type_hints`, `extract_constant` | ROUTE_ADMISSION_REJECTED | no family triple; the typed selector picks a reader |
| `format_file` | RAW_GOAL_COMPILATION_GAP | no formatter lane at all (no black/ruff/autopep8 row) |

### 2.3 Write tests — **0 / 3**

`write_unit_test` → `PROMISED_ARTIFACT_MISSING` (the sentence promised a test file and nothing wrote
one); `add_case_test` → `PROMISED_SOURCE_CHANGE_NOT_APPLIED`; `tests_from_docstrings` →
`CAPABILITY_RETURNED_A_VERDICT` (an auditor answered a writer's request). The writer exists
(`python.tests.generate.scaffold.v1`) and the sentence routes to the auditor.

### 2.4 Git — **0 / 5** (4 refused, 1 false)

`git_commit` and `git_blame` → `STATED_ANSWER_NOT_PROVIDED`; `git_diff` and `git_branch` →
`RAW_GOAL_COMPILATION_GAP`; `bisect_regression` → false PASS (P3). `git.repository.operate.v1` exists
and `_post_git` already verifies `status/log/diff/show/blame`; the mutating postconditions
(`_MUTATING_POSTCONDITIONS`) already exist. A commit needs a message (derivable from the changed
paths), a branch needs a stated name (already parsed).

### 2.5 Repair at scale — **5 / 7** (the strongest area)

`repair_two_modules` and `repair_test_file` both → `STATED_ANSWER_NOT_PROVIDED`: the single-file
repair lane is real (verb-first, target-first, bug-report, with-report, no-test-named all perform),
but a second module or a test file as the subject is not derived.

### 2.6 Analysis — **6 / 12** (best domain)

Real: callers, dead code, complexity, change impact, function count, perf review.
Refused: `find_definition` (no lane though the index exists), `explain_bug`
(`STATED_ANSWER_NOT_PROVIDED`), `security_audit` (`ROUTE_ADMISSION_REJECTED`),
`measure_coverage` (`REVIEW_RAN_AND_RETURNED_A_VERDICT` — P1's cousin).
False: `security_review`, `mutation_score` (P1, P2).

### 2.7 Toolchain — **1 / 7**

`run_suite` performs. `lint` and `typecheck` answer `REVIEW_RAN_AND_RETURNED_A_VERDICT` on this
machine because **ruff, mypy, bandit and coverage are not installed** — an environment fact, not a
capability fact, and the matrix prints it as a precondition. `create_pyproject` (no lane), `setup_ci`
(no lane), `add_dependency` and `measure_coverage` (`LIVE_CONTROLLER_EXECUTION`) are real gaps.

### 2.8 Honesty lane — **0 / 5** (all correct refusals but unhelpful)

`missing_source` (no lane), `read_request_intact`, `ambiguous_fix_it` (route rejected),
`delete_file` (`STEP_RAISED_OUTCOME_UNKNOWN` — P5), `idempotent_refusal` (route rejected). These are
supposed to refuse; what they should also do is name *what would make it possible*.

---

## 3. Structural problems — rows that exist and cannot be reached

1. **Unreachable rows.** V10 measured **45 of 64** SWE rows that no sentence reaches. Today's registry
   fix removed the "no declared input at all" class: **1 of 138** rows now declares no slot
   (`shell.command.run`, a pass-through by design), down from 18. The remaining unreachable rows are
   blocked on either a derivation (§3.1 of V10: `pr_intent_path`, `start_line`, `test_argv`, …) or a
   family triple in `swe_typed_plan_v1` (§3.2 of V10).
2. **Composition rows chosen as answers.** `software.hardcore.kernel.orchestrate.v1` and the nine
   `*.supercomposer.v1` rows are steps, not answers; the planner picks them for one-line requests and
   they refuse. Fix: mark them internal, or give them the previous step's artifact.
3. **Selection is lexical.** One matched token ("add", "value", "schema") outranks the SWE row —
   the mechanism that would stop it (`swe_typed_plan_v1._resolve_family`: enumerate by the registry's
   own keywords for a stated *effect family*, require the effect token in the answering row's id, fail
   closed on ambiguity) is decisive already for callers, type-check, coverage, security, mutation,
   perf, extract and repair. It is decisive for 21 of the 38 refusals today only because those
   sentences state an effect that is either not in `_FAMILIES` or has no row carrying the token.
   **Each missing family is one `(triggers, registry-terms, effect-token)` triple — not 21 bugs.**

---

## 4. Domains with no hardcore row at all — the real building work

Measured by scanning every row's id + keywords + provides for the domain vocabulary (V10 §5, re-checked
against today's 138 rows — unchanged except git, which now has `git.repository.operate.v1`):

| domain | SWE rows | what is missing |
|---|---|---|
| **Feature work** (add flag / param / logging / retries / endpoint) | **0** | the writer family over the AST editor |
| **CI / packaging / release** | **0** | workflow authoring, wheel build, dependency add/upgrade, lockfile, SBOM, vuln audit |
| **HTTP / API** | **0** | add a route, generate a client, check a handler against an OpenAPI schema |
| **Schema / data migration / ORM** | **0** | create or modify a migration, model a table, validate against a schema |
| **Observability** | **0** | structured logging, metrics, tracing |
| **Git history surgery** | 1 (operate) | commit, branch, rebase, worktree, cherry-pick, bisect, revert |
| **TypeScript / Go / Rust** | 1 (parser) | write, type-check, test, lint, port non-Python code |
| **Property / fuzz testing** | 1 (CEGIS) | generate property tests, shrink a failure, fuzz a parser |
| **Async / concurrency** | 2 (incidental) | make a function async, find a race, bound a pool, prove no deadlock |
| **Supply chain / hardening** | 5 (security gate) | secrets scan, dependency audit, path-traversal hardening, licence report |
| **Performance** | 3 (perf gate, complexity) | profile, benchmark with a recorded baseline, find the hot path |

Every one of these is **a registry row plus an adapter over machinery that already exists in the tree**
(the verified command runner with postconditions, the tree-sitter index, the AST editor, the CEGIS
oracle, the acceptance chain). It is not a subsystem.

---

## 5. The order that buys the most capability per hour

1. **Kill the three false PASSes** (P1, P2, P3). No capability gained, but every later measurement
   becomes trustworthy. One class (`REVIEW_VERDICT` polarity) + one call site (output collision) +
   one postcondition (bisect blame).
2. **One family table** (§3.3): 21 wrong destinations collapse to the triples that are missing. No new
   capability; the effect token must appear in the answering row's id.
3. **Feature writers** (§2.1, §4): add flag / parameter / logging / retries as rows over the AST
   editor that already inserts and refuses collisions. This is the "build software" request.
4. **Git surgery** (§2.4): commit, branch, diff, blame, bisect — `_post_git` and the mutating
   postconditions are already written; a message deriver and a stated-name binder are the missing
   half.
5. **Test authoring** (§2.3): make `python.tests.generate.scaffold.v1` the answer to "write a test
   for `<fn>`", and make the promised artifact real.
6. **Derivations for the unreachable rows** (V10 §3.1): `pr_intent_path`, `start_line`/`end_line`,
   `test_argv`, `measurement_receipt_path`. Each is a proof from stated evidence, refused on ambiguity.
7. **Repair at scale** (§2.5): the second module and the test-file subject.
8. **Then** the zero-row domains: packaging, data/schema, HTTP, polyglot, concurrency, observability,
   property testing.
9. **In parallel, the honesty items that cannot produce a PASS** (P4 effect gate, P5 diagnosis).

Do **not** rebuild: the verified command runner, the tree-sitter index, the AST editor with collision
refusal, the typed selector, `declared_input_derivation`, the acceptance chain. They are the reason 13
sentences already perform end to end.

---

## 6. What is already *not* a problem (do not spend hours here)

* Single-file Python repair — verb-first, target-first, bug report, with-report, no-test-named all
  really change the file and the receipt says `applied: true`, `source_restored: false`.
* Knowing a caller, a dead function, a complexity number, a change set, a function count, a perf
  regression — 6 of 12 analysis requests perform.
* A module move that would orphan its importers — refused before anything runs, the tree still
  imports (V10 §6.1).
* A report written onto the path the sentence reserved for source — repointed, pinned by a test.
* `pdf`/`docx`/`chart`/`finance` rows: out of scope on purpose. They answer, they are correct, and
  they are not the product.

---

## 7. Where the branch stands right now (honest status)

* PR **#6309**, head `dd840c98`, referee `referee/repo-integrity-guard` **PASS** (17 rules, 0
  violations, base `ba0924ea`), **0 new capability ids** versus `main` — the merge resolves the
  registry as `main`'s 138 rows with this branch's 8 enriched entries.
* Capability matrix on the merged tree: **13 REAL / 3 FALSE / 38 REFUSED / 1 DAMAGED**, latency
  median 86 ms, p90 759 ms, max 9.5 s. `main` with the same script: **5 REAL / 9 FALSE / 40 REFUSED /
  3 DAMAGED**.
* Unified model **33/33** (AUTHORITY NONE); bound-capability provenance **0 UNPROVEN / 0 MISSING**.
* Per-module sweep over the 106 modules that touch these paths: **42 modules with red ids**, of which
  40 were red before the merge. Of the six that went red in the merge, all six are now closed or
  accounted for: three were this branch's own claim-tests and are **fixed at their cause** (the
  `module:not_stated` settle-pass split, the `STATED_FLAKY` / `STATED_TEST_RUN` table order, and the
  change-set question that a definitions index was answering), one was a stale pin that is now
  re-pinned with the direction recorded (front-door/canonical selection 22 → 19, measured identically
  on the pre-merge branch, the merge base and `main`), and two are inherited from `main`
  (`test_swe_typed_plan_v1` 5 red there too, `test_a_goal_naming_a_real_program_is_attempted`).
* Affected 6-module sweep after those fixes: **18 red**, against **21** on the pre-merge branch and
  **24** on `main` — four of `main`'s/HEAD's reds are green here.

---

## 8. Reproduction

```bash
python3 execution_guard/swe_capability_matrix_v1.py          # 54 -> 13 / 3 / 38 / 1
python3 canonical/runtime/verify_brain_unified_model_v1.py   # 33/33, AUTHORITY NONE
python3 canonical/runtime/verify_bound_capability_provenance_v1.py --check   # 0 unproven
gh pr checks 6309                                            # referee PASS
```

Per-case status table, verbatim: `/tmp/matrix_now.txt` (this run) — the same 54 sentences, one line
each, with the refusal that names what is missing.

*Authority: NONE — sandbox measurement, not independent verification.*
