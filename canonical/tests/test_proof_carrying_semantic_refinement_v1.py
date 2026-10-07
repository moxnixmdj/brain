import unittest

from canonical.runtime.semantic_operator_counterfactuals import extract_semantic_operators
from canonical.runtime.source_aligned_semantic_proof_v1 import verify_proof
from canonical.runtime.proof_carrying_semantic_refinement_v1 import resolve_from_source_proof


class ProofCarryingSemanticRefinementTests(unittest.TestCase):
    def test_checked_operator_fact_can_discharge_matching_policy_atom(self):
        text = "Apply the rule unless the exception holds."
        op = extract_semantic_operators(text, source="s")[0]
        claim = {
            "claim_id": "c1",
            "kind": "OPERATOR_CLASS",
            "operator_id": op.operator_id,
            "semantic_class": "CONDITIONAL_UNLESS",
        }
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

    def test_unproved_high_level_atom_stays_unresolved(self):
        text = "The transaction qualifies."
        out = resolve_from_source_proof(
            text,
            source_id="s",
            claims=[{
                "claim_id": "guess",
                "kind": "SEMANTIC_MEANING",
                "meaning": "EXCEPTION_C_APPLIES",
            }],
            decision_basis=["EXCEPTION_C_APPLIES"],
            policy_conditions={"p": {"op": "ATOM", "id": "EXCEPTION_C_APPLIES"}},
        )
        self.assertEqual(out["status"], "UNRESOLVED")
        self.assertEqual(out["certified_common_policies"], [])

    def test_omitted_provable_claim_stays_unresolved(self):
        text = "Exposure must be at least 3."
        op = next(x for x in extract_semantic_operators(text, source="s") if x.semantic_class == "MIN_INCLUSIVE")
        checked = verify_proof(
            text,
            source_id="s",
            claims=[{
                "claim_id": "bound",
                "kind": "OPERATOR_BOUND",
                "operator_id": op.operator_id,
                "semantic_class": "MIN_INCLUSIVE",
                "bound_value": 3,
            }],
        )
        atom_id = checked["proved_constraint_ids"][0]
        out = resolve_from_source_proof(
            text,
            source_id="s",
            claims=[],
            decision_basis=[atom_id],
            policy_conditions={"p": {"op": "ATOM", "id": atom_id}},
        )
        self.assertEqual(out["status"], "UNRESOLVED")
        self.assertEqual(out["semantic_refinement"]["model_count"], 2)


if __name__ == "__main__":
    unittest.main()
