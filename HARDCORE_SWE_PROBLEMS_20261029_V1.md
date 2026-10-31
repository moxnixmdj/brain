# Every problem between this machine and being a hardcore software engineer

Measured 2026-10-29 on `main` `c79a8f5`, branch `arena/7ec91ca6-brain`, sandbox, Python 3.11.2.
Authority: **NONE** — this is a measurement, not an independent verification.
Model dependency: **0**. Incremental spend: **$0**.
Scope: hardcore software engineering only. PDF/DOCX/XLSX/codec/chart capabilities are out of
scope except where they are the *wrong-domain* destination of a SWE request.

Nothing below is inferred from reading a document. Every claim carries the probe that produced
it, and the exact command is given. Where an earlier document in this repo says something
different, the measurement here wins and the difference is called out.

---

## The one-line summary

The machine answers **"PASS"** for goals it did not accomplish (three separate, measured
mechanisms — §1), has **zero capabilities** for git, debugging, profiling, linting, type
checking, building, packaging or concurrency (§2), and **31 % of its software-engineering
registry is self-certifying stub code that always reports `verified: true`** (§2.2). Its
software-engineering score is measured on sentences the machine wrote for itself (§3.5), so
the score and the engineer are not the same object. The engineering substrate around it —
321 workflows, 2,128 runtime modules, 12 version-fan-out families up to v21, a 7,001-line
compiler, a 40–80 minute test suite and mutable state inside the tree — costs more than the
capability it exists to measure (§3).

Four defects were repaired in this session and are proven by test (§0). Everything else is a
named gap with a measurement and a fix direction.

---

## §0. Repaired in this session (so the rest of this document is current)

### 0.1 A cross-file rename returned PASS over a tree it had just broken — **fixed**

`python.refactor.rename_symbol.v1` renamed the def site and the `from m import s` sites,
reported `gate: PASS`, `complete: true`, `verified: true` — and left `app.core.helper(3)`
untouched in a third module. The tree then raised
`AttributeError: module 'app.core' has no attribute 'helper'`.

Root cause, measured: the cross-file harvest required the attribute receiver to be a bare
`ast.Name`:

```python
elif isinstance(node, ast.Attribute) and node.attr == old:
    v = node.value
    if isinstance(v, ast.Name):        # <-- every dotted receiver falls through
        ...
```

`import app.core` then `app.core.helper(...)`, and `from app import core` then
`core.helper(...)`, both have an `Attribute` receiver and matched **no branch at all** — no
edit, no `unknown_sites` entry, no refusal. `tested` was not measured; the tree was simply
wrong while the artifact was green.

Two laws are now enforced (`canonical/runtime/bound_capabilities/python_refactor_rename_symbol.py`):

1. **Resolution, not shape.** A new `_module_bindings` + `_receiver_module` pair resolves the
   full attribute chain to a module path (`import a.b` + `a.b.s` → `a.b`, `from a import b` +
   `b.s` → `a.b`, `import a.b as c` + `c.s` → `a.b`) and edits it when it provably denotes the
   renamed symbol's container.
2. **`DANGLING_REFERENCE_AFTER_EDIT`.** After every edit, the post-edit bytes of every file are
   re-parsed and re-resolved. If any receiver chain still provably resolves to the symbol's
   container and still spells the old name, the whole rename is refused and **not one byte is
   written**. This makes an unanticipated receiver shape a refusal instead of a green artifact,
   and it now also catches the method case (`mod.Class.method`), which the harvest never
   followed.

Measured after the fix: `app.core.assist(3)`, `core.assist(2)`, `from app.core import assist`
— and the renamed package is imported in a fresh interpreter and its functions called to prove
it (`other.c() -> 4`, `api.a() -> 2`). Method case: refuses with
`DANGLING_REFERENCE_AFTER_EDIT:app/use.py:4`, every byte restored.
New suite `canonical/tests/test_a_rename_never_leaves_a_dangling_reference_v1.py` (5 tests,
one of which is an independent in-a-fresh-interpreter oracle); the 18 pre-existing
`test_python_refactor_rename_symbol_v1.py` tests still pass (23/23).

Also fixed there: `run_tests: true` escaped the contract as an unhandled `TypeError`
(`list(True)`); it is now the typed refusal `RUN_TESTS_REQUIRES_EXPLICIT_PATHS`.

### 0.2 The patch search could not see any nested Python package — **fixed**

`python_test_guided_patch_search_v1._source_env` put only the *immediate parent* of the file
under repair on `PYTHONPATH`. A test that imports its module as a package — `import pkg.calc`,
which is what every real repository does — died with `ModuleNotFoundError` before one
assertion ran, so baseline and every candidate scored identically and the search reported
"no verified patch" for every bug.

Measured before the fix, `pkg/calc.py` = `def add(a,b): return a-b`,
`pkg/test_calc.py` asserting `add(2,3) == 5`:

```
tested_candidate_count : 1
patches                : []
status                 : OPEN__NO_VERIFIED_PATCH_IN_BOUNDED_LOOP
```

The identical pair as **flat siblings** (`calc.py` + `test_calc.py`, `import calc`):

```
tested_candidate_count : 1
patches                : 1  ("-    return a-b" / "+    return a + b")
status                 : PASS__VERIFIED_MULTI_EDIT_PATCH_FOUND
```

So the flagship repair capability worked only on layouts that no repository uses.
`_source_env` now also adds the **top of the package chain** — the highest ancestor that still
has an `__init__.py`, which is the importable root by definition, so nothing above the project
is ever added. After the fix the nested layout produces the `Sub->Add` patch and verifies it
twice. 78 pre-existing repair/patch-search tests still pass.

