from __future__ import annotations

import unittest

from canonical.runtime import r2_basis_discriminator_repair_v1 as repair


class R2BasisDiscriminatorRepairV1Tests(unittest.TestCase):
    def _request(self, discriminators=None):
        return {
            "task_id": "t",
            "goal": "g",
            "decision_payload": {
                "context_id": "ctx",
                "bound_relevance_cegar_loop": {
                    "cegar_problem": {
                        "decision_basis": ["x", "y"],
                        "policy_conditions": {},
                        "discriminators": list(discriminators or []),
                    },
                    "truth_payloads_by_discriminator_id": {},
                    "truth_payloads_by_predicate_id": {},
                    "source_positive_selection_contracts": {},
                },
            },
        }

    def _policy_request(self, witness=None):
        witness = witness or [
            {
                "model_id": "m0",
                "valuation": {"x": False, "y": False},
                "adequate_policy_ids": ["p0"],
            },
            {
                "model_id": "m1",
                "valuation": {"x": True, "y": False},
                "adequate_policy_ids": ["p1"],
            },
        ]
        return {
            "required_artifact": repair.SUPPORTED_ARTIFACT,
            "search_context": {
                "decision_basis": ["x", "y"],
                "conflicting_policy_region_witness": witness,
            },
        }

    def test_only_differing_basis_atoms_become_candidate_questions(self):
        out = repair.repair(self._request(), self._policy_request())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["added_basis_atoms"], ["x"])
        rows = out["request_patch"]["decision_payload"][
            "bound_relevance_cegar_loop"
        ]["cegar_problem"]["discriminators"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["formula"], {"op": "ATOM", "id": "x"})
        self.assertNotIn("cost_units", rows[0])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertTrue(out["downstream_cegar_reverification_required"])
        self.assertTrue(out["downstream_truth_observation_required_if_selected"])

    def test_existing_atom_partition_is_not_duplicated(self):
        existing = [
            {
                "discriminator_id": "already-x",
                "formula": {"op": "NOT", "arg": {"op": "ATOM", "id": "x"}},
                "cost_units": 7,
            }
        ]
        out = repair.repair(self._request(existing), self._policy_request())
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "UNRESOLVED__NO_NEW_BASIS_DISCRIMINATOR_CANDIDATE",
        )

    def test_non_disjoint_policy_sets_are_not_a_conflict_witness(self):
        witness = [
            {
                "model_id": "m0",
                "valuation": {"x": False, "y": False},
                "adequate_policy_ids": ["shared"],
            },
            {
                "model_id": "m1",
                "valuation": {"x": True, "y": False},
                "adequate_policy_ids": ["shared"],
            },
        ]
        out = repair.repair(self._request(), self._policy_request(witness))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "CONFLICT_WITNESS_POLICY_SETS_NOT_DISJOINT")

    def test_identical_valuations_cannot_generate_a_separator(self):
        witness = [
            {
                "model_id": "m0",
                "valuation": {"x": False, "y": False},
                "adequate_policy_ids": ["p0"],
            },
            {
                "model_id": "m1",
                "valuation": {"x": False, "y": False},
                "adequate_policy_ids": ["p1"],
            },
        ]
        out = repair.repair(self._request(), self._policy_request(witness))
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["reason"],
            "CONFLICT_WITNESS_HAS_NO_DIFFERING_DECISION_BASIS_ATOM",
        )

    def test_unrelated_gap_abstains(self):
        request = self._policy_request()
        request["required_artifact"] = "POSITIVE_POLICY_ADEQUACY_CERTIFICATE"
        out = repair.repair(self._request(), request)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "NOT_APPLICABLE__POLICY_ARTIFACT_NOT_BASIS_DISCRIMINATOR_GAP",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
