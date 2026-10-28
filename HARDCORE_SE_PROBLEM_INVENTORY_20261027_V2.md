# All the problems — hardcore software engineering

**Measured on `2754cf0` (this branch), 2026-10-27. Every number below came from running the machine.**

---

## Bottom line

I gave the machine **32 hardcore-SE tasks** in scratch git repositories it had never seen — the
tasks a strong engineer is hired for: refactor, localize, repair, review a diff, apply a patch, run
and gate tests, index symbols, choose tests for a change, commit, revert, branch, implement a
module, explain a failure.

| outcome | count | share |
|---|---|---|
| **genuinely correct** (right capability, real artifact) | **6** | 19% |
| **hollow PASS** (wrong capability, credible-looking artifact, accepted as success) | **3** | 9% |
| honest refusal / failure | 23 | 72% |

The project's own benchmark, on the same machine at the same moment, reports **0.8377**. Both
numbers are true. They measure different things — and *that gap is the single most important
problem in the repository*.

Latency is not the problem: every one of the 32 decisions took **0.2 – 1.1 s**.

---

## What the machine actually has

It is not capability-poor. It has a real hardcore-SE surface:

```
419 registry rows
 125 VERIFIED_BOUND_CAPABILITY
 294 RECEIPT_BACKED_PENDING_PROMOTION   (293 are "<path>.py.auto.v1", verification.pass = false)
 106 routable from a plain goal
  19 verified capabilities declare NO inputs at all
  64 verified capabilities are software-engineering shaped
```

The 64 divide into repair (11), refactoring (5), static analysis (9), test (6), review gates (7),
repo/PR (4), impact selection (3), acceptance/measurement (4), plus 8 zero-input "supercomposers".

So this is **not** a "we need more tools" problem first. It is a **reachability** problem: the tools
exist, and language cannot get to them.

---

## The measured probe table (22 tasks, one per capability, natural phrasing)

| task | bindable from the sentence? | selected | result |
|---|---|---|---|
| rename a function | ❌ `module` | markdown→PDF | fail |
| rename a parameter | ❌ `module` | markdown→PDF | fail |
| extract lines into a function | ❌ `end_line` | markdown→PDF | fail |
| index symbols | ✅ | ✅ right | **PASS** |
| resolve a symbol / find callers | ❌ `queries` | symbol index | PASS (substitute) |
| AST audit | ✅ | ✅ right | **PASS** |
| localize a fault | ✅ | tree-sitter **parse census** | PASS ← **hollow** |
| repair, test-guided | ✅ | ✅ right | tool non-success |
| repair, coupled | ✅ | ✅ right | **PASS** |
| search for a patch | ✅ | ✅ right | tool non-success |
| audit a unittest suite | ❌ `pattern` | ✅ right | controller failure |
| generate test scaffolding | ✅ | tree-sitter **parse census** | PASS ← **hollow** |
| apply a diff + full test gate | ❌ `anchor_path` | `shell.command.run` | fail |
| coverage gate on a diff | ❌ `anchor_path` | `shell.command.run` | fail |
| security gate on a diff | ❌ `output_path` | `shell.command.run` | fail |
| type gate on a diff | ❌ `python_executable` | `shell.command.run` | fail |
| perf gate on a diff | ❌ `anchor_path` | `shell.command.run` | fail |
| mutation gate on a diff | ❌ `anchor_path` | `shell.command.run` | fail |
| select tests affected by a change | ⚠️ front-only | ✅ right | **PASS** |
| check a contract | ❌ `target_path` | ✅ right | controller failure |
| measure repository acceptance | ✅ | ✅ right | **PASS** |
| synthesize a patch (CEGIS) | ❌ `manifest` | ✅ right | controller failure |

`bindable 8/22 · selected 10/22 · passed 8/22` — and 6 of the 22 selections were
**`shell.command.run`**.

Five more: `git status` ✗, `git diff` ✗, `git commit` ✗, `git revert` ✗, `git branch` ✗ — all five
attracted `source.candidates.enumerate.stdlib` or `shell.command.run`.
Four more: "explain why this test fails" → test-selection, fail. "read the traceback and fix it" →
fail. "repair then run the tests" (two steps) → `ROUTE_ADMISSION_REJECTED`.
"Implement a module with mean/median/mode" → **PASS** by `python.source.audit.ast`, which audited a
`stats.py` that contained **another capability's JSON report**, and called it a success.

---

## The seven defects

### 1. The benchmark speaks the registry's private dialect — so the score is not language understanding

Same world, same seeded bug, two phrasings:

```
bench : "Repair python bug in source <S> with ast patch search guided by test <T>
         using test command \"python3 <T>\" and save output_path <R>."
        -> python.patch.search.test_guided.ast.v1                      PASS

human : "The tests in <T> are failing. Work out what is wrong with <S> and fix it,
         then write a short report of what you changed to <R>."
        -> python.software.repair.apply.verified.v1   PROMISED_ARTIFACT_MISSING
```

6 of the 8 python bench families contain at least one dialect token (`source_root`,
`test command`, `output_path`, `with the … repair loop`, `pattern`). The benchmark is measuring
**template recall**, and it reads 0.84 while a human who says the same thing in English gets 19%.

**Consequence:** every optimisation driven by that number can move it without making the machine
better. This is the top problem, because it corrupts the signal that all other work is judged by.

### 2. Binding is name-matching, not role-binding

A path binds to a slot only if the sentence contains **the slot's own stem noun**:

| capability | slot | what an engineer says | outcome |
|---|---|---|---|
| `repo.diff_apply_full_testgate` | `anchor_path` | "the repository" / "the worktree" | unbound → dropped |
| ×4 review gates | `anchor_path` | same | dropped → `shell` |
| `symbols.resolve` | `queries` | "the symbol add" | unbound |
| `tests.audit.unittest` | `pattern` | "test_*.py files" | unbound |
| `contract.check.crosshair` | `target_path` | "the python module X" | unbound |
| `change_impact.testselect` | `changed_paths` | "the change to X" | front-binder only |
| `cegis.z3` | `manifest` | "the manifest" | unbound |
| `extract_function` | `start_line`/`end_line` | "lines 4 to 5" | unbound |
| `rename_symbol` / `rename_parameter` | `module`, `qualname` | "rename add to plus in module X" | unbound |

**18 of the 64** verified SE capabilities have at least one slot outside the binder's vocabulary, and
`target_path` shows that even an in-vocabulary `*_path` fails when the sentence doesn't happen to say
"target". There is no role table mapping *what a human calls the thing* to *what the registry calls
the slot*. Every "drop the candidate" path here is silent: the capability simply disappears from the
ranking and something else wins.

### 3. Execution knobs are treated as required inputs

`python_executable` and `timeout_s` are template slots in 8 SE capabilities. Every adapter already
defaults them (`args.get("timeout_s") or 300`). The binder raises, the candidate is dropped, and if
it was already selected, `_render_template` raises **again at dispatch**. Measured: the type gate is
unreachable because of `python_executable`.

### 4. The output format is inferred by substring, and a wrong guess is fatal

`python.review.diff_security_gate.v1` writes a JSON report. Its keywords include
"**hardcoded password**". The format inference tests `"word" in semantic_blob` — a substring — so it
concludes the artifact is a **`.docx`**, and then refuses to bind the `.json` path the sentence named:

```
"Review the diff <D> for security problems and save the report to <R>.json"
   -> GOAL_INPUT_BINDING_REQUIRED output_path     (wanted = {".docx"})
```

One capability in the whole SE surface is hit by this today, but the mechanism (substring marker →
hard extension constraint → hard failure) is unbounded.

### 5. All eight "hardcore SWE supercomposers" can never be selected

`software.hardcore.swe.supercomposer.v1`, `software.hardcore.final.supercomposer.v1`,
`software.hardcore.closing.supercomposer.v1`, `python.patch.review.supercomposer.v1`,
`software.test.contract.supercomposer.v1`, `python.evidence.contract.supercomposer.v1`,
`software.review.synthesis.supercomposer.v1`, `python.fault.patch.supercomposer.v1` — plus
`python.fault.provenance.fusion.v1`, `python.orchestration.symbol.supercomposer.v1`,
`python.pipeline.allowlist_gate.v1`, `python.pr.land.composer.v1`, `python.test.pipeline.verifier.v1`,
`python.symbol.resolve.standalone.v1`, `python.refactor.test_scaffold.fusion.v1`.

**19 verified capabilities declare zero inputs.** A zero-input capability either binds every
sentence (so it is a catch-all and is excluded from being the decision) or binds nothing. The most
ambitious-looking names in the registry are therefore decorative. Whatever they do, no sentence can
ever reach them.

### 6. Hollow PASS: the wrong tool answers, and the door accepts it

| asked | answered by | verdict |
|---|---|---|
| localize the fault | `code.multilanguage.parse.tree_sitter.v1` — a **parse census** (`file_count`, `error_count`) | PASS |
| generate unit test scaffolding | same parse census | PASS |
| implement a module with mean/median/mode | `python.source.audit.ast` — an audit | PASS |

