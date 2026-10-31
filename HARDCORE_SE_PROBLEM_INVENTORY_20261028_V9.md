# HARDCORE SOFTWARE-ENGINEERING PROBLEM INVENTORY — V9

Version 9. Supersedes V8. Everything here is **measured on this tree**, not asserted. Every number
has the command that produced it.

---

## 1. The change in this unit

V8 recorded seven hollow passes and could not say why they were hollow. This unit answered that
question and closed six of them, and along the way it separated two things that had been counted as
one: **defects in the machine** from **defects in the world the machine was measured in**.

The single sentence that produced the whole unit:

> `Find the flaky tests in the repository R` → `python.quality.changelog.v1` → `PASS`

A changelog builder reported success for a flake hunt. Nothing was broken in the changelog
builder. The evidence that admitted it was `{report, repository}` — the word that names the
artifact and the word that names the medium — and the two words that name the ACT (`flaky`,
`tests`) were ordinary English the registry had never heard. **Bindability is not relevance:** a
capability whose declared inputs fit the sentence proves where the values go, never that it
performs what was asked.

### 1.1 Defects fixed in the machine

| # | Defect | Proof before | Fix |
|---|--------|--------------|-----|
| 1 | A word in a capability's **id** earned the head-verb bonus even when it was a request verb (`scan`, `check`, `measure`, …) | `Scan the repository R for leaked secrets` gave `python.quality.license_scan.v1` the bonus, then R13 refused the security analyser as "another capability's act" | `_NON_ACT_TOKENS` and `_REQUEST_VERBS` cover the request-verb class in both layers |
| 2 | A **medium** word counted as distinctive evidence (`repository`, `repo`, `directory`, `folder`) | `Find the flaky tests in the repository R` admitted the changelog builder on `{report, repository}` | those four words are in `GENERIC_MATCH_TOKENS`; measured: **0 of 149** capabilities lose their last distinctive token |
| 3 | The head-verb bonus was paid to a capability that matched **the verb and nothing else** | `Audit the dependencies in R for known vulnerabilities` → `python.source.audit.ast` 18 (`{audit}` + bonus) beat `bandit_security` 17 (`{audit, known, vulnerabilities}`) and PASSed a dependency audit with a source-structure report | the bonus requires at least one matched argument word that is not the verb and not generic |
| 4 | ...but a verb that names **exactly one** capability is the capability, and losing the bonus broke `git bisect` | `Bisect the repository R from the ref HEAD~2 …` tied `shell.command.run` 11–11 and lost on alphabetical order; git surface fell **12/12 → 11/12** | the bonus also applies when the verb appears in exactly one capability id (`_shared_identity_verbs`, read from the pinned registry). `audit` lives in 5 ids → needs its object; `bisect` lives in 1 → stands alone |
| 5 | A verb phrase the registry spells as one word was read as its first word | `Type check the python source` gave the bonus to `python.review.diff_type_gate.v1` (`type` is a segment of its name) and the type checker lost the route | `_head_verb_compound`: `type`+`check` joins to `typecheck` **only because a capability already carries that token**, and the compound is then a token of the sentence |
| 6 | Typed admission — "the sentence states exactly this capability's declared inputs" — was allowed to admit on **one incidental keyword** | `Make the network calls in X retry safely` bound `python.source.symbols.index.ast` on `calls` (score 4) and PASSed with a symbol index | a bound contract admits only when the sentence says ≥2 things the capability is about, or the one thing it says is the ACT (its id) or the EFFECT (its provides); a sentence that overlaps **not at all** keeps the contract route |
| 7 | R14 was gated on "generic evidence", so it could not see an unheard **object** | `Find the flaky tests …` → coverage analyser measured coverage, PASSed, and every word of the answer was true about a different question | R14 now also fires when the sentence opens with a request verb and the **first thing that verb is asked about** is a word no capability has ever heard |
| 8 | A filesystem path is a value, not a word about the act | R14 reported the unheard word `home` (from `/home/user/…`) and `main` (a ref) | absolute paths, drive paths, extension-bearing tokens, determiners (`previous`, `last`, …) and interrogatives (`whether`, `which`, …) are not act words |
| 9 | A repository anchor bound to **the path's parent directory** | `Blame the lines of <repo>/pkg/calc.py` bound `worktree_path=<repo>/pkg`; git ran there and refused `fatal: no such path` | `goal_compiler._enclosing_worktree`: a repo anchor is the nearest ancestor that carries `.git` — a fact on the filesystem — and the same rule is used by the pinned binder and the composer |

