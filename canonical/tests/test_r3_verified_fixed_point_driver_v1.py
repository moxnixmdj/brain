from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from canonical.runtime import r3_verified_fixed_point_driver_v1 as fixed


class VerifiedFixedPointDriverTest(unittest.TestCase):
    def test_drains_until_state_is_stable(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            state_path.write_text('{"generation":0}\n', encoding="utf-8")
            calls = {"count": 0}

            def drain(**kwargs):
                calls["count"] += 1
                if calls["count"] == 1:
                    state_path.write_text('{"generation":1}\n', encoding="utf-8")
                    return {
                        "status": "IMPROVEMENT_QUEUE_ADVANCED",
                        "progress_count": 1,
                        "next_improvement_action": {"kind": "VERIFY_EPISODE"},
                    }
                return {
                    "status": "IMPROVEMENT_QUEUE_STABLE",
                    "progress_count": 0,
                    "next_improvement_action": None,
                }

            learning = SimpleNamespace(
                DEFAULT_STATE_PATH=state_path,
                load_state=lambda path: {
                    "improvement_queue": {},
                    "stats": {"pending_improvement_count": 0},
                },
                next_improvement_action=lambda state_path: None,
            )
            driver = SimpleNamespace(drain=drain)
            with patch.object(fixed, "_learning_module", return_value=learning), patch.object(
                fixed, "_queue_driver_module", return_value=driver
            ):
                result = fixed.run(
                    state_path=state_path,
                    repo_root=td,
                    max_rounds=4,
                    max_actions_per_round=8,
                )

        self.assertTrue(result["pass"])
        self.assertTrue(result["fixed_point"])
        self.assertEqual(result["round_count"], 2)
        self.assertEqual(calls["count"], 2)
        self.assertIsNone(result["residual_boundary"])
        self.assertFalse(result["terminal_authority"])

    def test_safety_bound_is_not_a_fixed_point(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            state_path.write_text('{"generation":0}\n', encoding="utf-8")
            calls = {"count": 0}

            def drain(**kwargs):
                calls["count"] += 1
                state_path.write_text(
                    json.dumps({"generation": calls["count"]}) + "\n",
                    encoding="utf-8",
                )
                return {
                    "status": "IMPROVEMENT_QUEUE_ADVANCED",
                    "progress_count": 1,
                    "next_improvement_action": {"kind": "VERIFY_EPISODE"},
                }

            learning = SimpleNamespace(
                DEFAULT_STATE_PATH=state_path,
                load_state=lambda path: {
                    "improvement_queue": {
                        "w1": {
                            "status": "PENDING",
                            "kind": "VERIFY_EPISODE",
                            "priority": 10,
                        }
                    },
                    "stats": {"pending_improvement_count": 1},
                },
                next_improvement_action=lambda state_path: {"kind": "VERIFY_EPISODE"},
            )
            driver = SimpleNamespace(drain=drain)
            with patch.object(fixed, "_learning_module", return_value=learning), patch.object(
                fixed, "_queue_driver_module", return_value=driver
            ):
                result = fixed.run(
                    state_path=state_path,
                    repo_root=td,
                    max_rounds=2,
                    max_actions_per_round=8,
                )

        self.assertFalse(result["pass"])
        self.assertFalse(result["fixed_point"])
        self.assertEqual(result["status"], "VERIFIED_R3_FIXED_POINT_SAFETY_BOUND_REACHED")
        self.assertEqual(
            result["residual_boundary"],
            "CURRENT_R3_WORK_REMAINS_PENDING_OR_PROVIDER_BOUND",
        )

    def test_invalid_bounds_fail_closed(self):
        with self.assertRaises(fixed.VerifiedFixedPointError):
            fixed.run(max_rounds=0)
        with self.assertRaises(fixed.VerifiedFixedPointError):
            fixed.run(max_actions_per_round=33)


if __name__ == "__main__":
    unittest.main()
