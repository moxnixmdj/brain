from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.bound_capabilities import semantic_authority_receipt_verify_v1 as verify


class SemanticAuthorityReceiptVerifyV1Tests(unittest.TestCase):
    def _fixture(self, *, role="OEWN_DECISION_MANIFEST_AUTHORITY"):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "canonical/governance").mkdir(parents=True)
        (root / "canonical/verification").mkdir(parents=True)

        receipt = {
            "pass": True,
            "schema": "PROJECT_BRAIN_OEWN_DECISION_SENSE_AUTHORITY_RECEIPT_V1",
            "manifest_sha256": "a" * 64,
            "scope_id": "scope-1",
            "release_id": "oewn-2025",
            "release_sha256": "b" * 64,
            "lemma": "margin",
            "part_of_speech": "n",
            "sense_set_binding_complete": True,
            "sense_terminal_signatures_authenticated": True,
            "observation_outcomes_authenticated": True,
            "verification_authority_mutated": False,
            "receipt_sha256": "c" * 64,
        }
        receipt_sha = verify._sha256(receipt)
        verification = {
            "schema": "TEST_SEMANTIC_AUTHORITY_INDEPENDENT_VERIFY_V1",
            "status": "PASS__INDEPENDENT_SEMANTIC_AUTHORITY_RECEIPT",
            "semantic_authority_receipt_sha256": receipt_sha,
            "independent_verifier_passed": True,
            "verification_authority_mutated": False,
        }
        verification_path = (
            root / "canonical/verification/semantic_authority_receipt_test.json"
        )
        raw = (json.dumps(verification, sort_keys=True, indent=2) + "\n").encode()
        verification_path.write_bytes(raw)

        registry = {
            "schema": verify.REGISTRY_SCHEMA,
            "status": "TEST_ONLY__CONTENT_ADDRESSED_SEMANTIC_AUTHORITY_ADMISSIONS",
            "admissions": [{
                "admission_id": "test-admission-1",
                "role": role,
                "receipt_schema": receipt["schema"],
                "receipt_sha256": receipt_sha,
                "verification_path": (
                    "canonical/verification/semantic_authority_receipt_test.json"
                ),
                "verification_git_blob_sha": verify._git_blob_sha(raw),
                "verification_receipt_sha256_field": (
                    "semantic_authority_receipt_sha256"
                ),
                "verification_status": verification["status"],
                "independent_verification_proved": True,
                "admitted": True,
            }],
        }
        registry_path = root / "canonical/governance/test_registry.json"
        registry_path.write_text(
            json.dumps(registry, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return td, root, receipt, registry_path, verification_path

    def test_exact_admitted_receipt_returns_same_controller_receipt_fields(self):
        td, root, receipt, registry_path, _ = self._fixture()
        self.addCleanup(td.cleanup)
        out = verify.verify_receipt(
            receipt,
            role="OEWN_DECISION_MANIFEST_AUTHORITY",
            root=root,
            registry_path=registry_path,
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["admission_verified"])
        self.assertEqual(out["schema"], receipt["schema"])
        self.assertEqual(out["manifest_sha256"], receipt["manifest_sha256"])
        self.assertEqual(out["receipt_sha256"], receipt["receipt_sha256"])
        self.assertFalse(out["semantic_truth_inferred"])
        self.assertFalse(out["terminal_authority"])

    def test_receipt_mutation_is_not_admitted(self):
        td, root, receipt, registry_path, _ = self._fixture()
        self.addCleanup(td.cleanup)
        changed = deepcopy(receipt)
        changed["lemma"] = "capital"
        out = verify.verify_receipt(
            changed,
            role="OEWN_DECISION_MANIFEST_AUTHORITY",
            root=root,
            registry_path=registry_path,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EXACT_RECEIPT_NOT_ADMITTED_FOR_ROLE")

    def test_wrong_semantic_role_is_not_admitted(self):
        td, root, receipt, registry_path, _ = self._fixture()
        self.addCleanup(td.cleanup)
        out = verify.verify_receipt(
            receipt,
            role="OEWN_SENSE_OBSERVATION_EVIDENCE",
            root=root,
            registry_path=registry_path,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EXACT_RECEIPT_NOT_ADMITTED_FOR_ROLE")

    def test_verification_artifact_blob_drift_fails_closed(self):
        td, root, receipt, registry_path, verification_path = self._fixture()
        self.addCleanup(td.cleanup)
        verification_path.write_text(
            verification_path.read_text(encoding="utf-8") + " ",
            encoding="utf-8",
        )
        out = verify.verify_receipt(
            receipt,
            role="OEWN_DECISION_MANIFEST_AUTHORITY",
            root=root,
            registry_path=registry_path,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "VERIFICATION_ARTIFACT_BLOB_MISMATCH")

    def test_verification_artifact_must_bind_exact_receipt_hash(self):
        td, root, receipt, registry_path, verification_path = self._fixture()
        self.addCleanup(td.cleanup)
        doc = json.loads(verification_path.read_text(encoding="utf-8"))
        doc["semantic_authority_receipt_sha256"] = "d" * 64
        raw = (json.dumps(doc, sort_keys=True, indent=2) + "\n").encode()
        verification_path.write_bytes(raw)
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["admissions"][0]["verification_git_blob_sha"] = verify._git_blob_sha(raw)
        registry_path.write_text(
            json.dumps(registry, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        out = verify.verify_receipt(
            receipt,
            role="OEWN_DECISION_MANIFEST_AUTHORITY",
            root=root,
            registry_path=registry_path,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "VERIFICATION_ARTIFACT_RECEIPT_BINDING_INVALID",
        )

    def test_independent_verifier_and_authority_immutability_are_mandatory(self):
        td, root, receipt, registry_path, verification_path = self._fixture()
        self.addCleanup(td.cleanup)
        doc = json.loads(verification_path.read_text(encoding="utf-8"))
        doc["independent_verifier_passed"] = False
        raw = (json.dumps(doc, sort_keys=True, indent=2) + "\n").encode()
        verification_path.write_bytes(raw)
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["admissions"][0]["verification_git_blob_sha"] = verify._git_blob_sha(raw)
        registry_path.write_text(
            json.dumps(registry, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        out = verify.verify_receipt(
            receipt,
            role="OEWN_DECISION_MANIFEST_AUTHORITY",
            root=root,
            registry_path=registry_path,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "INDEPENDENT_VERIFIER_PASS_NOT_BOUND")

    def test_production_empty_registry_mints_no_authority(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        (root / "canonical/governance").mkdir(parents=True)
        (root / verify.REGISTRY_REL).write_text(
            json.dumps({
                "schema": verify.REGISTRY_SCHEMA,
                "status": "ACTIVE__CONTENT_ADDRESSED_SEMANTIC_AUTHORITY_ADMISSIONS",
                "admissions": [],
            }),
            encoding="utf-8",
        )
        receipt = {
            "pass": True,
            "schema": "PROJECT_BRAIN_OEWN_DECISION_SENSE_AUTHORITY_RECEIPT_V1",
        }
        out = verify.run({
            "receipt_json": json.dumps(receipt),
            "role": "OEWN_DECISION_MANIFEST_AUTHORITY",
        }, root)
        self.assertFalse(out["pass"])
        self.assertFalse(out["admission_verified"])
        self.assertEqual(out["reason"], "EXACT_RECEIPT_NOT_ADMITTED_FOR_ROLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
