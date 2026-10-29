# What stands between this machine and being the most advanced software engineer — V4

Measured 2026-10-29 on `arena/47739ce8-brain` @ `2621ac7`, branched from `main` `e2d7981`.
Authority: **NONE**. Sandbox measurement, not independent verification. Credit: **0**.
Producer-cognition model dependency: **0**. Incremental spend: **$0**.
Scope: hardcore software engineering. PDF / DOCX / XLSX / chart / archive work is excluded *except*
where it shows up as the **wrong-domain destination** of an SWE request.

V4 supersedes V3. Since V3, three problems were closed **with the existing machinery** (S-1, S-2,
and a new one found by probing, S-5), and the list below is what remains, re-measured after those
fixes. Every number is a probe that ran on this branch; the commands are in §5.

---

## 0. The answer in one paragraph

The machinery is real and now honest about two of the biggest lies it was telling. What remains is
**coverage and cost**, not correctness of what exists: **37 of 47** synthetic requests are honest
refusals (feature 0/7, tests 0/3, git 0/4, honesty 0/5), the one remaining false answer is a
contract conflict that needs an owner's decision (H-1), a single question about one file costs
**21.4 s cold / 5.9 s warm** on the real repository (was 324,727 ms), and one index request still
writes a **103 MB** artifact. The deepest structural problem left is that the machine's **acceptance
layer is keyed by PROGRAM** (`git blame` is read-only, `git commit` is not, and one table cannot say
so) — which is why the git lane is 0/4 and why every new verb has to be added one row at a time.

---

## 1. What changed since V3 (closed, with the mechanism that closed it)

| # | problem | closed by | before → after |
|---|---|---|---|
| S-1 | a **parse** was accepted as the **answer** at directory scale | two rows in the door's existing `_STATED_EFFECTS`, applied **before** execution | `"Find every caller of X in canonical/tests"`: `code.index.tree_sitter.incremental.v1`, 8.7 s, PASS, **0 / 22** callers → `python.source.symbols.index.ast`, **6.4 s, 22 / 22** |
| S-1b | dead code had **no** answer and passed anyway | same table, one row | PASS over `definition_count` (1.2 s) → `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` (63 ms) — honest: 0 of 419 rows declare dead/unused |
| S-2 | one question cost **five minutes** | `_name_indexes()` — the resolver asked a per-path question once per (row, import) pair: 54,722,085 calls | 324,727 ms cold / 313,732 ms warm → **21,756 / 5,896 ms**, identical answer (133 affected, 15 candidate tests) |
| S-5 | **293 inventory rows were routable**, and a script's exit code was certified as the answer | `is_verified_entry()` from the registry's own declaration + "addressable by name, never by words" | `"Show the last 3 lines of <file>"` ran an unrelated `*_verify_v1.py` and returned PASS with `capability_id: None` → `shell.command.run`, `tail -n 3`, real output |
| S-5b | `"Who last changed line 2 of <file>?"` was answered by `tail -n 1 <that file>` and certified **exact semantic acceptance** | `_PROVENANCE_RE` + one `_STATED_EFFECTS` row | PASS (fabricated) → `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` in 63 ms |

The lesson that generalises, and the reason S-5 existed: **a report is not an answer, and an exit
code is the most convincing report of all.** The matrix harness had the same defect (blob-substring
oracles) and was fixed in the same branch.

---

## 2. The problems that remain

### A-1 · The wrong-domain destination is still reachable (analysis)

```
"Report the cyclomatic complexity of canonical/runtime/declared_input_derivation_v1.py"
   -> document.convert.markdown_pdf.pandoc_weasyprint      256 ms   FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
```

A complexity question reaches a **PDF converter**. It no longer *passes* (the gate catches it), but
it is routed to the wrong domain, which means the refusal is a symptom: the registry has **0 rows**
for `complexity` / `cyclomatic`, so there is nothing to route to. Same shape for `"Add type hints to
<function>"` → `plain_goal.bound_capability.grounding.verify.stdlib` (a grounding verifier).

