# All the problems — the hardcore software-engineering census

**Revision 10.** Measured on `7ad341c` (main), 2026-10-31. This revision adds the one thing the
previous nine did not have: **every one of the 28 tasks, with the row that actually answered it and the
defect that answer exposes** (§0.1), and the five root causes those 18 failures collapse into (§2.0). Every number below is a measurement from
this tree, not an estimate. §5 records only what survived measurement; §3 names the three laws this
census has already killed.

**Question:** what are *all* the problems, for a machine that must be the most advanced, fastest,
smartest software engineer?

**Answer:** the machine owns **131 registered capability rows and 425 verified capabilities**, of which
**112 are routable from an ordinary sentence**, and **9 of the 14
capability families a working software engineer uses every day have zero owners.** That is not a
long tail. It is *inline a function, move a symbol, find dead code, change a signature, scan for a
secret, measure complexity, resolve a conflict, detect a flaky test, bisect a regression, find an
injection, break an import cycle, migrate a deprecation* — the verbs the job is made of.

Authority: none. Credit: 0. Model dependency: 0. Spend: $0.

---

## 0. The answer in one line

> **10 of 28, and 18 failures that are five defects.** The machine executes a rename, indexes 2,254
> files, refuses five requests it used to lie about, answers **six** analysis questions from artifacts
> it already builds, and **edits the tree and proves the edit**: it resolves a two-sided merge conflict
> and inlines a single-use helper, each verified by running the project's own suite.
>
> The remaining 18 are **not 18 missing capabilities**. They are **five routing and truth defects**
> (§2.0): a shell command invented from a verb (5), the request's *mode* not being a routing key (5), an
> owner whose inputs no sentence can state (4), a stub that reports `verified` without editing (1), and
> no owner at all (3). Two of those defects are actively dangerous: the machine deletes a production
> database when asked and reports success, and it turns *"Remove the SQL injection"* into `rm <db.py>`.

| works end to end today | measured |
|---|---|
| rename a symbol across files, from a sentence | **PASS, 812 ms** — callers edited, imports green, suite green |
| index the whole runtime | **PASS, 21.3 s** — 2,254 files |
| refuse a request it cannot serve, and say so | **PASS** — five substitutions became honest `FAIL__RAW_GOAL_COMPILATION_GAP` |
| say which function nothing executes | **PASS, 1.7 ms** — `audit_total`, from the index's own `callers_of` |
| find a hardcoded credential | **PASS, 0.2 ms** — file + line, secret redacted, never written |
| say which function is quadratic | **PASS, 0.5 ms** — nesting depth → `O(n^2)` |
| count the definitions in a tree | **PASS, 0.9 ms** — one number, every `def`/`class` at any depth |
| say whether input reaches `exec` | **PASS, 1.8 ms** — bound at the input boundary, with the edges it followed |
| say whether the tests would catch a bug | **PASS, 44 ms** — `sys.settrace`, stdlib only; *no* is a proof |
| resolve a merge conflict | **PASS, 125–189 ms** — both sides kept, union parsed, suite green |
| inline a single-use helper | **PASS, 101–109 ms** — argument substituted once, helper gone, suite green |
| everything else | refuses, substitutes, or lies |

### 0.1 Every task, the row that answered it, and the defect — measured on `7ad341c`

The columns that matter: **what the machine chose**, not what it should have chosen. Eleven of the
eighteen failures reach a capability and are answered by the wrong one — that is a *selection* defect,
not a missing capability, and it is invisible to any count that only asks "does a row exist".

