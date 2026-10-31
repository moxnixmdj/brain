# HARDCORE SOFTWARE-ENGINEERING PROBLEM INVENTORY — V11

Version 11. Supersedes V10. Measured on this tree, not asserted.

---

## 1. The change in this unit

V10 left 18 honest refusals. Two of them were not missing ABILITIES at all — they were the door
being unable to hear an act the registry already contained:

* `Find the flaky tests in the repository R` was refused `R14_UNHEARD_ACT_WORD:flaky` while the
  machine had every tool needed to measure it, because a flake is a *measurement* and no
  capability performed it;
* `Run a differential test …` was answered by an acceptance measurer on `{run, test}` — two words
  that say "start something" and "there are tests" — and reported `PASS`.

Both are closed, and the second one closed a hole in the vocabulary law that had been hiding
since V9.

### 1.1 New capability: `python.quality.flake_detect.v1`

A flake is not a failing test and not a slow test: it is a test that passes and fails **on the
same bytes**. So the verb is not a linter and not a rewriter — it is a replay:

| varied condition | how | why it is a real flake source |
|---|---|---|
| execution order | `pytest -p flakeorder`, a shuffle plugin written to a **temp dir** and put on `PYTHONPATH` | order-dependent state is the classic flake |
| `PYTHONHASHSEED` | a different seed per run | set/dict iteration order |
| repetition | the same order again | timing-shaped flakes |

Verdict law, deliberately asymmetric:

* `flaky_tests` — outcome **changed** across runs. This is evidence, and the artifact names the
  exact order/hash seeds that failed.
* `consistently_failing` — failed in **every** run: a broken test, reported separately so nobody
  "fixes" a stable failure by rerunning it.
* `stable` — passed in every run **of this budget**, and `detection_scope` says in the artifact
  that this is not a certificate of determinism.

Refusals: `REPEATS_BELOW_TWO` (one execution is a test run, not a flake hunt), `NO_TESTS_FOUND`,
`TESTS_COULD_NOT_RUN` (a collection error is not a flake), `TOOL_NOT_INSTALLED`, `PATH_*`.
The measured tree is never modified.

Pins: `canonical/tests/test_python_quality_flake_detect_v1.py` — **7 passed**.
Receipt: `canonical/astra_runtime/evidence/ASTRA-VERIFY-FLAKEDETECT-001__RECEIPT.json`.
Measured golden: 4 runs, order-dependent test found, 730 ms.

### 1.2 Four vocabulary defects the new row exposed

| # | Defect | Proof | Fix |
|---|--------|-------|-----|
| 1 | `test` / `tests` counted as distinctive evidence | `Run a differential test …` answered by `python.repository.acceptance.measure.v1` with a PASS | `test`, `tests`, `testing` are in `GENERIC_MATCH_TOKENS` (measured: 0 of 151 capabilities lose their last distinctive token) |
| 2 | `run` counted as distinctive evidence | same row, still PASSing on `{run, test}` | `run`, `runs`, `running` are generic too — a mode shared by every capability that executes something |
| 3 | "heard" meant "shares a 4-letter prefix" | `differential` was "heard" because `diff` and `different` are in the vocabulary, so R14 never fired | `_is_a_form_of`: the same word modulo an **inflectional** ending (`-s`, `-ed`, `-ing`, `-ion`, …) |
| 4 | a multi-word keyword claimed only the phrase | `Find the duplicated code in X` was refused `R14_UNHEARD_ACT_WORD:duplicated` while `python.quality.duplication.v1` carried the phrase `duplicated code` | the vocabulary now claims each keyword's **words** as well as the phrase |

Defect 4 is the one worth staring at: the fix for 3 immediately broke a capability that had been
working, and only the probe caught it. A rule that is right about one sentence and wrong about the
next is not a rule yet.

---

## 2. Measured state

### 2.1 The 43-act missing-verb probe

