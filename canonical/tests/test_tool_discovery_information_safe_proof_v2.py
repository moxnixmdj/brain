from __future__ import annotations

import inspect
import json
import unittest

from canonical.runtime import tool_discovery_information_safe_candidate as candidate
from canonical.runtime import tool_discovery_information_safe_proof_v2 as proof


class ToolDiscoveryInformationSafeV2Tests(unittest.TestCase):
    def test_information_boundary_remains_hidden(self):
        case=proof.generate_case(2026,5)
        public=proof.public_stage(case,1)
        self.assertNotIn("_oracle",public)
        text=json.dumps(public).lower()
        self.assertNotIn("epoch0",text)
        self.assertNotIn("epoch1",text)
        src=inspect.getsource(candidate)
        self.assertNotIn("tool_discovery_information_safe_proof",src)
        self.assertNotIn("_oracle",src)

    def test_all_six_semantic_classes_pass(self):
        out=proof.run_batch(2026,60,candidate.next_action)
        self.assertTrue(out["all_pass"],out)
        self.assertEqual(set(out["by_class"]),set(proof.CLASSES))

    def test_unavailable_cheaper_tool_is_excluded(self):
        case=proof.generate_case(77,3)
        result=proof.score_episode(case,candidate.next_action)
        self.assertTrue(result["pass"],result)
        self.assertNotEqual(result["stage1"]["selected"],case["tools"][0]["tool_id"])

    def test_unauthorized_cheaper_tool_is_excluded(self):
        case=proof.generate_case(77,4)
        result=proof.score_episode(case,candidate.next_action)
        self.assertTrue(result["pass"],result)
        self.assertNotEqual(result["stage1"]["selected"],case["tools"][0]["tool_id"])

    def test_no_sufficient_route_escalates_after_evidence(self):
        case=proof.generate_case(77,5)
        result=proof.score_episode(case,candidate.next_action)
        self.assertTrue(result["pass"],result)
        self.assertEqual(result["stage1"]["reason"],"PASS_ESCALATE_NO_SUFFICIENT_ROUTE")
        self.assertGreater(result["stage1"]["probe_count"],0)

    def test_premature_escalation_fails(self):
        case=proof.generate_case(88,0)
        result=proof.score_episode(case,lambda public:{"action":"ESCALATE"})
        self.assertFalse(result["pass"],result)


if __name__=="__main__":
    unittest.main(verbosity=2)
