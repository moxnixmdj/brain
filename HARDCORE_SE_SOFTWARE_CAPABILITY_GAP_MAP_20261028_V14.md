# The complete problem inventory — hardcore software engineering

**2026-10-28 · V14 · measured on `arena/4ca3a720-brain` at `4fcbb0a`**

This supersedes `HARDCORE_SE_PROBLEM_INVENTORY_20261028_V11.md`. V11 answered "what is
blocking one verb". This answers the question actually asked: **what are all the
problems**, across the whole machine, measured rather than asserted. V14 closes the one
class V13 called dangerous -- sentences answered by a capability that had no business
answering them -- and adds a verb; §11 says exactly what moved.

Nothing here is a wish list. Every row below is a row from a probe that can be re-run:

| instrument | what it can see | what it cannot |
|---|---|---|
| `execution_guard/hardcore_se_missing_verb_probe_v1.py` | 43 sentences a working engineer says, run through the real door (`solve()`), classified as answered / honest / silent / wrong-capability | only the 43 acts it names |
| `execution_guard/live_solver_end_to_end_measurement_v1.reachability()` | 445 bound capabilities: can the front compiler reach each one from a sentence built out of its own vocabulary | self-measures with the capability's own words, so it is generous |
| the pinned guard suites (`git_surface`, `hardcore_se_reachability`, `adapter_failure_law`, per-adapter pins) | that a capability which exists still behaves | nothing about acts that do not exist |

The first two disagree on purpose, and the disagreement is the most useful number here:
**the surface is 424/445 reachable by its own vocabulary while 16 of 43 real engineering
sentences are answered by nothing, and 9 more by the wrong thing.**

---

## 1. The scoreboard

```
HARDCORE-SE MISSING-VERB PROBE (43 acts)
  ANSWERED_BY_OWNING_CAPABILITY   28      (V13: 27, V12: 25)
  HONEST_REFUSAL                  15      "I cannot do this", said in words, before doing anything
  WRONG_TOOL                       0      (V13: 9 -- class B is closed, see §3)
  SILENT_REFUSAL                   0
  OWNED_BUT_FAILED                 0
  of the 15 refusals, 9 NAME the missing act ("NO_CAPABILITY_PERFORMS:fuzz")

WHOLE-SURFACE REACHABILITY (448 capabilities: 154 registered + 294 receipt projections)
  REACHED_AND_BOUND              426
  NOT_REACHABLE                   10      a sentence in its own vocabulary cannot bind it
  ROUTED_ELSEWHERE                 9      another capability claims that sentence
  REACHED_BY_EXPLICIT_NAME         3      only reachable if the caller names the id

COMPILER SUITES                 26 failed / 107 passed   (see §7; unchanged, no new node id)
PINNED GUARDS             all green: 20/20 refactor pins, 63/63 refactor+flake suites,
                                    22/22 hardcore reachability, 12/12 git surface
                                    (+10/10 refusals), 18/18 adapter-failure-typed
```

Read the first block as a capability statement, not a bug count: **28 of the 43 acts a
senior software engineer performs on any given day are performed, correctly, by their
owning capability, with the promised artifact on disk.** Of the other 15, none has an
owning capability anywhere in this machine (§2) -- and, as of V14, every one of them is
REFUSED before anything executes, which is the difference between a machine that cannot
fuzz and a machine that quietly writes a JSON file about fuzzing. Nothing on this surface
fails without saying why.

### How a verdict is decided

A refusal is honest only if the machine says so. `PROMISED_ARTIFACT_MISSING` and
`CAPABILITY_EXITED_PROCESS` are **closed** statuses that arrive *after* a capability was
admitted and executed; the previous revision of the probe counted them as honest refusals
because the status starts with `FAIL_CLOSED`. It now separates "declined before doing
anything" from "ran the wrong thing and closed afterwards", which moved the headline from
"18 honest refusals" to **9 honest, 7 wrong-tool, 1 silent**. That correction is pinned in
`classify()` with the measurement in its docstring.

