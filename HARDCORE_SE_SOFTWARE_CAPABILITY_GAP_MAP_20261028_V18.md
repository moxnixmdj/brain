# The complete problem inventory — hardcore software engineering

**2026-10-28 · V18 · measured on `arena/4ca3a720-brain` at `43eaba7` + this unit**

Supersedes `…GAP_MAP_20261028_V17.md`. V14 answered "what are all the problems" with three
probes. V15 keeps those and adds the four classes that only appear when you ask a different
question: **is the machine's capability real when the environment is clean, is the evidence it
cites checkable, can the instrument that measures it finish, and does the number it reports mean
what it says?**

Everything below is a row from a probe that can be re-run. Nothing is a wish list.

| instrument | what it can see | what it cannot |
|---|---|---|
| `execution_guard/hardcore_se_missing_verb_probe_v1.py` | 43 sentences an engineer says, through the real door (`solve()`), classified answered / honest / silent / wrong-capability | only the 43 acts it names |
| `execution_guard/live_solver_end_to_end_measurement_v1.reachability()` | 448 bound entries: can the compiler reach each one from a sentence built from its own vocabulary | self-measures with the capability's own words |
| `execution_guard/capability_evidence_probe_v1.py` **(new)** | for every entry claiming verification: does it execute on a task-shaped fixture, find the planted defect, and reproduce on an identical second world | only the capabilities whose task it knows how to build |
| `execution_guard/toolchain_preflight_v1.py` | which declared distributions are actually installed in THIS interpreter | only what the declaration names |
| the pinned guard suites | that a capability which exists still behaves | nothing about acts that do not exist |

---

## 1. The scoreboard

```
HARDCORE-SE MISSING-VERB PROBE (43 acts)          with the declared toolchain  |  bare interpreter
  ANSWERED_BY_OWNING_CAPABILITY      32                                     |   24   <-- see §9
  HONEST_REFUSAL                     11                                     |   11
  OWNED_BUT_FAILED                    0                                     |    8
  WRONG_TOOL                          0                                     |    0
  SILENT_REFUSAL                      0                                     |    0
  refusals that NAME the missing act  7/11

WHOLE-SURFACE REACHABILITY (452 entries = 158 registered + 294 receipt projections)
  REACHED_AND_BOUND                429      NOT_REACHABLE 11
  ROUTED_ELSEWHERE                   9      REACHED_BY_EXPLICIT_NAME 3

REGISTRY EVIDENCE (158 entries)                                              see §8
  a verification block whose pointers exist on disk            116
  a block that names NO file a reader could check               34
  a block whose pointers name files nobody wrote                 8

COMPILER SUITES                    25 failed / 108 passed   (unchanged by this unit)  see §7
PINNED PINS                        16/16 evidence, 8/8 route-identification,
                                   6/6 api-compatibility, 6/6 resource-leak, 9/9 move-function
```

Read the first block as a capability statement: **32 of the 43 acts a senior engineer performs on
any given day are performed by their owning capability, with the promised artifact on disk, and
11 are refused in words that name the act.** Zero are answered by a tool that had no business
answering them. That last number is what V14 bought, and it is the only one in this table that was
ever *worse than zero* — a confident wrong answer costs more than a refusal.

The second column is the honest caveat, and it is Class H (§9): the same 43 sentences against a
bare interpreter lose 8 acts outright, because the tools those capabilities call are installed
here and merely *declared* there. That is a law the door does not yet enforce.

---

## 2. Class A — ten acts this machine cannot perform at all

No capability in the 158-entry registry performs these; verified by searching every id, keyword,
`provides` and effect, not assumed. Each is a missing *tier* of engineering, not a missing
parameter.

| act | the sentence | what it needs |
|---|---|---|
| `ci_config` | "Write a continuous integration workflow" | a workflow emitter + the schemas it must satisfy |
| `memory_profile` | "Measure the memory usage" | `tracemalloc` is stdlib; nothing wraps it |
| `differential_test` | "Run a differential test against a reference" | two implementations, one input stream, a diff |
| `crash_repro` | "Reproduce the crash and shrink it" | delta-debugging — a loop over the existing test runner |
| `interactive_debug` | "Debug it with breakpoints" | `sys.settrace`/`bdb` are stdlib |
| `merge_conflict` | "Resolve the merge conflicts" | conflict parse + a resolution policy; the git tool already reads the state |
| `schema_migration` | "Write a schema migration" | a schema reader (sqlite reader exists) + a writer |
| `observability` | "Add logging and metrics" | an edit, and a logging/metrics model to edit *towards* |
| `retry_design` | "Make the network calls retry safely" | an edit, decomposable into existing refactor primitives |
| `docstrings` | "Write docstrings for the functions" | the only act here that needs judgement — and no AI model may participate in Brain-credited cognition, so it needs a structural lane, not a generator |

