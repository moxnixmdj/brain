from __future__ import annotations

import copy
import unittest

from canonical.runtime import auto_one_shot_default_v1 as auto_default


class AutoOneShotDefaultV1Tests(unittest.TestCase):
    def test_safe_r2_internal_open_state_is_eligible(self):
        out = {
            "pass": False,
            "status": "OPEN__DECISION_CONTEXT_REQUIRED",
            "r2_control_policy_total": True,
            "r2_next_meta_action": {
                "kind": "RESOLVE_EXACT_OPEN_EDGE",
                "routing_total": True,
            },
            "execution_attempted": False,
        }
        decision = auto_default.classify(
            auto_routed=True,
            mode="ADEQUATE_DECISION",
            out=out,
            options={},
        )
        self.assertTrue(decision["eligible"], decision)
        self.assertEqual(decision["reason"], "SAFE_INTERNAL_R2_OPEN_STATE")

    def test_fail_closed_user_external_and_nonretryable_effect_are_ineligible(self):
        cases = [
            {
                "pass": False,
                "status": "FAIL_CLOSED",
                "r2_control_policy_total": True,
                "r2_next_meta_action": {"kind": "ABSTAIN_FAIL_CLOSED", "routing_total": True},
            },
            {
                "pass": False,
                "status": "OPEN__USER_DISAMBIGUATION_REQUIRED",
                "ask_user_required": True,
                "r2_control_policy_total": True,
                "r2_next_meta_action": {"kind": "ACQUIRE_MINIMUM_DECISION_INFORMATION", "routing_total": True},
            },
            {
                "pass": False,
                "status": "PASS__PROVEN_INFORMATION_THEORETICALLY_EXTERNAL",
                "externality_proved": True,
                "r2_control_policy_total": True,
                "r2_next_meta_action": {"kind": "ACQUIRE_MINIMUM_DECISION_INFORMATION", "routing_total": True},
            },
            {
                "pass": False,
                "status": "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY",
                "execution_attempted": True,
                "retry_by_other_route_authorized": False,
                "r2_control_policy_total": True,
                "r2_next_meta_action": {"kind": "RESOLVE_EXACT_OPEN_EDGE", "routing_total": True},
            },
        ]
        for out in cases:
            with self.subTest(status=out["status"]):
                decision = auto_default.classify(
                    auto_routed=True,
                    mode="ADEQUATE_DECISION",
                    out=out,
                    options={},
                )
                self.assertFalse(decision["eligible"], decision)

    def test_non_auto_non_r2_learning_disabled_and_recursion_are_ineligible(self):
        base = {
            "pass": False,
            "status": "OPEN__DECISION_CONTEXT_REQUIRED",
            "r2_control_policy_total": True,
            "r2_next_meta_action": {"kind": "RESOLVE_EXACT_OPEN_EDGE", "routing_total": True},
        }
        cases = [
            dict(auto_routed=False, mode="ADEQUATE_DECISION", options={}),
            dict(auto_routed=True, mode="COMPILED_TASK", options={}),
            dict(auto_routed=True, mode="ADEQUATE_DECISION", options={"learn": False}),
            dict(auto_routed=True, mode="ADEQUATE_DECISION", options={"__auto_one_shot_attempted": True}),
        ]
        for case in cases:
            with self.subTest(case=case):
                decision = auto_default.classify(out=base, **case)
                self.assertFalse(decision["eligible"], decision)

    def test_replay_request_is_exact_except_internal_guards(self):
        request = {
            "payload": {"task_id": "T", "goal": "G", "nested": {"x": 1}},
            "options": {"state_path": "state.json", "learn": True, "custom": {"a": 2}},
        }
        original = copy.deepcopy(request)
        replay = auto_default.prepare_replay_request(request)
        self.assertEqual(request, original)
        self.assertEqual(replay["payload"], original["payload"])
        self.assertEqual(replay["options"]["state_path"], "state.json")
        self.assertEqual(replay["options"]["custom"], {"a": 2})
        self.assertFalse(replay["options"]["learn"])
        self.assertTrue(replay["options"]["__auto_one_shot_attempted"])
        self.assertTrue(replay["options"]["__suppress_compounding_tick"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