### 1.2 Defects in the world — three "capability failures" that were fixture failures

The probe reported `OWNED_BUT_FAILED` for `git_blame`, `git_rebase`, `coverage_measure`. All three
were the fixture talking:

| row | error | what it actually was |
|---|---|---|
| `git_rebase` | `REF_NOT_FOUND:main` | `git init` with no `-b` made a tree with **no `main`**. The world could not support the act. |
| `coverage_measure` | `NO_TESTS_FOUND` | the fixture had no test module, and it also rewound HEAD under later rows: `checkout the previous commit` left the tree at a commit whose `calc.py` had no `sub`, so `coverage` reported `TESTS_COULD_NOT_RUN: ImportError` |
| `git_checkout` / `git_revert` / `git_rebase` | `WORKING_TREE_DIRTY` | **one shared world**: the `git_stash` row's dirty tree was handed to acts whose sentence never promised uncommitted work |
| `git_blame` | `fatal: no such path` | defect 9 above (machine, not fixture) |

The probe now gives **each row its own world**, with a `main` branch, a branch to replay, a real
test module, and the dirty tree only where the sentence implies one. A probe that measures the
fixture teaches nothing about the machine.

---

## 2. Measured state

### 2.1 The 43-act missing-verb probe

```
python3 execution_guard/hardcore_se_missing_verb_probe_v1.py
{"ANSWERED_BY_OWNING_CAPABILITY": 23, "HONEST_REFUSAL": 18,
 "SILENTLY_WRONG": 1, "WRONG_TOOL": 1}
```

| revision | owned | honest | hollow | wrong | owned-but-failed |
|---|---|---|---|---|---|
| V6 baseline | 0 | 23 | 18 | 2 | — |
| + analysers | 7 | 10 | 19 | 3 | — |
| + R13 (act vocabulary) | 12 | 14 | 15 | 2 | — |
| + output-vocabulary stopwords | 12 | 19 | 10 | 2 | — |
| V7 (+8 capabilities) | 16 | 15 | 8 | 4 | — |
| V8 | 15 | 17 | 7 | 4 | — |
| **V9 (this unit)** | **23** | **18** | **1** | **1** | **0** |

The 23 owned rows: all ten git acts except a predicate-less `bisect`, plus `coverage_measure`,
`complexity_metric`, `duplication`, `dead_code`, `vulnerability_audit`, `secret_scan`,
`license_check`, `lint`, `format`, `type_check`, `changelog`, `async_audit`, `exception_audit`.

**Hollow passes went 7 → 1.** The one left is `change_signature`: `Change the signature of the
function add … to take a tuple` is answered by `python.source.change_impact.testselect.v1`, which
reads `change` as the noun in its own name and selects tests instead of changing a signature. The
act is genuinely absent (no `refactor.change_signature` capability), and the head-verb word is
shared with a real capability's name, so neither R13 nor R14 can honestly refuse it. That is a
**missing capability**, not a routing defect.

The 18 refusals each name the act this brain does not have: `git_bisect` (no predicate stated),
`merge_conflict`, `interactive_debug`, `crash_repro`, `memory_profile`, `fuzz`, `flake_detect`,
`dependency_add`, `build_package`, `schema_migration`, `ci_config`, `resource_leak`,
`retry_design`, `observability`, `move_function`, `inline_function`, `docstrings`,
`api_compatibility`.

