from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


def work() -> dict:
    return {
        "work_id": "frontier",
        "kind": driver.FRONTIER_EXPANSION_KIND,
        "priority": driver.FRONTIER_EXPANSION_PRIORITY,
        "identity": {},
        "payload": {
            "blocked_success_work_id": "blocked",
            "observation_id": "obs",
            "verification_frontier_sha256": "1" * 64,
            "adapter_frontier_sha256": "2" * 64,
            "verification_authority_sha256": "3" * 64,
            "boundary_root": "R1_CAPABILITY_ACQUISITION",
        },
        "status": "PENDING",
        "observations": 1,
        "reopen_count": 0,
    }


def request(sha_char: str = "a") -> dict:
    return {
        "schema": "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_REQUEST_V1",
        "status": "PASS__MINIMUM_STRUCTURAL_DISTINGUISHING_EVIDENCE_REQUEST_READY",
        "pass": True,
        "request_sha256": "sha256:" + sha_char * 64,
        "proof_capsule_sha256": "sha256:" + "p" * 64,
        "replay_capsule_sha256": "sha256:" + "r" * 64,
        "candidate_evidence_bundles": [
            {
                "route": "CHECKPOINTED_VERIFIED_EXECUTION",
                "missing_obligations": ["CONTROLLER_CHECKPOINT_BOUND"],
                "missing_obligation_count": 1,
            }
        ],
        "acquisition_authority": False,
        "provider_truth_authority": False,
        "verification_authority": False,
        "terminal_authority": False,
    }


def reduction(sha_char: str = "a", *, evidence_only: bool = True) -> dict:
    return {
        "pass": True,
        "status": "PASS__VERIFICATION_FRONTIER_REPAIR_CLASSES_REDUCED",
        "admissible_repair_classes": (
            ["NEW_DISTINGUISHING_EVIDENCE"]
            if evidence_only
            else [
                "VERIFIER_PRESERVING_SUCCESS_ADAPTER",
                "INDEPENDENT_READONLY_SUCCESS_VERIFIER",
                "NEW_DISTINGUISHING_EVIDENCE",
            ]
        ),
        "preferred_repair_order": ["NEW_DISTINGUISHING_EVIDENCE"],
        "must_acquire_new_distinguishing_evidence": evidence_only,
        "distinguishing_evidence_request": (
            request(sha_char) if evidence_only else None
        ),
    }


def receipt(request_sha: str) -> dict:
    out = {
        "pass": True,
        "request_sha256": request_sha,
        "acquisition_or_experiment_attempted": True,
        "evidence_trace_sha256": "sha256:" + "e" * 64,
        "verification_authority_mutated": False,
        "adapter_frontier_mutated": False,
        "provider_truth_authority": False,
        "provider_verification_authority": False,
        "provider_promotion_authority": False,
        "provider_acceptance_authority": False,
        "provider_terminal_authority": False,
    }
    out["receipt_sha256"] = driver._receipt_sha256(out)
    return out


