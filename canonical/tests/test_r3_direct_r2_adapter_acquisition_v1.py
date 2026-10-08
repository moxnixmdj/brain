from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime import live_brain_runtime_v1 as live
from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import r3_direct_r2_success_adapter_v1 as direct_adapter

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"
STATE = TMP / "R3_DIRECT_R2_ACQUISITION_STATE.json"
RULES = ROOT / direct_adapter.RULES_PATH


class R3DirectR2AdapterAcquisitionV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        if STATE.exists():
            STATE.unlink()
        self._rules_original = RULES.read_bytes()
        RULES.write_text(
            json.dumps(
                {
                    "schema": "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_RULES_V1",
                    "version": 1,
                    "rules": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        RULES.write_bytes(self._rules_original)
        if STATE.exists():
            STATE.unlink()

    def _run_direct(self, task_id: str, literal: str):
        out = live.run_decision(
            {
                "task_id": task_id,
                "goal": f'Reply with exactly "{literal}"',
            },
            state_path=STATE,
            learn=True,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["decision_output"]["r2_fixed_point_status"],
            "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED",
        )
        self.assertIsInstance(out.get("learning"), dict)
        self.assertTrue(out["learning"]["proof_available"], out["learning"])
        return out

    def test_park_acquire_reopen_verify_then_sibling_reuses_rule(self):
        first = self._run_direct("direct-rule-a", "alpha")
        observation_id = first["learning"]["observation_id"]

        parked = driver.advance_once(state_path=STATE, repo_root=ROOT)
        self.assertEqual(
            parked["status"],
            "IMPROVEMENT_PARKED__CURRENT_OWNED_VERIFICATION_FRONTIER_INCOMPLETE",
            parked,
        )
        self.assertEqual(parked["observation_id"], observation_id)

        authority_before = driver._owned_success_verification_authority_sha256(
            repo_root=ROOT
        )
        acquired = driver.advance_once(state_path=STATE, repo_root=ROOT)
        self.assertTrue(acquired["pass"], acquired)
        self.assertEqual(
            acquired["status"],
            "IMPROVEMENT_ADVANCED__SUCCESS_ADAPTER_FRONTIER_EXPANDED_AND_SUCCESS_REOPENED",
        )
        self.assertTrue(acquired["verification_authority_unchanged"], acquired)
        self.assertEqual(
            authority_before,
            driver._owned_success_verification_authority_sha256(repo_root=ROOT),
        )
        self.assertEqual(
            acquired["provider_result"]["route_id"],
            "DIRECT_ADEQUACY::EXACT_LITERAL_RESPONSE_V1",
        )

        verified = driver.advance_once(state_path=STATE, repo_root=ROOT)
        self.assertTrue(verified["pass"], verified)
        self.assertEqual(
            verified["status"],
            "IMPROVEMENT_ADVANCED__SUCCESS_BECAME_VERIFIED_EPISODE",
        )
        state = live._learning_module().load_state(STATE)
        self.assertGreaterEqual(state["stats"]["verified_episode_count"], 1)

        rules_after_first = RULES.read_bytes()
        self.assertEqual(len(json.loads(rules_after_first)["rules"]), 1)

        second = self._run_direct("direct-rule-b", "beta")
        second_observation_id = second["learning"]["observation_id"]
        reused = driver.advance_once(state_path=STATE, repo_root=ROOT)
        self.assertTrue(reused["pass"], reused)
        self.assertEqual(
            reused["status"],
            "IMPROVEMENT_ADVANCED__SUCCESS_BECAME_VERIFIED_EPISODE",
        )
        self.assertEqual(RULES.read_bytes(), rules_after_first)

        state = live._learning_module().load_state(STATE)
        self.assertGreaterEqual(state["stats"]["verified_episode_count"], 2)
        obs = state["observations"][second_observation_id]
        self.assertNotEqual(
            obs.get("learning_disposition"),
            "UNRESOLVED_WITH_CURRENT_OWNED_VERIFICATION_FRONTIER",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