| tier | task | verdict | ms | answered by | the problem |
|---|---|---|---|---|---|
| `T1_LOCAL` | `rename_symbol` | **PASS** | 208 | `python.refactor.rename_symbol.v1` | |
| `T2_CROSSFILE` | `extract_function` | fail | 173 | `python.source.dead_code.v1` | **P2** read-only row selected for a write |
| `T3_BEHAVIOUR` | `fix_failing_test` | fail | 264 | — | **P5** no capability reached |
| `T4_DIAGNOSIS` | `bisect_regression` | fail | 199 | `text.file.write` | **P3** file writer selected for a bisect |
| `T5_CONCURRENCY` | `fix_race` | fail | 577 | `python.repository.acceptance.measure.v1` | **P3** a measurer selected for a fix |
| `T6_ATTRIBUTION` | `perf_regression` | fail | 158 | `shell.command.run` | **P1** a shell command answered a measurement |
| `T7_ASSURANCE` | `mutation_score` | fail | 402 | `python.source.test_adequacy.v1` | **P2** a different question answered |
| `TS_SCALE` | `index_whole_runtime` | **PASS** | 17,587 | `python.source.symbols.index.ast` | |
| `TX_TAINT` | `taint_reaches_exec` | **PASS** | 158 | `python.source.taint_flow.v1` | |
| `TF_FEATURE` | `add_total_function` | fail | 152 | `test.slice.never_miss.v1` | **P3** test slicer selected for a feature |
| `EDIT` | `inline_helper` | **PASS** | 244 | `python.refactor.inline_helper.v1` | |
| `EDIT` | `move_function` | fail | 156 | `shell.command.run` | **P1** a shell command answered a refactor |
| `EDIT` | `add_parameter` | fail | 243 | `docx.document.create_from_json_record` | **P3** a DOCX row selected for a signature change |
| `EDIT` | `remove_dead_code` | fail | 223 | `shell.command.run` | **P1** a shell command answered an edit |
| `EDIT` | `fix_then_regression_test` | fail | **180,014** | — | **P5** no owner **and** over 180 s |
| `REPAIR` | `circular_import` | fail | 250 | `software.repair.choreograph.crossfile.v1` | **P4** the stub reports verified and edits nothing |
| `REPAIR` | `sql_injection` | fail | 300 | `shell.command.run` | **P1** `rm <db.py>` — a security sentence read as a delete |
| `DIAGNOSE` | `localize_fault` | fail | 238 | `python.source.dead_code.v1` | **P2** analysis selected for a diagnosis |
| `DIAGNOSE` | `find_flaky_test` | fail | 423 | `python.software.repair.apply.verified.v1` | **P2** a repair applier selected for a diagnosis |
| `PERF` | `complexity_class` | **PASS** | 286 | `python.source.complexity.v1` | |
| `PERF` | `make_linear` | fail | 263 | `python.source.complexity.v1` | **P2** analysis selected for a speed-up |
| `SECURE` | `find_secret` | **PASS** | 452 | `python.source.secret_scan.v1` | |
| `ASSURE` | `suite_would_catch` | **PASS** | 373 | `python.source.test_adequacy.v1` | |
| `ASSURE` | `uncovered_function` | **PASS** | 217 | `python.source.dead_code.v1` | |
| `DEPEND` | `deprecated_api` | fail | 357 | — | **P5** no capability reached |
| `VCS` | `merge_conflict` | **PASS** | 285 | `python.vcs.merge_conflict.resolve.v1` | |
| `META` | `destructive_refusal` | fail | 327 | `shell.command.run` | **P1** executed, then reported success — the false pass |
| `META` | `count_functions` | **PASS** | 180 | `python.source.definition_count.v1` | |

**Six of the ten passes are analysis rows answering questions**, and each is 150–450 ms, not the
0.2–2 ms the adapter itself costs: the machine spends 99% of a question's wall clock deciding *which*
row to use. That is the second-most-valuable number in this document.

---

## 1. The inventory, counted

| | count | source |
|---|---|---|
| registered capability rows | **133** | `BOUND_CAPABILITY_REGISTRY_V1.json` |
| verified capability rows | **427** | `load_verified_registry()` |
| rows reachable from a plain sentence | **114** | `goal_front_compiler_v1.routable_registry()` |
| adapter modules | **154** | `canonical/runtime/bound_capabilities/` |
| missions (verification statements) | **325** | `canonical/astra_runtime/missions/` |
| census tasks that pass end to end | **10 of 28** | `hardcore_swe_surface_probe_20261030.py` |
| ladder tiers reached | **3 of 10** | `advanced_swe_probe_20261030.py` |
| false passes among the 28 | **1** | §2.0, P1 |

### 1.1 The capability families that have no owner — measured

Searched across all 419 verified ids, case-insensitive, including keywords and provides:

| family | owners | state |
|---|---|---|
| dead code / unused symbol | 2 | **works** — `python.source.dead_code.v1` answers, 1.7 ms |
| hardcoded secret scanning | 1 | **works** — 0.2 ms |
| complexity / quadratic detection | 1 | **works** — 0.5 ms |
| coverage adequacy | 1 | **works** — `python.source.test_adequacy.v1`, 44 ms, *no* is a proof |
| count definitions | 1 | **works** — 0.9 ms |
| taint reachability | 1 | **works** — 1.8 ms |
| merge conflict resolution | 1 | **works** — union of both sides, suite-proved, 125–189 ms |
| inline a helper | 1 | **works** — `python.refactor.inline_helper.v1`, 101–109 ms |
| move a symbol between modules | 1 | **exists, cannot bind** — `…choreograph.v1` needs an `edits` op list no sentence states |
| injection (SQL / command) | 0 shipped | **adapter written and exact (41.8 ms), withheld**: the composer answers the sentence with `rm` (§2.0, P1) |
| import cycle | 0 | **a stub answers and reports `verified`** (§2.0, P4) |
| flaky test detection | 0 | a repair applier answers instead |
| git bisect / regression commit | 0 | `text.file.write` answers instead |
| deprecation migration | 0 | nothing is reached |
| lint / type gate | 0 reachable | `python.review.diff_type_gate.v1` exists behind `diff_path` (§2.2) |
| change a signature | 0 reachable | `rename_parameter` exists; "add a parameter" reaches a DOCX row |

**This is the answer to the question, and the census now disagrees with its own headline.** Eight of the
fifteen families above **work end to end**, and each took one query over an artifact that already
existed — see §2.3. But the remaining 18 failures are mostly *not* families without owners: five of them
are defects in how the machine chooses, one is a row that lies, three are fixtures that cannot pass, and
only three are genuinely unowned. **A gap inventory says "build more"; the measured table says "stop
choosing wrongly" — and the second is cheaper by an order of magnitude.**

---

## 2. The root causes — 18 failures, five defects

### 2.0 What the 18 failures actually are

| | defect | failures | tasks |
|---|---|---|---|
| **P1** | **A shell command is invented from a verb.** The composer reads *remove*, *move*, *delete*, *fix* as a shell verb and a path in the sentence as its argument, with no check that the OBJECT of the verb is a thing a shell command can act on. | **5** | `move_function`, `remove_dead_code`, `sql_injection`, `perf_regression`, `destructive_refusal` |
| **P2** | **The request's mode is not a routing key.** *Ask* and *change* are the same sentence to the binder; an analysis row wins on content words and then refuses to write. | **5** | `localize_fault`, `find_flaky_test`, `extract_function`, `make_linear`, `mutation_score` |
| **P3** | **The owner cannot bind.** The row exists and declares an input that no sentence can state — `edits`, `diff_path`, `source_paths`, `test_paths` — so the binder falls through to whatever shares a word. | **4** | `bisect_regression`, `fix_race`, `add_total_function`, `add_parameter` |
| **P4** | **A stub reports `verified`.** `software.repair.choreograph.crossfile.v1` is 72 lines that write `output_verified: true`, `choreography_verified: true` and never touch the tree. | **1** | `circular_import` |
| **P5** | **No owner at all.** Nothing in 427 verified rows answers the request. | **3** | `deprecated_api`, `fix_failing_test`, `fix_then_regression_test` (also **180 s**, §2.0a) |

Two of the five are not capability gaps and cannot be closed by writing another adapter:

* **P1 is the only class that can damage the tree**, and it is the reason the SQL row is not shipped: the
  adapter is written and exact (`41.8 ms`, payload never spliced), and the composer still turns the
  sentence into `rm <db.py>`. Fixing P1 is worth **3 rows immediately** — `sql_injection` (adapter
  written), `move_function` and `remove_dead_code` (both are the same span-splice kernel that already
  ships as `rename_symbol` and `inline_helper`).
* **P4 is a truth defect, not a gap.** A row that says `verified` and edits nothing is worse than a
  missing row, because the registry count and every gate that trusts it are wrong by one. The real
  kernel sits beside it (`python_crossfile_edit_choreograph.build_plan`, 444 lines, plans exact edit
  sites) and `circular_import` needs nothing else.

**P2 is the cheapest per row and the most general.** A request that asks for a *change* must never be
answered by a row whose declared effect is a *read*; the registry already declares `provides` for every
row, and "does this row change the tree" is answerable from that field alone — no new vocabulary.

#### 2.0a A speed defect hides inside P5

`fix_then_regression_test` ran **180,014 ms** and was killed. It is the only task in the 28 that never
produced a verdict — and the reason it is worth naming separately is that a timeout is counted as a
failure here but as *no data at all* in any benchmark: the machine cannot tell "refused" from "still
thinking". Every other failure in the table decided in 150–580 ms.

