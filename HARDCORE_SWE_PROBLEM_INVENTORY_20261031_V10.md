# The hardcore software-engineering problem inventory — V10

**Measured 2026-10-31 on `arena/47739ce8-brain` @ `eee2aee` + the two fixes described in §7.**
Every number below comes from a command in §10, run on this machine, with the toolchain present
(`ruff mypy bandit coverage pytest`), `PRECONDITIONS head=… tools_present=10/10 spool_leftovers=0`.

*Authority: NONE — sandbox measurement, not independent verification. Credit: 0.*

---

## 0. The answer in one paragraph

The brain is **not short of software capability**. It holds **419 registry rows, 125 verified, 64 of
them software-engineering rows**, and those rows already perform real work: AST-precise symbol rename,
extract-function, cross-file edit planning, repair with baseline/after verification, coverage /
mutation / type / security / performance gates, change-impact test selection, a multi-language
tree-sitter parser and index, CEGIS and grid-induction synthesis, dynamic fault localisation, PR
realisation, and a diff-apply full-test gate. The problems are **wiring and coverage**, in that order:

| | measured |
|---|---|
| **What the machine answers, over 120 real advanced requests** | **18 (15.0 %)** |
| Of those 120, refusals because the sentence reached the **wrong row** | **27** |
| Refusals because **no lane** was found at all | **26** |
| Refusals because the right lane was reached and **refused for a missing declared input** | **15** |
| Refusals after a step **raised** (the report cannot say what happened) | **9** |
| SWE rows that **no measured sentence reached** | **45 of 64** |
| SWE rows that **declare no inputs at all** (unreachable by construction) | **18** |
| Hardcore domains that have **no SWE row whatsoever** | schema migration, HTTP/API, CI/packaging, TypeScript/Go/Rust, property tests, async/concurrency, observability |
| False PASSes in the 54-case capability matrix | **0** |

So the work is: **wire the 45 unreachable rows** (cheap, they already work), **derive the inputs of
the 18 no-input rows** (cheap), **fix the ranking that sends sentences to finance/tarball/chart rows**
(one mechanism), and **build the eight missing domains** (real work, but each is small and each is
reused from something already in the tree). §8 orders all of it by leverage per hour.

---

## 1. What "advanced software capability" means here, and what already passes

The 17 rows that certify real work today, measured on the capability matrix (`17 REAL / 0 FALSE /
37 REFUSED / 0 DAMAGED`):

| area | row | what it actually does |
|---|---|---|
| repair | `python.software.repair.apply.verified.v1` | finds a patch, runs the named tests before and after, applies, re-verifies |
| repair | `python.software.repair.loop.{coupled,strict_progress,test_guided}.ast` | multi-edit repair loops over the AST |
| refactor | `python.refactor.rename_symbol.v1` | binding-proved rename across modules, refuses on collision, unknown sites listed |
| refactor | `python.refactor.rename_parameter.v1`, `python.refactor.extract_function.v1` | signature and statement-span edits, proved by AST |
| refactor | `python.source.crossfile_edit.choreograph.v1` | the full site plan for a checked-in rename/move (fixed today, §7.1) |
| analysis | `python.source.symbols.index.ast`, `python.source.symbols.resolve.v1` | symbol index, callers, resolution |
| analysis | `python.source.change_impact.testselect.v1`, `code.impact.tree_sitter.testselect.v1` | which tests a change touches |
| review | `python.review.diff_{type,coverage,mutation,security,static_triage,perf}_gate.v1` | six measurement gates over a change set |
| acceptance | `python.repository.acceptance.measure.v1`, `python.tests.audit.unittest` | suite run, test inventory |
| synthesis | `software.patch.synthesize.cegis.z3.v1`, `software.synthesis.grid_induction.v1` | verified program synthesis |
| debugging | `python.fault.provenance.interprocedural.value.v1`, `python.fault.localize.dynamic.dataflow.v1` | value provenance, ranked fault lines |
| polyglot | `code.multilanguage.parse.tree_sitter.v1`, `code.index.tree_sitter.incremental.v1` | parse and index non-Python code |

That list is genuinely advanced. The problem is that **a user cannot reach most of it from a
sentence**, and 45 of the 64 SWE rows were never selected by any of the 120 measured requests.

---

## 2. The failure taxonomy, measured over 120 cases

