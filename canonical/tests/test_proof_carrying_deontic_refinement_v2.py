import unittest
from unittest.mock import patch

import canonical.runtime.proof_carrying_deontic_refinement_v1 as bridge
from canonical.runtime.certified_deontic_rule_fragment_v1 import parse_deontic_rule

def _claim(text):
    p=parse_deontic_rule(text,source="s")
    s=p.get("scope")
    return {
        "claim_id":"d","kind":"DEONTIC_RULE",
        "rule_id":p["rule_id"],"relation":p["relation"],
        "subject_span":p["subject_span"],"action_span":p["action_span"],
        "scope_id":s.get("scope_id") if s else None,
        "scope_relation":s.get("relation") if s else None,
        "condition_span":s.get("condition_span") if s else None,
    }

class T(unittest.TestCase):
    def test_entailed_true_policy_is_not_adequacy_without_authentication(self):
        text="The operator must archive the record."
        out=bridge.resolve_from_source_proof(
            text,source_id="s",claims=[_claim(text)],
            decision_basis=["A"],
            policy_conditions={"p":{"op":"TRUE"}},
        )
        self.assertEqual(out["status"],"POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED")
        self.assertEqual(out["entailed_policy_conditions"],["p"])
        self.assertEqual(out["certified_common_policies"],[])
        self.assertEqual(out["rejected_policy_adequacy_bindings"][0]["reason"],"ADEQUACY_BINDING_MISSING")

    def test_authenticated_adequacy_is_required_for_common_policy(self):
        text="The operator must archive the record."
        seen={}
        def fake(pid,condition,binding):
            seen["pid"]=pid;seen["condition"]=condition;seen["binding"]=binding
            return True,{"policy_id":pid,"condition_sha256":"x"}
        with patch.object(bridge,"_authenticate_policy_adequacy",side_effect=fake):
            out=bridge.resolve_from_source_proof(
                text,source_id="s",claims=[_claim(text)],
                decision_basis=["A"],
                policy_conditions={"p":{"op":"TRUE"}},
                policy_adequacy_bindings={"p":{"adequacy_certificate_path":"bound"}},
            )
        self.assertEqual(out["status"],"COMMON_POLICY_CERTIFIED")
        self.assertEqual(out["certified_common_policies"],["p"])
        self.assertEqual(seen["pid"],"p")
        self.assertEqual(seen["condition"],{"op":"TRUE"})
        self.assertEqual(seen["binding"],{"adequacy_certificate_path":"bound"})

    def test_deontic_entailment_survives_but_does_not_self_certify_policy(self):
        text="The operator must not publish the draft."
        c=_claim(text)
        p=parse_deontic_rule(text,source="s")
        atom=(
            "DEONTIC_RULE::"+p["rule_id"]+"::"+p["relation"]+"::"+
            p["subject_text_sha256"]+"::"+p["action_text_sha256"]+"::UNSCOPED"
        )
        out=bridge.resolve_from_source_proof(
            text,source_id="s",claims=[c],
            decision_basis=[atom],
            policy_conditions={"obey":{"op":"ATOM","id":atom}},
        )
        self.assertEqual(out["source_proof"]["status"],"PROOF_CHECKED")
        self.assertEqual(out["entailed_policy_conditions"],["obey"])
        self.assertEqual(out["status"],"POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED")
        self.assertEqual(out["certified_common_policies"],[])

if __name__=="__main__":
    unittest.main(verbosity=2)