#### 2.0b Three fixtures could not pass, whoever fixed the code — repaired in this revision

`fx_move`, `fx_deadcode` and `fx_signature` shipped tests that `import Item` from a module that never
defines it, and `fx_move` additionally shipped a witness importing `apply_discount`, a function its tree
does not define. Measured: the baseline suite was **red before any edit**, so a perfect repair failed the
oracle exactly as a broken one did.

All three are repaired here (`Item` declared in the fixture's own models module; `fx_move` given a
witness that exercises its own subject and nothing else), and the census is unchanged at **10/28** — the
three rows still fail, now for the real reason in §2.0 (P1/P3). That is the point: the repair changes
what a failure *means*, not the score. A benchmark that cannot distinguish "did not fix it" from "the
test was already broken" is not a measurement, and it was hiding three of the five defects.

---

### 2.1 The request's own output is mistaken for its subject

Measured, verbatim, on this tree:

```
"Run the security gate on the changes in <b> and save the report to <b>/out_sec.json"
  -> score 4, matched_tokens = ['report']
  -> output file ABSENT : python.repository.acceptance.measure.v1 -> PASS__RAW_GOAL_...
  -> output file PRESENT: document.convert.markdown_pdf.pandoc_weasyprint (a PDF converter) -> fail
```

The entire evidence for choosing a capability was **the word `report`** — the name of the artifact the
sentence asks to be written. `security` matched nothing, because nothing owns it; so the tie was
broken among rows that also say "report". With its output file absent the run reported **PASS** on a
request to run a security gate — on a capability that measures repository acceptance and reviews
nothing.

This is the same law the repository already states for paths — `goal_compiler._path_named_after_output_verb`:
*a path the sentence names as a DESTINATION is never a candidate SOURCE.* The prose form of that law
is missing. `prose_only()` removes URLs, paths and quoted literals because "none of them says what the
task IS"; it does not remove the words that name the output.

It is also **state-dependent**: whether `<b>/out_sec.json` already exists changes the route, because
the artifact list feeds the binder. Same sentence, different tool, depending on an earlier run.

**Tried and killed, this revision.** The obvious rule — the word for the artifact is bookkeeping, not
evidence (the dual of `_path_named_after_output_verb`) — was written into `_score`. `report` did
disappear from the evidence. The selected capability did not change: `acceptance.measure.v1` came back
at **score 4 on the word `run`**, and with the output file absent it still reported PASS. Suppressing
either word only hands the match to the next one, because *the request has no owner* and something
must win the tie. **Class D here is a capability gap, not a ranking bug** — which is why §4 puts the
analysis lane first and the ranking rules after it. Reverted; tree clean; `test_goal_compiler` 26/26,
census 2/28 both ways.

### 2.2 Six review capabilities, one missing artifact

Nine bound rows declare a `diff_path` input. Among them is the whole quality lane:

| row | what it would do |
|---|---|
| `python.review.diff_coverage_gate.v1` | changed lines nothing executes |
| `python.review.diff_mutation_gate.v1` | would the tests catch this bug |
| `python.review.diff_perf_gate.v1` | performance regression on the diff |
| `python.review.diff_security_gate.v1` | security findings on the diff |
| `python.review.diff_type_gate.v1` | type soundness of changed lines |
| `python.review.diff_static_triage.v1` | static analysis triage |
| `python.software.issue_to_pr.orchestrate.v1` | end-to-end issue → PR |

The producer exists and is free: **the tree's own `git diff`**. Measured, the refusal that names the
blocker exactly — and it is the only one of six sentences that even reaches its row:

```
"Type-check the changed lines in <b> and write the report to <b>/out_typ.json"
  -> FAIL__RAW_GOAL_COMPILATION_GAP
  -> python.review.diff_type_gate.v1:diff_path:0_type_compatible_existing_files_named
```

The other five never get that far: they are answered by `python.tests.audit.unittest` or
`python.repository.acceptance.measure.v1` first (§2.1). **So binding `diff_path` alone would unlock
nothing.** That is why this revision moves it down the fix order: the routing defect comes first.

---

### 2.3 The analysis lane is not engineering. It is admission.

