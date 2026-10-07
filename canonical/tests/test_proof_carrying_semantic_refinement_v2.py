import unittest

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.source_aligned_semantic_proof_v2 import verify_proof
from canonical.runtime.proof_carrying_semantic_refinement_v2 import resolve_from_source_proof


class ProofCarryingSemanticRefinementV2Tests(unittest.TestCase):
    def _scope_claim(self, p):
        return {
            "claim_id": "scope",
            "kind": "SCOPE_RELATION",
            "scope_id": p["scope_id"],
            "relation": p["relation"],
            "operator_id": p["operator_id"],
            "left_role": p["left_role"],
            "left_span": p["left_span"],
            "right_role": p["right_role"],
            "right_span": p["right_span"],
        }

    def test_certified_scope_can_discharge_matching_policy_atom(self):
        text = "Apply the rule unless the exception holds."
        p = parse_scope(text, source="s")["parse"]
        claim = self._scope_claim(p)
        checked = verify_proof(text, source_id="s", claims=[claim])
        atom_id = checked["proved_constraint_ids"][0]
        out = resolve_from_source_proof(
            text,
            source_id="s",
            claims=[claim],
            decision_basis=[atom_id],
            policy_conditions={"p": {"op": "ATOM", "id": atom_id}},
        )
        self.assertEqual(out["status"], "COMMON_POLICY_CERTIFIED")
        self.assertEqual(out["certified_common_policies"], ["p"])

    def test_omitted_scope_claim_remains_unresolved(self):
        text = "Apply the rule unless the exception holds."
        p = parse_scope(text, source="s")["parse"]
        checked = verify_proof(text, source_id="s", claims=[self._scope_claim(p)])
        atom_id = checked["proved_constraint_ids"][0]
        out = resolve_from_source_proof(
            text,
            source_id="s",
            claims=[],
            decision_basis=[atom_id],
            policy_conditions={"p": {"op": "ATOM", "id": atom_id}},
        )
        self.assertEqual(out["status"], "UNRESOLVED")

    def test_wrong_scope_claim_cannot_discharge_policy(self):
        text = "Apply the rule unless the exception holds."
        p = parse_scope(text, source="s")["parse"]
        claim = self._scope_claim(p)
        claim["left_role"], claim["right_role"] = claim["right_role"], claim["left_role"]
        correct = self._scope_claim(p)
        checked = verify_proof(text, source_id="s", claims=[correct])
        atom_id = checked["proved_constraint_ids"][0]
        out = resolve_from_source_proof(
            text,
            source_id="s",
            claims=[claim],
            decision_basis=[atom_id],
            policy_conditions={"p": {"op": "ATOM", "id": atom_id}},
        )
        self.assertEqual(out["status"], "UNRESOLVED")
        self.assertEqual(out["certified_common_policies"], [])


if __name__ == "__main__":
    unittest.main()
