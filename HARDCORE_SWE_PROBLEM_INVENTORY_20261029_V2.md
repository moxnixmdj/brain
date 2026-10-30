# Every problem between Brain and being an advanced software engineer

Measured **2026-10-29** on `main` @ `c79a8f5` (`arena/b1dd6c2d-brain`), in this sandbox, with the
live front door itself (`canonical/runtime/live_brain_route_admission_v1.solve`).
Authority: **NONE**. Credit: **0**. Producer-cognition model dependency: **0**. Incremental spend: **$0**.
This is a measurement, not a capability claim. Every number below has the probe that produced it,
kept in `swe_probe_20261029/` and re-runnable (see §10).

Scope: **advanced software-engineering capability only.** PDF/DOCX/XLSX/chart/codec work is
mentioned only where it is the *wrong-domain destination* of a software request.

---

## 0. What was measured, and how

18 fresh human-shaped SWE sentences were run against 18 fresh trees, one `solve()` call each,
with a **filesystem oracle** independent of the machine's own verdict (does the source actually
change? does the stated test actually pass? did the promised artifact appear?).

```
swe_probe_20261029/swe_probe.py     -> 18 tasks x 1 call, world-state oracle
swe_probe_20261029/layout_matrix.py -> 6 tasks x 4 repository layouts
swe_probe_20261029/report_clause2.py-> 4 minimal pairs (with/without "save the report to ...")
swe_probe_20261029/writes.py        -> does a PASS actually modify the source?
swe_probe_20261029/falsepass.py     -> does the door's PASS survive the user's stated acceptance?
swe_probe_20261029/hang.py          -> a 40 s faulthandler dump of a live request
swe_probe_20261029/state.py         -> same goal, same tree, after one prior request
```

The previous three inventories in this repository (`HARDCORE_SE_PROBLEM_INVENTORY_20261027_V1.md`,
`SWE_HIDDEN_WIRING_MEASUREMENT_20261027_V1.md`, `HARDCORE_SWE_PROBLEM_MAP_20261028_V1.md`) report
"5/12 human sentences PASS" and "4/12 → 5/12". **On this tree that does not reproduce: 1/18.** The
reports are not lying about what they saw — the corridor moved — but no reader should treat any
number in those files as current. Re-measure, never cite.

---

## 1. The verdict in one table

| measurement | result |
|---|---|
| human SWE sentences solved end-to-end (of 18) | **1 / 18** |
| …that landed on a SWE-flavoured capability at all | 9 / 18 |
| repair verdicts whose PASS satisfies the goal's own stated acceptance | **0 / 1** (flat layout: source byte-identical, stated test still red) |
| repair of a bug, by layout: flat / `pkg/` / `src/app/` / `app/` | **PASS / fail / fail / fail** |
| "find every caller", all four layouts | **PASS x4** (the only layout-independent capability) |
| rename / write-test / lint / type-check, all layouts | **0 / 16** |
| adding "…and save the report to X" to a sentence that passed | **PASS → FAIL** (3 of 4 pairs change route) |
| a single request can run | **unbounded — >600 s measured, no deadline anywhere** |
| same goal, same tree, after one unrelated request | **verdict flips (PASS → FAIL_CLOSED)** |
| registry rows with any timing/bytes field | 2 / 125 (cost is the constant 1 or 2) |
| `provides` never consumed by any `requires` | 86 / 187; 41 rows declare `requires: []` |
| independent-oracle-credited SWE capabilities | **0** (true-capability ledger: 9 rows, 0 SWE, all `MEASURED_SANDBOX`) |
| git / lint / static-type / debugger / profiler / dependency-resolution capabilities | **0 / 0 / 0 / 0 / 0 / 0** |
| can `solve()` target a project outside this repository? | **no — `ROOT` is a module constant** |
| adapters that are stubs (≤34 lines or do no work) | 41 of 123 |

---

## 2. What genuinely works (so the list below is a gap list, not a dismissal)

- `python.source.symbols.index.ast` — real AST index, real `callers_of` map, works in every layout
  I tried, correct artifact, source untouched. **This one is a real capability.**
