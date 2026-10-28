# HARDCORE SOFTWARE-ENGINEERING PROBLEM INVENTORY — V8

Version 8. Supersedes V7. Everything here is **measured on this tree**, not asserted. Every
number has the command that produced it.

---

## 1. The change in this unit

V7 recorded eleven version-control acts and four quality acts as *missing or hollow*. This unit
did not add vocabulary — it closed the gap that was actually load-bearing: **a sentence whose own
verb names a registered act was being answered by a different act, silently, with a PASS.**

Four defects were found and fixed, each by measurement:

| # | Defect | Proof | Fix |
|---|--------|-------|-----|
| 1 | `git rebase` / `git revert`: a stated revision in words was dropped, the adapter defaulted `ref` to HEAD, and a **different commit** was acted on | `Revert the commit <sha> ...` reverted `HEAD` | `goal_compiler`: tuning slots declared `TEXTUAL_TUNING` now bind stated text (`HEAD~1`, `main`, a sha), not only numbers |
| 2 | `HEAD~2` was silently truncated to `HEAD` | `_parse_typed_value('ref',' HEAD~2 …') -> 'HEAD'` | revision slots read the whole token (`~`, `^`, `@` included) |
| 3 | A **quoted command** bound no `argv` at all | `GOAL_INPUT_BINDING_REQUIRED:argv:not_stated`; the request was then answered by a changelog builder | `goal_compiler._stated_command_argv` + the same rule in `goal_front_compiler.bind_typed_key` |
| 4 | A predicate-less `git bisect` was answered by `source.candidates.enumerate.stdlib` (400 files enumerated) and reported `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED` | measured through `adm.solve` | `goal_front_compiler.stated_act_unbound` (F32): when the sentence's head verb names an act that OUTRANKS the winner and **no** capability naming that act can bind, the request is **refused by name** instead of served by a neighbour |

Two path-binding defects were also closed, both found by the same door:

- `extract_paths` read an **absolute directory** as a relative one and appended it at the END of
  the sentence, so `output_path` bound the directory it was asked to measure
  (`IsADirectoryError`, reported as `PROMISED_ARTIFACT_MISSING`). Directories now keep their
  separator and their place in the sentence.
- a stated content destination that is an existing **directory** is never bound to a file slot.

And one honesty defect in the git adapter: `WORKING_TREE_DIRTY` fired on untracked files, so a
`__pycache__` left by a test run made every later `checkout`/`revert`/`rebase` refuse. Rewriting
verbs now look at tracked changes only; `stash` still moves untracked work.

---

## 2. Measured state

### 2.1 The git surface — twelve acts, ordinary English, real repository

```
python3 execution_guard/hardcore_se_git_surface_v1.py
selected 12/12  pass 12/12  artifact 12/12  repository actually changed 12/12
```

Rows: status, log, diff, blame, branch_list, branch_create, checkout, commit, stash, revert,
**bisect**, **rebase**. Each row checks the capability selected, the door's verdict, the artifact's
declared fields, and the repository's own state afterwards (`head_moved`, `tree_is_clean`,
`head_is_on_the_feature_branch`, `bisect_names_the_commit_that_broke_the_test`,
`branch_replayed_onto_main`, …).

`bisect` is graded against a fixture whose predicate really flips: the test passes at commit 1 and
2, fails at 3, and the check requires `first_bad_sha == HEAD` **and** the subject to name the
breaking commit. `rebase` is graded by `main` becoming an ancestor of the replayed branch.

### 2.2 The refusals — ten sentences the verbs must refuse

```
python3 execution_guard/hardcore_se_git_surface_v1.py --refusals
refused and named 10/10   (untouched 10/10)
```