```
python3 execution_guard/hardcore_se_missing_verb_probe_v1.py
{"ANSWERED_BY_OWNING_CAPABILITY": 25, "HONEST_REFUSAL": 18}
silently answered (hollow pass): none
```

| revision | owned | honest | hollow | wrong tool | owned-but-failed |
|---|---|---|---|---|---|
| V6 baseline | 0 | 23 | 18 | 2 | — |
| + analysers | 7 | 10 | 19 | 3 | — |
| + R13 | 12 | 14 | 15 | 2 | — |
| V7 (+8 capabilities) | 16 | 15 | 8 | 4 | — |
| V8 | 15 | 17 | 7 | 4 | — |
| V9 (routing + fixtures) | 23 | 18 | 1 | 1 | 0 |
| V10 (`change_signature`) | 24 | 18 | 0 | 1 | 0 |
| **V11 (this unit)** | **25** | **18** | **0** | **0** | **0** |

Every one of the 43 sentences is now either answered by a capability that performs the act, or
refused. Nothing is silently answered by a neighbour.

### 2.2 The rest of the surface

```
python3 execution_guard/hardcore_se_git_surface_v1.py      12/12 selected, pass, artifact, repo changed
python3 execution_guard/hardcore_se_git_surface_v1.py --refusals   10/10 named, 10/10 untouched
python3 execution_guard/hardcore_se_reachability_v1.py     bindable 22/22  selected 22/22  pass 22/22
python3 execution_guard/adapter_failure_law_probe_v1.py    18 adapters that could end the process -> 18 TYPED_REFUSAL
```

### 2.3 Regression baseline

```
canonical/tests/test_goal_front_compiler_v1.py            14 failed
canonical/tests/test_goal_compiler_world_binding_v1.py     5 failed
canonical/tests/test_live_brain_route_admission_v1.py      7 failed
                                                          26 failed, 107 passed   (identical ids at fec9e26)
```

New pins: `change_signature` 14/14, `flake_detect` 7/7. No new failure, no silenced one.

---

## 3. What is still open (measured, ranked)

1. **17 acts are honestly missing.** Highest value per unit of reuse, with the tool that already
   does it:
   - `move_function` — `python.source.crossfile_edit.choreograph.v1` already computes the plan
     (collision law, ambiguous sites); `change_signature`'s splice + gate is the apply step.
   - `inline_function` — the inverse of `python.refactor.extract_function.v1`.
   - `docstrings` — AST insert + the same gate.
   - `api_compatibility` — public-API AST diff between two trees; pure stdlib.
   - `memory_profile` — stdlib `tracemalloc`.
   - `dependency_add`, `build_package`, `ci_config`, `schema_migration`, `merge_conflict`,
     `resource_leak` (`ruff SIM115`), `retry_design`, `observability`, `crash_repro`,
     `interactive_debug`, `fuzz`, `differential_test`.
2. **`differential_test` is now an honest refusal** where it used to be a wrong tool: the act
   needs a second implementation to compare against, which the sentence names only as "a
   reference".
3. **`change_signature` and `flake_detect` are reached through their stated contracts**, not by
   loose prose. `change_signature` takes an edit spec file (the `choreograph.edits_path`
   convention); `flake_detect` binds the tree and defaults the run budget.
4. **26 pre-existing test failures** on this branch (identical node ids at `fec9e26`) remain the
   largest single red area, untouched by this unit.

---

## 4. Reproduce

```bash
.venv/bin/python execution_guard/hardcore_se_missing_verb_probe_v1.py --json /tmp/mv.json
.venv/bin/python execution_guard/hardcore_se_git_surface_v1.py [--refusals]
.venv/bin/python execution_guard/hardcore_se_reachability_v1.py
.venv/bin/python execution_guard/adapter_failure_law_probe_v1.py
.venv/bin/python -m pytest -q canonical/tests/test_python_quality_flake_detect_v1.py \
                               canonical/tests/test_python_refactor_change_signature_v1.py
```
