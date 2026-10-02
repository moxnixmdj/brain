import inspect
import unittest

from canonical.runtime.trajectory_failure_information_safe_candidate import solve
from canonical.runtime.trajectory_failure_information_safe_proof import (
    generate_case, public_task, score_case, verify_candidate_rescue,
)


class TrajectoryFailureInformationSafeTests(unittest.TestCase):
    def test_candidate_source_has_no_oracle_import(self):
        import canonical.runtime.trajectory_failure_information_safe_candidate as m
        src=inspect.getsource(m)
        self.assertNotIn("trajectory_failure_information_safe_proof",src)
        self.assertNotIn("_oracle",src)

    def test_identifiable_dev_population(self):
        for seed in (11,12,13,14,16,17,18,19):
            case=generate_case(seed,ambiguous=False)
            public=public_task(case)
            self.assertNotIn("_oracle",public)
            out=solve(public)
            self.assertTrue(score_case(case,out)["pass"],(seed,out,case["_oracle"]))
            self.assertTrue(verify_candidate_rescue(case,out))
            violated=[x["action_id"] for x in public["task"]["trajectory"] if not x["contract_pass"]]
            self.assertGreaterEqual(len(violated),3)
            self.assertNotEqual(out["cause_action_id"],violated[0])

    def test_ambiguous_dev_population(self):
        for seed in (20,25,30,35):
            case=generate_case(seed,ambiguous=True)
            out=solve(public_task(case))
            self.assertEqual(out["status"],"AMBIGUOUS")
            self.assertTrue(score_case(case,out)["pass"],(seed,out,case["_oracle"]))
            self.assertTrue(verify_candidate_rescue(case,out))
            self.assertGreaterEqual(len(out["repair_ids"]),2)

    def test_shortcut_earliest_violation_fails(self):
        case=generate_case(41,ambiguous=False)
        public=public_task(case)
        earliest=next(x["action_id"] for x in public["task"]["trajectory"] if not x["contract_pass"])
        repair=next(x for x in public["task"]["repair_candidates"] if x["action_id"]==earliest)
        bad={
            "status":"IDENTIFIED",
            "cause_action_id":earliest,
            "repair_id":repair["repair_id"],
            "evidence_action_ids":[earliest],
        }
        self.assertFalse(score_case(case,bad)["pass"])

    def test_forced_unique_cause_on_ambiguous_case_fails(self):
        case=generate_case(45,ambiguous=True)
        rid=case["_oracle"]["rescue_repair_ids"][0]
        repair=next(x for x in case["task"]["repair_candidates"] if x["repair_id"]==rid)
        bad={
            "status":"IDENTIFIED",
            "cause_action_id":repair["action_id"],
            "repair_id":rid,
            "evidence_action_ids":[repair["action_id"]],
        }
        self.assertFalse(score_case(case,bad)["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)