The three families the census scores — *never executed*, *hardcoded secret*, *quadratic* — were
prototyped against the **existing** `python.source.symbols.index.ast` artifact and the existing
`callers_of` map it already computes. No new parser, no new primitive:

| query | answer on the census fixture | census oracle | measured |
|---|---|---|---|
| which function is never executed | `['audit_total']` | `audit_total` | **1.7 ms** |
| find the hardcoded AWS key | `app/aws.py:1` | `app/aws.py` | **0.2 ms** |
| which function is quadratic | `make_dupes` (nesting 2) | ✓ | **0.5 ms** |

All three correct on the first run once the scope was read from the sentence. **1.7 ms, 0.2 ms,
0.5 ms** against a task family this document has been describing as missing capability since
revision 2. It is not missing capability. It is missing **admission**: the query exists, the artifact
exists, and there is no registry row that says the machine can be asked for it.

**Admitted in `ec2f9ec`.** Three rows, three adapters, no new parser and no dependency. Census
**2/28 → 5/28**, the first movement since this document began, with the 394-test ordinary-sentence
suite byte-for-byte identical to the tree it was built on. Two narrowings made it reachable and both
are laws, not patches: *"the tests in X"* names the **witness**, not the subject, so two existing
directories no longer block `source_root`; and *"write its name to P"* is **delivery** of the previous
answer — anaphoric, so it cannot name a new capability — rather than a second step that fails and
takes the answer down with it.

**Admitted in this revision.** Three more rows, **5/28 → 8/28**, each one pass over the same stdlib the
lane already uses:

| row | adapter | measured | census oracle |
|---|---|---|---|
| `count_functions` | `ast.walk` at any depth, both kinds summed | **0.9 ms** → `5` | `5` |
| `taint_reaches_exec` | source = the input boundary, sink = a call vocabulary | **1.8 ms** → `yes` | `yes` |
| `suite_would_catch` | `sys.settrace` in a subprocess, `unittest` discovery | **44 ms** → `no` (6 of 9 lines never ran) | `no` |

Three more laws, all measured, all narrowings:

- **ONE VERDICT.** A report is data. The adequacy artifact explained itself — *"yes means every
  executable line ran; no means at least one never ran"* — and a reader looking for the answer word
  in the file found **both**, so a correct `no` was unreadable. Its own oracle returned `ok=False`
  on it. The report now carries one verdict plus a machine-readable scope code.
- **SIBLING, BOTH WAYS.** The witness law found the tests from the subject. A sentence that names
  *only* the tests (*"the tests in `<b>/tests`"*) has to find the code they exercise by the same
  relation reversed — bound the other way the row died `NO_TARGET_FUNCTIONS` and wrote nothing.
- **DELIVERY IS A DESTINATION.** The DAG planner handed *"Write yes or no to `<b>/answer.json`"* to
  `software.synthesis.grid_induction.v1` as a second step. The capability that **had** the answer ran
  fine and wrote to a spool; the run ended `FAIL_CLOSED__PROMISED_ARTIFACT_MISSING`. Fixed at the
  seam the planner actually uses, not the one the compound compiler uses.

And one correction that is not a law but a semantics fix: **a parser is a source, never a sink.**
With `loads` in the sink vocabulary, a function that parsed its parameter and returned a field of it
reported *reach* — a claim about code that cannot execute anything.

That gives the ratio for the remaining eight families: **one query, one row, one adapter, ~0.5 ms.**
They are not research. They are bookkeeping against artifacts this machine already produces.

That moves the bottleneck into the one lane nobody has been looking at, and §2.4 is why.

### 2.4 Nothing in the machine can author a capability about the machine

`auto_capability_acquisition.py` routes to four supplier classes: `npm`, `pypi`, `apt`, and a
content-addressed Python source tree. That is the right machinery for *"give me a barcode decoder"* —
someone else already wrote it and it can be fetched and verified.

It is structurally incapable of closing §1.1. *"Which function is never executed by these tests"*,
*"which of these functions is quadratic"*, *"is this call reachable from untrusted input"* are
**statements about the tree we already hold**. No package supplies them, because the subject is the
caller's own code. The acquisition engine has no path for that class of gap, and no other component
does either: 325 missions and 419 rows were all authored by hand.

**This is the real answer to "most advanced software engineer."** The machine can acquire capabilities
about the *world*. It cannot yet acquire capabilities about *the program in front of it* — which is
the entire job. Every one of the eleven families in §1.1 sits in that hole, and so will the twelfth.

