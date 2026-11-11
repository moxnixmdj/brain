from __future__ import annotations

import unittest
from unittest import mock

from canonical.runtime import root3_production_astra_brokered_launcher_v2 as launcher

MISSION = "canonical/astra_runtime/missions/ASTRA-REAL-PROFESSIONAL-SYSTEM-STABILITY-001.json"


class Root3ProductionAstraBrokeredLauncherV2Tests(unittest.TestCase):
    def test_canonical_mission_relative_accepts_repo_mission(self):
        self.assertEqual(launcher.canonical_mission_relative(MISSION), MISSION)

    def test_canonical_mission_relative_rejects_escape(self):
        with self.assertRaisesRegex(
            launcher.ProductionBrokeredLauncherError,
            "MISSION_PATH_OUTSIDE_REPO",
        ):
            launcher.canonical_mission_relative("../outside.json")

    def test_child_policy_enters_guarded_v1_inside_input_mount(self):
        policy = launcher.build_child_policy(MISSION)
        self.assertEqual(
            policy["argv"],
            [
                "/usr/bin/python3",
                "/input/canonical/runtime/root3_production_astra_launcher_v1.py",
                "/input/" + MISSION,
            ],
        )
        self.assertEqual(policy["input_dir"], str(launcher.REPO_ROOT))
        self.assertEqual(policy["limits"]["broker_max_bytes"], 8_000_000)

    def test_run_mission_uses_closed_parent_dispatch(self):
        observed = {}

        def fake_run(policy, handler, *, max_requests):
            observed["policy"] = policy
            observed["max_requests"] = max_requests
            with mock.patch.object(
                launcher.registry,
                "dispatch",
                return_value={"ok": True},
            ) as dispatch:
                result = handler({"request_sha256": "x"})
                dispatch.assert_called_once()
                self.assertEqual(result, {"ok": True})
            return {
                "status": "CHILD_EXITED",
                "broker_error": None,
                "returncode": 0,
            }

        with mock.patch.object(
            launcher.brokered,
            "run_confined_brokered",
            side_effect=fake_run,
        ):
            out = launcher.run_mission(MISSION)

        self.assertEqual(out["mission"], MISSION)
        self.assertEqual(
            out["production_entry"],
            "BROKERED_NAMESPACE_V2_TO_SUBPROCESS_GUARDED_V1",
        )
        self.assertTrue(out["closed_parent_registry"])
        self.assertFalse(out["generic_parent_effect_fallback"])
        self.assertEqual(observed["max_requests"], 4096)

    def test_result_exit_code_fails_closed_on_namespace_or_broker_failure(self):
        self.assertEqual(
            launcher.result_exit_code({
                "namespace": {
                    "status": "BROKER_PROTOCOL_ERROR",
                    "broker_error": "bad",
                    "returncode": 0,
                }
            }),
            70,
        )
        self.assertEqual(
            launcher.result_exit_code({
                "namespace": {
                    "status": "CHILD_EXITED",
                    "broker_error": "bad",
                    "returncode": 0,
                }
            }),
            71,
        )
        self.assertEqual(
            launcher.result_exit_code({
                "namespace": {
                    "status": "CHILD_EXITED",
                    "broker_error": None,
                    "returncode": 9,
                }
            }),
            9,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
