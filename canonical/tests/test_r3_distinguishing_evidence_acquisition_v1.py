from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from canonical.runtime import r3_distinguishing_evidence_acquisition_v1 as acquisition
from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import unified_cognitive_fabric_v1 as fabric
from canonical.runtime import r3_verification_frontier_repair_reducer_v1 as reducer


def compiled_request() -> dict:
    return {
        "schema": "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_REQUEST_V1",
        "status": "PASS__MINIMUM_STRUCTURAL_DISTINGUISHING_EVIDENCE_REQUEST_READY",
        "pass": True,
        "request_sha256": "sha256:" + "a" * 64,
        "minimum_missing_obligation_count": 3,
        "candidate_evidence_bundles": [
            {
                "route": "CHECKPOINTED_VERIFIED_EXECUTION",
                "missing_obligations": [
                    "NONEMPTY_SELECTED_PLAN",
                    "CONTROLLER_CHECKPOINT_BOUND",
                    "ALL_EXECUTION_ROWS_PASS",
                ],
                "missing_obligation_count": 3,
            }
        ],
    }


def candidate_output(task_id: str = "task-1") -> dict:
    return {
        "schema": "TEST_SUCCESS",
        "status": "PASS__TEST",
        "pass": True,
        "task_id": task_id,
        "selected_plan": ["cap.a"],
        "verified_target_effects": ["effect.done"],
        "controller_checkpoint": {
            "path": "checkpoint.json",
            "plan_sha256": "b" * 64,
        },
        "execution": [
            {
                "capability_id": "cap.a",
                "pass": True,
                "status": "PASS",
                "composition_capsule_head_hash": "c" * 64,
            }
        ],
        "terminal_authority": False,
    }


