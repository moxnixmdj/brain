# All the problems — the complete inventory, measured

**Branch `arena/4ca3a720-brain`, 2026-10-28.** Every number below came from running the machine. Instruments
are in the repository and re-runnable; the commands are at the bottom.

This is the answer to *"what are all the problems?"* for hardcore software engineering. There are
**seven families**, and they are not equally important: the first one silently redefines every other
number in this document, so it is first.

---

## The seven families

| # | problem | size | what it costs | status |
|---|---|---|---|---|
| **1** | **The software isn't in the repository** — the toolchain is undeclared, so a clean checkout silently loses capabilities | 8 of 8 declared distributions absent on a clean image → **22/22 pass becomes 14/22** | the machine claims capability it cannot execute, and reports a missing tool as a broken adapter | **fixed this unit** (declaration + preflight + bootstrap) |
| **2** | **The door lies** — a capability that does not perform the requested act answers, writes a credible artifact, and is credited PASS | **18 of 43** absent-act sentences | worst failure class: the caller builds on a wrong artifact | measured, mechanism named, fix ordered (tier D) |
| **3** | **38 missing verbs** — no capability exists at all for the act | 38 acts across 13 areas | the actual frontier of "most advanced software engineer" | inventoried, not built (tier C) |
| **4** | **The registry is inflated** — 313 of 419 entries declare zero inputs and can never be selected | 106 of 419 routable | 75% of the inventory is unreachable decoration; the ambitious "supercomposer" names are ornamental | structural, quantified |
| **5** | **False keywords** — an entry claims an act it does not perform | at least 1 measured (`blame` on `python.source.change_impact.testselect.v1`) | turns a missing capability into a wrong answer | measured, fix = declaration |
| **6** | **Refusals don't name the act** — the refusal never says which verb is missing | **0 of 23** refusals | the caller cannot tell "build this next" from "this is broken" | measured |
| **7** | **A write escaped its destination** — an absolute output path was also mirrored inside the repo root | intermittent, 1 observed run, 0 on the clean re-run | the same artifact written twice in a place nobody asked for | filed open; probe now reports it (`escaped_writes`) |

---

## 1. The software isn't in the repository (P0, new, fixed)

A verified capability is an **adapter plus the tool the adapter calls**. This repository declared only
the first half. In the live registry, dependencies are stored as human prose:

```
python.review.diff_type_gate.v1   source.module = "mypy"                      type = pypi
python.refactor.rename_symbol.v1  source.module = "python stdlib ast"          type = runtime
python.review.diff_mutation_gate  source.module = "python stdlib ast/pytest + git"
```

and `declared_dependency_executables` is **empty for all 419 verified capabilities**. Nothing could
install the toolchain, and nothing could distinguish *absent* from *broken*.

**The measurement.** Same commit, same code, same 22-task probe, two interpreters:

| interpreter | bind | select | pass |
|---|---|---|---|
| clean `python3` (no venv) | 22/22 | 19/22 | **14/22** |
| with the declared toolchain installed | 22/22 | **22/22** | **22/22** |

The eight capabilities that vanish: `rename_symbol, rename_param, repo_diff_apply, review_coverage,
review_security, review_type, contract_check, mutation_gate` — and every one of them fails as
`CAPABILITY_EXITED_PROCESS` or `FAIL__LIVE_CONTROLLER_EXECUTION`, i.e. it reports itself as **broken**
when it is merely **not installed**.

**Attribution by measurement, not by reading source.** Each distribution was blocked with an import
hook and the probe re-run, so the dependency list is *observed*:

| distribution | pinned | blocks (task fails without it) |
|---|---|---|
| **pytest** | 9.2.0 | `rename_symbol, rename_param, repo_diff_apply, review_coverage` |
| mypy | 2.4.0 | `review_type` |
| coverage | 7.17.0 | `review_coverage` |
| bandit | 1.9.4 | `review_security` |
| crosshair-tool | 0.0.112 | `contract_check` |
| z3-solver | 5.3.2.0 | `contract_check` |
| ruff | 0.17.3 | nothing yet — declared for the lint/format acts that do not exist |
| tree-sitter | 0.26.0 | nothing on this surface — `code.multilanguage.parse.tree_sitter.v1` needs it |

