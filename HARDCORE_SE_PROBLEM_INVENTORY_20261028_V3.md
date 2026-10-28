# All the problems — hardcore software engineering, answered

**Measured 2026-10-28 on this branch. Every number below came from running the machine.**
Instrument: `execution_guard/hardcore_se_reachability_v1.py` (in the repository, re-runnable).

---

## The answer in one table

The question was "what are all the problems?" — so the answer is a **complete inventory**, and
then the measurement of it. There are three kinds of problem, and only the third kind is about
what the machine cannot do:

| kind | count | what it means |
|---|---|---|
| **A. language reachability** — the tool exists, the sentence cannot reach it | 22 of 22, now closed | was the dominant defect; fixed and measured below |
| **B. execution depth** — the tool is reached and the *work* fails | 1 of 22 visible here, ~9 latent | adapters that refuse, crash, or measure nothing |
| **C. missing verbs** — no capability exists at all | **38** distinct acts | the real frontier: the machine cannot do these in any phrasing |

### The 22 hardcore-SE tasks, before and after this unit

Same 22 sentences, same machine, same day. No sentence was softened and no registry row was
edited; what changed is the compiler, the binders, and five adapters.

| | before | after |
|---|---|---|
| bindable from the sentence alone | 8 / 22 | **22 / 22** |
| selected the right capability | 10 / 22 | **22 / 22** |
| executed and passed | 8 / 22 | **22 / 22** |
| answered by `shell.command.run` | 6 | **0** |
| hollow PASS (right-looking artifact, wrong tool) | 3 | **0** |

Each row executes the real adapter against a real repository and is judged on the artifact it
wrote. Regression status: the front-compiler suite has the **same 12 failures on `origin/main`**
(verified in a clean worktree), so nothing here regresses; `test_f25_a_quoted_literal…` and
`test_f24_a_runtime_native…`, which were red mid-way through this work, are green again.

Honesty note on the perf gate: it gates on **physical timing**, so on a loaded box a 0.98× ratio
can land on either side of a 1.10 tolerance. It is green here (`gate: PASS`, `slowdown_ratio:
0.9813`), and it is the one row whose colour is a property of the machine as well as the code.

All 22 rows: rename symbol, rename parameter, extract function, symbol index, symbol resolve, AST
audit, fault localization, test-guided repair, coupled repair, patch search, unittest audit, test
scaffolding, diff apply + full test gate, coverage gate, security gate, type gate, change-impact
test selection, contract check (CrossHair), acceptance measurement, CEGIS patch synthesis (Z3),
performance gate, mutation gate.

---

## A. Reachability: what was actually wrong (22 defects, all measured, all closed)

**A1. A command word was found inside prose.** "Apply the diff …" and "Gate the diff …" were
parsed into argv for `shell.command.run`, because the word *apply* appears in the sentence. Six of
22 tasks were answered that way. Fixed by refusing a program word that is preceded by a
determiner, while "Compare A with B" / "Diff A and B" still parse as commands.

**A2. Binding was name-matching, not role-binding.** A path bound to a slot only if the sentence
used the *slot's own noun*. An engineer says "the repository", "the python module", "the change
to", "test_*.py". Now `canonical/runtime/input_role_lexicon_v1.py` maps **what a person says** to
the slot, with a KIND (file / files / dir / identifier / line span / text / knob), and the binder
accepts an alias only when the sentence states exactly one value of that KIND.

**A3. Identifiers were not read at all.** "rename the function add to plus in the python module X"
states `old_symbol`, `new_symbol`, `qualname`, `module` and `source_root`; nothing parsed them.
Now they are read (never inferred), including the parameter form and the enclosing-class form, and
`module`/`source_root` are bound *together* because adapters resolve one relative to the other.

**A4. A line span states two slots.** "Extract lines 2 to 2 of the function add … into a new
function named plus_of" now binds `start_line`, `end_line`, `qualname` and `new_name`.

**A5. A repository anchor was demanded although the sentence named a file in the repository.**
The tree a diff applies to is the tree the diff lives in. This fires only for the repo-anchor
roles; `source_root` is still required to be stated, and the refusal tests still pass.

**A6. Execution knobs were treated as required inputs.** `timeout_s`, `python_executable`,
`max_mutants`, `min_kill_ratio` are slots where every adapter already writes
`args.get(k) or default`. The binder raised on them, so a fully grounded capability was dropped —
or died at dispatch. They are now omitted from the action and the adapter's own default applies.
A number the sentence *does* state is still bound (`max age seconds 600`).