Instruments: `swe_request_probe_v1.py` (28 sentences), `--suite hardcore` (49), `--suite frontier`
(43, added today — it is the only suite that asks about release engineering, data/schema, HTTP,
concurrency, property tests, CI, PR review, hardening or the non-Python ports).

| refusal class | count | what it means |
|---|---|---|
| `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` | **27** | a row was selected and then refused as the wrong KIND of row (a reader for a transform, a writer for a question, a document converter for a code request) |
| `FAIL__RAW_GOAL_COMPILATION_GAP` | **26** | no lane at all: the compiler could name no capability and the composer no chain |
| `FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED` | **15** | the right lane refused on a declared input the sentence did not state and nothing derived |
| `FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN` | **9** | a composed step raised; the report cannot say which step or why (worst diagnosis in the system) |
| `FAIL__LIVE_CONTROLLER_EXECUTION` | **6** | the controller ran and failed; no capability-level cause |
| `FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED` | **5** | a chain was proposed; verification did not accept it |
| `FAIL_CLOSED__CAPABILITY_REFUSED_*` | **7** | the adapter refused with its own reason (suite red, base world red) |
| `FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT` | **2** | the measurement ran; its verdict was "no" and that is reported as a refusal |
| `FAIL_CLOSED__NO_OBSERVED_EFFECT` | **3** | something ran and the world did not move |
| `FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED` | **2** | the sentence promised source bytes; nothing wrote them |
| **PASS** | **18** | |

### 2.1 The wrong destinations (27 cases) — one mechanism, not 27 bugs

A SWE sentence routed to a row from another domain, then correctly refused:

| request | row it reached |
|---|---|
| "Profile the function total … and tell me where the time goes" | `chart.raster.axis_title_unit_binding.v1` |
| "Add a CI workflow …" | `yaml.to_json.yq` |
| "Add a database migration …" | `sqlite.table.create_from_json_records` |
| "Model the users table as a SQLAlchemy model …" | `sqlite.table.create_from_json_records` |
| "Validate config.json against a JSON schema …" | `docx.document.create_from_json_record` |
| "Add a FastAPI endpoint /health …" | `finance.saccr.credit.addon.v1` |
| "Add a benchmark … and record the baseline" | `docx.document.create_from_json_record` |
| "Trace why … returns the wrong value" | `decision.synthesis.typed.stdlib` |
| "Add structured logging to …" | `structured.decision_evidence.locate.stdlib` |
| "Write a unit test for the function mul" | `python.tests.audit.unittest` (the auditor, not a writer) |
| "Add the dependency `requests` to pyproject.toml" | `finance.saccr.credit.addon.v1` |
| "Build the package in <dir> into a wheel" | `archive.tar_gz.create_from_manifest` |
| "Measure the test coverage of <file>" (hardcore tree) | `python.review.diff_coverage_gate.v1` — right row, suite red, honest refusal |

**Cause:** selection is lexical (BM25 over keyword surfaces) and the registry's keyword field is
generous — a single matched token ("value", "add", "schema", "profile") is enough to outrank the SWE
row. Sweeping the request text for weakness is not done; the *verb–object family* is not used.

**Mechanism that already exists:** `swe_typed_plan_v1._resolve_family` — enumerate candidates by the
registry's own keywords for a stated effect family, let `selection.admit` be the oracle, require the
effect token in the id, fail closed on ambiguity. It is decisive for caller-finding, type-check,
coverage, security, mutation, perf, extract, repair and (today) cross-file rename planning. It is
**not** decisive for 27 of the measured cases because those sentences state an effect that is either
not in `_FAMILIES` or has no row carrying the token.

**Missing wire:** one more rule, not 27. Each row needed is a `(triggers, registry-terms, effect-token)`
triple, and each triple is only sound if a row's *name* carries the effect (that is the
no-false-PASS guard). §5 lists which families have a row to be decisive about and which do not.

---

## 3. Rows that exist and no sentence reaches — 45 of 64

Grouped by the one wire each cluster needs. These are the cheapest 40+ capabilities in the repository:
they are written, tested, verified, and unreachable.

### 3.1 Rows blocked on a *derivation* (the sentence carries the fact; nothing extracts it)

