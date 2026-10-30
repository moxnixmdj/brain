# Hardcore software engineering — the complete problem list (2026-10-30, V7)

**The subject.** One thing only: the machine that understands, changes, verifies and ships
software. Documents, PDFs, images, spreadsheets and charts appear here in exactly one role — as
**wrong destinations** the router must refuse. The target is the most advanced, fastest and
smartest software engineer available, so every problem below is judged by three questions only:
does it stop the machine from doing hard engineering work, from doing it fast, or from telling the
truth about what it did.

**Method.** Nothing in this document is remembered; every number was measured today, on this tree,
by instruments that are in the repository and re-runnable:

| instrument | what it answers |
|---|---|
| `execution_guard/swe_request_probe_v1.py --suite sentence` | 28 ordinary advanced requests over one tree |
| `execution_guard/swe_request_probe_v1.py --suite hardcore` | 46 advanced requests over a **fresh** tree each (git history, pyproject, Makefile, JS package) |
| `execution_guard/swe_capability_matrix_v1.py` | 54 designed requests, scored REAL / FALSE / REFUSED / DAMAGED |
| registry census (`load_verified_registry` + `is_verified_entry`) | what the machine claims it can do, and whether a sentence can reach it |
| the repository's own test modules | what is green, and what is red before anything changes |

Every probe case records `pass`, `touched` (did the named file really change), `dirty` (did a
refusal leave edits behind), `status` and `ms`. A pass with `touched=false` on a **source-change**
request is read as a claim the world does not support.

---

## 1. Scoreboard

| measurement | value |
|---|---|
| registry rows / **routable** | 419 / **125** |
| software-engineering rows | **63** (`python` 46, `software` 12, `code` 4, `shell` 1) |
| routable rows that **declare no inputs** — unreachable from any sentence | **19** |
| routable rows that need **6–9 inputs** — nothing derives that many | **8** |
| routable rows whose adapter module **does not exist** | **2** (`knowledge.consistency.assess`, `knowledge.json.fetch.external`) |
| 54-case matrix | **REAL 17 · FALSE 0 · REFUSED 37 · DAMAGED 0**, median **98 ms** |
| 28-sentence probe | **6 answered (21 %)**, 0 trees damaged |
| 46-request hardcore probe | **6 answered (13 %)**, 2 real source changes, **0 refusals that dirtied a tree** |
| hardcore latency | p50 **82 ms** · p90 **399 ms** · max **1 242 ms** |
| repository-scale caller map (cold → warm) | 18.3 s → **2.4 s** |
| installed and unused by any row | `git 2.39`, `node 22` + npm, `gcc`, `make`, `ruff`, `mypy`, `bandit`, `coverage`, `pytest`, `jq`, `patch` |
| not installed (so not cheaply claimable) | `tsc`, `eslint`, `prettier`, `cargo`/`rustc`, `go`, `javac`, `clang`, `cmake`, `docker`, `semgrep`, `shellcheck` |

What the machine really does today, measured: it reads a Python tree (symbols, callers, change
impact), runs a suite or a Makefile, typechecks with mypy, reviews security with bandit, renames a
symbol inside one file, extracts one stated statement, and repairs a bug when the failing test is
named — twice today it wrote `return a - b` → `return a + b` and the suite went green.

Everything an engineer calls *engineering* — write the test, restructure the code, move it, add the
feature, use git, build the package, find out why it broke, make it fast, do it in another
language — is refused. Not silently: the machine usually says something honest. But it cannot do
the work.

---

## 2. The ladder (what an advanced SWE does, rung by rung)

| rung | measured state | detail |
|---|---|---|
| **R1 Read** | ◐ partial | symbol index, callers, change impact, mypy, security review. No "explain this module", no dataflow, no "what breaks if I change this signature" beyond test selection |
| **R2 Change one thing** | ◐ partial | one-bug repair (named test), rename inside one file, extract one stated statement. No inline, no move, no split, no dedupe, no constants, no docstrings |
| **R3 Change many things** | ✗ | two-file repair: compilation gap. Repo-wide rename: `PROMISED_SOURCE_CHANGE_NOT_APPLIED`. The cross-file editor exists but needs an `edits_path` nothing produces |
| **R4 Write tests** | ✗ | `write_unit` → composed step raised; `write_regression` → live-controller failure on the test-guided patch search; coverage-raising refused on a red tree |
| **R5 Build & depend** | ✗ | wheel: composed step raised; `make test`: passes (it is a suite run); add/upgrade dependency: raised; CI setup: rejected |
| **R6 Version control** | ✗ | 0 of 6. commit, branch, status, bisect, revert, changelog — none compiles, though `git` is installed and `shell.command.run` works |
| **R7 Debug** | ✗ | root cause now refuses honestly (was a fabricated PASS, §3); "why is the suite red" is answered by *measuring* that it is red; trace → step raised; no debugger frames, no bisect |
| **R8 Review & ship** | ◐ partial | security review real; diff review gated on a green tree; no PR, no changelog, no release |
| **R9 Performance** | ✗ | "profile `total()`" routed to `chart.raster.axis_title_unit_binding.v1`; "make it faster" → compilation gap |
| **R10 Polyglot** | ✗ | JS suite → Python acceptance runner refuses; JS lint → Python static triage; Python→JS port → gap. `node --test` is installed |

