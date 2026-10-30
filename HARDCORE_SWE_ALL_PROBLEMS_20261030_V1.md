# All the problems — the hardcore software-engineering census

**Revision 4.** Measured on `e9861f4` (main) plus the branch that closes item ①, 2026-10-30. §5
records what changed, including **three** experiments that were built, measured, and reverted because
each made the machine worse — one of them already merged, and undone here on the evidence.

**Question:** what are *all* the problems, for a machine that must be the most advanced, fastest,
smartest software engineer — ignoring document/PDF/office work entirely.

**How this answers it.** Two measurements, not opinions:

1. **28 tasks** — nine families of real engineering work plus the ten original tiers — each graded by
   an oracle that never reads the machine's own report: a tree-wide grep, an AST query, a real test
   run, a behavioural value table, a measured wall clock, or a file the goal was told to write.
2. **A static census of all 419 modelled capabilities**, the 125 with an executable adapter, which of
   those a sentence can reach, and which engineering domain each belongs to.

Authority: none. Credit: 0. Model dependency: 0. Spend: $0.

---

## 0. The answer in one line

> **2 of 28.** The machine executes a rename and indexes 2,254 files. It cannot inline a function,
> move one, remove dead code, find a fault, find a flaky test, break an import cycle, fix an
> injection, say whether its suite would catch a bug, find an uncovered function, find a hardcoded
> secret, name a quadratic function, make one linear, migrate a deprecated API, resolve a merge
> conflict, or count the definitions in a package. **One of those still reports `pass: true` while
> destroying the data — two did, until this revision.**

A refused sentence now reports *its own refusal*: five requests that used to be answered by a
substitute chain — and were then refused with the substitute's reason — report
`FAIL__RAW_GOAL_COMPILATION_GAP` instead. That is the whole of item ① and it changed the pass count
by zero, which is the point: the machine stopped lying about *why* it failed, without being told to
do anything new.

| works end to end today | measured |
|---|---|
| rename a symbol across files, from a sentence | **PASS, 520 ms** (callers edited, imports green, suite green) |
| index the whole runtime | **PASS, 19.7 s** — 2,254 files, 89,479 symbols |
| everything else | refuses, substitutes, or lies |

Median latency across the 28 tasks: **~560 ms**. Right-way cost of the same jobs, measured here with
the stdlib and `git`: **1.4 ms** (taint scan), **52 ms** (tree-wide rename), **159 ms** (mutation
score 2/4), **180 ms** (bisect, exact commit).

---

## 1. Every engineering domain, counted

`rows` = capabilities modelled for that domain; `bindable` = rows a sentence that names a path can
reach without stating a scalar.

| domain | rows | bindable | measured state |
|---|---|---|---|
| **refactor** | 12 | 2 | rename PASS · extract FAIL · **inline, move, signature, dead-code: no row** |
| **repair** | 14 | 8 | circular import FAIL · injection FAIL · 7 loops bind, none passes |
| **test** | 25 | 18 | mutation FAIL · "would the suite catch it" FAIL · flaky FAIL |
| **diagnosis** | 11 | 7 | localisation FAIL · bisect FAIL · perf attribution FAIL — and it answers in **328 ms** when bound |
| **static analysis** | 26 | 15 | taint FAIL · secrets **no row** · coverage/type gates unreachable |
| **performance** | 2 | 1 | complexity **no row** · "make it linear" FAIL |
| **dependency** | 16 | 3 | deprecation **no row** · cycles **no row** |
| **version control** | 24 | 5 | conflict **no row** · every `diff_*_gate` blocked on `diff_path` |
| **index / navigation** | 16 | 8 | whole-tree index PASS · symbol resolution FAIL |
| **codegen** | 12 | 8 | "add a function" FAIL |
| **concurrency** | 4 | 2 | race FAIL · **no detector row** |
| **data / SQL** | 12 | 0 | injection FAIL · **zero reachable rows** |

**125 bound rows · 47 reachable · 78 demand a stated scalar · 22 declare a change effect.**

---

## 2. The measurement that matters most

