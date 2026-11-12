# Closing the 9 Remaining Refuted-Rule Code-Edit Paths, 6-Language CST Invalidation, and Impact-Sliced E-Graph Baseline

**Date:** 2026-11-12
**Authority:** `NONE` (sandbox measurement & unit-test verification; `truth.achieved = false`)

## 1. Why Guarding `apply_crystallized_code_rule` Left 9 Paths Open

PR #6717 (`90be6536d1`) added `if not rule_is_applicable(rule): return None` to `apply_crystallized_code_rule(source_text, rule)`. However, `apply_crystallized_code_rule` is a 1-line wrapper around `next(iter_crystallized_code_rule_candidates(source_text, rule), None)`. Production repair engines, scope learners, and cross-language transfer bridges call the underlying candidate generators directly.

Measured on `90be6536d1` after teaching `def classify(x): return x <= 100` -> `return x < 100` and refuting it via `store.refine_scope_from_counterexample(...)` (`persisted_state == 'INVALIDATED'`):

| Path | Entry point | Pre-fix behavior on `INVALIDATED` rule | Post-fix behavior |
|---|---|---|---|
| 1 | `verified_skill_crystallizer_v1.apply_crystallized_code_rule` | `None` (guarded in #6717) | `None` |
| 2 | `verified_skill_crystallizer_v1.iter_crystallized_code_rule_candidates` (called by `multistep_repo_closed_loop_solver_v1:1220`, `cow_impact_repair_engine_v1:168,195`, `language_neutral_skill_bridge_v1:218`) | **FIRES** (`['def g(y):\n    return y < 10\n']`) | `[]` |
| 3 | `verified_skill_crystallizer_v1.narrow_rule_at_apply_time` | **FIRES** (returns narrowed rule dict) | `None` |
| 4 | `operator_generalization_v1.propose_operator_swaps` | **FIRES** (`['def g(y):\n    if y < 10:\n        return 1\n']`) | `[]` |
| 5 | `boundary_disjunction_normalization_v1.propose_semantic_swaps` | **FIRES** (`['def g(y):\n    return y < 10\n']`) | `[]` |
| 6 | `egraph_and_deductive_synthesizer_v1.propose_egraph_algebraic_rewrites` | **FIRES** (`['def g(x, y):\n    return x * (1 + y)\n']`) | `[]` |
| 7 | `tree_sitter_cst_skill_skeleton_v1.iter_cst_skeleton_candidates` | **FIRES** (`['fn g(y: i32) -> bool { y < 10 }\n']`) | `[]` |
| 8 | `tree_sitter_cst_skill_skeleton_v1.recall_across_languages_cst` | **FIRES** (edits target language) | `None` |
| 9 | `language_neutral_skill_bridge_v1.cross_language_candidates` & `recall_across_languages` | **FIRES** (`patched_source: 'function tier(a) { return a < 50; }\n'`) | `[]` / `None` |
| 10 | `VerifiedSkillStore.recall_and_apply_verified` Stage 4B across `rust`, `go`, `typescript`, `javascript`, `java`, `cpp` | **FIRES in all 6 languages** | `None` in all 6 languages |

Meanwhile, `store.lookup_rules("python")` continues to return the `INVALIDATED` rule unchanged so `auditability_report_v1` never inflates its score by hiding refuted rules from its denominator.

## 2. Impact-Sliced E-Graph Synthesizer Baseline (`TWO_DOORS_COUNT_AVAILABILITY_DIFFERENTLY_20261112_V1.md` Rank #1)

When `python.swe.transform_and_synthesize.v1` (`egraph_and_deductive_synthesizer_v1.py`) targeted a module inside a repository whose `tests/` directory contains `> 60` test files (such as `canonical/tests` with 2,480 files), `_collect_project_bad_tests` and `_verify_no_new_test_failures` invoked `unittest.defaultTestLoader.discover` over the entire directory inside a single 20-second subprocess, resulting in `SIGKILL` (`rc=-9` / `124` -> `PROJECT_TEST_BASELINE_UNMEASURABLE`).

- `_suite_expr_and_env` now keeps full `unittest.defaultTestLoader.discover` for all suites with `<= 60` test files and impact-slices suites with `> 60` test files by target module stem (`swe_typed_plan_v1`: 20s timeout -> 3.45s `rc=0`).
- `structural_refactor_python`'s `extract_constant` now scopes its constant search to the named function when the sentence specifies `function <name>` (`stated_family_token` -> `NO_MAGIC_CONSTANT_FOUND`).

## 3. PEP 552 Same-Second `.pyc` Collision in `test_gate_accepts_a_failed_repair_v1.py`

In `test_the_repairable_fixture_really_is_repairable_and_really_is_broken`, `repaired` (`x * x`) and `REPAIRABLE_FIXTURE["calc.py"]` (`x + x`) have identical byte length (5 bytes). When `good` and `bad` executed within the same integer wall-clock second without `-B`, Python's PEP 552 `.pyc` header check (`int(st_mtime)`, `st_size`) treated `__pycache__/calc.cpython-311.pyc` from `good` as fresh and executed `x * x` during `bad`. Passing `-B` to `subprocess.run` eliminates the race.