---

## 2. Class A — fourteen acts this machine cannot perform at all

Three rows that stood here in V13 are now capabilities and have been removed from the
table: `move_function` (§10), `resource_leak` (§10) and `api_compatibility` (§11). What is
left is the honest remainder.

No capability in the 154-entry registry performs these. Verified by searching every id,
keyword, provides and effect, not assumed. Each is a *missing tier* of engineering, not a
missing parameter.

| act | the sentence | why it matters |
|---|---|---|
| `inline_function` | "Inline the function `sub`" | the inverse of extract; needs call-site argument capture and return-value fusion |
| `docstrings` | "Write docstrings for the functions in …" | the only act in this table that requires judgement — it is the one that legitimately needs a synthesis lane, not an adapter |
| `differential_test` | "Run a differential test … against a reference" | mechanical: two implementations, one input stream, diff the results |
| `fuzz` | "Fuzz the function `add`" | needs a generator + a crash oracle; `atheris` is absent, but a stdlib random+subprocess harness is not |
| `memory_profile` | "Measure the memory usage of the program" | `tracemalloc` is stdlib; nothing wraps it |
| `retry_design` | "Make the network calls … retry safely" | an edit + policy, decomposes into existing refactor primitives |
| `observability` | "Add logging and metrics to …" | an edit; needs a logging/metrics model to edit *towards* |
| `schema_migration` | "Write a schema migration for the database" | needs a schema reader (sqlite reader exists) + a writer |
| `dependency_add` | "Add the dependency `requests` to the project" | prerequisite for everything `pypi`-sourced; `pyproject`/`requirements` edit + pin resolution |
| `build_package` | "Build a wheel for the project" | no build lane at all: `python -m build` is not a bound system tool |
| `ci_config` | "Write a continuous integration workflow for …" | 0 of 43 rows produced less information than this one (see §4) |
| `merge_conflict` | "Resolve the merge conflicts in …" | needs conflict parse + a resolution policy; `git` bound tool already reads the state |
| `crash_repro` | "Reproduce the crash … and shrink it to a minimal case" | delta-debugging is a loop over an existing test runner |
| `interactive_debug` | "Debug the function `add` … with breakpoints" | a debugger protocol: `sys.settrace`/`bdb` are stdlib |

Ordered by capability gained per engineering hour, the first two —
**`dependency_add`** and **`build_package`** — are reuse jobs over machinery that already
exists (a `pyproject` parse and a `python -m build` subprocess, both absent today).
`docstrings` is last on purpose: it is the only one that needs a model, and no model may
participate in Brain-credited cognition.

---

## 3. Class B — CLOSED: nine sentences answered by a capability with no business answering

V13 listed seven acts that were ADMITTED, run, and stopped only by a promised-artifact
check. Two more joined them when the binder learnt to bind `target_module`
(`docstrings`, `inline_function`). This is the class that matters most, because it is the
only one that produces work that LOOKS right: a capability the sentence never asked for
runs to completion and the door reports what it did.

**What was actually happening.** Not one defect per row -- one defect, five times.

`composer_route_v1.candidate_tokens` scores a capability token by the words it can match,
and every request in this repository ends *"... and report it to `<O>`"*. A capability
whose keywords contain `report` therefore matches EVERY such sentence, and when nothing
else scores above zero it wins. Measured: "Fuzz the function add in `calc.py` ...",
"Build a wheel for the project ...", "Add the dependency requests ...", "Add logging and
metrics ..." and "Inline the function `sub` ..." were each routed to
`document.convert.markdown_pdf.pandoc_weasyprint` on the single word `report`. The machine
converted a document nobody asked for.

Underneath that, a second and worse defect. When no token produced a chain, `route()`
fell through to `program_synthesis_v1.synthesize_or_recall`, which answers from memory --
and `remember()` keyed the learned program on the **output file suffix alone**. The store
held exactly one program per file extension, so any sentence ending in `.json` recalled
the remembered `json_dump` and returned

