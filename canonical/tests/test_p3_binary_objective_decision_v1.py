import unittest
from canonical.runtime.p3_binary_objective_decision_v1 import evaluate


def base():
    return {
      "objective":"Determine whether thermal conductivity of AISI type 304 stainless steel is higher than thermal conductivity of 6061 aluminum.",
      "claims":[
        {"claim_id":"left","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","required":False},
        {"claim_id":"right","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","required":False},
      ],
      "evidence":[
        {"evidence_id":"E1","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","verified":True,"provenance":[{"source_id":"S1","locator":"p1"}]},
        {"evidence_id":"E2","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","verified":True,"provenance":[{"source_id":"S2","locator":"p2"}]},
      ],
    }


class Tests(unittest.TestCase):
    def test_false_comparison_is_derived(self):
        out=evaluate(base())
        self.assertTrue(out["pass"],out)
        self.assertIs(out["decision_truth"],False)
        self.assertEqual(out["operator"],"GT")
        self.assertTrue(out["required_decision_semantics_covered"])
        self.assertFalse(out["decision_expression_covered"])
        self.assertEqual({p["source_id"] for p in out["decision_provenance"]},{"S1","S2"})

    def test_reversing_objective_roles_changes_truth(self):
        p=base()
        p["objective"]="Determine whether thermal conductivity of 6061 aluminum is higher than thermal conductivity of AISI type 304 stainless steel."
        out=evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertIs(out["decision_truth"],True)

    def test_claim_input_order_irrelevant(self):
        p=base();p["claims"].reverse()
        out=evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertIs(out["decision_truth"],False)

    def test_model_numbers_do_not_win_over_shared_explicit_unit_pair(self):
        out=evaluate(base())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["left_operand"]["value"],"16")
        self.assertEqual(out["right_operand"]["value"],"167")
        self.assertEqual(out["left_operand"]["unit"],"w/mk")
        self.assertEqual(out["right_operand"]["unit"],"w/mk")

    def test_unrelated_numeric_decoy_is_excluded_by_role_binding(self):
        p=base()
        p["evidence"].append({"evidence_id":"D","text":"Office count is 999 W/mK.","verified":True,"provenance":[{"source_id":"D"}]})
        out=evaluate(p)
        self.assertTrue(out["pass"],out)
        self.assertIs(out["decision_truth"],False)

    def test_duplicate_role_evidence_fails_closed(self):
        p=base()
        p["evidence"].append({"evidence_id":"E3","text":"Thermal conductivity of AISI type 304 stainless steel is 17 W/mK.","verified":True,"provenance":[{"source_id":"S3"}]})
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"OBJECTIVE_ROLE_RELEVANCE_UNRESOLVED")

    def test_unit_mismatch_fails_closed(self):
        p=base()
        p["evidence"][1]["text"]="Thermal conductivity of 6061 aluminum is 167 BTU."
        p["claims"][1]["text"]=p["evidence"][1]["text"]
        out=evaluate(p)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"OBJECTIVE_RELATION_BINDING_FAILED")

    def test_unverified_evidence_fails_closed(self):
        p=base();p["evidence"][0]["verified"]=False
        out=evaluate(p)
        self.assertFalse(out["pass"])

    def test_no_authority_escalation(self):
        out=evaluate(base())
        self.assertTrue(out["pass"],out)
        for k in ("policy_adequacy_authority","db_admission_authority","u_subtraction_authority","terminal_authority"):
            self.assertFalse(out[k])
        self.assertEqual(out["terminal_credit_delta"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
