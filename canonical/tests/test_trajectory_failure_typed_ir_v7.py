from __future__ import annotations
import copy
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof
from canonical.runtime.p1_v6_derived_only_counterexample_v1 import public_counterexample


def check(kind, aid, passed, semantics="DIRECT_CONTRACT"):
    return {
        "kind":kind,
        "id":f"{aid}:{kind}",
        "pass":passed,
        "evidence":[f"receipt:{aid}",f"check:{aid}:{kind}"],
        "failure_semantics":semantics,
    }


def row(i, *, reads, writes, deps, failed=None, semantics="DIRECT_CONTRACT"):
    aid=f"A{i}"
    checks=[check("INVARIANT",aid,True)]
    if failed is not None:
        checks.append(check(failed,aid,False,semantics))
    return {
        "step":i,
        "action_id":aid,
        "domain":"TOOL_API",
        "reads":reads,
        "writes":writes,
        "depends_on":deps,
        "dependency_composition":"SEQUENTIAL",
        "checks":checks,
    }


def serial_direct_cofault_case():
    p="tool_api:"
    return {
        "schema":"PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_SERIAL_COFAULT_COUNTEREXAMPLE_V1",
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "task":{
            "domain":"TOOL_API",
            "trajectory":[
                row(0,reads=[],writes=[p+"seed"],deps=[]),
                row(1,reads=[p+"seed"],writes=[p+"scope_state"],deps=["A0"],failed="SCOPE"),
                row(2,reads=[p+"scope_state"],writes=[p+"tool_state"],deps=["A1"],failed="TOOL_CONTRACT"),
                row(3,reads=[p+"tool_state"],writes=[p+"symptom"],deps=["A2"],failed="INVARIANT",semantics="DERIVED_UPSTREAM"),
                row(4,reads=[p+"symptom"],writes=[p+"terminal"],deps=["A3"]),
            ],
            "terminal_failed_resources":[p+"terminal"],
            "goal":"LOCALIZE_CAUSAL_FAILURES_AND_NOMINATE_REPAIR_SET_THAT_ACTUALLY_RESCUES_TERMINAL_OUTCOME",
        },
    }


class Tests(unittest.TestCase):
    def test_inherits_v6_192_case_suite(self):
        failures=[]
        for case in proof.suite_cases():
            public=proof.public_task(case)
            out=candidate.solve(public)
            verdict=proof.score_case(case,out)
            if verdict.get("pass") is not True:
                failures.append((case["seed"],verdict,out))
        self.assertEqual(failures,[])

    def test_derived_only_failure_is_not_promoted_to_root(self):
        public=public_counterexample()
        out=candidate.solve(copy.deepcopy(public))
        self.assertEqual(out["status"],"ESCALATE",out)
        self.assertEqual(
            out["reason"],
            "ONLY_DERIVED_UPSTREAM_FAILURES_VISIBLE__DIRECT_CAUSAL_ROOT_NOT_ESTABLISHED",
        )
        self.assertFalse(proof.execute_intervention(copy.deepcopy(public),out)["terminal_rescued"])

    def test_serial_direct_cofault_keeps_both_direct_repairs(self):
        public=serial_direct_cofault_case()
        out=candidate.solve(copy.deepcopy(public))
        self.assertEqual(out["status"],"INTERACTION",out)
        self.assertEqual(out["cause_action_ids"],["A1","A2"],out)
        self.assertEqual(
            out["mechanism_by_action"],
            {"A1":["SCOPE"],"A2":["TOOL_CONTRACT"]},
        )
        self.assertEqual(
            out["repair_targets"],
            ["restore:A1:SCOPE","restore:A2:TOOL_CONTRACT"],
        )
        iv=proof.execute_intervention(copy.deepcopy(public),out)
        self.assertTrue(iv["terminal_rescued"],iv)

    def test_serial_partial_repair_still_fails(self):
        public=serial_direct_cofault_case()
        out=candidate.solve(copy.deepcopy(public))
        partial=copy.deepcopy(out)
        partial["repair_targets"]=partial["repair_targets"][:1]
        iv=proof.execute_intervention(copy.deepcopy(public),partial)
        self.assertFalse(iv["terminal_rescued"],iv)
        self.assertIn("A2:TOOL_CONTRACT",iv["active_direct_failures"])

    def test_failure_semantics_is_load_bearing(self):
        public=serial_direct_cofault_case()
        out_direct=candidate.solve(copy.deepcopy(public))
        mutated=copy.deepcopy(public)
        for row_ in mutated["task"]["trajectory"]:
            for item in row_["checks"]:
                if item["pass"] is False:
                    item["failure_semantics"]="DERIVED_UPSTREAM"
        out_derived=candidate.solve(mutated)
        self.assertNotEqual(out_direct,out_derived)
        self.assertEqual(out_derived["status"],"ESCALATE")

    def test_invalid_failure_semantics_fails_closed(self):
        case=proof.generate_case(63001,pattern="SINGLE",domain="CODE",kind="SCOPE")
        public=proof.public_task(case)
        for row_ in public["task"]["trajectory"]:
            for item in row_["checks"]:
                if item["pass"] is False:
                    item["failure_semantics"]="MAGIC"
                    out=candidate.solve(public)
                    self.assertEqual(out["status"],"FAIL_CLOSED")
                    return
        self.fail("expected a failed check")


if __name__=="__main__":
    unittest.main(verbosity=2)