### 0.3 The door credited a patch it never ran — **fixed**

`_statement_patch_authority` accepted an unchanged source when a stated report carried a diff
that **applies**. Applying was the whole bar. It now runs the suite the sentence *named*
against the patched bytes (with a `finally` restore, because a gate that can leave a user's
source broken is worse than the over-claim it closes).

Measured directly on the gate:

```
GOOD patch (suite green on it) -> authority=True    source intact=def add(a,b):|    return a-b
BAD  patch (suite red  on it)  -> authority=False   source intact=def add(a,b):|    return a-b
```

The stated suite is read from the sentence itself (`declared_input_derivation_v1`), never
assumed: no stated test means no test is run, and the old behaviour stands.

`test_live_brain_route_admission_v1.py` after the change: **4 failed, 35 passed** — byte-identical
to the same file on pristine `c79a8f5` (4 failed, 35 passed). Those four are pre-existing fleet
drift, not this work.

### 0.4 Referee (all four repairs)

`python3 execution_guard/repo_integrity_guard_v1.py`
→ `mode=static+diff base=c79a8f54 rules=17 violations=0 -> PASS`

---

### 0.5 "Show the last three git commits": a false PASS replaced by a real capability — **fixed**

Two laws, one measurement each, and a new capability so the law has something to point at.

**(a) A repository file is not a capability.** `load_verified_registry` admits 293 inventory
rows, each keyed by the path of one of this repository's own Python files
(`"<path>.py.auto.v1"`), and the lexical selector ranks every token of that filename as
evidence about the goal. New predicate `inventory_source_path()` plus one gate in
`route_admission`: a path-keyed row is admitted only when the sentence names that path or that
id. Measured:

```
"Show the last three git commits"   -> FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
"three"                            -> FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
"Show the last seven git commits"  -> FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
"three region complement nonidentifiability" -> FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
   rule = INVENTORY_FILE_IS_NOT_A_CAPABILITY_UNLESS_THE_SENTENCE_NAMES_IT
"Run canonical/runtime/cursorbench_three_region_...py" -> still reaches it (PASS)
```

**(b) The git surface exists now.** `git.repository.operate.v1`
(`canonical/runtime/bound_capabilities/git_repository_operate.py`) with seven declared
operations — `log status diff show blame branch commit` — and no argv pass-through: the
sentence chooses the operation, and `OP_NOT_DECLARED` refuses anything else by name. Every
reported effect is re-derived by a *different* git plumbing command
(`log`↔`rev-list`, `status`↔`diff --name-only`, `show`/`commit`↔`cat-file -t`,
`blame`↔`merge-base --is-ancestor`, `branch`↔`rev-parse`) and a disagreement is a refusal.
Determinism: `--no-pager`, `LC_ALL=C`, `core.abbrev=40`, `TZ=UTC`, no system config, no
prompt — two runs produce byte-identical artifacts. `commit` records **only what was staged**;
`git add -A` is reachable only by an explicit `staged=false`, because sweeping the working
tree is a much larger promise than "commit the staged changes".

Wire, four small pieces, no new primitive: `op` derived from the stated verb
(`_GIT_OPERATION_GRAMMAR`, ambiguity ⇒ nothing), `limit` derived from the stated count
("the last three git commits" ⇒ 3, not 20), `"git."` added to the derivation scope and the
typed-plan family prefixes, and F4 (`is_plain_goal_routable`) now judges the **declared**
contract instead of the binding shadow — F4 asks a question about the capability, and the
shadow exists only to decide what the binder must still be asked.

Measured end to end:

```
"Show the last three git commits" -> PASS, capability git.repository.operate.v1,
   basis DECLARED_INPUT_CONTRACT_FULLY_STATED_IN_GOAL, op=log limit=3,
   rows = [{sha: 5d2b0cfaf5ef, subject: "A rename may not report PASS over a tree it broke..."},
           {sha: c79a8f544fe4, subject: "The write rule is the action, ..."}]
"Show the last seven git commits" -> PASS, op=log limit=7
"Commit the staged changes with the message 'wip'" -> binds op=commit
"who wrote line 3 of pkg/calc.py" -> binds op=blame      "show me the diff" -> op=diff
"what is the status of the working tree" -> op=status    "list the branches" -> op=branch
```

Tests: `canonical/tests/test_git_repository_operate_v1.py` (16) and
`canonical/tests/test_git_sentence_routing_v1.py` (9). The oracle for every read is the `git`
CLI invoked by the test itself on the same repository — not the adapter's own parse.
Receipt: `canonical/astra_runtime/evidence/ASTRA-VERIFY-GIT-REPOSITORY-OPERATE-001__RECEIPT.json`,
`authority: NONE`, `carrier: SANDBOX`, 0 disagreements across the 7 operations.

**Zero regressions, measured against pristine `c79a8f5` in A/B**, over every test that imports
the two shared modules this touches: pristine `56 failed, 400 passed`; with these changes
`56 failed, 409 passed` (+9 new). `test_swe_typed_plan_v1.py` 17/17,
`goal_compilation_benchmark_v1` unchanged at `COMBINED 21/23`, same 2 WRONG-CAPABILITY rows.

**(c) A metaphor is not a repository operation.** Two false PASSes were found by adversarially
probing the new grammar itself, and both are now pinned:

```
"Branch out the new feature into three modules" -> bound op=branch, ran `git branch`,
                                                   returned PASS          (now: fails closed)
"Commit the transaction to the database"        -> bound op=commit, would have CREATED a
                                                   commit in the caller's repository
```

