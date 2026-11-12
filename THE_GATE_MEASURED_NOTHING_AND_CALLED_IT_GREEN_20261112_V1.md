# The gate measured nothing and called it green

Date: 2026-11-12. Branch: `arena/de512e04-brain` (branched from `8439f609`,
merged `ac6364e8` before commit). Engine file:
`canonical/swe_kernel/egraph_and_deductive_synthesizer_v1.py`.

## 0. Which question this answers

The standing question ("is instant learning solved?", "what is the current open
limiting factor?") already has its verdict-level answers in this tree
(`INSTANT_LEARNING_AUDIT_20261112_V1.md`, `ONE_TRY_IS_NOT_A_LEARNING_SIGNAL`,
`THE_PRIOR_IS_THE_WHOLE_GAME`, `TWO_DOORS_*`). Those verdicts are not re-argued
here. What a "learned it on the first try" claim needs underneath it is an
acceptance gate that can only pass when it actually ran the project's tests.
This round measures that gate itself and finds it defective in two directions at
once — one mode quit too early, one mode waved the edit through having measured
nothing. The second is the rubber stamp that would have manufactured the very
"worked first try" signal a learning claim would rest on.

## 1. Before — both failure modes measured on `8439f609`

The gate has three suite-measurement sites — `_collect_project_bad_tests` (the
baseline before an edit), `_verify_no_new_test_failures` (the verification
after it), and `_run_project_tests` (the runner several ops call directly,
e.g. `memoize_function` at :665 and `add_thread_pool_parallel` at :728). All
three call `_run_cmd(...)` with no `timeout`, inheriting its implicit helper
default of **20.0 s** (`:27`).

**M1 — the budget that could not hold any real suite.** A fixture project whose
test is a `unittest.TestCase` method that sleeps 21 s:

```
REFUSED-1: PROJECT_TEST_BASELINE_UNMEASURABLE in 20.3s   # deadline rc=-9, suite still running
```

The suite was runnable; the gate quit at 20 s and reported it as unmeasurable.
The brain's own `canonical/tests` at `timeout=300`: killed at 300.3 s with the
`SUBSTRATE_CAVEAT` refusal — genuinely beyond any fixed budget, correctly
fail-closed, but the budget itself was never a reviewed number anywhere in the
code.

**M2 — the empty measurement sold as green.** A fixture project whose test file
is pytest-shaped (`def test_it(): assert True`, no `TestCase` class):

```
VACUOUS-2: bad=set() in 0.0s   # test files exist, unittest loads none
```

Python 3.11's unittest loader collects **only `TestCase` subclasses** — there is
no `isTestMethod` check anymore (`/usr/lib/python3.11/unittest/loader.py:120-124`).
`defaultTestLoader.discover` returns an empty suite for the dominant modern test
style, the probe prints an empty bad-list, and the gate reads that as "no
failures" and stamps the edit. Measured end to end: the extract-constant
showcase at `canonical/astra_runtime/tmp/…` passed the door with this vacuous
baseline — `PASS__RAW_GOAL_EXECUTED_…` while nothing had been measured.

So the gate had exactly three modes: refuse-too-early on any suite over 20 s,
pass-while-measuring-nothing on function-style suites, and a real measurement
only for small `TestCase` suites under 20 s.

## 2. The fix — one constant, one named refusal, one scope rule

All in `canonical/swe_kernel/egraph_and_deductive_synthesizer_v1.py`:

1. **`BASELINE_BUDGET_S = 300.0`** — passed explicitly as `timeout=` at all
   three suite sites. Measured rationale in the constant's comment: 21 s fixture
   refused at 20.3 s; brain suite >300 s still refuses (fail-closed, never
   partial).
2. **`BASELINE_NO_DISCOVERABLE_TESTS`** — the suite children now report
   `suite.countTestCases()` by exiting 3 with a marker when it is 0. The parent
   converts that into a **named refusal** —
   `PROJECT_TEST_BASELINE_UNMEASURABLE:TEST_FILES_FOUND_NONE_DISCOVERABLE`
   (door status `FAIL_CLOSED__CAPABILITY_REFUSED_TEST_FILES_FOUND_NONE_DISCOVERABLE`) —
   **iff test files exist inside discovery's own scope**. An empty project (no
   test files) proceeds exactly as before: nothing to measure, nothing claimed.
