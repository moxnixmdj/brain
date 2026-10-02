from __future__ import annotations
import copy
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v7 as proof
from canonical.runtime.p1_v6_derived_only_counterexample_v1 import public_counterexample


class Tests(unittest.TestCase):
    def test_v6_192_case_envelope_is_preserved(self):
        cases=proof.baseline_cases()
        self.assertEqual(len(cases),192)
        failures=[]
        for case in cases:
            out=candidate.solve(proof.public_task(case))
            verdict=proof.score_case(case,out)
            if verdict.get("pass") is not True:
                failures.append((case["seed"],verdict,out))
        self.assertEqual(failures,[])

    def test_48_domain_by_mechanism_derived_only_cases_abstain(self):
        cases=proof.derived_only_cases()
        self.assertEqual(len(cases),48)
        self.assertEqual({c["task"]["domain"] for c in cases},set(proof.DOMAINS))
        self.assertEqual({c["_oracle"]["mechanism"] for c in cases},set(proof.KINDS))
        for case in cases:
            out=candidate.solve(proof.public_task(case))
            self.assertEqual(out["status"],"ESCALATE",out)
            self.assertEqual(out["reason"],"ONLY_DERIVED_UPSTREAM_FAILURES_VISIBLE",out)
            self.assertNotIn("cause_action_id",out)
            self.assertNotIn("repair_targets",out)
            verdict=proof.score_case(case,out)
            self.assertTrue(verdict["pass"],(case,verdict,out))
            self.assertFalse(verdict["intervention_rescue_verified"])

    def test_exact_v6_derived_only_counterexample_is_killed(self):
        public=public_counterexample()
        out=candidate.solve(public)
        self.assertEqual(out["status"],"ESCALATE",out)
        self.assertEqual(out["reason"],"ONLY_DERIVED_UPSTREAM_FAILURES_VISIBLE",out)
        self.assertEqual(out["derived_failure_action_ids"],["A1"])
        self.assertNotIn("repair_targets",out)
        iv=proof.execute_intervention(public,out)
        self.assertFalse(iv["terminal_rescued"],iv)

    def test_marking_the_only_direct_root_as_derived_forces_abstention(self):
        case=proof.generate_case(40001,pattern="DELAYED",domain="CODE",kind="SCOPE")
        public=proof.public_task(case)
        for row in public["task"]["trajectory"]:
            if row["action_id"]=="A1":
                failed=[x for x in row["checks"] if x["pass"] is False]
                self.assertEqual(len(failed),1)
                failed[0]["failure_semantics"]="DERIVED_UPSTREAM"
        out=candidate.solve(public)
        self.assertEqual(out["status"],"ESCALATE",out)
        self.assertNotIn("repair_targets",out)

    def test_downstream_derived_failure_never_enters_root_repair(self):
        case=proof.generate_case(40002,pattern="DELAYED",domain="RESEARCH",kind="PROVENANCE")
        out=candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"],"IDENTIFIED")
        self.assertEqual(out["cause_action_id"],"A1")
        self.assertEqual(out["repair_targets"],["restore:A1:PROVENANCE"])
        self.assertNotIn("restore:A4:INVARIANT",out["repair_targets"])
        self.assertTrue(proof.score_case(case,out)["pass"])

    def test_interaction_roots_remain_direct_and_joint(self):
        case=proof.generate_case(40003,pattern="INTERACTION",domain="TOOL_API",kind="SCOPE")
        out=candidate.solve(proof.public_task(case))
        self.assertEqual(out["status"],"INTERACTION")
        self.assertEqual(out["cause_action_ids"],["A1","A2"])
        self.assertEqual(len(out["repair_targets"]),2)
        self.assertTrue(proof.score_case(case,out)["pass"])

    def test_unknown_failure_semantics_fails_closed(self):
        case=proof.generate_case(40004,pattern="SINGLE",domain="BROWSER",kind="AUTHORITY")
        public=proof.public_task(case)
        next(
            x for row in public["task"]["trajectory"]
            for x in row["checks"] if x["pass"] is False
        )["failure_semantics"]="MAGIC"
        out=candidate.solve(public)
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_failure_semantics_cannot_be_erased_into_direct_root(self):
        case=proof.derived_only_case(40005,domain="FILESYSTEM",kind="DEPENDENCY")
        public=proof.public_task(case)
        derived=next(
            x for row in public["task"]["trajectory"]
            for x in row["checks"] if x["pass"] is False
        )
        self.assertEqual(derived["failure_semantics"],"DERIVED_UPSTREAM")
        safe=candidate.solve(copy.deepcopy(public))
        self.assertEqual(safe["status"],"ESCALATE")
        attacked=copy.deepcopy(public)
        next(
            x for row in attacked["task"]["trajectory"]
            for x in row["checks"] if x["pass"] is False
        ).pop("failure_semantics")
        erased=candidate.solve(attacked)
        self.assertEqual(erased["status"],"FAIL_CLOSED")
        self.assertNotEqual(safe["status"],erased["status"])


if __name__=="__main__":
    unittest.main(verbosity=2)
