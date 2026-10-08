from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import p3_conditioned_policy_adequacy_registry_v1 as registry
from canonical.runtime import p3_robust_policy_adequacy_cegar_v1 as p3


ATOM = "SYNTHESIS_TYPED_VISIBLE_SUPPORT_COMMON_POLICY_TOP_LAW_V1"
POLICY = "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1"


def atom():
    return {"op": "ATOM", "id": ATOM}


class P3ConditionedPolicyAdequacyRegistryV1Tests(unittest.TestCase):
    def test_catalog_contains_existing_synthesis_cell_only(self):
        out = registry.catalog()
        self.assertEqual(out["policy_count"], 1)
        self.assertEqual(out["policies"][0]["policy_id"], POLICY)
        self.assertEqual(out["policies"][0]["condition"], atom())
        self.assertFalse(out["membership_self_certified"])

    def test_unrelated_basis_injects_nothing(self):
        out = registry.augment_problem({"decision_basis": ["unrelated"]})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["injected_policy_ids"], [])
        self.assertEqual(out["basis_eligible_policy_count"], 0)
        self.assertEqual(out["problem"]["policy_conditions"], {})
        self.assertEqual(out["problem"]["policy_adequacy_bindings"], {})

    def test_exact_condition_atom_injects_existing_binding(self):
        out = registry.augment_problem({"decision_basis": [ATOM]})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["injected_policy_ids"], [POLICY])
        self.assertEqual(out["problem"]["policy_conditions"][POLICY], atom())
        binding = out["problem"]["policy_adequacy_bindings"][POLICY]
        self.assertEqual(
            set(binding),
            {
                "adequacy_certificate_path",
                "adequacy_certificate_blob_sha",
                "independent_verification_path",
                "independent_verification_blob_sha",
            },
        )

    def test_caller_cannot_override_registered_condition(self):
        out = registry.augment_problem(
            {
                "decision_basis": [ATOM, "other"],
                "policy_conditions": {
                    POLICY: {"op": "ATOM", "id": "other"}
                },
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "CALLER_POLICY_CONDITION_CONFLICTS_WITH_REGISTERED_ADEQUACY",
        )

    def test_caller_cannot_override_registered_binding(self):
        out = registry.augment_problem(
            {
                "decision_basis": [ATOM],
                "policy_conditions": {POLICY: atom()},
                "policy_adequacy_bindings": {
                    POLICY: {
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

    def test_registered_binding_drift_fails_closed(self):
        mutated = copy.deepcopy(registry._REGISTRY)
        mutated[POLICY]["binding_blob_sha"] = "0" * 40
        with patch.object(registry, "_REGISTRY", mutated):
            out = registry.augment_problem({"decision_basis": [ATOM]})
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "REGISTERED_POLICY_ADEQUACY_BINDING_INVALID",
        )

    def test_registered_binding_symlink_escape_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            allowed = root / "canonical" / "governance"
            allowed.mkdir(parents=True)
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            link = allowed / "binding.json"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("symlink creation unavailable")
            mutated = copy.deepcopy(registry._REGISTRY)
            mutated[POLICY]["binding_path"] = "canonical/governance/binding.json"
            mutated[POLICY]["binding_blob_sha"] = registry._git_blob_sha(outside)
            with patch.object(registry, "_REGISTRY", mutated):
                out = registry.augment_problem(
                    {"decision_basis": [ATOM]},
                    repo_root=root,
                )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "REGISTERED_POLICY_ADEQUACY_BINDING_INVALID",
        )
        self.assertIn(
            "REGISTERED_BINDING_SYMLINK_FORBIDDEN",
            out["detail"]["binding_error"],
        )

    def test_p3_evidence_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            allowed = root / "canonical" / "governance"
            allowed.mkdir(parents=True)
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            link = allowed / "cert.json"
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("symlink creation unavailable")
            old_root = p3.ROOT
            p3.ROOT = root
            try:
                with self.assertRaisesRegex(ValueError, "BOUND_SYMLINK_FORBIDDEN"):
                    p3._bound_path(
                        "canonical/governance/cert.json",
                        prefixes=("canonical/governance/",),
                    )
            finally:
                p3.ROOT = old_root

    def test_p3_authenticates_registered_cell_when_source_refinement_proves_condition(self):
        x = atom()
        out = p3.solve(
            {
                "decision_basis": [ATOM],
                "formal_source_constraints": [x],
                "proposed_refinements": [x],
            }
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS",
        )
        self.assertEqual(out["selected_policy_id"], POLICY)
        self.assertEqual(
            out["conditioned_policy_adequacy_registry"]["injected_policy_ids"],
            [POLICY],
        )

    def test_registry_presence_alone_does_not_self_certify_condition(self):
        out = p3.solve({"decision_basis": [ATOM]})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "AUTHENTICATED_POLICY_COVER_INCOMPLETE")
        uncovered = out["detail"]["uncovered_models"]
        self.assertTrue(
            any(row["valuation"].get(ATOM) is False for row in uncovered),
            uncovered,
        )
        self.assertFalse(
            out["conditioned_policy_adequacy_registry"]["membership_self_certified"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