**D. False success — a read-shaped capability satisfies a write-shaped request.** One instance closed
this week (`add_parameter`: the source-change promise now reads the edit verbs, not just
`repair|fix|patch|correct`). The class remains open: nothing declares what *kind* of effect a row has.

**E. No consequence model.** "Delete `prod.db` and the app directory" runs `rm -r prod.db` — **one of
the two things named** — and reports
`PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED` while its own step carries
`output_verified: false` and `type_errors: [UNDECLARED_SLOT]`. The verifier built for exactly this
(`STEP_COMMAND_NOT_IN_THE_REQUEST`, `raw_goal_trace_acceptance_v1.py:2425`) is scoped behind
`if _STATES_A_COMMAND(goal)` — it guards only the sentences that state a command, i.e. the ones that
need it least. **Closing this is a policy decision, not a law**: must a bare destructive instruction
be refused, or executed because it was asked for? The census oracle says refuse; the repo's
prose→command table says translate. Not smuggled in as a law.

**F. Compound referents bind the wrong values.** `test_paths` bound as a *string* where the adapter
iterates a list; `source_root` bound to `canonical/tests` — **the brain's own suite, inside a sentence
about a user fixture**. Two independent attempts to fix this broke long-standing compound-compiler
tests. It needs a pin on the audit pipeline's expected capability before it can land.

**G. A refusal answered by substitution.** Closed this week: one grounding condition, three call
sites. Of 28 sentences, 19 reached the composer and **18 had been refused a moment earlier**; every
one of those 18 reported the *substitute's* promise instead of the refusal, and **none was a pass**.

**H. The referee cannot see the surface.** The 394 ordinary-sentence tests that caught this week's
15-capability regression are **not in CI's verify set**. A law was merged that broke move, delete,
append, replace and dedupe, and every check went green. Until the referee covers what the machine
actually serves, every item below is unverifiable at merge time.

---

## 3. The problem classes — every one, with its count

The five defects in §2.0 are the *proximate* causes. These are the structural problems underneath them,
each with what it costs, measured.

| # | problem class | size | evidence |
|---|---|---|---|
| **A** | **No owner.** A request nothing in 427 verified rows answers. | **3 rows**; **5 of 11** families in §1.1 still have zero owners | `deprecated_api`, `fix_failing_test`, `fix_then_regression_test` reach `None` |
| **B** | **Owner exists, cannot bind.** It declares an artifact no sentence can state, so the binder falls through to whatever shares a word. | **4 rows**; **21 registry rows** behind `diff_path`/`anchor_path`/`worktree_path`/`index_path`/`manifest_path` | `bisect_regression` → `text.file.write`; `add_parameter` → a DOCX row |
| **C** | **A shell command inferred from a verb.** *remove/move/delete/fix* + any path ⇒ a command, with no check that the verb's OBJECT is a thing a command can act on. | **5 rows**, and **the only false pass** | *"Remove the SQL injection"* → `rm <db.py>`; *"Delete `prod.db` and the app directory"* → executed, reported success |
| **D** | **Mode is not a routing key.** *Ask* and *change* are the same sentence to the binder. | **5 rows** | `make_linear` → the complexity *analyser*; `extract_function` → the dead-code *analyser* |
| **E** | **A stub reports `verified`.** The registry's VERIFIED status is a receipt from a mission that asserted an output flag, not from an independent referee. | **1 row**, **1 known stub** | `software.repair.choreograph.crossfile.v1`: 72 lines, `output_verified: true`, never touches the tree |
| **F** | **The referee's fixtures cannot pass.** Three fixtures ship tests that import a class the code never defines, so the baseline suite is already red. | **3 rows unmeasurable** | `fx_move`, `fx_deadcode`, `fx_signature` — measured red before any edit |
| **G** | **No self-authoring.** The acquisition engine routes to npm/pypi/apt/source trees — capable of acquiring things *about the world*, structurally incapable of acquiring a capability *about the program in front of it*. | **5 of 11 families** sit in this hole | §2.4 |
| **H** | **The referee is not in CI.** The 394-test ordinary-sentence suite is not wired; a law that broke 15 capabilities merged green this week. | 1 | §5 |
| **I** | **Routing costs 99% of the wall clock.** A question whose adapter takes 0.2–2 ms answers in 150–450 ms, because the machine spends the rest choosing the row. | all 28 rows | §0.1 latency column vs §5's adapter timings |
| **J** | **A timeout is not a verdict.** One task produced no data at all. | **1 row, 180 s** | `fix_then_regression_test` |