**Reuse:** `radon`/`mccabe` are pure-python; `ast` gives cyclomatic count in ~30 lines without a
dependency. This is a *declaration over an installed tool*, not a new engine.

### F-1 · The verbs an SWE actually uses are absent (feature 0/7)

Census over the 419 registry rows (id + `provides` + `keywords`):

| verb | rows | verb | rows |
|---|---|---|---|
| `format` | **1** — a test-scaffold fusion, not a formatter | `complexity` / `cyclomatic` | **0** |
| `pyproject` | **0** | `dead` / `unused` | **0** |
| `type hint` | **0** | `blame` | **1** — inside a change-impact blob, not a blame capability |
| `logging` | **0** | `fuzz` / `property-based` / `hypothesis` | **0** / **0** / 2 |
| `retry` | **0** | `bisect` / `flaky` | **0** / **0** |
| `docstring` | **0** | `docker` / `ci` / `lockfile` | **0** / **0** / **0** |
| `import sort` | **0** | `profile` | **0** |

Measured at the door:

```
"Format the python source file <f>"                 157 ms  FAIL_CLOSED__NO_OBSERVED_EFFECT   python.source.audit.ast
"Add type hints to the function <f> in <f2>"         73 ms  FAIL__LIVE_CONTROLLER_EXECUTION  plain_goal...grounding.verify
```

**Reuse:** every one of these is a declaration over a tool that already exists (`ruff format`,
`ruff check --select I`, `mypy`, `git commit -m`, `python -m cProfile`, `pytest --lf`). T-1 is what
makes that cheap and T-2 is what makes it worthless without the shape fix.

### T-1 · The declared toolchain is provisioned by nothing

Six SWE rows declare a pypi source (`bandit`, `coverage`, `mypy`, `ruff`, `pytest`). On a fresh
container: **ruff / mypy / pytest absent** (I installed them to take these measurements); `bandit`
and `coverage` still absent. `git` is the only tool that is always there. V2 already measured that
installing them alone changes **no verdict** — necessary, not sufficient.

### T-2 · The tests lane is 0/3

```
"Write a unit test for <f>, run it, and save a report to <r>"   288 ms  FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
"Generate tests from the docstrings in <f>"                      98 ms  FAIL__LIVE_CONTROLLER_EXECUTION
"Add a case to the test for <f>"                                 68 ms  FAIL_CLOSED__NO_OBSERVED_EFFECT
```

Writing a test is the single most common thing an engineer asks for and it is **0/3**. `pytest` is
now installed, so this is shape, not substrate.

### G-1 · The git lane is 0/4, and the reason is structural

```
"Commit the current changes in <pkg> with the message 'fix calc'."     refused
"Show the diff of <file>."                                            refused
"Create a branch named feature/x."                                    refused
"Who last changed line 2 of <file>?"                                  refused (and was a fabricated PASS)
"Run the shell command \"git log -1 --oneline\""           120 ms  FAIL__RAW_GOAL_COMPILATION_GAP
```

`raw_goal_trace_acceptance_v1._READ_ONLY_COMMANDS` (`:963`) is a **frozenset of program names**, and
`_MUTATING_POSTCONDITIONS` is the complement. `git` cannot be placed in either: `git blame`, `log`,
`show`, `diff`, `rev-parse` are re-runnable readers; `git commit`, `checkout`, `reset`, `clean` are
not. So the acceptance layer — the thing that decides whether a run is verified — **cannot express
the most common mutation in software engineering**, and every git request therefore ends as either a
refusal or (before S-5) a fabricated PASS.

This is the deepest problem in the list. The fix is not 30 tools: it is **one key change**, program +
subcommand, and then the git lane is a table of rows over tools that are already installed.

### S-2b · The warm cost is keyed by the wrong thing (5.9 s vs 21.4 s)

`code_tree_sitter_impact_v1._derived_index` writes its index to `.impact_index_<output name>`. The
output name contains the **task id**, so every new request rebuilds the index:

```
"Which tests are affected if I change <one file>?"   cold 21,404 ms   warm (same task id) 5,896 ms
```

