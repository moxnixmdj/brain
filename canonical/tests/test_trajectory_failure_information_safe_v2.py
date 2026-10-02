import inspect
import unittest

from canonical.runtime.trajectory_failure_information_safe_candidate_v2 import solve
from canonical.runtime.trajectory_failure_information_safe_proof_v2 import (
    anti_shortcut_mutations,
    generate_case,
    public_task,
    score_case,
)


class TrajectoryFailureInformationSafeV2Tests(unittest.TestCase):
    def test_public_payload_contains_no_oracle_or_repair_answers(self):
        case=generate_case(101,ambiguous=False)
        public=public_task(case)
        self.assertNotIn("_oracle",public)
        self.assertNotIn("repair_candidates",public["task"])
        self.assertIn("repair_language",public["task"])

    def test_candidate_has_no_oracle_or_evaluator_import(self):
        import canonical.runtime.trajectory_failure_information_safe_candidate_v2 as m
        src=inspect.getsource(m)
        self.assertNotIn("trajectory_failure_information_safe_proof",src)
        self.assertNotIn("_oracle",src)
        self.assertNotIn("repair_candidates",src)

    def test_identified_cases_generate_their_own_repair(self):
        for seed in (101,102,103,104,106,107):
            case=generate_case(seed,ambiguous=False)
            out=solve(public_task(case))
            verdict=score_case(case,out)
            self.assertTrue(verdict["pass"],(seed,out,case["_oracle"]))
            self.assertEqual(out["status"],"IDENTIFIED")
            self.assertIn("repair",out)

    def test_ambiguous_cases_preserve_nonidentifiability(self):
        for seed in (105,110,115,120):
            case=generate_case(seed,ambiguous=True)
            out=solve(public_task(case))
            verdict=score_case(case,out)
            self.assertTrue(verdict["pass"],(seed,out,case["_oracle"]))
            self.assertEqual(out["status"],"AMBIGUOUS")
            self.assertIsNone(out["cause_action_id"])
            self.assertGreaterEqual(len(out["repairs"]),2)

    def test_earliest_violation_shortcut_is_not_repair_generation(self):
        case=generate_case(131,ambiguous=False)
        public=public_task(case)
        violated=[x for x in public["task"]["trajectory"] if not x["contract_pass"]]
        earliest=violated[0]
        bad={
            "status":"IDENTIFIED",
            "cause_action_id":earliest["action_id"],
            "repair":{
                "action_id":earliest["action_id"],
                "replacement_delta":earliest["contract_delta"],
            },
            "evidence_action_ids":[earliest["action_id"]],
        }
        self.assertFalse(score_case(case,bad)["pass"])

    def test_anti_shortcut_mutations_are_declared(self):
        ids={x["id"] for x in anti_shortcut_mutations(generate_case(137))}
        self.assertEqual(ids,{"MOVE_FIRST_VIOLATION","PERMUTE_ACTION_IDS","AMBIGUITY_PAIR"})


if __name__=="__main__":
    unittest.main(verbosity=2)