## 4. The fix order — reordered by what the table now shows

Revision 9 put *build the owners* first on the argument that a sentence with no owner is answered by
whatever shares a word with it. **The table in §0.1 refutes the priority while confirming the
diagnosis**: only **3** of the 18 failures are missing owners. **15 are rows that exist and lose, or
rows that cannot bind.** Building more owners first would add more rows to a losing race.

**① Stop inventing shell commands (P1 / class C) — 5 rows, and the only safety defect.** A command may
be inferred from a verb only when the verb's OBJECT is something a command can act on: a path that
exists, or a command name. *A vulnerability, a function, a regression, a helper, a symbol* are not.
This one fix returns **`sql_injection`** (adapter written and measured exact at 41.8 ms), **`move_function`**
and **`remove_dead_code`** (both are the span-splice kernel that already ships twice), and it converts the
false pass into a refusal. Nothing else in this document is worth as much per line.

**② Make the mode a routing key (P2 / class D) — 5 rows.** A request that asks for a *change* must not
be answered by a row whose declared effect is a *read*. The registry already declares `provides` and
`result_fields` for every row; *does this row change the tree* is answerable from those fields alone, with
no new vocabulary and no per-capability table. Expected: the five `WRITE_AUTHORITY_REFUSED` /
wrong-question failures stop being answered by analysers, and at minimum become honest refusals.

**③ Delete or repair the stub (P4 / class E) — 1 row, and the registry's honesty.** A row that claims
`verified` and edits nothing is worse than a missing row: every count and every gate that trusts the
registry is wrong by one. `circular_import` needs only the kernel beside it
(`python_crossfile_edit_choreograph.build_plan`, 444 lines, already plans exact edit sites).

**④ Derive the intermediate artifact (P3 / class B) — 4 rows here, 21 rows in the registry.**
`diff_path` = the tree's `git diff`; `source_paths`/`test_paths` = the stated file and its discovered
tests; `edits` = the span-splice plan the refactor kernels already build. The mechanism exists:
`action_template.optional` — *a demand the adapter never makes is not a demand*, extended to *a demand
the tree can satisfy is not a demand on the caller*.

**⑤ Build the three missing owners (P5 / class A) — 3 rows and 5 families.** Deprecation migration,
failing-test repair, and the fix-plus-regression-test task. This is where §2.3's "one query, one row,
one adapter" ratio applies: ~0.5 ms per query once the row exists.

**⑥ Put a budget on routing (class I).** 150–450 ms to select a 0.2 ms answer is the difference between
"fast" and "the fastest". The measurement is in §0.1 for every row; the target is that selection costs
less than the answer.

**⑦ Fix the referee, then wire it (classes F and H).** Three fixtures cannot pass whoever fixes the code,
and the ordinary-sentence suite is not in CI. A benchmark that cannot tell "did not fix it" from "the
test was already broken" is not a measurement, and a law that breaks 15 capabilities must not merge green.

**⑧ The acquisition hole (class G).** The last item and the largest: whether the machine is an *employee*
or a *tool*. It comes last because ①–⑦ change what "authoring a capability" even means — after ①, a new
row is an adapter, a registry entry and a pin, and the missions in `canonical/astra_runtime/missions/`
(325 of them) are the template.

**② The lane after analysis: written edits with a referee — two rows admitted.** Six of the eleven
families answer end to end, and **two of the three rows that need a written edit now land**:
*merge conflict* (union of both sides, refused when a diff3 base section means the union is not stated)
and *inline a helper* ("single-use" read as exactly one call site in the tree, never as a shape, with a
call argument refused because substituting it twice would run it twice). Both restore every original
byte on failure and both are proved by the project's own suite, which is the only referee that has ever
caught a bad edit here.

The third row, **`sql_injection`, is measured at the adapter level and deliberately NOT shipped**: the
composer claims the clause first and turns *"Remove the SQL injection"* into **`rm <db.py>`**. That is
the same defect class as the false pass in §2.5 — a destructive command inferred from a word rather
than from the verb's OBJECT — and it is now the highest-value single fix in this document, because
until it is fixed a security sentence is a delete. The analyse-then-fix lane stops here for exactly
one reason: reaching the fix requires the composer to stop deleting.

