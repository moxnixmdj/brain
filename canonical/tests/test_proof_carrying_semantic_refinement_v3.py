import unittest

from canonical.runtime.certified_deontic_rule_fragment_v1 import parse_deontic_rule
from canonical.runtime.source_aligned_semantic_proof_v3 import verify_proof
from canonical.runtime.proof_carrying_semantic_refinement_v3 import resolve_from_source_proof


class ProofCarryingSemanticRefinementV3Tests(unittest.TestCase):
    def _claim(self, p):
        scope=p.get("scope")
        return {
            "claim_id":"d",
            "kind":"DEONTIC_RULE",
            "rule_id":p["rule_id"],
            "relation":p["relation"],
            "subject_span":p["subject_span"],
            "action_span":p["action_span"],
            "scope_id":scope.get("scope_id") if scope else None,
            "scope_relation":scope.get("relation") if scope else None,
            "condition_span":scope.get("condition_span") if scope else None,
        }

    def test_checked_obligation_can_certify_matching_policy_atom(self):
        text="The operator must archive the record."
        p=parse_deontic_rule(text,source="s")
        checked=verify_proof(text,source_id="s",claims=[self._claim(p)])
        atom=checked["proved_constraint_ids"][0]
        out=resolve_from_source_proof(
            text,source_id="s",claims=[self._claim(p)],
            decision_basis=[atom],
            policy_conditions={"archive":{"op":"ATOM","id":atom}},
        )
        self.assertEqual(out["status"],"COMMON_POLICY_CERTIFIED")
        self.assertEqual(out["certified_common_policies"],["archive"])

    def test_unproved_obligation_cannot_certify_policy(self):
        text="The operator must archive the record."
        p=parse_deontic_rule(text,source="s")
        checked=verify_proof(text,source_id="s",claims=[self._claim(p)])
        atom=checked["proved_constraint_ids"][0]
        out=resolve_from_source_proof(
            text,source_id="s",claims=[],
            decision_basis=[atom],
            policy_conditions={"archive":{"op":"ATOM","id":atom}},
        )
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertEqual(out["certified_common_policies"],[])

    def test_wrong_scope_cannot_certify_policy(self):
        text="If the input is complete, The operator must archive the record."
        p=parse_deontic_rule(text,source="s")
        good=self._claim(p)
        checked=verify_proof(text,source_id="s",claims=[good])
        atom=checked["proved_constraint_ids"][0]
        bad=dict(good); bad["scope_relation"]="UNLESS"
        out=resolve_from_source_proof(
            text,source_id="s",claims=[bad],
            decision_basis=[atom],
            policy_conditions={"archive":{"op":"ATOM","id":atom}},
        )
        self.assertEqual(out["status"],"UNRESOLVED")
        self.assertEqual(out["certified_common_policies"],[])


if __name__=="__main__":
    unittest.main()
