from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime.coding_proof_carrying_typed_acceptance_controller_v1 import evaluate
from canonical.tests.test_cursorbench_typed_acceptance_source_coverage_atoms_v1 import (
    source_contract,
    write_binding as write_source_binding,
)
from canonical.tests.test_cursorbench_typed_acceptance_dependency_provenance_atom_v1 import (
    write_binding as write_dependency_binding,
)
from canonical.tests.test_cursorbench_typed_acceptance_information_boundary_atom_v1 import (
    write_binding as write_boundary_binding,
)


def full_model():
    return {
        "requirements": [
            {
                "id": "R1",
                "critical": True,
                "transform_kinds": ["artifact"],
                "must_detect_failure_modes": ["bad_output"],
                "builder_dependencies": ["raw:task", "builder:artifact-builder"],
            },
            {
                "id": "R2",
                "critical": True,
                "transform_kinds": ["numeric_formula"],
                "must_detect_failure_modes": [],
                "builder_dependencies": ["raw:task", "builder:formula-a"],
            },
        ],
        "checks": [
            {
                "id": "C1",
                "covers": ["R1"],
                "detects": ["bad_output", "existence", "schema", "roundtrip_or_parse"],
                "dependencies": ["raw:task", "checker:artifact-parser"],
                "provenance": "independent_runtime_oracle",
                "derived_from_builder_output": False,
            },
            {
                "id": "C2",
                "covers": ["R2"],
                "detects": ["unit_or_scale", "boundary_or_extreme", "alternate_derivation"],
                "dependencies": ["raw:task", "checker:formula-b"],
                "provenance": "independent_runtime_oracle",
                "derived_from_builder_output": False,
            },
        ],
    }


def payload_with_valid_bindings(root: Path, model):
    return {
        "typed_acceptance_model": model,
        "typed_acceptance_source_coverage_binding": write_source_binding(
            root, model, source_contract()
        ),
        "typed_acceptance_dependency_provenance_binding": write_dependency_binding(
            root, model
        ),
        "typed_acceptance_information_boundary_binding": write_boundary_binding(
            root, model
        ),
    }


class ProofCarryingTypedAcceptanceControllerTests(unittest.TestCase):
    def test_missing_evidence_blocks_without_fabricating_atom_truth(self):
        model = full_model()
        out = evaluate({"typed_acceptance_model": model})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "BLOCKED__PROOF_EVIDENCE_INSUFFICIENT")
        self.assertEqual(
            set(out["evidence_gaps"]),
            {
                "typed_acceptance_source_coverage_binding",
                "typed_acceptance_dependency_provenance_binding",
                "typed_acceptance_information_boundary_binding",
            },
        )
        self.assertFalse(out["preflight_authorized"])
        self.assertFalse(out["terminal_authority"])

    def test_malformed_supplied_proof_fails_closed(self):
        model = full_model()
        out = evaluate(
            {
                "typed_acceptance_model": model,
                "typed_acceptance_source_coverage_binding": {},
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SUPPLIED_PROOF_INVALID_OR_CONTRADICTORY",
        )
        self.assertTrue(out["proof_failures"])

    def test_unsupported_transform_fails_before_evidence(self):
        model = full_model()
        model["requirements"][0]["transform_kinds"] = ["invented_transform"]
        out = evaluate({"typed_acceptance_model": model})
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SUPPORTED_TRANSFORM_PROOF_FAILED",
        )

    def test_valid_proof_package_and_complete_acceptance_passes_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            model = full_model()
            out = evaluate(payload_with_valid_bindings(root, model), repo_root=root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__PROOF_CARRYING_TYPED_ACCEPTANCE_PREFLIGHT",
        )
        self.assertTrue(out["preflight_authorized"])
        self.assertEqual(len(out["proved_atom_ids"]), 5)
        self.assertTrue(out["assessment"]["pass"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_complete_proof_package_but_uncovered_failure_mode_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            model = full_model()
            model["checks"] = [model["checks"][0]]
            out = evaluate(payload_with_valid_bindings(root, model), repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "BLOCKED__INDEPENDENT_ACCEPTANCE_INCOMPLETE",
        )
        self.assertIn("R2", out["failed_requirements"])
        self.assertTrue(out["counterexample_templates"])
        self.assertFalse(out["preflight_authorized"])

    def test_cross_model_dependency_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            model = full_model()
            other = full_model()
            other["checks"][0]["dependencies"].append("checker:extra")
            payload = payload_with_valid_bindings(root, model)
            payload["typed_acceptance_dependency_provenance_binding"] = (
                write_dependency_binding(root, other)
            )
            out = evaluate(payload, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__SUPPLIED_PROOF_INVALID_OR_CONTRADICTORY",
        )
        self.assertTrue(
            any("RECEIPT_MODEL_DIGEST_MISMATCH" in x for x in out["proof_failures"])
        )

    def test_unknown_payload_fields_fail_closed(self):
        out = evaluate(
            {
                "typed_acceptance_model": full_model(),
                "caller_declares_everything_true": True,
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED__UNKNOWN_PAYLOAD_FIELDS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
