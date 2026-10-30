# Hardcore software engineering — the complete problem census (2026-10-30, V8)

**Scope.** The machine that understands, changes, verifies and ships software. Document, PDF, image,
spreadsheet and chart work appears in exactly one role here: as a **wrong destination** the router
must refuse. Everything below is judged by three questions only — does it stop the machine from doing
hard engineering work, from doing it fast, or from telling the truth about what it did.

**Status of every claim.** Measured on this tree today (HEAD `ea66344`), by instruments in the
repository: `execution_guard/swe_request_probe_v1.py` (`--suite sentence` 28 cases, `--suite
hardcore` 46 cases over a fresh tree each), `execution_guard/swe_capability_matrix_v1.py` (54 cases),
and a registry census over `load_verified_registry()` / `is_verified_entry()`.

---

## 1. Scoreboard

| measurement | value |
|---|---|
| registry rows / **routable** | 419 / **125** |
| software-engineering rows | **63** (`python` 46, `software` 12, `code` 4, `shell` 1) |
| SWE rows that declare **no inputs** (unreachable by any sentence) | **18** |
| SWE rows that need 6–9 inputs | **8** (3 refactor primitives, 3 review gates, `pr_realize`, `issue_to_pr`) |
| rows that structurally EDIT code | **4** (extract_function, rename_symbol, rename_parameter, crossfile choreograph) — the other 11 "editing-ish" rows are repair loops |
| rows for git / build / dependency / CI work | **0** |
| 54-case matrix | **17 REAL · 0 FALSE · 37 REFUSED · 0 DAMAGED**, median 100 ms, p90 1 012 ms |
| 28-sentence probe | **6 answered (21 %)**, p50 46 ms, 0 trees damaged |
| 46-request hardcore probe | **6 answered (13 %)**, 2 real source changes, 0 refusals that dirtied a tree, p50 90 ms |
| installed and unused by any reachable row | `git 2.39`, `node 22` + npm, `ruff`, `mypy`, `bandit`, `coverage`, `pytest`, `make`, `gcc`, `patch`, `diff` |

**The machine's real capability, in one line:** it reads a Python tree (symbols, callers, change
impact), runs a suite or a Makefile, typechecks with mypy, reviews security with bandit, renames a
symbol inside one file, extracts one stated statement, and repairs one bug when the failing test is
named. That is 17 of 54 designed hardcore requests and 6 of 46 ordinary advanced ones.

---

## 2. Reach — the request does not arrive at the right capability

**R1 · Selection does not follow the command line.** Measured today, attempting the cheapest git
capability in the repo:

```
"What changed since the last commit?"
  argv in hand   ["git", "status", "--porcelain"]        (composer_route.extract_argv)
  compiler picks python.source.change_impact.testselect.v1   (on the word "changed")
  answer         FAIL_CLOSED__ROUTE_ADMISSION_REJECTED:NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND
```

The refusal is correct about the row and wrong about the request: a row that cannot run a command
was chosen while a row that runs nothing else exists. **Cheapest fix:** where that exact rule fires
and `extract_argv` is non-None, re-select `shell.command.run` and re-enter the same gate chain.

**R2 · An operand is bound as a destination.** `git -C <dir> status --porcelain` executes with the
right argv and then fails `FAIL_CLOSED__NO_OBSERVED_EFFECT`, because the shell row binds the
sentence's only path as `output_path` — and in `-C <dir>` the path is a **target**. This blocks every
`tool -C/-f/--path <path>` shape, not just git. **Cheapest fix:** one rule in the binder — a path the
derived argv already contains is an operand, never an output.

**R3 · A wrong subject can still pass.** `Show me the recent commits in <fixture>.` returned
`pass=True` with the history of **the enclosing repository**, because the target directory was not
resolved and the row fell back to `.`. A true statement about the wrong world is worse than a
refusal. **Cheapest fix:** the same rule as R2, plus "no target resolved ⇒ refuse".

**R4 · Work done, report says nothing happened.** `Create the branch feature/x in <dir> and switch to
it.` **created the branch** and returned `FAIL_CLOSED__NO_OBSERVED_EFFECT`. The effect existed and no
verifier looked at it. **Cheapest fix:** a `_post_git` postcondition (written and measured this
session, waiting on R1/R2).

