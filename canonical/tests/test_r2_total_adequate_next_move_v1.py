from __future__ import annotations
import unittest
from unittest import mock
from canonical.runtime import r2_total_adequate_next_move_v1 as mod

class Tests(unittest.TestCase):
    def test_verified_or_fail_closed(self):
        ok=mod.classify_result({"pass":True,"status":"PASS","actual_goal_satisfaction_verified":True,"realization":{"x":1}})
        self.assertEqual(ok["next_move_kind"],mod.RETURN_VERIFIED_ACTION)
        bad=mod.classify_result({"pass":True,"status":"PASS","actual_goal_satisfaction_verified":False})
        self.assertEqual(bad["next_move_kind"],mod.FAIL_CLOSED)

    def test_information_and_fresh_reality(self):
        req={"predicate_id":"P"}
        info=mod.classify_result({"pass":False,"status":"OPEN","next_information_request":req})
        self.assertEqual(info["next_move_kind"],mod.ACQUIRE_MINIMUM_INFORMATION)
        fresh=mod.classify_result({"pass":False,"status":"OPEN","next_information_request":req,
          "information_trace":[{"provider_returned_payload":False}]},information_provider_supplied=True)
        self.assertEqual(fresh["next_move_kind"],mod.ACQUIRE_FRESH_REALITY)

    def test_policy_observation_and_residual_edges(self):
        self.assertEqual(mod.classify_result({"pass":False,"next_policy_request":{"x":1}})["next_move_kind"],mod.SYNTHESIZE_POLICY_ADEQUACY)
        self.assertEqual(mod.classify_result({"pass":False,"next_observation_request":{"x":1}})["next_move_kind"],mod.ACQUIRE_POLICY_COVER_OBSERVATION)
        self.assertEqual(mod.classify_result({"pass":False,"next_required_edge":"INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION"})["next_move_kind"],mod.ACQUIRE_GOAL_ACCEPTANCE)
        self.assertEqual(mod.classify_result({"pass":False,"next_required_edge":"AUTHENTICATED_SELECTED_POLICY_TO_EXECUTION_BINDING"})["next_move_kind"],mod.REALIZE_POLICY)
        self.assertEqual(mod.classify_result({"pass":False,"next_required_edge":"AUTHENTICATED_FULL_OR_SOUND_PARTIAL_GOAL_TO_DECISION_CONTEXT"})["next_move_kind"],mod.ACQUIRE_SEMANTIC_BINDING)
        self.assertEqual(mod.classify_result({"pass":False,"next_required_edge":"NEW_VERIFIABLE_PRIMITIVE"})["next_move_kind"],mod.EXPAND_VERIFIED_PRIMITIVE)

    def test_run_delegates_to_existing_fixed_point(self):
        result={"pass":False,"status":"OPEN","next_information_request":{"predicate_id":"P"}}
        with mock.patch.object(mod,"run_fixed_point",return_value=result) as fixed:
            out=mod.run({"task_id":"t","goal":"g"})
        fixed.assert_called_once()
        self.assertEqual(out["next_move_kind"],mod.ACQUIRE_MINIMUM_INFORMATION)
        self.assertEqual(out["decision_result"],result)

if __name__=="__main__":
    unittest.main(verbosity=2)
