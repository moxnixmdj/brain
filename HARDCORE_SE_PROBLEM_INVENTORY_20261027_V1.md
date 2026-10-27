# Every problem that stands between this machine and being an advanced software engineer

Measured on `53150bd` (branch `arena/1ca46375-brain`, on top of main `7913c4d`), 2026-10-27.
Nothing here is inferred from reading code: every claim below has the probe that produced it.
Where a number is quoted, the exact command is given.

## What is already proven (so the list below is a gap list, not a dismissal)

| measurement | result |
|---|---|
| 37-family end-to-end suite, fixed seed 424242, fresh instances | **0.8241** in scope (183/222), **1.00** out-of-scope fail-closed (20/20), no family below its baseline |
| the five python repair families (patch search, coupled AST, coupled provenance, strict progress, test-guided apply) | **150/150** across seeds 7, 11, 99, 1234, 424242 |
| unified model verifier | 33/33 PASS |
| reachability from one entry, 405 admissible capabilities | 398 reached and bound, 4 by explicit name, 2 routed elsewhere, 1 not reachable |

So single-file Python repair is now real and measured. Everything below is what that corridor does
**not** cover, ordered by how much damage it does.

---

## P0-1. The machine destroys before it detects: a refactor sentence deleted the source file

```
Repair request, natural refactor wording:
  "Rename the parameter old_price to price in the python module <D>/pkg/util.py
   and save the report to <D>/r7.json."
```

Measured result (`solve`, task `ISO_R7`):

```
status : FAIL_CLOSED__NAMED_INPUT_REMOVED
capability selected : shell.command.run
util.py exists after the run : False
files left in the directory  : r7.json          <- a report, and no source
```

The gate is right that the input vanished — **after the fact**. `python.refactor.rename_parameter.v1`
exists, is registered, has an adapter and detailed limitations. It was never consulted: the catch-all
shell capability claimed the sentence and deleted the file. Detect-after-destroy is not a guard; it is
an audit trail on a lost file.

Repro: `canonical/astra_runtime/tmp/inv3` probe in this session's log (5 lines, deterministic).

**Why it matters more than any missing feature**: a user who runs this loses work. Every other problem
on this list can be retried; this one cannot.

**Fix**: make a run transactional. The machine already snapshots (`execute_v1._snapshot`), so restoring
the stated subtree on any refusal is cheap (2.9 ms for a stated subtree). Second, a sentence that names
an existing source file and matches a registered source-editing capability must not be claimable by a
capability that has no source-edit contract.

## P0-2. A human sentence does not route; the machine's own sentence does

Same broken file, same test, five phrasings (`solve`, task prefix `PAR_`):

| phrasing | verdict | capability |
|---|---|---|
| `Repair the python source <D>/pkg/calc.py so that the unit test ... passes, and save the repair report to <D>/a.json.` | **PASS** | `python.software.repair.loop.test_guided.ast.v1` |
| `the add function in <D>/pkg/calc.py is broken, fix it so its tests pass` | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED | `python.software.request.semantic_behavior.compile.v1` |
| `fix <D>/pkg/calc.py` | FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN | — |
| `my tests in <D>/pkg are failing because of a bug in calc.py, can you find and fix the bug and write down what you changed` | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED | `python.tests.audit.unittest` |
| `Bug: <D>/pkg/calc.py add() returns the wrong value. Failing test: <D>/pkg/test_calc.py.` | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED | — |

**4/4 human phrasings fail; 1/1 template phrasing passes.** The 0.8241 above is measured on
**machine-authored** sentences — each family generates its own goal text in the exact shape the binder
expects. That number is a ceiling on template understanding, not on engineering capability.

**Fix**: measure and fix the front door on human wording (issue text, bug reports, one-line
imperatives), which is what a user actually types. This is not a new subsystem; the binder already
binds by role, so the work is intent wording, not mechanism.

## P0-3. Selection is token overlap, so it picks unrelated capabilities

Ten real software-engineering tasks, one `solve` call each (`task_id` prefix `INV_`), **0/10 reached a
capability that could do the job**:

| task | routed to | verdict |
|---|---|---|
| rename a function and update callers | `code.multilanguage.parse.tree_sitter.v1` | FAIL_CLOSED__NAMED_SOURCE_UNPARSEABLE |
| write a unit test for a module | `python.patch.search.test_guided.ast.v1` | FAIL__LIVE_CONTROLLER_EXECUTION |
| explain why a test fails | `evidence.claim_relation.generic_units.stdlib` | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED |
| find every caller of a function | — | FAIL__RAW_GOAL_COMPILATION_GAP |
| show the last three git commits | `shell.command.run` | FAIL_CLOSED__PROMISED_ARTIFACT_MISSING |
| commit the staged changes | — | FAIL__RAW_GOAL_COMPILATION_GAP |
| type-check a file | `software.hardcore.kernel.orchestrate.v1` (composed) | FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED |
| extract a function body and save a patch | `pdf.extract.ocr.tesseract` | FAIL_CLOSED__PROMISED_ARTIFACT_MISSING |
| run a failing test under a debugger | `document.convert.markdown_pdf.pandoc_weasyprint` | FAIL_CLOSED__ROUTE_ADMISSION_REJECTED |
| lint a file | `text.file.write` | FAIL_CLOSED__PROMISED_ARTIFACT_MISSING |

`pdf.extract.ocr.tesseract` for a refactor and `document.convert.markdown_pdf.pandoc_weasyprint` for a
debugging request are not near-misses; they are different domains chosen because one word matched.

The compile benchmark shows the same class on its own rows:

```
python canonical/runtime/goal_compilation_benchmark_v1.py
PRIMARY   compiled 9/9, expected capability selected 8/9, WRONG-CAPABILITY 1
EXTENDED  compiled 13/14, expected 10/14, WRONG-CAPABILITY 3
  EXT_XLSX_CREATE   -> auto.pypi.msgpack                    WRONG-CAPABILITY
  EXT_SQLITE_VERIFY -> auto.pypi.msgpack                    WRONG-CAPABILITY
  EXT_JQ_TABLE      -> document.convert.markdown_pdf...     WRONG-CAPABILITY
  EXT_AST_AUDIT     <- GOAL_COMPILATION_AMBIGUOUS
```

A capability is "OK" in that benchmark when it compiles at all — **compiling is not selecting**.

**Fix**: rank by what the sentence's inputs can bind, then by effect; a capability whose declared
inputs cannot bind the sentence's paths must be excluded before scoring, not scored low. That predicate
already exists (`request_may_select`); it is not applied to the catch-all and the auto.* rows on the
paths measured here.

## P1-4. The bench measures a narrow corridor, so the score overstates the engineer

37 families, of which **9 are software engineering** — and all nine are single-file, stdlib-only modules
of two or three functions with tests written by the generator. Not measured at all: multi-file edits,
real repositories, package layouts, import graphs, git history, build systems, dependency resolution,
concurrency, performance, memory, flaky tests, dynamic analysis, debugging sessions.

The out-of-scope set proves *refusal* discipline, not capability. A machine that scores 0.8241 here can
still be unable to change a real repository — and P0-3 shows it is.

**Fix**: at least one family per real SE surface (git operations, multi-file refactor, test synthesis
for an existing suite, failure diagnosis from a traceback, static type errors), each on a real
repository fixture with an independent oracle. The families' shape is already right; the artifacts are
too small.

## P1-5. Whole capability surfaces are absent

Counted over the 111 registered capabilities by id:

| surface | capabilities |
|---|---|
| python repair / patch search | 11 |
| python review gates (type, security, perf, coverage, mutation) | 6 |
| python source index / symbols / impact | 6 |
| python refactor / test scaffold | 2 |
| shell / terminal | 2 |
| **git operations (log, commit, branch, merge, blame, bisect)** | **0** |
| **dynamic analysis (trace, profile, debugger, breakpoints)** | **0** |
| **dependency / build resolution beyond `auto.pypi.*` + `auto.npm.*` wrappers** | **0 dedicated** |

`python.repo.diff_apply_full_testgate.v1` and `python.pr.land.composer.v1` assume a diff already
exists; nothing produces one from a repository state change, and nothing can commit, branch, or read
history. There is no tracer and no debugger in the registry at all — the two tools a working engineer
reaches for first when a test fails in a way that is not a one-line bug.

**Fix order**: git object model first (read history, diff, commit, branch — stdlib `subprocess` +
`git` CLI, no model), then dynamic analysis (stdlib `sys.settrace`, `cProfile`, `pdb` in batch mode).
Both are already-installed substrates; nothing needs to be bought.

## P1-6. 45 of 52 software-engineering capabilities have never been measured from a sentence

Shape-matched SE ids in the registry: **52**. SE families in the suite: **9**. The other 43 —
`python.refactor.rename_parameter.v1`, `python.tests.generate.scaffold.v1`,
`python.review.diff_type_gate.v1`, `python.source.crossfile_edit.choreograph.v1`,
`software.patch.synthesize.cegis.z3.v1`, `python.issue.natural_language.parse_edit_intent.v1` and the
rest — have no plain-sentence measurement. A probe that names them by id compiles 9 to themselves and
fails to compile for 43, which says the probe is shaped wrong, not that the capability works.