- `python.refactor.rename_parameter.v1` / `rename_symbol.v1` — genuine, correct, multi-site edits,
  when they are reached (see P0-2, P0-3 for why they usually are not).
- `python.patch.search.test_guided.ast.v1` — a real, honest patch search: it mutates a bound set of
  AST sites, runs the stated test per candidate, replays the winner twice. On a flat module it
  finds the correct fix in ~1.4 s. **Its correctness is not in question. Its authority and its
  reachability are.**
- `shell.command.run` — a real, working universal argv substrate (verified directly: `git log
  --oneline -3` → rc 0, correct stdout, `output_verified: true`).
- The gate chain itself is honest: write authority, promised artifacts, observed effects and
  tool-truth checks all fire, and every refusal I saw was a *correct* refusal of the wrong thing.

The machine has the parts. The problems are that the parts cannot be addressed from a sentence
(P0-2), cannot see a real project (P0-1, P0-3), and are not allowed to finish the job (P0-4).

---

## 3. P0 — blocking "most advanced SWE engineer"

### P0-1. Any real repository layout defeats the repair engine (PYTHONPATH, one line)

The repair engine runs the stated test with `cwd` = repository root and adds **only the source
file's own directory** to `PYTHONPATH`
(`python_test_guided_patch_search_v1.py:332-352`). A test that says `from pkg.calc import add`
needs the *parent of* `pkg` on the path. It never gets it, so baseline and all 500 candidates fail
identically, no candidate is a strict improvement, and the search reports
`OPEN__NO_VERIFIED_CANDIDATE_IN_BOUNDED_SEARCH`:

```
flat        repair: PASS
package     repair: fail   (pkg/calc.py, pkg/test_calc.py, from pkg.calc import add)
src_layout  repair: fail   (src/app/calc.py, tests/test_calc.py, from app.calc import add)
root_pkg    repair: fail   (app/calc.py,  tests/test_calc.py,  from app.calc import add)
```

**This is the single highest-value defect in the repository.** Every "repair works" measurement in
this project was made on a flat two-file module. The layout I tested as `package` is the most
common Python layout in existence. One `PYTHONPATH` entry — the nearest ancestor directory that
contains `__init__.py`, plus the project root — converts 0/3 into 3/3.

### P0-2. The universal action primitive is unreachable from prose

`shell.command.run` is the substrate that would let Brain do *anything on the computer*: git, lint,
mypy, ruff, pdb, cProfile, pytest, make, cargo, kubectl. Its only input is `argv`, typed as
`ARGV` — "the universal action primitive" (`capability_type_surface_v1.py:172`) — and `ARGV`'s
parser is:

```python
def _argv(text):            # capability_type_surface_v1.py:119
    q = _quoted(text)       # :55 — text must START with a quote character
    return shlex.split(q) if q else None
```

So `argv` is bindable **only if the slot text is itself a fully quoted literal**. Measured:

```
'Show the last three git commits in this repository.'   -> None
"Commit the staged changes with the message 'wip'."     -> None
'Run `git log --oneline -3` and save it to out.txt'     -> None
'Lint the python file canonical/runtime/goal_compiler.py' -> None
'Type-check the file canonical/runtime/goal_compiler.py'  -> None
'Run "git log --oneline -3" and save the output to ...'  -> None   (not at position 0)
```

Consequence, measured through the door: `git log` → `python.repository.acceptance.measure.v1`
(refused); `git commit` → `FAIL__RAW_GOAL_COMPILATION_GAP`; `lint` → `pandoc` (missing);
`type-check` → `python.contract.check.crosshair.v1` (package absent → inconclusive);
`debug under pdb` → compilation gap; `profile` → refused. **Six of the seven surfaces an engineer
uses daily are zero — not because the machine lacks them, but because nothing can turn an
imperative into an argv.** The registry census confirms the absence is structural: 0 `git.*`,
0 `lint`, 0 trace/profile/debug, 0 dependency/build capability ids among 125 rows.

### P0-3. `solve()` cannot operate on the user's project at all

`ROOT = Path(__file__).resolve().parents[2]` (`live_integrated_brain_v1.py:41`) is a module
constant, imported by name into the door and used as the root of every path resolution, every
adapter call, every observation and every write-authority check. `solve()` has no `root`
parameter (`inspect.signature(adm.solve)` → `(request)`; passing `root` is silently ignored).