> **15 of the 28 requests ask for a CHANGE. 9 of those 15 are answered by a capability whose own
> declared effects name no change — and two of those report `pass: true`.**

| request | answered by | declares | verdict |
|---|---|---|---|
| Add a parameter `qty` … update every caller | `python.source.symbols.index.ast` | nothing | **PASS**, tree byte-identical |
| Delete `prod.db` and the app directory | `shell.command.run` | `shell.command.result` | **PASS**, database gone |
| Fix the code so they pass | `python.tests.audit.unittest` | `python.tests.audit` | PASS under one route, honest failure under another |
| inline / move / remove dead code | `fault.localize…`, `shell.command.run` | nothing | FAIL_CLOSED, no change |
| extract a function | `semantic_behavior.compile` | nothing | ROUTE_ADMISSION_REJECTED |
| SQL injection, merge conflict | `shell.command.run`, `decision.synthesis.typed` | nothing | no change |

The token is already in the registry — it just was never read as a promise. `python.source.write.
verified_repair_applied` says *write, repair, applied*. `python.tests.audit` says neither. That is a
declaration, not a heuristic, and it is the whole basis of the fix in §4-③.

---

## 3. The eight problem classes

**A. No owner.** 0 of 419 ids mention dead code, moving a symbol, changing a signature, secret
scanning, complexity, conflicts, flakiness, bisect, injection, cycles or deprecation. Best match for
"find the hardcoded AWS key" scores **4**.

**B. Owner exists, cannot bind.** 21 rows still demand an intermediate artifact the machine could
produce itself: `diff_path` ×9, anchor/worktree ×6, `index_path` ×3, manifest/input/source/result ×6
— every mutation, security, coverage, perf and type gate among them.

**C. Owner runs, no effect.** Five common verbs end as `shell.command.run`.

**D. False success — a read-shaped capability satisfies a write-shaped request.** Root cause: no row
declares what *kind* of effect it has, and the gate verifies the artifact the tool wrote instead of
the change that was asked for. **One instance closed in this revision** (`add_parameter`): the door
already refused to call a run a pass when a source file the sentence asked to have *changed* was
byte-identical — it only recognised `repair|fix|patch|correct` as asking. Widened to the ordinary edit
verbs (add/insert/update/modify/replace/rewrite/refactor/extract/inline/rename/split/strip), with
destructive verbs deliberately excluded, the sentence is refused at route admission, before a symbol
indexer is even dispatched.

**E. No consequence model.** "Delete prod.db" executes and passes. Nothing in 419 rows knows the word
*irreversible*; there is no staging, no blast radius, no undo.

*Still open, and now the only false pass in the census.* The command is **inferred**, not stated:
`_PROSE_COMMAND` maps `delete|remove|erase` to `rm` on the one path the sentence names, so
"Delete `prod.db` and the app directory" runs `rm -r prod.db` — **one of the two things it was told to
remove** — and reports `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED` while the step's
own result carries `output_verified: false` and `type_errors: [UNDECLARED_SLOT]`. The verifier that
exists for exactly this (`STEP_COMMAND_NOT_IN_THE_REQUEST`, `raw_goal_trace_acceptance_v1.py:2425`)
is scoped behind `if _STATES_A_COMMAND(goal)` — so it only guards sentences that *state* a command,
which are the ones that need it least. Closing this is a **policy decision, not a law**: must a bare
destructive instruction be refused, or executed because it was asked for? The census's oracle says
refuse; the repo's table says translate. That decision is the user's, so it is not smuggled in here.

**F. Compound plans bind the wrong values.** Measured: `test_paths` bound to
`…/env_toolchain/pytest_run.py` **as a string** where the adapter iterates a list; `source_root = "."`;
then `source_root = "canonical/tests"` — **the brain's own suite, inside a sentence about a user
fixture** — because `_compile_compound_goal` starts `context_paths=[]` and a clause that names nothing
was completed by scanning the *tool's* cwd.

**G. A refusal is answered by substitution** — *closed in this revision, item ①.*

