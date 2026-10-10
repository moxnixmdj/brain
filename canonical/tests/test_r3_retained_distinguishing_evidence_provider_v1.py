from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from canonical.runtime import astra_runtime
from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_distinguishing_evidence_acquisition_v1 as evidence_acquisition
from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import r3_retained_distinguishing_evidence_provider_v1 as provider
from canonical.runtime import r3_verification_frontier_repair_reducer_v1 as reducer


def _compiled(route: str, obligations: list[str]) -> dict:
    out = {
        "schema": "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_REQUEST_V1",
        "status": "PASS__MINIMUM_STRUCTURAL_DISTINGUISHING_EVIDENCE_REQUEST_READY",
        "pass": True,
        "minimum_missing_obligation_count": len(obligations),
        "candidate_evidence_bundles": [{
            "route": route,
            "missing_obligations": list(obligations),
            "missing_obligation_count": len(obligations),
        }],
    }
    out["request_sha256"] = evidence_acquisition.request_compiler._digest(out)
    return out


class R3RetainedDistinguishingEvidenceProviderV1Tests(unittest.TestCase):
    def test_checkpoint_evidence_is_reconstructed_without_effect_replay(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            checkpoint = root / "checkpoint.json"
            plans = [
                {
                    "type": "invoke_verified_bound_capability_adapter",
                    "args": {
                        "capability_id": "cap.test",
                        "requires": [],
                        "provides": ["effect.done"],
                    },
                },
                {"type": "finish", "args": {"summary": "done"}},
            ]
            plan_sha = astra_runtime._controller_plan_sha256(plans)
            checkpoint.write_text(
                json.dumps({
                    "schema": "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
                    "status": "COMPLETE",
                    "plan_sha256": plan_sha,
                    "completed_actions": [
                        {
                            "cycle": 0,
                            "plan": plans[0],
                            "result": {
                                "pass": True,
                                "status": "PASS__TEST",
                                "composition_capsule_head_hash": "c" * 64,
                                "result_sha256": "d" * 64,
                            },
                        },
                        {
                            "cycle": 1,
                            "plan": plans[1],
                            "result": {"pass": True},
                        },
                    ],
                }),
                encoding="utf-8",
            )
            proof = {
                "material": {
                    "source_schema": "TEST_SUCCESS",
                    "source_status": "PASS",
                    "controller_checkpoint": {
                        "path": "checkpoint.json",
                        "plan_sha256": plan_sha,
                    },
                    "selected_plan": [],
                    "verified_target_effects": [],
                    "execution": [],
                },
            }
            replay = {
                "context": {
                    "mode": "generic",
                    "request": {
                        "task_id": "task-1",
                        "target_effects": ["effect.done"],
                    },
                },
            }
            request = _compiled(
                provider.CHECKPOINT_ROUTE,
                [
                    "NONEMPTY_SELECTED_PLAN",
                    "NONEMPTY_VERIFIED_TARGET_EFFECT_SET",
                    "EXECUTION_COUNT_MATCHES_SELECTED_PLAN_AND_NONZERO",
                    "ALL_EXECUTION_ROWS_PASS",
                    "COMPOSITION_DIGEST_PRESENT_FOR_EVERY_EXECUTION_ROW",
                ],
            )
            with patch.object(
                provider.learning,
                "get_success_proof_context",
                return_value=proof,
            ), patch.object(
                provider.learning,
                "get_success_replay_context",
                return_value=replay,
            ):
                self.assertTrue(
                    provider.can_acquire(
                        request,
                        observation_id="observation:1",
                        state_path=root / "state.json",
                        repo_root=root,
                    )
                )
                out = provider.acquire(
                    {
                        "kind": provider.REQUEST_KIND,
                        "request_sha256": request["request_sha256"],
                        "observation_id": "observation:1",
                        "distinguishing_evidence_request": request,
                    },
                    state_path=root / "state.json",
                    repo_root=root,
                )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["route"], provider.CHECKPOINT_ROUTE)
        self.assertEqual(out["evidence"]["selected_plan"], ["cap.test"])
        self.assertEqual(
            out["evidence"]["verified_target_effects"],
            ["effect.done"],
        )
        self.assertEqual(
            out["evidence"]["execution"][0]["composition_capsule_head_hash"],
            "c" * 64,
        )
        self.assertFalse(out["provider_truth_authority"])
        self.assertFalse(out["verification_authority"])

    def test_raw_metadata_is_reconstructed_from_retained_acceptance_and_replay(self):
        goal = "Reply with exactly hello"
        acceptance = {
            "pass": True,
            "semantic_acceptance_complete": True,
            "task_contract_sha256": "a" * 64,
            "accepted_obligation_ids": ["goal", "literal"],
        }
        proof = {
            "material": {
                "source_schema": "TEST_RAW",
                "source_status": "PASS",
                "raw_goal_acceptance": acceptance,
            },
        }
        replay = {
            "context": {
                "mode": "raw_bound",
                "request": {"task_id": "raw-1", "goal": goal},
            },
        }
        request = _compiled(
            provider.RAW_ROUTE,
            [
                "SEMANTIC_ACCEPTANCE_COMPLETE",
                "RAW_GOAL_DIGEST_BOUND",
                "RAW_TASK_CONTRACT_DIGEST_BOUND",
                "RAW_ACCEPTANCE_OBLIGATION_COUNT_POSITIVE",
                "ALL_RAW_ACCEPTANCE_OBLIGATIONS_ACCEPTED",
            ],
        )
        with patch.object(
            provider.learning,
            "get_success_proof_context",
            return_value=proof,
        ), patch.object(
            provider.learning,
            "get_success_replay_context",
            return_value=replay,
        ):
            out = provider.acquire(
                {
                    "kind": provider.REQUEST_KIND,
                    "request_sha256": request["request_sha256"],
                    "observation_id": "observation:raw",
                    "distinguishing_evidence_request": request,
                },
                state_path=Path("/tmp/unused-state.json"),
                repo_root=Path("."),
            )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["evidence"]["raw_goal_sha256"],
            sha256(goal.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(out["evidence"]["raw_task_contract_sha256"], "a" * 64)
        self.assertEqual(out["evidence"]["raw_acceptance_obligation_count"], 2)
        self.assertEqual(
            out["evidence"]["accepted_raw_obligation_ids"],
            ["goal", "literal"],
        )

    def test_missing_raw_acceptance_receipt_is_not_fabricated(self):
        proof = {"material": {"source_schema": "TEST_RAW", "source_status": "PASS"}}
        replay = {
            "context": {
                "mode": "raw_bound",
                "request": {"task_id": "raw-2", "goal": "x"},
            },
        }
        request = _compiled(
            provider.RAW_ROUTE,
            ["RAW_GOAL_ACCEPTANCE_BINDING_PRESENT"],
        )
        with patch.object(
            provider.learning,
            "get_success_proof_context",
            return_value=proof,
        ), patch.object(
            provider.learning,
            "get_success_replay_context",
            return_value=replay,
        ):
            self.assertFalse(
                provider.can_acquire(
                    request,
                    observation_id="observation:raw",
                    state_path=Path("/tmp/unused-state.json"),
                    repo_root=Path("."),
                )
            )

    def test_driver_uses_native_provider_when_host_provider_absent(self):
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
        request = _compiled(
            provider.CHECKPOINT_ROUTE,
            ["EXECUTION_COUNT_MATCHES_SELECTED_PLAN_AND_NONZERO"],
        )
        reduction = {
            "pass": True,
            "admissible_repair_classes": [reducer.NEW_EVIDENCE],
            "must_acquire_new_distinguishing_evidence": True,
            "distinguishing_evidence_request": request,
        }
        acquired = {
            "schema": evidence_acquisition.SCHEMA,
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
            provider,
            "can_acquire",
            return_value=True,
        ), patch.object(
            provider,
            "acquire",
            return_value={
                "schema": provider.CANDIDATE_SCHEMA,
                "pass": True,
                "request_sha256": request["request_sha256"],
                "route": provider.CHECKPOINT_ROUTE,
                "evidence": {"execution": []},
                "provider_truth_authority": False,
                "verification_authority": False,
                "promotion_authority": False,
                "acceptance_authority": False,
                "terminal_authority": False,
            },
        ), patch.object(
            evidence_acquisition,
            "acquire",
            return_value=acquired,
        ) as acquire_call, patch.object(
            driver,
            "_resolve_work",
        ) as resolve:
            out = driver.advance_once(
                state_path=Path("/tmp/r3-test-state.json"),
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"])
        self.assertEqual(
            acquire_call.call_args.kwargs["provider_id"],
            provider.PROVIDER_ID,
        )
        self.assertTrue(callable(acquire_call.call_args.kwargs["provider"]))
        resolve.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
