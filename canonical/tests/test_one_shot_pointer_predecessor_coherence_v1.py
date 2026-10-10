from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
POINTER_PATH = ROOT / "canonical/governance/CURRENT_ONE_SHOT_REALITY_CLOSURE.json"
RUNTIME_PATH = ROOT / "canonical/runtime/one_shot_verified_closure_v1.py"


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("utf-8")
    return hashlib.sha1(header + payload).hexdigest()


class OneShotPointerPredecessorCoherenceV1Tests(unittest.TestCase):
    def test_current_pointer_binds_exact_v1_runtime_blob(self):
        pointer = json.loads(POINTER_PATH.read_text(encoding="utf-8"))
        predecessor = pointer.get("predecessor")
        self.assertIsInstance(predecessor, dict)
        self.assertEqual(
            predecessor.get("path"),
            "canonical/runtime/one_shot_verified_closure_v1.py",
        )
        self.assertEqual(
            predecessor.get("git_blob_sha"),
            _git_blob_sha(RUNTIME_PATH),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