| row(s) | what it does | the slot nothing fills | the fact is in the sentence as |
|---|---|---|---|
| `python.repo.pr_realize.v1` | realises a PR from a diff | `pr_intent_path`, `base_branch`, `branch_name`, `apply_directory` | "open a PR … against main … for these edits" |
| `python.software.issue_to_pr.orchestrate.v1` | issue → PR end to end | `task_path`, `pr_intent_path`, `index_path` | the issue text + the tree |
| `python.issue.natural_language.parse_edit_intent.v1` | issue text → edit intent | `issue_path`, `index_path` | the issue text |
| `python.refactor.extract_function.v1` | extract a statement span into a function | `start_line`, `end_line`, `qualname`, `new_name` | "extract the body of the loop in <fn> into <name>" |
| `python.refactor.rename_parameter.v1` | rename a parameter everywhere | `qualname`, `old_param`, `new_param` | "rename the parameter x to y in <fn>" (the AST proof already exists for symbols) |
| `python.software.repair.*` (4 loops) | repair loops | `test_paths`, `test_argv`, budgets | "make the failing test in <T> pass" |
| `python.task.acceptance.measured.objective.v1` | objective measurement of a task | `measurement_receipt_path` | the receipt a previous step produced |
| `python.software.repair.semantic_acceptance.v1`, `…measured_acceptance.v1` | task-text acceptance | `task_text`, `test_argv` | the sentence itself |
| `python.review.diff_perf_gate.v1` | performance regression gate | `bench_path` | "run a performance review of <module>" (`def bench()` discovery exists) |
| `python.repo.diff_apply_full_testgate.v1` | apply a diff, run the whole gate | `diff_path`, `anchor_path` | the previous step's artifact |

**The mechanism exists.** `declared_input_derivation_v1.derive()` proves values from stated evidence
and refuses on ambiguity; today it gained the cross-file edit set. Every slot above is the same shape:
a stated path, a proved symbol, or a previous step's artifact.

### 3.2 Rows blocked on a *family triple* in `swe_typed_plan_v1` (the effect is stated; no route)

`python.refactor.test_scaffold.fusion.v1`, `python.tests.generate.scaffold.v1`,
`python.patch.search.test_guided.ast.v1`, `python.pr.land.composer.v1`,
`python.pipeline.allowlist_gate.v1`, `orchestration.verify.bridge_enumeration.v1`,
`test.slice.never_miss.v1`, `python.fault.provenance.fusion.v1`,
`python.fault.patch.supercomposer.v1`, `python.contract.check.crosshair.v1`,
`python.symbol.resolve.standalone.v1`, `python.test.pipeline.verifier.v1`.

Some of these have no declared inputs at all (§4) and cannot be bound by any derivation.

### 3.3 Rows that are *composition steps*, not answers

`software.hardcore.{swe,final,closing}.supercomposer.v1`, `python.orchestration.symbol.supercomposer.v1`,
`python.provenance.coupling.supercomposer.v1`, `python.patch.review.supercomposer.v1`,
`python.evidence.contract.supercomposer.v1`, `software.{review,test}.{gate,synthesis}.composer.v1`,
`software.evidence.synthesis.supercomposer.v1`, `software.hardcore.kernel.orchestrate.v1`.

They are reachable, but only as a step inside a chain, and the chain planner selects them at the wrong
moment (measured: `software.hardcore.kernel.orchestrate.v1` chosen for "Extract the magic numbers",
"Split the module", "Set up CI" — three refusals in this census).

---

## 4. Rows that cannot be reached by construction — 18 no-input rows

These declare **no** input slots at all, so no sentence can bind anything to them and `admit()` has
nothing to admit:

```
python.contract.issue_orchestration.fusion.v1      software.hardcore.swe.supercomposer.v1
python.evidence.contract.supercomposer.v1          python.orchestration.symbol.supercomposer.v1
python.fault.patch.supercomposer.v1                python.patch.review.supercomposer.v1
python.fault.provenance.fusion.v1                  python.pipeline.allowlist_gate.v1
python.pr.land.composer.v1                         python.provenance.coupling.supercomposer.v1
python.refactor.test_scaffold.fusion.v1            python.symbol.resolve.standalone.v1
python.test.pipeline.verifier.v1                   software.evidence.synthesis.supercomposer.v1
software.hardcore.closing.supercomposer.v1         software.hardcore.final.supercomposer.v1
software.review.synthesis.supercomposer.v1         software.test.contract.supercomposer.v1
```