The door checks that the promised artifact **exists** and that the capability's own `expect` field is
satisfied. It never checks that the artifact **is the thing the sentence asked for**, and it never
parses semantic content. 84 of 125 verified capabilities satisfy `output_verified == true`; 10
satisfy `gate == "PASS"`.

Worse, the artifact can be actively corrupt: in the third case a capability wrote **JSON into
`stats.py`** — a file the sentence named as a Python module — and the next run's AST audit consumed
it and passed. No extension/type coherence check exists between the promised artifact and the
capability's declared effect.

### 7. Missing verbs — the parts of the job with no capability at all

Grepping the 125 verified capabilities for the verb an engineer would use:

| verb class | capabilities | note |
|---|---|---|
| `git status` / `log` / `checkout` / `revert` / `bisect` / `blame` | **0** | only `repo.pr_realize` (branch→commit→push→PR) and `repo.diff_apply_full_testgate` exist, and both are unbindable |
| `git commit`, `git branch` | 1 | only inside the unbindable PR realize |
| debugging (`pdb`, breakpoints, step) | **0** | |
| coverage **measurement** | 0 | a coverage *gate* on a diff exists; nothing reports what is uncovered |
| profiling / benchmarking | 1 | only the perf *gate* |
| fuzzing | **0** | |
| property-based testing | 1 | an oracle *node*, not a synthesizer |
| docstrings / documentation | **0** | |
| DB migrations / schema | **0** | |
| containers / Dockerfiles | **0** | |
| OpenAPI / interface contracts | **0** | |
| concurrency / races / locks | **0** | |
| SQL, regex | **0** | |
| flaky-test detection | **0** | |
| test generation | 1 | `tests.generate.scaffold` — and it doesn't reach the route |

### 8. Two smaller ones that cost real tasks

- **A referee suite that was already red is read as "you broke it."** The test-guided repair loop
  refuses `TOOL_REPORTED_NON_SUCCESS` when the world's suite fails before the edit. A refactor's
  contract is "no worse than before", not "green".
- **Two-step requests are rejected, not planned.** "Repair X so the tests pass, then run the tests
  and save the report" → `ROUTE_ADMISSION_REJECTED`. The DAG planner exists; it does not fire here.

---

## What "the most advanced software engineer" actually requires

Ordered by leverage, each item with the measured evidence that motivates it:

1. **Make the benchmark speak English.** Add a paraphrase layer to every SE family: for each
   generated world, run 3 phrasings — the dialect one and two human ones — and score the human ones.
   Until the score is computed on human phrasing, it cannot distinguish progress from dialect
   memorisation. *(The 0.84-vs-0.19 gap.)*
2. **A role table for slots.** Map `what a human says` → `what the registry calls it`
   (`anchor_path` ← "repository"/"worktree"/"repo"; `target_path` ← "module"/"file"/"source";
   `queries` ← "symbol"/"the names …"; `pattern` ← "test_*.py"; `manifest` → the json/py that lists
   the case; `start_line`/`end_line` ← "lines N to M"; `module`/`qualname` ← the renaming grammar).
   One table, ~20 rows, unblocks 18 measured capabilities including all six review gates and both
   repo verbs. *(8/22 bindable today.)*
3. **Default execution knobs instead of requiring them.** `python_executable`, `timeout_s` and
   friends are the adapter's business. *(Type gate unreachable today.)*
4. **Type-coherent artifacts.** The promised artifact's extension must match the effect the
   capability declares, the writer must refuse to write JSON into a `.py`, and the door must parse
   the artifact and check it answers the sentence. *(JSON-in-`stats.py`, three hollow PASSes.)*
5. **Git as first-class verbs**: status, diff, log, commit, branch, checkout, revert, bisect, blame —
   stdlib + `git` subprocess, each with a family. *(0/5 git tasks today; the most-used verb class in
   real engineering.)*
6. **Make the orchestrators reachable.** Give the 19 zero-input capabilities a declared contract
   (inputs it consumes from the plan, or a state path) so a compound request can select them;
   otherwise delete them — a capability no sentence can reach is a liability, not a capability.
7. **Dynamic analysis**: coverage measurement, profiling, tracing, flaky detection, and a debugger
   driver. *(0 today; this is what separates "static linter" from "engineer".)*
8. **Test synthesis that is graded by killing mutants.** `tests.generate.scaffold` exists; make it
   synthesize a suite, then grade it by mutation kill ratio, and add the family. *(0 today.)*
9. **Baseline-aware referees** so a refactor is judged as "no regression". *(Already-red world.)*
10. **Benign fallbacks instead of a shell.** `shell.command.run` answered 27% of the hardcore tasks
    I gave it. Either teach the shell to write the promised artifact with provenance, or remove it
    from plain-goal routing.