**A7. A slot the sentence never filled was read as ambiguity.** `source_root` on a repair
capability aborted the whole compilation instead of skipping that candidate, so "Apply the jq
filter …" never reached `json.query.jq`. Now: a bare unbound key is SKIPPED (walk continues), an
ambiguous slot (`<key>:2_…_named`) still keeps the request open, and a wrong-KIND value
(`type_mismatch:<key>`) is skipped too.

**A8. The F23 elimination pass could choose a file of the wrong kind.** With two files named and
two slots open, elimination handed a `.json` to `diff_path`. The pass may choose *which* stated
file fills a slot; it may never decide that a JSON document is a unified diff.

**A9. Output format was inferred by substring.** "hardcoded password" (a keyword of the security
gate) contains the letters of "word", so a JSON report was required to be `.docx` and the
sentence's own `.json` destination was refused. Marker matching is whole-word now.

**A10. The sentence's head verb did not count.** "Localize the fault in the python source tree …"
scored a tree-sitter **parse census** 25 against `python.fault.localize…` 24 — the parser matched
three nouns from the *medium*. A verb that identifies an act now adds weight; generic verbs
("generate", "create") do not, which is what keeps the QR decoder/generator counterexample intact.

**A11. Inflected names did not match.** "Generate unit test **scaffolding** …" could not match the
capability whose own name contains `scaffold`, so a parser took the request and reported success —
the hollow-PASS shape. Name tokens now match a morphological variant (≥5 chars, prefix), weighted
like a `provides` match.

**A12. The role rescue must stay behind an allowlist.** A broad rescue lets a slot fill from the
wrong evidence and re-breaks fail-closed semantics; `RESCUE_SLOTS` is explicit, with an
environment kill switch (`BRAIN_ROLE_RESCUE_OFF=1`) so the contribution is measurable.

*(A13–A22 are the same class, itemised in the commit history: quoted literals leaking into the
ranking, `*_tests` discovery scoped to refactoring requests, the joint-binder pool, whole-word
format inference, the type gate applied to joint assignments, the pinned binder admitting slots
by lexicon kind, and four more.)*

---

## B. Execution depth: reached, selected, and then the work does not happen

These are not reachability problems. The front door picks the right capability and the adapter
then has to actually do the job. Five were found and fixed in this unit:

**B1. A gate copied the anchor INTO the anchor.** Every diff gate compares an untouched anchor
against a patched *copy*, and the output artifact usually sits inside the anchor. Scratch beside
the output is therefore inside the copy, into the next copy … Measured: a perf-gate run against
the repository as anchor left **thirty nested copies** and died with `ENAMETOOLONG`. Scratch now
lives outside the anchor (`_diff_gate_anchor_v1.scratch_base`), deterministically.

**B2. The anchor was the repository, not the tree the diff applies to.** A unified diff names
`a/pkg/calc.py` relative to the tree it came from; anchoring at the repository root meant
`DIFF_DOES_NOT_APPLY` while the diff was perfect. The anchor is now the nearest directory — from
the diff's own directory up to the stated anchor — where `git apply --check` succeeds
(`_diff_gate_anchor_v1.resolve_anchor`).

**B3. Test paths and bench paths were written against the wrong root.** A stated
`…/pkg/test_calc.py` was handed to pytest running *inside the copied tree*, which collected
nothing: `BASE_WORLD_RED:no tests ran`. Same for the benchmark: `BENCH_FILE_MISSING` while the
file sat exactly where the sentence said. Both are now re-expressed relative to the anchor.

**B4. The word "patch" inside a filename became an instruction.** "Review the diff fix.patch"
carries the word *patch*, so the front door recorded a promise to CHANGE SOURCE, and threw away
the gate's own PASS with `PROMISED_SOURCE_CHANGE_NOT_APPLIED`. A verb inside a path or a quoted
value is not a verb about the task — the same law F25 applies to literals.

**B5. A capability that took a path was given the path and crashed.** `software.patch.synthesize.
cegis.z3.v1` consumed a manifest *document* while the registry binds a manifest *file*: every call
died with `AttributeError: 'str' object has no attribute 'get'`. It was reachable, selected, and
never once executed. It now loads the file (repo-confined) or accepts a dict.

**Still open, and honest:**

* **The type gate can only report `PASS_BASELINE_ONLY`** when mypy is absent — and mypy is not a
  declared dependency of the image. Same class: coverage needs `coverage`, security needs
  `bandit`, contract checks need `crosshair`, CEGIS needs `z3`. On this box all five are now
  installed by hand, which is exactly the kind of invisible prerequisite that makes a capability
  look broken. **The image has no pinned toolchain.**