Either they are steps that should take the previous step's artifact (`diff_path`, `index_path`,
`task_text`, `source_root`) or they are not answers at all and should be marked as internal. Both are
registry declarations, not code: **8–9 slots** per row in the composer families.

---

## 5. Domains with no SWE row at all — the real building work

Measured by scanning every registry row's id + keywords + provides for the domain vocabulary. This is
what the machine genuinely cannot do, and what stands between it and "the most advanced software
engineer":

| domain | rows found | what is missing | what to reuse (already in the tree) |
|---|---|---|---|
| **Schema / data migration** | **0 SWE** | create/modify a migration, model a table, validate a document against a schema | `sqlite.table.create_from_json_records`, `json.*` validators, the AST editor |
| **HTTP / API** | **0 SWE** | add a route, generate a client, check a handler against an OpenAPI schema | the shell runner + `sqlite`-style adapters; `python.contract.check.crosshair.v1` for the contract |
| **CI / packaging / release** | **0 SWE** | workflow authoring, wheel build, dependency add/upgrade, lockfile, SBOM, vuln audit | `pip`, `python -m build`, `make`, `yaml` rows, `pip-audit` semantics |
| **TypeScript / Go / Rust** | 1 (parser only) | write, type-check, test, lint, port non-Python code | `code.multilanguage.parse.tree_sitter.v1`, `code.index.tree_sitter.incremental.v1`, `node --test`, `npx` |
| **Property / fuzz testing** | 1 (CEGIS only) | generate property tests, shrink a failure, fuzz a parser | `software.patch.synthesize.cegis.z3.v1` (it *has* a property oracle) |
| **Async / concurrency** | 2 (fault localisers, incidental) | convert a function to async, find a race, bound a thread pool, prove no deadlock | `python.fault.localize.dynamic.dataflow.v1` (it already traces scheduling) |
| **Observability** | 1 (incidental) | structured logging, metrics, tracing, dashboards | `python.fault.provenance.*`, the JSON emitters |
| **Supply chain / hardening** | 5 (security gate only) | secrets scan, dependency audit, path-traversal hardening, licence report | `python.review.diff_security_gate.v1` (bandit-backed), `_SAFE_PATH` helpers |
| **Git history surgery** | 1 (`pr_realize`) | commit, branch, rebase, worktree, cherry-pick, bisect, revert | `shell.command.run` + the postcondition table (`_post_git`) that already verifies status/log/diff |

Every one of these is **a registry row plus an adapter**, not a subsystem: the tree already runs
commands with verified postconditions (`raw_goal_trace_acceptance_v1`), already parses three
languages, already has the acceptance gate chain. The missing thing is the row.

### 5.1 Git: five rows' worth of work, two of them almost free

Measured: `git status`, `git log`, `git diff` pass. `git commit`, `git branch`, `git bisect`,
`git revert` have **no lane** (`FAIL__RAW_GOAL_COMPILATION_GAP`) although `_post_git` already verifies
`status/log/diff/show/blame` and the mutating postconditions (`_MUTATING_POSTCONDITIONS`,
`_SIDE_EFFECTING_FLAGS_BY_PROGRAM`) already exist. A commit needs a message (derivable from the
changed paths), a branch needs a stated name (already parsed), and a bisect needs `git bisect run` +
the exit code as the postcondition.

---

## 6. Honesty defects — where the machine is wrong today

The one thing this repository exists to prevent. Measured this session, on real sentences:

### 6.1 Fixed today (see §7)

| defect | evidence before | after |
|---|---|---|
| A module move that orphans its importers certified **exact semantic acceptance** | "Move the module `pkg/util.py` to `pkg/helpers/util.py` and update the imports." → `pass=True`, `PASS__…EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`; `pkg/uses_util.py` still imported `pkg.util`; `import pkg.uses_util` then raised `ModuleNotFoundError`. **The tree was broken and the machine said verified.** | refused before anything runs, with `MODULE_MOVE_WOULD_ORPHAN_IMPORTERS:<file>`; the source is intact, the tree still imports |
| A report was written onto the path the sentence reserved for **source** | the same sentence's next lane bound `python.source.audit.ast` with `output_path = pkg/helpers/util.py` and wrote a **633-byte JSON report** where the module was going to be | the front compiler now repoints a report off any stated move destination; pinned by a test |
| A plan that planned nothing certified PASS | "Which files must change to rename …" → `pass=True`, `affected_file_count: 0`, `refusals: [MODULE_NOT_IN_INDEX]` | `TOOL_PLANNED_NOTHING_AND_REFUSED` is a truth-check error |
| A refusal reported the wrong cause | a refused move came back `PROMISED_ARTIFACT_MISSING` over a tree nothing had touched | `failure_reason` now names `MODULE_MOVE_WOULD_ORPHAN_IMPORTERS` |

