"""Independent acceptance tests for the generic Stage-A pre-exposure reducer.

Builder self-consistency is not independent evidence, so these tests do not
re-assert the reducer's own assumptions. They mutate a *copy* of the live
policy-compliant ledger and require each seeded fault to be killed by a named
predicate. The real qualification ledger is never written to: mutating frozen
qualification evidence would itself be contamination.
"""
import copy, hashlib, json, pathlib, shutil, tempfile, unittest
from pathlib import Path

from canonical.runtime import prequalification_stage_a_generic as stage_a_v1
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
# rank21 is the LIVE frontier rank: Stage-A independently passed, Stage-B
# instruction exposure authorized. Its ledger carries a nonzero brain_pr_hits
# that is fully classified as self-referential pre-exposure bookkeeping, so it
# is the decisive oracle for the classification model.
RANK21_TASK = "foodstuff-beta-activity"
RANK21 = 21
RANK21_LEDGER = (
    "canonical/capabilities/opus55/"
    "FOODSTUFF_BETA_ACTIVITY_RANK21_CONTAMINATION_LEDGER_V1.json"
)
RANK21_ADMISSION = (
    "canonical/capabilities/opus55/"
    "FOODSTUFF_BETA_ACTIVITY_RANK21_STAGE_A_ADMISSION_V1.json"
)
V1_SOURCE = "canonical/runtime/prequalification_stage_a_generic.py"


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
            "STAGE_A_PASS_AUTHORIZES_ONLY_ONE_OFFICIAL_INSTRUCTION_EXPOSURE",
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

    def assert_reproduces_recorded_admission(self, task, rank, ledger_rel, admission_rel):
        """A recorded admission must be reproducible from canonical code.

        Ledgers are live and legitimately mutate as a task advances past Stage A,
        so both states are asserted rather than skipped: while the ledger is still
        at Stage A the recorded verdict must be reproduced field for field, and
        once the task has advanced the reducer must refuse it, with the recorded
        artifact standing as a historical Stage-A pass.
        """
        recorded = json.loads((ROOT / admission_rel).read_text(encoding="utf-8"))
        self.assertTrue(recorded["pass"], "expected the recorded artifact to assert a pass")
        ledger = json.loads((ROOT / ledger_rel).read_text(encoding="utf-8"))
        out = evaluate(ROOT, task=task, rank=rank, ledger_path=ledger_rel)
        if ledger.get("state") == "UNEXPOSED__STAGE_A_PRE_EXPOSURE":
            self.assertEqual(out["pass"], recorded["pass"], out)
            self.assertEqual(out["authorization"], recorded["authorization"])
            self.assertEqual(out["failed_predicates"], recorded["failed_predicates"])
            # The rule label and schema are part of the recorded verdict, not
            # decoration: v2 once emitted the generic schema with the legacy
            # rank15 reducer's shorter rule wording, and a comparison that
            # skipped those two fields could not see the divergence.
            for key in ("rule", "schema"):
                if key in recorded:
                    self.assertEqual(out[key], recorded[key], key)
            self.assertEqual(
                out["task_execution_authorized"], recorded["task_execution_authorized"]
            )
        else:
            self.assertFalse(out["pass"], out)
            self.assertEqual(out["authorization"], "NONE")
            self.assertIn("QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"])
            self.assertFalse(out["task_execution_authorized"])

    def test_recorded_rank18_admission_artifact_is_reproducible(self):
        self.assert_reproduces_recorded_admission(
            TASK,
            RANK,
            LEDGER,
            "canonical/capabilities/opus55/"
            "FREECAD_IMPELLER_RANK18_STAGE_A_ADMISSION_V1.json",
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
    def test_unclassified_nonzero_hit_is_killed(self):
        for field in EXPECTED_HIT_FIELDS:
            with self.subTest(field=field):
                out = self.mutated(lambda l, f=field: self.search(l).__setitem__(f, 1))
                self.assertFalse(out["pass"])
                self.assertIn(
                    "PRIOR_EXPOSURE_HIT_CLASSIFICATION_INCOMPLETE", out["failed_predicates"]
                )

    # --- hit classification (mirrors prequalification_stage_a_generic) --------
    # A nonzero raw hit is not automatically contamination: once a frozen task
    # name is canonically recorded, later searches legitimately find
    # self-referential frontier bookkeeping. Every nonzero hit must be completely
    # classified, and any disqualifying or unclassified hit fails closed.
    def classify(self, ledger, field, count=1):
        search = self.search(ledger)
        search[field] = count
        search.setdefault("disqualifying_hits", {})
        entries = search.setdefault("non_disqualifying_hits", [])
        for index in range(count):
            entries.append(
                {
                    "counter_field": field,
                    "classification": "FROZEN_TASK_NAME_FRONTIER_BOOKKEEPING_ONLY",
                    "evidence": f"brain PR #{index + 1} body explicitly says instruction unread",
                }
            )

    def test_fully_classified_nonzero_hit_admits(self):
        out = self.mutated(lambda l: self.classify(l, "brain_pr_hits", 2))
        self.assertTrue(out["pass"], out)

    def test_partially_classified_hit_is_killed(self):
        def fault(ledger):
            self.classify(ledger, "brain_pr_hits", 1)
            self.search(ledger)["brain_pr_hits"] = 2

        out = self.mutated(fault)
        self.assertFalse(out["pass"])
        self.assertIn(
            "PRIOR_EXPOSURE_HIT_CLASSIFICATION_INCOMPLETE", out["failed_predicates"]
        )

    def test_disqualifying_hit_is_killed(self):
        def fault(ledger):
            search = self.search(ledger)
            search["brain_code_hits"] = 1
            search["disqualifying_hits"] = {"brain_code_hits": 1}

        out = self.mutated(fault)
        self.assertFalse(out["pass"])
        self.assertIn("PRIOR_EXPOSURE_DISQUALIFYING_HIT", out["failed_predicates"])

    def test_disqualifying_count_exceeding_raw_is_killed(self):
        def fault(ledger):
            search = self.search(ledger)
            search["brain_pr_hits"] = 1
            search["disqualifying_hits"] = {"brain_pr_hits": 5}

        out = self.mutated(fault)
        self.assertFalse(out["pass"])
        self.assertIn(
            "PRIOR_EXPOSURE_DISQUALIFYING_COUNT_INVALID", out["failed_predicates"]
        )

    def test_non_integer_raw_count_is_killed(self):
        out = self.mutated(
            lambda l: self.search(l).__setitem__("brain_pr_hits", "0")
        )
        self.assertFalse(out["pass"])
        self.assertIn("PRIOR_EXPOSURE_RAW_COUNT_INVALID", out["failed_predicates"])

    def test_negative_raw_count_is_killed(self):
        out = self.mutated(lambda l: self.search(l).__setitem__("brain_pr_hits", -1))
        self.assertFalse(out["pass"])
        self.assertIn("PRIOR_EXPOSURE_RAW_COUNT_INVALID", out["failed_predicates"])

    def test_classification_item_without_evidence_is_killed(self):
        def fault(ledger):
            search = self.search(ledger)
            search["brain_pr_hits"] = 1
            search["non_disqualifying_hits"] = [
                {"counter_field": "brain_pr_hits", "classification": "BOOKKEEPING_ONLY"}
            ]

        out = self.mutated(fault)
        self.assertFalse(out["pass"])
        self.assertIn(
            "PRIOR_EXPOSURE_NONDISQUALIFYING_ITEM_INVALID", out["failed_predicates"]
        )

    def test_classification_for_unknown_field_is_killed(self):
        def fault(ledger):
            search = self.search(ledger)
            search["non_disqualifying_hits"] = [
                {
                    "counter_field": "not_a_real_counter",
                    "classification": "BOOKKEEPING_ONLY",
                    "evidence": "brain PR #1",
                }
            ]

        out = self.mutated(fault)
        self.assertFalse(out["pass"])
        self.assertIn(
            "PRIOR_EXPOSURE_NONDISQUALIFYING_ITEM_INVALID", out["failed_predicates"]
        )

    def test_malformed_disqualifying_counts_are_killed(self):
        out = self.mutated(
            lambda l: self.search(l).__setitem__("disqualifying_hits", "not-a-dict")
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            "PRIOR_EXPOSURE_DISQUALIFYING_COUNTS_INVALID", out["failed_predicates"]
        )

    def test_malformed_classification_list_is_killed(self):
        out = self.mutated(
            lambda l: self.search(l).__setitem__("non_disqualifying_hits", "not-a-list")
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            "PRIOR_EXPOSURE_NONDISQUALIFYING_CLASSIFICATION_INVALID",
            out["failed_predicates"],
        )

    def test_zero_hits_need_no_classification_block(self):
        # Backward compatibility: a ledger predating the classification keys is
        # still admissible when every raw counter is zero.
        out = evaluate(self.root, task=TASK, rank=RANK, ledger_path=LEDGER)
        self.assertTrue(out["pass"], out)

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
                self.assertIn("PRIOR_EXPOSURE_RAW_COUNT_INVALID", out["failed_predicates"])

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
        self.assert_reproduces_recorded_admission(
            "satb-audio-transcription", 19, RANK19_LEDGER, RANK19_ADMISSION
        )

    def test_recorded_rank20_admission_artifact_is_reproducible(self):
        # rank20's ledger carries nonzero raw hits that are fully classified as
        # non-disqualifying frontier bookkeeping, so it is the live case that a
        # blanket "any nonzero hit is contamination" test wrongly refuses.
        self.assert_reproduces_recorded_admission(
            "vba-userform-port",
            20,
            "canonical/capabilities/opus55/"
            "VBA_USERFORM_PORT_RANK20_CONTAMINATION_LEDGER_V1.json",
            "canonical/capabilities/opus55/"
            "VBA_USERFORM_PORT_RANK20_STAGE_A_ADMISSION_V1.json",
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


def git_blob_sha1(path):
    """Exactly what `git hash-object` reports, without depending on git."""
    data = pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class Rank21LiveFrontierOracleTests(unittest.TestCase):
    """rank21 is the live frontier rank, so it is the strongest available oracle.

    Its recorded admission was produced by v1 and independently verified against
    five named properties. Those properties are re-executed here against v2, so
    the parity claim rests on upstream's own recorded verification rather than on
    this suite's assumptions.
    """

    def tree(self, fault=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for rel in SUPPORT_PATHS + (RANK21_LEDGER,):
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)
        ledger = json.loads((root / RANK21_LEDGER).read_text(encoding="utf-8"))
        if fault is not None:
            fault(ledger)
            (root / RANK21_LEDGER).write_text(
                json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        return root, ledger

    def run_v2(self, fault=None):
        root, _ = self.tree(fault)
        return evaluate(root, task=RANK21_TASK, rank=RANK21, ledger_path=RANK21_LEDGER)

    def search(self, ledger):
        return ledger["prior_exposure_search"]

    def test_live_rank21_ledger_is_admitted_for_stage_a_only(self):
        out = self.run_v2()
        recorded = json.loads((ROOT / RANK21_ADMISSION).read_text(encoding="utf-8"))
        self.assertTrue(recorded["status"].startswith("INDEPENDENT_STAGE_A_PASS"))
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["failed_predicates"], [])
        self.assertEqual(out["authorization"], "STAGE_B_INSTRUCTION_EXPOSURE_ONLY")
        self.assertEqual(
            out["task_execution_authorized"], recorded["task_execution_authorized"]
        )
        # The recorded authorization names exactly one official instruction
        # exposure and nothing else; v2 must not widen it.
        self.assertIn("ONE_OFFICIAL_INSTRUCTION_EXPOSURE", recorded["authorization"])
        self.assertIn("STAGE_B_ONLY", recorded["authorization"])

    def test_blanket_nonzero_hit_rule_would_refuse_the_live_frontier_rank(self):
        # The defect this change repairs, measured on the live frontier ledger:
        # brain_pr_hits is 1 and fully classified, so the policy-mandated
        # dict-wide "every value equals 0" test refuses a ledger the canonical
        # reducer admits and the frontier is currently authorized on.
        _, ledger = self.tree()
        search = self.search(ledger)
        self.assertEqual(search["brain_pr_hits"], 1)
        self.assertFalse(all(v == 0 for v in search.values()))
        self.assertTrue(self.run_v2()["pass"])

    def test_recorded_verified_properties_hold_in_v2(self):
        recorded = json.loads((ROOT / RANK21_ADMISSION).read_text(encoding="utf-8"))
        properties = {
            "EXACT_RANK21_LEDGER_PASSES_STAGE_A_ONLY": (None, None),
            "INSTRUCTION_READ_FAILS_CLOSED": (
                lambda l: l.__setitem__("instruction_read", True),
                "QUALIFICATION_CONTAMINATION_LEDGER",
            ),
            "UNCLASSIFIED_PR_HIT_FAILS_CLOSED": (
                lambda l: self.search(l).__setitem__("non_disqualifying_hits", []),
                "PRIOR_EXPOSURE_HIT_CLASSIFICATION_INCOMPLETE",
            ),
            "DISQUALIFYING_HIT_FAILS_CLOSED": (
                lambda l: self.search(l)["disqualifying_hits"].__setitem__(
                    "brain_pr_hits", 1
                ),
                "PRIOR_EXPOSURE_DISQUALIFYING_HIT",
            ),
            "INCOMPLETE_SEARCH_FAILS_CLOSED": (
                lambda l: self.search(l).__setitem__("search_complete", False),
                "PRIOR_EXPOSURE_SEARCH_INCOMPLETE",
            ),
        }
        # Anti-rot: if upstream records a sixth property this oracle must be
        # extended, not silently narrowed.
        unknown = [p for p in recorded["verified"] if p not in properties]
        self.assertEqual(unknown, [], "unbound recorded properties: %s" % unknown)
        for name in recorded["verified"]:
            fault, predicate = properties[name]
            with self.subTest(property=name):
                out = self.run_v2(fault)
                if predicate is None:
                    self.assertTrue(out["pass"], out)
                    self.assertFalse(out["task_execution_authorized"])
                else:
                    self.assertFalse(out["pass"], out)
                    self.assertIn(predicate, out["failed_predicates"])

    def test_v1_and_v2_agree_on_the_live_rank21_ledger(self):
        root, ledger = self.tree()
        v2 = evaluate(root, task=RANK21_TASK, rank=RANK21, ledger_path=RANK21_LEDGER)
        v1 = stage_a_v1.evaluate(
            root, RANK21_LEDGER, RANK21_TASK, RANK21, ledger["task_identity_sha256"]
        )
        shared = sorted(set(v1) & set(v2))
        self.assertTrue(shared)
        # Parity is claimed over every shared key, including the rule label, so
        # a cosmetic divergence cannot hide behind a matching verdict.
        self.assertEqual({k: v1[k] for k in shared}, {k: v2[k] for k in shared})

    def test_recorded_provenance_drift_does_not_change_the_verdict(self):
        # rank21's recorded admission cites a ledger blob that upstream later
        # mutated without refreshing the citation. Drift in a citation is
        # tolerable only while the live evidence still reproduces the recorded
        # verdict; the moment it does not, this fails closed.
        recorded = json.loads((ROOT / RANK21_ADMISSION).read_text(encoding="utf-8"))
        candidate = recorded["candidate"]
        live_ledger_blob = git_blob_sha1(ROOT / candidate["ledger"])
        drifted = live_ledger_blob != candidate["ledger_blob"]
        out = self.run_v2()
        self.assertTrue(
            out["pass"],
            "recorded provenance drift=%s and the live ledger no longer reproduces "
            "the recorded admission: recorded_blob=%s live_blob=%s"
            % (drifted, candidate["ledger_blob"], live_ledger_blob),
        )
        self.assertEqual(out["failed_predicates"], [])
        # v1 is named as the producing source; its live form must agree too.
        root, ledger = self.tree()
        v1 = stage_a_v1.evaluate(
            root, RANK21_LEDGER, RANK21_TASK, RANK21, ledger["task_identity_sha256"]
        )
        self.assertTrue(v1["pass"], v1)


if __name__ == "__main__":
    unittest.main()
