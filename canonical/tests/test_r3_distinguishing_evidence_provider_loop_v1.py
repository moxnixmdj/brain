from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


REQUEST_SHA = "sha256:" + "a" * 64
PROOF_SHA = "sha256:" + "b" * 64


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


def evidence_request() -> dict:
    return {
        "schema": "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_REQUEST_V1",
        "status": "PASS__MINIMUM_STRUCTURAL_DISTINGUISHING_EVIDENCE_REQUEST_READY",
        "pass": True,
        "request_sha256": REQUEST_SHA,
        "proof_capsule_sha256": PROOF_SHA,
        "replay_capsule_sha256": None,
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


def reduction() -> dict:
    return {
        "pass": True,
        "status": "PASS__VERIFICATION_FRONTIER_REPAIR_CLASSES_REDUCED",
        "admissible_repair_classes": ["NEW_DISTINGUISHING_EVIDENCE"],
        "preferred_repair_order": ["NEW_DISTINGUISHING_EVIDENCE"],
        "must_acquire_new_distinguishing_evidence": True,
        "distinguishing_evidence_request": evidence_request(),
    }


def proof_context() -> dict:
    return {
        "observation_id": "obs",
        "proof_capsule_sha256": PROOF_SHA,
        "material": {
            "source_schema": "TEST_SUCCESS",
            "source_status": "PASS",
            "task_id": "task",
            "selected_plan": ["cap"],
            "verified_target_effects": ["DONE"],
            "controller_checkpoint": {"path": None, "plan_sha256": None},
            "execution": [
                {
                    "capability_id": "cap",
                    "pass": True,
                    "status": "PASS",
                    "composition_capsule_head_hash": "c" * 64,
                }
            ],
            "cognition_dependency_class": None,
            "model_dependency_count": 0,
            "semantic_acceptance_complete": False,
            "raw_goal_sha256": None,
            "raw_task_contract_sha256": None,
            "raw_acceptance_obligation_count": None,
            "accepted_raw_obligation_ids": [],
            "compiled_capability_id": None,
            "raw_goal_acceptance": None,
        },
    }


def receipt(*, extra_evidence: dict | None = None) -> dict:
    candidate = {
        "controller_checkpoint": {
            "path": "canonical/astra_runtime/tmp/test-checkpoint.json",
            "plan_sha256": "d" * 64,
        }
    }
    if extra_evidence:
        candidate.update(extra_evidence)
    out = {
        "schema": driver.DISTINGUISHING_EVIDENCE_RECEIPT_SCHEMA,
        "pass": True,
        "request_sha256": REQUEST_SHA,
        "route": "CHECKPOINTED_VERIFIED_EXECUTION",
        "candidate_evidence": candidate,
        "acquisition_or_experiment_attempted": True,
        "evidence_trace_sha256": "sha256:" + "e" * 64,
        "runtime_source_mutated": False,
        "r3_learning_state_mutated": False,
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

    def _authority_patches(self):
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
                "_frontier_sha256",
                return_value="sha256:" + "4" * 64,
            ),
            mock.patch.object(
                learning,
                "get_success_proof_context",
                return_value=proof_context(),
            ),
            mock.patch.object(
                learning,
                "get_success_replay_context",
                side_effect=learning.SelfImprovementError("NO_REPLAY"),
            ),
        )

    def test_candidate_bundle_reingests_through_normal_success_pipeline(self):
        path = self._state()
        provider = mock.Mock(return_value=receipt())
        patches = self._authority_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            out = driver._execute_distinguishing_evidence_acquisition(
                work(),
                state_path=path,
                repo_root=driver.ROOT,
                provider=provider,
                provider_id="TEST_EVIDENCE_PROVIDER",
                repair_reduction=reduction(),
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        self.assertTrue(out["candidate_only"])
        self.assertFalse(out["candidate_evidence_verified"])
        self.assertFalse(out["provider_truth_authority"])
        self.assertFalse(out["provider_verification_authority"])
        state = learning.load_state(path)
        self.assertEqual(
            state["improvement_queue"]["frontier"]["status"],
            "RESOLVED",
        )
        candidate_id = out["candidate_observation_id"]
        self.assertIn(candidate_id, state["observations"])
        candidate = state["observations"][candidate_id]
        self.assertIsInstance(candidate.get("proof_capsule"), dict)
        queued = [
            row
            for row in state["improvement_queue"].values()
            if row.get("kind") == "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE"
            and row.get("status") == "PENDING"
        ]
        self.assertEqual(len(queued), 1)

    def test_provider_cannot_mutate_r3_learning_state_directly(self):
        path = self._state()

        def mutate_state(_request):
            state = learning.load_state(path)
            state["stats"]["provider_was_here"] = 1
            learning._write_state(state, path)
            return receipt()

        patches = self._authority_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            out = driver._execute_distinguishing_evidence_acquisition(
                work(),
                state_path=path,
                repo_root=driver.ROOT,
                provider=mutate_state,
                provider_id="TEST_EVIDENCE_PROVIDER",
                repair_reduction=reduction(),
            )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "DISTINGUISHING_EVIDENCE_PROVIDER_MUTATED_R3_STATE",
        )

    def test_provider_cannot_mutate_adapter_frontier(self):
        path = self._state()
        provider = mock.Mock(return_value=receipt())
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
            "_frontier_sha256",
            side_effect=["sha256:" + "4" * 64, "sha256:" + "4" * 64],
        ), mock.patch.object(
            learning,
            "get_success_proof_context",
            return_value=proof_context(),
        ):
            out = driver._execute_distinguishing_evidence_acquisition(
                work(),
                state_path=path,
                repo_root=driver.ROOT,
                provider=provider,
                provider_id="TEST_EVIDENCE_PROVIDER",
                repair_reduction=reduction(),
            )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "DISTINGUISHING_EVIDENCE_ADAPTER_FRONTIER_CHANGED",
        )

    def test_incomplete_or_extra_bundle_is_rejected(self):
        path = self._state()
        provider = mock.Mock(
            return_value=receipt(extra_evidence={"selected_plan": ["forged"]})
        )
        patches = self._authority_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
            out = driver._execute_distinguishing_evidence_acquisition(
                work(),
                state_path=path,
                repo_root=driver.ROOT,
                provider=provider,
                provider_id="TEST_EVIDENCE_PROVIDER",
                repair_reduction=reduction(),
            )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "DISTINGUISHING_EVIDENCE_MINIMUM_BUNDLE_INCOMPLETE_OR_EXTRA",
        )

    def test_advance_once_uses_evidence_provider_only_for_evidence_only_gap(self):
        path = self._state()
        provider = mock.Mock(return_value=receipt())
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
            return_value=reduction(),
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
