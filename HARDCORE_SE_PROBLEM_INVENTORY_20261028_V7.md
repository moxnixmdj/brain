# All the problems

**Hardcore software engineering only.** Branch `arena/4ca3a720-brain`, 2026-10-28. Every number
below is measured on this branch by an instrument that is in the repository and re-runnable;
commands at the end. Nothing here is an opinion about code quality — each line is a defect in the
machine's ability to *do* software engineering, with the measurement that shows it.

The question is "what are all the problems?" — so this document is the complete list, ordered by
what each one costs the machine's ability to be an engineer, with the status of each.

---

## The scoreboard

| # | family | measured | status |
|---|---|---|---|
| 1 | **The machine had no hands on version control** | 11 acts, **0** implemented; `git blame/stash/rebase/bisect` in **0 files** | **10 of 11 fixed** (bisect + rebase remain) |
| 2 | **The analysers were never called** | lint/type/dead/complexity/security answered by an **AST walker with PASS** | **6 acts fixed** (ruff, mypy, bandit) |
| 3 | **The door lies: an absent act gets a PASS** | **10 of 43** absent-act requests still get a credible artifact + PASS | measured; 18 → 10 this unit |
| 4 | **The machine cannot refuse cleanly** | **19 of 43** honest refusals, 12 of which name the act | measured; improving |
| 5 | **A capability can kill its caller** | **16 of 16** exiting adapters killed the process | **fixed** (16/16 typed refusal) |
| 6 | **The registry is inflated** | **122 of 435** verified entries routable | quantified, unchanged |
| 7 | **The registry's words are not its acts** | 1 false keyword measured (`blame`); **no `acts` declaration exists** | open — the structural fix |
| 8 | **Refusals name nothing** | **0 of 23** named the act (V6) → **12 of 19** now | improving |
| 9 | **Capability is concentrated where the leverage isn't** | git **10** routable, refactor **3**, patch **3** vs audit/repair **21** | map below |
| 10 | **The instruments rot, silently** | 3 instruments measured wrong in 3 different ways in this unit alone | 3 fixed |
| 11 | **The toolchain isn't declared** | clean image **14/22**, with it **22/22** | **fixed** (declared + preflight) |
| 12 | **Single destructive acts have unbounded scope** | one "Format the python source" sentence rewrote **146 files** | **open, unguarded** |

---

## 1. Version control — the layer everything else assumes

Before this branch the machine could not inspect or move its own work. `grep "git blame"`,
`"git stash"`, `"git rebase"`, `"git bisect"` over the whole repository returned **0 files**, and
the only git code in the runtime was `_git_head()`, used for change detection.

Ten verbs now exist and are measured through the live door against real repositories
(`execution_guard/hardcore_se_git_surface_v1.py`):

| row | act | hit | pass | artifact | repository actually changed |
|---|---|---|---|---|---|
| status, log, diff, blame, branch_list, branch_create, commit, stash, checkout, revert | 10 | **10/10** | **10/10** | **10/10** | **10/10** |

And the half that matters more — a git surface that acts on a request it cannot honour throws away
an engineer's tree. Eight contracts are measured refusing, all with the repository **byte-identical
afterwards**:

| refusal | stated as | named |
|---|---|---|
| `NOT_A_REPOSITORY` | "git status of the repository R" where R is a plain directory | ✓ |
| `REPOSITORY_NOT_STATED` | "git status of the repository" with no repository stated | ✓ |
| `WORKING_TREE_DIRTY:1` | "check out the branch feature" on a dirty tree | ✓ |
| `REF_NOT_FOUND` | "check out the branch nosuchbranch" | ✓ |
| `NOTHING_TO_COMMIT` | "commit the changes" on a clean tree | ✓ |
| `BRANCH_ALREADY_EXISTS` | "create a branch called main" | ✓ |
| `REVERT_CONFLICT` | revert a commit whose lines a later commit rewrote | ✓ |
| `PATH_NOT_IN_REPOSITORY` | blame a file outside the repository | ✓ |

**Still missing: `git bisect`, `git rebase`, cherry-pick, merge-conflict resolution.** Bisect is
not hard, it is *unbound*: it needs a predicate, and the honest form is "bisect with the stated
test command until it fails", which the composer already knows how to carry (`argv` slots exist).