The suite's own reachability number (398/405 "reached and bound") is measured on sentences generated
**from each capability's own id words** — a self-fulfilling instrument. It cannot distinguish a
capability a user can reach from one only its own name can reach.

**Fix**: a per-capability, human-shaped sentence corpus with an independent oracle; report
"reachable by a natural request" as its own number and stop counting self-generated sentences.

## P1-7. The door credits a patch it never ran

`_statement_patch_authority` accepts an unchanged source when a stated report carries a diff that
**applies**. It does not run the stated test on the patched copy. Measured counterexample (seed 11 of
the coupled family, before the instrument fix): a patch satisfied the single stated equation and left
`test_calc_bpfkg_iqtaum.py` failing — it would have been credited.

**Fix**: apply the promised diff to a copy and run the stated test argv before crediting; refuse on
red. The applier and the runner are both already in the machine.

## P2-8. Verdicts are not reproducible

The same goal against the same tree returned different verdicts in two consecutive runs of the same
14-goal sequence:

```
"Commit the staged changes with the message 'wip' and show the resulting commit sha."
  run 1: PASS (no commit was created, no artifact, capability None)
  run 2: FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
"Lint the python file <D>/pkg/util.py ..."
  run 1: FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
  run 2: FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN
```

A PASS in run 1 for a goal that changed nothing is a false credit. Root cause is not yet isolated
(hidden state: controller checkpoints, experience records, admission state). No SE capability can be
trusted while the same input has two verdicts.

**Fix**: a replay harness that runs the same goal twice in two clean trees and asserts identical
verdict, added to the suite; then bisect whatever state makes them differ.

## P2-9. The measured ceiling is partly the machine's package list

```
capabilities_total 111
adapter_import_failed       9   (all chart.* raster + professional.artifact.visual_observer)
external_dependency_missing 9   (yq, tesseract, pandoc, python-docx, zint, zbarimg, ...)
executor_kernel_refuses_source_type 27
```

These are environment, not cognition — but they cap what any measurement can show and they make
`YAML_TO_JSON`, `DOCX_CREATE`, `XLSX_*`, `PDF_TEXT_OCR`, `CHART_RASTER_READERS`, `CODEC_MSGPACK` read as
failures of the machine rather than of its container. For the SE surfaces that matter (P1-5) the
substrate is stdlib and git, both present, so this is not a blocker there.

## P2-10. A composed plan can write a report over a user's source file

Observed once in a 14-goal sequence: `pkg/util.py` was replaced by
`{"schema":"PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1", "source_root": ".../pkg", ...}` — a symbol index
written to the path of the source it indexed. Not reproduced on demand; the trigger is not isolated.
It is the same authority defect as P0-1 in a different shape: an intermediate artifact may land on a
user path.

**Fix**: no capability may write to a path it did not declare as an output, checked before the write,
not after.

---

## The fix order

1. **Transactionality and write authority** (P0-1, P2-10) — nothing else matters if work is lost.
2. **Human-shaped routing** (P0-2, P0-3) — the corridor is understood; the front door is not.
3. **Negative binding before ranking** — a capability that cannot bind the sentence must not be scored.
4. **Git and dynamic analysis** (P1-5) — the two missing surfaces a software engineer cannot work without.
5. **Real-repository families** (P1-4, P1-6, P1-7) — measure what is claimed, on artifacts that matter.
6. **Replay determinism** (P2-8) — a second verdict on the same input invalidates the first.

## Repro

```bash
# 1. destruction (P0-1): source deleted by a refactor sentence
python3 - <<'PY'
import sys; sys.path.insert(0,'.')
from canonical.runtime import live_brain_route_admission_v1 as adm
from pathlib import Path
B="canonical/astra_runtime/tmp/repro1"; (Path(B)/"pkg").mkdir(parents=True,exist_ok=True)
src=Path(B)/"pkg/util.py"; src.write_text("def add(a,b):\n    return a+b\n")
r=adm.solve({"task_id":"R","goal":f"Rename the parameter old_price to price in the python module {B}/pkg/util.py and save the report to {B}/r7.json."})
print(r["status"], "| capability:", r.get("compiled_capability_id"), "| source exists:", src.exists())
PY

# 2. human phrasing (P0-2): four failures, one pass
#    (same harness, goal replaced by the five phrasings in the table)

# 3. selection (P0-3): ten SE tasks, ten failures
python3 canonical/runtime/goal_compilation_benchmark_v1.py

# 4. full suite
python3 execution_guard/live_solver_end_to_end_measurement_v1.py --seed 424242 --per-family 6 --oos 20 --entries new --out /tmp/suite.json
```
