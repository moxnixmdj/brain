from __future__ import annotations
import inspect,json,unittest
from canonical.runtime import browser_state_information_safe_candidate as candidate
from canonical.runtime import browser_state_information_safe_proof as proof

class BrowserStateInformationSafeTests(unittest.TestCase):
    def test_hidden_terminal_state_not_public(self):
        case=proof.generate_case(11,0)
        public=proof.public_state(case,case["_initial_state"],[])
        self.assertNotIn("_oracle",public)
        self.assertNotIn("_initial_state",public)
        self.assertNotIn("expected_terminal_status",json.dumps(public))

    def test_candidate_has_no_evaluator_dependency(self):
        src=inspect.getsource(candidate)
        self.assertNotIn("browser_state_information_safe_proof",src)
        self.assertNotIn("_oracle",src)

    def test_all_interaction_classes(self):
        out=proof.run_batch(2026,100,candidate.next_action)
        self.assertTrue(out["all_pass"],out)
        self.assertEqual(set(out["by_class"]),set(proof.CLASSES))

    def test_stale_case_rebinds_after_rerender(self):
        case=proof.generate_case(7,3)
        out=proof.run_episode(case,candidate.next_action)
        self.assertTrue(out["pass"],out)
        clicks=[x["element_id"] for x in out["history"]]
        self.assertGreaterEqual(len(clicks),3)
        self.assertNotEqual(clicks[0],clicks[1])

    def test_ambiguity_escalates_without_action(self):
        case=proof.generate_case(7,4)
        out=proof.run_episode(case,candidate.next_action)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["reason"],"PASS_AMBIGUITY_ESCALATED")
        self.assertEqual(out["history"],[])

if __name__=="__main__": unittest.main(verbosity=2)