`pytest` has the highest blast radius of any dependency here, and it is not a linter: **it is the
oracle**. The full test gate, the coverage gate, and both refactor capabilities that re-run the suite
after editing all disappear without it — meaning "repaired" becomes unmeasurable. A machine that
cannot run a test suite cannot know whether it fixed anything.

**What shipped:** `canonical/runtime/TOOLCHAIN_DECLARATION_V1.json` (machine-checkable, measured),
`execution_guard/toolchain_preflight_v1.py` (`--check` default, `--bootstrap`, `--attribute`), and a
strict pin policy — a drifted version fails the check, because drift is exactly what turned 22/22 into
14/22 without anyone editing a line.

```
$ python3 execution_guard/toolchain_preflight_v1.py --python .venv/bin/python
  OK   pytest         9.2.0      needs 9.2.0     blocks rename_symbol, rename_param, repo_diff_apply, review_coverage
  ...
toolchain-preflight: PASS : 8 of 8 declared distributions present

$ python3 execution_guard/toolchain_preflight_v1.py        # clean interpreter
toolchain-preflight: FAIL_CLOSED : 0 of 8 declared distributions present
capabilities this interpreter cannot run: 7 of 22 measured hardcore-SE tasks
```

---

## 2. The door lies (18 of 43)

The 38 missing verbs were already inventoried. What was missing is what the door *does* when one is
asked for: `execution_guard/hardcore_se_missing_verb_probe_v1.py`, 43 ordinary-English sentences
against a real two-commit repository.

| verdict | count |
|---|---|
| **SILENTLY_WRONG** — ran, wrote a credible artifact, door said PASS | **18** |
| HONEST_REFUSAL | 23 |
| WRONG_TOOL — ran, wrong capability, failed | 2 |
| answered by a capability that does not own the act | 36 / 43 |

**Mechanism:** `F3_ARTIFACT_WRITERS_PREFERRED` prefers whatever can write the promised file. When no
capability performs the act, a generic writer sharing one *medium* word (`python`, `source`) answers,
keeps the artifact promise, and the act never happens. A false keyword does the same job: `blame` is
declared by a test-selection capability that does not blame.

Three fixes were built and measured; the act-admission rule (winner must name the sentence's head
verb) takes hollow passes **18 → 6** with reachability at 22/22 but takes the goal-compiler suites
from **17 failing / 149 passing** to **27 / 139** — rejected rather than tuned. The correct fix is a
**declared act vocabulary per capability**, checked at registration; details and the residual 6 are in
`HARDCORE_SE_PROBLEM_INVENTORY_20261028_V4.md`.

---

## 3. The 38 missing verbs (the real frontier)

| area | missing acts |
|---|---|
| **version control** (11) | status, log, diff, commit, branch/checkout, revert, bisect, blame, stash, rebase, cherry-pick; merge-conflict resolution |
| **debugging** (2) | interactive debug (breakpoints, step, inspect); crash reproduction + minimisation |
| **quality measurement** (5) | coverage *measurement*, memory/leak analysis, cyclomatic complexity, duplication, dead code |
| **testing** (3) | fuzzing, differential testing, flakiness detection |
| **verification** (1) | invariant inference |
| **dependencies & supply chain** (5) | add/upgrade dependency, vulnerability audit, secret scan, license compliance, SBOM |
| **hygiene** (2) | lint and format *as acts* (only diff gates exist) |
| **build & release** (4) | build/package, schema migration, changelog, CI-config authoring |
| **runtime quality** (5) | async/concurrency, exception-handling audit, SQL injection, path traversal, resource leak |
| **robustness** (2) | retry/idempotency design, observability |
| **refactoring** (1) | move / split / inline (rename and extract are the whole surface today) |
| **docs** (1) | docstrings / API docs |
| **architecture** (1) | API compatibility / semver / breaking changes |
| **packaging** (1) | container image |