### 6.2 Open

| # | defect | evidence | fix |
|---|---|---|---|
| **H1** | **A stated *effect* is not gated — only a stated *artifact* is.** "Make the test suite in `<dir>` run in parallel." returns `pass=True` because `python.repository.acceptance.measure.v1` ran the suite: the files are unchanged (`touched=False`, `dirty=0`) and nothing is parallel. | frontier suite, `test/parallel`, the only pass in 43 | an effect gate: a stated effect (parallel, async, metrics, cached, streaming) must be declared by the answering row, exactly as `_shape_errors` already refuses a writer-for-a-question |
| **H2** | **`FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN` (9 cases) names neither the step nor the reason.** | `understand/trace_flow`, `test/write_unit`, `build/add_dep`, `build/upgrade_dep`, `feature/issue_to_pr`, `debug/debugger` | the composed executor must carry the raising step's id and its own error text into `failure_reason` |
| **H3** | **A review that returns a verdict is reported as a refusal.** Two coverage/mutation gates "fail" because the measurement said the change set is not covered — that is an answer, not an inability. | `measure/coverage`, `measure/mutation` | a `REVIEW_VERDICT` status class, distinct from `CAPABILITY_REFUSED` |
| **H4** | **A red base tree converts capability into refusal.** Three cases refuse `CAPABILITY_REFUSED_SUITE_RED` / `BASE_WORLD_RED` on the probe fixture. | `test/raise_coverage`, `quality/review_diff`, `pr/review` | the tree's own red state must be reported as the finding, and the request answered over the *change*, not the whole suite |
| **H5** | **17 pre-existing red test ids** in the command-module suites (measured at baseline, identical with and without this session's changes) and **no CI gate** that would have caught them. | `test_an_ordinary_sentence_runs_the_command_it_states_v1` ×16, `…verified_by_running_it_again_v1` ×1 | T7, unchanged |
| **H6** | **A row that only reports on a file may still be handed a source file as output** in any path that does not go through `repair_output_collisions` (fixed for the move case today; the general rule now lives in one place, but the composer and the legacy compiler call it at different points). | §6.1 | one call site, both lanes |

---

## 7. What changed today

### 7.1 `edits_path` — the cross-file plan is reachable (item 1 of V9's ladder)

`declared_input_derivation_v1` derives the edit set from a stated rename: the pair, the single stated
directory, and the ONE module under it that defines the symbol at module scope (`ast`; zero or several
⇒ nothing). The op's `module` is the repository-relative path the symbol index uses — the first
derivation emitted the path under `source_root` and the plan refused its only op
`MODULE_NOT_IN_INDEX:pkg/calc.py`. `live_brain_route_admission_v1` learned that a row whose own
registry declaration says *"Plans, does not apply"* is not a writer, and that a plan-only row owes no
byte change when the sentence does not demand the change.

Measured: "Which files must change to rename the symbol `mul` to `multiply` in `<dir>`?" →
`planned_op_count 1`, `refused_op_count 0`, `affected_file_count 2`, `ambiguous_site_count 0`, sites
`DEFINITION pkg/calc.py:1`, `IMPORT_SITE pkg/util.py`, `REFERENCE pkg/util.py:5`. An **imperative**
rename still fails `PROMISED_SOURCE_CHANGE_NOT_APPLIED` when only a plan comes back.

### 7.2 A module move no longer certifies a broken tree (§6.1)

The check is **before** execution, in the composer, next to the existing "a file command cannot move a
definition" rule. The first attempt put it in the `mv` postcondition and was worse than the false pass
it removed: the door's rollback deletes the destination and does not restore the source, so
`pkg/util.py` was gone. A refusal that loses the caller's file is not a refusal.

### 7.3 A new instrument: `--suite frontier` (43 cases)

The 28-sentence and 49-case hardcore suites never asked about release engineering, data/schema, HTTP,
concurrency, property tests, CI, PR review, hardening, observability or the non-Python ports. That is
why **2 of 43** was the first measurement of it: the ceiling there is not 15 %, it is 5 %.

---

## 8. The order of work — leverage per hour

1. **Ranking by verb–object family** (kills 27 wrong destinations). One mechanism
   (`_resolve_family`), one table of triples, one invariant: the effect token must appear in the
   answering row's id. *No new capability.*
2. **Derivations for the 45 unreachable rows** (§3.1). Each is a proof from stated evidence, refused
   on ambiguity. Highest ceiling: PR realisation, issue→PR, extract-function, rename-parameter, the
   repair loops.
3. **Register the 18 no-input rows** (§4): give the composer rows their 8–9 declared slots, or mark
   them internal so they stop appearing as candidates.
4. **Git: commit, branch, bisect, revert, cherry-pick** (§5.1). `_post_git` already verifies the world;
   the message deriver and the mutating postconditions already exist.
5. **Refactor beyond rename**: inline, move-symbol, split-file, dedupe, dead-code removal — all over
   the AST editor that already does extract/rename with collision refusal.
6. **Test authoring**: a writer for tests (`python.tests.generate.scaffold.v1` exists; the sentence
   routes to the auditor), the 2 scaffold rows, and the test-guided controller fix.
7. **Build & dependencies**: wheel (`python -m build`), add/upgrade dependency, lockfile, SBOM, audit.
   Zero new machinery: `pip`, `make`, `python -m build` are installed.
8. **Data & schema**: migration, model, JSON-schema validation. Reuse the sqlite adapter.
9. **HTTP/API**: route, client, contract check.
10. **Polyglot**: `node --test`, `npx` linters, and the tree-sitter index that already parses
    TypeScript/Go/Rust; then the ports.
11. **Concurrency, observability, property testing**: the last three domains, each a row over an
    existing tracer/synthesizer.
12. **Honesty items H1–H6**, in parallel: the effect gate (H1) is the one that can still produce a
    false PASS today.

---

## 9. What is *not* the problem (do not rebuild these)

* **Not capability.** 64 SWE rows exist; 45 were never reached. Build rows last.
* **Not the acceptance layer.** `raw_goal_trace_acceptance_v1` re-derives commands, checks
  postconditions from the disk, and catches the false passes above; it is the strongest thing here.
* **Not speed.** p50 across 120 requests: **39 ms** (28-suite), **69 ms** (hardcore), **63 ms**
  (frontier). The bottleneck is routing, not execution. The only slow lane is mutation testing
  (1.1 s) and it is honest about it.
* **Not spend.** All of it is model-free: `model_dependency_count 0`, `incremental_spend_usd 0`.
* **Not PDF/DOCX/chart/finance coverage.** Those rows exist and are irrelevant here, except as the
  destinations that wrong-ranking keeps choosing (§2.1).

---

## 10. Reproduction

```bash
cd /home/user/brain
git fetch origin arena/47739ce8-brain && git reset --mixed origin/arena/47739ce8-brain
pip install -q --break-system-packages pytest ruff mypy bandit coverage

python3 execution_guard/swe_request_probe_v1.py                  # 28 sentences -> 6 answered
python3 execution_guard/swe_request_probe_v1.py --suite hardcore  # 49 requests  -> 10 answered
python3 execution_guard/swe_request_probe_v1.py --suite frontier  # 43 domains   -> 1 answered
python3 execution_guard/swe_capability_matrix_v1.py               # 54 cases -> 17/0/37/0
python3 canonical/runtime/verify_brain_unified_model_v1.py        # 33/33

# the two honesty findings of §6.1, on a fresh frontier tree
python3 execution_guard/swe_request_probe_v1.py --suite frontier   # refactor/move_module: refused, dirty=0
python3 -m pytest -q canonical/tests/test_a_rename_question_is_answered_by_a_plan_v1.py \
                    canonical/tests/test_a_module_move_needs_its_importers_v1.py
```

Registry arithmetic used throughout:

```python
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry, is_verified_entry
reg = load_verified_registry()                       # 419 rows, 125 verified
swe = [k for k in reg if k.startswith(("python.","code.","software.","test.","orchestration.verify."))]
len(swe)                                             # 64
```

*Authority: NONE — sandbox measurement, not independent verification.*

---

## 9. V10.1 addendum — the last FALSE row is closed (2026-10-31, branch `arena/47739ce8-brain`)

H11 in §6 was the sharpest honesty defect left: **a proposer passed as a repair**. Measured on the
54-case matrix, verbatim:

```
goal    "Repair the python source <pkg>/calc.py so that the unit test <pkg>/test_calc.py passes,
         and save the repair report to <pkg>/out.json."
answer  python.patch.search.test_guided.ast.v1 -> PASS__VERIFIED_CANDIDATE_PATCH_FOUND
door    PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED
world   <pkg>/calc.py BYTE-IDENTICAL to how it was found            (FALSE)
```

The row is not lying: it says in its own registry `limitations` that *"source bytes are restored
after every trial and before return; no source write or promotion authority"*. It is a **proposer**.
The door was asking the sentence's *effect* and its *contract*, and never its **authority**.

The fix is one rule, read from the row's own declaration, applied at the three places a verdict is
formed — no new subsystem, no id table:

1. `write_authority_v1.declares_no_source_write_authority(entry)` / `cannot_perform_the_stated_change`
   — the authority is read from `limitations`, never from the id (`is_source_transformer` reads the
   id, and `python.patch.search...` contains "patch", which is why it was called a transformer).
   The sentence half is the door's own `sentence_promises_a_change`, so a *question about* a change
   is still not a promise to make one.
2. `capability_selection_retrieval_v1.admit` refuses a declared candidate-only row for a
   change-promising sentence (`CANDIDATE_ONLY_ROW_DECLARES_NO_SOURCE_WRITE_AUTHORITY`) — which is
   what lets the typed selector reach `python.software.repair.apply.verified.v1`, the row that binds
   the identical inputs and *applies* the verified repair.
3. `live_brain_route_admission_v1` asks it **before the run** (the same place the answer gate is
   asked), so the refusal costs nothing and does not set `executed: True` — the one flag that
   forbade the scoped typed retry from reaching the applier.

Two further defects surfaced while wiring it, both closed in the same module:

* the applier reported a green baseline only in `status`; it now says `already_satisfied: true` /
  `edited: false` in the vocabulary the door already honours, and the door lifts that flag from a
  PASS — so the idempotent sentence ("repair this, it is already green") stays a PASS with
  `edited: false` instead of becoming `PROMISED_SOURCE_CHANGE_NOT_APPLIED`;
* an `already_satisfied` claim over a source that **does not parse** is empty (the green suite never
  imported it): it is now `FAIL_CLOSED__NAMED_SOURCE_UNPARSEABLE`, named per file.

Measured after the change, same machine, tree cleared of `tmp/frontier_matrix` first:

| instrument | before | after |
|---|---|---|
| `swe_capability_matrix_v1.py` | 54 → 11 REAL / **1 FALSE** / 42 REFUSED / 0 DAMAGED | 54 → **12 REAL / 0 FALSE / 42 REFUSED / 0 DAMAGED** |
| repair class | 4/7 REAL | **5/7 REAL** (`repair_with_report` now applied=true, source_restored=false, file really changed) |
| latency | median 66 ms, p90 545, max 1040 | median 60 ms, p90 629, max 1095 |
| `verify_brain_unified_model_v1.py` | 33/33, AUTHORITY NONE | 33/33, AUTHORITY NONE |
| `verify_bound_capability_provenance_v1.py --check` | 0 unproven of 133 | 0 unproven of 133 |

Regression pins: `canonical/tests/test_a_proposer_is_not_a_repair_v1.py` (7 tests: the declaration
set, the question-vs-promise split, the selector, the end-to-end repair on a broken tree, the
idempotent green tree, the unparseable source). Whole-repository sweep over the 106 modules that
touch these paths: **39 failures, the same 39 node ids as `origin/main`'s tree** — no new red.

Reproduction:

```bash
python3 execution_guard/swe_capability_matrix_v1.py                 # 54 -> 12/0/42/0
python3 -m pytest -q canonical/tests/test_a_proposer_is_not_a_repair_v1.py
python3 canonical/runtime/verify_bound_capability_provenance_v1.py --check
python3 canonical/runtime/verify_brain_unified_model_v1.py          # 33/33
```

*Authority: NONE — sandbox measurement, not independent verification.*