* **A gate's expectation is "PASS"**, so a gate that honestly FAILs a bad diff is reported by the
  front door as `ACTION_EXPECTATION_FAILED`. A verdict is not a failure — the registry models a
  gate's *success* as `gate == PASS`, which means the machine can never report "I reviewed it and
  it is not safe" as a completed job.
* **Timing gates are physically flaky** by construction (B-row above).

---

## C. Missing verbs: 38 acts with no capability at all

This is the real frontier, and it is where "most advanced software engineer" is actually decided.
Grep across the 125 canonical verified capabilities found **no capability** for:

| area | missing acts |
|---|---|
| **version control** (11) | `git status`/`log`, `git diff`, `git commit`, `git branch`/`checkout`, `git revert`, `git bisect`, `git blame`, `git stash`, `git rebase`, `git cherry-pick`, merge-conflict resolution |
| **debugging** (2) | interactive debug (breakpoints, step, inspect), crash reproduction/minimisation |
| **quality measurement** (5) | coverage *measurement* (only a diff gate exists), memory/leak analysis, complexity metrics, duplication detection, dead-code detection |
| **testing** (3) | fuzzing, differential testing, test-flakiness detection |
| **verification** (1) | invariant inference |
| **dependencies & supply chain** (5) | dependency add/upgrade, vulnerability audit, secret scan (only inside a diff gate), license compliance, SBOM |
| **hygiene** (2) | lint/format as an act, type-check as an act (only a diff gate) |
| **build & release** (4) | build/package, schema migration, changelog/release notes, CI-config authoring |
| **runtime quality** (5) | async/concurrency correctness, exception/error-handling audit, SQL-injection audit, path-traversal audit, resource-leak audit |
| **robustness** (2) | retry/idempotency design, observability (logs/metrics/traces) |
| **refactoring** (1) | move/split/inline-* (rename and extract exist; that is the whole refactoring surface) |
| **docs** (1) | docstrings/API documentation |
| **architecture** (1) | API compatibility / semver / breaking-change analysis |
| **packaging** (1) | container/image build |

**Structural reasons that block the 19 "supercomposers"**: 313 of the 419 loaded entries declare
**zero inputs**. A zero-input capability either binds every sentence (a catch-all, excluded from
being the decision) or binds nothing. The most ambitious-sounding names in the registry
(`software.hardcore.swe.supercomposer.v1` and its siblings) can therefore never be selected by any
sentence. Only **106** of 419 are routable from a plain goal.

---

## What this means for "the most advanced software engineer"

1. **Reachability first, and it was 19%.** The machine had the tools; language could not get to
   them. That is now 100% on this probe. This was the cheapest, largest win available and it is
   done.
2. **Then execution depth.** Half of the remaining gap is capabilities that run and refuse, and
   the refuses are often *toolchain* (mypy/coverage/bandit/crosshair/z3 absent) rather than
   capability. A pinned, declared, verified toolchain in the image is worth more than five new
   adapters, because it turns "UNAVAILABLE" into a verdict.
3. **Then the 38 missing verbs, in this order of leverage for building software fast:**
   version control (11 acts — the machine cannot even `git status`), dependency/supply chain (5),
   coverage/memory/complexity measurement (5), refactoring beyond rename+extract (move, inline,
   split, change signature), and fuzzing/differential/flakiness (3). Everything else is behind
   those.
4. **Then the gate expectation model.** A reviewer that can only report PASS is not a reviewer.
   The registry must be able to record "verdict: FAIL, job: complete" as a success.

---

## How to reproduce every number

```bash
# the 22-task hardcore-SE probe (writes /tmp/se_reach.json)
python3 execution_guard/hardcore_se_reachability_v1.py --json /tmp/se_reach.json

# one task
python3 execution_guard/hardcore_se_reachability_v1.py --only rename_symbol

# registry composition: 419 loaded / 125 canonical verified / 106 routable / 313 zero-input
python3 - <<'EOF'
import sys; sys.path.insert(0,'.')
from canonical.runtime import live_integrated_brain_v1 as live, goal_front_compiler_v1 as front
reg = live.load_verified_registry()
print(len(reg), len(live.load_verified_registry(include_extended=False)),
      len(front.routable_registry(reg)),
      sum(1 for c,e in reg.items() if not front.input_keys(e)))
EOF
```

Fixture policy, stated because it is part of the measurement: a **review gate** is given a green
baseline and a small fully-covered diff (a gate seeded with a red suite measures its refusal, not
its gate); a **single-edit searcher** is given a one-bug world (its own non-claims say it cannot do
multi-edit); a **scaffolder** is given an annotated library (it refuses what it cannot derive).
Everything else runs against the shared seeded-bug world.