---

## 2. Static analysis — installed, declared nowhere, called by nothing

The gap was never an algorithm. `ruff 0.17.3`, `mypy 2.4.0`, `bandit 1.9.4` and `coverage` are in
this repository's own environment. Measured before this unit, through the live door:

```
"Lint the python source <R>/pkg and report it to <O>"        -> python.source.audit.ast  PASS
"Type check the python source <R>/pkg and report it to <O>"  -> python.source.audit.ast  PASS
"Find the dead code in the python source <R>/pkg ..."        -> python.source.audit.ast  PASS
```

An AST walker answering a lint request with a PASS is the worst shape a report takes: a clean lint
report and a lint that never ran are indistinguishable.

Six capabilities now exist through one adapter (`bound_capabilities/toolchain_v1.py`), each
measured executing:

| act | tool | measured on this repository |
|---|---|---|
| lint | ruff | 727 findings over `canonical/runtime/bound_capabilities` |
| format | ruff | applied; 0 files changed (already formatted) |
| type check | mypy | 0 errors (with `--explicit-package-bases`) |
| complexity | ruff C901 | threshold stated, per-function measurement in the artifact |
| dead code | ruff F401/F811/F841 | 32 unused imports/variables |
| security | bandit | 3 findings |

**Principles that are now enforced rather than hoped for:** an analyser that is not installed is
`TOOL_NOT_INSTALLED` — never an empty finding list; every tool is resolved from *this* interpreter's
directory first; every artifact's digest re-derives from its own bytes.

**Still missing:** duplication detection (needs a real clone detector, not `ruff`), memory/leak
profiling, coverage-of-a-tree as an *act*, invariant inference.

---

## 3. The door lies — 10 of 43

`execution_guard/hardcore_se_missing_verb_probe_v1.py`: 43 ordinary-English sentences, one per act,
through the live door. Progress this unit:

| | V6 baseline | after git surface | after analysers + R12 | **now** |
|---|---|---|---|---|
| acts answered by the capability that owns them | 0 | 7 | 12 | **12** |
| honest refusal | 23 | 18 | 14 | **19** |
| **SILENTLY_WRONG — PASS + credible artifact for a different act** | **18** | 14 | 15 | **10** |
| WRONG_TOOL — ran, wrong capability, failed | 2 | 3 | 2 | **2** |

The ten that still lie:

| act asked | what answers | why it wins |
|---|---|---|
| `duplication` | `python.toolchain.ruff_dead_code.v1` | shares "dead"/"code"; no clone detector exists |
| `differential_test` | `python.repository.acceptance.measure.v1` | shares "run"/"test" |
| `vulnerability_audit` | `python.source.audit.ast` | "audit" is generic (11 entries name it) |
| `license_check` | `python.toolchain.mypy_typecheck.v1` | "check" |
| `changelog` | `source.candidates.enumerate.stdlib` | "repository" |
| `async_audit`, `exception_audit` | `python.source.audit.ast` | "audit" + "source" |
| `retry_design` | `.../bandit_security` | "calls" |
| `change_signature` | `python.source.change_impact.testselect.v1` | "change" |
| `api_compatibility` | `python.toolchain.mypy_typecheck.v1` | "type" |

**The mechanism, named:** `F3_ARTIFACT_WRITERS_PREFERRED` prefers whatever can write the promised
file, and a generic capability that shares one *medium* word with the sentence beats nothing. The
output-vocabulary fix cut this from 15 to 10 by removing the words that name the artifact rather
than the act (`report`, `receipt`, `result`, `summary`, `findings`, `issue`).

**The structural fix is still open:** every capability must declare the **acts** it performs
(verb + object), checked at registration against the adapter, and a request is admitted only when
one capability declares both. That closes families 3, 7 and 8 *by construction* instead of by
keyword surgery.

---

## 4. The machine cannot refuse cleanly

An honest refusal is worth more than a hollow pass, but only if the caller can act on it. V6
measured **0 of 23** refusals naming the act they declined. Two mechanisms were dropping the
information: the route-admission rejection carried `rule` but no `reason`, and the composed-failure
path carried neither.

