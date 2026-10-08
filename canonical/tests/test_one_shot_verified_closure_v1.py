from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import one_shot_verified_closure_v1 as closure
from canonical.runtime import root1_default_acquisition_provider_v1 as root1


class Root1DefaultProviderTests(unittest.TestCase):
    def test_frontier_provider_is_present_but_has_zero_authority(self):
        request = {
            "kind": "EXPAND_SUCCESS_VERIFICATION_FRONTIER",
            "allowed_frontier_change_class": "SUCCESS_ADAPTER_ONLY__VERIFICATION_AUTHORITY_IMMUTABLE",
            "verification_authority_change_allowed": False,
            "required_capability_class": "SUCCESS_TO_VERIFIABLE_EPISODE_ADAPTER",
            "adapter_frontier_sha256": "a" * 64,
            "verification_authority_sha256": "b" * 64,
        }
        out = root1.acquire(request)
        self.assertEqual(out["provider_id"], root1.PROVIDER_ID)
        self.assertFalse(out["pass"])
        self.assertTrue(out["exhaustive_over_sound_routes_derivable_from_request"])
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])


class OneShotVerifiedClosureTests(unittest.TestCase):
    def _state(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "state.json"
        path.write_text(
            '{"schema":"TEST","observations":{},"failures":{},"episodes":{},'
            '"skills":{},"improvement_queue":{},"stats":{}}\n',
            encoding="utf-8",
        )
        return path

    def test_verified_task_returns_only_verified_postcondition(self):
        state = self._state()
        decision = {
            "pass": True,
            "status": "PASS",
            "actual_goal_satisfaction_verified": True,
            "r2_meta_action": "RETURN_VERIFIED_RESULT",
        }
        tick = {
            "pass": True,
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "progress_count": 0,
            "actions": [],
            "next_improvement_action": None,
        }
        with (
            mock.patch.object(closure.r2, "run", return_value=decision),
            mock.patch.object(closure.r3, "drain", return_value=tick),
            mock.patch.object(closure, "_state_fingerprint", side_effect=["s0", "s0"]),
        ):
            out = closure.run({"task_id": "t", "goal": "g"}, state_path=state)
        self.assertEqual(out["status"], closure.VERIFIED)
        self.assertIn(out["postcondition_state"], closure.RETURN_STATES)
        self.assertTrue(out["fixed_point_reached"])

    def test_open_task_with_no_progress_totalizes_to_irreducible(self):
        state = self._state()
        decision = {
            "pass": False,
            "status": "OPEN__POLICY",
            "actual_goal_satisfaction_verified": False,
            "r2_meta_action": "REPAIR_OR_EXPAND_VERIFIABLE_ADEQUACY_COVER",
            "r2_fixed_point_status": "OPEN__R2_EDGE_RESOLVER_NO_PROGRESSIVE_CANDIDATE",
        }
        tick = {
            "pass": True,
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "progress_count": 0,
            "actions": [],
            "next_improvement_action": None,
        }
        with (
            mock.patch.object(closure.r2, "run", return_value=decision),
            mock.patch.object(closure.r3, "drain", return_value=tick),
            mock.patch.object(closure, "_state_fingerprint", side_effect=["s0", "s0"]),
        ):
            out = closure.run({"task_id": "t", "goal": "g"}, state_path=state)
        self.assertEqual(out["status"], closure.IRREDUCIBLE)
        self.assertIn(out["postcondition_state"], closure.RETURN_STATES)
        self.assertFalse(out["internal_provider_missing"])
        cert = out["irreducible_certificate"]
        self.assertEqual(cert["residual_class"], "MISSING_ADEQUATE_POLICY_OR_NEW_CAPABILITY")
        self.assertFalse(cert["internal_provider_missing"])

    def test_native_root1_provider_is_bound_when_caller_omits_one(self):
        state = self._state()
        decision = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "actual_goal_satisfaction_verified": False,
            "r2_meta_action": "ABSTAIN_FAIL_CLOSED",
        }
        tick = {
            "pass": True,
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "progress_count": 0,
            "actions": [],
            "next_improvement_action": None,
        }
        with (
            mock.patch.object(closure.r2, "run", return_value=decision),
            mock.patch.object(closure.r3, "drain", return_value=tick) as drain,
            mock.patch.object(closure, "_state_fingerprint", side_effect=["s0", "s0"]),
        ):
            closure.run({"task_id": "t", "goal": "g"}, state_path=state)
        self.assertIsNotNone(drain.call_args.kwargs["verification_frontier_acquisition_provider"])
        r2_kwargs = closure.r2.run.call_args.kwargs
        self.assertIsNotNone(r2_kwargs["information_provider"])
        self.assertIsNotNone(r2_kwargs["proposal_provider"])
        self.assertIsNotNone(r2_kwargs["capability_expander"])
        self.assertEqual(
            drain.call_args.kwargs["verification_frontier_acquisition_provider_id"],
            root1.PROVIDER_ID,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