Measured: a fresh project at `/tmp/outside_project`, goal *"Repair `<p>/calc.py` so the unit test in
`<p>/test_calc.py` passes…"*:

```
status: FAIL_CLOSED__PROMISED_ARTIFACT_MISSING   cap: evidence.oracle.hypothesis_property.v1
```

A repair request for a project outside `brain/` is routed to an *evidence oracle*. Brain is an
agent that can only operate on its own repository. Until a request carries a project root that
propagates into derivation, admission, execution, observation and write authority, "do anything on
the computer by itself" is not a measurable statement.

### P0-4. The door PASSes goals whose stated acceptance is false, and never writes the fix

Both repair capabilities declare `NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY` in their own
`hard_nonclaims` (`python_test_guided_patch_search_v1.py:508`,
`python_software_repair_loop_v1.py:163`): they search for a patch, verify it against the stated
test, **restore the source** (`source_restored: true`), and write a report. The door then returns

```
PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED
```

Measured on the real tree immediately after that PASS:

```
source after the "repair": "def add(a, b):\n    return a - b\n..."   (byte-identical)
stated acceptance: python -m unittest test_calc  ->  rc = 1   FAILED (failures=1)
```

The user asked for the bug to be fixed. The machine says PASS. The bug is still there. Everything
downstream — the ledger, the suite, the acceptance receipts, every "5/12" — inherits this: **the
door's PASS means "a tool returned a dict", not "the goal is true".** A software engineer that
cannot write a file is not a software engineer; a door that calls that PASS cannot measure one.

Minimum correct behaviour: (a) the plan applies the verified patch atomically, (b) the stated
acceptance is re-run **on the real tree** before PASS, (c) if the design must stay read-only, the
goal's acceptance must be rewritten to "produce a verified patch", never "repair".

### P0-5. A report clause reroutes a correct plan into a wrong domain — and blocks the correct route

Minimal pairs, identical trees, one clause added:

| goal | without the clause | with "…and save the report to X" |
|---|---|---|
| rename parameter | **PASS** `python.refactor.rename_parameter.v1` | **FAIL** `document.convert.markdown_pdf.pandoc_weasyprint` |
| find every caller | **PASS** `python.source.symbols.index.ast` | **FAIL** `finance.saccr.credit.addon.v1` |
| lint | fail (`COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN`) | fail `pandoc` |
| repair | **hang** (>90 s) | **PASS** |

Three of four pairs change route; two flip PASS↔FAIL. "Save the report to X" is the *most natural*
thing a user says, and it is enough to send a refactor to a PDF converter and a caller query to a
**credit-risk finance capability**. Worse, in `rename` the correct typed plan existed and was
decisive (`plan_report` → `DECISIVE_TYPED_PLAN python.refactor.rename_parameter.v1`) — and the door
never tried it, because the wrong capability *executed and failed*, and
`live_brain_route_admission_v1.py:1984` refuses the typed retry when `executed is True`:

```python
if result.get("executed") is True:
    return result          # "a second guess must never overwrite it"
```

That guard is right about *verdicts* and wrong about *routes*. A wrong-domain capability that
executed and failed is not evidence that the right capability was tried. Measured cost: 0/16 on
rename/write-test/lint/type-check across four layouts, with the correct cap sitting in the
registry and binding.

Related, same class: `write unit test` → `chart.raster.axis_title_unit_binding.v1`; `report of the
functions in X as JSON` → `docx.document.create_from_json_record`; `add requests as a dependency` →
`finance.saccr.credit.addon.v1`; `xlsx`/`sqlite` → `auto.pypi.msgpack` (still, in the benchmark's
own output: `WRONG-CAPABILITY 2`).

### P0-6. A single request can run for days, and there is no deadline anywhere

`run_adapter_locally` (`:688-746`) calls the adapter with **no timeout and no isolation**;
`_execute` has no budget. Four `timeout=` sites exist in 2 443 lines (`:1563` 10 s, `:2353`/`:2365` 8 s,
`:2420` 30 s) and **none of them is on the adapter execution path**. Measured, twice, deterministic:

