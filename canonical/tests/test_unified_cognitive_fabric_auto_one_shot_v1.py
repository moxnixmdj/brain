from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import unified_cognitive_fabric_v1 as fabric


PAYLOAD = {"task_id": "auto-closure", "goal": "Do the unresolved thing."}


def unresolved():
    return {
        "pass": False,
        "status": "OPEN__DECISION_CONTEXT_REQUIRED",
        "r2_fixed_point_status": "OPEN__R2_EDGE_RESOLVER_UNAVAILABLE",
        "terminal_authority": False,
    }


def solved():
    return {
        "pass": True,
        "status": "PASS__GOAL_BOUND_ADEQUATE_DECISION_REALIZED_AND_ACCEPTANCE_VERIFIED",
        "semantic_acceptance_complete": True,
        "actual_goal_satisfaction_verified": True,
        "terminal_authority": False,
    }


def fixed_point():
    return {
        "pass": True,
        "status": "PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT",
        "fixed_point": True,
        "terminal_authority": False,
    }


class UnifiedFabricAutoOneShotClosureTests(unittest.TestCase):
    def _run(self, request, *, decision_side_effect, closure_return):
        with patch.object(
            fabric,
            "_run_adequate_decision_engine",
            side_effect=decision_side_effect,
        ) as decision, patch.object(
            fabric.one_shot_reality_closure,
            "run",
            return_value=closure_return,
        ) as closure, patch.object(
            fabric.improvement_driver,
            "drain",
            return_value={"pass": True, "status": "NOOP", "terminal_authority": False},
        ):
            out = fabric.run(request)
        return out, decision, closure

    def test_auto_unresolved_fixed_point_closure_replays_exact_decision_path(self):
        out, decision, closure = self._run(
            {"payload": PAYLOAD, "options": {"learn": False}},
            decision_side_effect=[unresolved(), solved()],
            closure_return=fixed_point(),
        )
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "ADEQUATE_DECISION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(decision.call_count, 2)
        self.assertEqual(decision.call_args_list[0].args[0], PAYLOAD)
        self.assertEqual(decision.call_args_list[1].args[0], PAYLOAD)
        self.assertEqual(
            decision.call_args_list[0].args[1],
            decision.call_args_list[1].args[1],
        )
        closure.assert_called_once()
        meta = out["auto_one_shot_closure"]
        self.assertTrue(meta["attempted"])
        self.assertTrue(meta["fixed_point"])
        self.assertTrue(meta["replay_attempted"])
        self.assertTrue(meta["replay_pass"])
        self.assertEqual(
            out["result"]["_auto_one_shot_closure"]["replay_status"],
            solved()["status"],
        )

    def test_proven_externality_does_not_replay_or_turn_task_green(self):
        external = {
            "pass": True,
            "status": "PASS__PROVEN_INFORMATION_THEORETICALLY_EXTERNAL",
            "fixed_point": True,
            "gap_contract": {"gap_class": "PROVEN_INFORMATION_THEORETICALLY_EXTERNAL"},
            "terminal_authority": False,
        }
        out, decision, closure = self._run(
            {"payload": PAYLOAD, "options": {"learn": False}},
            decision_side_effect=[unresolved()],
            closure_return=external,
        )
        self.assertFalse(out["inner_pass"], out)
        self.assertEqual(decision.call_count, 1)
        closure.assert_called_once()
        meta = out["auto_one_shot_closure"]
        self.assertTrue(meta["proven_external"])
        self.assertFalse(meta["replay_attempted"])
        self.assertFalse(meta["replay_pass"])
        self.assertEqual(out["result"]["status"], unresolved()["status"])

    def test_open_one_shot_provider_gap_does_not_replay(self):
        opened = {
            "pass": False,
            "status": "OPEN__CAPABILITY_SYNTHESIS_PROVIDER_REQUIRED",
            "gap_contract": {"gap_class": "CONSTRUCTIVE_CAPABILITY_GAP"},
            "terminal_authority": False,
        }
        out, decision, closure = self._run(
            {"payload": PAYLOAD, "options": {"learn": False}},
            decision_side_effect=[unresolved()],
            closure_return=opened,
        )
        self.assertFalse(out["inner_pass"])
        self.assertEqual(decision.call_count, 1)
        self.assertFalse(out["auto_one_shot_closure"]["replay_attempted"])

    def test_explicit_adequate_decision_never_auto_invokes_one_shot(self):
        out, decision, closure = self._run(
            {
                "mode": "ADEQUATE_DECISION",
                "payload": PAYLOAD,
                "options": {"learn": False},
            },
            decision_side_effect=[unresolved()],
            closure_return=fixed_point(),
        )
        self.assertFalse(out["auto_routed"])
        self.assertFalse(out["inner_pass"])
        self.assertEqual(decision.call_count, 1)
        closure.assert_not_called()
        self.assertIsNone(out["auto_one_shot_closure"])

    def test_user_clarification_requirement_skips_one_shot(self):
        ask = {
            **unresolved(),
            "ask_user_required": True,
            "action": "ASK_USER_MINIMUM_CLARIFICATION",
        }
        out, decision, closure = self._run(
            {"payload": PAYLOAD, "options": {"learn": False}},
            decision_side_effect=[ask],
            closure_return=fixed_point(),
        )
        self.assertFalse(out["inner_pass"])
        self.assertEqual(decision.call_count, 1)
        closure.assert_not_called()
        self.assertIsNone(out["auto_one_shot_closure"])

    def test_auto_one_shot_can_be_explicitly_disabled(self):
        out, decision, closure = self._run(
            {
                "payload": PAYLOAD,
                "options": {"learn": False, "auto_one_shot_closure": False},
            },
            decision_side_effect=[unresolved()],
            closure_return=fixed_point(),
        )
        self.assertFalse(out["inner_pass"])
        self.assertEqual(decision.call_count, 1)
        closure.assert_not_called()
        self.assertIsNone(out["auto_one_shot_closure"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