---

## How to reproduce (all of it)

```bash
# 1. the 22-capability natural-phrasing probe
python3 /tmp/se_probe.py            # writes /tmp/se_reach.json

# 2. registry composition
python3 - <<'EOF'
import sys; sys.path.insert(0,'.')
from canonical.runtime import live_integrated_brain_v1 as live, goal_front_compiler_v1 as front
from collections import Counter
reg = live.load_verified_registry()
print(len(reg), Counter(e.get('status') for e in reg.values() if isinstance(e,dict)))
print("routable", len(front.routable_registry(reg)),
      "zero-input", sum(1 for c,e in reg.items() if isinstance(e,dict) and not front.input_keys(e)))
EOF

# 3. the dialect A/B: same seeded world, bench phrasing vs human phrasing
#    (live_solver_families_v5.gen_python_ast_patch_search, then solve both goals)

# 4. the project bench, for contrast
python3 execution_guard/live_solver_end_to_end_measurement_v1.py \
  --seed 424242 --per-family 6 --oos 20 --entries new --out /tmp/bench.json
```

Probe sources for this document: `/tmp/se_probe.py`, `/tmp/gitprobe.py`, `/tmp/one_probe.py`,
results in `/tmp/se_reach.json`.

---

## Re-measured after the role/binding work (2026-10-27, same machine, same probe)

The table above is the diagnosis. This is the reading after the fix, on the SAME 22 sentences
(no sentence was softened, no registry row was edited):

| | before | after |
|---|---|---|
| bindable from the sentence alone | 8 / 22 | **22 / 22** |
| selected the right capability | 10 / 22 | **21 / 22** |
| executed and passed | 8 / 22 | **12 / 22** |
| answers by `shell.command.run` | 6 | **0** |

What changed, and the measurement that forced each change:

* **A command word preceded by a determiner is not a command.** "Apply the diff …" and
  "Gate the diff …" were parsed into argv for `shell.command.run`; "Compare A with B" and
  "Diff A and B" still are. This is what removed six `shell` answers.
* **The role lexicon.** A person calls `anchor_path` "the repository", `target_path`
  "the python module", `changed_paths` "the change to", `pattern` "test_*.py". The lexicon
  (`canonical/runtime/input_role_lexicon_v1.py`) maps what a person says to the slot, and the
  binder accepts it only when the sentence states exactly one value of the right KIND.
* **Identifiers are read, not inferred.** "rename the function add to plus in module X" now binds
  `old_symbol`/`new_symbol`/`qualname`/`module`/`source_root`; "rename the parameter a to x in the
  function add" binds the parameter form; "extract lines 2 to 2 of the function add … into a new
  function named plus_of" binds the span and the enclosing function. All three execute and pass.
* **A repository anchor is stated when the sentence names a file inside the repository.** The tree
  a diff applies to is the tree the diff lives in; `source_root` is NOT treated this way and must
  still be stated (it is measured by the refusal tests).
* **Execution knobs are not inputs.** `timeout_s`, `python_executable`, `max_mutants`,
  `min_kill_ratio` are omitted from the action so the adapter's own default applies.
* **Whole-word format inference.** "hardcoded password" no longer makes a JSON report "a .docx".
* **A slot the sentence never filled is SKIPPED, not ambiguity.** `source_root` on a repair
  capability is not a reason to refuse a sentence that names a jq filter; the walk continues down
  the ranking. An ambiguous slot (two files named, `<key>:2_…`) still keeps the request open.
* **A diff slot takes a patch.** The F23 elimination pass may choose WHICH stated file fills a
  slot, never that a `.json` is a unified diff.
* **The head verb decides the act.** "Localize the fault …" now selects
  `python.fault.localize.dynamic.dataflow.v1` instead of the tree-sitter parse census, which had
  won by matching three nouns from the medium. The bonus applies to verbs that IDENTIFY an act,
  not to generic ones, and is gated so the QR decoder/generator counterexample is unchanged.

Still open, measured, in this same run:

* `tests_scaffold` selects the tree-sitter parse census (hollow PASS): the sentence's head verb
  "generate" is generic, so the verb rule does not separate it from the parser. The scaffold tool
  itself refuses on the fixture's unannotated parameters — honest, but the selection is still wrong.
* 9 of the 12 remaining failures are capabilities that were selected CORRECTLY and then reported
  non-success: the review gates fail the seeded diff (the fixture does not meet the gate), the
  test-guided repair loop cannot fix the seeded bug, `contract.check.crosshair` and
  `patch.synthesize.cegis.z3` need an installed `crosshair`/`z3`. That is execution depth, not
  reachability, and it is the next unit of work.