| sentence | named refusal |
|---|---|
| status of a directory that is not a repository | `NOT_A_REPOSITORY` |
| status with no repository stated | `REPOSITORY_NOT_STATED` |
| checkout on a dirty tree | `WORKING_TREE_DIRTY` |
| checkout of a branch that does not exist | `REF_NOT_FOUND` |
| commit on a clean tree | `NOTHING_TO_COMMIT` |
| create a branch that exists | `BRANCH_ALREADY_EXISTS` |
| revert of a commit a later commit rewrote | `REVERT_CONFLICT` |
| blame of a file outside the repository | `PATH_NOT_IN_REPOSITORY` |
| **bisect with no predicate** | `argv:not_stated` (F32, the act is named and refused) |
| **rebase onto a revision that is not there** | `REF_NOT_FOUND` |

Untouched 10/10 means the five mutating verbs left HEAD, branch, index and worktree exactly as
found.

### 2.3 The 43-act missing-verb probe

```
python3 execution_guard/hardcore_se_missing_verb_probe_v1.py
{"ANSWERED_BY_OWNING_CAPABILITY": 15, "HONEST_REFUSAL": 17, "SILENTLY_WRONG": 7, "WRONG_TOOL": 4}
```

| revision | owned | honest | hollow | wrong |
|---|---|---|---|---|
| V6 baseline | 0 | 23 | 18 | 2 |
| + analysers | 7 | 10 | 19 | 3 |
| + R13 (act vocabulary) | 12 | 14 | 15 | 2 |
| + output-vocabulary stopwords | 12 | 19 | 10 | 2 |
| V7 (+8 capabilities) | 16 | 15 | 8 | 4 |
| **V8 (this unit)** | **15** | **17** | **7** | **4** |

The unit moved two hollow passes to honest refusals and one hollow pass to a named act. The
handful of "owned" that shifted did so because a sentence that previously bound loosely is now
refused by name — the direction the door is supposed to move.

### 2.4 The rest of the surface (unchanged, re-measured)

```
python3 execution_guard/hardcore_se_reachability_v1.py      22/22 bindable, 22/22 selected, 22/22 pass
python3 execution_guard/adapter_failure_law_probe_v1.py     16 adapters that could end the process -> 16 TYPED_REFUSAL
```

### 2.5 Regression baseline

The branch itself is red in places before this unit. Compared against `bd3726b`, over the 16
test files that exercise the front compiler, the composer and the door:

```
17 failed, 138 passed        (bd3726b)
17 failed, 138 passed        (this tree, identical node ids)
```

No new failure, no silenced one.

---

## 3. What is still open (measured, ranked)

1. **Seven hollow passes remain** in the 43-act probe: `flake_detect`, `vulnerability_audit`,
   `secret_scan`, `license_check`, `ci_config`, `retry_design`, `change_signature`. Each has an
   analyser available (`ruff flake8-bugbear`, `bandit`, `pip-audit`, `ruff ASYNC`, CI schema
   validators) — the same reuse the analyser unit used.
2. **Four wrong-tool answers**: `complexity_metric`, `dependency_add`, `schema_migration`,
   `build_package` are answered by capabilities that do not own the act. F32 now refuses the
   displacement case; these are cases where the winner is not displaced but the act is simply
   absent.
3. **`git bisect` still needs its predicate stated as a command.** That is deliberate: an invented
   predicate names a commit unrelated to the bug. A natural extension is to accept "using the test
   <path>" and derive the runner, which the composer already does for `test_argv`.
4. **The 17 pre-existing failures** in the front-compiler suite on this branch (identical at
   `bd3726b`) are untouched by this unit and remain the largest single red area.
5. `git rebase` refuses a dirty tree rather than stashing it. Correct by default, but the
   `autostash` behaviour of `git rebase --autostash` is the engineer's expectation, and the
   adapter does not offer it yet.

---

## 4. Reproduce

```bash
.venv/bin/python execution_guard/hardcore_se_git_surface_v1.py
.venv/bin/python execution_guard/hardcore_se_git_surface_v1.py --refusals
.venv/bin/python execution_guard/hardcore_se_missing_verb_probe_v1.py
.venv/bin/python execution_guard/hardcore_se_reachability_v1.py
.venv/bin/python execution_guard/adapter_failure_law_probe_v1.py
```

Every harness writes `--json OUT` and exits 0 whatever it found: a probe that fails the build when
it finds a defect teaches people to stop running it.
