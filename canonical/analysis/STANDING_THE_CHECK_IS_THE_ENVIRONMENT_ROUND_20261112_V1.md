# Standing the check: the environment round Problem 2's own measurement asked for

**2026-11-12. Branch `arena/f1d1612c-brain`. Base `f5b6d486`. Authority NONE** — producer-run,
one machine, zero model calls, `$0`, no capability registered, `truth.achieved` stays `false`.

The owner's framing, restated as given:

> **Problem 1: Exact Recall (SOLVED)** — 8.13×. **Problem 2: Generalization (NOT SOLVED)** —
> a similar task, exact matches only. **Focus on solving problem 2 perfectly with the smartest
> solutions in the fastest way.**

The previous round measured where generalisation actually stops and named the next action in
one line: *"One demonstration is enough to learn a change, and a check is what makes the learning
safe to use. Neither is missing. What is missing is standing up a project's checks — its
dependencies and its test entry point — for each new environment."* It could not do that action:
**0 of 42** changed files in real projects were verifiable here (6 tasks: no test module imports
the file; 6 tasks: tests need a dependency that is not installed).

This round built the named action, ran it on the same twelve pull requests, and reports what is
still blocking — refusal by refusal, in the record's own words.

---

## 1. The verdict, in one line

**The check now stands up: five tasks got their declared dependencies installed into isolated
venvs, five got manifest-named repairs, three execute their own suites end to end — and the
verified-pair count on this corpus is still 0 of 132, because every remaining refusal is a real
project condition with a specific name, not a missing organ.**

The organs are built and proven on real repositories (including a dependency install against the
live index); the corpus's residual blockers are now enumerated per project instead of bucketed
half/half; and the number the previous round said matters — *how much of 0.529 becomes verified* —
is honestly still `0.000`, with the reason printed for each of the twelve tasks.

## 2. What was built (all in `canonical/tools/generalization_rung_gradient_v1.py`)

