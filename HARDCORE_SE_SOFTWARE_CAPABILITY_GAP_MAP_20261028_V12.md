# The complete problem inventory — hardcore software engineering

**2026-10-28 · V12 · measured on `arena/4ca3a720-brain` at `2ace3d6`**

This supersedes `HARDCORE_SE_PROBLEM_INVENTORY_20261028_V11.md`. V11 answered "what is
blocking one verb". This answers the question actually asked: **what are all the
problems**, across the whole machine, measured rather than asserted.

Nothing here is a wish list. Every row below is a row from a probe that can be re-run:

| instrument | what it can see | what it cannot |
|---|---|---|
| `execution_guard/hardcore_se_missing_verb_probe_v1.py` | 43 sentences a working engineer says, run through the real door (`solve()`), classified as answered / honest / silent / wrong-capability | only the 43 acts it names |
| `execution_guard/live_solver_end_to_end_measurement_v1.reachability()` | 445 bound capabilities: can the front compiler reach each one from a sentence built out of its own vocabulary | self-measures with the capability's own words, so it is generous |
| the pinned guard suites (`git_surface`, `hardcore_se_reachability`, `adapter_failure_law`, per-adapter pins) | that a capability which exists still behaves | nothing about acts that do not exist |

The first two disagree on purpose, and the disagreement is the most useful number here:
**the surface is 424/445 reachable by its own vocabulary while 18 of 43 real engineering
sentences are answered by nothing, and 9 more by the wrong thing.**

---

## 1. The scoreboard

```
HARDCORE-SE MISSING-VERB PROBE (43 acts)
  ANSWERED_BY_OWNING_CAPABILITY   25
  HONEST_REFUSAL                   9      "I cannot do this", said in words, before doing anything
  WRONG_TOOL                       7      a capability that does not own the act was ADMITTED and ran
  SILENT_REFUSAL                   1      no capability, no artifact, no reason at all
  OWNED_BUT_FAILED                 1      the ownership heuristic credited a neighbour (see §3)
  ----------------------------------------------------------------
  for reference: a capability that does not own the act was selected in 14 of the 43 rows

WHOLE-SURFACE REACHABILITY (445 capabilities)
  REACHED_AND_BOUND              424
  NOT_REACHABLE                    8      a sentence in its own vocabulary cannot bind it
  ROUTED_ELSEWHERE                10      another capability claims that sentence
  REACHED_BY_EXPLICIT_NAME         3      only reachable if the caller names the id

COMPILER SUITES                 26 failed / 107 passed   (see §7)
PINNED GUARDS             all green: 20/20 refactor pins, 63/63 refactor+flake suites,
                                    22/22 hardcore reachability, 12/12 git surface
                                    (+10/10 refusals), 18/18 adapter-failure-typed
```

Read the first block as a capability statement, not a bug count: **25 of the 43 acts a
senior software engineer performs on any given day are performed, correctly, by their
owning capability, with the promised artifact on disk.** Of the other 18, 17 have no
owning capability anywhere in this machine (§2), 7 of them are answered by a wrong tool
that actually executed (§4), and 1 produces no diagnosis at all.

### How a verdict is decided

A refusal is honest only if the machine says so. `PROMISED_ARTIFACT_MISSING` and
`CAPABILITY_EXITED_PROCESS` are **closed** statuses that arrive *after* a capability was
admitted and executed; the previous revision of the probe counted them as honest refusals
because the status starts with `FAIL_CLOSED`. It now separates "declined before doing
anything" from "ran the wrong thing and closed afterwards", which moved the headline from
"18 honest refusals" to **9 honest, 7 wrong-tool, 1 silent**. That correction is pinned in
`classify()` with the measurement in its docstring.

---

## 2. Class A — seventeen acts this machine cannot perform at all

No capability in the 151-entry registry performs these. Verified by searching every id,
keyword, provides and effect, not assumed. Each is a *missing tier* of engineering, not a
missing parameter.

