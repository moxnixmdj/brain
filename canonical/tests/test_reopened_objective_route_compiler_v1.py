import unittest
from canonical.runtime.reopened_objective_route_compiler_v1 import evaluate

class Tests(unittest.TestCase):
    def fixture(self):
        reg={"predicates":[
            {"id":"M1","kind":"MATCHED_NONINFERIORITY"},
            {"id":"M2","kind":"MATCHED_SCOPE_AUDIT"},
            {"id":"P","kind":"PUBLIC_FIXED_BAR"},
        ]}
        spec={
            "required_gate_status":"PASS_GATE",
            "routes":[
                {"id":"R1","behavior_id":"B1","scope_relation":"FULL_PROTOCOL_REPLACEMENT_CANDIDATE","target_predicates":["M1"]},
                {"id":"R2","behavior_id":"B2","scope_relation":"PARTIAL_ONLY","target_predicates":[]},
            ],
        }
        gate={"status":"PASS_GATE"}
        return reg,spec,gate

    def test_candidate_never_gets_credit(self):
        out=evaluate(*self.fixture())
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["candidate_predicates"],["M1"])
        self.assertEqual(out["routes"][0]["state"],"TERMINAL_EVIDENCE_REQUIRED")
        self.assertFalse(out["promotion_authority"])

    def test_gate_mismatch_fails(self):
        reg,spec,gate=self.fixture()
        gate["status"]="OTHER"
        out=evaluate(reg,spec,gate)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["candidate_predicates"],[])

    def test_public_target_rejected(self):
        reg,spec,gate=self.fixture()
        spec["routes"][0]["target_predicates"]=["P"]
        out=evaluate(reg,spec,gate)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertTrue(any(x.startswith("TARGET_NOT_MATCHED") for x in out["errors"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
