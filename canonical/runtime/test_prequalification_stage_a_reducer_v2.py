"""Independent acceptance tests for the generic Stage-A pre-exposure reducer.

Builder self-consistency is not independent evidence, so these tests do not
re-assert the reducer's own assumptions. They mutate a *copy* of the live
policy-compliant ledger and require each seeded fault to be killed by a named
predicate. The real qualification ledger is never written to: mutating frozen
qualification evidence would itself be contamination.
"""
import copy, json, shutil, tempfile, unittest
from pathlib import Path

from canonical.runtime.prequalification_stage_a_reducer_v2 import (
    EXPECTED_HIT_FIELDS,
    EXPECTED_SURFACES,
    REQUIRED_BUDGET_BEHAVIORS,
    REQUIRED_BUDGET_WORKFLOWS,
    evaluate,
)

ROOT = Path(__file__).resolve().parents[2]

# rank18 is the live policy-compliant clean ledger: UNEXPOSED, search_complete,
# all eight surfaces searched, all eight hit counters zero.
TASK = "freecad-impeller"
RANK = 18
LEDGER = "canonical/capabilities/opus55/FREECAD_IMPELLER_RANK18_CONTAMINATION_LEDGER_V1.json"
# rank17 was spent and contaminated at the source boundary; rank16 was contaminated
# during Stage B. Both must keep failing closed, each for its own true reason.
SPENT_LEDGER = (
    "canonical/capabilities/opus55/DATA_ANONYMIZATION_RANK17_CONTAMINATION_LEDGER_V1.json"
)
CONTAMINATED_LEDGER = (
    "canonical/capabilities/opus55/"
    "SESSION_WINDOW_DEBUG_RANK16_CONTAMINATION_LEDGER_V1.json"
)

# Every artifact the reducer reads, so a mutated tree can be built without
# touching canonical state.
SUPPORT_PATHS = (
    "canonical/capabilities/opus55/TB4_V5_TARGET_VERSION_LOCK_V1.json",
    "canonical/capabilities/opus55/GENERIC_EXECUTION_SURFACE_CERTIFICATE_20261001_V1.json",
    "canonical/capabilities/opus55/INDEPENDENT_ACCEPTANCE_MODEL_EVIDENCE_V1.json",
    "canonical/capabilities/opus55/REQUIREMENT_GRAPH_KERNEL_001.json",
    "canonical/capabilities/opus55/TB4_V5_STAGE1_STATISTICAL_PROMOTION_PLAN_V1.json",
    "canonical/governance/DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V1.json",
    "canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json",
    "canonical/governance/PER_ACTION_CANONICAL_LEASE_REVALIDATION_VERIFICATION_20261001_V1.json",
    "canonical/governance/RUNNER_TOTAL_STAGE_C_BUDGET_GUARD_VERIFICATION_20261001_V1.json",
)
BUDGET_EVIDENCE = (
    "canonical/governance/"
    "RUNNER_TOTAL_STAGE_C_BUDGET_GUARD_VERIFICATION_20261001_V1.json"
)
LEASE_EVIDENCE = (
    "canonical/governance/"
    "PER_ACTION_CANONICAL_LEASE_REVALIDATION_VERIFICATION_20261001_V1.json"
)
RANK19_LEDGER = (
    "canonical/capabilities/opus55/"
    "SATB_AUDIO_TRANSCRIPTION_RANK19_CONTAMINATION_LEDGER_V1.json"
)
RANK19_ADMISSION = (
    "canonical/capabilities/opus55/"
    "SATB_AUDIO_TRANSCRIPTION_RANK19_STAGE_A_ADMISSION_V1.json"
)


class StageAReducerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in SUPPORT_PATHS + (LEDGER,):
            dst = self.root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)
        self.ledger = json.loads((self.root / LEDGER).read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    def write_ledger(self, ledger):
        (self.root / LEDGER).write_text(
            json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def mutated(self, fn):
        ledger = copy.deepcopy(self.ledger)
        fn(ledger)
        self.write_ledger(ledger)
        return evaluate(self.root, task=TASK, rank=RANK, ledger_path=LEDGER)

    def search(self, ledger):
        return ledger["prior_exposure_search"]

    # --- live canonical state -------------------------------------------------
    def test_live_policy_compliant_ledger_passes(self):
        out = evaluate(ROOT, task=TASK, rank=RANK, ledger_path=LEDGER)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["authorization"], "STAGE_B_INSTRUCTION_EXPOSURE_ONLY")
        self.assertEqual(out["failed_predicates"], [])

    def test_stage_a_never_authorizes_execution(self):
        out = evaluate(ROOT, task=TASK, rank=RANK, ledger_path=LEDGER)
        self.assertFalse(out["task_execution_authorized"])
        self.assertIn(
            "STAGE_A_PASS_AUTHORIZES_ONLY_OFFICIAL_INSTRUCTION_EXPOSURE",
            out["rule"],
        )

    def test_spent_rank17_ledger_fails_closed(self):
        out = evaluate(
            ROOT,
            task="data-anonymization",
            rank=17,
            ledger_path=SPENT_LEDGER,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["authorization"], "NONE")
        # Must fail because the task is genuinely spent/contaminated, never
        # because a compliant eight-surface search is unreadable.
        self.assertIn("QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"])

    def test_contaminated_rank16_ledger_fails_closed(self):
        out = evaluate(
            ROOT,
            task="session-window-debug",
            rank=16,
            ledger_path=CONTAMINATED_LEDGER,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["authorization"], "NONE")
        self.assertIn("QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"])

    def test_recorded_rank18_admission_artifact_is_reproducible(self):
        # A canonical artifact on main asserts this pass. If the reducer cannot
        # reproduce a recorded admission, the recorded admission is unverifiable.
        recorded = json.loads(
            (
                ROOT
                / "canonical/capabilities/opus55/"
                "FREECAD_IMPELLER_RANK18_STAGE_A_ADMISSION_V1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(recorded["pass"], "expected the recorded artifact to assert a pass")
        out = evaluate(ROOT, task=TASK, rank=RANK, ledger_path=LEDGER)
        self.assertEqual(out["pass"], recorded["pass"])
        self.assertEqual(out["authorization"], recorded["authorization"])
        self.assertEqual(out["failed_predicates"], recorded["failed_predicates"])
        self.assertEqual(
            out["task_execution_authorized"], recorded["task_execution_authorized"]
        )

    # --- the repaired defect: completeness metadata is provenance, not a hit --
    def test_policy_mandated_metadata_is_not_counted_as_exposure(self):
        # search_complete and searched_surfaces are mandated by the eight-surface
        # policy, so a compliant ledger necessarily carries non-integer values
        # inside prior_exposure_search. A blanket "every value must equal 0" test
        # therefore made every compliant ledger unsatisfiable.
        search = self.search(self.ledger)
        self.assertIs(search["search_complete"], True)
        self.assertEqual(sorted(search["searched_surfaces"]), sorted(EXPECTED_SURFACES))
        non_hit_values = [
            v for k, v in search.items() if not k.endswith("_hits")
        ]
        self.assertTrue(
            any(isinstance(v, bool) or isinstance(v, list) for v in non_hit_values),
            "expected mandated completeness metadata inside prior_exposure_search",
        )
        out = evaluate(self.root, task=TASK, rank=RANK, ledger_path=LEDGER)
        self.assertTrue(out["pass"], out)

    def test_additional_self_referential_metadata_does_not_fail(self):
        # Self-referential frontier PR metadata is provenance about Brain's own
        # search, not exposure to task content.
        def fault(ledger):
            self.search(ledger)[
                "non_disqualifying_self_referential_brain_pr_metadata"
            ] = [{"pr": 999, "classification": "FRONTIER_METADATA_ONLY"}]

        out = self.mutated(fault)
        self.assertTrue(out["pass"], out)

    # --- seeded faults: each must be killed by its own named predicate --------
    def test_nonzero_hit_counter_is_killed(self):
        for field in EXPECTED_HIT_FIELDS:
            with self.subTest(field=field):
                out = self.mutated(lambda l, f=field: self.search(l).__setitem__(f, 1))
                self.assertFalse(out["pass"])
                self.assertIn("PRIOR_EXPOSURE_SEARCH_NOT_CLEAN", out["failed_predicates"])

    def test_incomplete_search_flag_is_killed(self):
        out = self.mutated(lambda l: self.search(l).__setitem__("search_complete", False))
        self.assertFalse(out["pass"])
        self.assertIn("PRIOR_EXPOSURE_SEARCH_INCOMPLETE", out["failed_predicates"])

    def test_missing_hit_field_is_killed(self):
        for field in EXPECTED_HIT_FIELDS:
            with self.subTest(field=field):
                out = self.mutated(lambda l, f=field: self.search(l).pop(f))
                self.assertFalse(out["pass"])
                self.assertIn(
                    "PRIOR_EXPOSURE_SEARCH_FIELDS_MISSING", out["failed_predicates"]
                )
                # A missing counter must never be read as a zero counter.
                self.assertIn("PRIOR_EXPOSURE_SEARCH_NOT_CLEAN", out["failed_predicates"])

    def test_missing_surface_is_killed(self):
        for surface in EXPECTED_SURFACES:
            with self.subTest(surface=surface):
                def fault(ledger, s=surface):
                    search = self.search(ledger)
                    search["searched_surfaces"] = [
                        x for x in search["searched_surfaces"] if x != s
                    ]

                out = self.mutated(fault)
                self.assertFalse(out["pass"])
                self.assertIn(
                    "PRIOR_EXPOSURE_SEARCH_SURFACES_INCOMPLETE", out["failed_predicates"]
                )

    def test_absent_search_block_is_killed(self):
        out = self.mutated(lambda l: l.pop("prior_exposure_search"))
        self.assertFalse(out["pass"])
        self.assertIn("PRIOR_EXPOSURE_SEARCH_MISSING", out["failed_predicates"])

    def test_instruction_read_is_killed(self):
        out = self.mutated(lambda l: l.__setitem__("instruction_read", True))
        self.assertFalse(out["pass"])
        self.assertIn("QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"])

    def test_disqualifying_exposure_event_is_killed(self):
        out = self.mutated(
            lambda l: l.__setitem__(
                "disqualifying_exposure_events", [{"kind": "SEEDED_FAULT"}]
            )
        )
        self.assertFalse(out["pass"])
        self.assertIn("QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"])

    def test_not_clean_for_stage_b_is_killed(self):
        out = self.mutated(lambda l: l.__setitem__("clean_for_stage_b_exposure", False))
        self.assertFalse(out["pass"])
        self.assertIn("QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"])

    def test_wrong_task_identity_is_killed(self):
        out = evaluate(self.root, task="wrong-task", rank=RANK, ledger_path=LEDGER)
        self.assertFalse(out["pass"])
        self.assertIn("QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"])

    def test_wrong_rank_is_killed(self):
        out = evaluate(self.root, task=TASK, rank=RANK + 1, ledger_path=LEDGER)
        self.assertFalse(out["pass"])
        self.assertIn("QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"])

    # --- policy binding -------------------------------------------------------
    def test_policy_without_eight_surface_requirement_fails_closed(self):
        rel = "canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json"
        policy = json.loads((self.root / rel).read_text(encoding="utf-8"))
        required = policy["staged_admission"]["stage_a_pre_exposure"]["required"]
        required.remove("COMPLETE_8_SURFACE_PRIOR_EXPOSURE_SEARCH_INCLUDING_BRAIN_PRS")
        (self.root / rel).write_text(json.dumps(policy, indent=2), encoding="utf-8")
        out = evaluate(self.root, task=TASK, rank=RANK, ledger_path=LEDGER)
        self.assertFalse(out["pass"])
        self.assertIn("STAGE_A_POLICY_INCOMPLETE", out["failed_predicates"])

    def test_benchmark_ref_drift_fails_closed(self):
        rel = "canonical/capabilities/opus55/TB4_V5_TARGET_VERSION_LOCK_V1.json"
        lock = json.loads((self.root / rel).read_text(encoding="utf-8"))
        lock["benchmark_ref"] = "0" * 40
        (self.root / rel).write_text(json.dumps(lock, indent=2), encoding="utf-8")
        out = evaluate(self.root, task=TASK, rank=RANK, ledger_path=LEDGER)
        self.assertFalse(out["pass"])
        self.assertIn("TARGET_VERSION_LOCK", out["failed_predicates"])

    # --- parity with the v1 generic reducer -----------------------------------
    # v2 enforced neither of these, which made it a fail-open admission path for
    # exactly the escape that let rank18 spend one execution lease twice.
    def mutate_evidence(self, rel, fn):
        path = self.root / rel
        payload = json.loads(path.read_text(encoding="utf-8"))
        fn(payload)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return evaluate(self.root, task=TASK, rank=RANK, ledger_path=LEDGER)

    def test_recorded_rank19_admission_artifact_is_reproducible(self):
        recorded = json.loads((ROOT / RANK19_ADMISSION).read_text(encoding="utf-8"))
        self.assertTrue(recorded["pass"], "expected the recorded artifact to assert a pass")
        out = evaluate(ROOT, task="satb-audio-transcription", rank=19, ledger_path=RANK19_LEDGER)
        self.assertEqual(out["pass"], recorded["pass"])
        self.assertEqual(out["authorization"], recorded["authorization"])
        self.assertEqual(out["failed_predicates"], recorded["failed_predicates"])
        self.assertEqual(
            out["task_execution_authorized"], recorded["task_execution_authorized"]
        )

    def test_absent_budget_guard_evidence_fails_closed(self):
        (self.root / BUDGET_EVIDENCE).unlink()
        out = evaluate(self.root, task=TASK, rank=RANK, ledger_path=LEDGER)
        self.assertFalse(out["pass"])
        self.assertIn(
            "TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD", out["failed_predicates"]
        )

    def test_unmerged_budget_guard_fails_closed(self):
        out = self.mutate_evidence(
            BUDGET_EVIDENCE, lambda d: d.__setitem__("status", "PROPOSED__NOT_MERGED")
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            "TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD", out["failed_predicates"]
        )

    def test_missing_required_budget_behavior_fails_closed(self):
        for behavior in sorted(REQUIRED_BUDGET_BEHAVIORS):
            with self.subTest(behavior=behavior):
                def fault(payload, b=behavior):
                    payload["repair"]["behavior"] = [
                        x for x in payload["repair"]["behavior"] if x != b
                    ]

                out = self.mutate_evidence(BUDGET_EVIDENCE, fault)
                self.assertFalse(out["pass"])
                self.assertIn(
                    "TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD",
                    out["failed_predicates"],
                )

    def test_unverified_budget_workflow_fails_closed(self):
        for workflow in sorted(REQUIRED_BUDGET_WORKFLOWS):
            with self.subTest(workflow=workflow):
                def fault(payload, w=workflow):
                    for entry in payload["independent_verification"]:
                        if entry.get("workflow") == w:
                            entry["conclusion"] = "failure"

                out = self.mutate_evidence(BUDGET_EVIDENCE, fault)
                self.assertFalse(out["pass"])
                self.assertIn(
                    "TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD",
                    out["failed_predicates"],
                )

    def test_absent_lease_revalidation_evidence_fails_closed(self):
        (self.root / LEASE_EVIDENCE).unlink()
        out = evaluate(self.root, task=TASK, rank=RANK, ledger_path=LEDGER)
        self.assertFalse(out["pass"])
        self.assertIn(
            "PER_ACTION_CANONICAL_LEASE_REVALIDATION", out["failed_predicates"]
        )

    def test_failed_lease_revalidation_test_fails_closed(self):
        out = self.mutate_evidence(
            LEASE_EVIDENCE,
            lambda d: d["runner"].__setitem__("verification_tests_failed", 1),
        )
        self.assertFalse(out["pass"])
        self.assertIn("PER_ACTION_CANONICAL_LEASE_REVALIDATION", out["failed_predicates"])

    def test_lease_revalidation_for_a_later_rank_still_admits(self):
        # Regression against frozen-constant rot: the status names the rank that
        # first blocked the escape class. Re-issuing the artifact for a later rank
        # must not spuriously fail Stage A closed.
        out = self.mutate_evidence(
            LEASE_EVIDENCE,
            lambda d: d.__setitem__(
                "status", "VERIFIED_AND_MERGED__RANK22_REVOCATION_ESCAPE_CLASS_BLOCKED"
            ),
        )
        self.assertTrue(out["pass"], out)


if __name__ == "__main__":
    unittest.main()
