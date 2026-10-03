from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from canonical.runtime import harbor_science_planner_v1


ROOT = Path(__file__).resolve().parents[2]
CAPSULE_PATH = ROOT / "canonical/governance/TB_SCIENCE_EXECUTION_CAPSULE_CANDIDATE_V1.json"
ACTION_INTENT_PATH = ROOT / "canonical/governance/ACTION_INTENTS/BIND_TB_SCIENCE_EXECUTION_CAPSULE_ZERO_CASE_V1.json"
METADATA_WORKFLOW_PATH = ROOT / ".github/workflows/verify-tb-science-capsule-metadata-only-v1.yml"
MANIFEST_PATH = ROOT / "canonical/governance/TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json"
MANIFEST_RECEIPT_PATH = ROOT / "canonical/verification/TB_SCIENCE_210_SLOT_MANIFEST_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
ROUTE_RECEIPT_PATH = ROOT / "canonical/verification/TB_SCIENCE_DEDICATED_PLANNER_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


class TBScienceExecutionCapsuleTests(unittest.TestCase):
    def test_manifest_blob_is_exactly_the_blob_adjudicated_independently(self):
        capsule = _load(CAPSULE_PATH)
        manifest_receipt = _load(MANIFEST_RECEIPT_PATH)
        binding = capsule["execution_manifest"]
        actual = _git_blob_sha(MANIFEST_PATH)
        self.assertEqual(actual, binding["git_blob_sha"])
        self.assertEqual(actual, manifest_receipt["exact_manifest_blob"])
        self.assertEqual(actual, "e0318f4fcde040498077dcdd872e398e32240791")
        self.assertEqual(manifest_receipt["independent_runner"]["conclusion"], "success")
        self.assertEqual(manifest_receipt["independent_runner"]["workflow_run_id"], 37101057700)
        self.assertEqual(manifest_receipt["independent_runner"]["workflow_job_id"], 111140509307)

        binding = _load(ROOT / "canonical/governance/TB_SCIENCE_MANIFEST_EXACT_BLOB_BINDING_V1.json")
        self.assertEqual(binding["exact_verified_manifest_git_blob_sha"], actual)
        self.assertEqual(binding["independent_verification"]["exact_manifest_git_blob_sha"], actual)
        self.assertFalse(binding["execution_authority"])
        self.assertFalse(binding["promotion_authority"])
        self.assertEqual(binding["prior_main_blob_rejected_for_exact_binding"], "6dfa880b1f68881531afbba6ca211681801fd19b")

    def test_capsule_binds_current_route_blobs_and_transport_configuration(self):
        capsule = _load(CAPSULE_PATH)
        route = capsule["route_inputs"]
        for key, expected in (
            ("controller", "8ab8287fdb6a9b63b9fe2d2addde731486c89d1e"),
            ("planner_transport", "17472fd2b01b164fbb180aecfc04385b55b11499"),
            ("source_gate", "b168b131f6383e158bdc0d931439d14e61f2a5de"),
        ):
            row = route[key]
            self.assertEqual(_git_blob_sha(ROOT / row["path"]), expected)
            self.assertEqual(row["git_blob_sha"], expected)

        self.assertEqual(harbor_science_planner_v1.ENDPOINT, route["planner_transport"]["endpoint"])
        self.assertEqual(
            list(harbor_science_planner_v1.MODEL_ALIASES),
            route["planner_transport"]["allowed_model_aliases_in_order"],
        )
        self.assertFalse(route["planner_transport"]["environment_execution_authority"])
        self.assertFalse(route["planner_transport"]["finish_authority"])

        for dependency in route["brain_execution_dependencies"]:
            self.assertEqual(_git_blob_sha(ROOT / dependency["path"]), dependency["git_blob_sha"])
        for path, expected in route["brain_route_test_blobs"].items():
            self.assertEqual(_git_blob_sha(ROOT / path), expected)
        candidate = route["route_candidate"]
        self.assertEqual(_git_blob_sha(ROOT / candidate["path"]), candidate["git_blob_sha"])

        route_receipt = _load(ROUTE_RECEIPT_PATH)
        exact = route_receipt["exact_brain_blobs"]
        self.assertEqual(exact[route["controller"]["path"]], route["controller"]["git_blob_sha"])
        self.assertEqual(exact[route["planner_transport"]["path"]], route["planner_transport"]["git_blob_sha"])
        self.assertEqual(route_receipt["independent_runner"]["conclusion"], "success")

    def test_dataset_scorer_and_conservative_slot_contract_are_frozen(self):
        capsule = _load(CAPSULE_PATH)
        manifest = _load(MANIFEST_PATH)
        dataset = capsule["frozen_dataset"]
        self.assertEqual(dataset["content_hash"], manifest["frozen_dataset"]["content_hash"])
        self.assertEqual(dataset["source_commit"], manifest["frozen_dataset"]["source_commit"])
        self.assertEqual(dataset["task_count"], 70)
        self.assertFalse(dataset["task_names_or_instructions_embedded"])

        contract = capsule["conservative_execution_contract"]
        acceptance = manifest["acceptance"]
        rules = manifest["execution_rules"]
        self.assertEqual(contract["slot_count"], manifest["frozen_dataset"]["slot_count"])
        self.assertEqual(contract["slot_count"], 210)
        self.assertEqual(contract["attempts_per_task"], 3)
        self.assertEqual(contract["required_exact_successes"], acceptance["required_successes"])
        self.assertEqual(contract["required_exact_successes"], 124)
        self.assertEqual(contract["irreversible_failure_lock"], acceptance["irreversible_failure_count"])
        self.assertEqual(contract["irreversible_failure_lock"], 87)
        self.assertEqual(contract["retries_per_slot"], rules["retries_per_slot"])
        self.assertEqual(contract["retries_per_slot"], 0)
        self.assertEqual(contract["slot_replacement"], rules["slot_replacement"])
        self.assertFalse(contract["slot_replacement"])
        self.assertFalse(rules["denominator_shrink"])
        self.assertEqual(contract["non_success_censored_unrun_and_carrier_failure_credit"], 0)

        scorer = capsule["scorer_binding"]
        self.assertEqual(scorer["score_contract"]["success_condition"], "reward >= 1.0")
        self.assertEqual(scorer["score_contract"]["reward_domain"], "EXACT_BINARY_0_OR_1")
        self.assertIn("NOT_TREATED_AS_AN_END_TO_END_PASS", scorer["semantics_evidence"]["scope_limit"])

    def test_capsule_is_metadata_only_and_never_authorizes_execution(self):
        capsule = _load(CAPSULE_PATH)
        self.assertFalse(capsule["execution_authority"])
        self.assertFalse(capsule["promotion_authority"])
        self.assertEqual(capsule["terminal_task_content_read"], 0)
        self.assertEqual(capsule["terminal_trials_executed"], 0)
        self.assertEqual(capsule["terminal_results_observed"], 0)
        self.assertEqual(capsule["new_reality_units_consumed"], 0)
        self.assertEqual(capsule["incremental_spend_usd"], 0)
        self.assertFalse(capsule["execution_manifest"]["task_names_slot_ids_and_task_content_duplicated_in_capsule"])
        self.assertNotIn("task_metadata", capsule)
        self.assertNotIn("slot_ids", capsule)
        self.assertNotIn("slots", capsule)
        self.assertTrue(capsule["activation_blockers"])

        guard = capsule["global_execution_guard"]
        self.assertEqual(_git_blob_sha(ROOT / guard["authority_path"]), guard["authority_git_blob_sha"])
        self.assertEqual(guard["proved_atomic_predicates"], 8)
        self.assertEqual(guard["unresolved_atomic_predicates"], 30)
        self.assertEqual(guard["authorized_acceptance_case_actions"], [])
        self.assertFalse(guard["terminal_goal_achieved"])
        self.assertFalse(guard["fresh_reality_before_zero_reality_saturation"])
        self.assertFalse(guard["execution_authority"])
        self.assertFalse(guard["promotion_authority"])

        reconciliation = capsule["execution_manifest"]
        self.assertEqual(
            _git_blob_sha(ROOT / reconciliation["exact_blob_reconciliation"]),
            reconciliation["exact_blob_reconciliation_git_blob_sha"],
        )

    def test_clean_runner_workflow_cannot_download_or_execute_tasks(self):
        workflow = METADATA_WORKFLOW_PATH.read_text(encoding="utf-8").lower()
        for forbidden in (
            "harbor run",
            "dry-run",
            "pip install",
            "terminal-bench-science/",
            "text.pollinations.ai",
            "urllib.request",
            "wget ",
            "curl ",
            "download-artifact",
        ):
            self.assertNotIn(forbidden, workflow)
        self.assertIn("permissions:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("clean_runner_metadata_only_preflight_pass", workflow)
        self.assertIn('"execution_authority":false', workflow)
        self.assertIn('"promotion_authority":false', workflow)

    def test_non_metadata_external_run_is_explicitly_excluded(self):
        intent = _load(ACTION_INTENT_PATH)
        candidate_binding = intent["causal_finding"]["capsule_candidate"]
        self.assertEqual(candidate_binding["path"], str(CAPSULE_PATH.relative_to(ROOT)))
        self.assertEqual(_git_blob_sha(CAPSULE_PATH), candidate_binding["git_blob_sha"])
        self.assertEqual(candidate_binding["status"], "UNVERIFIED_CANDIDATE_NO_EXECUTION_OR_PROMOTION_AUTHORITY")

        screen = intent["independent_verification_screen"]
        preflight = screen["clean_runner_preflight"]
        self.assertEqual(
            preflight["workflow_path"],
            ".github/workflows/verify-tb-science-capsule-metadata-only-v1.yml",
        )
        self.assertEqual(
            preflight["status"],
            "CONFIGURED__RESULT_NON_AUTHORIZING_AND_NOT_YET_ADJUDICATED",
        )
        self.assertFalse(intent["execution_authority"])
        self.assertFalse(intent["promotion_authority"])
        excluded = screen["excluded_run"]
        self.assertEqual(screen["status"], "NO_ADMISSIBLE_CAPSULE_VERIFICATION_FOUND")
        self.assertEqual(excluded["pull_request"], 1227)
        self.assertEqual(excluded["workflow_run_id"], 37101489446)
        self.assertEqual(
            excluded["candidate_manifest_git_blob_sha_expected_by_that_workflow"],
            "6dfa880b1f68881531afbba6ca211681801fd19b",
        )
        self.assertEqual(
            excluded["current_capsule_manifest_git_blob_sha"],
            "e0318f4fcde040498077dcdd872e398e32240791",
        )
        self.assertFalse(excluded["authority_or_credit"])
        self.assertIn(
            "THE_WORKFLOW_RUNS_HARBOR_DRY_RUNS_FOR_TASK_IDENTIFIERS_AND_IS_NOT_METADATA_ONLY",
            excluded["exclusion_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