**Closed in this unit: `dependency_add` and `build_package`** (§13) — the two that stood between
this machine and using any project it is pointed at.

**Closed in this unit: `inline_function`** (§12) — the inverse of `extract_function`, and the only
refactor whose failure mode is silently wrong code, which is why it refuses more than it edits.

**Closed in this unit: `fuzz`** (§14) — the generator, the subprocess isolation, the shrinker and
the reproducer, over the function the sentence names.

**Ranked by capability gained per hour of work:** `crash_repro` (its hard half — reproduce, then
shrink — now exists inside `fuzz`), then `differential_test` (the same runner, two coordinates and
a comparison), then `memory_profile` (one stdlib wrapper), then `merge_conflict` +
`schema_migration`, then `docstrings` last.

---

## 3. Class B — CLOSED: sentences answered by a capability with no business answering

Nine of the 43 were answered by the wrong tool in V13. `WRONG_TOOL` is now **0**, closed by three
laws in V14 (§3 of that document): an artefact word is not evidence about the act; a chain is
accepted only when the sentence *identified* the token; the synthesis fallback answers only what a
format writer can actually do. Costs measured then: composer/synthesis suites 9 → 8 failing ids,
compiler suites unchanged, 8/8 new pins.

What remains is not the same class: **five refusals still SELECT a candidate that does not own the
act** (`interactive_debug`, `crash_repro`, `differential_test`, `retry_design`, `docstrings`) and
are then stopped by route admission (`R12`/`R14`). Nothing executes and the refusal names the word
it could not perform — but the door hands a wrong candidate to the guard instead of knowing at
selection time. **This is the single highest-value routing guard left.**

---

## 4. Class C — a refusal must name the act it cannot perform

`FAIL__RAW_GOAL_COMPILATION_GAP` used to report the closest capability and the unbound slot and
nothing a reader could act on. V14 made it append `NO_CAPABILITY_PERFORMS:<word>`, reusing
`_unheard_act_word` (already computed for R14). **9 of 15 refusals now name the act in the word a
user reads.**

The six that do not name it in `reason` all carry the name in `status`/`detail` instead
(`git_bisect`, `interactive_debug`, `crash_repro`, `differential_test`, `retry_design`,
`docstrings`). The gap is reporting plumbing, not knowledge: the word is computed and then dropped
on the `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` path.

---

## 5. Class D — twenty-two reachability defects

Each row is a capability that exists and cannot be reached from a sentence built out of its own
vocabulary; 426 of 448 entries bind.

**Not reachable (10).** `vcs.git.log.v1` (its sentence is claimed by commit), `vcs.git.blame.v1`
(two files named, one slot), `code.impact.tree_sitter.testselect.v1` and
`python.source.change_impact.testselect.v1` (`source_root` unbound on a sentence naming a file),
`chart.raster.curve_value_query.v1` + `chart.raster.direct_curve_label_family_rank.v1`
(`y_value: not_stated`), `json.file.write` (`output_path_equals_an_input_path`),
`text.file.write` (`NO_VERIFIED_CAPABILITY_MATCH: source_root`), `shell.command.run`
(`argv: not_stated` — a capability whose input is a command, not a sentence),
`python.refactor.move_function.v1` + `python.refactor.rename_symbol.v1` (their own vocabulary
generates a sentence that binds `source_paths` to zero files).

**Routed elsewhere (9).** `code.patch.tree_sitter.verify.v1`, `python.refactor.extract_function.v1`,
`python.refactor.rename_parameter.v1`, `python.refactor.change_signature.v1`,
`python.repo.pr_realize.v1`, `software.patch.synthesize.cegis.z3.v1`,
`plain_goal.bound_capability.grounding.stdlib`, `vcs.git.bisect.v1`, `vcs.git.branch_create.v1` —
each lost to a neighbour that shares its noun.

**By explicit name only (3).** `python.contract.issue_orchestration.fusion.v1`,
`python.pipeline.allowlist_gate.v1`, `python.refactor.test_scaffold.fusion.v1`.

This is the cheapest class in the document: routing and vocabulary, no new abilities. It must be
fixed **by law** — a capability must not lose its own sentence to a neighbour — and the two
reachability tests in §7 fail for exactly this reason.

