from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RECORD_PATH = ROOT / "canonical/verification/R2_GENERAL_CROSS_DOCUMENT_UNDERSTANDING_CLOSURE_RECONCILIATION_20261010_V1.json"


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    return sha1(header + raw).hexdigest()


class GeneralCrossDocumentClosureReconciliationV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))

    def test_all_exact_bound_files_match_declared_git_blobs(self):
        bindings = self.record["exact_bindings"]
        rows = [
            bindings["current_r2_pointer"],
            bindings["fixed_point"],
            bindings["live_admission"],
            bindings["current_dynamic_pointer"],
            bindings["dynamic_manifest"],
            bindings["deployment_candidate"],
            bindings["deployment_receipt"],
            bindings["route_verification"],
            bindings["lattice_v8"],
            bindings["source_proof_v15"],
            bindings["compositional_natural_clause"],
            bindings["abc_regression"],
        ]
        route = bindings["admitted_cross_document_route"]
        rows.append({
            "path": route["runtime_path"],
            "git_blob_sha": route["runtime_git_blob_sha"],
        })
        for row in rows:
            path = ROOT / row["path"]
            self.assertTrue(path.is_file(), row["path"])
            self.assertEqual(git_blob_sha(path), row["git_blob_sha"], row["path"])

    def test_current_dynamic_pointer_and_manifest_bind_live_cross_document_route(self):
        ptr = json.loads(
            (ROOT / self.record["exact_bindings"]["current_dynamic_pointer"]["path"])
            .read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (ROOT / self.record["exact_bindings"]["dynamic_manifest"]["path"])
            .read_text(encoding="utf-8")
        )
        expected = self.record["exact_bindings"]["admitted_cross_document_route"]
        self.assertEqual(
            ptr["target"]["path"],
            self.record["exact_bindings"]["dynamic_manifest"]["path"],
        )
        self.assertEqual(
            ptr["target"]["git_blob_sha"],
            self.record["exact_bindings"]["dynamic_manifest"]["git_blob_sha"],
        )
        rows = manifest.get("admissions") or manifest.get("routes") or []
        matches = [row for row in rows if row.get("route_id") == expected["route_id"]]
        self.assertEqual(len(matches), 1)
        row = matches[0]
        self.assertTrue(row["active"])
        self.assertTrue(row["automatic_live_admission"])
        self.assertEqual(row["runtime_path"], expected["runtime_path"])
        self.assertEqual(row["runtime_git_blob_sha"], expected["runtime_git_blob_sha"])
        self.assertEqual(
            row["candidate_git_blob_sha"],
            self.record["exact_bindings"]["deployment_candidate"]["git_blob_sha"],
        )
        self.assertEqual(
            row["independent_receipt_git_blob_sha"],
            self.record["exact_bindings"]["deployment_receipt"]["git_blob_sha"],
        )
        self.assertEqual(
            row["verification_git_blob_sha"],
            self.record["exact_bindings"]["route_verification"]["git_blob_sha"],
        )

    def test_deployment_receipt_independently_authorizes_admission_without_terminal_authority(self):
        receipt = json.loads(
            (ROOT / self.record["exact_bindings"]["deployment_receipt"]["path"])
            .read_text(encoding="utf-8")
        )
        self.assertTrue(receipt["independent_verified"])
        self.assertTrue(receipt["preflight_pure_no_effect"])
        self.assertTrue(receipt["producer_independent_acceptance"])
        self.assertTrue(receipt["deployment_eligible"])
        self.assertFalse(receipt["promotion_authority"])
        self.assertFalse(receipt["terminal_authority"])

    def test_original_abc_exception_scenario_is_bound_to_same_live_route(self):
        abc = json.loads(
            (ROOT / self.record["exact_bindings"]["abc_regression"]["path"])
            .read_text(encoding="utf-8")
        )
        expected = self.record["exact_bindings"]["admitted_cross_document_route"]
        self.assertEqual(
            abc["status"],
            self.record["exact_bindings"]["abc_regression"]["expected_status"],
        )
        self.assertTrue(abc["live_binding"]["active_dynamic_admission"])
        self.assertEqual(abc["live_binding"]["route_id"], expected["route_id"])
        self.assertEqual(
            abc["live_binding"]["runtime_git_blob_sha"],
            expected["runtime_git_blob_sha"],
        )

    def test_fixed_point_uses_live_admission_wrapper_and_wrapper_uses_v21_legacy_carrier(self):
        fixed = (
            ROOT / self.record["exact_bindings"]["fixed_point"]["path"]
        ).read_text(encoding="utf-8")
        live = (
            ROOT / self.record["exact_bindings"]["live_admission"]["path"]
        ).read_text(encoding="utf-8")
        self.assertIn(
            "from canonical.runtime import r2_direct_live_admission_v1 as direct_adequacy",
            fixed,
        )
        self.assertIn(
            "from canonical.runtime import r2_direct_end_to_end_adequacy_v21 as legacy",
            live,
        )
        self.assertIn(
            "from canonical.runtime import r2_direct_route_dynamic_admission_v1 as admission",
            live,
        )

    def test_remaining_cross_document_top_is_classified_as_shared_semantic_evidence_gap(self):
        current = json.loads(
            (ROOT / self.record["exact_bindings"]["current_r2_pointer"]["path"])
            .read_text(encoding="utf-8")
        )
        self.assertIn(
            "CROSS_DOCUMENT_REQUIRED_EFFECT_FIELDS_REMAINING_AT_SEMANTIC_TOP",
            current["remaining_problem_class"],
        )
        boundary = self.record["scope_boundary"]
        self.assertFalse(boundary["cross_document_specific_remaining_blocker"])
        self.assertEqual(
            boundary["classification"],
            "SHARED_SEMANTIC_EVIDENCE_ACQUISITION_OR_WORD_SENSE_ONTOLOGY_RELATION_PROOF_GAP__NOT_A_DOCUMENT_INTERACTION_OR_COMPOSITION_GAP",
        )
        self.assertFalse(boundary["global_open_world_closure_claimed"])

    def test_reopen_law_forbids_architecture_churn_for_upstream_language_gaps(self):
        law = self.record["reopen_law"]
        prohibited = set(law["do_not_reopen_for"])
        self.assertIn("GENERAL_WORD_SENSE_DISAMBIGUATION", prohibited)
        self.assertIn("GENERAL_INFERRED_SYNONYMY", prohibited)
        self.assertIn("OPEN_WORLD_ONTOLOGY_MAPPING", prohibited)
        self.assertEqual(
            law["next_owner_for_open_semantic_top"],
            "GENERAL_SEMANTIC_ACQUISITION_AND_AUTHENTICATED_RELATION_PROOF_FRONTIER",
        )


if __name__ == "__main__":
    unittest.main()