**R5 · 18 SWE rows no sentence can reach**, including every `*supercomposer*`,
`python.pr.land.composer.v1`, `python.test.pipeline.verifier.v1`,
`python.patch.review.supercomposer.v1`, `python.fault.patch.supercomposer.v1`,
`software.hardcore.swe.supercomposer`. They declare no inputs, so nothing can bind them.

**R6 · 8 SWE rows ask for more than anything derives** — `pr_realize` and `issue_to_pr.orchestrate`
most importantly. (Note: slot count alone is not the blocker — `rename_symbol` needs 8 and works,
because a typed plan derives them. The blocker is the missing derivation, not the arity.)

**R7 · Two routable rows point at an adapter module that does not exist**
(`knowledge.consistency.assess`, `knowledge.json.fetch.external` → `runtime_native_action`).

---

## 3. Understand — before changing anything

| what an engineer does | measured | blocker |
|---|---|---|
| "Explain what this module does" | `FAIL__RAW_GOAL_COMPILATION_GAP` | no explanation row; the index lists definitions, it does not describe behaviour |
| "Trace how data flows from A into B" | `FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN` | `python.fault.provenance.interprocedural.value.v1` needs 7 inputs and is unreachable |
| "What breaks if I change this signature?" | ◐ change-impact works (test selection) | no type-level or call-site impact beyond tests |
| "Who last changed this line, and why?" | refused (`_PROVENANCE_RE` returns no argv by design) | `git blame` is verifiable and unbound |
| "Find every caller" | ✅ 19 s cold for `canonical/runtime`, 2.4 s warm | correct but the slowest measured read |

---

## 4. Change — one thing, then many things

**C1 · Four structural editors, all narrow.** `rename_symbol` (one file), `rename_parameter`,
`extract_function` (one stated statement), `crossfile_edit.choreograph` (needs an `edits_path` nothing
produces). Missing primitives: **inline, move, split, dedupe, extract constant, add type hints, add
docstrings, remove dead code** — 0 of 7 in the matrix, 1 of 7 in the probe.

**C2 · No multi-file change.** `Repair calc.py and util.py so the tests pass` → compilation gap. The
choreographer exists with 3 slots and no derivation for `edits_path`. This is the single highest-value
missing derivation in the repository.

**C3 · No repo-wide rename.** `Rename mul to multiply everywhere in <repo>` →
`PROMISED_SOURCE_CHANGE_NOT_APPLIED` (the machine catching itself, which is good, and still not the
work).

**C4 · No feature work.** `--verbose` flag, logging, error handling, "implement this issue end to
end": 0 of 4 probe, 0 of 7 matrix.

**C5 · Repair works only when a named test can prove it.** One bug and it writes `return a - b` →
`return a + b` and the suite goes green (measured twice). But when the named subject is innocent
("the behaviour of `mul()` regressed" against a tree whose bug is in `add`), the machine fixes `add`,
passes, and **never says that `mul` was not the problem**.

---

## 5. Tests — the first act of every change

| request | measured | blocker |
|---|---|---|
| write a unit test | `FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN` | `python.tests.generate.scaffold.v1` exists (3 slots), no derivation |
| write a regression test | `FAIL__LIVE_CONTROLLER_EXECUTION` | `python.patch.search.test_guided.ast.v1` is *selected* and then the controller fails |
| raise coverage to 90 % | `CAPABILITY_REFUSED_SUITE_RED` | the coverage gate refuses while the tree is red — the moment it is needed |
| mutation score | `CAPABILITY_REFUSED_BASE_WORLD_RED` | same gate on the mutation gate |
| which tests after a change | ✅ 82 ms | works |
| run the suite | ✅ 62 ms | works |

---

## 6. Debug — the rung senior engineers are paid for

`Why does this test fail?` → compilation gap. `Find the root cause` → refuses honestly now (it used to
fabricate a PASS; closed today). `Explain why the suite is red` → answered by *measuring* that it is
red. `Attach a debugger and show the failing frame` → composed step raised. `git bisect` → gap, though
`git` is installed and the whole bisect is `git bisect start/good/bad/run`.

---

## 7. Build, dependency, packaging, CI

Zero rows for wheel building, dependency add/upgrade, lockfiles, or CI setup. Measured:
`build the package` → composed step raised; `make test` → passes (it is a suite run); `add the
dependency requests` → raised; `upgrade setuptools and fix what breaks` → raised; `set up CI` →
`ROUTE_ADMISSION_REJECTED` on `software.hardcore.kernel.orchestrate.v1` (a nonsense destination).