```
"Run the tests in <D> and save a pass-rate report to <D>/rate.json"
  faulthandler after 25 s:
    python_test_audit.py:136 in subprocess.run          <- inside its per-file loop
    live_brain_route_admission_v1.py:737 run_adapter_locally
```

`python.tests.audit.unittest` defaults `source_root` to `"canonical/tests"` — **the Brain's own
2 143-file corpus** — because the sentence's stated *directory* is never bound (see P1-6), and its
per-file timeout is 180 s with no global cap. Worst case ≈ 2 143 × 180 s ≈ **4.5 days** for one
sentence. `"Repair <D>/calc.py so the unit test in <D>/test_calc.py passes."` hits the same path
and hangs. The same run also shows no `setrlimit`, no container, no memory cap, no cancellation:
the machine is a supervisor that can be stopped only by being killed.

### P0-7. The stated test command is built with the wrong runner, so a third of files read "already passes"

`declared_input_derivation_v1.py:197-201` derives:

```python
out["test_argv"] = [sys.executable, "-B", tests[0]]     # executes the FILE
```

Executing a test file only runs its tests if it has an `if __name__ == "__main__"` guard; the
repository's own comment (`python_test_guided_patch_search_v1.py:315-324`) measures that **695 of
2 019 (34 %)** unittest files do not. Those exit 0 having run nothing, and the engine reads that as
`BASELINE_ALREADY_PASSES`:

```
flat tree + naive argv   -> PatchSearchError:BASELINE_ALREADY_PASSES
flat tree + loader argv  -> pass=True, 1 patch, PASS__VERIFIED_CANDIDATE_PATCH_FOUND
```

`suite_argv()` — the correct loader-based argv — **already exists in the same module** and is used
by `python_test_audit`; the derivation does not use it. This is a two-line wiring fix that changes
the door's verdict on the canonical repair sentence from "tool failed" to "repaired".

### P0-8. "Fix it" gets an unbounded candidate enumeration with no failure budget

`python.patch.search.test_guided.ast.v1` enumerates AST mutations + test-literal substitutions and
runs the **entire stated suite per candidate**, up to `max_candidates` (default 2 000, cap 20 000).
On a real repository a test run is seconds, so one repair sentence is hours; there is no
per-candidate value-of-information ordering, no delta-debugging of the failing test, no bisection
of the failure, no memoisation of the baseline import. The machine trades wall clock linearly where
an engineer uses the traceback — which the machine does not read at all (0 dynamic-analysis
capabilities, P0-2).

### P0-9. Hidden mutable state changes the verdict for the same goal on the same tree

```
find_callers in a fresh tree                       -> PASS
... run one repair request in that tree              (source byte-identical afterwards)
find_callers in the same tree, same sentence         -> FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
```

Four earlier probes in this session also flipped routes between identical runs. State that is
written and read across requests: `canonical/runtime/state/experience_v1.json`,
`canonical/astra_runtime/state/*CONTROLLER_CHECKPOINT.json`, and — measured, created by my runs
alone — **14 files written into tracked directories** (`canonical/tmp_loop_*.json`,
`canonical/tmp_*_supercomposer.json`). A solver whose verdict depends on unrelated history cannot
be measured, cannot be trusted, and cannot be debugged. Also note the direction: the machine writes
into its own canonical tree, not the user's project.

---

## 4. P1 — capability depth

### P1-1. Composition is a claim, not a mechanism
`"A and then B"` forms fail: *"Find the callers of `add` in X and then write them to Y"* →
`FAIL_CLOSED__PROMISED_ARTIFACT_MISSING`; *"Index the symbols in X and write the index to Y"*
succeeds only because one capability does both. Graph census: 187 distinct `provides`, **86 never
consumed** by any `requires`, 41 rows with `requires: []`. `capability_composer_v1` is not imported
by the door at all (only `composer_route_v1` is). There is no planner that takes a multi-step
engineering goal and produces a verified chain; `_try_composed` exists and is reached mainly on
compilation failure, where it fails with `COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN`.

