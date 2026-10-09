from __future__ import annotations

import unittest

from canonical.runtime import r2_assurance_shadow_v1 as shadow


class R2AssuranceShadowV1Tests(unittest.TestCase):
    @staticmethod
    def pass_result():
        return {
            "schema":"PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_FIXED_POINT_V2",
            "status":"PASS__R2_ADAPTIVE_FIXED_POINT_CLOSED",
            "pass":True,
            "semantic_acceptance_complete":True,
            "actual_goal_satisfaction_verified":True,
            "terminal_authority":False,
            "terminal_credit_delta":0,
            "incremental_spend_usd":0,
        }

    @staticmethod
    def open_result():
        return {
            "schema":"PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_FIXED_POINT_V2",
            "status":"OPEN__R2_EDGE_RESOLVER_UNAVAILABLE",
            "pass":False,
            "next_required_edge":"AUTHENTICATED_GOAL_TO_DECISION_CONTEXT",
            "semantic_acceptance_complete":False,
            "actual_goal_satisfaction_verified":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
            "incremental_spend_usd":0,
        }

    def test_pass_remains_r2_pass_but_v2_stays_adversarially_open(self):
        src=self.pass_result()
        out=shadow.observe_result(src)
        self.assertTrue(out["r2_pass"],out)
        self.assertEqual(out["status"],"SHADOW_OBSERVED_R2_PASS")
        self.assertEqual(
            out["assurance_status"],
            "OPEN__ADVERSARIAL_CLOSURE_REQUIRED",
        )
        self.assertFalse(out["shadow_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertNotIn("pass",out)

    def test_open_r2_becomes_ordinary_v2_residual(self):
        out=shadow.observe_result(self.open_result())
        self.assertFalse(out["r2_pass"])
        self.assertEqual(out["status"],"SHADOW_OBSERVED_R2_OPEN_OR_FAIL")
        self.assertEqual(
            out["assurance_status"],
            "OPEN__ASSURANCE_RESIDUAL",
        )
        self.assertFalse(
            out["assurance_result"]["new_primitive_required"]
        )

    def test_shadow_never_mutates_source_result(self):
        src=self.pass_result()
        before=dict(src)
        out=shadow.observe_result(src)
        self.assertEqual(src,before)
        self.assertEqual(out["r2_result"],before)
        out["r2_result"]["status"]="MUTATED_COPY"
        self.assertEqual(src,before)

    def test_bare_pass_without_goal_acceptance_cannot_close_execution(self):
        src={
            "schema":"X",
            "status":"PASSISH",
            "pass":True,
            "semantic_acceptance_complete":False,
            "actual_goal_satisfaction_verified":False,
        }
        out=shadow.observe_result(src)
        self.assertTrue(out["r2_pass"])
        self.assertFalse(
            out["assurance_result"]["closure_gates"]["execution_closure"]
        )
        self.assertFalse(out["shadow_authority"])

    def test_injected_runner_executes_once_and_preserves_request(self):
        calls=[]
        request={"task_id":"x","goal":"Do the right thing."}
        def runner(arg,**kwargs):
            calls.append((dict(arg),dict(kwargs)))
            return self.pass_result()
        out=shadow.run(
            request,
            fixed_point_runner=runner,
            fixed_point_kwargs={"max_fixed_point_steps":3},
        )
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0],request)
        self.assertEqual(calls[0][1],{"max_fixed_point_steps":3})
        self.assertTrue(out["r2_pass"])
        self.assertFalse(out["shadow_authority"])

    def test_runner_failure_fails_closed_without_authority(self):
        def runner(_request,**_kwargs):
            raise RuntimeError("boom")
        out=shadow.run(
            {"task_id":"x","goal":"g"},
            fixed_point_runner=runner,
        )
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("R2_RUNNER_EXCEPTION:RuntimeError:boom",out["reason"])
        self.assertFalse(out["terminal_authority"])


if __name__=="__main__":
    unittest.main()
