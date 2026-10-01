"""Independent acceptance tests for the generic Stage-A pre-exposure reducer.

Builder self-consistency is not independent evidence, so these tests do not
re-assert the reducer's own assumptions. They mutate a *copy* of the live
policy-compliant ledger and require each seeded fault to be killed by a named
predicate. The real qualification ledger is never written to: mutating frozen
qualification evidence would itself be contamination.
"""
import copy, hashlib, json, pathlib, re, shutil, tempfile, unittest
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


# Ledgers that read UNEXPOSED__STAGE_A_PRE_EXPOSURE while their own rank's
# Stage-B/Stage-C artifacts and leases attest exposure or spend. Pinned by
# test_uncorroborated_clean_ledgers_are_exactly_the_documented_ones; see its
# docstring for why this change does not rewrite them.
UNCORROBORATED_CLEAN_LEDGERS = {"freecad-impeller"}

CLEAN_STATE = "UNEXPOSED__STAGE_A_PRE_EXPOSURE"
OPUS55 = "canonical/capabilities/opus55"
HIERARCHY = "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json"
POLICY = "canonical/governance/PREQUALIFICATION_FAILURE_IMMUNITY_V1.json"


def recorded_admissions():
    """Every recorded Stage-A admission in the tree, paired with its ledger.

    Discovered rather than hardcoded. The frontier advances continuously and a
    recorded ledger legitimately mutates as its task moves past Stage A, so an
    oracle pinned to "rank N is live and admitted" rots within hours: rank21 was
    the live admitted rank while this suite was being written and was
    contaminated by post-Stage-B external discovery before it was pushed.
    """
    entries = []
    for admission in sorted((ROOT / OPUS55).glob("*STAGE_A_ADMISSION*.json")):
        doc = json.loads(admission.read_text(encoding="utf-8"))
        candidate = doc.get("candidate") or {}
        ledger_rel = candidate.get("ledger")
        if not isinstance(ledger_rel, str) or not ledger_rel:
            ledger_rel = admission.relative_to(ROOT).as_posix().replace(
                "_STAGE_A_ADMISSION", "_CONTAMINATION_LEDGER"
            )
        if not (ROOT / ledger_rel).is_file():
            continue
        ledger = json.loads((ROOT / ledger_rel).read_text(encoding="utf-8"))
        status = str(doc.get("status") or "")
        rank = ledger.get("rank")
        if rank is None:
            rank = doc.get("rank")
        entries.append(
            {
                "admission": admission.relative_to(ROOT).as_posix(),
                "ledger": ledger_rel,
                "doc": doc,
                "ledger_doc": ledger,
                # Two encodings of a recorded pass exist in the tree: the generic
                # verdict schema carries pass:true, the per-rank evidence schemas
                # carry a status instead. Both are honoured.
                "recorded_pass": doc.get("pass") is True
                or status.startswith("INDEPENDENT_STAGE_A_PASS"),
                "task": ledger.get("task") or doc.get("task"),
                "rank": rank,
                "clean": ledger.get("state") == CLEAN_STATE,
            }
        )
    return entries


