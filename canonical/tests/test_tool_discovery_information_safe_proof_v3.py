from __future__ import annotations

import inspect,json,unittest
from canonical.runtime import tool_discovery_information_safe_candidate_v3 as candidate
from canonical.runtime import tool_discovery_information_safe_proof_v3 as proof

class Tests(unittest.TestCase):
    def test_information_boundary(self):
        case=proof.generate_case(4401,0)
        public=proof.public_initial(case)
        self.assertNotIn("_oracle",public)
        raw=json.dumps(public).lower()
        self.assertNotIn("epoch0",raw);self.assertNotIn("epoch1",raw)
        src=inspect.getsource(candidate)
        self.assertNotIn("tool_discovery_information_safe_proof_v3",src)
        self.assertNotIn("_oracle",src)

    def test_all_six_classes(self):
        out=proof.run_batch(4401,120,candidate.next_action)
        self.assertTrue(out["all_pass"],out["failures"][:10])
        self.assertEqual(set(out["by_class"]),set(proof.CLASSES))

    def test_dynamic_discovery_is_load_bearing(self):
        case=proof.generate_case(77,0)
        first=candidate.next_action(proof.public_initial(case))
        self.assertEqual(first["action"],"DISCOVER")

    def test_constraints_exclude_cheapest_hidden_capable_tool(self):
        case=proof.generate_case(77,1)
        out=proof.score_episode(case,candidate.next_action)
        self.assertTrue(out["pass"],out)
        self.assertNotEqual(out["stage1"]["selected"],case["pages"][0][1]["tool_id"])

    def test_no_route_escalates_after_negative_evidence(self):
        case=proof.generate_case(77,5)
        out=proof.score_episode(case,candidate.next_action)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["stage1"]["reason"],"PASS_ESCALATE")

    def test_constraint_dsl_fail_closed_on_unknown(self):
        public=proof.public_initial(proof.generate_case(77,0))
        public["catalog_complete"]=True
        public["active_constraints"]=[{"field":"region","op":"mystery","value":"eu"}]
        self.assertEqual(candidate.next_action(public)["action"],"ESCALATE")

if __name__=="__main__":
    unittest.main(verbosity=2)