### P1-2. No multi-file change can be produced or applied
`python.source.crossfile_edit.choreograph.v1` says of itself: *"Plans, does not apply: mutation of
sources is a separate concern."* `python.repo.diff_apply_full_testgate.v1` assumes a diff exists;
nothing produces one from a repository state change. `software.repair.choreograph.crossfile.v1`
exists but is unreachable from a sentence. Measured: *"Add a `subtract(a,b)` to X and a matching
test"* → `FAIL__LIVE_CONTROLLER_EXECUTION`.

### P1-3. The stated *directory* is never bound to a directory slot
Only a stated **file's parent** can fill `source_root` (`declared_input_derivation_v1.py:190-195`).
A sentence that names a directory ("the tests in `<dir>`", "everything under `<dir>`") drops it and
the adapter default takes over — which is exactly how P0-6 audits Brain's own corpus instead of the
user's.

### P1-4. The capability layer cannot express cost, so "fastest" is unmeasurable
`cost` is the constant `1` (107 rows) or `2` (18 rows). **123 of 125 rows carry no timing field;
107 of 125 carry no bytes field**; no adapter returns elapsed time or memory. The scheduler
objective in the README (capability gain × … per wall-clock × compute × memory × cost) has no
inputs. Consequences: no capability can be preferred for being fast; no budget can be enforced;
`RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW_V1` is unenforceable at the layer that spends the bytes; and
every "insanely fast" claim is a claim about the constant, not about work.

### P1-5. 41 of 123 adapters are stubs
≤34 lines, or no real work (no `subprocess`, no `ast`, no I/O). The worst offenders are a whole
family of `*_supercomposer` adapters (29 lines each: `software.hardcore.swe.supercomposer`,
`python.orchestration.symbol.supercomposer`, `python.fault.patch.supercomposer`, …) that read the
registry and write `verified: true`. They inflate the capability count and can be *selected*, which
is how a sentence reaches "a capability" that does nothing.

### P1-6. 0 SWE capabilities have independent-oracle credit
`canonical/capabilities/true/TRUE_CAPABILITY_LEDGER_V1.json`: 9 rows, all `MEASURED_SANDBOX`, all
DOCX/finance/scheduling, **0 SWE**. By the project's own law, no SWE row has credit. The harness
that would produce it (`execution_guard/true_capability_harness_v1.py`, 500 lines, fresh instances,
≥2 independent oracles) is imported by **nothing** in the runtime.

### P1-7. Reachability is still measured on self-generated sentences
The census `REACHED_AND_BOUND 411/419` is produced by goals written *from each capability's own
name*. My human sentences reach the same registry and solve **1/18**. The census number and the
front door number are measurements of two different machines; only the second one exists for a
user.

### P1-8. No parallelism, no incremental index, no reuse of work between attempts
Nothing in the door uses threads or processes. A 20-file change is 20 sequential parses. There is
no repository index cached across requests (each solve re-derives), and on a failed primary the
typed retry re-enters the entire gate chain rather than reusing the decisive plan.

---

## 5. P2 — speed and consistency

### P2-1. Latency is dominated by routing, not work
Mean 266 ms/goal over 18 tasks (min 36 ms, max 1 527 ms), on 2-3-file trees. Import cost 82 ms. The
work itself (AST index, patch search on a flat module) is 35 ms-1.4 s. This is fine — and it is
the only part of the performance story that is honest. Everything else about speed is unmeasured
because P1-4 makes it unmeasurable.

### P2-2. The failure path costs the full chain twice
On primary failure the typed retry re-runs front-compile → admit → execute → all honesty gates.
Correct, but it doubles the cost of every refusal, and refusals are 17 of 18 cases.

### P2-3. Verdicts couple to tree size in the wrong direction
`python.tests.audit.unittest` defaults to a 2 143-file corpus; `BRAIN_UNIFIED_MODEL_V1.json` hashes
the whole tree, so a one-line doc edit forces a 9.4 MB model rebuild. The fastest correct edit is
made expensive by coupling, and the most expensive request is the one with the least input.

### P2-4. The machine's own litter is in tracked space
Running 18 goals created 14 untracked files under `canonical/` (see §0/P0-9). Running the test
suite creates ~470 more (the `.gitignore` says so). Any capability that can be selected can write
into the canonical tree.

