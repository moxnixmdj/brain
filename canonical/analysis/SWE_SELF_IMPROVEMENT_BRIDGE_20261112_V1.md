# Bridging Executable SWE Code Repair to the Formal Self-Improvement Loop (2026-11-12)

## 1. The Integration Gap Identified in `THE_HONEST_STATUS.md`

`THE_HONEST_STATUS.md` and `canonical/analysis/WHY_CANT_WE_DO_THIS_NOW_20261112_V1.md`
identified why the repository's two learning subsystems could not operate as a single loop:

1. **`VerifiedSkillStore` (`canonical/swe_kernel/verified_skill_crystallizer_v1.py`):**
   Anti-unifies concrete `(before_snippet, after_snippet)` code repairs into parameterized AST/token
   rewrite rules, verifies them against a scoped `TEST_SUITE` contract, and (since PR `#6755`)
   gates learn and recall with `skill_recheck_v1`, `skill_precondition_presence_v1`,
   `skill_sequence_verify_v1`, and `rule_generalization_probe_v1`.
2. **`autonomous_verified_self_improvement_v1.py` + `universal_verified_adaptive_solver_v12.py`:**
   Executes formal capability graphs with content-addressed `effect_semantics_binding` receipts,
   authenticates episode traces via `universal_solver_episode_verification_authenticator_v1.py`,
   induces cross-scope `PROJECT_BRAIN_EXECUTABLE_SKILL_PROGRAM_V7` candidates when two verified
   episodes share the same `program_sha256`, authenticates skills via
   `executable_skill_verification_authenticator_v1.py`, admits them to the Pareto frontier in
   `SELF_IMPROVEMENT_STATE_V1`, and reuses active skills (`reuse_first=True`) to prune distractor
   capabilities on subsequent problems.

Neither subsystem called the other. `THE_HONEST_STATUS.md` specified the exact five-step milestone
required to connect them:

> *"The first step is to pick ONE simple coding task and:
> 1. Define it as a formal problem
> 2. Create the verification infrastructure (test suite)
> 3. Run it through the solver
> 4. Integrate the result
> 5. Verify that a skill gets induced"*

---

## 2. Architecture of `canonical/swe_kernel/swe_self_improvement_bridge_v1.py`

`canonical/swe_kernel/swe_self_improvement_bridge_v1.py` connects `VerifiedSkillStore` and
subprocess Python `unittest` verification directly to `universal_verified_adaptive_solver_v12`
and `autonomous_verified_self_improvement_v1.run_learning_episode`:

1. **Subprocess `TEST_SUITE` Verifier (`make_python_unittest_verifier`):**
   Writes the candidate Python module and `unittest` suite to an isolated temporary directory,
   executes `unittest` in a fresh Python subprocess, and returns a scoped
   `VerificationResult(kind="TEST_SUITE", scope_id=scope_id)` with exact `test_count`,
   `returncode`, `measurement_program_sha256`, `measurement_spec_sha256`, and `snapshot_sha256`.
2. **Fail-Closed Baseline Check:**
   Executes the `unittest` suite on `before_code` first and refuses the episode
   (`REFUSED__FAILING_TEST_BASELINE_REQUIRED`) unless `before_code` genuinely fails (`passed=False`
   and `test_count > 0`).
3. **Code-Level Learn or Cross-Scope Recall (`VerifiedSkillStore`):**
   - When `candidate_after_code` is provided (teaching episode), calls
     `VerifiedSkillStore.crystallize_code_fix(..., contract={"schema_version": 1, "verification_kind": "TEST_SUITE", "scope_id": scope_id, ...})`,
     which verifies the failing baseline, passing candidate, mutated twin rejection,
     `rule_generalization_probe_v1` oracle probes (when supplied), and `skill_recheck_v1`.
   - When `candidate_after_code is None` (transfer episode), calls
     `VerifiedSkillStore.recall_and_apply_verified(..., required_verification_kind="TEST_SUITE", scope_id=scope_id, allow_cross_scope_transfer=True)`
     to synthesize `patched_code` from previously crystallized rules and verify it against the new
     scope's subprocess `unittest` suite.