The branch rule now requires an imperative or a question (`list/show/git ... branches`,
`branches`, `which branch`), never the bare noun — and the one DESTRUCTIVE operation requires
repository context in the sentence (`git`, `staged`, `changes`, `working tree`, `branch`,
`repo`, `uncommitted`, `history`). **Reading the wrong repository is a wrong answer; committing
into it is a wrong change**, so the bar is higher. Third law, same family: `commit` records only
what was already staged, and `git add -A` is unreachable without an explicit `staged=false`.

**(d) Speed.** A stated git operation now takes the typed route FIRST instead of paying a
lexical compile that is discarded by construction (the module already declared a stated SWE
effect family AUTHORITATIVE). Measured `solve()` on git goals: **median 452 ms → 269 ms**
(single goal 353 ms → 218 ms; the primary compile alone was 135 ms of it). The fast path is
scoped to the git family on purpose — measured: running it for every family changed a
caller-finding verdict from PASS to `WRITE_AUTHORITY_REFUSED`, and **a speed change may not
alter a verdict**.

**Honest scope.** Seven operations. No push, rebase, merge, reset or history rewrite. `op` is
derived only from a verb; a sentence that states two operations binds neither. The 56
pre-existing failures in the slice above are a separate, untouched backlog.

---

### 0.6 A tool that printed "no" was credited as a pass — **fixed**

§1.1's defect, made systematic by one missing read. Capabilities executed through the generic
command adapter (`bound_capabilities/cli_command.py`) do not return a verdict — they return
an **envelope**:

```json
{"adapter": "bound_capability_cli", "argv": ["python3", "..."],
 "returncode": 0, "stdout": "<the capability's own JSON>", "stderr": ""}
```

`tool_truth_errors()` read `pass` and `status` off the envelope, where neither key exists,
found nothing, and returned `[]`. The verdict was one string away, on `stdout`, and was never
read.

**Measured on c79a8f5** over the 616 CLI-shaped registry rows, each run through
`capability_receipt_lane_v1.run_cli_adapter` — the same runner that issues their receipts:

```
616 CLI-shaped rows
183 run and print JSON
120 print "pass"      148 print "status"
 21 print a NON-SUCCESS verdict with exit code 0
  0 of those 21 were visible to the truth check
```

Five of them through the real door, before → after:

```
run ...professional_quality_leaf_binder_v1.py.auto.v1
   printed {"pass": false, "status": "OPEN__DOMAIN_LEAVES_OR_EVIDENCE_FRESHNESS_REMAIN"}
   PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
      -> FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS
run ...verify_terminal_scheduling_v11_candidate_v1.py.auto.v1
   printed {"pass": false, "status": "FAIL_CLOSED__SOURCE_BLOB_DRIFT"}
   PASS__RAW_GOAL_..._EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
      -> FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS
   ... target_role_escape_frontier_v1, v13_db_existing_evidence_saturation_verifier_v1,
       shared_channel_dominator_v1: same shape, same outcome.
```

**The whole blast radius, measured, over all 183 runnable rows — pristine `c79a8f5` vs this
tree, same corpus, same goals:**

| | PASS | FAIL |
|---|---|---|
| pristine `c79a8f5` | 174 | 9 |
| this tree | 153 | 30 |

**21 moved PASS → FAIL. 0 moved FAIL → PASS. Every one of the 21 is a capability whose own
stdout says it failed, and there is no other change of any kind.** That is the whole delta,
and it is fully accounted for — which is what makes it a repair rather than a tightening.

**The rule now has two sides, on purpose.** `pass: false` or a
`FAIL*`/`OPEN*`/`UNRESOLVED*`/`ERROR*`/`BLOCKED*`/`REJECTED*`/`INCOMPLETE*` status on the
printed payload fails the step; `pass: true` with a `PASS*` status still passes; **prose is
not a verdict** and is left alone; an exit code is not a verdict either (`diff` exits 1 to
say "these differ", which `cli_command` already documents). A check that only ever says "no"
would be the next bug, so all four directions are pinned.

**The identity half.** If the printed payload names a `capability_id` and it is not the
capability that ran, the step is refused with
`TOOL_ANSWERED_A_DIFFERENT_QUESTION:<ran>:PRINTED:<named>`. Only `capability_id` is compared:
in this repository that name is unambiguously a registry id, while `capability` is also used
for family and adapter names and cannot be judged.

**One discriminator, deliberately narrow.** An envelope is recognised by carrying *both*
`returncode` and `adapter`. Measured over the 147 adapters: exactly one (`cli_command.py`)
emits `returncode` + `stdout` + `adapter` + `argv` together, and the three that put
`returncode` beside `stdout` do so inside a per-test record. Requiring both keys is what stops
a test runner's output being unwrapped as the capability's verdict — which would be §1.1's
mistake running backwards.

Tests: `test_the_tool_s_own_printed_verdict_is_the_verdict_v1.py` (18). One existing test
needed a fixture repaired, not an assertion changed: it reached three path-keyed inventory
rows by *prose*, which §0.5(a) now refuses before anything runs; the goal names the capability
instead and the law it states — a tool that ran and said no must report its own cause — is
untouched and still green.

#### The fix order, updated

| # | item | state |
|---|---|---|
| 1 | a path-keyed row is not a capability, a stated op is not a filename | **done** (§0.5) |
| 2 | the git object model as a real capability | **done** (§0.5) |
| 3 | a printed "no" is not a pass | **done** (§0.6) |
| 4 | bind the remaining hidden adapters through `derive()` | open |
| 5 | a human-sentence corpus with a tree oracle, per-adapter latency/bytes | open |
| 6 | fan-out collapse, `goal_compiler.py` split, `pyproject.toml` | open |

