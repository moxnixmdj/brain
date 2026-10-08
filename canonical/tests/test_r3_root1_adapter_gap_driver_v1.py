from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import r3_root1_adapter_gap_witness_v1 as witness


class R3Root1AdapterGapDriverV1Tests(unittest.TestCase):
    def test_proof_bearing_owned_adapter_miss_surfaces_constructive_root1_gap(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            observed = learning.record_success_observation(
                {
                    "schema": "TEST_PROOF_BEARING_SUCCESS_V1",
                    "status": "PASS__CHECKPOINTED_BUT_UNADAPTED",
                    "pass": True,
                    "task_id": "proof-gap",
                    "selected_plan": ["verified.test.capability"],
                    "verified_target_effects": ["test.effect"],
                    "controller_checkpoint": {
                        "path": "canonical/nonexistent-test-checkpoint.json",
                        "plan_sha256": "a" * 64,
                    },
                    "execution": [],
                },
                surface="PROOF_BEARING_UNADAPTED_SURFACE",
                state_path=state_path,
                replay_context={
                    "mode": "generic",
                    "problem": {"task_id": "proof-gap", "target_effects": ["test.effect"]},
                },
            )

            first = driver.advance_once(state_path=state_path)
            self.assertTrue(first["pass"], first)
            self.assertFalse(first["progress"], first)
            self.assertTrue(first["disposition_recorded"], first)

            second = driver.advance_once(state_path=state_path)
            self.assertTrue(second["pass"], second)
            self.assertFalse(second["progress"], second)
            blocker = next(
                row
                for row in second["blockers"]
                if row["kind"] == driver.FRONTIER_EXPANSION_KIND
            )
            self.assertEqual(
                blocker["blocker"],
                "ROOT1_CONSTRUCTIVE_R3_ADAPTER_AUTHORING_GAP__NO_BOUND_ACQUISITION_ROUTE",
            )
            self.assertTrue(blocker["root1_positive_gap_established"])
            gap = blocker["root1_gap_witness"]
            self.assertTrue(gap["pass"], gap)
            self.assertEqual(
                gap["required_primitive"],
                witness.REQUIRED_PRIMITIVE,
            )
            self.assertTrue(
                gap["root1_transaction"]["gate"]["root1_active"]
            )
            self.assertEqual(
                gap["root1_transaction"]["minimum_delta"]["missing_primitives"],
                [witness.REQUIRED_PRIMITIVE],
            )
            self.assertEqual(
                gap["root1_transaction"]["route_cover"]["status"],
                "NO_ADMISSIBLE_ROUTE_COVER",
            )

            state = learning.load_state(state_path)
            parked = state["improvement_queue"][observed["improvement_work_id"]]
            self.assertEqual(parked["status"], "PARKED")

    def test_proofless_success_does_not_fabricate_constructive_root1_gap(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            learning.record_success_observation(
                {
                    "schema": "TEST_OPAQUE_SUCCESS_V1",
                    "status": "PASS__OPAQUE",
                    "pass": True,
                    "result": {"opaque": True},
                },
                surface="OPAQUE_SURFACE",
                state_path=state_path,
                replay_context={
                    "mode": "generic",
                    "problem": {"task_id": "opaque"},
                },
            )
            first = driver.advance_once(state_path=state_path)
            self.assertTrue(first["disposition_recorded"], first)
            second = driver.advance_once(state_path=state_path)

        blocker = next(
            row
            for row in second["blockers"]
            if row["kind"] == driver.FRONTIER_EXPANSION_KIND
        )
        self.assertEqual(
            blocker["blocker"],
            "ROOT1_VERIFICATION_CAPABILITY_ACQUISITION_REQUIRED",
        )
        self.assertFalse(blocker["root1_positive_gap_established"])
        self.assertFalse(blocker["root1_gap_witness"]["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
