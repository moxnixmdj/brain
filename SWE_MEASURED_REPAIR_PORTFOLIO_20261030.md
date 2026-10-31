# Reuse-first measured repair portfolio

2026-10-30. Local implementation and execution measurements; no independent admission or terminal credit.

## What changed

Connected **existing specialist engines**, rather than adding a replacement repair engine:

- `python_repair_measured_acceptance_controller_v1.py` accepts opt-in `repair_strategy: "iterative_then_guided"`. The default remains `"guided"`.
- The existing strict-progress iterative engine runs first. Only its two normal bounded-exhaustion statuses permit guided fallback. Exceptions, failed fresh replays, and observed input drift stop execution instead of being reclassified as search exhaustion.
- Successful iterative repair must survive its two fresh final replays, patch reconstruction, repository acceptance measurement and objective/contract checks. Search success alone does not authorize acceptance. Semantic rejection does not trigger a route that discards the requirement.
- Reused the existing exact-tree manifest and explicit test hashes to check restoration between branches. Only the newly owned scratch **path**, not every same-named directory, is filtered from source comparison. The manifest's existing cache/metadata exclusions still apply.
- Search reports use a fresh private temporary directory instead of a fixed intermediate filename; a caller-owned old intermediate artifact is preserved. Reports retain strategy and actual branch/candidate/round evidence, including ordinary exhaustion.
- Reused one final pytest summary parser for acceptance measurement and iterative progress scoring. Supported pytest failure scores sum failed and error counts; collection exit codes, timeouts and unparseable baselines refuse iterative search. These are runner-output observations, not attestation of an honest test runner.
- Iterative trials now restore their source bytes in `finally`, including executor exceptions. Accepted edits retain the existing outer restoration and fresh replay gates.
- The existing confined qualification API/CLI accepts this strategy and three strictly bounded iterative budgets. Baseline, measurement, separately reconstructed replay, count agreement and source immutability remain mandatory. No unconfined fallback was added.

No registry or protected-policy edits, promotion, commit or push in this cycle. Ordinary natural-language `solve()` is not newly connected to this portfolio or automatically confined.

## Bounds and invocation

Measured controller arguments:

| Argument | Default | Accepted values |
|---|---:|---|
| `repair_strategy` | `guided` | `guided`, `iterative_then_guided` |
| `iterative_max_rounds` | 6 | strict integer 1–20 |
| `iterative_candidates_per_file` | 24 | strict integer 1–5000 |
| `iterative_max_candidates` | 128 | strict integer 1–50000 |

Booleans, strings and out-of-range budgets refuse. Existing guided budgets are separate bounds, not one shared global candidate quota. The existing confined wallclock bound covers execution, not all host preparation or aggregate cgroup resources.

Example **confined repair payload**, with deliberately small search budgets suitable for the authored fixture below (not recommended universal settings):

```json
{
  "task_text": "tests_pass must be true.",
  "repair_strategy": "iterative_then_guided",
  "test_paths": ["trace_a.py", "trace_b.py", "trace_c.py"],
  "search_limits": {
    "max_guided_files": 3,
    "iterative_candidates_per_file": 1,
    "iterative_max_candidates": 12,
    "timeout_s": 10
  }
}
```

Use the existing `canonical.runtime.confined_crossfile_qualification_v1` CLI with `--source-root`, `--repair-task-path` and a fresh `--output-path`. This is the explicit measured-controller API route, not a general natural-language repair claim.

## Fresh end-to-end measurements

Python 3.11.2, pytest 9.2.0, Hypothesis 6.170.12 in the local recreated venv. Authored temporary Python projects, not held-out upstream defects. No prior Boltons timing or artifact is reused here.

Two fixtures reuse the real test helper in `canonical/tests/test_measured_repair_portfolio_v1.py`:

1. **Three independent defects:** `a(x)`, `b(x)`, `c(x)` each incorrectly use strict `<` at their respective boundaries 3, 5, 7. Three pytest cases check boundary, interior and exterior behavior. Three separate source edits are required by these checks.
2. **Nonmonotonic pair:** two strict-boundary defects; one pytest case requires both fixes. Neither single edit reduces the failed-test score.

All runs use actual subprocess tests, actual patch realization and source-byte restoration checks. Guided bounds: three files, twelve mutations per file, thirty pair attempts. Iterative bounds: six rounds, one candidate per file, twelve total attempts. These are explicit policy configurations with different search bases and budgets—not identical candidate sets or a universal optimality experiment.

Each whole-suite execution counter is incremented by the actual imported pytest test module, outside the source subtree. It includes measurement/replays, but excludes separate localization/trace subprocesses. Attempt counts can exceed executed tests because overlapping/invalid pair combinations are counted but not executed. No test result is cached.

Three runs per direct-controller configuration:

| Fixture / policy | Elapsed samples (ms) | Median (ms) | Whole-suite executions each | Outcome |
|---|---|---:|---:|---|
| Three defects / guided | 11901.940, 11268.131, 11439.554 | 11439.554 | 42 | No verified repair in bounds, 3/3 runs |
| Three defects / iterative→guided | 3764.054, 3459.895, 3419.995 | 3459.895 | 13 | Three-edit measured acceptance, 3/3 runs |
| Coupled pair / guided | 5380.386, 5369.210, 5129.484 | 5369.210 | 19 | Two-edit measured acceptance, 3/3 runs |
| Coupled pair / iterative→guided | 5729.851, 6149.928, 6214.017 | 6149.928 | 22 | Normal exhaustion then two-edit measured acceptance, 3/3 runs |

Three-defect iterative scores: **3 → 2 → 1 → 0**. Candidate trials per round: **1, 2, 3**, total **6**; three additional accepted-improvement replays, two fresh final replays, one baseline and one measurement make thirteen full-suite invocations. Guided-only reports 24 single and 30 pair attempts and emits no patches on this case.

On the coupled pair, iterative search tests two candidates, restores source and reports normal no-progress exhaustion; guided then reports fourteen singles and seven pair attempts, crosses the nonmonotonic valley and verifies both edits.

**Interpretation:** the portfolio broadens measured repair to the demonstrated three-edit task and avoids this guided-only bounded failure. That is not a same-outcome speedup measurement. On the demonstrated pair it adds **14.54% median latency** and three full-suite invocations. Accordingly, guided remains the default. This small benchmark does not justify automatic globally optimal scheduling or a general latency claim.

### Real confined run

One additional uninstrumented three-defect run through `qualify_repair()` completed in **7381.104 ms**:

- whole-project baseline: **3 completed, 3 failed**, return code 1;
- existing iterative engine: six candidate trials, three accepted edits, two fresh passing final replays;
- candidate acceptance measurement: **3 tests, return code 0, tests_pass true**;
- separate reconstructed whole-project replay: **3 completed, 0 failed**;
- original source and copied input snapshot unchanged; no source promotion;
- `independent_semantic_oracle_credit: false`.

The separate replay reruns the same test oracle against reconstructed candidate bytes. It is not an independent semantic specification. This fixture does not establish multi-repository, upstream, multi-language or production repair quality.

## Tests and integrity

New module: `canonical/tests/test_measured_repair_portfolio_v1.py`, **34 cases**. Actual execution covers:

- three-edit pytest progress and acceptance, including `source_root: "."`;
- guided-only bounded failure on that task;
- both normal iterative exhaustion statuses and guided fallback;
- nonmonotonic pair repair;
- final replay failure without fallback;
- source drift, including a same-named but unowned scratch directory;
- executor exception restoration;
- actual timeout/unparseable baseline refusal;
- semantic acceptance rejection without route shopping;
- old intermediate-file preservation;
- strict controller and confined-payload strategy/budget validation;
- real namespace baseline, measured repair and separate reconstructed replay.

Core regression selection: patch search, iterative, coupled, provenance-guided, repository measurement, measured acceptance, reuse, confined measured repair, new portfolio and namespace-launcher tests: **132 passed in 97.01 s** on the final run (10 modules). The new module contributes 34 cases. The preceding core run, before adding the last exhaustion test, was **131 passed in 95.28 s**.

Integrity guard against base `c79a8f544fe47b1d7250b1c64889b958237db4f3`: **17 rules, 0 violations, PASS**. `git diff --check`: clean. These are local checks, not an independent verifier or GitHub referee verdict.

Adjacent 11-module selection (task-bound/public contracts, acceptance clause, crossfile qualification, portability, apply-verified and semantic repair):

- first run: **174 passed, 2 failed in 56.35 s**;
- identical repeat: **175 passed, 1 failed in 54.77 s**;
- persistent failure: `test_python_repair_apply_verified_v1.py::RepairApplyVerifiedTests::test_missing_test_paths_is_refused_rather_than_guessed` expects refusal, whereas the unchanged apply adapter explicitly discovers unstated tests. This conflict was not resolved or hidden by changing that test;
- first-run-only failure: `test_front_door_task_bound_contracts_v1.py::test_existing_report_is_preserved_before_execution` observed a passing result instead of refusal. It passed in isolation, in a 69-case task-bound/public-contract rerun, in the identical 176-case repeat, and in 100 further direct existing-report requests. **Root cause remains unresolved; this is not claimed fixed.**

No full-suite or CI-green claim. Earlier expanded-suite failures remain historical evidence in the linked prior report, not new results for this cycle.

Prior work: [guided search reuse and confinement](SWE_GUIDED_REPAIR_REUSE_20261030.md). Those prior measurements are distinct from the fresh measurements above.