| act | the sentence | why it matters |
|---|---|---|
| `move_function` | "Move the function `add` … into a new module" | the bread-and-butter refactor after rename; `rename_symbol` already owns 95% of the machinery (def-site resolve, span splice, cross-file import rewrite, rollback-on-red) |
| `inline_function` | "Inline the function `sub`" | the inverse of extract; needs call-site argument capture and return-value fusion |
| `docstrings` | "Write docstrings for the functions in …" | the only act in this table that requires judgement — it is the one that legitimately needs a synthesis lane, not an adapter |
| `api_compatibility` | "Check whether the change breaks the public api" | mechanical (AST diff of public surface across two revs) yet nothing does it |
| `differential_test` | "Run a differential test … against a reference" | mechanical: two implementations, one input stream, diff the results |
| `fuzz` | "Fuzz the function `add`" | needs a generator + a crash oracle; `atheris` is absent, but a stdlib random+subprocess harness is not |
| `memory_profile` | "Measure the memory usage of the program" | `tracemalloc` is stdlib; nothing wraps it |
| `resource_leak` | "Find the resource leaks in …" | static: `open()`/`connect()` without `with`; the AST machinery for this already ships |
| `retry_design` | "Make the network calls … retry safely" | an edit + policy, decomposes into existing refactor primitives |
| `observability` | "Add logging and metrics to …" | an edit; needs a logging/metrics model to edit *towards* |
| `schema_migration` | "Write a schema migration for the database" | needs a schema reader (sqlite reader exists) + a writer |
| `dependency_add` | "Add the dependency `requests` to the project" | prerequisite for everything `pypi`-sourced; `pyproject`/`requirements` edit + pin resolution |
| `build_package` | "Build a wheel for the project" | no build lane at all: `python -m build` is not a bound system tool |
| `ci_config` | "Write a continuous integration workflow for …" | 0 of 43 rows produced less information than this one (see §4) |
| `merge_conflict` | "Resolve the merge conflicts in …" | needs conflict parse + a resolution policy; `git` bound tool already reads the state |
| `crash_repro` | "Reproduce the crash … and shrink it to a minimal case" | delta-debugging is a loop over an existing test runner |
| `interactive_debug` | "Debug the function `add` … with breakpoints" | a debugger protocol: `sys.settrace`/`bdb` are stdlib |

Ordered by capability gained per engineering hour, the first four —
**`move_function`, `resource_leak`, `api_compatibility`, `dependency_add`** — are each a
reuse job over machinery that already exists (span splicing, AST walk, pyproject parse).
`docstrings` is last on purpose: it is the only one that needs a model, and no model may
participate in Brain-credited cognition.

---

## 3. Class B — seven sentences answered, and executed, by the wrong capability

The dangerous class: the sentence is not understood, a tool is selected anyway, it is
admitted, it runs, and only the promised-artifact check stops it.

| act | the sentence asks for | what actually ran |
|---|---|---|
| `merge_conflict` | resolve merge conflicts | `python.quality.changelog.v1` |
| `memory_profile` | measure memory usage | `python.quality.changelog.v1` |
| `dependency_add` | add a dependency | `document.convert.markdown_pdf.pandoc_weasyprint` |
| `build_package` | build a wheel | `document.convert.markdown_pdf.pandoc_weasyprint` |
| `observability` | add logging and metrics | `document.convert.markdown_pdf.pandoc_weasyprint` |
| `schema_migration` | write a schema migration | `text.file.write` |
| `docstrings` | write docstrings | `python.source.audit.ast` |

A markdown-to-PDF converter was admitted for three of them. None of the seven wrote what
the sentence promised, so no user was fooled — but a tool ran on a request it had no
business running on, and the only thing that stopped it was a file check at the end.

**The single law that would catch all seven.** The existing guards (`R12` stated act is
not an act this brain performs, `R13` stated act is owned by another capability, `R14`
unheard act word) all key on the **verb**, and every one of the seven has a head verb the
*wrong* capability legitimately claims — `check`, `add`, `write`, `measure`, `build`,
`resolve`. The discriminating evidence is the **object**: "merge conflicts", "memory
usage", "wheel", "docstrings", "schema migration", "logging and metrics", "dependency".
Not one of those nouns is in the selected capability's vocabulary, and not one is in the
registry's — which is exactly the definition of an act this machine does not perform.

