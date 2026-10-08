from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import p3_policy_adequacy_registry_v1 as registry
from canonical.runtime import p3_robust_policy_adequacy_cegar_v1 as p3


P2_ATOM = "P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1"
P3_BINARY_ATOM = "P3_BOUND_BINARY_REAL_CONTEXT_GROUNDED_DECISION_TOP_LAW_V1"
SYNTHESIS_ATOM = "SYNTHESIS_TYPED_VISIBLE_SUPPORT_COMMON_POLICY_TOP_LAW_V1"


def atom(name: str):
    return {"op": "ATOM", "id": name}


class P3PolicyAdequacyRegistryV1Tests(unittest.TestCase):
    def test_catalog_contains_three_existing_verified_cells(self):
        out = registry.catalog()
        self.assertEqual(out["policy_count"], 3)
        ids = {row["policy_id"] for row in out["policies"]}
        self.assertEqual(
            ids,
            {
                "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1",
                "P3_BOUND_BINARY_DECISION_GROUNDED_EXPRESSION_POLICY_V1",
                "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1",
            },
        )
        self.assertFalse(out["membership_self_certified"])

    def test_unrelated_basis_injects_nothing(self):
        out = registry.augment_problem({"decision_basis": ["unrelated"]})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["injected_policy_ids"], [])
        self.assertEqual(out["basis_eligible_policy_count"], 0)
        self.assertEqual(out["problem"]["policy_conditions"], {})
        self.assertEqual(out["problem"]["policy_adequacy_bindings"], {})

    def test_exact_basis_atoms_inject_only_matching_cells(self):
        cases = [
            (
                P2_ATOM,
                "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1",
            ),
            (
                P3_BINARY_ATOM,
                "P3_BOUND_BINARY_DECISION_GROUNDED_EXPRESSION_POLICY_V1",
            ),
            (
                SYNTHESIS_ATOM,
                "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1",
            ),
        ]
        for basis_atom, policy_id in cases:
            with self.subTest(policy_id=policy_id):
                out = registry.augment_problem({"decision_basis": [basis_atom]})
                self.assertTrue(out["pass"], out)
                self.assertEqual(out["injected_policy_ids"], [policy_id])
                self.assertEqual(
                    out["problem"]["policy_conditions"][policy_id],
                    atom(basis_atom),
                )
                binding = out["problem"]["policy_adequacy_bindings"][policy_id]
                self.assertEqual(
                    set(binding),
                    {
                        "adequacy_certificate_path",
                        "adequacy_certificate_blob_sha",
                        "independent_verification_path",
                        "independent_verification_blob_sha",
                    },
                )

    def test_caller_cannot_override_registered_policy_condition(self):
        policy_id = "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1"
        out = registry.augment_problem(
            {
                "decision_basis": [P2_ATOM, "other"],
                "policy_conditions": {policy_id: atom("other")},
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "CALLER_POLICY_CONDITION_CONFLICTS_WITH_REGISTERED_ADEQUACY",
        )

    def test_caller_cannot_override_registered_binding(self):
        policy_id = "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1"
        out = registry.augment_problem(
            {
                "decision_basis": [P2_ATOM],
                "policy_conditions": {policy_id: atom(P2_ATOM)},
                "policy_adequacy_bindings": {
                    policy_id: {
                        "adequacy_certificate_path": "canonical/governance/fake.json",
                        "adequacy_certificate_blob_sha": "0" * 40,
                        "independent_verification_path": "canonical/verification/fake.json",
                        "independent_verification_blob_sha": "0" * 40,
                    }
                },
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "CALLER_POLICY_BINDING_CONFLICTS_WITH_REGISTERED_ADEQUACY",
        )

    def test_registered_binding_blob_drift_fails_closed(self):
        mutated = copy.deepcopy(registry._REGISTRY)
        mutated[
            "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1"
        ]["binding_blob_sha"] = "0" * 40
        with patch.object(registry, "_REGISTRY", mutated):
            out = registry.augment_problem({"decision_basis": [P2_ATOM]})
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "REGISTERED_POLICY_ADEQUACY_BINDING_INVALID",
        )

    def test_p3_reuses_registered_p2_adequacy_when_membership_is_proved(self):
        x = atom(P2_ATOM)
        out = p3.solve(
            {
                "decision_basis": [P2_ATOM],
                "formal_source_constraints": [x],
                "proposed_refinements": [x],
            }
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS",
        )
        self.assertEqual(
            out["selected_policy_id"],
            "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1",
        )
        self.assertIn(
            "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1",
            out["policy_adequacy_registry"]["injected_policy_ids"],
        )

    def test_p3_authenticates_every_registered_cell_when_membership_is_proved(self):
        cases = [
            (
                P2_ATOM,
                "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1",
            ),
            (
                P3_BINARY_ATOM,
                "P3_BOUND_BINARY_DECISION_GROUNDED_EXPRESSION_POLICY_V1",
            ),
            (
                SYNTHESIS_ATOM,
                "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1",
            ),
        ]
        for basis_atom, expected_policy_id in cases:
            with self.subTest(policy_id=expected_policy_id):
                x = atom(basis_atom)
                out = p3.solve(
                    {
                        "decision_basis": [basis_atom],
                        "formal_source_constraints": [x],
                        "proposed_refinements": [x],
                    }
                )
                self.assertTrue(out["pass"], out)
                self.assertEqual(
                    out["status"],
                    "COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS",
                )
                self.assertEqual(out["selected_policy_id"], expected_policy_id)
                self.assertIn(
                    expected_policy_id,
                    out["policy_adequacy_registry"]["injected_policy_ids"],
                )

    def test_registry_presence_does_not_self_certify_membership(self):
        out = p3.solve({"decision_basis": [P2_ATOM]})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "AUTHENTICATED_POLICY_COVER_INCOMPLETE")
        uncovered = out["detail"]["uncovered_models"]
        self.assertTrue(
            any(row["valuation"].get(P2_ATOM) is False for row in uncovered),
            uncovered,
        )
        self.assertFalse(
            out["policy_adequacy_registry"]["membership_self_certified"]
        )

    def test_multiple_registered_cells_can_coexist_without_condition_widening(self):
        out = registry.augment_problem(
            {"decision_basis": [P2_ATOM, P3_BINARY_ATOM, SYNTHESIS_ATOM]}
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["basis_eligible_policy_count"], 3)
        self.assertEqual(len(out["injected_policy_ids"]), 3)
        for policy_id, condition in out["problem"]["policy_conditions"].items():
            registered = registry._REGISTRY[policy_id]["condition"]
            self.assertEqual(condition, registered)

    def test_registry_rejects_symlink_escape_before_reading_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            allowed = root / "canonical" / "governance"
            allowed.mkdir(parents=True)
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            link = allowed / "link.json"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("symlink creation unavailable")
            value, error = registry._load_registered_binding(
                "TEST_POLICY",
                {
                    "binding_path": "canonical/governance/link.json",
                    "binding_blob_sha": "0" * 40,
                    "condition": atom(P2_ATOM),
                },
                root=root,
            )
            self.assertIsNone(value)
            self.assertTrue(
                str(error).startswith("REGISTERED_BINDING_SYMLINK_FORBIDDEN:"),
                error,
            )

    def test_p3_adequacy_evidence_loader_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            allowed = root / "canonical" / "governance"
            allowed.mkdir(parents=True)
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            link = allowed / "link.json"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with patch.object(p3, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "BOUND_SYMLINK_FORBIDDEN"):
                    p3._bound_path(
                        "canonical/governance/link.json",
                        prefixes=("canonical/governance/",),
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