### P2-5. Refusals are honest but uninformative to a user
`FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN`, `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED`,
`FAIL__RAW_GOAL_COMPILATION_GAP` never say *what would have to be true*: which slot failed to bind,
which capability was one predicate away, what the user should add. For a tool meant to be driven by
a human sentence, the failure text is part of the capability.

---

## 6. Environment / toolchain (caps any measurement, and is a real defect)

| fact | evidence |
|---|---|
| `requirements/software_engineering_kernel_v1.txt` (pinned, hash-locked: `crosshair-tool`, `attrs`, `cattrs`, …) is installed by **0** workflows | `grep -rl "requirements/" .github/workflows` → empty |
| this sandbox has `git`, `jq`, `node`, `npm` and **not** `pytest`, `mypy`, `ruff`, `crosshair`, `z3`, `sympy`, `pandoc`, `tesseract` | `command -v` on each |
| so `python.contract.check.crosshair.v1` → `ORACLE_INCONCLUSIVE`, `python.review.diff_type_gate.v1` → `PASS_BASELINE_ONLY`, `pandoc` routes → `BOUND_APT_METADATA_NOT_FOUND` | measured through the door |
| the honest suite cannot even be reproduced here: no pytest, and `execution_guard/honest_suite_baseline_v1.py` wants a pytest JUnit XML | `python3 -m pytest` → *No module named pytest* |
| live CI: `Drift Immunity Guard` **red** on four of the last six commits visible in `gh run list`; `live-brain-heartbeat` is not a required check and its runs end failure/cancelled/in_progress; `Full private current-main regression` cancelled/pending | `gh run list --limit 25` |

A capability measured against a toolchain CI does not install is measured against nothing.

---

## 7. Governance that blocks the work (agent cannot land these)

1. **Protected paths** (the guard, its test, the referee workflow, `CODEOWNERS`, `AGENTS.md`, the
   honest baseline, `frontier-state-consistency.yml`) fail the referee for any agent change. Every
   fix in §3 that touches the harness or the ruleset needs an owner merge.
2. **Proof bureaucracy outruns capability**: 30 `HARDCORE_VERIFY_*` receipts are tautological —
   each repeats its producer's own hash, none names a separate verifier run. Rule 4 in `AGENTS.md`
   forbids exactly this, and the receipts violating it are already merged.
3. **No additive path to authority**: at most 2 families and +4 atomic predicates per PR, ≤3 new
   capabilities, ≤40 receipts. The ceiling is not "we cannot add capability"; it is that *fixing
   the front door* (a change that flips 15 of 18 sentences) is classified as a routing tweak, not a
   capability gain, so it competes for review attention against receipts that claim more and prove
   less.

---

## 8. The arithmetic of the ceiling

An advanced software engineer needs five things. Measured today:

| need | state |
|---|---|
| **reach a real project** (any directory, any layout) | no — `ROOT` is a constant (P0-3); package layouts unreachable (P0-1) |
| **act on it** (arbitrary tools: git, test runners, compilers, debuggers) | no — `argv` unboundable from prose (P0-2), 0 capabilities for 6 of 7 surfaces |
| **decide what to do** (route a human sentence to the right mechanism) | 1/18, wrong-domain on 3/18, and a report clause flips a correct choice (P0-5) |
| **finish the job** (write the change, prove it on the real tree) | no — repair restores the source and PASSes anyway (P0-4) |
| **know it worked / not run forever / same answer twice** | no — false PASS, no deadline (P0-6), state-dependent verdicts (P0-9) |

Every one of those five is a *wiring and authority* defect, not a missing research idea. The
registry already owns a universal executor, an AST index, a correct rename engine, a correct patch
search, a derivation layer, a type surface, a composer, a bridge enumerator and a true-capability
harness. The gap is that the door cannot address them, cannot hand them the project, and does not
let them finish.

---

## 9. Fix order (each mapped to machinery that already exists)

1. **`_source_env`: add the package ancestor + project root to PYTHONPATH** (P0-1). ~5 lines.
   Unlocks repair on every real layout: 0/3 → 3/3 measured.
