# Verdict on §3: Instant Learning — What Is Real, False, Unproven, Missing

**Date:** 2026-11-26 · **Branch:** `arena/fe676c2a-brain` · **Head:** `ac5c1015`
**Method:** live runs this session + file evidence. Nothing asserted because it was said earlier.

## 1. The claim

> "We already solved instant learning, including in new arbitrary environments. The agent does a task once in any new coding environment or computer task and learns it permanently."

## 2. Verdict

**FALSE as stated. A narrower claim is TRUE, and the gap between them is the whole of §6.**

- **TRUE (narrow):** the project has a real K3=0 instrument that reads a repair off a failing run without a model, for a specific class of bugs (single-expression binop/operand fixes, guard conjuncts spelled in the same file, type-materialisation). Verified this session: `solve_swe_repo_native` fixed `a-b → a+b` in 0.13s with `model_calls: 0`, verified by the project's own suite on disk.
- **FALSE (broad):** the agent does NOT do a task once in an arbitrary new environment and learn it permanently. Three independent failures prove it:
  1. **Cold-start failure:** `UnifiedModel.solve("Fix the bug where add returns subtraction…")` → `FAIL_CLOSED: CAPABILITY_INPUTS_MISSING`. The engine requires structured inputs (`repo_root`, `test_targets`, `candidate_files`); natural-language specs have no path to them. PR #7080's HARD-51 receipt is **0/51** for exactly this reason.
  2. **False-green oracle:** `solve_swe_repo_native_multifile._run_suite_in_dir` runs `python -m unittest <file>` which does not discover plain `def test_*` functions. On a repo with `assert get_name(None) == ""` (failing), the engine returned `PASS__BASELINE_ALREADY_GREEN` — a lie. The correct oracle (`stdlib_cow_test_runner_v1`) reports `1 failed, 1 passed` in 8.5ms. An agent that cannot tell green from red cannot learn from experience.
  3. **No crystallization:** even on success, `crystallized_law_id=None` and `learned_skill_id=None` for multi-statement fixes. `CanonicalLawStore.add_verified_diff` requires exactly one changed line-block (`len(changed)==1`, `tag=="replace"`, ≤12 old / ≤20 new lines) and the spine only calls it when `len(changed)==1` (single file). Multi-file and multi-statement fixes are never stored, so nothing compounds.

## 3. Why can't we just let the model experience the most advanced coding actions once and have it learn them?

Because **experience is not learning unless three things happen, and none of them happen today:**

1. **The experience must be read correctly.** The relation reader (`the_relation_is_read_from_the_failing_run_v1` + `the_assertion_is_the_demand_v1`) extracts value obligations from the failing assertion's own right-hand side. This works when the test suite runs and the failure is an assertion with live values. It fails when the oracle lies (unittest false-green) or when the failure is not an assertion (crash, timeout, missing import). No oracle, no obligation, no learning.
2. **The read must be generalised, not memorised.** `CanonicalLawStore` stores `old_fragment → new_fragment` keyed by error class (`python:AssertionError`). That is a lookup, not a law: it cannot apply to a new file with different identifiers, and it cannot represent "delete this guard and wrap that element in a fallback" because that is a tree difference, not a line difference. `SkillStoreV2` (statement-level anti-unification) + `ASTSubtreeAntiUnifier` (schematic holes) were built to generalise — but they are unwired, so generalisation never runs.
3. **The generalisation must survive contact with a new environment.** Even if a morphism is stored, nothing re-probes it before trusting it (staleness), nothing refutes it on regression (`mark_refutation` exists but is never called by the spine), and nothing filters future candidates against negative invariants (`NegativeInvariantStore` exists but is never consulted). Without admission control, the store fills with untested guesses and the agent repeats dead ends.

In short: **we have a reader without a writer, a writer without a gate, and an oracle that sometimes lies.** Experience flows in, nothing permanent comes out.

## 4. What stops us now (ranked by leverage)

| # | Blocker | Evidence | Fix this session |
|---|---|---|---|
| 1 | **False-green baseline oracle** | `_run_suite_in_dir` uses `unittest`; plain-function tests invisible. Reproduced live: failing repo → `PASS__BASELINE_ALREADY_GREEN`. | Replace with `stdlib_cow_test_runner_v1` (supports plain functions, pytest nodeids, no pytest dep). |
| 2 | **Cold-start spec gap** | `solve()` needs structured inputs; NL issues have no path. HARD-51 0/51. | New `cold_start_swe_adapter_v1`: NL issue + repo scan → localization → structured spine call. K3=0, retrieval + interrogation only. |
| 3 | **Multi-statement crystallization gap** | `add_verified_diff` single-block only; `SkillStoreV2` unwired; `learned_skill_id=None` on every multi-line fix. | Wire `SkillStoreV2.learn` + `ASTSubtreeAntiUnifier` into spine crystallization; keep `CanonicalLawStore` for single-line, add `SkillStoreV2` for multi-statement. |
| 4 | **No admission gate** | `NegativeInvariantStore`, `verifier_falsification_v1`, `learned_skill_verdict_v1`, `conformal_evalue_gate` all unwired. Store has no refutation path. | Wire `NegativeInvariantStore.record/refuted` into spine: refuted patches become invariants that filter future candidates before compilation. |
| 5 | **No honest local benchmark** | Container benchmarks need Docker (absent); no local harness reports per-task results with ablations. | New `swe_bench_local_harness_v1`: runs spine on hard local tasks (verified rows + lens + multi-statement + boundary cases), reports per-task + empty-vs-seeded ablation. |
| 6 | **Unwired dark matter (11 modules)** | 11 files exist, 9 unwired. | Wire the 4 highest-leverage (quotient, contrast-probe, seed-corpus, metamorphic) into the cold-start adapter; leave the rest for Wave 46. |

## 5. What is unproven (not false, not true)

- Whether `SkillStoreV2` morphisms actually transfer to held-out repos (no transfer test has been run; this session's harness runs the first one).
- Whether `infer_transducer` cracks codec/byte-table bugs in practice (implemented, never benchmarked; harness includes a lens case).
- Whether boundary fuzzing (`differential_boundary_scan`) catches hidden regressions (implemented, never run against a real patch; harness includes it as a post-check).
- Whether the 6 verified relation rows (attrs/packaging/more-itertools from the 2026-11-24 verdict) still land at the new head (harness re-runs them).

## 6. What is missing (not yet built anywhere)

- A spec-discovery front-end that turns "fix the bug where X" into `(test_targets, candidate_files, obligations)` without a model. This session builds the minimal version.
- A seeded skill store (PR #7080 notes `instant_swe_skill_store_v1.new_store()` is the only store builder; a seeded arm is new work). This session seeds from `SkillStoreV2` + `CanonicalLawStore` JSON.
- A Docker CI runner for official SWE-bench Pro / Terminal-Bench 4.0 / OSWorld 2.1. Blocked locally (no Docker); GitHub Actions workflow is the path, recorded as blocked, not faked.

## 7. The one line that matters

**The project has a real instrument and a false agent. The instrument reads an edit off a failing run; the agent cannot reach the instrument from a cold-start goal, cannot trust its own oracle, and cannot keep what it learns. Fix the oracle, wire the writer, build the front-end — in that order.**
