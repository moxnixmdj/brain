from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime.proof_atom_receipt_index_v2 import _candidate_files
from canonical.runtime.proof_atom_receipt_snapshot_v1 import build_snapshot, seal_candidate_universe


def run(*args: str, cwd: Path) -> str:
    cp = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)
    return cp.stdout.strip()


def init_repo(root: Path) -> None:
    run("git", "init", "-q", cwd=root)
    run("git", "config", "user.email", "proof@example.invalid", cwd=root)
    run("git", "config", "user.name", "proof", cwd=root)
    for rel in (
        "canonical/verification",
        "canonical/capabilities",
        "canonical/governance",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)
        (root / rel / ".keep").write_text("keep\n", encoding="utf-8")
    (root / "canonical/verification/r.json").write_text(
        '{"claim":"R1"}\n', encoding="utf-8"
    )
    run("git", "add", ".", cwd=root)
    run("git", "commit", "-qm", "fixture", cwd=root)


class Tests(unittest.TestCase):
    def test_seal_is_stable_and_binds_complete_candidate_universe(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            files = _candidate_files(root)
            a = seal_candidate_universe(root, files)
            b = seal_candidate_universe(root, files)
            self.assertEqual(a, b)
            self.assertEqual(a["scanned_file_count"], 1)
            self.assertEqual(
                [x["path"] for x in a["scanned_files"]],
                ["canonical/verification/r.json"],
            )
            self.assertEqual(len(a["scanned_manifest_sha256"]), 64)
            self.assertEqual(len(a["repository_commit_sha"]), 40)
            self.assertEqual(len(a["repository_tree_sha"]), 40)

    def test_modified_tracked_candidate_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            p = root / "canonical/verification/r.json"
            p.write_text('{"claim":"changed"}\n', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "WORKTREE_OR_INDEX_DRIFT"):
                seal_candidate_universe(root, _candidate_files(root))


    def test_snapshot_fails_if_index_corpus_digest_differs_from_sealed_universe(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            fake_index = {
                "status": "PASS__FAKE",
                "scanned_file_count": 1,
                "scanned_corpus_manifest_sha256": "0" * 64,
                "atoms": [],
            }
            with patch(
                "canonical.runtime.proof_atom_receipt_snapshot_v1.build_index",
                return_value=fake_index,
            ):
                out = build_snapshot({}, {}, root=root)
            self.assertEqual(out["status"], "FAIL_CLOSED")
            self.assertIn("SCANNED_CORPUS_MANIFEST_MISMATCH", out["errors"])


    def test_untracked_candidate_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            init_repo(root)
            (root / "canonical/verification/untracked.json").write_text(
                '{"claim":"R2"}\n', encoding="utf-8"
            )
            with self.assertRaises(RuntimeError):
                seal_candidate_universe(root, _candidate_files(root))


if __name__ == "__main__":
    unittest.main(verbosity=2)
