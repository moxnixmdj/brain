from __future__ import annotations
import copy, unittest
from canonical.runtime import trajectory_failure_typed_ir_candidate_v6 as v6_candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as v6_proof
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v7 as proof

class Tests(unittest.TestCase):
    def test_all_192_v6_cases_preserved(self):
        failures=[]
        for case in proof.suite_cases():
            out=candidate.solve(proof.public_task(case))
            verdict=proof.score_case(case,out)
            if verdict.get("pass") is not True:
                failures.append((case["seed"],verdict,out))
        self.assertEqual(failures,[])

    def test_48_derived_only_cases_abstain_without_repair(self):
        count=0
        for domain in proof.DOMAINS:
            for kind in proof.KINDS:
                public=proof.derived_only_case(domain,kind)
                out=candidate.solve(public)
                verdict=proof.score_derived_only(out)
                self.assertTrue(verdict["pass"],(domain,kind,out,verdict))
                self.assertFalse(proof.execute_intervention(public,out)["terminal_rescued"])
                count+=1
        self.assertEqual(count,48)

    def test_48_direct_plus_derived_cases_find_root_and_rescue(self):
        count=0
        for domain in proof.DOMAINS:
            for kind in proof.KINDS:
                public=proof.direct_plus_derived_case(domain,kind)
                out=candidate.solve(public)
                verdict=proof.score_direct_plus_derived(public,out,kind)
                self.assertTrue(verdict["pass"],(domain,kind,out,verdict))
                count+=1
        self.assertEqual(count,48)

    def test_reproduce_v6_derived_only_counterexample_and_kill_it(self):
        public=proof.derived_only_case("CODE","SCOPE")
        old=v6_candidate.solve(public)
        self.assertEqual(old["status"],"IDENTIFIED")
        self.assertEqual(old["cause_action_id"],"A1")
        self.assertEqual(old["repair_targets"],["restore:A1:SCOPE"])
        self.assertFalse(v6_proof.execute_intervention(public,old)["terminal_rescued"])
        new=candidate.solve(public)
        self.assertEqual(new["status"],"AMBIGUOUS")
        self.assertIsNone(new["cause_action_id"])
        self.assertEqual(new["cause_action_ids"],[])
        self.assertNotIn("repair_targets",new)

    def test_failure_semantics_is_load_bearing(self):
        public=proof.derived_only_case("RESEARCH","SCOPE")
        derived=candidate.solve(public)
        self.assertEqual(derived["status"],"AMBIGUOUS")
        attacked=copy.deepcopy(public)
        failed=next(
            check for row in attacked["task"]["trajectory"] for check in row["checks"]
            if check["pass"] is False
        )
        failed["failure_semantics"]="DIRECT_CONTRACT"
        direct=candidate.solve(attacked)
        self.assertEqual(direct["status"],"IDENTIFIED")
        self.assertEqual(direct["cause_action_id"],"A1")

    def test_missing_failure_semantics_fails_closed(self):
        public=proof.derived_only_case("TOOL_API","PROVENANCE")
        failed=next(
            check for row in public["task"]["trajectory"] for check in row["checks"]
            if check["pass"] is False
        )
        failed.pop("failure_semantics")
        out=candidate.solve(public)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"STEP_SCHEMA_INVALID")

    def test_partial_interaction_and_fake_repair_regressions_still_killed(self):
        case=v6_proof.generate_case(88001,pattern="INTERACTION",domain="FILESYSTEM",kind="SCOPE")
        public=v6_proof.public_task(case)
        out=candidate.solve(public)
        self.assertTrue(v6_proof.score_case(case,out)["pass"])
        partial=copy.deepcopy(out); partial["repair_targets"]=partial["repair_targets"][:1]
        self.assertFalse(v6_proof.execute_intervention(public,partial)["terminal_rescued"])

if __name__=="__main__":
    unittest.main(verbosity=2)