def provider_result(*, request_sha: str | None = None, task_id: str = "task-1") -> dict:
    return {
        "schema": acquisition.CANDIDATE_SCHEMA,
        "pass": True,
        "request_sha256": request_sha or compiled_request()["request_sha256"],
        "candidate_success_output": candidate_output(task_id),
        "provider_truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }


class R3DistinguishingEvidenceAcquisitionV1Tests(unittest.TestCase):
    def _success_patches(self):
        proof = {
            "proof_capsule_sha256": "sha256:" + "1" * 64,
            "material": {"task_id": "task-1"},
        }
        replay = {
            "replay_capsule_sha256": "sha256:" + "2" * 64,
            "context": {"mode": "generic", "request": {"task_id": "task-1"}},
        }
        candidate_proof = {
            "schema": "PROJECT_BRAIN_SUCCESS_PROOF_CAPSULE_V1",
            "sha256": "sha256:" + "3" * 64,
            "material": {"task_id": "task-1"},
        }
        context = {
            "schema": "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_AUTHOR_CONTEXT_V1",
            "pass": True,
        }
        reduction = {
            "pass": True,
            "admissible_repair_classes": [reducer.ADAPTER, reducer.NEW_EVIDENCE],
            "must_acquire_new_distinguishing_evidence": False,
        }
        recorded = {
            "pass": True,
            "proof_available": True,
            "observation_id": "observation:new",
            "improvement_work_id": "work:new",
        }
        return (
            patch.object(acquisition.learning, "get_success_proof_context", return_value=proof),
            patch.object(acquisition.learning, "get_success_replay_context", return_value=replay),
            patch.object(acquisition.learning, "_make_success_proof_capsule", return_value=candidate_proof),
            patch.object(acquisition.author_context, "compile_context", return_value=context),
            patch.object(acquisition.reducer, "reduce_author_context", return_value=reduction),
            patch.object(acquisition.learning, "record_success_observation", return_value=recorded),
        )

    def test_provider_candidate_is_reingested_only_as_unverified_success(self):
        provider = Mock(return_value=provider_result())
        patches = self._success_patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5] as record:
            out = acquisition.acquire(
                compiled_request(),
                observation_id="observation:source",
                state_path=Path("/tmp/r3-test-state.json"),
                provider=provider,
                provider_id="TEST_PROVIDER",
                improvement_work_id="work:frontier",
                blocked_success_work_id="work:blocked",
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"])
        self.assertEqual(out["new_observation_id"], "observation:new")
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])
        request = provider.call_args.args[0]
        self.assertFalse(request["provider_contract"]["provider_truth_authority"])
        self.assertFalse(request["provider_contract"]["provider_verification_authority"])
        self.assertFalse(request["provider_contract"]["automatic_effectful_replay_authorized"])
        record.assert_called_once()
        self.assertEqual(
            record.call_args.kwargs["surface"],
            acquisition.SURFACE,
        )

    def test_stale_request_digest_is_rejected_before_reingestion(self):
        provider = Mock(
            return_value=provider_result(request_sha="sha256:" + "f" * 64)
        )
        with patch.object(acquisition.learning, "record_success_observation") as record:
            out = acquisition.acquire(
                compiled_request(),
                observation_id="observation:source",
                state_path=Path("/tmp/r3-test-state.json"),
                provider=provider,
                provider_id="TEST_PROVIDER",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "DISTINGUISHING_EVIDENCE_CANDIDATE_BINDING_INVALID",
        )
        record.assert_not_called()

    def test_provider_authority_escalation_is_rejected(self):
        forged = provider_result()
        forged["verification_authority"] = True
        with patch.object(acquisition.learning, "record_success_observation") as record:
            out = acquisition.acquire(
                compiled_request(),
                observation_id="observation:source",
                state_path=Path("/tmp/r3-test-state.json"),
                provider=lambda _request: forged,
                provider_id="FORGED_PROVIDER",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "DISTINGUISHING_EVIDENCE_PROVIDER_AUTHORITY_ESCALATION_REJECTED",
        )
        record.assert_not_called()

    def test_candidate_that_does_not_reduce_gap_is_rejected(self):
        patches = self._success_patches()
        unchanged = {
            "pass": True,
            "admissible_repair_classes": [reducer.NEW_EVIDENCE],
            "must_acquire_new_distinguishing_evidence": True,
        }
        next_request = {
            "pass": True,
            "minimum_missing_obligation_count": 3,
        }
        with patches[0], patches[1], patches[2], patches[3], patch.object(
            acquisition.reducer,
            "reduce_author_context",
            return_value=unchanged,
        ), patch.object(
            acquisition.request_compiler,
            "compile_request",
            return_value=next_request,
        ), patch.object(acquisition.learning, "record_success_observation") as record:
            out = acquisition.acquire(
                compiled_request(),
                observation_id="observation:source",
                state_path=Path("/tmp/r3-test-state.json"),
                provider=lambda _request: provider_result(),
                provider_id="TEST_PROVIDER",
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "DISTINGUISHING_EVIDENCE_CANDIDATE_DID_NOT_REDUCE_GAP",
        )
        record.assert_not_called()

    def test_queue_routes_evidence_only_gap_to_evidence_provider_not_adapter_provider(self):
        work = {
            "work_id": "work:frontier",
            "kind": driver.FRONTIER_EXPANSION_KIND,
            "status": "PENDING",
            "observations": 1,
            "payload": {
                "blocked_success_work_id": "work:blocked",
                "observation_id": "observation:source",
                "boundary_root": "R1_CAPABILITY_ACQUISITION",
            },
        }
        state = {
            "improvement_queue": {"work:frontier": work},
            "observations": {},
        }
        reduction = {
            "pass": True,
            "admissible_repair_classes": [reducer.NEW_EVIDENCE],
            "must_acquire_new_distinguishing_evidence": True,
            "distinguishing_evidence_request": compiled_request(),
        }
        provider = Mock()
        acquired = {
            "schema": acquisition.SCHEMA,
            "status": "PASS__DISTINGUISHING_EVIDENCE_CANDIDATE_REINGESTED",
            "pass": True,
            "progress": True,
            "new_observation_id": "observation:new",
        }
        with patch.object(
            driver,
            "_reactivate_parked_successes",
            return_value={"frontier_sha256": "frontier"},
        ), patch.object(
            driver.learning,
            "load_state",
            return_value=state,
        ), patch.object(
            driver,
            "_repark_stale_replayable_success_after_resolved_handoff",
            return_value=None,
        ), patch.object(
            driver,
            "_frontier_acquisition_attempt_consumed",
            return_value=False,
        ), patch.object(
            driver,
            "_attempt_already_consumed_current_evidence",
            return_value=False,
        ), patch.object(
            driver,
            "_current_frontier_repair_reduction",
            return_value=reduction,
        ), patch.object(
            acquisition,
            "acquire",
            return_value=acquired,
        ) as acquire_call, patch.object(
            driver,
            "_resolve_work",
        ) as resolve:
            out = driver.advance_once(
                state_path=Path("/tmp/r3-test-state.json"),
                distinguishing_evidence_provider=provider,
                distinguishing_evidence_provider_id="EVIDENCE_PROVIDER",
                verification_frontier_acquisition_provider=Mock(),
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"])
        acquire_call.assert_called_once()
        self.assertIs(
            acquire_call.call_args.kwargs["provider"],
            provider,
        )
        resolve.assert_called_once()

    def test_fabric_forwards_evidence_provider_to_improvement_cycle(self):
        provider = Mock()
        with patch.object(
            fabric.improvement_driver,
            "drain",
            return_value={
                "pass": True,
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "progress_count": 0,
            },
        ) as drain:
            out = fabric.run(
                {
                    "mode": "IMPROVEMENT_CYCLE",
                    "payload": {},
                    "options": {"max_improvement_actions": 1},
                },
                r3_distinguishing_evidence_provider=provider,
                r3_distinguishing_evidence_provider_id="FABRIC_EVIDENCE_PROVIDER",
            )
        self.assertTrue(out["inner_pass"], out)
        self.assertIs(
            drain.call_args.kwargs["distinguishing_evidence_provider"],
            provider,
        )
        self.assertEqual(
            drain.call_args.kwargs["distinguishing_evidence_provider_id"],
            "FABRIC_EVIDENCE_PROVIDER",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