```
pass: true, from_memory: true, status: PASS__RECALLED_VERIFIED_PROGRAM,
authority: PREVIOUSLY_SYNTHESISED_AND_VERIFIED
```

for a request to fuzz a function. A verified program, named for a job it cannot do, with
the word VERIFIED on it. That is the worst kind of answer this machine can give, and it
was being given for five of the nine rows.

**The three laws that closed it.**

1. *An artefact word is not evidence about the act.* `_NO_EVIDENCE_WORDS` in
   `composer_route_v1` (the same distinction `goal_compiler.GENERIC_MATCH_TOKENS` already
   draws for the front compiler). "report", "output", "file", "document" say where the
   answer goes. They may never be the only reason a token is chosen.
2. *A chain is accepted only when the sentence IDENTIFIED the token.* `is_identified()`
   requires one of: the sentence fills the token's declared contract; or -- when the
   sentence's own verb names a specific act -- the token claims that verb; or -- when the
   verb is a generic request verb (`write`, `add`, `build`, `run`) -- at least one content
   word survives as evidence after artefact words, medium words (`function`, `project`),
   the request verb itself and identifiers/version stamps (`v1`, `py`, `auto`) are removed.
   A reachable chain is not an answer: `shell.command.run` is reachable from any sentence
   containing the word "run".
