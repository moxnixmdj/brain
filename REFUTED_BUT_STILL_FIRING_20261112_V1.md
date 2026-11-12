# The rule was refuted, and kept firing

**2026-11-12.** Authority **NONE**. `truth.achieved` = `false`.

This pass tested whether the tree's *revision* machinery — the lever with the largest measured
effect in the literature (+22 points vs +3.5 for one-shot) — actually repairs a bad rule. It
does. Then I found that the repair was recorded and thrown away at the point of use.

---

## 1. The good news, measured first

A rule induced from one correct edit (`x <= 100` → `x < 100`), then given a spec counterexample
(`50` must stay inclusive), is handled correctly:

```
refine_scope_from_counterexample -> INVALIDATED
persisted state                  -> INVALIDATED (and a counterexample record)
recall_and_apply_verified        -> refused, with a strict verifier
recall_and_apply_verified        -> refused, with `lambda c: True` as the verifier
```

That last line matters: two passes ago the permissive verifier was what inflated
`verified_hits`. The counterexample path is not fooled by it.

## 2. The defect: enforcement lived in a call site, not in the primitive

The **apply** primitive never looked at state:

```
apply_crystallized_code_rule("def tier(a):\n    return a <= 50\n", refuted_rule)
    -> "def tier(a):\n    return a < 50\n"      # still edits, still the wrong answer
```

And one production consumer pairs the state-blind public read with it:

```python
# canonical/runtime/bound_capabilities/software_repair_crossfile_choreograph_v1.py:1126
for rule in VerifiedSkillStore().lookup_rules("python", "python_test_repair"):
    c_out = apply_crystallized_code_rule(src, rule)
    if c_out is not None and c_out != src:
        candidates.insert(0, c_out)          # <-- highest priority repair candidate
```

**A refuted edit was being offered as the first candidate for repair.** The sibling consumer
(`cow_impact_repair_engine_v1.py:1152`) guards the same read by hand:

```python
for lang_rule in store.lookup_rules("python"):
    if lang_rule.get("state") == "INVALIDATED":
        continue
```

Two callers, same API, opposite behaviour. Enforcement that each caller must remember is not
enforcement — it is a convention with one violator per new caller.

## 3. The fix, and the fix I rejected

**Rejected:** filter invalidated rules out of `lookup_rules()`. Measured reason:
`auditability_report_v1` enumerates exactly that call to compute its denominator. Filtering the
read would have *raised* the reported auditability by hiding the rules it could not verify.
An observability tool that improves when you delete the evidence is the failure this session
keeps finding.

**Shipped:** one guard in the primitive, `state in (None, 'ACTIVE')`, plus a shared
`rule_is_applicable()` that the recall path can adopt. Returning `None` is the same contract as
"the rule did not fire", so every caller already handles it. The public read stays complete.

```
primitive applies a refuted rule   False  ->  None
public view still shows it         True   (state INVALIDATED)
backward compatible                a rule with no state field still applies
```

## 4. A refutation is knowledge, so it must travel

A permanent memory that is only permanent on one machine is not permanent:

```
export_bundle after refutation  ->  bundle carries INVALIDATED
import into a FRESH store       ->  state INVALIDATED, apply refused
stale bundle (state forced ACTIVE) re-imported into a refuted store -> stays INVALIDATED
```

The second line is the one worth having: a fresh machine learns not only the rule but that the
rule was refuted. The third says an older bundle cannot revive it.

## 5. Regression evidence

36 suites touch this store. On this branch: **13 failed, 358 passed**. On an unmodified clone
of `main`: **14 failed, 343 passed**. The 13 are a strict subset — my change caused zero
regressions, and the one extra failure on `main` is a test that reads the live store db, which a
fresh clone does not have. The +15 passing are the new tests.

14 new tests, including `test_the_public_view_still_returns_refuted_rules`, which exists to
fail if anyone later "improves" auditability by hiding refutations.

---

## What this changes about the answer

Last pass I said the gap was the oracle. This pass confirms the oracle side works — a spec
counterexample correctly kills a rule — and shows the loss was **downstream of the oracle**, in
a primitive that ignored it. So the honest state of the chain is:

## 6. Second-pass audit on `90be6536d1`: 9 remaining paths, 6-language CST transfer, and impact-sliced e-graph baseline

Re-probing `90be6536d1` after restoring the pinned 10-module SWE substrate (`python3 scripts/restore_substrate_v1.py` -> `SUBSTRATE_READY`, `tree-sitter==0.20.4`) resolved two misconceptions from the first pass and exposed 9 remaining code-edit paths where an `INVALIDATED` rule still fired:

1. **Cross-language transfer across all 6 non-Python languages works in this tree today**:
   `test_phase3_one_python_lesson_transfers_across_all_six_other_languages` failed in the first pass only because `restore_substrate_v1.py` had not been run (`tree_sitter` was absent). With `tree-sitter==0.20.4` present, `test_phase3_one_python_lesson_transfers_across_all_six_other_languages` **PASSES**: one Python lesson (`len(xs) <= cap -> len(xs) < cap`) transfers across `rust`, `go`, `typescript`, `javascript`, `java`, and `cpp` via `tree_sitter_cst_skill_skeleton_v1.py`.
2. **Because cross-language transfer works, a rule refuted in Python (`state == 'INVALIDATED'`) was still editing code across all 6 other languages and 9 sibling generators**:
   Guarding only `apply_crystallized_code_rule` (a 1-line wrapper around `next(iter_crystallized_code_rule_candidates(...), None)`) left the underlying generators and cross-language bridges unguarded. On `90be6536d1`, a rule with `state == 'INVALIDATED'` still fired in:
   - `verified_skill_crystallizer_v1.iter_crystallized_code_rule_candidates` (called directly by `multistep_repo_closed_loop_solver_v1.py:1220`, `cow_impact_repair_engine_v1.py:168,195`, `language_neutral_skill_bridge_v1.py:218`)
   - `verified_skill_crystallizer_v1.narrow_rule_at_apply_time`
   - `operator_generalization_v1.propose_operator_swaps`
   - `boundary_disjunction_normalization_v1.propose_semantic_swaps`
   - `egraph_and_deductive_synthesizer_v1.propose_egraph_algebraic_rewrites`
   - `tree_sitter_cst_skill_skeleton_v1.iter_cst_skeleton_candidates` & `recall_across_languages_cst`
   - `language_neutral_skill_bridge_v1.cross_language_candidates` & `recall_across_languages`
   - `VerifiedSkillStore.recall_and_apply_verified` Stage 4B across all 6 non-Python languages (`rust`, `go`, `typescript`, `javascript`, `java`, `cpp`)
   - Scope calibration enumerators (`autonomous_awake_loop_v1.py:1320`, `sentient_cognitive_core_v1.py:1585,1644`)
   All 9 paths now enforce `state in (None, "ACTIVE")`, verified by `canonical/tools/invalidation_enforcement_v1.py` (`any_path_applies_refuted_rule == False`) and `canonical/tests/test_invalidation_enforcement_v1.py` (17/17 passing).
3. **E-graph synthesizer baseline scalability (`TWO_DOORS_COUNT_AVAILABILITY_DIFFERENTLY_20261112_V1.md` Rank #1) & PEP 552 `.pyc` race**:
   - `egraph_and_deductive_synthesizer_v1._suite_expr_and_env` now impact-slices test suites with `> 60` test files by target module stem (`swe_typed_plan_v1`: 2,480 files -> impacted slice in 3.45s instead of 20s `SIGKILL` / `PROJECT_TEST_BASELINE_UNMEASURABLE`), and `extract_constant` scopes to the stated function name when present (`stated_family_token` -> `NO_MAGIC_CONSTANT_FOUND`).
   - `test_gate_accepts_a_failed_repair_v1.py::test_the_repairable_fixture_really_is_repairable_and_really_is_broken` now passes `-B` to `subprocess.run` so overwriting 5-byte `x * x` with 5-byte `x + x` within the same integer wall-clock second never executes stale PEP 552 `.pyc` bytecode.

| link | status |
|---|---|
| record one exposure | TRUE |
| re-check a stored rule | TRUE, 4 mechanisms |
| detect a rule that breaks behaviour | TRUE (`rule_generalization_probe_v1`, BREAKS reachable) |
| revise on a counterexample | **TRUE, and enforced across all 10 Python + cross-language paths** |
| transfer one lesson across six languages | **TRUE when `ACTIVE` (`tree-sitter==0.20.4`), and refused across all 6 when `INVALIDATED`** |
| arbitrary new environments | Bounded by version-space identifiability (`settlement_v1`, `contrast_selection_v1`) and operator vocabulary |
| repetition → ability | FALSE (`EXPERT_FIXES_DOSE_RESPONSE_20261112_V1.json`: 2,864 fixes = 55/100 vs 1,000 fixes = 56/100) |

> A rule that is refuted and still fires is not a learning system. It is a cache with a
> comment explaining why the entry is bad.