class RecordedStageAOracleTests(unittest.TestCase):
    """Re-execute the tree's own recorded Stage-A claims against the reducer.

    Every recorded admission artifact is an independent verification claim. These
    tests convert those claims into executable checks so the fail-closed and
    parity properties rest on evidence the repository already recorded rather
    than on assumptions this suite invented.

    Nothing here rewrites or reconstructs a ledger. A ledger that has been
    exposed, spent or contaminated carries real disqualifying evidence --
    task_specific_web_or_repo_search, disqualifying_exposure_events,
    clean_for_stage_b_exposure -- and erasing those fields to force the recorded
    pass to reproduce would fabricate the very evidence the admission exists to
    attest. So behavior properties are re-executed against the live clean ledger,
    content properties against the ledger that recorded them, and a recorded pass
    whose ledger has advanced is asserted to be truthfully refused instead.
    """

    # --- harness -----------------------------------------------------------
    def tree(self, ledger_rel, ledger=None, drop=()):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for rel in tuple(SUPPORT_PATHS) + (ledger_rel,):
            if rel in drop:
                continue
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if rel == ledger_rel and ledger is not None:
                dst.write_text(
                    json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
            else:
                shutil.copyfile(ROOT / rel, dst)
        return root

    def clean_entry(self):
        """The live ledger still at Stage A: real clean evidence, not a fixture."""
        clean = [e for e in recorded_admissions() if e["clean"] and e["rank"] is not None]
        if not clean:
            self.skipTest(
                "no live ledger is still at Stage A, so there is no clean evidence "
                "to re-execute the recorded fail-closed properties against"
            )
        return max(clean, key=lambda e: int(e["rank"]))

    def verdict(self, entry, fault=None, drop=()):
        ledger = copy.deepcopy(entry["ledger_doc"])
        if fault is not None:
            fault(ledger)
        root = self.tree(entry["ledger"], ledger=ledger, drop=drop)
        return evaluate(
            root, task=entry["task"], rank=int(entry["rank"]), ledger_path=entry["ledger"]
        )

    def search(self, ledger):
        return ledger["prior_exposure_search"]

    def classify(self, ledger, field="brain_pr_hits", count=1):
        search = self.search(ledger)
        search[field] = count
        search.setdefault("disqualifying_hits", {f: 0 for f in EXPECTED_HIT_FIELDS})
        entries = search.setdefault("non_disqualifying_hits", [])
        for index in range(count):
            entries.append(
                {
                    "counter_field": field,
                    "classification": "PREEXPOSURE_LEDGER_AND_SEARCH_BOOKKEEPING_ONLY",
                    "evidence": "brain PR #%d body explicitly says instruction unread"
                    % (index + 1),
                }
            )

    def unclassify(self, ledger, field="brain_pr_hits"):
        search = self.search(ledger)
        search[field] = 1
        search["disqualifying_hits"] = {f: 0 for f in EXPECTED_HIT_FIELDS}
        search["non_disqualifying_hits"] = []

    def disqualify(self, ledger, field="brain_pr_hits"):
        search = self.search(ledger)
        search[field] = 1
        search["disqualifying_hits"] = {f: 0 for f in EXPECTED_HIT_FIELDS}
        search["disqualifying_hits"][field] = 1
        search["non_disqualifying_hits"] = []

    def accounted(self, search, field):
        """How much of a raw counter is explained by explicit classification."""
        raw = search.get(field) or 0
        disqualifying = (search.get("disqualifying_hits") or {}).get(field, 0)
        nondisqualifying = len(
            [
                item
                for item in (search.get("non_disqualifying_hits") or [])
                if isinstance(item, dict) and item.get("counter_field") == field
            ]
        )
        return raw, disqualifying + nondisqualifying, disqualifying

    # --- the recorded verdicts ---------------------------------------------
    def test_every_recorded_admission_is_reproduced_or_truthfully_refused(self):
        entries = recorded_admissions()
        self.assertTrue(entries, "no recorded Stage-A admissions discovered")
        for entry in entries:
            with self.subTest(admission=entry["admission"]):
                out = evaluate(
                    ROOT,
                    task=entry["task"],
                    rank=int(entry["rank"]),
                    ledger_path=entry["ledger"],
                )
                self.assertFalse(out["task_execution_authorized"], out)
                if entry["clean"]:
                    # Still at Stage A: the recorded verdict must be reproducible.
                    self.assertEqual(out["pass"], entry["recorded_pass"], out)
                    if entry["recorded_pass"]:
                        self.assertEqual(out["failed_predicates"], [])
                        self.assertEqual(
                            out["authorization"], "STAGE_B_INSTRUCTION_EXPOSURE_ONLY"
                        )
                else:
                    # Advanced past Stage A: refusal is the truthful verdict and
                    # the recorded pass stands as history.
                    self.assertFalse(out["pass"], out)
                    self.assertEqual(out["authorization"], "NONE")
                    self.assertIn(
                        "QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"]
                    )

    # --- the recorded properties -------------------------------------------
    BEHAVIOR_PROPERTIES = {
        "ALL_EIGHT_EXPOSURE_SURFACES_PRESENT_AND_ZERO",
        "BRAIN_PR_HIT_FAILS_CLOSED",
        "CORRECTED_RAW_VS_DISQUALIFYING_HIT_CLASSIFICATION_PASSES",
        "CURRENT_STAGE_A_POLICY_COMPLETE",
        "DISQUALIFYING_HIT_FAILS_CLOSED",
        "DISQUALIFYING_PRIOR_HIT_FAILS_CLOSED",
        "INCOMPLETE_SEARCH_FAILS_CLOSED",
        "INCOMPLETE_SEARCH_FLAG_FAILS_CLOSED",
        "INSTRUCTION_READ_FAILS_CLOSED",
        "MISSING_BRAIN_PR_SURFACE_FAILS_CLOSED",
        "TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD_PRESENT",
        "UNCLASSIFIED_PR_HIT_FAILS_CLOSED",
        "UNCLASSIFIED_PRIOR_HIT_FAILS_CLOSED",
    }
    CONTENT_PROPERTIES = {
        "ALL_EIGHT_DISQUALIFYING_EXPOSURE_COUNTS_ZERO",
        "ALL_NONZERO_RAW_PR_HITS_EXPLICITLY_CLASSIFIED_NON_DISQUALIFYING",
        "INSTRUCTION_UNREAD",
        "TASK_COMMAND_UNEXECUTED",
    }

    def known(self, name):
        return (
            bool(re.fullmatch(r"EXACT_RANK\d+_LEDGER_PASSES_STAGE_A_ONLY", name))
            or name in self.BEHAVIOR_PROPERTIES
            or name in self.CONTENT_PROPERTIES
        )

    def check_behavior(self, name, entry):
        """Properties about the reducer, re-executed on live clean evidence."""
        clean = self.clean_entry()
        if name == "CURRENT_STAGE_A_POLICY_COMPLETE":
            required = set(
                json.loads((ROOT / POLICY).read_text(encoding="utf-8"))
                .get("staged_admission", {})
                .get("stage_a_pre_exposure", {})
                .get("required", [])
            )
            self.assertIn(
                "COMPLETE_8_SURFACE_PRIOR_EXPOSURE_SEARCH_INCLUDING_BRAIN_PRS", required
            )
            self.assertIn(
                "TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD_VERIFIED", required
            )
            out = self.verdict(clean)
            self.assertNotIn("STAGE_A_POLICY_INCOMPLETE", out["failed_predicates"], out)
            return
        if name == "TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD_PRESENT":
            self.assertTrue((ROOT / BUDGET_EVIDENCE).is_file(), BUDGET_EVIDENCE)
            out = self.verdict(clean, drop=(BUDGET_EVIDENCE,))
            self.assertFalse(out["pass"], out)
            self.assertIn(
                "TOTAL_STAGE_C_EXECUTION_AND_TERMINAL_BUDGET_GUARD", out["failed_predicates"]
            )
            return
        if name == "ALL_EIGHT_EXPOSURE_SURFACES_PRESENT_AND_ZERO":
            search = self.search(clean["ledger_doc"])
            self.assertEqual(sorted(search["searched_surfaces"]), sorted(EXPECTED_SURFACES))
            for field in EXPECTED_HIT_FIELDS:
                raw, classified, disqualifying = self.accounted(search, field)
                self.assertEqual(disqualifying, 0, field)
                self.assertEqual(classified, raw, field)
            return
        if name == "CORRECTED_RAW_VS_DISQUALIFYING_HIT_CLASSIFICATION_PASSES":
            out = self.verdict(clean, fault=lambda l: self.classify(l, count=2))
            self.assertTrue(out["pass"], out)
            return
        if name == "INSTRUCTION_READ_FAILS_CLOSED":
            out = self.verdict(
                clean, fault=lambda l: l.__setitem__("instruction_read", True)
            )
            self.assertFalse(out["pass"], out)
            self.assertIn("QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"])
            return
        if name in (
            "BRAIN_PR_HIT_FAILS_CLOSED",
            "UNCLASSIFIED_PR_HIT_FAILS_CLOSED",
            "UNCLASSIFIED_PRIOR_HIT_FAILS_CLOSED",
        ):
            out = self.verdict(clean, fault=self.unclassify)
            self.assertFalse(out["pass"], out)
            self.assertIn(
                "PRIOR_EXPOSURE_HIT_CLASSIFICATION_INCOMPLETE", out["failed_predicates"]
            )
            return
        if name in ("DISQUALIFYING_HIT_FAILS_CLOSED", "DISQUALIFYING_PRIOR_HIT_FAILS_CLOSED"):
            out = self.verdict(clean, fault=self.disqualify)
            self.assertFalse(out["pass"], out)
            self.assertIn("PRIOR_EXPOSURE_DISQUALIFYING_HIT", out["failed_predicates"])
            return
        if name in ("INCOMPLETE_SEARCH_FAILS_CLOSED", "INCOMPLETE_SEARCH_FLAG_FAILS_CLOSED"):
            out = self.verdict(
                clean, fault=lambda l: self.search(l).__setitem__("search_complete", False)
            )
            self.assertFalse(out["pass"], out)
            self.assertIn("PRIOR_EXPOSURE_SEARCH_INCOMPLETE", out["failed_predicates"])
            return
        if name == "MISSING_BRAIN_PR_SURFACE_FAILS_CLOSED":
            def drop_surface(ledger):
                search = self.search(ledger)
                search["searched_surfaces"] = [
                    s for s in search["searched_surfaces"] if s != "brain_prs"
                ]

            out = self.verdict(clean, fault=drop_surface)
            self.assertFalse(out["pass"], out)
            self.assertIn(
                "PRIOR_EXPOSURE_SEARCH_SURFACES_INCOMPLETE", out["failed_predicates"]
            )
            return
        self.fail("recorded behavior property is not bound: %s" % name)

    def check_content(self, name, entry):
        """Properties about a specific recorded ledger, checked as it stands."""
        ledger = entry["ledger_doc"]
        doc = entry["doc"]
        search = ledger.get("prior_exposure_search") or {}
        if name == "ALL_EIGHT_DISQUALIFYING_EXPOSURE_COUNTS_ZERO":
            disqualifying = search.get("disqualifying_hits")
            if disqualifying is None:
                # Ledger predates the classification keys: there is no
                # disqualifying count to check, and every raw counter must then
                # be zero for the recorded pass to have been true.
                for field in EXPECTED_HIT_FIELDS:
                    self.assertEqual(search.get(field, 0), 0, field)
                return
            self.assertEqual(sorted(disqualifying), sorted(EXPECTED_HIT_FIELDS))
            self.assertEqual(sum(disqualifying.values()), 0, disqualifying)
            return
        if name == "ALL_NONZERO_RAW_PR_HITS_EXPLICITLY_CLASSIFIED_NON_DISQUALIFYING":
            saw_nonzero = False
            for field in EXPECTED_HIT_FIELDS:
                raw, classified, disqualifying = self.accounted(search, field)
                if raw:
                    saw_nonzero = True
                    self.assertEqual(classified, raw, field)
                    self.assertEqual(disqualifying, 0, field)
            self.assertTrue(
                saw_nonzero or search.get("disqualifying_hits") is not None,
                "nothing to classify and no classification block: the recorded "
                "property would be vacuous",
            )
            return
        if name == "INSTRUCTION_UNREAD":
            if "instruction_read" in doc:
                self.assertFalse(doc["instruction_read"], "the artifact must attest it")
            elif entry["clean"]:
                self.assertFalse(ledger["instruction_read"])
            else:
                self.skipTest(
                    "the ledger was legitimately exposed after admission and the "
                    "artifact records no instruction_read attestation"
                )
            return
        if name == "TASK_COMMAND_UNEXECUTED":
            self.assertFalse(ledger.get("task_command_executed", False))
            return
        self.fail("recorded content property is not bound: %s" % name)

    def check_property(self, name, entry):
        if re.fullmatch(r"EXACT_RANK\d+_LEDGER_PASSES_STAGE_A_ONLY", name):
            # The exact ledger is adjudicated as it stands: reproduced while it is
            # still at Stage A, truthfully refused once it has advanced.
            out = evaluate(
                ROOT,
                task=entry["task"],
                rank=int(entry["rank"]),
                ledger_path=entry["ledger"],
            )
            if entry["clean"]:
                self.assertEqual(out["pass"], entry["recorded_pass"], out)
            else:
                self.assertFalse(out["pass"], out)
                self.assertIn(
                    "QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"]
                )
            self.assertFalse(out["task_execution_authorized"], out)
        elif name in self.BEHAVIOR_PROPERTIES:
            self.check_behavior(name, entry)
        elif name in self.CONTENT_PROPERTIES:
            self.check_content(name, entry)
        else:
            self.fail("recorded property is not bound to an executable check: %s" % name)

    def test_recorded_verified_properties_re_execute_against_v2(self):
        discovered = set()
        for entry in recorded_admissions():
            for name in entry["doc"].get("verified") or []:
                discovered.add(name)
                with self.subTest(admission=entry["admission"], property=name):
                    self.check_property(name, entry)
        self.assertTrue(discovered, "no recorded verified properties discovered")
        # Anti-rot: a newly recorded property must be bound here, not ignored.
        unbound = sorted(n for n in discovered if not self.known(n))
        self.assertEqual(unbound, [], "unbound recorded properties: %s" % unbound)

    # --- reducer parity ------------------------------------------------------
    def test_v1_and_v2_agree_on_every_shared_key(self):
        clean = self.clean_entry()
        root = self.tree(clean["ledger"])
        v2 = evaluate(
            root,
            task=clean["task"],
            rank=int(clean["rank"]),
            ledger_path=clean["ledger"],
        )
        v1 = stage_a_v1.evaluate(
            root,
            clean["ledger"],
            clean["task"],
            int(clean["rank"]),
            clean["ledger_doc"]["task_identity_sha256"],
        )
        shared = sorted(set(v1) & set(v2))
        self.assertTrue(shared)
        # Parity is claimed over every shared key, including the rule label, so a
        # cosmetic divergence cannot hide behind a matching verdict.
        self.assertEqual({k: v1[k] for k in shared}, {k: v2[k] for k in shared}, shared)

    def test_v1_and_v2_agree_on_refusals_too(self):
        # Parity on admissions alone would hide a fail-open divergence, which is
        # how one lease was spent twice, so refusals are compared as well.
        compared = 0
        for entry in recorded_admissions():
            if entry["clean"] or entry["rank"] is None:
                continue
            identity = entry["ledger_doc"].get("task_identity_sha256")
            if not identity:
                continue
            with self.subTest(admission=entry["admission"]):
                root = self.tree(entry["ledger"])
                v2 = evaluate(
                    root,
                    task=entry["task"],
                    rank=int(entry["rank"]),
                    ledger_path=entry["ledger"],
                )
                v1 = stage_a_v1.evaluate(
                    root, entry["ledger"], entry["task"], int(entry["rank"]), identity
                )
                self.assertEqual(v1["pass"], v2["pass"], entry["admission"])
                self.assertFalse(v2["pass"], entry["admission"])
                compared += 1
        self.assertGreater(compared, 0, "no refusal was compared, so parity is untested")

    def test_blanket_nonzero_hit_rule_would_refuse_a_classified_ledger(self):
        # The repaired defect, measured on recorded evidence rather than on a
        # synthetic fixture: recorded ledgers carry nonzero raw hits that are
        # fully classified as non-disqualifying, which the blanket dict-wide zero
        # test refuses outright while the classification model adjudicates.
        subjects = []
        for entry in recorded_admissions():
            search = entry["ledger_doc"].get("prior_exposure_search") or {}
            if any(
                isinstance(search.get(f), int) and search.get(f) for f in EXPECTED_HIT_FIELDS
            ):
                subjects.append(entry)
        self.assertTrue(subjects, "no recorded ledger carries a nonzero raw hit")
        for entry in subjects:
            search = self.search(entry["ledger_doc"])
            with self.subTest(admission=entry["admission"]):
                # The blanket rule evaluates False on real recorded evidence.
                self.assertFalse(all(v == 0 for v in search.values()))
                raw, classified, disqualifying = self.accounted(search, "brain_pr_hits")
                if raw:
                    self.assertEqual(classified, raw)
                    self.assertEqual(disqualifying, 0)
        # And the classification model admits a fully classified nonzero hit.
        clean = self.clean_entry()
        out = self.verdict(clean, fault=lambda l: self.classify(l, count=2))
        self.assertTrue(out["pass"], out)

    def test_authority_named_task_has_a_recorded_stage_a_admission(self):
        # Ties this oracle to the authority: whatever rank the hierarchy names as
        # the next clean task must have a recorded Stage-A admission in the tree.
        # Skipped rather than faked when the authority names no task, which is the
        # state it is in when the next sample must be recomputed.
        hierarchy = json.loads((ROOT / HIERARCHY).read_text(encoding="utf-8"))
        task = (hierarchy.get("stage1_next_clean_task") or {}).get("task")
        if not task:
            self.skipTest("the authority names no next clean task")
        self.assertIn(task, [e["task"] for e in recorded_admissions()])

    def test_uncorroborated_clean_ledgers_are_exactly_the_documented_ones(self):
        """A ledger reading UNEXPOSED must not be contradicted by its own rank's
        Stage-B and Stage-C evidence.

        Every spent rank in this tree records its spend in its ledger -- rank15
        STAGE_C_SPENT_BY_POST_REVOCATION_TASK_SPECIFIC_EXECUTION, rank17
        SPENT__STAGE_C_V2_BURST0_EXECUTED, rank19 SPENT_EXECUTION_SURFACE_FAILURE,
        rank20 CONTAMINATED__TASK_SPECIFIC_EXTERNAL_SEARCH, rank21
        CONTAMINATED_POST_STAGE_B_EXTERNAL_DISCOVERY, rank22
        EXPOSED__STAGE_B_POST_INSTRUCTION_PRE_EXECUTION. rank18 is the sole
        outlier: its ledger still reads UNEXPOSED__STAGE_A_PRE_EXPOSURE while
        FREECAD_IMPELLER_RANK18_STAGE_B_CONTRACT_V1.json is
        FROZEN_POST_INSTRUCTION_PRE_EXECUTION, its Stage-C reconciliation is
        SPENT__ONE_SHOT_EXECUTION_BUDGET_EXCEEDED__NO_TERMINAL_VERDICT and all
        three of its leases are CONSUMED_SUPERSEDED, SPENT or REVOKED.

        This change does not rewrite that ledger: it is frontier evidence owned by
        rank18's lease history, and editing it is a separate causal work unit that
        enforce_goal_hierarchy.py would reject here as a second intent in one PR.
        So the contradiction is pinned explicitly instead, which keeps the rest of
        this suite honest about what its clean subject is worth and fails the day
        upstream corrects the ledger, forcing this list to be re-derived rather
        than trusted.
        """
        contradicted = sorted(
            {e["task"] for e in recorded_admissions() if e["clean"] and self.contradicted(e)}
        )
        self.assertEqual(contradicted, sorted(UNCORROBORATED_CLEAN_LEDGERS))

    def contradicted(self, entry):
        """True when the rank's own Stage-B/C artifacts attest exposure or spend."""
        stem = pathlib.Path(entry["ledger"]).name.split("_CONTAMINATION_LEDGER")[0]
        for sibling in sorted((ROOT / OPUS55).glob(stem + "_STAGE_[BC]_*.json")):
            doc = json.loads(sibling.read_text(encoding="utf-8"))
            text = str(doc.get("status") or "") + str(doc.get("state") or "")
            if any(
                token in text
                for token in ("POST_INSTRUCTION", "EXPOSED", "SPENT", "EXECUTED", "PASS")
            ):
                return True
        for lease in sorted((ROOT / "canonical/governance").glob("LEASE_" + stem + "_*.json")):
            doc = json.loads(lease.read_text(encoding="utf-8"))
            text = str(doc.get("status") or "")
            if any(token in text for token in ("CONSUMED", "SPENT", "REVOKED")):
                return True
        return False