---

## 3. Closed today (three fixes, each with its measured incident)

**3.1 A content request deleted the file it was asked to clean.** `Remove the dead code from
<pkg>/calc.py.` → `rm <pkg>/calc.py`, file **deleted**, `pass=True`. The prose table refused
"remove the duplicate *lines* from the file X" but its noun list held only things that are *read*
inside a file, not the nouns of a code *change*. Fixed in the `rm` row; both directions pinned in
`test_a_content_request_never_deletes_the_file_v1.py`.

**3.2 A chain certified "done" when its only step said UNRESOLVED.** `Find the root cause of the
failure in <pkg>/test_calc.py.` routed to a theorem assessment (`terminal.kstar.root.assess`),
which returned `{"outcome": "UNRESOLVED", "missing_premises": [3 named premises]}`. The composer
wrote `PASS__COMPOSER_CHAIN_EXECUTED` because every step returned a dict, and the door lifted it to
`PASS__COMPOSED_CAPABILITY_CHAIN`. **No diagnosis existed anywhere in the answer.** Now the last
step's own verdict is the chain's verdict, and the composer's name for the failure survives to the
caller: `FAIL_CLOSED__COMPOSED_STEP_UNRESOLVED`, `failed_step.reason = outcome=UNRESOLVED`.
Pinned in `test_a_chain_that_came_back_unresolved_is_not_a_pass_v1.py`, including the exact
counter-case that must keep passing: `rm` reports `output_verified: false` **because the output is
absent**, which is the promise being kept, and deletions still certify.

**3.3 Requests died on their own scratch.** Two of 46 hardcore requests printed a raw adapter error
instead of an answer: `output already exists: canonical/astra_runtime/tmp/spool_0_output.json`. The
planner makes spool paths deterministic on purpose, so the *first* request worked and every later
one that needed the same slot was refused by its own leftovers. Spool artifacts are now replaceable
by later runs; **every other existing output path is still somebody's file and still refused**.
Pinned in `test_a_second_request_does_not_die_on_the_first_requests_scratch_v1.py`.

---

## 4. The problems

### A · Reach — the request does not arrive at the right capability

**A1 · Wrong-family routing (4 of 46 measured).** `Profile the function total and tell me where the
time goes` → **`chart.raster.axis_title_unit_binding.v1`** (a chart-reading row). `Extract the magic
numbers into constants`, `Split this module into two`, `Set up CI` → all three →
`software.hardcore.kernel.orchestrate.v1`. `What changed since the last commit?` →
`python.source.change_impact.testselect.v1`. `Run the javascript test suite` →
`python.repository.acceptance.measure.v1`. Every refusal is honest and every one is undiagnosable:
a caller cannot tell "we have no such capability" from "you asked badly".

**A2 · Nineteen routable rows that no sentence can ever reach.** All the advanced orchestration
rows declare **no inputs**: `software.hardcore.swe.supercomposer`,
`software.hardcore.final.supercomposer`, `python.pr.land.composer.v1`, `python.test.pipeline.verifier.v1`,
`python.patch.review.supercomposer.v1`, `python.fault.patch.supercomposer.v1`,
`python.provenance.coupling.supercomposer.v1`, `python.evidence.contract.supercomposer.v1`,
`software.review.synthesis.supercomposer.v1`, … The most advanced machinery in the repository is
advertised, verified, and unreachable.

**A3 · Eight rows that want 6–9 inputs.** `python.software.issue_to_pr.orchestrate.v1`,
`python.repo.pr_realize.v1`, `python.fault.localize.dynamic.dataflow.v1`,
`python.patch.search.test_guided.ast.v1`, `code.patch.tree_sitter.verify.v1`, … Nothing derives a
seventh slot, so they are equally unreachable from the other end.

**A4 · Two rows whose adapter does not exist.** `knowledge.consistency.assess` and
`knowledge.json.fetch.external` point at `runtime_native_action`, which is not a module. A registry
that certifies a capability cannot contain a row that cannot run.