Note what this table means for "the most advanced software engineer": the machine cannot even read
its own working tree with `git status`, cannot reproduce a crash, cannot measure coverage on a tree,
and has exactly two refactorings. The capabilities it *does* have are strong; the job it is being
asked to do is much wider than the job it can do.

---

## 4. The registry is inflated

419 loaded `VERIFIED_BOUND_CAPABILITY` = 125 canonical + 293 `*.auto.v1`. **313 declare zero inputs.**
A zero-input capability either binds every sentence (a catch-all, never allowed to decide) or binds
nothing, so it can never be selected from a request. **106 of 419 are routable.** The most
ambitious-sounding names in the registry — `software.hardcore.swe.supercomposer.v1` and its siblings —
are among the unreachable. A registry that counts them as capability overstates the machine by 4×.

---

## 5–7. Smaller but real

- **False keywords** (measured ≥ 1): a keyword is a claim, and nothing validates it against the
  adapter. `blame` on a test-selection capability turns a missing verb into a wrong answer.
- **Refusals name nothing** (0 of 23): the honest half of the machine is mute. The refusal object
  already carries a `detail`; it never names the act the brain lacks.
- **A write escaped its destination** (1 observed, 0 on the clean re-run): a stated absolute output
  path was also mirrored inside the repository root — the same file written twice. The probe now
  reports `escaped_writes` instead of hiding it; the path-joining defect is open.

---

## What is *not* a problem (so effort does not go there)

- **Language reachability on the 22 hardcore-SE tasks: 22/22 bind, 22/22 select, 22/22 pass**, with
  zero `shell.command.run` fallbacks and zero hollow passes — once the toolchain is installed.
- **The adapters themselves**, for those 22: they execute against real repositories and are judged
  on the artifact they write.
- **Composition**: multi-step requests plan into a DAG and execute (verified to 10 steps).

---

## The order of work, and why that order

1. **Keep the software present.** The preflight must run before any capability claim — it is the only
   check that separates "absent" from "broken". *(shipped)*
2. **Make the registry say what it performs and what it needs, machine-checkably** — an `acts`
   vocabulary (verb + object) and a resolved dependency block per entry. This closes families 2, 5,
   and 6 at once, by construction, and makes both the hollow pass and the false keyword impossible.
3. **Version control (11 acts).** The machine cannot inspect or move its own work. Everything else in
   software engineering assumes this layer.
4. **Supply chain (5) + measurement (5).** Vulnerability audit, secret scan, license, SBOM;
   then coverage, memory, complexity, duplication, dead code.
5. **Refactoring beyond rename/extract** — move, inline, split, change signature.
6. **Fuzzing, differential testing, flakiness** — these buy *finding* defects, which is the only way
   quality improves without a human in the loop.
7. **A gate expectation model.** A reviewer that can only report PASS is not a reviewer.

---

## Reproduce every number

```bash
# 1. toolchain: the P0, in one command each
python3 execution_guard/toolchain_preflight_v1.py                      # clean image -> FAIL_CLOSED
python3 execution_guard/toolchain_preflight_v1.py --bootstrap          # make .venv match the pins
python3 execution_guard/toolchain_preflight_v1.py --python .venv/bin/python
python3 execution_guard/toolchain_preflight_v1.py --attribute          # re-derive the blocks matrix

# 2. the 22-task surface (with the toolchain installed)
python3 execution_guard/hardcore_se_reachability_v1.py --json /tmp/se_reach.json

# 3. the 43 absent acts and what the door does with them
python3 execution_guard/hardcore_se_missing_verb_probe_v1.py --json /tmp/missing.json

# 4. registry composition: 419 loaded / 125 canonical / 106 routable / 313 zero-input
python3 - <<'EOF'
import sys; sys.path.insert(0,'.')
from canonical.runtime import live_integrated_brain_v1 as live, goal_front_compiler_v1 as front
reg = live.load_verified_registry()
print(len(reg), len(front.routable_registry(reg)),
      sum(1 for c,e in reg.items() if not front.input_keys(e)))
EOF
```

Tiers A–C: `HARDCORE_SE_PROBLEM_INVENTORY_20261028_V3.md`. Tier D (the door lies): `…_V4.md`.
