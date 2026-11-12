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

| link | status |
|---|---|
| record one exposure | TRUE |
| re-check a stored rule | TRUE, 4 mechanisms |
| detect a rule that breaks behaviour | TRUE (`rule_generalization_probe_v1`, BREAKS reachable) |
| revise on a counterexample | **TRUE, and now enforced** (was: recorded, then ignored) |
| transfer one lesson across six languages | **FALSE in this tree today** — 2 tests for it fail on `main` too |
| arbitrary new environments | FALSE, <9% / <3% unseen-site reuse in the literature |
| repetition → ability | FALSE, +16.2pp curated vs +0.0pp self-generated |

**The mechanism is now correct where it exists, and the mechanism is not where the claim needs
it.** Cross-language transfer — the closest thing in this tree to "learn it once in a new
environment" — has failing tests on `main` and has had them for at least a pass. That is the
next real target, and it is a target I can measure rather than argue about: three of them
(`test_phase3_one_python_lesson_transfers_across_all_six_other_languages`, and two others) fail
identically before and after my change, so they are a pre-existing defect, not a cost of this
fix.

> A rule that is refuted and still fires is not a learning system. It is a cache with a
> comment explaining why the entry is bad.