4. **Formal Capability Wrapping & Content-Addressed Handshake (`build_formal_swe_problem`):**
   Wraps the verified code repair and subprocess test-suite execution as a formal 2-step capability
   chain (`swe.apply_parameterized_repair` $\to$ `swe.verify_scoped_test_suite`, plus a distractor
   capability `swe.distractor_noop_lint`) and runs
   `autonomous_verified_self_improvement_v1.run_learning_episode(...)` with content-addressed
   SHA-1 git-blob receipts (`git_blob_id(..., object_format="sha1")`).

---

## 3. Measured Results (`python3 canonical/swe_kernel/swe_self_improvement_bridge_v1.py --json`)

### 3.1 Positive 3-Episode Loop (Teach $\to$ Cross-Scope Induction $\to$ Unseen Transfer)

| Episode | Scope | Input Task | `VerifiedSkillStore` Action | Subprocess `unittest` | Formal Self-Improvement Outcome | `verified_episode_count` | `active_skill_count` |
|---|---|---|---|---|---|---|---|
| `ep_swe_1` | `scope_a` | `discount(price)` + taught fix | Crystallizes `skill_54cbfc801c82ee777bf3a0f4` (`recheck=PASS`, `oracle_probe=HOLDS`) | `0/2 -> 2/2` (`rc=0`) | `VERIFIED_EPISODE_PERSISTED__MORE_EVIDENCE_NEEDED_FOR_SKILL` | `1` | `0` |
| `ep_swe_2` | `scope_b` | `apply_markdown(amount)` (`candidate_after_code=None`) | Recalls `skill_54cbfc801c82ee777bf3a0f4` across scopes | `0/2 -> 2/2` (`rc=0`) | Induces & authenticates `skill:dd9f1d8f84314ca8c51ccb841ca74f19782f78757ce2eb499ec187e85c6bd748` (`VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE`) | `2` | `1` |
| `ep_swe_3` | `scope_c` (unseen) | `net_payout(gross)` (`candidate_after_code=None`) | Recalls `skill_54cbfc801c82ee777bf3a0f4` across scopes | `0/2 -> 2/2` (`rc=0`) | Reuses active Pareto skill (`reuse_first=True`, `fallback_used=False`, prunes distractor `3 -> 2` caps, `reuse.successes=1`) | `3` | `1` |

### 3.2 Negative Counterfactuals (Fail-Closed Verification Boundary)

Consistent with 2025–2026 findings on test-blindness and single-example overfitting (*SWE Refactor
Bench*, `arXiv:2608.23564` Stage III executable counterexamples; *CMU-S3D-25-113* Spell/MELT),
four negative counterfactuals verify that invalid or overfitted repairs cannot mint episode or
skill receipts:

| Counterfactual | Defect Injected | Bridge Verdict | Verified Episodes Minted | Verified Skills Minted |
|---|---|---|---|---|
| `cf1_broken_candidate` | Candidate patch (`price * 10`) fails `unittest` suite | `REFUSED__CRYSTALLIZE_FAILED:TRAINING_VERIFICATION_FAILED` | `0` | `0` |
| `cf2_overfit_constant` | Hardcoded-constant patch (`price - 10`) passes weak 1-case training test (`discount(100) == 90`) but fails held-out `rule_generalization_probe_v1` on `(50, 200, 0)` | `REFUSED__CRYSTALLIZE_FAILED:ORACLE_PROBE_BREAKS:3_OF_4_FAILED` | `0` | `0` |
| `cf3_passing_baseline` | `before_code` already passes `unittest` suite | `REFUSED__FAILING_TEST_BASELINE_REQUIRED` | `0` | `0` |
| `cf4_corrupted_rule_recall` | Stored `taught_sources` in SQLite corrupted before unseen transfer recall | Blocked by `skill_recheck_v1` (`REFUSED__NO_VERIFIED_SKILL_RECALLED`) | `0` | `0` |

---

## 4. Verification Commands

```bash
python3 canonical/swe_kernel/swe_self_improvement_bridge_v1.py --json
pytest canonical/tests/test_swe_self_improvement_bridge_v1.py -q
```
