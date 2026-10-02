import unittest

from canonical.runtime.scope_equivalent_proof_gate_v2 import evaluate


def base():
    return {
        "source_private_or_nonexecutable_surface":"X",
        "candidate_proof_route":"Y",
        "required_behavior_ids":["B"],
        "candidate_behavior_ids":["B"],
        "required_interaction_ids":["I"],
        "candidate_interaction_ids":["I"],
        "proof_mode":"ABSOLUTE_BEHAVIORAL_PROTOCOL",
        "population_relation":"EXACT",
        "environment_relation":"EXACT",
        "oracle_relation":"EXACT",
        "relation_receipts":{},
        "candidate_information_relation":"EXACT_CANDIDATE_VISIBLE_INFORMATION",
        "required_inference_ids":["J"],
        "candidate_visible_derived_or_oracle_ids":[],
        "hidden_oracle_ids":["J"],
        "anti_shortcut_mutation_ids":["M"],
        "unresolved_required_dimensions":[],
        "required_subjective_quality_dimensions":[],
        "candidate_subjective_quality_dimensions":[],
        "zero_incremental_spend":True,
        "independent_acceptance":True,
        "contamination_safe":True,
        "candidate_route_owned_or_noncapability_jit_only":True,
        "candidate_does_not_receive_hidden_oracle_payload":True,
        "candidate_does_not_receive_reference_solution":True,
        "opaque_target_capability_provider":False,
        "target_weakened":False,
    }


class ScopeEquivalentProofGateV2Tests(unittest.TestCase):
    def test_clean_boundary_passes(self):
        self.assertTrue(evaluate(base())["admissible"])

    def test_load_bearing_judgment_leak_fails(self):
        x=base()
        x["candidate_visible_derived_or_oracle_ids"]=["J"]
        out=evaluate(x)
        self.assertFalse(out["admissible"])
        self.assertIn("J",out["leaked_inference_ids"])

    def test_hidden_oracle_required(self):
        x=base()
        x["hidden_oracle_ids"]=[]
        self.assertFalse(evaluate(x)["admissible"])

    def test_anti_shortcut_mutations_required(self):
        x=base()
        x["anti_shortcut_mutation_ids"]=[]
        self.assertFalse(evaluate(x)["admissible"])

    def test_less_information_requires_receipt(self):
        x=base()
        x["candidate_information_relation"]="CANDIDATE_HAS_STRICTLY_LESS_INFORMATION_PROVEN"
        self.assertFalse(evaluate(x)["admissible"])
        x["relation_receipts"]={"candidate_information":"canonical/verification/r.json"}
        self.assertTrue(evaluate(x)["admissible"])


if __name__=="__main__":
    unittest.main()
