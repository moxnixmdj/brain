from __future__ import annotations

import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import r3_historical_failure_irreducibility_v1 as cert
from canonical.runtime import one_shot_verified_closure_v1 as closure


class HistoricalFailureIrreducibilityV1Tests(unittest.TestCase):
    def _fixture(self, root: Path):
        core = {
            "status": "FAIL_CLOSED",
            "reason": None,
            "next_required_edge": None,
            "repair_class": cert.SUPPORTED_REPAIR_CLASS,
            "falsified_capability_ids": [],
            "deferred_capability_ids": [],
            "counterexamples": [],
            "attempts": [],
        }
        fid = cert._sha(core)
        wid = "work:test-historical-failure"
        state = {
            "improvement_queue": {
                wid: {
                    "work_id": wid,
                    "kind": "REPAIR_FAILURE_CLASS",
                    "status": "PENDING",
                    "identity": {
                        "failure_fingerprint": fid,
                        "retry_capsule_sha256": None,
                    },
                    "payload": {
                        "failure_fingerprint": fid,
                        "repair_class": cert.SUPPORTED_REPAIR_CLASS,
                        "status": "FAIL_CLOSED",
                        "reason": None,
                        "retry_capsule_sha256": None,
                    },
                }
            },
            "failures": {
                fid: {
                    **core,
                    "failure_fingerprint": fid,
                    "count": 2,
                    "retry_capsules": {},
                    "last_retry_capsule_sha256": None,
                    "repair_receipts": {},
                }
            },
        }
        state_path = root / "canonical" / "runtime" / "SELF_IMPROVEMENT_STATE_V1.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state), encoding="utf-8")
        return state_path, state, wid, fid

    def test_exact_generic_unreplayable_failure_proves_external_information_required(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_path, state, wid, fid = self._fixture(root)
            fake = types.SimpleNamespace(load_state=lambda path: state)
            with patch.object(cert, "_learning_module", return_value=fake):
                out = cert.certify(wid, state_path=state_path, repo_root=root)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["irreducible_external_information_proved"])
        self.assertEqual(out["failure_fingerprint"], fid)
        self.assertTrue(out["future_evidence_reopens"])
        self.assertFalse(out["permanent_nonrepairability_claimed"])

    def test_retry_capsule_presence_rejects_certificate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_path, state, wid, fid = self._fixture(root)
            state["failures"][fid]["retry_capsules"] = {
                "a" * 64: {"context": {"task_id": "recoverable"}}
            }
            fake = types.SimpleNamespace(load_state=lambda path: state)
            with patch.object(cert, "_learning_module", return_value=fake):
                out = cert.certify(wid, state_path=state_path, repo_root=root)
        self.assertFalse(out["pass"])
        self.assertFalse(out["irreducible_external_information_proved"])

    def test_task_identity_presence_rejects_certificate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_path, state, wid, _ = self._fixture(root)
            state["improvement_queue"][wid]["payload"]["task_id"] = "recoverable-task"
            fake = types.SimpleNamespace(load_state=lambda path: state)
            with patch.object(cert, "_learning_module", return_value=fake):
                out = cert.certify(wid, state_path=state_path, repo_root=root)
        self.assertFalse(out["pass"])

    def test_one_shot_accepts_only_explicit_strict_failure_certificate(self):
        pending = [{
            "work_id": "w-failure",
            "kind": "REPAIR_FAILURE_CLASS",
            "last_attempt_status": "IMPROVEMENT_REPAIR_BLOCKED__REPLAY_CAPSULE_REQUIRED",
            "last_attempt_reason": None,
            "payload": {
                "retry_capsule_sha256": None,
                "repair_class": cert.SUPPORTED_REPAIR_CLASS,
            },
        }]
        def snap(digest):
            return {
                "schema": closure.SCHEMA,
                "digest": digest,
                "state_sha256": "state-" + digest,
                "payload": {
                    "state_file": {"path": "state.json", "sha256": "state-" + digest, "bytes": 1},
                    "files": [],
                    "pending": pending,
                    "stats": {},
                },
            }
        snaps = [snap("a"), snap("a"), snap("a")]
        blocker = {
            "work_id": "w-failure",
            "kind": "REPAIR_FAILURE_CLASS",
            "blocker": "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE",
        }
        strict = {
            "pass": True,
            "status": "PASS__ALL_PENDING_FAILURE_WORK_REQUIRES_EXTERNAL_REPLAY_INFORMATION",
            "irreducible_external_information_proved": True,
        }
        with patch.object(closure, "frontier_snapshot", side_effect=snaps), \
             patch.object(closure.r3, "drain", return_value={
                 "status": "IMPROVEMENT_QUEUE_STABLE",
                 "pass": True,
                 "progress_count": 0,
                 "actions": [{"blockers": [blocker]}],
             }), \
             patch.object(closure.historical_evidence, "certify_pending_set", return_value={"pass": False}), \
             patch.object(closure.historical_failure, "certify_pending_set", return_value=strict):
            out = closure.run(repo_root=".", state_path="state.json")
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["fixed_point"])
        self.assertEqual(
            out["status"],
            "VERIFIED_FIXED_POINT__IRREDUCIBLE_EXTERNAL_INFORMATION_REQUIRED",
        )
        self.assertTrue(out["irreducible_external_information_proved"])
        self.assertEqual(out["strict_external_failure_certificate"], strict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