A noun-side mirror of `R14` — *the sentence states an object the selected capability never
mentions, and no capability in the registry claims that object* — would refuse all seven
before anything executes. It is a routing guard, not a new ability, and its blast radius
is measurable against the 25 owned rows and the 445-capability reachability table before
it lands.

The remaining 7 of the 14 non-owning selections (`interactive_debug`, `crash_repro`,
`fuzz`, `differential_test`, `resource_leak`, `retry_design`, `api_compatibility`,
`inline_function`) are refused at admission — `R12`, `R13` and `R14` do fire there — so
the guard already exists; it just does not fire when the object is the only unusual word.

`move_function` is reported `OWNED_BUT_FAILED` rather than `WRONG_TOOL` because the
probe's ownership test matches the word `function`, which `python.source.audit.ast`
claims. That is the probe's own heuristic being generous, not a capability: nothing in
this machine moves a function.

## 4. Class C — one row with no diagnosis at all, and one lost diagnosis

| act | what came back |
|---|---|
| `ci_config` | `FAIL__RAW_GOAL_COMPILATION_GAP`, `reason: ""` — a closed failure with an empty diagnosis |
| `change_signature` (before this commit's fixture fix) | `FAIL_CLOSED__CAPABILITY_EXITED_PROCESS`, `reason: ""` — a capability raised `SystemExit`, the door converted it to a closed failure, and **which capability did it and the reason it gave were both dropped** |

The second is worse than it looks: the adapter's `SystemExit` payload *is* the diagnosis,
and the conversion at `live_brain_route_admission_v1._execute_locally` throws it away
while reporting a status that names no capability. A caller cannot tell what failed.
Both are one-line fixes in the diagnosis path, not capability work, and both matter more
than they look because *an unexplained refusal cannot be acted on by the machine that
received it* — the owner's goal requires the system to detect missing data and acquire it,
which it cannot do for a refusal that says nothing.

## 5. Class D — eighteen reachability defects

Each row: a capability that exists and cannot be reached from its own vocabulary.
Measured after this commit's fixes: **8 not reachable, 10 routed elsewhere, 3 by explicit
name** (before them: 7 / 11 / 3 -- `python.review.diff_mutation_gate.v1` became reachable
and `chart.raster.curve_value_query.v1` lost its sentence to a neighbour, a net move of
one row with no net gain, which is why this class must be fixed by law and not one row at
a time).

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

## 8. What this commit fixed, and the measurement for each

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

Pins added: 2 (package-root source root; ambiguous name never matched). The probe itself
is now a committed instrument, and it changed two of its own conclusions while being
built — the fixture must be pristine per act, and a wrong-tool failure is not a refusal.

---

## 9. The plan this implies

| # | work | class | why now |
|---|---|---|---|
| 1 | noun-side refusal law (§3) | B | one guard converts 7 wrong-tool executions into refusals and protects every future absence |
| 2 | diagnosis path: never report a closed failure with an empty reason (§4) | C | cheap, and it makes every future failure self-explaining |
| 3 | the 10 routed-elsewhere rows (§5) | D | two lines each, one measurement each |
| 4 | `move_function` | A | rebuilds an act a refactor runner is expected to have, from `rename_symbol`'s machinery |
| 5 | `resource_leak` + `api_compatibility` | A | analysis, deterministic, AST machinery already shipped |
| 6 | `dependency_add` + `build_package` | A | unblocks the pypi/build lane entirely |
| 7 | `extract_function` statement→span binding (§6) | E | turns an unrunnable verb into a usable one |
| 8 | attribute the 26 red tests (§7) | F | restores the ability to see a regression |

Two rules for all of it, unchanged: **reuse before synthesis** — five of the eight rows
are rebuilds over machinery that already ships — and **measure, never assert**: every row
above is a re-runnable probe, and a red row is still not an authority until the owner
says so.