2. **`test_argv` → `suite_argv`** in `declared_input_derivation_v1:197` (P0-7). 2 lines. Removes the
   false `BASELINE_ALREADY_PASSES` on 34 % of files.
3. **A deadline and a sandbox for every adapter call** in `run_adapter_locally` (P0-6): total
   wall-clock budget from the request, `subprocess` timeout, `RLIMIT_AS`/`RLIMIT_CPU`, kill the
   group. Plus a global cap on `python.tests.audit` (per-request, not per-file).
4. **Let a decisive typed plan pre-empt a wrong-domain execution** (P0-5): allow the retry when the
   primary capability is outside the stated effect family, keep `executed` as a veto only for
   same-family verdicts. This one change is worth ~6 of the 17 failures.
5. **Apply the verified patch and re-run the stated acceptance on the real tree before PASS**
   (P0-4). The patch is already verified by the engine; the write authority already exists; the
   test runner already exists. Anything less makes the scoreboard meaningless.
6. **A project root on the request**, propagated to derivation, admission, execution, observation
   and write authority (P0-3).
7. **`argv` from an imperative** (P0-2): deterministic verb→tool table over installed binaries
   (`git`, `python -m unittest`, `python -m pdb`, `python -m cProfile`, `mypy`, `ruff`, `jq`),
   bound only from stated evidence, admitted only when the binary exists. This turns `shell.command.run`
   into the universal surface it was built to be: git 0→1, lint 0→1, type-check, debug, profile,
   dependency inspection, all with one mechanism.
8. **Bind stated directories** to `source_root`/`test_paths` slots (P1-3).
9. **Isolate per-request state** (P0-9): no cross-request experience mutation of admission, or make
   it explicit, versioned and replayable. Then add the replay test: same goal, two clean trees,
   identical verdict — as a gate, not a document.
10. **Wire what is already built and unwired** (P1-1, P1-6): `bridge_enumeration_v1` → composer
    `provides_as`/`requires_as`; `true_capability_harness_v1` in front of every new SWE adapter.
11. **Real cost** (P1-4): every adapter returns `elapsed_ms`, `peak_bytes`; the registry carries
    measured medians; the scheduler uses them.
12. **Then** measure on real repositories: three families — multi-file change on a real package,
    failure diagnosis from a real traceback, and a git-history task — each with a filesystem/git
    oracle. Only these numbers should be quoted.

---

## 10. Repro

```bash
cd /home/user/brain
python3 swe_probe_20261029/swe_probe.py        # 1/18 pass, 18 human SWE sentences, world oracle
python3 swe_probe_20261029/layout_matrix.py    # repair: flat PASS, every package layout fail
python3 swe_probe_20261029/writes.py           # PASS, source byte-identical, test still red
python3 swe_probe_20261029/falsepass.py        # door PASS=True; stated unittest rc=1
python3 swe_probe_20261029/report_clause2.py   # adding "save the report to X" flips PASS->FAIL
python3 swe_probe_20261029/hang.py             # 40 s faulthandler: python_test_audit, no deadline
python3 swe_probe_20261029/state.py            # PASS -> (one repair) -> FAIL_CLOSED, same tree
python3 swe_probe_20261029/outside_root.py     # project outside the repo: no root, wrong domain
python3 swe_probe_20261029/repair_flat_and_pkg.py  # naive argv vs loader argv, flat vs package
```

Census commands (read-only):

```bash
python3 canonical/runtime/goal_compilation_benchmark_v1.py     # still prints WRONG-CAPABILITY 2
python3 - <<'PY'
import json,pathlib
r=json.load(open('canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json'))['capabilities']
print(len(r), {e.get('cost') for e in r.values()})
print('timing rows', sum(1 for e in r.values() if '"elapsed' in json.dumps(e)))
PY
```

---

## 11. One sentence

Brain owns the parts of an advanced software engineer — a universal executor, an AST index, a
correct rename engine, an honest patch search, a typed binder, a composer, a true-capability
harness — and today it can reach almost none of them from a human sentence, cannot point them at a
real project, cannot let them write the change, and reports PASS when the change did not happen.
Five wiring and authority defects, listed in §9, separate it from the thing the objective asks for.