**Reuse:** `code_tree_sitter_incremental_index_v1` is already incremental by file digest
(`reused_file_count: 2256`). Keying the derived path by **scope** (`source_root`), not by output
name, makes the second question on the same tree cost the warm number. One line, no new subsystem.

### S-3 · The index representation costs hundreds of megabytes

```
one symbol-index request over canonical/runtime  ->  103.36 MB artifact
one parse of canonical/runtime                   ->  spool artifact 103 MB (earlier round: 284 MB index)
canonical/astra_runtime/tmp after a session of queries -> 488 MB
```

The artifact carries per-file `definitions`, `references` and `imports` as JSON. **Reuse:** the
definition rows and a per-file identifier multiset (Counter) are all the impact and caller queries
actually read; both are a fraction of the size, and `parquet`/`sqlite` are already-latency-neutral
options. This is a representation bug, not a capability gap.

### S-4 · Composition is still 0

```
"Write a unit test for X, run it, and save a report."   288 ms  PROMISED_ARTIFACT_MISSING
"Find the bug in X, fix it, and run the tests."         143 ms  FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
                                                                 (routed to a patch *search*)
```

The DAG planner exists. The chained sentences that a real engineer writes are exactly the ones it
does not fire on. This is the difference between "a machine with 419 capabilities" and "an engineer".

### H-1 · The one false answer is a contract conflict — an owner decision

`"Repair <calc.py> so that the unit test <test_calc.py> passes, and save the repair report to
<out.json>"` returns PASS with the source byte-identical and the test red. The repair family's own
oracle (`live_solver_families_v3.py:430`) demands exactly that. The sentence asks for the test to
pass. Two oracles in this repository disagree; one has to change. **Not code.**

---

## 3. The honest scoreboard

47 requests on fresh 8-file trees, typed oracles, filesystem and a real runner as the only judges:

```
REAL 9 · FALSE 1 · REFUSED 37 · DAMAGED 0 · median 57 ms · p90 687 ms · max 1,766 ms
lanes:  repair 2/7   refactor 1/7   tests 0/3   analysis 3/8
        toolchain 3/6  git 0/4   feature 0/7   honesty 0/5
```

The 37 refusals are not noise; each is a sentence an engineer would write and this machine will not
answer. That number **is** the gap.

What is advanced and measured, and should not be lost: provable-binding cross-file rename (1.2 s),
five repair families with verified apply, the AST symbol index at small scope (159 ms), review gates
on changed lines (0.6 s), a 916,734-reference whole-repository index in one pass, the stated-command
runner (`tail`/`head`/`cut`/`wc`/`sort`/`cp`/`mv`/`rm` from English, verified by re-run), and now a
door that refuses what it cannot answer instead of certifying a report.

---

## 4. The order I would work in

1. **G-1 — the acceptance key (program + subcommand).** It is one change and it unlocks the whole
   git lane, which is the substrate of every other workflow (commit, diff, branch, blame, bisect).
2. **S-2b — key the derived index by scope.** One line; 21.4 s → 5.9 s for every new question.
3. **T-2 — the tests lane (0/3).** `write_unit_test` promises a file and never writes it.
4. **F-1 — the missing verbs** as declarations over installed tools (`ruff format`, `mypy`,
   `import sort`, `logging`, `retry`, `profile`, `complexity`).
5. **S-3 — prune the representation** (103 MB per index request is a tax on every downstream use).
6. **S-4 — let the existing DAG planner fire on SWE chains.**
7. **H-1** — needs an owner decision, not code.

---

## 5. Reproduce

```
python3 execution_guard/swe_capability_matrix_v1.py                  # 47 requests, 8-file trees
python3 execution_guard/swe_capability_matrix_v1.py --lane git       # the 0/4 lane
python3 -m pytest -q canonical/tests/test_a_pending_inventory_row_is_not_an_answer_v1.py
python3 -c "import sys;sys.path.insert(0,'.');from canonical.runtime import live_brain_route_admission_v1 as d;\
print(d.solve({'task_id':'x','goal':'Who last changed line 2 of canonical/runtime/declared_input_derivation_v1.py?'})['status'])"
```
