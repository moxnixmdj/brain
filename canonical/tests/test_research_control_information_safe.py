from __future__ import annotations
import inspect, json, unittest
from canonical.runtime import research_control_information_safe_candidate as candidate
from canonical.runtime import research_control_information_safe_proof as proof

class ResearchControlInformationSafeTests(unittest.TestCase):
    def test_hidden_source_truth_not_public(self):
        case=proof.generate_case(123,0)
        public=proof.public_state(case)
        self.assertNotIn("_oracle",public)
        raw=json.dumps(public)
        self.assertNotIn("Authoritative evidence for",raw)
        self.assertNotIn("Secondary evidence for",raw)

    def test_candidate_has_no_oracle_dependency(self):
        src=inspect.getsource(candidate)
        self.assertNotIn("research_control_information_safe_proof",src)
        self.assertNotIn("_oracle",src)

    def test_cross_domain_grid(self):
        out=proof.run_batch(2026,60,candidate.next_action)
        self.assertTrue(out["all_pass"],out)
        self.assertEqual(set(out["by_domain"]),set(proof.DOMAINS))

    def test_premature_stop_rejected(self):
        case=proof.generate_case(9,0)
        out=proof.run_episode(case,lambda public:{"action":"STOP"})
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"PREMATURE_STOP")

    def test_irrelevant_query_drift_rejected(self):
        case=proof.generate_case(9,0)
        def bad(public):
            rid=public["material_requirements"][0]["id"]
            return {"action":"SEARCH","target_requirement_id":rid,"query":"unrelated wandering query"}
        out=proof.run_episode(case,bad)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"QUERY_DRIFT")

if __name__=="__main__":
    unittest.main(verbosity=2)
