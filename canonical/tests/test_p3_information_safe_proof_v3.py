from __future__ import annotations
import inspect,unittest
from canonical.runtime import p3_information_safe_proof_suite_v3 as suite
from canonical.runtime import p3_information_safe_candidate_v3 as candidate

class Tests(unittest.TestCase):
    def test_public_boundary_hides_support_and_relevance(self):
        case=suite.generate_case(17,5)
        public=suite.public_task(case); raw=repr(public)
        self.assertNotIn("_oracle",public)
        self.assertNotIn("hidden_support_graph",raw)
        self.assertNotIn("hidden_decision_relevance",raw)
        self.assertNotIn("'stance'",raw)
        self.assertNotIn("supports",raw)
        self.assertNotIn("refutes",raw)

    def test_candidate_has_no_evaluator_or_hidden_oracle_dependency(self):
        src=inspect.getsource(candidate)
        self.assertNotIn("p3_information_safe_proof_suite_v3",src)
        self.assertNotIn("_oracle",src)
        self.assertNotIn("hidden_support",src)
        self.assertNotIn("hidden_decision",src)

    def test_candidate_executes_and_matches_bounded_oracle_grid(self):
        for difficulty in range(1,6):
            for seed in (17,101,991,7919):
                case=suite.generate_case(seed,difficulty)
                got=candidate.solve(suite.public_task(case))
                verdict=suite.score_case(case,got)
                self.assertTrue(verdict["pass"],(seed,difficulty,verdict,got,case["_oracle"]))

    def test_hidden_conflict_oracle_rejects_uncertainty_deletion(self):
        for seed in range(100):
            case=suite.generate_case(seed,5)
            if case["_oracle"]["uncertainty_claims"]:
                bad={
                  "selected_claims":list(case["_oracle"]["selected_claims"]),
                  "uncertainty_claims":[],
                }
                self.assertFalse(suite.score_case(case,bad)["pass"])
                return
        self.fail("NO_CONFLICT_CASE_FOUND")

if __name__=="__main__":
    unittest.main(verbosity=2)