## §1. P0 — the machine says yes when it means no

Three independent mechanisms, each with its own repro. This is the class that makes every
other number in the project untrustworthy, because a measurement cannot see a lie the
measurement tool tells.

### 1.1 A single word selects a capability and returns PASS — **the whole world**

```
goal  : "Show the last three git commits"
status: PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
pass  : True
semantic_acceptance_complete : True
independent_reinspection     : True
compiled_capability_id : canonical/runtime/cursorbench_three_region_complement_nonidentifiability_v1.py.auto.v1
route_admission.matched_tokens        : ["three"]
route_admission.admission_basis       : DECISIVE_LEXICAL_MARGIN
route_admission.lexical_margin        : 0.36662357292334863
execution[0].result.stdout            : {"schema": "..._THREE_REGION_COMPLEMENT_..._V1",
                                         "pass": true,
                                         "status": "PASS__THREE_REGION_COMPLEMENT_EMPTINESS_
                                                    NOT_IDENTIFIED_BY_CURRENT_EVIDENCE__ZERO_CREDIT",
                                         "total_distinct_condition_atoms": 18, ...}
```

Nothing about git was read and no commit list exists — but the result was **not** empty, and
that is the sharper defect: a set-theory verifier ran, and *its own stdout says `"pass": true`
about a statement in set theory*. The door read the tool's self-assessment of a different
question as the verdict on the caller's sentence. The word **"three"** matched a *filename*.

Reproduced with `"three"` alone (PASS), `"Show the last seven git commits"` (PASS, via
`root3_seven_class_one_substrate_*`), and `"three region complement nonidentifiability"`
(PASS). 14 goals total: 11 correctly fail closed, **3 return PASS and all 3 are false**.

Why it is possible: the extended registry is an *inventory of the repository's own Python
files* (`canonical/runtime/autonomous_capability_inventory_v1.py`: every `canonical/**/*.py`
becomes `"<path>.auto.v1"`). 2,309 such rows exist. `load_verified_registry()` admits **293**
of them by receipt evidence, and the lexical selector then ranks *path tokens* as evidence.

**Fixed 2026-10-29** (§0.5). A capability id that is a path is not a capability id, and a
program's opinion of itself is not an observation of the world. The remaining half of the
defect — an obligation that names git being discharged by a result that never mentions git —
is now moot for this goal because the git capability answers it. The general rule is now
**half** mechanical (§0.6): a step whose payload names a *different* capability is refused,
and a step that printed `pass: false` can no longer be a pass. What still does not exist is
the general check that the *content* of a result bears on the *content* of the obligation —
"this JSON says nothing about the sentence" remains unexpressible, and only the identity half
of it is decided.

### 1.2 The user's source is still broken and the answer is PASS

```
goal  : "Repair the python source <D>/pkg/calc.py so that the unit test <D>/pkg/test_calc.py
         passes, and save the repair report to <D>/a.json."
status: PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED
capability : python.software.repair.loop.test_guided.ast.v1
source after: def add(a,b):|    return a-b        <-- unchanged, test still red
```

The adapter is honest: it declares `NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY`, finds and verifies
the patch, then restores the source in a `finally`. The door's `promised_source_change_errors`
gate then sees an unchanged file and `_statement_patch_authority` grants authority because the
stated report carries a diff that applies. **The sentence "Repair the python source X" is
answered PASS while X is byte-identical and its test fails.**

This is a recorded policy choice, not an accident:

> `promised_source_change_errors` docstring: *"A repair verb is not always a promise to write
> in place. When the sentence also states where the repair report goes, the promised result is
> the patch, and the file is untouched by design."*

And the bench oracle trains exactly that reading (`live_solver_families_v3.py:430` demands
"untouched source plus one applicable patch in the report"). **The instrument and the user
disagree about what a repair is, and the instrument wins.** §1.3 is the same defect from the
other side.

**Fix direction**: the door must decide the *effect* from the sentence, not from the artifact.
An imperative on an existing source file with no stated report is a write promise; a patch that
applies but was not applied is not a repair. Then change the family oracle in the same PR, so
the bench and the door measure one thing.

### 1.3 The measured SWE score is 0 of 10 human sentences, and the one PASS was false

Ten fresh human software-engineering sentences, one `solve()` each, fresh fixture per run
(three-module package `pkg/{calc,util,test_calc}.py`, `add()` returning `a-b`):

| task | verdict | reached |
|---|---|---|
| repair_full | `FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS` → **PASS after §0.2/§0.3** | repair loop |
| fix_short | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | `semantic_behavior.compile` |
| bug_report | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | — |
| find_callers | `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | `semantic_behavior.compile` |
| rename_param | `FAIL__LIVE_CONTROLLER_EXECUTION` | **`document.convert.markdown_pdf.pandoc_weasyprint`** |
| write_test | `FAIL__LIVE_CONTROLLER_EXECUTION` | **`chart.raster.axis_title_unit_binding.v1`** |
| lint | `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN` | — |
| typecheck | `FAIL__LIVE_CONTROLLER_EXECUTION` | `python.contract.check.crosshair.v1` |
| explain_fail | `FAIL_CLOSED__WRITE_AUTHORITY_REFUSED` | `code.impact.tree_sitter.testselect.v1` |
| git_log | **PASS** | `cursorbench_three_region_*.py.auto.v1` (false, §1.1) |

**0 / 10 honest. The one PASS is the false one.** `rename_param` reaching a markdown→PDF
converter and `write_test` reaching a chart legend reader are not near-misses; they are
different domains chosen because one word matched.

The compile benchmark says the same on its own rows:

```
python canonical/runtime/goal_compilation_benchmark_v1.py
  COMBINED: compiled 21/23, expected capability selected 19/23
  compiled against the WRONG capability: 2
  EXT_XLSX_CREATE   -> auto.pypi.msgpack  WRONG-CAPABILITY
  EXT_SQLITE_VERIFY -> auto.pypi.msgpack  WRONG-CAPABILITY
