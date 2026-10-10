from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import one_shot_verified_closure_v1 as closure


class OneShotClosureTests(unittest.TestCase):
    def _snap(self, digest, pending):
        return {
            "schema": closure.SCHEMA,
            "digest": digest,
            "state_sha256": "state-" + digest,
            "payload": {
                "state_file": {
                    "path": "canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json",
                    "sha256": "state-" + digest,
                    "bytes": 1,
                },
                "files": [],
                "pending": pending,
                "stats": {},
            },
        }

    def test_scalar_remaining_hard_frontier_is_preserved_as_one_item(self):
        from tempfile import TemporaryDirectory
        import json
        from pathlib import Path

        with TemporaryDirectory() as td:
            root = Path(td)
            gov = root / "canonical" / "governance"
            gov.mkdir(parents=True)
            target = gov / "CURRENT_R2_DECISION_INTELLIGENCE.json"
            target.write_text(json.dumps({
                "status": "OPEN",
                "primary_primitive": "x",
                "primary_primitive_state": "OPEN",
                "remaining_problem_class": "y",
                "remaining_hard_frontier": "FINANCE_SEMANTIC_ADEQUACY_TAIL",
                "current_cell_classifications": {},
                "mechanism_closure": {
                    "universal_positive_action_coverage_closed": False
                },
            }), encoding="utf-8")
            out = closure._canonical_r2_residual(root)

        self.assertEqual(
            out["remaining_hard_frontier"],
            ["FINANCE_SEMANTIC_ADEQUACY_TAIL"],
        )

    def test_empty_queue_is_verified_internal_fixed_point(self):
        snaps = [
            self._snap("a", []),
            self._snap("a", []),
            self._snap("a", []),
        ]
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertTrue(out["pass"])
        self.assertTrue(out["fixed_point"])
        self.assertEqual(
            out["status"],
            "VERIFIED_INTERNAL_FIXED_POINT__IMPROVEMENT_QUEUE_EMPTY",
        )

    def test_empty_r3_queue_does_not_hide_current_r2_internal_gap(self):
        r2_residual = {
            "current_internal_unsolved_count": 1,
            "current_internal_unsolved_cells": [{
                "cell_id": "FINANCE_SEMANTIC_ADEQUACY_TAIL",
                "state": "INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
                "required_action": "ACQUIRE_OR_EXPERIMENT",
                "wake_on": [],
            }],
        }
        snaps = [
            self._snap("a", []),
            self._snap("a", []),
            self._snap("a", []),
        ]
        for snap in snaps:
            snap["payload"]["r2_residual"] = r2_residual
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertFalse(out["pass"], out)
        self.assertTrue(out["fixed_point"], out)
        self.assertEqual(
            out["status"],
            "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
        )
        self.assertTrue(out["residual"]["internally_solvable_gap_remaining"])
        self.assertEqual(out["residual"]["internal_blockers"], [])
        self.assertIn(
            "R2_PENDING_ACQUISITION:FINANCE_SEMANTIC_ADEQUACY_TAIL",
            out["residual"]["evidence_blockers"],
        )
        self.assertTrue(
            out["residual"]["pending_acquisition_or_experiment_required"]
        )
        self.assertEqual(out["residual"]["r2_acquisition_request_count"], 1)
        request = out["residual"]["r2_acquisition_requests"][0]
        self.assertEqual(request["cell_id"], "FINANCE_SEMANTIC_ADEQUACY_TAIL")
        self.assertEqual(request["required_action"], "ACQUIRE_OR_EXPERIMENT")
        self.assertEqual(len(request["request_sha256"]), 64)
        self.assertFalse(request["full_benchmark_default"])

    def test_internal_root1_gap_remains_open(self):
        pending = [{"work_id": "w1", "kind": "EXPAND_SUCCESS_VERIFICATION_FRONTIER"}]
        snaps = [
            self._snap("a", pending),
            self._snap("a", pending),
            self._snap("a", pending),
        ]
        blocker = {
            "work_id": "w1",
            "kind": "EXPAND_SUCCESS_VERIFICATION_FRONTIER",
            "blocker": (
                "ROOT1_CONSTRUCTIVE_R3_VERIFICATION_FRONTIER_GAP__"
                "NO_BOUND_ACQUISITION_ROUTE"
            ),
        }
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [{
                    "status": "IMPROVEMENT_QUEUE_HAS_NO_CURRENTLY_ACTIONABLE_WORK",
                    "blockers": [blocker],
                }],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertFalse(out["pass"])
        self.assertTrue(out["fixed_point"])
        self.assertEqual(out["status"], "OPEN__INTERNAL_UNSOLVED_GAP_REMAINS")
        self.assertTrue(out["residual"]["internally_solvable_gap_remaining"])

    def test_external_evidence_only_fixed_point_stays_open_without_irreducibility_proof(self):
        pending = [{"work_id": "w2", "kind": "COLLECT_MATCHING_VERIFIED_EPISODE"}]
        snaps = [
            self._snap("a", pending),
            self._snap("a", pending),
            self._snap("a", pending),
        ]
        blocker = {
            "work_id": "w2",
            "kind": "COLLECT_MATCHING_VERIFIED_EPISODE",
            "blocker": "WAITING_FOR_NEW_INDEPENDENTLY_VERIFIED_EXPERIENCE",
        }
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [{
                    "status": "IMPROVEMENT_QUEUE_HAS_NO_CURRENTLY_ACTIONABLE_WORK",
                    "blockers": [blocker],
                }],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
        )
        self.assertFalse(out["irreducible_external_information_proved"])

    def test_pending_without_blocker_certificate_fails_closed_as_internal(self):
        pending = [{"work_id": "w-unclassified", "kind": "VERIFY_EPISODE"}]
        snaps = [
            self._snap("a", pending),
            self._snap("a", pending),
            self._snap("a", pending),
        ]
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__INTERNAL_UNSOLVED_GAP_REMAINS")
        self.assertEqual(out["residual"]["class"], "UNCLASSIFIED_UNRESOLVED_WORK")
        self.assertIn(
            "UNCLASSIFIED_UNRESOLVED_WORK_WITHOUT_BLOCKER_CERTIFICATE",
            out["residual"]["internal_blockers"],
        )
        self.assertFalse(out["irreducible_external_information_proved"])

    def test_rejects_false_progress(self):
        pending = [{"work_id": "w3", "kind": "VERIFY_EPISODE"}]
        snaps = [
            self._snap("a", pending),
            self._snap("a", pending),
            self._snap("a", pending),
        ]
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_ADVANCED",
                "pass": True,
                "progress_count": 1,
                "actions": [{"pass": True, "progress": True}],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__CLAIMED_PROGRESS_WITHOUT_STATE_OR_FRONTIER_CHANGE",
        )


    def test_replayable_success_backoff_is_internal_root1_gap(self):
        pending = [{
            "work_id": "w4",
            "kind": "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
            "last_attempt_status": "IMPROVEMENT_PROVIDER_RETURNED_NO_SUCCESS_ADAPTATION",
            "last_attempt_reason": None,
            "frontier_expansion_work_id": "handoff:w4",
            "payload": {
                "replayable": True,
                "proof_available": False,
                "replay_capsule_sha256": "a" * 64,
            },
        }]
        snaps = [
            self._snap("a", pending),
            self._snap("a", pending),
            self._snap("a", pending),
        ]
        blocker = {
            "work_id": "w4",
            "kind": "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
            "blocker": "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE",
        }
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [{"blockers": [blocker]}],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__INTERNAL_UNSOLVED_GAP_REMAINS")
        self.assertIn(
            "ROOT1_SUCCESS_ADAPTER_OR_VERIFIER_FRONTIER_GAP",
            out["residual"]["internal_blockers"],
        )

    def test_unreplayable_historical_success_requires_new_experience(self):
        pending = [{
            "work_id": "w5",
            "kind": "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
            "last_attempt_status": "IMPROVEMENT_ACTION_EXCEPTION",
            "last_attempt_reason": (
                "SelfImprovementError:SUCCESS_OBSERVATION_NOT_REPLAYABLE:observation:x"
            ),
            "frontier_expansion_work_id": None,
            "payload": {
                "replayable": False,
                "proof_available": False,
                "replay_capsule_sha256": None,
            },
        }]
        snaps = [
            self._snap("a", pending),
            self._snap("a", pending),
            self._snap("a", pending),
        ]
        blocker = {
            "work_id": "w5",
            "kind": "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
            "blocker": "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE",
        }
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), patch.object(
            closure.r3,
            "drain",
            return_value={
                "status": "IMPROVEMENT_QUEUE_STABLE",
                "pass": True,
                "progress_count": 0,
                "actions": [{"blockers": [blocker]}],
            },
        ):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT",
        )
        self.assertFalse(out["irreducible_external_information_proved"])
        self.assertIn(
            "NEW_EXPERIENCE_REQUIRED__HISTORICAL_SUCCESS_NOT_REPLAYABLE",
            out["residual"]["evidence_blockers"],
        )


    def test_default_root1_adapter_acquisition_provider_is_bound(self):
        sentinel = object()
        snaps = [
            self._snap("a", []),
            self._snap("a", []),
            self._snap("a", []),
        ]
        with (
            patch.object(
                closure.root1_adapter_acquisition,
                "make_provider",
                return_value=sentinel,
            ) as make_provider,
            patch.object(closure, "frontier_snapshot", side_effect=snaps),
            patch.object(
                closure.r3,
                "drain",
                return_value={
                    "status": "IMPROVEMENT_QUEUE_STABLE",
                    "pass": True,
                    "progress_count": 0,
                    "actions": [],
                },
            ) as drain,
        ):
            out = closure.run(repo_root=".", state_path="state.json")

        self.assertTrue(out["pass"], out)
        make_provider.assert_called_once_with(
            repo_root=".",
            state_path="state.json",
        )
        self.assertIs(
            drain.call_args.kwargs["verification_frontier_acquisition_provider"],
            sentinel,
        )
        self.assertEqual(
            drain.call_args.kwargs[
                "verification_frontier_acquisition_provider_id"
            ],
            "ROOT1_STRUCTURAL_ADAPTER_RULE_ACQUISITION_PROVIDER_V1",
        )


if __name__ == "__main__":
    unittest.main()
