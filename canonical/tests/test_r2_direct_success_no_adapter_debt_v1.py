from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import live_brain_runtime_v1 as live

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"


class R2DirectSuccessNoAdapterDebtV1Tests(unittest.TestCase):
    def test_verified_direct_success_records_owned_telemetry_without_adapter_debt(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            work = Path(td)
            token = work.name.replace("_", "-")
            state_path = work / "state.json"
            task_id = "r2-direct-no-debt-" + token
            checkpoint = (
                ROOT
                / "canonical"
                / "astra_runtime"
                / "state"
                / (task_id + "__live-raw-goal-controller__CONTROLLER_CHECKPOINT.json")
            )
            try:
                out = live.run(
                    {
                        "mode": "decision",
                        "state_path": state_path.as_posix(),
                        "request": {
                            "task_id": task_id,
                            "goal": 'Reply with exactly "hello".',
                        },
                    },
                    repo_root=ROOT,
                )
                self.assertTrue(out["pass"], out)
                self.assertTrue(out["actual_goal_satisfaction_verified"], out)
                self.assertTrue(out["semantic_acceptance_complete"], out)
                self.assertEqual(
                    out["decision_output"]["r2_fixed_point_status"],
                    "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED",
                )
                observed = out["learning"]
                self.assertEqual(
                    observed["status"],
                    "SUCCESS_OBSERVED__OWNED_DIRECT_EXECUTION__NO_NEW_EXECUTABLE_CAPABILITY_EVIDENCE",
                    observed,
                )
                self.assertFalse(observed["new_improvement_work_enqueued"], observed)
                self.assertFalse(observed["frontier_expansion_required"], observed)
                self.assertFalse(observed["permanent_reuse_authorized"], observed)

                state = learning.load_state(state_path)
                pending = [
                    row
                    for row in state["improvement_queue"].values()
                    if row.get("status") in {"PENDING", "PARKED"}
                ]
                self.assertEqual(pending, [], pending)
                observations = list(state["observations"].values())
                self.assertEqual(len(observations), 1, observations)
                self.assertEqual(
                    observations[0]["learning_disposition"],
                    "NO_NEW_EXECUTABLE_CAPABILITY_EVIDENCE_FROM_OWNED_DIRECT_SURFACE",
                )
                self.assertTrue(observations[0]["existing_capability_authority_unchanged"])
            finally:
                try:
                    checkpoint.unlink()
                except FileNotFoundError:
                    pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