### 2.2 The git surface — twelve acts, unchanged and re-measured

```
python3 execution_guard/hardcore_se_git_surface_v1.py
selected 12/12  pass 12/12  artifact 12/12  repository actually changed 12/12
python3 execution_guard/hardcore_se_git_surface_v1.py --refusals
refused and named 10/10   (untouched 10/10)
```

This suite is the reason defects 4 and 5 were caught: the ranker change that fixed
`vulnerability_audit` silently broke `bisect`, and the compound rule that fixed `type_check` had to
leave `lint` and `format` (35 and 35, both with arguments) alone. Both regressions were caught by
re-running this probe, not by reasoning about the change.

### 2.3 The rest of the surface

```
python3 execution_guard/hardcore_se_reachability_v1.py    bindable 22/22  selected 22/22  pass 22/22
python3 execution_guard/adapter_failure_law_probe_v1.py   16 adapters that could end the process -> 16 TYPED_REFUSAL
```

### 2.4 Regression baseline

Compared against `fec9e26` (the parent of this unit), same node ids, run twice:

```
canonical/tests/test_goal_front_compiler_v1.py    14 failed, 30 passed   (parent AND this tree)
canonical/tests/test_goal_compiler_world_binding_v1.py  5 failed, 45 passed  (parent AND this tree)
```

The only new failure introduced during this unit —
`test_f23_two_same_type_inputs_bind_by_the_roles_the_sentence_states`, broken by requiring
act-or-effect evidence — was fixed inside the same unit by letting a **zero-overlap** sentence keep
the contract route, which is the distinction the rule was always about.

---

## 3. What is still open (measured, ranked)

1. **18 acts are honestly missing.** Ranked by how often they appear in real requests and how
   cheap the existing analyser is: `flake_detect` (`pytest-randomly` / rerun evidence, not a
   linter), `api_compatibility` (`griffe`/`pyright` symbol diff), `retry_design` and
   `observability` (pattern + AST rewrite over `requests`/`urllib` calls),
   `move_function`/`inline_function`/`change_signature` (`rope` has all three; the repo already
   binds `rope` for rename), `docstrings` (AST + template), `memory_profile`
   (`tracemalloc`/`memray`), `fuzz` (`atheris`/`hypothesis`), `dependency_add` (`pip`/`uv`),
   `build_package` (`python -m build`), `schema_migration` (`alembic`), `ci_config`
   (schema validation), `resource_leak` (`ruff` `SIM115`/`PLR`), `merge_conflict` (git's own
   conflict markers), `crash_repro` (`--deltablue` style delta debugging on argv), `interactive_debug`
   (`pdb` driven by a breakpoint plan).
2. **One hollow pass remains** (`change_signature`) and it is a missing capability, not a routing
   defect — see §2.1.
3. **One wrong-tool answer remains** (`differential_test` → `code.impact.tree_sitter.testselect.v1`
   with `INDEX_UNREADABLE`): the act is absent and the nearest capability cannot even index the
   tree. Both halves are real.
4. **`git bisect` still needs its predicate stated as a command.** Deliberate: an invented
   predicate names a commit unrelated to the bug. The composer already derives `test_argv` for
   other families, so "using the test <path>" is the natural extension.
5. **19 pre-existing test failures** on this branch (identical node ids at `fec9e26`) remain the
   largest single red area, untouched by this unit.

---

## 4. Reproduce

```bash
.venv/bin/python execution_guard/hardcore_se_missing_verb_probe_v1.py --json /tmp/mv.json
.venv/bin/python execution_guard/hardcore_se_git_surface_v1.py
.venv/bin/python execution_guard/hardcore_se_git_surface_v1.py --refusals
.venv/bin/python execution_guard/hardcore_se_reachability_v1.py
.venv/bin/python execution_guard/adapter_failure_law_probe_v1.py
```

Every harness writes `--json OUT` and exits 0 whatever it found: a probe that fails the build when
it finds a defect teaches people to stop running it.