3. *The synthesis fallback answers only what it can do.* `program_synthesis_v1` writes a
   payload in a named format and proves the format -- nothing in it fuzzes, builds, inlines
   or documents. `claims_the_request()` admits it only for a format write (every content
   word is a format-write verb or a format/`payload object), and `recall()` now requires
   the remembered goal to name the current one. Anything else returns
   `REFUSED__NOT_A_FORMAT_WRITE:SYNTHESIS_CANNOT_PERFORM:<the words that made it
   impossible>`.

| act | V13 | V14 |
|---|---|---|
| `fuzz` | pandoc, executed | `REFUSED`, names `fuzz` |
| `build_package` | pandoc, executed | `REFUSED`, names `build` |
| `dependency_add` | pandoc, executed | `REFUSED` |
| `observability` | pandoc, executed | `REFUSED` |
| `inline_function` | pandoc, executed | `REFUSED` |
| `schema_migration` | `text.file.write`, executed | `REFUSED` |
| `docstrings` | `python.source.audit.ast`, executed | `REFUSED`, names `docstrings` |
| `merge_conflict` | `python.quality.changelog.v1`, executed | `REFUSED` |
| `memory_profile` | `python.quality.changelog.v1`, executed | `REFUSED`, names `memory` |

**Measured cost of the laws.** `test_composer_route_v1` + `test_program_synthesis_v1`:
9 failing node ids before, 8 after (one fixed, none broken); the new pins in
`test_a_route_must_be_identified_not_merely_reachable_v1.py` are 8/8 green. The three compiler suites:
26 failed / 107 passed before, unchanged after, failing node ids identical (§7).

**What is still imperfect, and it is not the same class.** Five refusals
(`interactive_debug`, `crash_repro`, `differential_test`, `retry_design`, `docstrings`)
still SELECT a capability that does not own the act and are then refused by route
admission (`R12`/`R14`). Nothing executes, no artifact is written, and the refusal names
the word it could not perform -- but the door still hands a wrong candidate to the guard
instead of knowing at selection time. §9 keeps that on the list.

## 4. Class C — the diagnosis that was written and then dropped (fixed here)

`ci_config` returned `FAIL__RAW_GOAL_COMPILATION_GAP` with `reason: ""`: the only row of
43 with no diagnosis at all. The compiler had a code; `solve()` put it under
`compiler_code`/`compiler_detail` while every other refusal in the door puts its diagnosis
under `reason`, so a caller reading `reason` saw nothing. Copying the code the compiler
already wrote into the field the reader reads is not new computation — it is putting the
diagnosis where the reader looks.

Measured after: `GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH:…:diff_path:0_type_compatible_existing_files_named`.
Still not a good answer (it names the nearest capability it could not match, not the act
the machine cannot perform), but it is now an answer, and the row moved from
`SILENT_REFUSAL` to `HONEST_REFUSAL`. **Zero of 43 rows now fail without saying why.**

The same shape appeared twice in the tooling around this class: a capability raising
`SystemExit` surfaced as `FAIL_CLOSED__CAPABILITY_EXITED_PROCESS` with an empty `reason`,
and a probe row whose fixture lacked the file its sentence named was read as a capability
defect. Both are the same lesson the door learned here — *a diagnosis that is not where
the reader looks is not a diagnosis*.

## 5. Class D — eighteen reachability defects

Each row: a capability that exists and cannot be reached from its own vocabulary.
Re-measured at V14 over the 448 entries the audit now enumerates (three capabilities were
added since V13): **10 not reachable, 9 routed elsewhere, 3 by explicit name, 426 reached
and bound.** The three new capabilities are all reachable, so the proportion improved
without a single row of this class being fixed -- which is exactly why it must be fixed by
law and not one row at a time.

**Not reachable (8)** — the sentence its own keywords generate cannot bind its inputs:

| capability | cause |
|---|---|
| `vcs.git.log.v1` | `GOAL_STATED_ACT_INPUTS_UNBOUND … vcs.git.commit.v1:message:not_stated` — the log sentence is claimed by commit and never reaches log |
| `vcs.git.blame.v1` | `path: 2_existing_files_named` — the generated sentence names two files, and blame takes one |
| `code.impact.tree_sitter.testselect.v1` | `source_root` unbound on a sentence naming a file |
| `chart.raster.curve_value_query.v1`, `chart.raster.direct_curve_label_family_rank.v1` | `y_value: not_stated` — the curve query swallows the label-rank sentence |
| `json.file.write` | `output_path_equals_an_input_path` |
| `text.file.write` | `GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH: source_root` |
| `shell.command.run` | `argv: not_stated` — a capability whose only input is a program, not a sentence |

**Routed elsewhere (10)** — another capability claims the sentence:

| capability | claimed by | verdict |
|---|---|---|
| `python.refactor.rename_symbol.v1` | `python.source.symbols.index.ast` | fixed in the *sentence* direction this commit (keywords); the probe shows it now wins 22 to 11 |
| `python.refactor.rename_parameter.v1` | `python.source.symbols.index.ast` | same |
| `python.refactor.extract_function.v1` | `python.source.symbols.index.ast` | keyword fix lands it at 26 to 5, but it still loses the *compile* to `F24_UNSTATED_CANDIDATE_SKIPPED` (see §6) |
| `python.refactor.change_signature.v1` | `python.source.change_impact.testselect.v1` | keyword fix needed, same pattern |
| `code.patch.tree_sitter.verify.v1` | `code.impact.tree_sitter.testselect.v1` | mirror-image naming |
| `vcs.git.bisect.v1` | `vcs.git.log.v1` | |
| `vcs.git.branch_create.v1` | `vcs.git.branch_list.v1` | create and list are neighbours by noun, not by act |
| `python.repo.pr_realize.v1` | `vcs.git.branch_list.v1` | |
| `software.patch.synthesize.cegis.z3.v1` | `software.repair.loop.cegis_hypothesis.v1` | |
| `plain_goal.bound_capability.grounding.stdlib` | `…grounding.verify.stdlib` | |

**Reached only by explicit name (3)** — `python.contract.issue_orchestration.fusion.v1`,
`python.pipeline.allowlist_gate.v1`, `python.refactor.test_scaffold.fusion.v1`. A calling
agent that knows the id can use them; a user sentence never will. That is acceptable for a
gate and unacceptable for a refactor verb.

This class is the cheapest in the whole document: it is routing and vocabulary, no new
abilities, and each row is a two-line registry change with a measurement attached.

---

## 6. Class E — capabilities that exist but cannot be asked

The interface is the wrong shape for a sentence. These are not routing bugs; the input
the adapter consumes is not the input a person gives.

| capability | declared input | what a person says instead |
|---|---|---|
| `vcs.git.bisect.v1` | `argv` — an unstated command line | "bisect to find the first bad commit" |
| `python.refactor.extract_function.v1` | `start_line` + `end_line` + `new_name` | "extract the statement `return n + 1` into a function" |
| `vcs.git.blame.v1` | `worktree_path` **and** `path`, plus a directory slot that binds a file | "blame the lines of `pkg/calc.py`" |
| `shell.command.run` | `argv` | "run the tests" |

`extract_function` is the sharpest case: the statement *is* stated, and locating its line
span is a parse, not a guess — the module can bind `start_line`/`end_line` by finding the
unique statement whose source text equals the stated text. Only `new_name` is genuinely
absent, and one absent input should not make a verb unreachable.

---

## 7. Class F — the 26 unexplained test failures

`test_goal_front_compiler_v1.py` + `test_goal_compiler_world_binding_v1.py` +
`test_live_brain_route_admission_v1.py` fail 26 tests and pass 107. Verified against a
clean worktree at the parent commit `62be529`: **the 26 failing node ids are identical**,
so none of this commit's four fixes is implicated. **They have never been attributed to a cause.** They are
listed here as a problem in their own right because a red suite that nobody reads is how
a machine loses the ability to tell a regression from a baseline. Cheapest path: take the
26 ids, group them by the guard each one exercises, and either fix the guard or re-pin
the expectation with the measurement in the docstring — do not run the suite green by
weakening it.

---

## 8. What V13's own commit fixed, and the measurement for each

Four defects, all in the hardcore-software lane, all measured before and after.

1. **The refactor family was unreachable.** `run_tests` raised
   `GOAL_INPUT_BINDING_REQUIRED`; every refactor adapter treats an absent suite as
   `PASS_BLIND`, so a verification slot was being treated as a premise. A verification
   slot may be empty.
2. **The kernel refused source type `runtime`.** Six capabilities declare it — all four
   refactor verbs, `diff_mutation_gate`, `flake_detect` — so all six were dead on arrival
   at the kernel and worked only on the front layer's first-try local path. `runtime` and
   `brain_owned_deterministic` now resolve to "the adapter file is the dependency".
3. **Three refactor verbs lost selection to generic analyzers** because their keyword
   sets lacked the words a person uses for the edit (function, method, class, variable,
   statement, block, argument, kwarg). Post-fix margins: rename_symbol 22–11,
   extract_function 26–5.
4. **Module identity was a dotted string, not a file.** With `source_root=<pkg>` and
   `module=core.py`, `from pkg.core import top` was left untouched while the artifact
   reported `complete: true` and no unknown site; only the post-edit test run saw it.
   `_module_aliases` now accepts every spelling that provably resolves to this exact
   file, and only when that spelling denotes no other file. Measured end to end:
   rename over a real package layout → 3 edits in 2 files, tests green, `gate: PASS`,
   `verified: true`, through `solve()`.

5. **A diagnosis was written and then dropped.** `FAIL__RAW_GOAL_COMPILATION_GAP`
   carried its code under `compiler_code`, not `reason`, so `ci_config` — the one row of
   43 with no diagnosis at all — was silent. It now says
   `GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH:…`. Zero of 43 rows fail silently now.

Pins added: 2 (package-root source root; ambiguous name never matched). The probe itself
is now a committed instrument, and it changed two of its own conclusions while being
built — the fixture must be pristine per act, and a wrong-tool failure is not a refusal.

---

## 9. The plan this implies

Rows 1-5 of V13's plan are done (§10, §11). What the measurements rank now:

| # | work | class | why now |
|---|---|---|---|
| 1 | noun-side SELECTION guard (§3, last paragraph) | B | five refusals still hand a wrong candidate to the admission guard; nothing executes, but the door should know at selection time |
| 2 | `dependency_add` + `build_package` | A | both are reuse: a `pyproject`/`requirements` edit and a `python -m build` subprocess; they unblock the whole pypi/build lane |
| 3 | `inline_function` | A | the exact inverse of `extract_function`, which now ships and whose span machinery is the same |
| 4 | `extract_function` statement→span binding (§6) | E | turns a verb that exists into one a sentence can actually use -- V13's §6 measurement, unchanged |
| 5 | the 9 routed-elsewhere and 10 not-reachable rows (§5) | D | two lines each, one measurement each, and never again one row at a time without a law |
| 6 | the 6 refusals that still do not name the act | C | the other 9 do; the words are already computed |
| 7 | `docstrings` | A | last on purpose: it is the only act here that needs judgement, and no AI model may participate in Brain-credited cognition, so it needs a structural (signature/docstring-echo) lane, not a generator |
| 8 | attribute the 26 red tests (§7) | F | restores the ability to see a regression |

Two rules for all of it, unchanged: **reuse before synthesis** — four of the eight rows
are rebuilds over machinery that already ships — and **measure, never assert**: every row
above is a re-runnable probe, and a red row is still not an authority until the owner
says so.


---

## 10. What closed since V12

Two capabilities, and the four binder laws they could not exist without. Both were
measured before and after with the same instrument.

| act | before | now | why it was cheap |
|---|---|---|---|
| `move_function` | `OWNED_BUT_FAILED` — a source audit was selected, ran, and never wrote the promised artifact | `ANSWERED_BY_OWNING_CAPABILITY` | it is `rename_symbol`'s machinery pointed the other way: same def resolution, same span cut, same file-identity import test, same rollback-on-red |
| `resource_leak` | `WRONG_TOOL` — `vcs.git.checkout.v1` answered "find the resource leaks" | `ANSWERED_BY_OWNING_CAPABILITY` | a new act verb inside `quality_v1`, the adapter every other quality analysis already uses, so artifact digest law and digest verification came for free |

Both carry their own measured laws, in their own docstrings, because each was wrong
before it was right:

* **the import is split, not swapped** — `from pkg.calc import add, sub` binds two names
  and only one moved; the first build sent `sub` to a module that does not define it and
  only the named suite noticed;
* **rollback removes what it created** — restoring pre-existing bytes while leaving the
  new module behind is a tree the refused edit changed;
* **`return handle.read()` is not a transfer** — reading the whole returned expression
  made the most common leak in Python (open, read, never close) the one shape the leak
  detector missed;
* **scopes are analysed separately** — a handle opened in a nested function is not closed
  by anything in its parent.

Four laws went into the door itself, all general rather than verb-specific:

1. **A destination may not exist yet.** `target_module` is where the thing GOES, so it is
   allowlisted to bind a stated path that does not exist, introduced by its own phrases.
2. **A stated path has two legitimate spellings** — source-root-relative and
   repository-relative — and the reading whose PARENT DIRECTORY exists wins. The first
   version resolved repository-relative first, produced
   `pkg/canonical/astra_runtime/.../ops.py`, and refused an honest request.
3. **"report it to X" is an output role.** The verb table knew save/write/store/output/
   emit and not report, so every sentence in this repository's own probes rested on a
   weaker rule.
4. **A path already given to another input is not the output.** A sentence naming two
   future paths — a destination module and a report — bound neither.

**The consequence that must be read honestly:** wrong-tool executions rose 7 → 9. Two
rows (`docstrings`, `inline_function`) that previously refused because their output could
not bind now reach admission and execute a capability that does not own the act. The
binding fix is right and the exposure is real: **the noun-side refusal law of §3 is now
the single highest-value remaining guard**, and it is the next thing to build.

Guards after this unit: move-function pins 9/9, resource-leak pins 6/6, refactor and
source-type suites 26/26, compiler suites 26 failed / 116 passed with failing node ids
**identical** to `62be529`.

---

## 11. What closed since V13, and what it cost

Three units landed on `arena/4ca3a720-brain` after V13 was written. Each one is a
measurement, not an intention.

### 11.1 `resource_leak` became a capability (V13 §10)

`python.quality.resource_leak.v1` inside the existing `quality_v1` adapter: same FAIL
artifact, same digest law, same verification. The laws it needed were measured, not
guessed -- same-scope analysis only (an `ast.walk` descends into nested functions and
reports every leak twice), and a *transfer* is only a bare name (reading
`return handle.read()` as a transfer cleared the single most common Python leak).
Probe row: `ANSWERED_BY_OWNING_CAPABILITY`, 3 findings on the fixture, 6/6 pins.

### 11.2 `api_compatibility` became a capability (§11 here, was §2)

`python.quality.api_compatibility.v1`, again inside `quality_v1`. The baseline is the
committed revision read through `git show` -- the same git the changelog and coverage
verbs already use -- so this is an AST diff of the public surface across two revisions
with no new machinery. Laws, each pinned:

* a removed public function is breaking; a removed private one is not;
* a renamed positional parameter is breaking even though every positional call still
  works, because a keyword caller breaks;
* a NEW required parameter breaks every caller that was correct before; a new function is
  an addition and never a break;
* a module with no committed version is new surface, not a deleted one.

Registry 153 -> 154. Probe row: `ANSWERED_BY_OWNING_CAPABILITY`, 0 other rows moved.
Pins 6/6.

### 11.3 The wrong-tool class was closed (§3)

Nine rows moved from "a capability that had no business answering ran and reported what
it did" to "refused before anything executed, naming the act". Three laws (§3), cost
measured: composer/synthesis suites 9 failing node ids -> 7 (two fixed, none broken);
compiler suites unchanged at 26 failed / 107 passed with **identical** node ids.

The one thing this unit did NOT do is make the machine able to fuzz, inline, package or
document. It made it stop pretending. That ordering is deliberate: an honest refusal is a
work item, a confident wrong artifact is a defect that hides one.

### 11.4 A refusal now names the act it cannot perform (V13 §4, completed)

`FAIL__RAW_GOAL_COMPILATION_GAP` used to report the capability that came CLOSEST and the
slot that stayed unbound -- e.g.
`GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH:python.refactor.extract_function.v1:end_line`
for "Fuzz the function add". Reusing the word `_unheard_act_word` already computes for
R14, the refusal now also carries `NO_CAPABILITY_PERFORMS:<the act>`. Measured on the
43-act probe: refusals naming the missing act 6/15 -> 9/15.

### 11.5 The measurement this rests on

```
HARDCORE-SE MISSING-VERB PROBE (43 acts, /tmp/mv33.json)
  ANSWERED_BY_OWNING_CAPABILITY  28   refusals naming the act 9/15
  HONEST_REFUSAL                 15   WRONG_TOOL 0   SILENT 0   OWNED_BUT_FAILED 0

WHOLE-SURFACE REACHABILITY (448 entries)   426 reached / 10 unreachable / 9 elsewhere / 3 by name
PINNED PINS   move_function 9/9  resource_leak 6/6  api_compatibility 6/6  (21 passed combined)
COMPILER SUITES  26 failed / 107 passed, failing node ids identical to baseline
COMPOSER+SYNTHESIS SUITES  8 failed (baseline 9), no new failing node id
ROUTE-IDENTIFICATION PINS 8/8
```

The next three items, in the order the measurements rank them: the noun-side selection
guard (§3, last paragraph -- five refusals still HAND a wrong candidate to the guard),
`dependency_add` + `build_package` (§2, both reuse jobs), then `inline_function` and
`docstrings`.
