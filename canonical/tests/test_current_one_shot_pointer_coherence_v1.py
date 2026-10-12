from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import current_one_shot_projection_v1 as projection

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json"


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class CurrentOneShotPointerCoherenceV1Tests(unittest.TestCase):
    def test_stable_load_bearing_bytes_are_exact(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertEqual(
            pointer["predecessor"]["git_blob_sha"],
            git_blob_sha(ROOT / "canonical/runtime/one_shot_verified_closure_v1.py"),
        )
        self.assertEqual(
            pointer["runtime"]["git_blob_sha"],
            git_blob_sha(ROOT / "canonical/runtime/one_shot_reality_closure_v2.py"),
        )
        dynamic = pointer["authority"]["dynamic_current_projection"]
        self.assertEqual(dynamic["path"], projection.PATHS["self"])
        self.assertEqual(
            dynamic["git_blob_sha"],
            git_blob_sha(ROOT / projection.PATHS["self"]),
        )

    def test_moving_r2_and_terminal_truth_resolve_dynamically(self):
        out = projection.evaluate(ROOT)
        self.assertTrue(out["pass"], out)

        r2_path = ROOT / projection.PATHS["r2"]
        terminal_path = ROOT / projection.PATHS["terminal"]
        terminal = json.loads(terminal_path.read_text(encoding="utf-8"))

        self.assertEqual(out["current_r2"]["git_blob_sha"], git_blob_sha(r2_path))
        self.assertEqual(
            out["current_terminal_authority"]["git_blob_sha"],
            git_blob_sha(terminal_path),
        )
        self.assertEqual(
            out["current_terminal_authority"]["pointer_revision"],
            terminal["pointer_revision"],
        )

    def test_future_snapshot_drift_is_observable_not_authoritative(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertFalse(
            pointer["authority"]["static_projection_snapshots_authoritative"]
        )

        with TemporaryDirectory() as td:
            root = Path(td)
            for rel in projection.PATHS.values():
                src = ROOT / rel
                dst = root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)

            terminal_path = root / projection.PATHS["terminal"]
            terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
            terminal["pointer_revision"] = int(terminal["pointer_revision"]) + 1
            terminal["status"] = str(terminal["status"]) + "__SIMULATED_NEXT_REVISION"
            terminal_path.write_text(
                json.dumps(terminal, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            out = projection.evaluate(root)

        self.assertTrue(out["pass"], out)
        self.assertFalse(out["snapshot_drift"]["snapshot_is_authoritative"])
        self.assertTrue(
            out["snapshot_drift"]["terminal_snapshot_differs_from_current"],
            out,
        )
        self.assertEqual(
            out["current_terminal_authority"]["pointer_revision"],
            terminal["pointer_revision"],
        )

    def test_latest_v1_truth_repair_binds_current_v1_bytes(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        latest = pointer["verification"]["latest_v1_truth_repair"]
        verify_path = ROOT / latest["path"]
        self.assertEqual(latest["git_blob_sha"], git_blob_sha(verify_path))

        receipt = json.loads(verify_path.read_text(encoding="utf-8"))
        self.assertIn("26_OF_26", receipt["status"])
        self.assertIn(
            receipt["exact_changed_blobs"][
                "canonical/runtime/one_shot_verified_closure_v1.py"
            ],
            {
                pointer["predecessor"]["git_blob_sha"],
                pointer["verification"]["latest_v1_post_replay_shape_fix"][
                    "prior_verified_v1_git_blob_sha"
                ],
            },
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