**2.1 The test-entry finder reports its own uncertainty.** The previous finder asked one
question of one file (`test_*.py` that imports the record's *first* path). Now, per target path:

* candidates are collected from `test_*.py`, `*_test.py`, `tests.py` and anything under a
  `test/`/`tests/`/`testing/` directory;
* the criterion is still **an import, never a mention** (the earlier round's bug stays fixed);
* a candidate must import the target directly (tier 0/1) or reach it through one intermediate
  module (tier 3, labelled `INDIRECT`);
* within a tier, a module that **defines tests** outranks one that does not — stem's
  `test/arguments.py` sits in `test/`, imports the target, and is the runner's argument parser;
  a candidate that defines nothing collects nothing;
* the receipt is `{chosen, candidates, confidence}` with `DIRECT | IN_DIRECTORY | INDIRECT |
  NONE`, written into the record per task.

**2.2 The oracle is resolved per file, not per task.** The old `Check` bound one test module
(the record's first path) to every path of the task: a file whose own tests never ran could be
judged by a sibling's suite. `accepts(path, …)` now resolves the entry for `path` and refuses
with `CHECK_NO_TEST_MODULE` when no test imports *that* file — even when a sibling's suite is
green. (The unit test pins exactly that: `pkg/b.py` refused while `pkg/a.py` passes.)

**2.3 Dependencies get stood up.** On `CHECK_DEPENDENCY_MISSING`, the check now:

1. reads what the project **declares** — `requirements*.txt`, `pyproject.toml`
   (`project.dependencies` + optional groups), `setup.py` (`install_requires`, `tests_require`,
   **all of `extras_require`**), `setup.cfg`;
2. creates an isolated venv outside the project copy and installs the declaration (one venv per
   task, reused by every pair; `pip` behind a single `_pip_install` seam so tests never need an
   index);
3. re-runs; if the suite still cannot import something, **repairs**: the missing root package
   name is installed **only if the project's own manifest text spells it out** (the words the
   literal parser did not reach — `read("requirements.txt")`, dynamic `setup()`, dev files).
   A name the project never writes is still not installed; that would be a guess, and refusing
   guesses is the point of this instrument;
4. reports `STOOD | INSTALL_FAILED (with pip's tail) | NO_DECLARED_DEPENDENCIES` per task, and
   names every residual import (`missing_modules: ["graphene"]`, not "a dependency").

**2.4 A suite that ran nothing is not a check.** `unittest` collecting `Ran 0 tests` used to
return code 0 — a silent green light. It is now `CHECK_NO_DISCOVERABLE_TESTS` unless the
project's own `pytest` is importable in the (possibly stood-up) interpreter, in which case
pytest runs the file and pytest's exit 5 (collected nothing) is refused the same way. This fired
on a real project on the first run (torproject/stem).

**2.5 The corpus was filtering out the very manifests the check must read** — instrument bug,
found this round, fixed: `fetch_tree` kept only `*.py`, so `requirements.txt`,
`pyproject.toml`, `setup.cfg`, `Pipfile`, `tox.ini`, `extension.json` were absent from every
project copy and six tasks read `NO_DECLARED_DEPENDENCIES` for dependencies their own
manifests named. `_carries()` now keeps sources **and** the project's dependency manifests;
`fetch_again`'s hash check and the old record are unaffected (they name `.py` entries only).

## 3. What changed on the same twelve pull requests

Corpus: the exact twelve merged PRs of `GENERALIZATION_RUNG_GRADIENT_20261112_V1.json`,
re-taken by name with `--labels` (same frozen merge commits, same deterministic draw).
New record: **`canonical/verification/STANDING_THE_CHECK_20261112_V1.json`**.

| task | before | after | standing / repair | the residual, by name |
|---|---|---|---|---|
| ArduPilot/MAVProxy#1623 | NO_TEST | NO_TEST | — | no test imports the changed files at all |
| Azure/azure-cli-extensions#8010 | DEPENDENCY | DEPENDENCY | no declaration reachable | missing `azure` (extension manifest not parsed) |
| CCSI-Toolset/FOQUS#1002 | DEPENDENCY | DEPENDENCY | requirements **INSTALL_FAILED** + repaired `pyqt5, pytest` | missing `foqus_lib.version.version` — a **generated** module |
| FZJ-IEK3-VSA/ActivityAssure#2 | NO_TEST | DEPENDENCY | **STOOD** (requirements) | missing `test.integration_tests` — stdlib `test` package shadows the project's namespace `test/` |
| avocado-framework/avocado-vt#2887 | NO_TEST | DEPENDENCY | requirements **INSTALL_FAILED** + repaired `aexpect` | missing `avocado` — a **different repository's** framework |
| cta-observatory/pyirf#289 | DEPENDENCY | **FAILS_ON_THE_ORIGINAL** | **STOOD** (setup) | suite runs; baseline red — conftest needs data files the `.py` corpus never carried |
| jodal/comics#652 | NO_TEST | NO_TEST | pyproject **INSTALL_FAILED** + repaired `django` | files[0] has no importing test |
| learning-unlimited/django-argcache#5 | NO_TEST | NO_TEST | **STOOD** (setup) + repaired `django` | files[0] has no importing test |
| openimis/openimis-be-core_py#414 | DEPENDENCY | DEPENDENCY | **STOOD** (setup) | missing `graphene` — not in the installed declaration |
| scoursen/django-softdelete#114 | DEPENDENCY | **FAILS_ON_THE_ORIGINAL** | repaired `django` | suite runs; baseline red (genuine failure under installed django) |
| torproject/stem#155 | NO_TEST | **FAILS_ON_THE_ORIGINAL** | — | suite runs (`test.integ.installation`); integration baseline red — needs a real tor environment |
| wolfSSL/wolfcrypt-py#120 | DEPENDENCY | DEPENDENCY | **STOOD** (pyproject) + repaired `pytest` | missing `wolfcrypt._ffi` — a **C extension that must be built** |

Reason counts, old → new: `NO_TEST 6 → 3`, `DEPENDENCY 6 → 6`, **`FAILS_ON_THE_ORIGINAL 0 → 3`**
(suites now execute), `NO_DISCOVERABLE` fired once mid-run and is now absorbed by the
defines-tests ranking. Standing: **5 tasks STOOD, 5 tasks repaired, 3 tasks executing.**

**And the headline number did not move: `any_rung_check` edited 0 of 132, verified coverage
0.000.** The check-gated arms refused all 726 candidate evaluations — correctly, because on
this corpus every task-level entry is either still missing an import, red on its own baseline,
or absent. The difference from yesterday is not the count; it is that each refusal now carries
the operator that would lift it (§5).

## 4. The four claims, split

| claim | verdict | evidence |
|---|---|---|
| exact recall is solved | **TRUE** (unchanged) | precision 1.000 on the same corpus; the old record's 15 tests still pin it |
| "generalisation is exact matches only" | **FALSE as stated** | one showing recovers 0.548 of the developers' changes at precision 1.000; two showings 0.895 |
| "semantic similarity (TF-IDF 0.4–0.5) solved Problem 2" | **FALSE** | a similarity score never executed an adaptation. The live `PASS__TIER0A_SEMANTIC_GENERALIZATION` path (#6815) returns `pass=True` from an `ast` keyword counter dressed with `top_similarities`; the retrieval result supplies the label, not the work. Receipts, not titles |
| widen the rule / bigger library / pick better demonstrations | **FALSE** (already killed; re-confirmed) | widest rung: 0.048 coverage, 0.455 precision, 42 wrong changes |
| the missing thing is standing up the environment | **TRUE, and now partly built** | 0/42 → three suites executing, five installs standing; residual gaps named per project |

The honest scope of Problem 2 after this round: **within a change kind, one demonstration
already transfers precisely (half the work, zero wrong); what blocks "a similar task in a new
environment" is verification standing, and verification standing is now an implemented organ
whose remaining failures are enumerated, not a mystery.** The verified number on this corpus is
still zero; the sentence "we cannot verify anything here" is no longer true — we can verify, and
we can say exactly why each of these twelve does not yet pass.

## 5. The remaining operators, in order of what the record names

1. **Generated and built artifacts** (`foqus_lib.version.version`, `wolfcrypt._ffi`): the check
   must run the project's build step (`pip install -e .` / `python setup.py build_ext`) before
   the suite. Three tasks name this class.
2. **The project's own package missing from the tree** (`avocado` — a different repo; also
   self-install for projects whose suite imports the project by installed name).
3. **Namespace shadowing** (`test.integration_tests` under stdlib `test`): run with the project
   forced ahead of the stdlib (or refuse by that name — already refused by that name).
4. **Baseline red for environment reasons** (pyirf's data files, stem's tor): the corpus carries
   sources and manifests; data assets and system services are outside a `str` tree. The honest
   next instrument step is a real checkout for the check, not more parsing.
5. **An extension manifest that is not yet parsed** (azure's `extension.json` is *carried* now;
   the declaration parser does not read it yet).
6. **A custom runner** (stem's `run_tests.py`): entry finding stops at unittest/pytest; the
   project's own entry point is the next rung of the same finder.

None of these require a smarter learner. All of them are code, priced the way this tree has
always priced code: one class, one lesson-shaped test, measured on the same corpus.

## 6. What the outside world was doing in 2026 while this was measured

* **Environment-in-the-Loop** (arXiv `2602.09944`): "automated environment setup must become a
  first-class concern"; correctness "is ultimately verified only within a runnable environment."
* **HerAgent** (arXiv `2602.07871`): Environment Maturity Hierarchy with execution-based
  validation and repair; +79.6% over prior work; resolves instances no prior method could.
* **EnvPilot** (arXiv `2609.07357`): experience-augmented setup configures **75.00% of 112
  unseen GitHub projects** (+12.5 pp); its benchmark *fails* a run where "no tests are executed"
  — the same vacuity this round refuses by name.
* **ResearchEnvBench** (arXiv `2603.06739`): formalises a **capability-hallucination metric**
  (self-reported success vs ground-truth executability); "it installs" ≠ "it runs".
* **SetupBench / DeployBench / MEnvAgent / RAT** (2025–2026): the same bottleneck, measured.
* Test-impact practice (2026): import-graph selection with **conservative fallback** — "missing
  a failure is worse than running extra tests" — which is exactly this check's refusal rule.

This round's organ is the tree's instance of the same frontier: the check is the verifier, the
venv is the environment agent, `Ran 0 tests` refusal is the hallucination guard.

## 7. Reproduce

```bash
# the record (network: gh + codeload + pypi; ~7 minutes)
python3 canonical/tools/generalization_rung_gradient_v1.py \
  --labels "ArduPilot/MAVProxy#1623,Azure/azure-cli-extensions#8010,CCSI-Toolset/FOQUS#1002,FZJ-IEK3-VSA/ActivityAssure#2,avocado-framework/avocado-vt#2887,cta-observatory/pyirf#289,jodal/comics#652,learning-unlimited/django-argcache#5,openimis/openimis-be-core_py#414,scoursen/django-softdelete#114,torproject/stem#155,wolfSSL/wolfcrypt-py#120" \
  --check tests --files 4 --out canonical/verification/STANDING_THE_CHECK_20261112_V1.json

# the pins (offline)
pytest -q canonical/tests/test_the_check_is_the_difference_v1.py \
          canonical/tests/test_the_check_stands_up_what_verification_needs_20261112_V1.py
# 28 passed  (15 previous + 13 new)
```

## 8. Mistakes this instrument made this round, none of which survived into a number

1. **Monkeypatch arity**: `_pip_install` patched as a function of `(python, args)` while the
   seam is a method — two tests failed loudly before anything was measured.
2. **Relative-import resolution written backwards** (`from .x` resolved to `x` instead of
   `pkg.x`) — caught by re-reading the branch before any corpus run.
3. **The candidate list ranked alphabetically**, so stem's `test/arguments.py` (defines no
   test) beat the unit tests — fixed by the defines-tests rank; pinned.
4. **A repair venv lingered after every install failed** — cleaned when nothing succeeded;
   pinned (`_venv_dir is None`).
5. **`extras_require` not parsed** (half of these projects put pytest there) — fixed, pinned.
6. **The corpus carried only `.py`**, silently deleting every declaration the standing organ
   exists to read (§2.5) — the largest instrument bug of the round; fixed, pinned offline.
7. **One entry bound to the task's first path** (inherited from the previous round's checker) —
   fixed by per-path resolution; pinned with the sibling-suite refusal test.

## 9. What is not claimed

* **0 of 132 pairs verified on this corpus.** The verified-coverage number the previous round
  wanted is unchanged; what changed is that its blockers are named per project (§3, §5).
* No computer-use task was executed; no capability registered; `truth.achieved` stays `false`.
* Installing dependencies is real pip against the live index in the corpus run, but five
  projects still fail to install (heavy/old pins) or lack a parseable declaration — reported,
  not hidden.
* The 8.13× exact-recall result and the 0.529/0.891 coverage curve belong to the previous
  records and their pinned tests; this round changes neither.
