import unittest
from canonical.runtime.shared_residual_contract_gate import admit_mechanism_target

FIELDS={
 "inputs":"i","environment_state":"s","allowed_information":"a",
 "required_output_or_action":"o","success_condition":"ok","failure_condition":"bad",
 "terminal_consequence":"t","verification_route":"v","dependency_boundary":"d","scope":"q",
}

class Tests(unittest.TestCase):
    def test_unregistered_label_is_not_implementation_target(self):
        reg={"active_contracted_residuals":[]}
        out=admit_mechanism_target("S0_RAW_CONTEXT_TO_TYPED_FACT_TEMPLATE_AND_EFFECT_MODEL",reg)
        self.assertFalse(out["admitted"])
        self.assertEqual(out["status"],"SPECIFICATION_REQUIRED")

    def test_complete_behavior_is_admitted(self):
        row={"behavior_id":"B",**FIELDS}
        out=admit_mechanism_target("B",{"active_contracted_residuals":[row]})
        self.assertTrue(out["admitted"])

    def test_duplicate_registered_behavior_fails_closed(self):
        row={"behavior_id":"B",**FIELDS}
        out=admit_mechanism_target("B",{"active_contracted_residuals":[row,dict(row)]})
        self.assertFalse(out["admitted"])
        self.assertEqual(out["status"],"SPECIFICATION_REQUIRED")

    def test_incomplete_behavior_is_blocked(self):
        row={"behavior_id":"B",**FIELDS}; del row["success_condition"]
        out=admit_mechanism_target("B",{"active_contracted_residuals":[row]})
        self.assertFalse(out["admitted"])
        self.assertIn("success_condition",out["missing_fields"])

if __name__=="__main__": unittest.main()