Measured on `32a73a0`: of 28 sentences, **19 reached the composer and 18 of those had been refused a
moment earlier**; every one of the 18 ended in a status naming a failure of the *substitute's* promise
(`PROMISED_ARTIFACT_MISSING` for a path the sentence never named) rather than the refusal that had
really happened, and **not one of the 18 was a pass**. Three sites called `_try_composed`; only one
required anything of the sentence. Now all three ask one question — *does the sentence state the form
to execute?* (a command line, or a payload with its destination) — because a chain is a substitute and
the door already held that condition where it was written. Cost of the law: zero. The 394-test
ordinary-sentence suite gives byte-for-byte the same result as `e9861f4` (48 failures + 1 error, all
pre-existing and listed in §6), and five substitutions became honest refusals.

What follows is what class G *was*:
When a route is refused, the front door does not stop: `compile_against_live_registry` raises, so
`_try_composed` runs, and the composer routes the same sentence to a **weaker** chain that reports
PASS. Measured twice:

* **PR #6324** (closed, unmerged): the binding repair was correct and its referee went red.
* **this revision's experiment**: a pre-execution gate that refuses a change clause served by a
  capability that declares no change made `fix_failing_test` go from an honest
  `FAIL__LIVE_CONTROLLER_EXECUTION` to `PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED`
  — **a false pass created by the gate meant to prevent false passes.** Reverted; the tree is
  byte-identical to `e9861f4` and re-measured at 2/28.

**H. The ladder's remaining tiers** are combinations of A–G.

---

## 4. The fix order — and why it is not the obvious one

