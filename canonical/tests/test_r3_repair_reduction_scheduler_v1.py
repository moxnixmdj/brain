from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as driver


def _frontier_work() -> dict:
    return {
        "work_id": "frontier",
        "kind": driver.FRONTIER_EXPANSION_KIND,
        "priority": driver.FRONTIER_EXPANSION_PRIORITY,
        "identity": {},
        "payload": {
            "blocked_success_work_id": "blocked",
            "observation_id": "obs",
            "verification_frontier_sha256": "v" * 64,
            "adapter_frontier_sha256": "a" * 64,
            "verification_authority_sha256": "z" * 64,
            "required_capability_class": "INDEPENDENT_READONLY_SUCCESS_VERIFIER_OR_ADAPTER",
            "boundary_root": "R1_CAPABILITY_ACQUISITION",
        },
        "status": "PENDING",
        "observations": 1,
        "reopen_count": 0,
    }


class R3RepairReductionSchedulerV1Tests(unittest.TestCase):
    def _state(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "state.json"
        state = learning._empty_state()
        state["improvement_queue"] = {"frontier": _frontier_work()}
        learning._refresh_stats(state)
        learning._write_state(state, path)
        return path

    def test_evidence_only_reduction_skips_adapter_provider(self):
        path = self._state()
        reduction = {
            "pass": True,
            "status": "PASS__VERIFICATION_FRONTIER_REPAIR_CLASSES_REDUCED",
            "admissible_repair_classes": ["NEW_DISTINGUISHING_EVIDENCE"],
            "preferred_repair_order": ["NEW_DISTINGUISHING_EVIDENCE"],
            "must_acquire_new_distinguishing_evidence": True,
        }
        provider = mock.Mock(return_value={"pass": True})
        with mock.patch.object(
            driver,
            "_current_frontier_repair_reduction",
            return_value=reduction,
        ):
            out = driver.advance_once(
                state_path=path,
                verification_frontier_acquisition_provider=provider,
                verification_frontier_acquisition_provider_id="TEST_PROVIDER",
            )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["progress"], out)
        blocker = out["blockers"][0]
        self.assertEqual(
            blocker["blocker"],
            "R3_VERIFICATION_FRONTIER_NEW_DISTINGUISHING_EVIDENCE_REQUIRED",
        )
        self.assertTrue(blocker["adapter_acquisition_provider_skipped"])
        self.assertEqual(blocker["repair_class_reduction"], reduction)
        provider.assert_not_called()

    def test_noncanonical_frontier_identity_cannot_produce_pruning_verdict(self):
        path = self._state()
        state = learning.load_state(path)
        state["improvement_queue"]["frontier"]["payload"]["adapter_frontier_sha256"] = ""
        learning._write_state(state, path)
        with mock.patch.object(
            driver,
            "_owned_success_adapter_frontier_sha256",
            return_value="a" * 64,
        ), mock.patch.object(
            driver,
            "_owned_success_verification_authority_sha256",
            return_value="z" * 64,
        ):
            reduction = driver._current_frontier_repair_reduction(
                state["improvement_queue"]["frontier"],
                state_path=path,
                repo_root=driver.ROOT,
            )
        self.assertFalse(reduction["pass"], reduction)
        self.assertEqual(
            reduction["status"],
            "FRONTIER_REPAIR_REDUCTION_UNAVAILABLE",
        )
        self.assertNotIn(
            "admissible_repair_classes",
            reduction,
        )

    def test_adapter_admissible_reduction_is_forwarded_to_provider_request(self):
        path = self._state()
        reduction = {
            "pass": True,
            "status": "PASS__VERIFICATION_FRONTIER_REPAIR_CLASSES_REDUCED",
            "admissible_repair_classes": [
                "VERIFIER_PRESERVING_SUCCESS_ADAPTER",
                "INDEPENDENT_READONLY_SUCCESS_VERIFIER",
                "NEW_DISTINGUISHING_EVIDENCE",
            ],
            "preferred_repair_order": [
                "VERIFIER_PRESERVING_SUCCESS_ADAPTER",
                "INDEPENDENT_READONLY_SUCCESS_VERIFIER",
                "NEW_DISTINGUISHING_EVIDENCE",
            ],
            "must_acquire_new_distinguishing_evidence": False,
        }
        captured = {}

        def fake_execute(work, **kwargs):
            captured.update(kwargs)
            return {
                "schema": driver.SCHEMA,
                "status": "TEST_STOP",
                "pass": False,
                "progress": False,
                "work_id": "frontier",
                "terminal_authority": False,
            }

        with mock.patch.object(
            driver,
            "_current_frontier_repair_reduction",
            return_value=reduction,
        ), mock.patch.object(
            driver,
            "_execute_frontier_acquisition",
            side_effect=fake_execute,
        ):
            out = driver.advance_once(
                state_path=path,
                verification_frontier_acquisition_provider=lambda request: None,
                verification_frontier_acquisition_provider_id="TEST_PROVIDER",
            )
        self.assertFalse(out["pass"], out)
        self.assertEqual(captured["repair_reduction"], reduction)

    def test_execute_request_becomes_adapter_specific_when_reduced(self):
        path = self._state()
        work = _frontier_work()
        reduction = {
            "pass": True,
            "admissible_repair_classes": [
                "VERIFIER_PRESERVING_SUCCESS_ADAPTER",
                "NEW_DISTINGUISHING_EVIDENCE",
            ],
            "preferred_repair_order": [
                "VERIFIER_PRESERVING_SUCCESS_ADAPTER",
                "NEW_DISTINGUISHING_EVIDENCE",
            ],
            "must_acquire_new_distinguishing_evidence": False,
        }
        seen = {}

        def provider(request):
            seen.update(request)
            return {"pass": False, "status": "NO_CHANGE"}

        with mock.patch.object(
            driver,
            "_owned_success_learning_frontier_sha256",
            return_value="1" * 64,
        ), mock.patch.object(
            driver,
            "_owned_success_adapter_frontier_sha256",
            return_value="2" * 64,
        ), mock.patch.object(
            driver,
            "_owned_success_verification_authority_sha256",
            return_value="3" * 64,
        ), mock.patch.object(
            driver,
            "_record_frontier_acquisition_attempt",
        ):
            out = driver._execute_frontier_acquisition(
                work,
                state_path=path,
                repo_root=driver.ROOT,
                provider=provider,
                provider_id="TEST_PROVIDER",
                repair_reduction=reduction,
            )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            seen["required_capability_class"],
            "VERIFIER_PRESERVING_SUCCESS_ADAPTER",
        )
        self.assertEqual(
            seen["admissible_repair_classes"],
            reduction["admissible_repair_classes"],
        )
        self.assertFalse(seen["must_acquire_new_distinguishing_evidence"])
        self.assertFalse(seen["verification_authority_change_allowed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
