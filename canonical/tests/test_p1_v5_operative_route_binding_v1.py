from __future__ import annotations
import copy
import unittest
from canonical.runtime import p1_v5_operative_route_binding_v1 as gate

class Tests(unittest.TestCase):
    def test_live_binding_passes_but_grants_zero_credit(self):
        out=gate.evaluate()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["source_gate_v2_pass"])
        self.assertEqual(out["candidate_model_dependency_count"],0)
        self.assertFalse(out["external_hidden_target_capability_provider"])
        self.assertFalse(out["p1_whole_scope_restored"])
        self.assertFalse(out["terminal_credit_authorized"])
        self.assertFalse(out["family_credit_authorized"])
        self.assertFalse(out["promotion_authority"])

    def test_entrypoint_drift_fails_closed(self):
        b=copy.deepcopy(gate._load(gate.BINDING))
        b["entrypoint"]="some.external.provider:solve"
        out=gate.evaluate(b)
        self.assertFalse(out["pass"])
        self.assertIn("ENTRYPOINT_DRIFT",out["errors"])

    def test_hidden_provider_fails_source_gate(self):
        b=copy.deepcopy(gate._load(gate.BINDING))
        b["source_gate"]["route_input"]["external_hidden_target_capability_provider"]=True
        out=gate.evaluate(b)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("SOURCE_GATE_V2_REJECTED:") for x in out["errors"]))

    def test_premature_whole_scope_flag_fails_closed(self):
        b=copy.deepcopy(gate._load(gate.BINDING))
        b["current_claim"]["p1_whole_scope_restored"]=True
        out=gate.evaluate(b)
        self.assertFalse(out["pass"])
        self.assertIn("PREMATURE_CREDIT_OR_SCOPE_FLAG:p1_whole_scope_restored",out["errors"])

    def test_premature_family_credit_fails_closed(self):
        b=copy.deepcopy(gate._load(gate.BINDING))
        b["current_claim"]["family_credit_authorized"]=True
        out=gate.evaluate(b)
        self.assertFalse(out["pass"])
        self.assertIn("PREMATURE_CREDIT_OR_SCOPE_FLAG:family_credit_authorized",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
