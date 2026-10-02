from __future__ import annotations
import unittest
from canonical.runtime import trajectory_failure_typed_ir_candidate_v6 as old
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v7 as proof

class Tests(unittest.TestCase):
    def test_standard_v6_192_cases_are_preserved(self):
        failures=[]
        for case in proof.suite_cases()[:192]:
            out=candidate.solve(proof.public_task(case))
            v=proof.score_case(case,out)
            if v.get("pass") is not True:
                failures.append((case["seed"],v,out))
        self.assertEqual(failures,[])

    def test_48_nested_competing_direct_cases_abstain(self):
        cases=proof.nested_cases()
        self.assertEqual(len(cases),48)
        for case in cases:
            out=candidate.solve(proof.public_task(case))
            self.assertEqual(out["status"],"AMBIGUOUS",(case,out))
            self.assertEqual(out["cause_action_ids"],["A1","A2"])
            self.assertIsNone(out["cause_action_id"])
            self.assertTrue(out["information_request"])
            self.assertTrue(proof.score_case(case,out)["pass"],(case,out))

    def test_old_v6_overclaims_nested_case_and_v7_does_not(self):
        case=proof.generate_nested_case(44001,domain="CODE",kind="AUTHORITY")
        public=proof.public_task(case)
        old_out=old.solve(public)
        new_out=candidate.solve(public)
        self.assertEqual(old_out["status"],"IDENTIFIED",old_out)
        self.assertEqual(old_out["cause_action_id"],"A1",old_out)
        self.assertEqual(new_out["status"],"AMBIGUOUS",new_out)

    def test_nested_hidden_worlds_have_incompatible_minimal_rescuers(self):
        case=proof.generate_nested_case(44002,domain="RESEARCH",kind="PROVENANCE")
        a1=[f"restore:A1:{case['_oracle']['mechanisms']['A1'][0]}"]
        a2=[f"restore:A2:{case['_oracle']['mechanisms']['A2'][0]}"]
        self.assertEqual(proof.nested_world_rescue_vector(case,a1),(True,False))
        self.assertEqual(proof.nested_world_rescue_vector(case,a2),(False,True))

    def test_derived_downstream_symptom_still_allows_unique_root(self):
        case=proof.v6.generate_case(44003,pattern="DELAYED",domain="BROWSER",kind="SCOPE")
        out=candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"],"IDENTIFIED",out)
        self.assertEqual(out["cause_action_id"],"A1",out)
        self.assertTrue(proof.score_case(case,out)["pass"])

    def test_conjunctive_independent_direct_roots_still_form_interaction(self):
        case=proof.v6.generate_case(44004,pattern="INTERACTION",domain="TOOL_API",kind="DEPENDENCY")
        out=candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"],"INTERACTION",out)
        self.assertEqual(out["cause_action_ids"],["A1","A2"])
        self.assertTrue(proof.score_case(case,out)["pass"])

    def test_missing_failure_semantics_is_fail_safe_ambiguous_for_nested_failures(self):
        case=proof.generate_nested_case(44005,domain="FILESYSTEM",kind="SCHEMA")
        public=proof.public_task(case)
        for row in public["task"]["trajectory"]:
            for check in row["checks"]:
                check.pop("failure_semantics",None)
        out=candidate.solve(public)
        self.assertEqual(out["status"],"AMBIGUOUS",out)

    def test_visible_provenance_erasure_remains_fail_closed(self):
        case=proof.v6.generate_case(44006,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
        public=proof.public_task(case)
        for row in public["task"]["trajectory"]:
            for check in row["checks"]:
                if check["pass"] is False:
                    check["evidence"]=[]
        out=candidate.solve(public)
        self.assertEqual(out["status"],"FAIL_CLOSED",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