```
refusals that name the missing act:   0/23  (V6)   ->   12/19  (now)
```

The remaining seven refusals are honest but mute, all through the composition path
(`FAIL__RAW_GOAL_COMPILATION_GAP`, `FAIL_CLOSED__PROMISED_ARTIFACT_MISSING`).

---

## 5. A capability can kill its caller — fixed

19 bound adapters reported failure by ending the interpreter (`raise SystemExit(json...)`).
`SystemExit` is a `BaseException`, so `except Exception` in `_execute_locally` never saw it: no
verdict, no culprit, no retry.

| | verdict |
|---|---|
| before the guard | **16/16 PROCESS_KILLED** |
| after the guard | **16/16 TYPED_REFUSAL** — the adapter's own reason, delivered |

---

## 6. The registry is inflated — 122 of 435

| | count |
|---|---|
| verified entries | **435** |
| routable (declares at least one input, so a sentence can select it) | **122** |
| added this unit | +10 git, +6 analysers — **all 16 routable** |

The most ambitious names in the registry (`software.hardcore.swe.supercomposer.v1` and siblings)
are among the unreachable. An entry that declares no inputs can never be selected from a request,
so it is a claim rather than a capability.

---

## 7. The registry's words are not its acts

A keyword is a claim and nothing validates it against the adapter. Measured: `blame` was declared
by `python.source.change_impact.testselect.v1`, which does not blame. This is the same defect as
family 3 seen from the registry side, and it has the same fix: an `acts` block per entry, verified
against the adapter's own artifact fields at registration time.

---

## 8. Capability is concentrated where the leverage isn't

Verified / routable by area, measured on this branch:

| area | verified | routable |
|---|---|---|
| audit / analysers (`source.audit` + `toolchain`) | 7 | **7** |
| repair | 9 | 9 |
| review / diff gates | 6 | 6 |
| tests | 9 | 6 |
| **repo / git operations** | **10** | **10** |
| patch synthesis | 5 | 3 |
| refactoring | 4 | 3 |
| symbol index | 4 | 2 |
| **TOTAL** | **435** | **122** |

The machine is deepest where a human *reviewer* works and thinnest where a human *engineer* spends
the day: moving code (git, refactor, synthesize). The git column went from 2 to 10 in this unit and
is now the healthiest area in the registry — that is what the shape of the gap looks like when it
is closed.

---

## 9. Single destructive acts have unbounded scope — open

Measured accidentally and then verified: a single sentence, *"Format the python source
`canonical/runtime/bound_capabilities` and report it to `<out>`"*, rewrote **146 files**. The
artifact listed every changed file, so the report was honest — but nothing in the contract asked
the caller to confirm a 146-file rewrite, and nothing defaulted to check-only.

The same shape exists in `ruff check --fix`, `git checkout`, `git stash`, `revert` and any future
`--apply` capability. **Fix:** a `scope` declaration per mutating act (`files_touched` known before
the act) plus a stated confirmation policy — `check_only` by default for scope-wide formatters, and
a refusal (`SCOPE_EXCEEDS_THE_STATED_SCOPE`) when the act would touch more than the sentence named.

---

## 10. The instruments rot, silently

Four instruments were caught reporting the wrong thing in this unit — each failure mode is "reports
nothing wrong":

| instrument | what it said | what was true |
|---|---|---|
| `typed_capability_sweep_v1` | crashed on its first capability (fixture moved) | had not completed a run in weeks |
| `adapter_failure_law_probe_v1` (v1) | **16/16 fine** | 16/16 were dying |
| `hardcore_se_missing_verb_probe_v1` ownership check | "does not own the act" for every row | it compared the capability's vocabulary with the sentence's **first word** ("Show", "Commit") |
| same probe, naming check | "0 refusals name the act" | it looked for the sentence's first word, not the act's |

All four are fixed and re-runnable. The rule they teach is in the repository now: **an instrument
whose failure mode is "reports nothing" must be tested against the failure it is supposed to
detect.**

---

## 11. The toolchain is not declared — fixed