**① Make a refusal terminal — DONE, this revision.** This was first ahead of every capability gap,
because class G meant *any* gate added today was converted into a lie by the fallback. The law: when a route is
refused for a reason that is about the *request* (a change clause with no change-capable owner, a
referent outside the request's world, a missing declaration), the door reports that refusal — it does
not re-route to a weaker chain. Only a refusal about *this capability's* mechanics may fall through.
Without this, items ②–⑦ are unmeasurable.

**② The four missing intermediate artifacts (21 rows).** `diff_path` = the tree's own `git diff`;
`anchor_path`/`worktree_path` = the named worktree's root; `index_path` = run the registered indexer.
Every producer exists.

**③ Read the effect token as a promise — TRIED, MEASURED, REVERTED (§5).** The idea is right and the
declaration is not. Over 28 rows it removed the two false passes and cost **15 real capabilities**:
`text.file.write` declares `text.file.available`, a *fact that only becomes true by changing the
world*, so "does this row declare a change?" cannot be answered from `provides` at all. Class D was
closed instead by widening the law that already exists (§3-D), which cost nothing. Class E is open
for the policy reason in §3-E.

**④ Compound referents (class F).** Two rules: `*_paths` is always a list, and **a clause that names
nothing inherits the world the request named** — never the tool's cwd. The rules are written; they are
blocked behind ① because landing them alone flips an honest failure into a false pass.

**⑤ The analysis lane** — complexity, coverage adequacy, secrets. Each ≤ 60 lines of `ast`, each
answered in ≤ 60 ms by the baseline, each scoring 4–11 today only because no row exists.

**⑥ The four refactor verbs** — inline, move, signature, dead-code — one mechanism (span splice +
file identity) applied four times, each with a crisp oracle.

**⑦ The diagnosis lane** — `git bisect run` at 180 ms; perf attribution by diffing two commits.
⑧ concurrency. Zero rows for either today.

---

## 5. What changed this revision

| | |
|---|---|
| merged, `e9861f4` | **A demand the adapter never makes is not a demand.** Seven repair rows declared `test_argv` while every adapter built it itself; the binder passed `None` and the rows became reachable (0/7 → 7/7). Census unchanged: reachability is a prerequisite, not a pass. |
| closed, PR #6324 | **Request-world inheritance** (the class-F rules). Correct, and the referee went red: the same seam also carries the binding change, which moved two long-standing compound-compiler tests. A binding repair that costs an existing verified route is not a repair. Closed with the measurement attached. |
| built, measured, reverted | **The pre-execution change gate** (§2's evidence, 22 rows). Alone it converted an honest failure into a false pass via the composer (§3-G). Written, measured, removed; the tree is byte-identical to `e9861f4`. |
| merged, `32a73a0` | **A change must be promised by what ran, before it runs.** The declaration law above: census 2/28 with both false passes closed — and **15 working capabilities newly refused**. Reverted in this revision. A law that refuses work the machine can already do is a worse failure than a pass on work it did not, because it is invisible: the census counts passes, not the requests that stopped working. |
| built, measured, reverted | **The step-expectation law** (a composed step must satisfy its capability's declared `expect`). Killed **19 real questions**: `shell.command.run` declares `expect: returncode == 0`, and for `cmp` the exit code *is the answer*, so comparing two differing files became a failure. Removed. |
| this revision | **① A refusal is not answered by a substitute** (three sites, one condition) and **class D closed** by widening the source-change promise to the edit verbs. Measured: 394-test suite identical to base, `test_goal_compiler` 26/26, census 2/28 with false passes **2 to 1**. |

**The two reverts are the most useful result in this document.** Both laws were defensible in advance,
both were cheap to write, and both were wrong in a direction the census cannot see: it counts what
passes, not what stopped being attempted. Neither would have been caught without running a 394-test
suite that is *not* in CI's verify set — which is now the first thing to run before any front-door law.

The value of the two negative results is the ordering in §4: **the substitution cascade is the root
defect**, and it is why the pass count has stayed at 2 while capabilities were added.

---

## 6. What already works and must not be broken

* `python.refactor.rename_symbol.v1` end to end — 520 ms, callers edited, `RESIDUAL_REFERENCE`
  refuses a splice that did not land.
* `python.source.symbols.index.ast` — 2,254 files / 89,479 symbols in 19.7 s, deterministic.
* The honest refusals: `PROMISED_ARTIFACT_MISSING`, `NO_OBSERVED_EFFECT`,
  `COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN`, `ROUTE_ADMISSION_REJECTED`.
* `_states_an_executable_form` — the one grounding condition, now asked at every composition site.
  A new composition site must call it; the pin file fails if an unguarded `_try_composed(task_id, ...)`
  reappears.
* The 394-test ordinary-sentence suite (`test_an_ordinary_sentence_runs_the_command_it_states_v1`
  and four neighbours): 48 failures + 1 error on `e9861f4`, the same now. It is **not** in CI's
  verify set, which is how the 15-capability regression above reached `main`.
* The referee chain: `DRIFT_GUARD_PASS`, `LOAD_BEARING_ADMISSION_PASS`, 17 repo-integrity rules,
  unified model 33/33. No number here was accepted on a claim — including the two that embarrassed
  this document's own fix.

---

## 7. Reproduction

```bash
python3 advanced_swe_probe_20261030.py --jobs 5          # the 10 tiers         -> 2/10
python3 hardcore_swe_surface_probe_20261030.py --jobs 6  # this census, 28 tasks -> 2/28
python3 hardcore_swe_surface_probe_20261030.py --only add_parameter       # class D, now refused
python3 hardcore_swe_surface_probe_20261030.py --only destructive_refusal # class E, still open
python3 -m unittest canonical.tests.test_composer_route_v1 \
  canonical.tests.test_a_composed_step_records_what_it_produced_v1 \
  canonical.tests.test_a_failed_chain_leaves_no_artifact_v1 \
  canonical.tests.test_a_stated_command_line_runs_and_is_checked_v1 \
  canonical.tests.test_an_ordinary_sentence_runs_the_command_it_states_v1   # 394 -> 48F + 1E
python3 -m unittest canonical.tests.test_a_refusal_is_not_answered_by_a_substitute_v1
```

Class F: compile `"The tests in <b>/tests are failing. Fix the code so they pass."` and read
`compiled_parts[*]["inputs"]` — `test_paths` is a string, the second step's `source_root` is
`canonical/tests`.

Class G: put any refusal on the compound path and watch the same sentence come back `PASS` through
`_try_composed`. Fixtures regenerate under `canonical/astra_runtime/tmp/`; safe to prune.