class R3DistinguishingEvidenceProviderLoopV1Tests(unittest.TestCase):
    def _state(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "state.json"
        state = learning._empty_state()
        state["improvement_queue"] = {"frontier": work()}
        learning._refresh_stats(state)
        learning._write_state(state, path)
        return path

    def _hash_patches(self):
        return (
            mock.patch.object(
                driver,
                "_owned_success_learning_frontier_sha256",
                return_value="1" * 64,
            ),
            mock.patch.object(
                driver,
                "_owned_success_adapter_frontier_sha256",
                return_value="2" * 64,
            ),
            mock.patch.object(
                driver,
                "_owned_success_verification_authority_sha256",
                return_value="3" * 64,
            ),
            mock.patch.object(
                driver,
                "_frontier_acquisition_attempt_consumed",
                return_value=False,
            ),
            mock.patch.object(driver, "_record_frontier_acquisition_attempt"),
        )

    def test_provider_receipt_without_observed_reduction_change_fails_closed(self):
        before = reduction("a")
        provider = mock.Mock(
            return_value=receipt(before["distinguishing_evidence_request"]["request_sha256"])
        )
        patches = self._hash_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], mock.patch.object(
            driver,
            "_current_frontier_repair_reduction",
            return_value=before,
        ):
            out = driver._execute_distinguishing_evidence_acquisition(
                work(),
                state_path=self._state(),
                repo_root=driver.ROOT,
                provider=provider,
                provider_id="TEST_EVIDENCE_PROVIDER",
                repair_reduction=before,
            )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__EVIDENCE_PROVIDER_RECEIPT_WITHOUT_OBSERVED_REDUCTION_CHANGE",
        )
        self.assertFalse(out["progress"])
        provider.assert_called_once()

    def test_changed_minimum_request_counts_as_observed_progress(self):
        before = reduction("a")
        after = reduction("b")
        provider = mock.Mock(
            return_value=receipt(before["distinguishing_evidence_request"]["request_sha256"])
        )
        patches = self._hash_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], mock.patch.object(
            driver,
            "_current_frontier_repair_reduction",
            return_value=after,
        ):
            out = driver._execute_distinguishing_evidence_acquisition(
                work(),
                state_path=self._state(),
                repo_root=driver.ROOT,
                provider=provider,
                provider_id="TEST_EVIDENCE_PROVIDER",
                repair_reduction=before,
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        self.assertEqual(
            out["status"],
            "IMPROVEMENT_ADVANCED__DISTINGUISHING_EVIDENCE_CHANGED_REPAIR_REDUCTION",
        )
        self.assertNotEqual(
            out["request_sha256_before"],
            out["request_sha256_after"],
        )
        self.assertFalse(out["provider_truth_authority"])
        self.assertFalse(out["provider_verification_authority"])

    def test_provider_cannot_mutate_adapter_frontier(self):
        before = reduction("a")
        provider = mock.Mock(
            return_value=receipt(before["distinguishing_evidence_request"]["request_sha256"])
        )
        with mock.patch.object(
            driver,
            "_owned_success_learning_frontier_sha256",
            return_value="1" * 64,
        ), mock.patch.object(
            driver,
            "_owned_success_adapter_frontier_sha256",
            side_effect=["2" * 64, "9" * 64],
        ), mock.patch.object(
            driver,
            "_owned_success_verification_authority_sha256",
            side_effect=["3" * 64, "3" * 64],
        ), mock.patch.object(
            driver,
            "_frontier_acquisition_attempt_consumed",
            return_value=False,
        ), mock.patch.object(
            driver,
            "_record_frontier_acquisition_attempt",
        ):
            out = driver._execute_distinguishing_evidence_acquisition(
                work(),
                state_path=self._state(),
                repo_root=driver.ROOT,
                provider=provider,
                provider_id="TEST_EVIDENCE_PROVIDER",
                repair_reduction=before,
            )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "DISTINGUISHING_EVIDENCE_ADAPTER_FRONTIER_CHANGED",
        )

    def test_advance_once_uses_evidence_provider_only_for_evidence_only_gap(self):
        path = self._state()
        before = reduction("a")
        provider = mock.Mock(return_value={})
        evidence_out = {
            "schema": driver.SCHEMA,
            "status": "TEST_EVIDENCE_PROGRESS",
            "pass": True,
            "progress": True,
            "work_id": "frontier",
            "terminal_authority": False,
        }
        with mock.patch.object(
            driver,
            "_current_frontier_repair_reduction",
            return_value=before,
        ), mock.patch.object(
            driver,
            "_execute_distinguishing_evidence_acquisition",
            return_value=evidence_out,
        ) as execute:
            out = driver.advance_once(
                state_path=path,
                distinguishing_evidence_acquisition_provider=provider,
                distinguishing_evidence_acquisition_provider_id="TEST_EVIDENCE_PROVIDER",
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        kwargs = execute.call_args.kwargs
        self.assertIs(kwargs["provider"], provider)
        self.assertEqual(kwargs["repair_reduction"], before)
        self.assertFalse(out["provider_truth_authority"])
        self.assertFalse(out["provider_verification_authority"])

    def test_fabric_forwards_evidence_provider_to_background_compounding(self):
        tick = {
            "schema": driver.SCHEMA,
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "pass": True,
            "progress_count": 0,
            "actions": [],
            "terminal_authority": False,
        }
        provider = mock.Mock()
        with mock.patch.object(
            fabric.improvement_driver,
            "drain",
            return_value=tick,
        ) as drain:
            out = fabric.run(
                {
                    "mode": "CAPABILITY_SCHEDULER",
                    "payload": {
                        "work": [{
                            "work_id": "W",
                            "work_type": "CAPABILITY_BUILD",
                            "expected_capability_gain_lcb": 1,
                            "expected_efficiency_gain_lcb": 0,
                            "expected_reliability_gain_lcb": 1,
                            "reuse_breadth_lcb": 1,
                            "generalization_lcb": 1,
                            "success_probability_lcb": 1,
                            "wall_clock_cost_ub": 1,
                            "compute_cost_ub": 1,
                            "memory_cost_ub": 1,
                            "complexity_cost_ub": 1,
                        }],
                    },
                },
                distinguishing_evidence_acquisition_provider=provider,
                distinguishing_evidence_acquisition_provider_id="TEST_EVIDENCE_PROVIDER",
            )
        self.assertEqual(out["compounding_tick"], tick)
        kwargs = drain.call_args.kwargs
        self.assertIs(
            kwargs["distinguishing_evidence_acquisition_provider"],
            provider,
        )
        self.assertEqual(
            kwargs["distinguishing_evidence_acquisition_provider_id"],
            "TEST_EVIDENCE_PROVIDER",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