---

## 8. Version control and delivery

0 of 6 git sentences; 0 of 5 matrix. Commit, branch, status, bisect, revert, changelog. The
acceptance layer **already verifies git read subcommands** (`status`, `diff`, `log`, `show`, `blame`,
`rev-list`, `merge-base`, …) by re-running them, and `_MUTATING_POSTCONDITIONS` already proves `rm`,
`mv`, `cp`, `tee`, `gzip`, `chmod`, `ruff format` and `sed` against the disk. The machinery is there;
only R1/R2 stand between it and the work. No PR, review, changelog or release capability at all.

---

## 9. Performance, concurrency, security

- **Performance:** `Profile the function total` → `chart.raster.axis_title_unit_binding.v1` (a chart
  row). `Make it faster` → gap. No benchmark, no regression gate reachable (`diff_perf_gate` needs 9
  inputs).
- **Concurrency:** no capability names races, deadlocks or thread safety. No test runner is asked to
  run repeatedly or under stress.
- **Security:** review works (bandit); **fixing** what it finds does not (`Find and fix the security
  issues` → `STATED_ANSWER_NOT_PROVIDED` — a review row cannot fix, correctly).

---

## 10. Polyglot

Python only. The JS suite refuses (`node --test` is installed), JS lint routes to a *Python* static
triage row, porting between languages is a gap. `code.multilanguage.parse.tree_sitter.v1` is routable
with **zero inputs**. Rust/Go/Java/C++: no rows and no toolchains.

---

## 11. Truth and the referee

- **T1 · A chain could certify "done" with no answer.** Closed today: the last step's verdict is the
  chain's verdict (`FAIL_CLOSED__COMPOSED_STEP_UNRESOLVED`).
- **T2 · A content request could delete the file.** Closed earlier: `Remove the dead code from X` no
  longer compiles to `rm X`.
- **T3 · Requests died on their own scratch.** Closed: spool artifacts are replaceable.
- **T4 · A "why" question is certified by a measurement.** Open.
- **T5 · Measurement refuses on a red tree.** Open (§5).
- **T6 · The referee is state-sensitive.** Four consecutive matrix runs gave 17/17/17 after one
  16 — a leftover spool artifact changed a verdict. A referee whose number depends on leftovers
  cannot certify a branch.
- **T7 · Core modules are red at HEAD** (2 modules, 18 test ids, proved pre-existing), and there is
  no CI gate.

---

## 12. Speed

| | |
|---|---|
| routing / refusals | p50 46–90 ms — already fast |
| answer that does work | 60 ms (suite) · 82 ms (impact) · 861 ms (typecheck) · 1.2–1.3 s (repair) · **19 s** (caller map on `canonical/runtime`, 2.4 s warm) |
| reuse between requests | none: 419 registry rows reloaded, inputs re-derived, plans rebuilt |
| parallelism | none: independent steps (parse, index, run) are serial |
| long horizon | no plan, no checkpoint, no resume — every request is one shot |

**The bottleneck is capability, not speed.** The machine is slow at engineering because it mostly
cannot do it; when it can, it answers in milliseconds.

---

## 13. Learning

40 of 46 advanced requests refuse, identically, every time. Nothing records that git, build, tests,
debugging and performance work are missing; nothing ranks what to build next from what was refused.

---

## 14. What already exists (the leverage table)

| mechanism | file | already solves | missing |
|---|---|---|---|
| read-command verification | `raw_goal_trace_acceptance_v1._READ_ONLY_COMMANDS` / `_READ_ONLY_SUBCOMMANDS` | re-runs and compares `cat`, `grep`, `sed`, **`git status/diff/log/show/blame`** | reachable rows for git prose |
| write postconditions | `_MUTATING_POSTCONDITIONS` | proves `rm`, `mv`, `cp`, `mkdir`, `touch`, `tee`, `gzip`, `chmod`, `sort`, **`ruff format`**, `sed` against disk | `git commit/branch`, build artefacts |
| command execution | `composer_route_v1` + `shell.command.run` | any stated argv, verified | selection (R1) and operand binding (R2) |
| structural editing | `bound_capabilities/python_refactor_*` | rename symbol/parameter, extract function | inline, move, split, dedupe, constants |
| patch driving | `software.repair.*` (11 rows) | one-bug repair with a named test | multi-file, test-guided authoring reachable |
| index | `python_source_symbol_index` | callers, impact, 18 s → 2.4 s warm | cross-language, incremental across requests |
| typed planning | `swe_typed_plan_v1` | derives 8–9 slots for rename/extract | `edits_path`, `source_root`, scaffold inputs |
| planners | 18 no-input supercomposers | exist, verified, unreachable | any declaration |

