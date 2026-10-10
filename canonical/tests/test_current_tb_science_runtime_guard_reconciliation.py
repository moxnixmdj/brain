from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "canonical/governance/CURRENT_TB_SCIENCE_RUNTIME_GUARD.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError("OBJECT_REQUIRED")
    return value


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


class RuntimeGuardDelegationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = load(GUARD)

    def test_exact_runtime_blobs(self) -> None:
        for row in self.guard["runtime"].values():
            self.assertEqual(row["git_blob_sha"], blob(ROOT / row["path"]))

    def test_exact_identity_and_repair_receipts(self) -> None:
        identity = self.guard["logical_attempt_identity"]
        self.assertEqual(identity["git_blob_sha"], blob(ROOT / identity["path"]))
        self.assertEqual(
            identity["basis"],
            "SLOT_ID_PLUS_TASK_DIGEST_PLUS_EXECUTION_CLAIM_BINDING_DIGEST",
        )
        for name in ("identity_repair_verification", "planner_repair_verification"):
            row = self.guard[name]
            self.assertTrue(row["verified"])
            self.assertEqual(row["git_blob_sha"], blob(ROOT / row["path"]))

    def test_mutable_state_is_not_copied_into_runtime_guard(self) -> None:
        live = self.guard["live_state"]
        self.assertEqual(
            live["execution_pointer"],
            "canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json",
        )
        self.assertEqual(
            live["scheduler_pointer"],
            "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json",
        )
        self.assertTrue(live["read_current_values_at_decision_time"])
        self.assertFalse(live["copy_slot_state_here"])
        self.assertFalse(live["copy_benchmark_counts_here"])
        for key in ("counts", "rank18", "rank19", "rank20"):
            self.assertNotIn(key, self.guard)

    def test_guard_grants_no_live_authority(self) -> None:
        for key in (
            "execution_authority",
            "task_read_authority",
            "activation_authority",
            "retry_authority",
            "replacement_authority",
        ):
            self.assertIs(self.guard[key], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