A verified capability is an adapter **plus the tool it calls**, and only the first half was
declared: `source.module` was prose and `declared_dependency_executables` was empty for all 419
then-current entries. Same code, same probe:

| interpreter | bind | select | pass |
|---|---|---|---|
| clean image | 22/22 | 19/22 | **14/22** |
| with the declared toolchain | 22/22 | 22/22 | **22/22** |

Fixed by `canonical/runtime/TOOLCHAIN_DECLARATION_V1.json` + `execution_guard/toolchain_preflight_v1.py`.

---

## 12. The defect catalogue — mechanisms found while closing families 1 and 2

These are the *micro*-problems: each one is why a correctly-ranked, fully bound capability failed to
execute, or executed and lied. All are fixed, all are in this branch, and each was found by
measurement rather than by reading.

| # | defect | what it looked like | fix |
|---|---|---|---|
| 1 | `system_tool` without `source.executable` | every git row died `BOUND_SYSTEM_TOOL_EXECUTABLE_INVALID` before its adapter ran | `executable: "git"` on all ten |
| 2 | template slot ≠ binder slot (`repo_path` vs `worktree_path`) | 11 slots reached the adapter empty → `REPOSITORY_NOT_STATED` | rename the template key |
| 3 | prose read as a command line | "Show the git diff … against HEAD" ran `/usr/bin/diff` and failed **after** the right capability had been selected and refused `NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND` | `statement_is_a_command_line`: an imperative puts its action first |
| 4 | pronoun payload ("write **it** to O") | the write rule demanded a text slot, so the capability that produces the report was refused `NO_SLOT_FOR_THE_STATED_PAYLOAD` | an anaphor is not stated text |
| 5 | destination bound as a source | the same sentence worked once and then refused `path:2_existing_files_named` forever, because its own output became an input | a stated destination is never a source (binder **and** composer) |
| 6 | tuning slots dropped stated text | "Revert the commit `<sha>`" reverted **HEAD** — a different commit, silently | `TEXTUAL_TUNING` + revision phrases (`HEAD~1`) |
| 7 | alias matching without a word boundary | the alias `ref` matched inside `refuse_revert_conflict` | `(?![A-Za-z0-9_])` |
| 8 | `_write` hashed a payload it had not written | recorded digest named bytes that never existed | `verify_artifact` re-derives from the file |
| 9 | `gate: PASS` with `committed: false` | the door reported PASS for a commit that never happened | `NOTHING_TO_COMMIT` is a refusal |
| 10 | refusal artifacts skipped when the refusal is about the repository | "git status of the repository" (none stated) → `FAIL_CLOSED__PROMISED_ARTIFACT_MISSING` with an **empty reason** | resolve the destination first, write every refusal |
| 11 | composed steps dropped the template's constants | `vcs.git.status.v1` dispatched with no `git_verb` → `GIT_VERB_NOT_SUPPORTED` | constants are part of the contract |
| 12 | directory vs file scope | `path` is a PATH_FILE slot, so "lint the python source `pkg/`" could never bind | `proposal_bindings: path_file_or_dir` |
| 13 | absolute paths lost their separator | `/home/u/x.json` read as `home/u/x.json` → reports written to a **mirror inside the repository** | keep the slash; both adapters read a path as stated |
| 14 | mypy on a package directory | "Source file found twice under different module names" surfaced as `TOOL_FAILED` | `--explicit-package-bases` |
| 15 | output artifacts are not future artifacts | a stated output that already exists cannot bind (correct), but the refusal is indistinguishable from a missing one | documented; needs a distinct code |
| 16 | an act with exactly one owner answered by another capability | registering an analyser turned honest refusals into hollow passes | `R13_STATED_ACT_IS_OWNED_BY_ANOTHER_CAPABILITY` |

---

## What is *not* a problem

- **Reachability on the 22 hardcore-SE tasks: 22/22 bind, 22/22 select, 22/22 pass**, zero
  `shell.command.run` fallbacks.
- **The 22 adapters themselves** execute against real repositories and are judged on the artifact.
- **Composition**: multi-step requests plan into a DAG and execute.
- **The front-compiler unit suite**: 32 passed / 12 failed **on this branch and the same 12 failed
  at the base commit** — compared name by name. Those 12 are pre-existing and are their own
  inventory item.

