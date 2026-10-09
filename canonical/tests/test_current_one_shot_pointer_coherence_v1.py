from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json"


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class CurrentOneShotPointerCoherenceV1Tests(unittest.TestCase):
    def test_current_load_bearing_bytes_are_exact(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        refresh = pointer["current_projection_refresh_20261009"]

        targets = {
            "one_shot_v1_runtime_git_blob_sha":
                "canonical/runtime/one_shot_verified_closure_v1.py",
            "one_shot_v2_runtime_git_blob_sha":
                "canonical/runtime/one_shot_reality_closure_v2.py",
            "current_r2_pointer_git_blob_sha":
                "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
            "current_terminal_authority_git_blob_sha":
                "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
        }
        for field, rel in targets.items():
            self.assertEqual(refresh[field], git_blob_sha(ROOT / rel), rel)

        self.assertEqual(
            pointer["predecessor"]["git_blob_sha"],
            refresh["one_shot_v1_runtime_git_blob_sha"],
        )
        self.assertEqual(
            pointer["runtime"]["git_blob_sha"],
            refresh["one_shot_v2_runtime_git_blob_sha"],
        )
        self.assertEqual(
            pointer["authority"]["current_terminal_authority_git_blob_sha"],
            refresh["current_terminal_authority_git_blob_sha"],
        )

    def test_current_terminal_revision_matches_pointer(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        terminal = json.loads(
            (ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(
            pointer["authority"]["current_terminal_authority_pointer_revision"],
            terminal["pointer_revision"],
        )
        self.assertEqual(
            pointer["current_projection_refresh_20261009"][
                "current_terminal_authority_pointer_revision"
            ],
            terminal["pointer_revision"],
        )

    def test_latest_v1_truth_repair_binds_current_v1_bytes(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        latest = pointer["verification"]["latest_v1_truth_repair"]
        verify_path = ROOT / latest["path"]
        self.assertEqual(latest["git_blob_sha"], git_blob_sha(verify_path))

        receipt = json.loads(verify_path.read_text(encoding="utf-8"))
        self.assertIn("26_OF_26", receipt["status"])
        self.assertEqual(
            receipt["exact_changed_blobs"][
                "canonical/runtime/one_shot_verified_closure_v1.py"
            ],
            pointer["predecessor"]["git_blob_sha"],
        )

    def test_no_false_terminal_credit_added(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertFalse(pointer["authority"]["terminal_authority"])
        self.assertEqual(
            pointer["current_projection_refresh_20261009"]["terminal_credit_delta"],
            0,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