---

## 6. Class E — capabilities that exist but cannot be asked

The interface is the wrong shape for a sentence: `vcs.git.bisect.v1` and `vcs.git.rebase.v1` want
an `argv`/`ref` a person does not say; `extract_function` wants a statement span
(`GOAL_STATED_ACT_INPUTS_UNBOUND … end_line`); `shell.command.run` wants a command line. The
capability works when called correctly (this unit proved it: §11), and a sentence reaches it only
if the sentence happens to state exactly that shape.

---

## 7. Class F — the 25 red compiler tests, now ATTRIBUTED

V13 called these "unexplained". They are now grouped by cause from their own failure bodies, and
the grouping is what makes them fixable:

| # | cause | tests | whose problem |
|---|---|---|---|
| 5 | multi-step DAG returns `FAIL__CAPABILITY_DAG_RESULT_INVALID` / `NO_OBSERVED_EFFECT` | f11 ×4, no-op repair | the DAG executor, not the compiler |
| 3 | a sentence that should stay open compiles anyway (`DID NOT RAISE`), or binds the wrong code | f23 ×2, f24 | over-eager compilation: the mirror of §3, on the ambiguity side |
| 3 | the test expects an older guard code (`R1_PATH_TOKENS_ONLY`, `R3_WEAK_EVIDENCE`) than the one now issued (`R12`, `R14`) | path-token, single-word | the guard improved; the assertion is stale |
| 2 | reachability counts | `…BY_PROSE_alone` ×1 (+1 body covering the same) | Class D, exactly |
| 2 | a quoted literal routes to the wrong capability | f25 | generic token scoring again |
| 2 | `source_root` binds the parser instead of the auditor; the two live doors disagree | source-root, both-doors | slot binding / door parity |
| 1 | `r9` selection rate 18 vs 22 | r9 | Class D, measured as a rate |
| 1 | named source unparseable on a real repair | no-op repair (also #1) | the repair lane |
| ~~1~~ | ~~no registry entry without proof~~ | — | **FIXED this unit (§8): 26 → 25** |

Two of the 25 are Class D wearing a test name, three are stale assertions about a guard that
improved, and the rest are real compiler defects in four families. That is a work queue, not a fog.

---

## 8. NEW Class G — evidence that names nothing

`test_no_registry_entry_is_left_without_proof` asserts that every entry carries a `verification`
block. It was **red**: 16 of 154 entries had none — and they were exactly the hardcore-software
lanes added through the adapter lanes (`quality_v1`, `toolchain_v1`, `vcs_git_v1`), i.e. the hole
sat where the work is.

The existing receipt lane could not close it. `capability_receipt_lane_v1.discover()` fills every
`${input.*}` with a content-addressed **sink path**, so an adapter whose declared input is a real
source tree fails closed on a path that does not exist: measured, **0 of 16 receipts issued**.

Three further measurements, once the hole was probed properly:

* **34 entries carry a block that names no file at all** — a `verification` dict with no
  `receipt_path` and no `state_path` (`shell.command.run`, `text.file.write`, `json.query.jq`,
  `python.fault.provenance.interprocedural.value.v1`, …). A block a reader cannot follow is the
  same assertion as a status string.
* **33 pointers named files that do not exist**, over 19 capabilities. Twenty-two of them were the
  git surface (11 capabilities × receipt + state) and `move_function`: probes that measured
  everything and wrote nothing.
* the one metric in this class that was actively false: `ruff_complexity` reported
  **`max_complexity: 0`** on a tree whose most complex function is 5 — `0` is impossible for any
  function with a branch, and it meant "nothing measured". Fixed: `null` plus `measurement_limit`.

**What this unit did about it.**

`execution_guard/capability_evidence_probe_v1.py` builds task-shaped fixtures *outside* the
repository — a python package that leaks a handle, duplicates a block, carries no licence and has a
failing test; a git repository with a known-good commit, a known-bad commit and an upstream — then
runs each capability on it **twice, from byte-identical worlds**, and records:

* `EXECUTED` — the adapter really returned a mapping;
* `reproduced` — the findings of the two runs are equal, after dropping what belongs to the run
  (paths, clocks, transcripts, commit ids) and keeping what belongs to the work;
* `planted_defect_found` — an oracle predicate over the capability's own result, because *running
  is not finding*: a leak analyser reporting "0 leaks" on a file with an unclosed `open()` has
  executed successfully and told a lie.

Measured: **16/16 executed, 16/16 reproduced, 13/13 planted defects found, 0 false claims.**
The git-surface probe now writes the receipt its 11 entries have always cited (12/12 selected,
12/12 pass, 12/12 artifact, 12/12 repository actually changed). Evidence pointers: **33 dangling →
8**, pinned by name so a new one fails. Registry: 154/154 entries carry a block; compiler suites
**25 failed / 108 passed** with the failure list otherwise byte-identical.

---

## 9. NEW Class H — the machine's capability is a function of its environment

The same commit, the same code, twice:

```
with the declared toolchain      28 answered /  0 owned-but-failed
bare interpreter                 20 answered /  8 owned-but-failed
```

The eight are `coverage_measure`, `complexity_metric`, `dead_code`, `lint`, `format`, `type_check`,
`async_audit`, `exception_audit` — the entire analysis tier. The adapters do not degrade either:
they exit their process, so the caller is told a capability is **BROKEN** when it is merely
**ABSENT**, which is the difference between debugging code that is fine and installing a package.

`TOOLCHAIN_DECLARATION_V1.json` + `execution_guard/toolchain_preflight_v1.py --bootstrap` now
declare, check and install the eight distributions (`ruff`, `bandit`, `mypy`, `coverage`,
`pytest`, `tree-sitter`, `z3-solver`, `crosshair-tool`): measured **8 of 8 present** after
bootstrap. What is still missing is not the fix but the **enforcement**: nothing in the door
refuses a capability whose declared tool is absent with a status that says "install this", and
nothing in CI installs from the declaration.

---

## 10. NEW Class I — the instrument that sees routing regressions could not finish

`test_every_capability_is_reachable_from_one_sentence_by_prose_or_by_name` ran past a 90-second
test timeout, and the suite ran past **15 minutes with no verdict at all**. The stack was the same
frame every time: `world_binding_v1._world_path_for` re-`sorted()` the whole world index and
re-matched every entry against the kind's suffixes, once per slot ask.

15,181 files, 9,458 of them JSON. The index itself was already cached; the *filtering* was not.

Fixed with a per-kind cache: **66 s for that test, verdict delivered** (a real failure — Class D,
§5). This is the class that hides every other class: a gate that cannot finish reports nothing, and
nothing looks green.

---

## 11. What this unit changed, each with its measurement

| change | before | after |
|---|---|---|
| `capability_evidence_probe_v1.py` (new): task-shaped fixtures, twofold observation, planted-defect oracle | 0 of 16 entries could be evidenced by the generic lane | 16/16 executed, 16/16 reproduced, 13/13 defects found |
| registry evidence blocks | 16 entries with none, 33 dangling pointers | 154/154 with a block, 8 dangling (pinned by name) |
| `hardcore_se_git_surface_v1.py` writes the receipt its 11 entries cite | pointer to a file nobody wrote | 12/12 selected / pass / artifact / effect, receipt on disk |
| `world_binding_v1` per-kind index cache | one test >90 s, suite >15 min with no verdict | that test 66 s, verdict delivered |
| `ruff_complexity.max_complexity` | `0` on a tree whose worst function is 5 | `null` + `max_complexity_measured` + `measurement_limit` |
| evidence pins | — | 6/6, incl. "a new dangling pointer fails" |
| `packaging_v1.py` (new, previous unit) | 2 acts undeliverable by any of 154 entries | both answered, both evidenced, pinned (10/10) |
| probe fixture | a source tree only; packaging rows measured the fixture (`NO_MANIFEST`) | a *project*: manifest + build-system |
| evidence probe "reproduction" | second run re-used the first run's mutated world, so a mutating verb "failed" to reproduce | every observation is a copy of a pristine template |
| registry evidence blocks with a real pointer | 112 / 154 | 115 / 157 |
| **this unit** — `python_refactor_inline_function.py` (new) | `inline_function` undeliverable by any of 156 entries | answered through the door, evidenced, pinned (11/11) |
| the fixture's `sub` had no caller in the clean world | the row refused `INLINE_NO_CALL_SITES` — a fact about the fixture | the refactor rows get a working tree (`_DIRTY_WORLD_ACTS`) |
| evidence probe's world | minted in `/tmp`, so every path-confining verb refused `PATH_ESCAPE` | minted under `canonical/astra_runtime/tmp`, like the missing-verb probe |
| a refusal inside an adapter | `SystemExit` — it took the caller with it (`CAPABILITY_EXITED_PROCESS`, reason lost) | a normal exception: the door now reports the reason it was given |
| **this unit** — `dynamic_probe_v1.py` (new) | `fuzz` undeliverable by any of 157 entries | answered through the door, evidenced, pinned (11/11) |
| the door's binding of "fuzz the function X in <file>" | a directory + a name, no module | the module that DEFINES the name is resolved; two definitions refuse `MODULE_AMBIGUOUS` |

Nothing was promoted. Every receipt written here records `independent_verifier: null` and
`producer_independent: false`: one identity ran its own work, and that is exactly what the evidence
says.

---

## 12. Closed in the previous unit — `dependency_add` and `build_package`

The two acts the inventory ranked #2 and #3, and neither needed a new tool.

**`dependency_add`** (`python.packaging.dependency_add.v1`) splices one line into the project's own
manifest — `[project].dependencies` in `pyproject.toml`, or `requirements*.txt` — and verifies the
edit **by re-reading the file**: it still parses with `tomllib`, the dependency appears exactly
once, and nothing outside the dependency array moved. The manifest is never re-serialised, which is
the same law the bound registry obeys. Asking twice is answered (`already_present: true`), not
applied twice. A value that starts an option or carries a second line is refused
(`DEPENDENCY_NOT_A_REQUIREMENT`), because a manifest is code an installer will execute.

**`build_package`** (`python.packaging.build_package.v1`) builds with `pip wheel` — the tool that
builds wheels, already installed, 1.5 s on a small project — and verifies the artifact **by reading
it**: a wheel is a zip with `.dist-info/METADATA` and `RECORD`, and name, version, `Requires-Python`,
declared requirements and top-level modules are read back out of it. A build that produced a file
with no metadata has not built the package it claims to.

Both reuse rather than invent: the manifest parse is the same one `environment_fit_v1` already uses
to decide what to install, `pip` is the builder, and the artifact law (digest, verification, FAIL
artifact on refusal) is `quality_v1`'s, imported rather than reimplemented.

Measured, through the real door (`solve()`), 2.1 s for both rows:

```
dependency_add   ANSWERED_BY_OWNING_CAPABILITY  python.packaging.dependency_add.v1   PASS
build_package    ANSWERED_BY_OWNING_CAPABILITY  python.packaging.build_package.v1    PASS
```

and evidenced like every other capability: `EXECUTED`, `reproduced` on a byte-identical second
world, and the planted defect found (the new dependency is in the manifest; the wheel's own
METADATA names `demo-pkg 0.1.0`). Registry 154 → 156. Pins 10/10.

The one thing this does **not** do is install what it declares. `environment_fit_v1.satisfy` is
still the step that puts a declared dependency into the interpreter, and wiring that so the door
installs instead of refusing is §15 row 5.

---

## 13. Closed in the previous unit — `inline_function`

`python.refactor.inline_function.v1`, the exact inverse of the verb that already shipped. Its
machinery was free (the span/marker law, the path law, the test referee, the def-lookup); what
cost thought is that **inlining is the only refactor here whose failure is silently wrong code**:
the module still parses, the call is gone, and the answer changed. So the verb refuses more than
it edits, and every refusal names its reason.

The five laws it holds:

1. **evaluated once.** Each argument becomes a binding at the site (`a = <expr>`), so an argument
   expression runs once and a body that mutates its parameter is still correct.
2. **never clobbers the caller.** A parameter name already live at the site is renamed `_inl_<name>`,
   and the returned expression is renamed *with it* — the expression was written in the callee's
   scope, and copying it unchanged reads whatever the caller happens to have under that name.
3. **the definition dies only when nothing names it.** A test file that does
   `from pkg.calc import sub` keeps it (`external_references`), and the suite stays green.
4. **a branching return is refused, not spliced.** Turning `if v > hi: return hi` into a statement
   list needs a flag and an indent level that the original did not have.
5. **a red suite restores every byte**, and no named suite is `PASS_BLIND` / `verified: false`.

Three of those laws were **written because the measurement found the bug**, not before it:

| defect | what it looked like | what caught it |
|---|---|---|
| the body's own `return` was copied *and* re-emitted | `return n * 2` in the middle of a loop body; the code ran and the answer was wrong | `PASS_BLIND` on the fixture, then a wrong number from `caller()` |
| the returned expression was copied from the callee's scope | `t += n * 2` where `n` was the caller's loop variable; right by coincidence | the rename that produced a dead `_inl_n` binding |
| the rename ran over the whole body including the dropped `return` | a stray `_inl_n` line above the call | `INLINE_BODY_DEDENT_UNSAFE` |

Through the real door (`solve()`), and evidenced like every other capability
(`EXECUTED`, reproduced on a byte-identical second world, planted defect found):

```
inline_function   ANSWERED_BY_OWNING_CAPABILITY  python.refactor.inline_function.v1  PASS
```

Registry 156 → 157; pins 11/11. Whole-surface reachability stays 428 of 451: the new verb is
`NOT_REACHABLE` from a keyword-synthesised sentence — exactly the state its sibling `move_function`
is in, and exactly Class D (§5). Through the door a sentence a person would actually write
("Inline the function sub in …") reaches it; the synthesised keyword soup does not. That is the
routability law's problem, not this verb's, and pretending otherwise by adding keywords would be
the same defect wearing a fix's clothes.

The one thing the probe had to be told: a fixture whose suite *contains a planted defect* cannot referee an edit that
must stay green — naming it made the verb refuse `TESTS_RED_AFTER_EDIT`, which is the referee
working. That row is evidenced `PASS_BLIND` and says so.

---

## 14. Closed in this unit — `fuzz`

`python.dynamic.fuzz.v1`. The piece that makes it a capability rather than a loop is **process
isolation**: every case runs in a child interpreter with a wall-clock cap, so a segfault, a
`sys.exit`, a `MemoryError` or a hang is an *outcome* (`crashed`, `signaled`, `timeout`) instead
of the run that was measuring it. The second piece is the shrink: each argument is reduced
greedily against a pool of strictly smaller candidates, and a reduction is kept only while it
fails the **same way**.

Measured on a fixture with a planted divide-by-zero and a planted hang:

```
buggy(a: int, b: int)   -> 16 cases, 2 failures, minimal [0, 0], mode raised, 0.42 s
hangs(n: int)           ->  3 cases, 1 failure,  minimal [1],    mode timeout, 2.07 s
safe_div                -> 16 cases, 0 failures                     0.39 s
```

Two of its laws were written because the first run misbehaved:

| what happened | what it was | the law now |
|---|---|---|
| the run never returned, parked inside the child's `communicate()` | the shrink accepted `0` as a reduction of `0` — `candidate == 0` in the filter — so it looped on the case it started with | candidates must be **strictly** smaller, and the loop is bounded |
| the reproducer said `from pkg.c import buggy` | the module had already been dotted, and the reproducer stripped `.py` a second time | the reproducer takes the dotted module as given |

And one thing the door hid: the sentence says *"fuzz the function add in …/pkg/calc.py"*, but the
compiler binds a **directory** and a **function name**, not a file. Resolving that by choosing the
module that *defines* the name is a fact about the tree — so it is done, and when two files define
it the verb refuses `MODULE_AMBIGUOUS` with their names instead of guessing.

```
fuzz   ANSWERED_BY_OWNING_CAPABILITY  python.dynamic.fuzz.v1   PASS   (through solve())
```

Registry 157 → 158, pins 11/11, evidenced (`EXECUTED`, reproduced, planted defect found:
`minimal_case == [0, 0]`, `failure_mode == raised`). Reachability 428 → 429 of 452 — this one *is*
reachable from a synthesised keyword sentence, which is why the number moved.

---

## 15. The plan this implies

| # | work | class | why now |
|---|---|---|---|
| 1 | noun-side **selection** guard | B residual | five refusals still hand a wrong candidate to admission; nothing executes, but the door should know at selection time |
| 2 | the routability **law** (one row → one rule) | D | 22 rows, two failing tests and the `r9` rate are the same defect seen three ways |
| 3 | install-or-refuse at the door | H | the toolchain is declared; nothing enforces it, so 8 capabilities vanish silently on a clean interpreter |
| 4 | three stale guard-code assertions | F | the guard improved and the test did not; 3 of 25 red rows for free |
| 5 | `crash_repro` + `differential_test` | A | the runner, the shrinker and the reproducer now exist inside `fuzz`; these add a stated case and a second coordinate |
| 6 | the four compiler defect families (DAG result, DID NOT RAISE, quoted literal, door parity) | F | each is a law with more than one failing row behind it |
| 7 | 34 evidence blocks that name no file | G | each needs the lane that measured it to write one line |
| 8 | `docstrings` | A | last on purpose: the only act here that needs judgement, and no model may supply it |

Two rules for all of it, unchanged: **reuse before synthesis**, and **measure, never assert** —
every row above is a re-runnable probe, and a red row is still not an authority until the owner
says so.
