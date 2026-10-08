from __future__ import annotations

import unittest

from canonical.runtime import raw_goal_exact_literal_acceptance_v1 as a


class ExactLiteralAcceptanceTests(unittest.TestCase):
    def test_preflight_is_strict_and_side_effect_free(self):
        out=a.preflight('Reply with exactly "HELLO WORLD".')
        self.assertTrue(out["matched"],out)
        self.assertEqual(out["literal"],"HELLO WORLD")
        bad=a.preflight('Reply with exactly "HELLO WORLD". Also explain.')
        self.assertFalse(bad["matched"])

    def test_accepts_only_exact_single_finish_trace(self):
        goal='Respond with exactly READY_42.'
        pf=a.preflight(goal)
        contract=a.compile_contract(
            goal,
            source_id="user",
            routing_target_effects=[a.ROUTING_EFFECT],
        )
        raw={
            "pass":True,
            "compiler_mode":"DETERMINISTIC_EXACT_LITERAL_RESPONSE",
            "raw_goal_sha256":pf["goal_sha256"],
            "raw_task_contract_sha256":contract["task_contract_sha256"],
            "raw_source_coverage_complete":True,
            "raw_acceptance_obligation_count":len(contract["acceptance_contract"]["obligations"]),
            "controller_action_count":1,
            "model_dependency_count":0,
            "cognition_dependency_class":"MODEL_INDEPENDENT",
            "controller_execution":{
                "returncode":0,
                "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
                "final_summary":"READY_42",
                "trace":[{
                    "cycle":0,
                    "plan":{"type":"finish","args":{"summary":"READY_42"}},
                    "result":{"summary":"READY_42"},
                }],
            },
        }
        out=a.verify(goal=goal,raw_result=raw)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertEqual(
            len(out["accepted_obligation_ids"]),
            out["required_obligation_count"],
        )

    def test_near_miss_summary_is_not_accepted(self):
        goal='Respond with exactly READY_42.'
        pf=a.preflight(goal)
        contract=a.compile_contract(
            goal,
            source_id="user",
            routing_target_effects=[a.ROUTING_EFFECT],
        )
        raw={
            "pass":True,
            "compiler_mode":"DETERMINISTIC_EXACT_LITERAL_RESPONSE",
            "raw_goal_sha256":pf["goal_sha256"],
            "raw_task_contract_sha256":contract["task_contract_sha256"],
            "raw_source_coverage_complete":True,
            "raw_acceptance_obligation_count":len(contract["acceptance_contract"]["obligations"]),
            "controller_action_count":1,
            "model_dependency_count":0,
            "cognition_dependency_class":"MODEL_INDEPENDENT",
            "controller_execution":{
                "returncode":0,
                "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
                "final_summary":"READY_42!",
                "trace":[{
                    "cycle":0,
                    "plan":{"type":"finish","args":{"summary":"READY_42"}},
                    "result":{"summary":"READY_42!"},
                }],
            },
        }
        out=a.verify(goal=goal,raw_result=raw)
        self.assertFalse(out["pass"])
        self.assertFalse(out["semantic_acceptance_complete"])


if __name__=="__main__":
    unittest.main(verbosity=2)