**A5 · The row exists and is still not allowed to run (6 of 46).** `route admission rejected` is the
largest single family after the compilation gap: `extract_const`, `type_hints`, `split_module`,
`setup_ci`, `js_lint`, `git_status`. The sentence finds a row, the row finds a plan, and the door
declines — with `R3_WEAK_EVIDENCE` and no statement of what evidence would have sufficed.

**A6 · No row compiles at all (12 of 46).** git commit/branch/bisect/revert, feature
flag/logging, refactor move/dedupe, perf optimise, polyglot port, explain-module, two-file repair.
`FAIL__RAW_GOAL_COMPILATION_GAP` is accurate and useless: it is the machine's way of saying "there
is no capability here" without saying which capability is missing.

### B · Change — the engineering itself

**B1 · No test authoring (0 of 3).** The first act of every real change is a failing test. The
registry has three rows that touch it and no request reaches any of them.

**B2 · Refactoring is rename + extract only.** Missing: inline, move (function or module), split,
dedupe, extract constant, add type hints, add docstrings, remove dead code. Also missing: any
repo-wide rename — `rename_repo` refuses with `PROMISED_SOURCE_CHANGE_NOT_APPLIED`, which is the
machine catching itself before it lies, and is still not the work.

**B3 · No multi-file change.** `Repair calc.py and util.py so the tests pass` is a compilation gap.
`python.source.crossfile_edit.choreograph.v1` exists and needs an `edits_path`; nothing in the
pipeline produces one. That is one derivation away from the single most valuable capability in the
list.

**B4 · No feature work.** CLI flag, logging, error handling, "implement this issue end to end" — 0
of 4, and the matrix agrees (feature 0/7).

**B5 · No version control.** 0 of 6. `git` is installed; `shell.command.run` executes argv;
`python.pipeline.allowlist_gate.v1` exists with no inputs. Nothing in the registry declares commit,
branch, diff, bisect or revert.

**B6 · No build, packaging or dependency work.** Wheel, dependency add/upgrade, CI. Two of these
(`add_dep`, `upgrade_dep`) die inside a composed chain with `STEP_RAISED_OUTCOME_UNKNOWN` — the
machine tried, something raised, and nobody knows what the world looks like.

**B7 · No diagnosis.** `Find the root cause` now refuses (it used to fabricate a pass); `why is the
suite red` is answered by *measuring* that it is red — the question is *why*, the answer is *that*.
No dataflow, no debugger frames, no bisect, no "who last touched this line".

**B8 · No performance engineering.** Profiling routes to a chart row; optimisation is a gap. This is
the rung most senior engineers are hired for.

**B9 · No polyglot.** Python only. `node --test` is installed and the JS suite still refuses; JS
lint routes to a *Python* static triage row; porting a function between languages is a gap.
`code.multilanguage.parse.tree_sitter.v1` (tree-sitter, language-agnostic) is routable with **zero
inputs**.

**B10 · Repair works only in the narrowest shape.** One named failing test, one file, local. And
when the named subject is innocent — `The behaviour of mul() regressed` against a tree whose bug is
in `add` — the machine fixes `add`, the suite goes green, `pass=True`, and **nothing ever tells the
caller that `mul` was never the problem**. A repair that disproves its own premise must report it.

### C · Truth — the machine must not certify what it did not do

**C1 · A "why" question is certified by a measurement** (measured today, still open).
`The suite in <dir> is red. Find out why.` → `python.repository.acceptance.measure.v1` →
`pass=True`. The capability declares "tests measured", the sentence asks for a cause, and no stated
-effect gate connects them.

**C2 · Measurement refuses exactly when it matters.** Coverage and mutation refuse on a red tree
(`CAPABILITY_REFUSED_SUITE_RED`, `CAPABILITY_REFUSED_BASE_WORLD_RED`). The moment you most need to
know the coverage of a broken repo is the moment you have one.

**C3 · Stale scratch is consumed as input.** `{"error": "EDIT_PLAN_INPUT_INVALID", "message":
"edits_path unreadable JSON"}` — a spool artifact from an earlier run was bound as this request's
input. Writing our own scratch is fixed (§3.3); *trusting* a file merely because it sits in the
spool is not.

**C4 · Composition still cannot say "unknown" precisely.** Six hardcore requests end in
`STEP_RAISED_OUTCOME_UNKNOWN` — a step raised, the world is unobserved, and the answer says so.
Honest, and still the vaguest possible report of a concrete event.