3. **`_test_files_present` mirrors the loader, not a glob.** The first draft
   used `rglob`, and the tree caught it: `test_three_pillar_…::test_zero_hint_…`
   has a target outside the package tree whose tests live under a non-package
   directory that `discover` never descends — `rglob` saw those files and
   demanded a measurement discovery could not make. The check now walks the
   loader's traversal: direct `test*.py` / `*_test.py` files, descending only
   into directories carrying `__init__.py`.

## 3. After — measured on this branch

| probe | before | after |
|---|---|---|
| 21 s `TestCase` suite | refused at 20.3 s | **measured, `set()` in 21.0 s** |
| function-style test files | silent `set()` in 0.0 s | **named refusal** (baseline and runner) |
| empty project (no tests) | proceeds | proceeds (unchanged) |
| tests outside discovery scope | proceeds | proceeds (unchanged — after the loader-mirror fix) |
| timeout actually passed | `[20.0, 20.0, 20.0]` implicit | **`[300.0, 300.0, 300.0]`** (spy over all three sites) |
| extract chain, `TestCase` suite, in-repo workspace | door PASS on a vacuous baseline | **door PASS on a measured baseline**: `PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED`, `python.swe.transform_and_synthesize.v1`, file rewritten to `EXTRACTED_CONSTANT = 7` |
| same sentence, function-style suite | would have PASSed vacuously | `FAIL_CLOSED__CAPABILITY_REFUSED_TEST_FILES_FOUND_NONE_DISCOVERABLE` |

## 4. Regression ledger

- New pins: `canonical/tests/test_the_gate_waits_for_the_suite_it_measures_v1.py`
  — 6 tests: the budget spy, the named refusal at both sites, the empty project,
  the out-of-scope control, the 21 s measurement, and the door showcase.
- Suites on this branch: `test_swe_transform_contracts_v1` 49/49;
  `test_three_pillar_swe_breakthroughs_v1` + contracts 52/52;
  door/refactor/near-miss/pass-did-not-serve batch 36 passed, 1 skipped;
  new file 6/6 in 22.0 s.
- Substrate: restored by the repo's own `scripts/restore_substrate_v1.py` →
  `SUBSTRATE_READY modules_present=10/10` (needed to run the pytest-importing
  suites locally, same as CI installs pytest).
- The `rglob` regression above was caught by `test_three_pillar_…` before any
  commit — recorded because the scope asymmetry (files existing ≠ files
  discoverable) is exactly the class of error this round is about.
- Pre-existing on base, stash-verified, **not** this round:
  `test_hardcore_swe_kernel_v1::test_egraph_memoize_gil_and_mutation_synthesis`
  fails `FAIL_CLOSED__CAPABILITY_REFUSED_OUTPUT_ALREADY_EXISTS` at its second
  `door.solve` with or without this change. Not fixed silently.

## 5. What this does not claim — next steps, named

- **pytest fallback (the instrumented next round).** Projects whose tests are
  pytest-shaped now *refuse* instead of rubber-stamping — an availability
  regression paid for honesty, the same class of trade the boundary draft made
  when it removed automatic fallbacks. The follow-up instrument is a pytest
  runner used only when `import pytest` succeeds in the child (now known to be
  installable via `restore_substrate_v1.py`); its exit-code map and output
  parsing deserve their own measured round, not a smuggled edit.
- **>300 s suites still refuse.** The brain's own `canonical/tests` remains
  unmeasurable inside the budget; that is the correct fail-closed outcome, now
  explicit and reviewed instead of an accident of a helper default.
- **`_find_project_root` quirks** (targets outside any tests tree) are untouched.
- No capability credit, no benchmark row moved, `truth.achieved` stays false.

## 6. Tie-back

A permanent learning claim is only as honest as its acceptance gate. Two of the
gate's three modes were not measurements: one quit at 20 s and called the suite
unmeasurable, one loaded zero tests and called the edit green. Both are now
named refusals or real measurements. The standing verdicts (`P3 HOLDS`, ONE_TRY
§7, `THE_PRIOR_IS_THE_WHOLE_GAME`) are unchanged; the ground under them got
harder.