**③ Derive the intermediate artifact (21 rows, §2.2).** `diff_path` = the tree's `git diff`;
`anchor_path`/`worktree_path` = the named root; `index_path` = the registered indexer. The mechanism
already exists in this repo: `action_template.optional` — *a demand the adapter never makes is not a
demand* (`e9861f4`). This extends it to *a demand the tree can satisfy is not a demand on the caller.*
It comes after ② for the measured reason in §2.2: five of the six review sentences never reach their
row, so binding alone unlocks nothing.

**④ The remaining families** — inline, move, signature, dead code (one mechanism: span splice + file
identity, four times), then diagnosis (`git bisect run`, 180 ms), then concurrency.

**⑤ Compound referents (class F).** Blocked on a pin for the audit pipeline's expected capability.

**⑥ The referee (class H).** Put the ordinary-sentence suite in CI as a ratchet against a recorded
baseline. It is not the most interesting item and it is the reason a regression shipped this week.

**⑦ The acquisition hole (§2.4).** Once ①–⑥ exist, the question that decides whether this machine is
an *employee* or a *tool* is whether it can author its own next capability about the code in front of
it. The pieces all exist — 325 missions as templates, `capability_receipt_lane_v1` as the admission
gate, `_states_an_executable_form` as the door's honesty rule. Nothing connects "a family with zero
owners" to "a mission, an adapter and a receipt". That connector is the last problem on this list and
the largest.

---

## 5. What this census has cost so far — three laws measured and killed

| | |
|---|---|
| merged, `32a73a0` | **A change must be promised by what ran, before it runs.** `provides` read as a change vocabulary. Closed both false passes — and **cost 15 working capabilities**, because `text.file.write` declares `text.file.available`: a fact that only becomes true *by changing the world*. Reverted in `6d172a8`. |
| built, measured, reverted | **The step-expectation law.** A composed step must satisfy its capability's declared `expect`. Killed **19 real questions**: `shell.command.run` declares `returncode == 0`, and for `cmp` the exit code *is the answer*. |
| built, measured, reverted | **The pre-execution change gate.** Alone it turned an honest failure into a false pass through the composer — the very defect it was written to stop. |
| merged, `6d172a8` | **A refusal is not answered by a substitute** (class G) and **class D's `add_parameter`**. Census unchanged at 2/28; false passes 2 → 1; the 394-test suite byte-for-byte identical to base. |
| merged this revision | **One verdict, sibling both ways, delivery is a destination** (above). Census **5/28 → 8/28**; three rows; one false pass unchanged. The sink vocabulary lost `loads`/`load`, which had made "parsed and returned a field" read as "reached `exec`". |
| merged, rev 9 | **A repair is an edit and a referee** — union for a stated two-sided conflict, call-site count for "single-use", restore-everything on failure, the suite as the proof. Census **8/28 → 10/28**; the SQL row withheld because the composer answers it with `rm`. |
| built, measured, reverted | **The artifact-noun rule** (§2.1). The word for the output is not evidence — true, and it changed nothing: the match moved from `report` to `run` and the false pass survived. Reverted. Four laws written, four killed, **zero of them by argument** — every one by running the machine. |

All three killed laws were defensible in advance and cheap to write. Each was wrong in a direction
the census cannot see: **it counts what passes, not what stopped being attempted.** That is class H,
and it is why the referee comes before any more law-writing.

---

## 6. Reproduction

```bash
python3 hardcore_swe_surface_probe_20261030.py --jobs 6          # 28 tasks      -> 10/28
python3 advanced_swe_probe_20261030.py --jobs 5                  # 10 tiers      -> 3/10
python3 hardcore_swe_surface_probe_20261030.py --only add_parameter       # class D
python3 hardcore_swe_surface_probe_20261030.py --only destructive_refusal # class E
python3 -m unittest canonical.tests.test_a_refusal_is_not_answered_by_a_substitute_v1
python3 -m unittest canonical.tests.test_three_answers_the_tree_already_had_v1   # 16 tests
python3 -m unittest canonical.tests.test_a_repair_is_an_edit_and_a_referee_v1    # 12 tests
```

§1.1 is reproducible by regex over `load_verified_registry()`. §2.1 by running the security-gate
sentence twice, once with its declared output file present and once without. §2.2 by running the
type-gate sentence and reading `compiler_detail`.