```

The benchmark prints `OK` for a row that reached the wrong capability, because "OK" means "it
compiled". **Compiling is not selecting**, and the instrument's own label hides it.

### 1.4 `solve()` mutates the repository it is solving in

Every `solve()` call rewrote **tracked** file `canonical/runtime/state/experience_v1.json`
(74 insertions: `last_seen` timestamps from `time.time()` and appended observation vectors), and
left untracked state in the tree:

```
canonical/astra_runtime/state/*__live-raw-goal-controller__CONTROLLER_CHECKPOINT.json   (9 files)
canonical/astra_runtime/state/{ASSOCIATIVE_MEMORY_V1,IGNORANCE_LEDGER_V1,JIT_KNOWLEDGE_SOURCE_VALUE_V1}.json
canonical/tmp_{loop_cegis_0,loop_choreo_0,patch_review_supercomposer,fault_patch_supercomposer,...}.json
gz18554, gz7056
canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json          (rebuilt because the tree moved)
```

Consequence: **run 2 of the same goal is not run 1.** That is the root cause of the
"same input, two verdicts" class in `HARDCORE_SE_PROBLEM_INVENTORY` P2-8, and it is also why a
single-line edit triggers a 9.4 MB unified-model rebuild. No capability can be trusted while
its own execution moves the ground it is measured on.

**Fix direction**: state belongs outside the tree (one `BRAIN_STATE_DIR`), and `solve()` must
be a pure function of (goal, tree bytes).

---

## §2. P0 — the software-engineering surface that does not exist

### 2.1 What is registered, counted by id, over the 125 verified capabilities

| surface | capabilities |
|---|---|
| python repair / patch search | 11 |
| python review gates (type, security, perf, coverage, mutation) | 6 |
| python source index / symbols / impact | 6 |
| refactor / test scaffold | 4 |
| shell / terminal | 2 |
| git (log, diff, commit, branch, blame, show, status) | **1** — added 2026-10-29, §0.5 |
| git (merge, rebase, bisect, reset, history rewrite) | **0** |
| **dynamic analysis (trace, debugger, breakpoints, post-mortem, delta-debug)** | **0** |
| **profiling / benchmarking / complexity / memory** | **0** |
| **lint / format (ruff, flake8, black, eslint)** | **0** |
| **type checking (mypy, pyright, tsc)** | **0** |
| **build systems (make, cmake, cargo, gradle, bazel)** | **0** |
| **packaging (wheel, sdist, lockfile, semver, venv)** | **0** |
| **concurrency (threads, async, race detection)** | **0** |
| **LSP / incremental index / language server** | **0** |
| **migrations / ORM / SQL schema** | **0** |

```
grep -c for each term over canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json:
git 0, debug 0, trace 0, profile 0, pdb 0, bisect 0, blame 0, branch 0, commit 0, merge 0,
lint 0, mypy 0, ruff 0, flake 0, bench 0, concurrency 0, thread 0, async 0, build 0,
packaging 0, wheel 0, virtualenv 0, docker 0, k8s 0, make 0, cmake 0, cargo 0, lockfile 0,
semver 0, migration 0, orm 0, grpc 0, lsp 0
```

A software engineer cannot work without git and a debugger. These are the first two tools
reached for when a test fails in a way that is not a one-line bug, and the machine has neither.
Both substrates are already installed (`git` CLI, `sys.settrace`, `cProfile`, `pdb` in batch
mode). Nothing needs to be bought; nothing exists.

The 64 SWE-prefixed rows that *do* exist are also structurally shallow: every one is single
file, stdlib only, and the "advanced" ones are compositions of the shallow ones.

### 2.2 20 of the 64 SWE capabilities are self-certifying stubs — and all 20 report `verified: true`

Every adapter that reads `BOUND_CAPABILITY_REGISTRY_V1.json`, checks that some capability ids
appear in it, and writes `{"verified": ...}` — 28–30 lines each:

```
python.contract.issue_orchestration.fusion.v1     python.patch.review.supercomposer.v1
python.evidence.contract.supercomposer.v1         python.pipeline.allowlist_gate.v1
python.fault.patch.supercomposer.v1               python.pr.land.composer.v1
python.fault.provenance.fusion.v1                 python.provenance.coupling.supercomposer.v1
python.orchestration.symbol.supercomposer.v1      python.refactor.test_scaffold.fusion.v1
python.symbol.resolve.standalone.v1               software.evidence.synthesis.supercomposer.v1
python.test.pipeline.verifier.v1                  software.hardcore.closing.supercomposer.v1
software.review.gate.composer.v1                  software.hardcore.final.supercomposer.v1
software.review.synthesis.supercomposer.v1        software.hardcore.swe.supercomposer.v1
software.test.contract.supercomposer.v1           test.slice.never_miss.v1
```

Executed directly, with a repo-local output path:

```
stubs returning verified=True: 20 / 20
```

They do no work. They assert that *other capability ids exist* and write
`{"verified": true, "model_dependency_count": 0}` to a JSON file. All 20 are registered as
`VERIFIED_BOUND_CAPABILITY` in the real registry. That is 31 % of the software-engineering
surface and 16 % of the whole registry.

This is the exact class `AGENTS.md` rule 6 forbids ("no tautologies"), sitting inside the data
the rules protect. And `canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` is a
**protected path** (`CODEOWNERS`, owner-only), so an agent cannot remove them.

**Fix direction**: delete the 20 rows and their adapters, or make each one compose and execute
the real adapters and return their observed effect. A registry row whose adapter cannot be
distinguished from `echo '{"verified": true}'` is not a capability.

### 2.3 Zero SWE capability carries independent-oracle credit

`canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json`: **9 rows, 0 software
engineering** (4 DOCX, finance, scheduling, scheduling-Pareto), and `canary_pass` is `0/0` on 8
of the 9. By the project's own law (`TRUE_CAPABILITY_TEST_LAW_V1`, `VERIFICATION_IS_SOMEONE_ELSE`)
none of the SWE work in §2.1–§2.2 has any credit at all.

### 2.4 The cross-file rename is now correct, but the rest of the refactor surface is one verb deep

`rename_parameter`, `rename_symbol`, `extract_function` exist. **No** inline, move, safe-delete,
change-signature, codemod, or formatting-preserving splice for anything but these three. And
`extract_function` / `crossfile_edit.choreograph` have never been measured from a sentence.

---

## §3. P1 — the engineering substrate costs more than the capability

### 3.1 Scale without structure

```
files          4,754 .py    9,434 .json    169 .md
python LOC     801,385
canonical/     205 MB (99 % of the repo)
canonical/runtime/  2,128 modules
tests          2,142 test files, 14,168 collected cases
workflows      321 .github/workflows/*.yml
```

There is **no packaging metadata at all**: no `pyproject.toml`, no `setup.py`, no `tox.ini`, no
`Makefile`, no dev requirements. The only requirements file
(`requirements/software_engineering_kernel_v1.txt`) is pinned by SHA-256 and **no workflow runs
`pip install -r`** on it. So the suite cannot even *collect* on a clean machine:

```
python3 -m pytest canonical/tests --collect-only -q
  14168 tests collected, 33 errors in 25.14s
  ModuleNotFoundError: No module named 'PIL'   (chart/raster/osworld/PDF modules)
```

### 3.2 Version fan-out instead of refactoring

```
21x  r2_direct_end_to_end_adequacy_*        19x  osworld_v21_brain_subject_*
15x  source_aligned_semantic_proof_*        13x  osworld_v21_workflow_policy_*
12x  universal_verified_adaptive_solver_*   12x  retrieval_live_provider_arena_*
 8x  cross_document_effect_semantic_lattice_{,_verify}_v1..v8
```

36 module pairs at token-shingle Jaccard > 0.7, i.e. near-identical files kept side by side:

```
0.99  trajectory_failure_typed_ir_candidate_v5  / _v6
0.98  harbor_science_agent_v12 / _v13
0.98  cross_document_effect_semantic_lattice_v6 / _v7 / _v8
0.97  cross_document_effect_semantic_lattice_verify_v6 / _v7 / _v8
```

There is no deprecation, no supersession record, no import indirection. Every fix has to be
found in up to 21 places, and new readers cannot tell which one is live. This is the single
biggest tax on every future change.

### 3.3 The core is two monoliths

```
canonical/runtime/goal_compiler.py                 7,001 lines, 130 defs, 858 `if`s
canonical/runtime/live_brain_route_admission_v1.py 2,443 lines (+250 today)
```

Both are the *entire* front door. `goal_compiler.py` is the lexical selector — the thing §1.1
and §1.3 show selecting wrong — and it is "pinned by governance records", so the door
(`live_brain_route_admission_v1`) grew to 2,443 lines of compensating gates instead of the
selector being fixed. Every new honesty gate is another `if` in the door. That is how a
project ends up with 17 referee rules and still no way to say "this row is wrong".

### 3.4 The suite is too slow to be a gate, and it is red on pristine main

- Full suite, measured: **19 % in 900 s** → 40–80 min projected; the heartbeat's own comment
  records `>40 minutes against a 40-minute timeout`, cancelled on 17 of the last 20 runs.
- One file alone: **280 s** (`canonical/tests` sample, 4-way parallel, 240 files → 281 s wall,
  of which a single file was 280.9 s). No `pytest-timeout`, so one hang costs a whole job.
- Failure rate on pristine HEAD, random 240-file sample (2,405 cases):
  **53 failed, 3 collection errors, 2,349 passed ≈ 2.2 %.** Extrapolated over 14,168 cases:
  **≈ 310 failing cases on `main` today.**
- `test_live_brain_route_admission_v1.py` alone: **4 failed / 35 passed** on pristine `c79a8f5`.
- 33 collection errors are pure missing dependencies.

So "green" is not a signal the project has, and the honest baseline document (344 failures,
2026-10-14) is already stale.

### 3.5 The SWE score is measured on machine-authored sentences

The 37-family end-to-end suite generates each instance's goal text in the exact shape the
binder expects, from the capability's own id words. The reachability census
(411/419 "reached and bound") is generated the same way. Against 10 real human sentences the
same machine scores 0/10 (§1.3). **The instrument measures template understanding; the score
is a ceiling on the template, not on the engineer.** The inventory's own words: "a self-
fulfilling instrument. It cannot distinguish a capability a user can reach from one only its
own name can reach."

The suite also does not contain a single real-repository family: no git history, no multi-file
edit, no package layout, no import graph, no concurrency, no performance, no flaky test, no
build system, no dependency resolution.

### 3.6 Determinism hazards are structural

```
29 runtime modules `import random`;   38 `random.` call sites without an explicit seed
62 `time.time()`;  150 `perf_counter`;  11 `datetime.now()/utcnow()`
112 `urlopen`/`requests` sites;  426 `subprocess` sites
```

plus the tracked mutable state of §1.4. Verdicts are a function of wall-clock time, the
network, the process table and prior runs. The inventory already measured the consequence
("run 1: PASS, run 2: FAIL_CLOSED" for the identical goal) and the root cause was never
isolated — §1.4 is that root cause.

---

## §4. P1 — the composition and selection machinery that does not compose

### 4.1 The composition graph is dead

```
distinct `provides` across the registry : 187
never consumed by any `requires`       :  86
rows declaring `requires: []`          :  41
```

`orchestration.bridge_table.verified` has **0 consumers**; `bridge_enumeration_v1` proves
bridges by execution and its output never reaches `capability_composer_v1.graph()`.
`astra_runtime` implements `provides_as` / `requires_as` aliases that nothing feeds.
"Compose capabilities to build software" is a claim, not a running mechanism — the 20 stubs of
§2.2 are what "composition" produced.

### 4.2 No cost, latency or size model — so "fastest" is unimplementable

```
registry rows with a `cost` field        : 125 (100 %)
distinct cost values                     : {1: 107, 2: 18}
rows with latency / p50 / bytes / timeout:   0
adapters exposing timing or bytes        :   0
```

The owner's goal is *"the fastest way with minimal actions"*. The machine has a two-valued
constant where a cost model should be. It cannot prefer the fast correct capability, cannot
budget, cannot honour the resource-bounded-bytes law, and cannot say why one plan is cheaper
than another. Every "fastest" statement is currently unmeasured at the capability layer.

Measured end-to-end latency for the record: import 79 ms warm / 431 ms cold; `solve()` median
**98 ms** when nothing executes, **374–1 500 ms** when a real adapter runs; the typed SWE
selector alone is ~119 ms, and on a primary failure the retry re-enters the **entire** gate
chain a second time (compile + execute + every honesty gate) with no reuse of the first plan.

### 4.3 Negative binding is not applied before ranking

The predicate that would exclude a capability whose declared inputs cannot bind the sentence's
paths (`request_may_select`) exists and is not applied to the catch-all rows or the `auto.*`
rows. That is why `pdf.extract.ocr.tesseract` wins a refactor and `chart.raster` wins a test
authoring request. 8 of the 10 `INV_` families still reach no owned adapter from a sentence.

### 4.4 Type-level determinism is shallow

0 adapters import `z3`. `program_synthesis_v1` and `documentation_mining_v1` are not in the
admission path. Typed selection is deterministic but is keyword overlap plus a small effect
vocabulary — which is why `EXT_XLSX_CREATE → auto.pypi.msgpack` still happens.

---

## §5. P2 — governance that blocks the fixes above

These are **owner-only**; an agent cannot land them, and each one blocks work in §1–§4.

1. **`BOUND_CAPABILITY_REGISTRY_V1.json` is a protected path.** The 20 stubs of §2.2 and the
   wrong-domain rows of §4.3 cannot be removed by an agent. Every fix has to route around data
   that is frozen wrong.
2. **The heartbeat is not a required check.** The only required check is
   `referee/repo-integrity-guard`, which is a *structural* guard — it cannot tell whether the
   machine can do anything. `live-brain-heartbeat` is red or cancelled on every recent run
   (>40 min against a 40-min timeout) and is not required. So nothing public blocks a merge
   that makes the machine worse. Making it required **and sharding it** (`--jobs`, the flags
   already exist) is a one-time owner action.
3. **Protected paths generally** (`AGENTS.md`, the guard, its test, the referee workflow,
   `frontier-state-consistency.yml`, `CODEOWNERS`, the policy, the honest-baseline tool and
   document, the landing script) mean any change to how honesty is *measured* needs the owner
   in person. Correct as a rule; it does mean agent work can only ever go around the
   instrument.
4. **30 `HARDCORE_VERIFY_*` receipts are tautological** — `verified: true`, each repeating the
   producer's own hash, none naming a different verifier or a run reference, in direct
   violation of `VERIFICATION_IS_SOMEONE_ELSE`.
5. **321 workflows, most one-shot.** Each trigger-file workflow is a permanent cost in review
   surface, secret scope and CI minutes, and none of them is the gate that matters (§5.2).

---

## §6. The fix order (by damage per unit of work)

1. **Make PASS mean what it says** (§1.1, §1.2, §1.4). Three gates, no new capability:
   path-shaped ids out of the selector's token space; a non-empty obligation cannot be
   discharged by an empty result; a repair imperative on a stated file with no stated report
   requires the file to change. Then move `experience_v1.json` and the checkpoints out of the
   tree. Nothing else is worth measuring until a PASS is a fact.
   *Done so far:* path-shaped ids out of the token space (§0.5a), and the printed verdict read
   instead of the envelope that carried it — 21 capabilities that had been credited as passes
   while printing "no" (§0.6). *Still open:* a non-empty obligation discharged by an empty
   result, and the general rule that a result must bear on the obligation by content, not just
   by identity.
2. **Delete the 20 stubs** (§2.2) — owner action, one registry edit — and re-run the census.
   The real SWE surface is 44 rows, not 64. Every number the project quotes improves in
   honesty the moment this lands.
3. **Build the two missing surfaces** (§2.1): git object model first (read history, diff,
   commit, branch — `subprocess` + the `git` CLI, no model), then dynamic analysis
   (`sys.settrace`, `cProfile`, `pdb` in batch mode). Both substrates are already installed.
   *Done:* `git.repository.operate.v1`, seven declared operations, §0.5. *Still open:* dynamic
   analysis — 0 capabilities for a debugger, a profiler, a linter, a type checker, a build or
   an LSP.
   Without them no claim of "advanced software engineer" survives one honest reviewer.
4. **Measure a real repository** (§3.5): replace the machine-authored sentence corpus with a
   human-sentence corpus whose oracle is the tree (does it still import? do the stated tests
   pass? is the stated file different?). The tooling exists — §0.1 uses exactly this oracle.
5. **A cost model** (§4.2): one measured `latency_ms` / `peak_bytes` per adapter, written by the
   adapter, recorded by the door. Then "fastest" becomes a statement the machine can make.
6. **Then** refactor: collapse the version fan-out (§3.2), split `goal_compiler.py` (§3.3),
   add `pyproject.toml` + a dev lockfile + `pytest-timeout` + sharding (§3.1, §3.4).

---

## §7. What is genuinely solid (so the list above is a gap list, not a dismissal)

- `python.source.symbols.index.ast` is real: a full stdlib-AST index with a verified effect
  (`symbols 86,796`, `references 579,194`, `call_edges 221,482`, `files 2,196`).
- `python.refactor.rename_symbol.v1` is now correct across the receiver shapes measured, and
  refuses rather than breaks on the ones it cannot prove (§0.1).
- The test-guided patch search is a real bounded CEGIS-free search with a real candidate space
  (BinOp / Compare / BoolOp swaps, constant substitution from test literals, `not` insertion),
  and it verifies twice before claiming. It now works on real package layouts (§0.2).
- The fail-closed discipline in the door is genuinely good: 11 of 14 nonsense goals were
  refused, and the two known destruction paths (write-authority over a stated source, the
  composed-artifact-over-source bug) are gated.
- The independent-oracle machinery (`true_capability_harness_v1`, witness and counterexample
  gates, receipt lanes) exists and is more than most projects have. It is simply not pointed at
  the software-engineering surface.

---

## §8. Repro

```bash
# §1.1 — one word returns PASS
python3 - <<'PY'
import sys; sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
r = adm.solve({"task_id":"x","goal":"Show the last three git commits"})
print(r["pass"], r["status"], r["compiled_capability_id"],
      r["route_admission"]["matched_tokens"], r["execution"][0]["result"])
PY

# §1.2 — PASS over a still-broken source
#   fixture: pkg/calc.py "def add(a,b): return a-b"; pkg/test_calc.py asserts add(2,3)==5
#   goal   : "Repair the python source <D>/pkg/calc.py so that the unit test <D>/pkg/test_calc.py
#             passes, and save the repair report to <D>/a.json."
#   result : status PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED,
#            calc.py still "return a-b"

# §1.3 — the compile benchmark hides wrong-capability behind "OK"
python3 canonical/runtime/goal_compilation_benchmark_v1.py

# §2.2 — 20/20 stubs report verified: true
python3 - <<'PY'
import json, importlib, pathlib
ROOT = pathlib.Path('.').resolve()
reg = json.loads((ROOT/'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json').read_text())['capabilities']
out = ROOT/'canonical/astra_runtime/tmp/stubaudit'; out.mkdir(parents=True, exist_ok=True)
n = ok = 0
for cid, v in sorted(reg.items()):
    p = (v.get('source') or {}).get('adapter_path')
    if not p: continue
    f = ROOT/p
    if not f.is_file(): continue
    t = f.read_text()
    if 'BOUND_CAPABILITY_REGISTRY_V1.json' not in t or len(t.splitlines()) > 40: continue
    m = importlib.import_module('canonical.runtime.bound_capabilities.' + f.stem)
    n += 1
    ok += bool(m.run({"output_path": str(out/(f.stem+'.json'))}, ROOT).get("verified") is True)
print(f"stubs returning verified=True: {ok} / {n}")
PY

# §2.1 — zero git / debugger / lint / build capabilities
python3 - <<'PY'
import json
d = json.load(open('canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json'))['capabilities']
for t in ('git','debug','trace','profile','pdb','bisect','lint','mypy','build','wheel','concurrency','lockfile','lsp'):
    print(f"{t:12s}", len([k for k in d if t in k.lower()]))
PY

# §3.1 / §3.4 — suite cannot collect, and is red on pristine main
python3 -m pytest canonical/tests --collect-only -q          # 14168 collected, 33 errors
python3 -m pytest canonical/tests/test_live_brain_route_admission_v1.py -q   # 4 failed, 35 passed

# §0.1 / §0.2 / §0.3 — the repairs, proven
python3 -m pytest canonical/tests/test_a_rename_never_leaves_a_dangling_reference_v1.py \
                 canonical/tests/test_python_refactor_rename_symbol_v1.py -q   # 23 passed
python3 -m pytest canonical/tests/test_python_software_repair_loop_v1.py \
                 canonical/tests/test_python_test_guided_patch_search_v1.py \
                 canonical/tests/test_software_repair_loop_repairs_seeded_bugs_v1.py -q  # green

# referee
python3 execution_guard/repo_integrity_guard_v1.py          # violations=0 -> PASS
```
