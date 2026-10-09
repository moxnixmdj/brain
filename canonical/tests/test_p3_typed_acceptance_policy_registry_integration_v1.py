from __future__ import annotations

import unittest

from canonical.runtime import p3_conditioned_policy_adequacy_registry_v1 as registry
from canonical.runtime import p3_robust_policy_adequacy_cegar_v1 as p3

POLICY = "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
ATOMS = [
    "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1",
    "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1",
    "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1",
    "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1",
    "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
]

def condition():
    return {
        "op": "AND",
        "args": [{"op": "ATOM", "id": atom} for atom in ATOMS],
    }

class Tests(unittest.TestCase):
    def test_catalog_exposes_exact_specialist_condition_without_membership_authority(self):
        out = registry.catalog()
        by_id = {row["policy_id"]: row for row in out["policies"]}
        self.assertIn(POLICY, by_id)
        self.assertEqual(by_id[POLICY]["condition"], condition())
        self.assertFalse(out["membership_self_certified"])
        self.assertFalse(out["terminal_authority"])

    def test_all_five_basis_atoms_are_required_before_registry_injection(self):
        for missing in ATOMS:
            basis = [x for x in ATOMS if x != missing]
            out = registry.augment_problem({"decision_basis": basis})
            self.assertTrue(out["pass"], out)
            self.assertNotIn(POLICY, out["injected_policy_ids"])
            skipped = {x["policy_id"]: x for x in out["skipped_registered_policies"]}
            self.assertIn(POLICY, skipped)
            self.assertIn(missing, skipped[POLICY]["missing_atoms"])

        out = registry.augment_problem({"decision_basis": list(ATOMS)})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["injected_policy_ids"], [POLICY])
        self.assertEqual(out["problem"]["policy_conditions"][POLICY], condition())
        self.assertIn(POLICY, out["problem"]["policy_adequacy_bindings"])

    def test_registry_presence_does_not_prove_five_atom_condition_true(self):
        out = p3.solve({"decision_basis": list(ATOMS)})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "AUTHENTICATED_POLICY_COVER_INCOMPLETE")
        self.assertFalse(
            out["conditioned_policy_adequacy_registry"]["membership_self_certified"]
        )

    def test_source_authorized_truth_for_all_five_atoms_can_reuse_specialist_policy(self):
        constraints = [{"op": "ATOM", "id": atom} for atom in ATOMS]
        out = p3.solve(
            {
                "decision_basis": list(ATOMS),
                "formal_source_constraints": constraints,
                "proposed_refinements": constraints,
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

    def test_partial_truth_cannot_select_specialist_policy(self):
        constraints = [{"op": "ATOM", "id": atom} for atom in ATOMS[:-1]]
        out = p3.solve(
            {
                "decision_basis": list(ATOMS),
                "formal_source_constraints": constraints,
                "proposed_refinements": constraints,
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "AUTHENTICATED_POLICY_COVER_INCOMPLETE")

if __name__ == "__main__":
    unittest.main(verbosity=2)
