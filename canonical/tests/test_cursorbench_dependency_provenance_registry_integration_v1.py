from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import p3_conditioned_policy_adequacy_registry_v1 as registry
from canonical.runtime.cursorbench_typed_acceptance_dependency_provenance_atom_v1 import (
    ATOM_ID,
    RECEIPT_SCHEMA,
    VERIFY_SCHEMA,
    model_sha256,
    projection_sha256,
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


def write_binding(root: Path, m, *, bad=False):
    gov = root / "canonical/governance"
    ver = root / "canonical/verification"
    gov.mkdir(parents=True, exist_ok=True)
    ver.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "audit_id": "audit:dep-prov",
        "producer_id": "producer",
        "subject_model_sha256": model_sha256(m),
        "dependency_provenance_projection_sha256": projection_sha256(m),
        "dependency_labels_source_verified": True,
        "provenance_labels_authorized": not bad,
        "independence_relevant_edges_complete": True,
        "no_undeclared_nonraw_dependencies": True,
        "builder_output_derivation_labels_truthful": True,
        "source_authority_complete": True,
    }
    rp = gov / "dep.json"
    rp.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    verification = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": git_blob_sha(rp),
        "subject_model_sha256": model_sha256(m),
        "dependency_provenance_projection_sha256": projection_sha256(m),
        "audit_id": "audit:dep-prov",
        "producer_id": "producer",
        "independent_verifier_id": "verifier",
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
    vp = ver / "dep.verify.json"
    vp.write_text(json.dumps(verification, sort_keys=True), encoding="utf-8")
    return {
        "receipt": {
            "path": "canonical/governance/dep.json",
            "git_blob_sha": git_blob_sha(rp),
        },
        "verification": {
            "path": "canonical/verification/dep.verify.json",
            "git_blob_sha": git_blob_sha(vp),
        },
    }


class DependencyProvenanceRegistryIntegrationTests(unittest.TestCase):
    def test_valid_binding_adds_exact_atom_but_does_not_self_close_policy(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = model()
            binding = write_binding(root, m)
            out = registry.augment_problem(
                {
                    "decision_basis": ["SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1"],
                    "typed_acceptance_model": m,
                    "typed_acceptance_dependency_provenance_binding": binding,
                },
                repo_root=root,
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["dependency_provenance_proved_atom_ids"], [ATOM_ID])
        self.assertIn(ATOM_ID, out["proved_condition_atom_ids"])
        self.assertIn(ATOM_ID, out["problem"]["decision_basis"])
        self.assertIn(
            {"op": "ATOM", "id": ATOM_ID},
            out["problem"]["formal_source_constraints"],
        )
        typed = [
            row for row in out["skipped_registered_policies"]
            if row["policy_id"] == "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
        ]
        self.assertEqual(len(typed), 1)
        self.assertIn(
            "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1",
            typed[0]["missing_atoms"],
        )
        self.assertIn(
            "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
            typed[0]["missing_atoms"],
        )
        self.assertFalse(out["membership_self_certified"])
        self.assertFalse(out["terminal_authority"])

    def test_malformed_dependency_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            m = model()
            binding = write_binding(root, m, bad=True)
            out = registry.augment_problem(
                {
                    "decision_basis": ["SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1"],
                    "typed_acceptance_model": m,
                    "typed_acceptance_dependency_provenance_binding": binding,
                },
                repo_root=root,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "DEPENDENCY_PROVENANCE_ATOM_BINDING_INVALID")

    def test_binding_without_model_fails_closed(self):
        out = registry.augment_problem(
            {
                "decision_basis": ["SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1"],
                "typed_acceptance_dependency_provenance_binding": {},
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "DEPENDENCY_PROVENANCE_BINDING_REQUIRES_TYPED_ACCEPTANCE_MODEL",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
