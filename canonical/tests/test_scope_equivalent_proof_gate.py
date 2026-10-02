import unittest
from canonical.runtime.scope_equivalent_proof_gate import evaluate

def valid():
    return {
      "source_private_or_nonexecutable_surface":"PRIVATE_X",
      "candidate_proof_route":"ABSOLUTE_Y",
      "required_behavior_ids":["B1","B2"],
      "candidate_behavior_ids":["B1","B2","B3"],
      "required_interaction_ids":["I1"],
      "candidate_interaction_ids":["I1","I2"],
      "proof_mode":"THEORETICAL_CEILING",
      "population_relation":"CANDIDATE_SUPERSET_PROVEN",
      "environment_relation":"CANDIDATE_STRICTER_PROVEN",
      "oracle_relation":"CANDIDATE_STRONGER_PROVEN",
      "relation_receipts":{"population":"p.json","environment":"e.json","oracle":"o.json"},
      "unresolved_required_dimensions":[],
      "required_subjective_quality_dimensions":["presentation_quality"],
      "candidate_subjective_quality_dimensions":["presentation_quality"],
      "zero_incremental_spend":True,
      "independent_acceptance":True,
      "contamination_safe":True,
      "candidate_route_owned_or_noncapability_jit_only":True,
      "opaque_target_capability_provider":False,
      "target_weakened":False,
    }

class GateTests(unittest.TestCase):
    def test_valid_stronger_route(self):
        self.assertTrue(evaluate(valid())["admissible"])
    def test_missing_behavior_fails(self):
        x=valid(); x["candidate_behavior_ids"]=["B1"]
        self.assertFalse(evaluate(x)["admissible"])
    def test_missing_interaction_fails(self):
        x=valid(); x["candidate_interaction_ids"]=["I2"]
        self.assertFalse(evaluate(x)["admissible"])
    def test_nonexact_relation_needs_receipt(self):
        x=valid(); x["relation_receipts"].pop("population")
        self.assertFalse(evaluate(x)["admissible"])
    def test_subjective_quality_cannot_be_dropped(self):
        x=valid(); x["candidate_subjective_quality_dimensions"]=[]
        self.assertFalse(evaluate(x)["admissible"])
    def test_opaque_provider_fails(self):
        x=valid(); x["opaque_target_capability_provider"]=True
        self.assertFalse(evaluate(x)["admissible"])
    def test_target_weakening_fails(self):
        x=valid(); x["target_weakened"]=True
        self.assertFalse(evaluate(x)["admissible"])
    def test_unknown_proof_mode_fails(self):
        x=valid(); x["proof_mode"]="TRUST_ME"
        self.assertFalse(evaluate(x)["admissible"])
    def test_unresolved_dimension_fails(self):
        x=valid(); x["unresolved_required_dimensions"]=["hidden_quality"]
        self.assertFalse(evaluate(x)["admissible"])

if __name__=="__main__":
    unittest.main()
