from __future__ import annotations
import inspect, unittest

from canonical.runtime import p2_p3_information_safe_proof_suites_v2 as suite
from canonical.runtime import p2_p3_information_safe_candidate_v2 as candidate


class Tests(unittest.TestCase):
    def test_public_tasks_hide_load_bearing_gold(self):
        for contract in suite.CONTRACTS:
            case=suite.generate_case(contract,17,5)
            public=suite.public_task(case)
            raw=repr(public)
            self.assertNotIn("_oracle",public)
            self.assertNotIn("hidden_quality_factors",raw)
            self.assertNotIn("hidden_support_graph",raw)
            self.assertNotIn("hidden_decision_relevance",raw)
            # Old P2/P3 leaks are forbidden.
            if contract==suite.P2:
                self.assertNotIn("scores",raw)
            if contract==suite.P3:
                self.assertNotIn("'role'",raw)
                self.assertNotIn("'support'",raw)

    def test_candidate_cannot_import_evaluator_or_oracle(self):
        src=inspect.getsource(candidate)
        self.assertNotIn("p2_p3_information_safe_proof_suites_v2",src)
        self.assertNotIn("_oracle",src)
        self.assertNotIn("hidden_quality",src)
        self.assertNotIn("hidden_support",src)

    def test_preflight_candidate_executes_across_seed_grid(self):
        # Preflight only: this checks interface/harness executability, not terminal credit.
        for contract in suite.CONTRACTS:
            for difficulty in range(1,6):
                for seed in (17,101,991,7919):
                    case=suite.generate_case(contract,seed,difficulty)
                    got=candidate.solve(suite.public_task(case))
                    self.assertIsInstance(got,dict)

    def test_p2_hidden_quality_oracle_can_kill_bad_plan(self):
        case=suite.generate_case(suite.P2,123,5)
        bad={"selected_edits":[]}
        self.assertFalse(suite.score_case(case,bad)["pass"])

    def test_p3_conflict_uncertainty_is_oracle_checked(self):
        seed=0
        while True:
            case=suite.generate_case(suite.P3,seed,5)
            if case["_oracle"]["uncertainty_claims"]:
                break
            seed+=1
        gold={
            "selected_claims":list(case["_oracle"]["selected_claims"]),
            "uncertainty_claims":[],
        }
        self.assertFalse(suite.score_case(case,gold)["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)