---

## The 31 acts that are still missing, by verdict

Honest refusal (19 — the machine knows it cannot): `git_bisect`, `git_rebase`, `merge_conflict`,
`interactive_debug`, `crash_repro`, `coverage_measure`, `memory_profile`, `complexity_metric`,
`fuzz`, `dependency_add`, `secret_scan`, `build_package`, `schema_migration`, `ci_config`,
`resource_leak`, `observability`, `move_function`, `inline_function`, `docstrings`.

Wrong tool (2 — a capability ran and it was not the act): `git_blame` (the probe's sentence states
no repository, only a file), `flake_detect`.

Silently answered (10 — the lie): `duplication`, `differential_test`, `vulnerability_audit`,
`license_check`, `changelog`, `async_audit`, `exception_audit`, `retry_design`, `change_signature`,
`api_compatibility`.

---

## Order of work

1. **An `acts` declaration per registry entry, checked against the adapter.** It closes families 3,
   7, 8 and 9 of the scoreboard by construction and makes a false keyword impossible to register.
   This is the highest-leverage change left, and it is a registration-time gate rather than a
   routing heuristic.
2. **Scope + confirmation for mutating acts** (family 9): a 146-file rewrite must be a decision, not
   a side effect.
3. **Finish version control**: `git bisect` (with a stated predicate command) and `git rebase`.
4. **The remaining measurement acts**: coverage-of-a-tree, memory/leak, duplication (a real clone
   detector — `jscpd`/`pylint -d R0801` or an AST n-gram matcher over the repository's own AST).
5. **Testing that finds defects**: fuzzing (hypothesis is already a dependency), differential
   testing, flakiness detection.
6. **Refactoring beyond rename/extract**: move, inline, change signature — the 3 routable entries are
   thin against 10 git acts.
7. **The 12 pre-existing front-compiler suite failures**, one at a time, with the same rule as
   everything above: measure, name the mechanism, fix the rule rather than the test.

---

## Where the solutions already are (searched, not assumed)

| need | already exists | reuse shape |
|---|---|---|
| version control | `git 2.39.5` on the box | one adapter, fixed argv shape, refusal contract — **done** |
| lint / format / types / complexity / dead code / security | ruff, mypy, bandit **in this venv** | `toolchain_v1` — **done** |
| coverage | `coverage.py` (installed) | `coverage run -m pytest` + `coverage json` |
| fuzzing / property tests | `hypothesis` (already a dependency) | generate + minimise, report the counterexample |
| duplication | `pylint -d R0801`, `jscpd`, or AST n-grams | a threshold + a report, no model |
| mutation testing | `mutmut` / `cosmic-ray` | the strongest repair oracle there is |
| move / inline / signature change | `rope`, `libcst`, `jedi` | refactorings with a real symbol table |
| dependency / supply chain | `pip-audit`, `bandit`, `licensecheck` | one adapter per act |
| bisect | `git bisect run <cmd>` | the composer already carries `argv` slots |

No model participates in any of it. Everything above is deterministic, local, and already installed
or one `pip install` away.

---

## Reproduce every number

```bash
python3 execution_guard/hardcore_se_git_surface_v1.py                 # 10/10 hit-pass-artifact-effect
python3 execution_guard/hardcore_se_git_surface_v1.py --refusals      # 8/8 refused, named, untouched
python3 execution_guard/hardcore_se_git_surface_v1.py --reuse         # the same sentences again, same world
python3 execution_guard/hardcore_se_reachability_v1.py                # 22/22 bind, select, pass
python3 execution_guard/hardcore_se_missing_verb_probe_v1.py          # 12 owned / 19 refused / 10 hollow / 2 wrong
python3 execution_guard/adapter_failure_law_probe_v1.py               # 16/16 typed refusal
python3 execution_guard/toolchain_preflight_v1.py                     # FAIL_CLOSED on a clean image
```

Earlier tiers: `HARDCORE_SE_PROBLEM_INVENTORY_20261027_V1.md` … `_20261028_V6.md`.
