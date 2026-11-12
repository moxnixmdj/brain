# Wiring the Four Disconnected Skill-Verification Gates into `VerifiedSkillStore`

**2026-11-12.** Base `d677e54e`. Branch `arena/60a8e979-brain`. Authority: **NONE**.
`truth.achieved` = `false`. Zero model calls in every result-bearing path.

---

## 1. The Defect Recorded in `rule_generalization_probe_v1.py`

In `canonical/tools/rule_generalization_probe_v1.py`, the docstring explicitly noted:

> *"Three of the four checks this session shipped were never called by the learn path at all --
> they existed and measured nothing. A check whose success case is 'I didn't look' is the same
> failure in a new place."*

Auditing `canonical/swe_kernel/` and `canonical/tools/` on `d677e54e` revealed that **all four**
verification modules (`skill_recheck_v1`, `skill_precondition_presence_v1`,
`skill_sequence_verify_v1`, and `rule_generalization_probe_v1`) were disconnected or partially
disconnected from `VerifiedSkillStore` (`canonical/swe_kernel/verified_skill_crystallizer_v1.py`):

1. **`skill_recheck_v1.py` (`ON CONFLICT` & bundle-merge `taught_sources` loss + recall bypass):**
   - `crystallize_code_fix` constructed `rule['provenance']['taught_sources']`, but its SQLite
     upsert (`ON CONFLICT(skill_id) DO UPDATE SET verified_hits = ..., provenance_json = ...`)
     **never updated `pattern_json`**.
   - Consequently, re-teaching an already-seeded rule or teaching a second distinct example
     `(before_2, after_2)` for the same `skill_id` silently discarded the new `taught_sources`.
   - `import_bundle` similarly merged `provenance_json` and `INVALIDATED`/`counterexamples`, but
     never merged `provenance.taught_sources` into `retained` when `existing is not None`.
   - `recall_and_apply_verified` never checked `skill_recheck_v1.recheck(rule)`, so a stale rule
     whose `recheck(rule)["verdict"] == "FAIL"` still fired at recall time.
   - `canonical/astra_runtime/skills/VERIFIED_SKILLS_BUNDLE_V1.json` carried `0/5`
     `taught_sources`, causing `auditability_report_v1.py` layer `skills` to report `0/5 (0.0%)`
     checkable (`no taught source 5`).
2. **`skill_precondition_presence_v1.py` (0 callers in `canonical/` and 0 tests):**
   - `defect_is_present` / `gate` (`PRESENT`, `ABSENT`, `REFUSED`, `UNOBSERVABLE`) was never
     called by `crystallize_code_fix` or `recall_and_apply_verified`, and had no test file.
3. **`skill_sequence_verify_v1.py` (0 callers in `VerifiedSkillStore`):**
   - Two opposing `ACTIVE` rules (`<= -> <` and `< -> <=`) could revert a file to its starting
     state across multi-step repair because `recall_and_apply_verified` did not track
     `prior_sources` and `VerifiedSkillStore` had no sequence verification or interference-audit
     methods.
4. **`rule_generalization_probe_v1.py` (0 callers in `VerifiedSkillStore`):**
   - `probe_rule` (`HOLDS`, `BREAKS`, `NOT_APPLICABLE`, `REFUSED`, `NO_RULE`) was never called by
     `crystallize_code_fix` when an executable oracle + probe points were supplied, and
     `VerifiedSkillStore` had no method (`probe_skill_on_victim`) to execute a stored skill on a
     held-out victim and invalidate it when `verdict == "BREAKS"`.

---

## 2. What Was Repaired and Measured

| Verification Gate | Before (`d677e54e`) | After |
|---|---|---|
| `skill_recheck_v1` on 2nd example (`ON CONFLICT`) & `import_bundle` | `sources_checked = 1` (2nd example dropped) | **`sources_checked = 2`** (`_merge_taught_sources` unions `taught_sources`) |
| `skill_recheck_v1` at `recall_and_apply_verified` | Stale rule with `recheck == FAIL` still fires | **Blocked** (`None` returned when `recheck(rule)["verdict"] == "FAIL"`) |
| Shipped `VERIFIED_SKILLS_BUNDLE_V1.json` (`auditability_report_v1` `skills` layer) | `0/5 (0.0%)` checkable (`ABSENT 5`) | **`5/5 (100.0%)` checkable (`PASS 5, FAIL 0, ABSENT 0`)** |
| `skill_precondition_presence_v1` in `crystallize_code_fix` & `recall_and_apply_verified` | 0 callers, 0 tests | Refuses `ABSENT`/`REFUSED`/`UNOBSERVABLE` at learn & apply; 7 tests in `test_skill_precondition_presence_v1.py` |
| `skill_sequence_verify_v1` in `VerifiedSkillStore` | 0 callers | `prior_sources` blocks 2-step reversions; `apply_verified_sequence` & `audit_sequence_interference` wired |
| `rule_generalization_probe_v1` in `VerifiedSkillStore` | 0 callers | `crystallize_code_fix(oracle=..., probes=...)` refuses `BREAKS`; `probe_skill_on_victim` invalidates on `BREAKS` |

---

## 3. Verification Commands

```bash
python3 canonical/tools/learn_path_verification_wiring_v1.py --json
python3 -m canonical.swe_kernel.skill_recheck_v1
python3 -m pytest -q canonical/tests/test_skill_precondition_presence_v1.py canonical/tests/test_learn_path_verification_wiring_v1.py
python3 canonical/runtime/verify_brain_unified_model_v1.py
python3 execution_guard/repo_integrity_guard_v1.py
```
