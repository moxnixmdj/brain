from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_root1_adapter_gap_witness_v1 as witness


def _state_fixture(root: Path):
    state = learning._empty_state()
    state_path = root / "state.json"

    adapter_sha = witness._frontier_sha256(
        witness.SUCCESS_ADAPTER_FRONTIER_PATHS,
        repo_root=witness.Path(__file__).resolve().parents[2],
    )
    authority_sha = witness._frontier_sha256(
        witness.SUCCESS_VERIFICATION_AUTHORITY_PATHS,
        repo_root=witness.Path(__file__).resolve().parents[2],
    )

    observation_id = "observation:test-adapter-gap"
    blocked_id = "work:blocked-success"
    handoff_id = "work:frontier-expansion"

    replay_context = {
        "mode": "specialized",
        "request": {"task_id": "t"},
    }
    replay_capsule = learning._make_retry_capsule(replay_context)
    material = {"source_schema": "TEST_SUCCESS", "source_status": "PASS"}
    proof_capsule = {
        "schema": "PROJECT_BRAIN_SUCCESS_PROOF_CAPSULE_V1",
        "sha256": learning._sha(material),
        "material": material,
        "secret_scan": "PASS",
    }

    state["observations"][observation_id] = {
        "observation_id": observation_id,
        "output_sha256": "a" * 64,
        "replay_capsule": replay_capsule,
        "proof_capsule": proof_capsule,
        "learning_disposition_reason": (
            "OWNED_SUCCESS_ADAPTER_RETURNED_NO_CANDIDATE"
        ),
        "adapter_frontier_sha256": adapter_sha,
        "verification_authority_sha256": authority_sha,
        "frontier_expansion_work_id": handoff_id,
    }
    state["improvement_queue"][blocked_id] = {
        "work_id": blocked_id,
        "kind": witness.BLOCKED_KIND,
        "status": "PARKED",
        "parked_reason": "NO_CURRENT_OWNED_VERIFICATION_PATH",
        "frontier_expansion_work_id": handoff_id,
        "adapter_frontier_sha256": adapter_sha,
        "verification_authority_sha256": authority_sha,
    }
    state["improvement_queue"][handoff_id] = {
        "work_id": handoff_id,
        "kind": witness.FRONTIER_KIND,
        "status": "PENDING",
        "payload": {
            "blocked_success_work_id": blocked_id,
            "observation_id": observation_id,
            "adapter_frontier_sha256": adapter_sha,
            "verification_authority_sha256": authority_sha,
        },
    }
    learning._refresh_stats(state)
    learning._write_state(state, state_path)
    return state_path, state["improvement_queue"][handoff_id]


class R3Root1AdapterGapWitnessV1Tests(unittest.TestCase):
    def test_exact_parked_adapter_miss_reopens_root1_on_one_primitive(self):
        with tempfile.TemporaryDirectory() as td:
            state_path, work = _state_fixture(Path(td))
            out = witness.compile_gap(
                work,
                state_path=state_path,
                repo_root=Path(__file__).resolve().parents[2],
                acquisition_provider_bound=False,
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["root1_positive_gap_established"])
        self.assertEqual(
            out["required_primitive"],
            witness.REQUIRED_PRIMITIVE,
        )
        tx = out["root1_transaction"]
        self.assertTrue(tx["gate"]["root1_active"])
        self.assertEqual(
            tx["minimum_delta"]["missing_primitives"],
            [witness.REQUIRED_PRIMITIVE],
        )
        self.assertEqual(
            tx["route_cover"]["status"],
            "NO_ADMISSIBLE_ROUTE_COVER",
        )
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_stale_adapter_frontier_does_not_reopen_root1(self):
        with tempfile.TemporaryDirectory() as td:
            state_path, work = _state_fixture(Path(td))
            state = learning.load_state(state_path)
            state["improvement_queue"][work["work_id"]]["payload"][
                "adapter_frontier_sha256"
            ] = "0" * 64
            learning._write_state(state, state_path)
            out = witness.compile_gap(
                work,
                state_path=state_path,
                repo_root=Path(__file__).resolve().parents[2],
                acquisition_provider_bound=False,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "SUCCESS_ADAPTER_FRONTIER_CHANGED__REACTIVATE_BEFORE_ROOT1_GAP",
        )

    def test_owned_adapter_candidate_now_available_blocks_root1_gap(self):
        with tempfile.TemporaryDirectory() as td:
            state_path, work = _state_fixture(Path(td))
            with patch.object(
                witness.bound_adapter,
                "adapt",
                return_value={"candidate_only": True},
            ):
                out = witness.compile_gap(
                    work,
                    state_path=state_path,
                    repo_root=Path(__file__).resolve().parents[2],
                    acquisition_provider_bound=False,
                )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "OWNED_ADAPTER_CANDIDATE_NOW_AVAILABLE__ROOT1_GAP_NOT_ESTABLISHED",
        )

    def test_bound_acquisition_provider_prevents_gap_compiler_from_claiming_authority(self):
        with tempfile.TemporaryDirectory() as td:
            state_path, work = _state_fixture(Path(td))
            out = witness.compile_gap(
                work,
                state_path=state_path,
                repo_root=Path(__file__).resolve().parents[2],
                acquisition_provider_bound=True,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "ACQUISITION_PROVIDER_ALREADY_BOUND__GAP_COMPILER_NOT_AUTHORITY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