**C5 · The referee is rung.** The two command-reading modules carry **17 + 1** red test ids at HEAD
(proved identical with today's changes stashed), and three more red ids in modules this branch
touches. A referee that is red cannot certify anything, including its own fixes.

**C6 · The PR-scope guard is out of reach of the process.** `FRONTIER_PR_SCOPE_TOO_BROAD_RECONCILE_AND_SPLIT`:
17 non-intent sensitive files have accumulated on one session PR. The remedy the guard names —
split — needs a branch this session may not create. Not weakened, not bypassed, open.

### D · Speed — the machine must be fast at real scale

**D1 · Repository-scale questions cost seconds.** Caller map over `canonical/runtime`: **18.3 s**
cold, **2.4 s** with the index cache landed earlier today. Real work happens on the large tree, so
2.4 s is the number that matters and it is still 30× the probe's p50.

**D2 · Nothing is reused between requests.** Every request reloads 419 registry rows, re-derives
its inputs, and re-plans from scratch.

**D3 · Steps are serial.** Typecheck 861 ms, repair 1.2 s — each is a single serial step; the
independent parts (parse, index, run) never overlap.

**D4 · No plan, no checkpoint, no resume.** Every request is one shot. Long-horizon work — the only
kind that matters for "build software" — has no representation at all.

**D5 · The bottleneck is capability, not speed.** p50 across 46 advanced requests is **82 ms**.
Routing is already fast. The machine is slow at engineering because it mostly cannot do it.

### E · Learning — the machine does not improve

**E1 · Refusals are not collected.** 40 of 46 advanced requests refuse, identically, every time. No
queue records that the machine is missing git, a test author, a refactoring engine.

**E2 · No decomposition.** One capability per request (or one guessed chain). Nothing plans "write
the test → change the code → run the suite → commit".

**E3 · Ranking is lexical.** A1 is the evidence: `profile` matching a chart row, `kernel.orchestrate`
swallowing every hard refactor. The ranker sees words, not work.

---

## 5. Order to fix (each step makes the next cheaper)

1. **C5 then C1** — a green referee first, then the "why" gate; nothing else can be trusted while
   the referee is red, and a certification that answers a different question is the one failure a
   user cannot see.
2. **B3 + B1** — one derivation each for `python.source.crossfile_edit.choreograph.v1` (`edits_path`)
   and `python.tests.generate.scaffold.v1`. Multi-file editing and test authoring, from machinery
   that already exists and already has adapters.
3. **B5** — declare the git family over the installed `git` (commit, branch, diff, revert, bisect).
   Six sentences, one binary, zero new subsystems.
4. **A2 + A3** — give the 19 no-input and 8 over-parameterised rows a derivation. That is where
   `issue_to_pr.orchestrate` and `repo.pr_realize` live.
5. **B2** — inline, move, split as three rows on the existing AST editor.
6. **A1 + E3** — rank by work, not by word: family-first routing with the family taken from the
   verb-object pair.
7. **B9** — JS/TS behind `code.multilanguage.parse.tree_sitter.v1`; `node --test` is already here.
8. **B7 + B8** — debugging (frames, bisect) and profiling (the `coverage`/`cProfile` machinery is
   installed).
9. **D2 + D4** — reuse the registry across requests; give long work a plan and a checkpoint.
10. **E1** — refusals feed an acquisition queue; the queue feeds the roadmap.

---

## 6. Reproduction

```bash
cd /home/user/brain
python3 execution_guard/swe_request_probe_v1.py                     # 28 sentences  -> 6 answered
python3 execution_guard/swe_request_probe_v1.py --suite hardcore    # 46 requests   -> 6 answered
python3 execution_guard/swe_capability_matrix_v1.py                 # 54 cases      -> 17/0/37/0
python3 canonical/runtime/verify_brain_unified_model_v1.py          # 33/33
python3 -m pytest -q canonical/tests/test_a_content_request_never_deletes_the_file_v1.py \
                    canonical/tests/test_a_chain_that_came_back_unresolved_is_not_a_pass_v1.py \
                    canonical/tests/test_a_second_request_does_not_die_on_the_first_requests_scratch_v1.py
```

Fixtures (`canonical/astra_runtime/tmp/swe_request_probe`, `…/swe_hardcore_probe`) are throwaway and
git-ignored; the probes rebuild them.

---

## 7. One paragraph

The machine is an **honest Python reader with three verified write operations and a router that
often knows it is lost** — 6 of 28 ordinary advanced requests and 6 of 46 hardcore ones are
answered, no refusal damages a tree, and the median answer takes 82 ms. The gap to "the most
advanced, fastest, smartest software engineer" is not speed and not truth-telling: it is that
writing a test, restructuring code across files, using version control, building a package,
diagnosing a failure, making something faster and touching a second language are **absent**, while
the registry already contains 27 routable rows for exactly that work which no sentence can reach and
two rows whose adapters do not exist. Today three defects that made the machine lie were closed —
a deletion certified as PASS, a chain certified as PASS with no answer, requests dying on their own
scratch — and the census that found them is now two probes in the repository instead of one scratch
script.

*Authority: NONE — sandbox measurement, not independent verification.*