---

## 15. Fastest correct order

1. **R1** selection follows the command line (one block, measured).
2. **R2** operand ≠ destination in the binder (one rule; unblocks git, `-f` flags, every CLI path).
3. **R3/R4** a target must resolve; a `_post_git` postcondition turns created branches and commits
   into verified work.
4. **C2** one derivation for `crossfile_edit.choreograph.edits_path` → multi-file editing.
5. **§5** one derivation for `tests.generate.scaffold` and one controller fix for
   `patch.search.test_guided` → test authoring.
6. **§7/§8** rows for build and git write over installed binaries.
7. **R5/R6** derivations for the 18 no-input and 8 over-parameterised rows (`issue_to_pr`,
   `pr_realize`) — the highest ceiling in the repository.
8. **§6/§9** debugging and profiling behind the existing tree-sitter and `cProfile`/`coverage`.
9. **§10** JS/TS behind `code.multilanguage.parse.tree_sitter.v1`, then `node --test`.
10. **§12** registry reuse across requests, then plans and checkpoints for long work.

---

## 15b. Closed this round — the first two sockets (measured)

**R1 and R2 are closed for the git family, and the shape generalises.** Three changes, each read
off a measured failure, no new subsystem:

| change | incident it closes | after |
|---|---|---|
| a git READ row in the prose table (`status`, `log`, `diff`) | "What changed since the last commit?" compiled to nothing although the acceptance layer had always been able to verify git | **answered and certified**, 99–125 ms |
| a read command's answer lands in the machine's own scratch, and a path inside the argv is an OPERAND | `git -C <dir> status` executed correctly and reported `NO_OBSERVED_EFFECT`; with no path the slot was never bound (`OPEN__COMPOSER_SLOT_UNBOUND`) | answered; the operand is untouched |
| a QUESTION is not a promise to change | "What changed since the last commit?" ran the right command and was refused `NO_OBSERVED_EFFECT` because the noun "commit" matched the change-verb table | answered |
| a capture is a SUFFIX (12 000 chars), and the machine's own scratch lines are not the caller's world | a command that reproduced exactly was refused `COMMAND_OUTPUT_NOT_REPRODUCED` | reproduced, reported as such |

A directory that is not a repository is now **refused** rather than answered about the enclosing
repository — measured before the fix: `git log` inside a plain directory returned the parent
repository's history with `pass=True`.

Probe, with the three git questions added to the hardcore suite: **8 of 48 answered** (was 6 of 46),
p50 81 ms, 0 damaged trees. The 54-case matrix is unchanged at **17 / 0 / 37 / 0**, and the branch's
command-reading modules move from 18 to **17** red ids with **zero new failures**.

**Two measurement lessons recorded, because they cost time:** the referee's numbers depend on the
TOOLCHAIN being present (without `ruff`/`mypy`/`bandit`/`coverage` the same code scores 13 instead
of 17), and the working tree had been reset to the merge base with all earlier work present only as
uncommitted changes — so a "baseline" taken before re-anchoring to the branch tip compares against
the wrong tree. Both are the same class as T6: **a referee must assert its own preconditions.**

## 16. Reproduction

```bash
cd /home/user/brain
python3 execution_guard/swe_request_probe_v1.py                     # 28 sentences -> 6 answered, p50 46 ms
python3 execution_guard/swe_request_probe_v1.py --suite hardcore    # 46 requests  -> 6 answered, p50 90 ms
python3 execution_guard/swe_capability_matrix_v1.py                 # 54 cases     -> 17/0/37/0
python3 canonical/runtime/verify_brain_unified_model_v1.py          # 33/33
python3 -m pytest -q canonical/tests/test_a_content_request_never_deletes_the_file_v1.py \
                    canonical/tests/test_a_chain_that_came_back_unresolved_is_not_a_pass_v1.py \
                    canonical/tests/test_a_second_request_does_not_die_on_the_first_requests_scratch_v1.py
```

*Authority: NONE — sandbox measurement, not independent verification.*