class RecordedProvenanceCitationTests(unittest.TestCase):
    """A recorded admission cites the exact blobs it adjudicated.

    Citations legitimately drift when upstream corrects a ledger after recording
    the admission, as it did for rank21. Drift is tolerable only while the live
    evidence still decides the verdict the same way; the moment it does not, the
    recorded pass is unreproducible and this fails closed. Nothing here rewrites
    a recorded artifact -- refreshing a citation belongs to its lease holder.
    """

    def citations(self):
        found = []
        for entry in recorded_admissions():
            candidate = entry["doc"].get("candidate") or {}
            for kind, path_key, blob_key in (
                ("ledger", "ledger", "ledger_blob"),
                ("source", "stage_a_source", "source_blob"),
            ):
                rel = candidate.get(path_key)
                recorded = candidate.get(blob_key)
                if not isinstance(rel, str) or not isinstance(recorded, str):
                    continue
                target = ROOT / rel
                if not target.is_file():
                    continue
                live = git_blob_sha1(target)
                found.append((entry["admission"], kind, recorded, live, recorded != live))
        return found

    def test_citation_drift_never_changes_the_verdict(self):
        for entry in recorded_admissions():
            if entry["rank"] is None:
                continue
            with self.subTest(admission=entry["admission"]):
                out = evaluate(
                    ROOT,
                    task=entry["task"],
                    rank=int(entry["rank"]),
                    ledger_path=entry["ledger"],
                )
                # Whatever the citations say, live evidence decides: a ledger still
                # at Stage A reproduces its recorded verdict, an advanced one is
                # truthfully refused.
                if entry["clean"]:
                    self.assertEqual(out["pass"], entry["recorded_pass"], out)
                else:
                    self.assertFalse(out["pass"], out)
                    self.assertIn(
                        "QUALIFICATION_CONTAMINATION_LEDGER", out["failed_predicates"]
                    )

    def test_blob_citations_are_actually_compared(self):
        # Guards against the test above passing because nothing was compared.
        citations = self.citations()
        self.assertGreater(len(citations), 0, "no recorded blob citations to compare")
        self.assertTrue(
            all(len(recorded) == 40 and len(live) == 40 for _, _, recorded, live, _ in citations),
            "a citation is not a git blob sha1",
        )



if __name__ == "__main__":
    unittest.main()
