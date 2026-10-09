from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.cursorbench_typed_acceptance_dependency_provenance_atom_v1 import (
    ATOM_ID,
    RECEIPT_SCHEMA,
    VERIFY_SCHEMA,
    dependency_provenance_projection,
    model_sha256,
    projection_sha256,
    verify,
)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def model():
    return {
        "requirements": [{
            "id": "R1",
            "critical": True,
            "transform_kinds": ["artifact"],
            "must_detect_failure_modes": ["bad_output"],
            "builder_dependencies": ["raw:task", "builder:parser"],
        }],
        "checks": [{
            "id": "C1",
            "covers": ["R1"],
            "detects": ["bad_output", "existence", "schema", "roundtrip_or_parse"],
            "dependencies": ["raw:task", "checker:independent-parser"],
            "provenance": "independent_runtime_oracle",
            "derived_from_builder_output": False,
        }],
    }


def write_binding(root: Path, m, *, receipt_mut=None, verify_mut=None):
    gov = root / "canonical/governance"
    ver = root / "canonical/verification"
    gov.mkdir(parents=True, exist_ok=True)
    ver.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "audit_id": "audit:dependency-provenance-1",
        "producer_id": "brain-producer",
        "subject_model_sha256": model_sha256(m),
        "dependency_provenance_projection_sha256": projection_sha256(m),
        "dependency_labels_source_verified": True,
        "provenance_labels_authorized": True,
        "independence_relevant_edges_complete": True,
        "no_undeclared_nonraw_dependencies": True,
        "builder_output_derivation_labels_truthful": True,
        "source_authority_complete": True,
    }
    if receipt_mut:
        receipt_mut(receipt)
    rp = gov / "dependency-provenance.json"
    rp.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    verification = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": git_blob_sha(rp),
        "subject_model_sha256": model_sha256(m),
        "dependency_provenance_projection_sha256": projection_sha256(m),
        "audit_id": receipt.get("audit_id"),
        "producer_id": "brain-producer",
        "independent_verifier_id": "independent-sprite",
        "verification_method": "INDEPENDENT_AUDIT",
        "pass": True,
        "independent_verified": True,
        "dependency_labels_source_verified": True,
        "provenance_labels_authorized": True,
        "independence_relevant_edges_complete": True,
        "no_undeclared_nonraw_dependencies": True,
        "builder_output_derivation_labels_truthful": True,
        "source_authority_completeness_verified": True,
    }
    if verify_mut:
        verify_mut(verification)
    vp = ver / "dependency-provenance.verify.json"
    vp.write_text(json.dumps(verification, sort_keys=True), encoding="utf-8")
    return {
        "receipt": {
            "path": "canonical/governance/dependency-provenance.json",
            "git_blob_sha": git_blob_sha(rp),
        },
        "verification": {
            "path": "canonical/verification/dependency-provenance.verify.json",
            "git_blob_sha": git_blob_sha(vp),
        },
    }


class DependencyProvenanceAtomTests(unittest.TestCase):
    def test_projection_is_exact_and_order_normalized(self):
        m = model()
        p = dependency_provenance_projection(m)
        self.assertEqual(p["requirements"][0]["requirement_id"], "R1")
        self.assertEqual(
            p["requirements"][0]["builder_dependencies"],
            ["builder:parser", "raw:task"],
        )
        self.assertEqual(p["checks"][0]["provenance"], "independent_runtime_oracle")

    def test_missing_binding_is_open_not_truth(self):
        out = verify(model(), None)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__DEPENDENCY_PROVENANCE_BINDING_REQUIRED")
        self.assertFalse(out["atom_truth_authorized"])

    def test_independent_audit_proves_only_dependency_provenance_atom(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = model()
            out = verify(m, write_binding(root, m), repo_root=root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["atom_id"], ATOM_ID)
        self.assertEqual(out["proved_constraint"], {"op": "ATOM", "id": ATOM_ID})
        self.assertEqual(out["other_condition_atoms_proved"], [])
        self.assertFalse(out["whole_policy_condition_proved"])
        self.assertFalse(out["whole_cursorbench_adequate"])

    def test_different_model_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = model()
            other = model()
            other["checks"][0]["dependencies"].append("checker:extra")
            out = verify(m, write_binding(root, other), repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("RECEIPT_MODEL_DIGEST_MISMATCH", out["errors"][0])

    def test_projection_drift_is_load_bearing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = model()
            binding = write_binding(
                root,
                m,
                receipt_mut=lambda r: r.__setitem__(
                    "dependency_provenance_projection_sha256", "0" * 64
                ),
            )
            out = verify(m, binding, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("RECEIPT_PROJECTION_DIGEST_MISMATCH", out["errors"][0])

    def test_labels_cannot_self_assert_truth(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = model()
            binding = write_binding(
                root,
                m,
                receipt_mut=lambda r: r.__setitem__("provenance_labels_authorized", False),
            )
            out = verify(m, binding, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("RECEIPT_PREMISE_UNPROVED:provenance_labels_authorized", out["errors"][0])

    def test_independent_verifier_must_verify_edge_completeness(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = model()
            binding = write_binding(
                root,
                m,
                verify_mut=lambda v: v.__setitem__("independence_relevant_edges_complete", False),
            )
            out = verify(m, binding, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn(
            "VERIFICATION_PREMISE_UNPROVED:independence_relevant_edges_complete",
            out["errors"][0],
        )

    def test_verifier_must_be_producer_independent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = model()
            binding = write_binding(
                root,
                m,
                verify_mut=lambda v: v.__setitem__("independent_verifier_id", "brain-producer"),
            )
            out = verify(m, binding, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertIn("VERIFICATION_NOT_PRODUCER_INDEPENDENT", out["errors"][0])

    def test_unknown_requirement_reference_fails_before_evidence(self):
        m = model()
        m["checks"][0]["covers"] = ["R2"]
        out = verify(m, None)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__DEPENDENCY_PROVENANCE_MODEL_INVALID")
        self.assertIn("CHECK_COVERS_UNKNOWN_REQUIREMENT", out["errors"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
